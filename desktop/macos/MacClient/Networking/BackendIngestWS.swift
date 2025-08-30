import Foundation

/// Backend Ingest WebSocket client for routing audio to backend instead of direct Deepgram
/// Protocol: TEXT frame for handshake/control, BINARY frame for PCM data
/// 
/// Features: State machine, guarded send, exponential backoff reconnect, PCM ring buffer
/// Uses WebSocketURLUtil for consistent URL normalization and scheme handling.
final class BackendIngestWS {
    
    // MARK: - State Machine
    
    enum State {
        case idle
        case connecting
        case connected
        case closing
        case disconnected
        
        var description: String {
            switch self {
            case .idle: return "idle"
            case .connecting: return "connecting"
            case .connected: return "connected"
            case .closing: return "closing"
            case .disconnected: return "disconnected"
            }
        }
    }
    
    // MARK: - PCM Ring Buffer
    
    private struct PCMRingBuffer {
        private var micBuffer: [Data] = []
        private var systemBuffer: [Data] = []
        private let maxBufferDuration: TimeInterval = 0.5 // 500ms
        private let sampleRate: Int = 16000
        private let maxBufferSize: Int
        
        init() {
            // Calculate max buffer size for 500ms at 16kHz mono Int16
            self.maxBufferSize = Int(maxBufferDuration * Double(sampleRate) * 2) // 2 bytes per sample
        }
        
        mutating func add(_ data: Data, source: String) {
            if source == "mic" {
                micBuffer.append(data)
                
                // Keep only recent data within buffer duration
                let totalSize = micBuffer.reduce(0) { $0 + $1.count }
                if totalSize > maxBufferSize {
                    // Remove oldest chunks until we're under limit
                    var currentSize = totalSize
                    while currentSize > maxBufferSize && !micBuffer.isEmpty {
                        let removed = micBuffer.removeFirst()
                        currentSize -= removed.count
                    }
                }
            } else {
                systemBuffer.append(data)
                
                // Keep only recent data within buffer duration
                let totalSize = systemBuffer.reduce(0) { $0 + $1.count }
                if totalSize > maxBufferSize {
                    // Remove oldest chunks until we're under limit
                    var currentSize = totalSize
                    while currentSize > maxBufferSize && !systemBuffer.isEmpty {
                        let removed = systemBuffer.removeFirst()
                        currentSize -= removed.count
                    }
                }
            }
        }
        
        func getBuffered(source: String) -> [Data] {
            return source == "mic" ? micBuffer : systemBuffer
        }
        
        mutating func flush(source: String? = nil) {
            if let source = source {
                if source == "mic" {
                    micBuffer.removeAll()
                } else {
                    systemBuffer.removeAll()
                }
            } else {
                micBuffer.removeAll()
                systemBuffer.removeAll()
            }
        }
    }
    
    // MARK: - Handshake Structure
    
    struct Handshake: Codable {
        let type: String = "handshake"
        let source: String       // "mic" | "system"
        let sample_rate: Int     // 48000
        let channels: Int        // 1
        let language: String     // "tr" | "en" | "auto"
        let ai_mode: String      // "standard" | "super"
        let device_id: String
    }

    // MARK: - Properties
    
    private var task: URLSessionWebSocketTask?
    private let session: URLSession = {
        let cfg = URLSessionConfiguration.default
        cfg.timeoutIntervalForRequest = 30
        cfg.timeoutIntervalForResource = 60
        return URLSession(configuration: cfg)
    }()

    private let maxChunkBytes = 32_000 // Backend MAX_INGEST_MSG_BYTES=32768 altında tut
    
    // State management
    private var state: State = .idle {
        didSet {
            onLog?("[WS] State: \(oldValue.description) → \(state.description)")
            
            // State-based actions
            switch state {
            case .connected:
                resetRetryCount()
                startKeepAlive()
                flushBufferedPCM()
            case .disconnected, .closing:
                stopKeepAlive()
            default:
                break
            }
        }
    }
    
    // PCM buffering
    private var pcmBuffer = PCMRingBuffer()
    
    // Connection parameters for reconnection
    private var connectionParams: (baseURL: String, meetingId: String, source: String, jwtToken: String, handshake: Handshake)?
    
    // Retry logic with exponential backoff
    private var retryCount = 0
    private let maxRetries = 5
    private let backoffDelays: [TimeInterval] = [1.0, 2.0, 5.0, 10.0, 30.0]
    private var retryTask: Task<Void, Never>?
    
    // Keep-alive mechanism
    private var keepAliveTimer: Timer?
    private let keepAliveInterval: TimeInterval = 30.0
    
    // Callbacks
    var onLog: ((String) -> Void)?
    var onError: ((String) -> Void)?
    var onConnected: (() -> Void)?
    var onDisconnected: (() -> Void)?
    
    // MARK: - Computed Properties
    
    var isConnected: Bool {
        return state == .connected
    }
    
    var canSend: Bool {
        return state == .connected && task != nil
    }


    
    // MARK: - Helper Methods
    
    /// Get exponential backoff delay based on retry count
    private func getRetryDelay() -> TimeInterval {
        let index = min(retryCount, backoffDelays.count - 1)
        return backoffDelays[index]
    }
    
    /// Reset retry count on successful connection
    private func resetRetryCount() {
        retryCount = 0
        retryTask?.cancel()
        retryTask = nil
    }
    
    /// Start keep-alive timer (only in connected state)
    private func startKeepAlive() {
        guard state == .connected else { return }
        
        stopKeepAlive() // Stop existing timer
        
        keepAliveTimer = Timer.scheduledTimer(withTimeInterval: keepAliveInterval, repeats: true) { [weak self] _ in
            self?.sendKeepAlive()
        }
        
        onLog?("[WS] Keep-alive timer started (\(keepAliveInterval)s interval)")
    }
    
    /// Stop keep-alive timer
    private func stopKeepAlive() {
        keepAliveTimer?.invalidate()
        keepAliveTimer = nil
        onLog?("[WS] Keep-alive timer stopped")
    }
    
    /// Send keep-alive ping
    private func sendKeepAlive() {
        guard canSend else {
            onLog?("[WS] Keep-alive skipped - not connected")
            return
        }
        
        let keepAliveMsg = #"{"type":"ping","timestamp":"\(Date().timeIntervalSince1970)"}"#
        sendText(keepAliveMsg)
    }
    
    /// Flush buffered PCM data after reconnection
    private func flushBufferedPCM() {
        guard canSend else { return }
        
        // Flush mic buffer
        let micData = pcmBuffer.getBuffered(source: "mic")
        if !micData.isEmpty {
            onLog?("[WS] Flushing \(micData.count) mic PCM chunks from buffer")
            for data in micData {
                sendPCMInternal(data, source: "mic")
            }
        }
        
        // Flush system buffer
        let systemData = pcmBuffer.getBuffered(source: "system")
        if !systemData.isEmpty {
            onLog?("[WS] Flushing \(systemData.count) system PCM chunks from buffer")
            for data in systemData {
                sendPCMInternal(data, source: "system")
            }
        }
        
        // Clear buffers after flushing
        pcmBuffer.flush()
    }
    
    /// Schedule reconnection with exponential backoff
    private func scheduleReconnect() {
        guard let params = connectionParams else {
            onError?("[WS] No connection parameters for reconnect")
            state = .disconnected
            return
        }
        
        guard retryCount < maxRetries else {
            onError?("[WS] Max retries (\(maxRetries)) exceeded - giving up")
            state = .disconnected
            onDisconnected?()
            return
        }
        
        retryCount += 1
        let delay = getRetryDelay()
        state = .disconnected
        
        onLog?("[WS] Scheduling reconnect \(retryCount)/\(maxRetries) in \(String(format: "%.1f", delay))s...")
        
        retryTask = Task {
            try? await Task.sleep(nanoseconds: UInt64(delay * 1_000_000_000))
            
            await MainActor.run {
                guard self.state == .disconnected else {
                    self.onLog?("[WS] Reconnect cancelled - state changed")
                    return
                }
                
                self.onLog?("[WS] Attempting reconnect \(self.retryCount)/\(self.maxRetries)")
                self.connectInternal(
                    baseURL: params.baseURL,
                    meetingId: params.meetingId,
                    source: params.source,
                    jwtToken: params.jwtToken,
                    handshake: params.handshake
                )
            }
        }
    }

    // MARK: - Public API
    
    func open(baseURL: String, meetingId: String, source: String, jwtToken: String, handshake: Handshake) {
        // Store connection parameters for reconnection
        connectionParams = (baseURL, meetingId, source, jwtToken, handshake)
        
        // Close any existing connection
        close(sendFinalize: false)
        
        // Start fresh connection
        connectInternal(baseURL: baseURL, meetingId: meetingId, source: source, jwtToken: jwtToken, handshake: handshake)
    }
    
    private func connectInternal(baseURL: String, meetingId: String, source: String, jwtToken: String, handshake: Handshake) {
        guard state == .idle || state == .disconnected else {
            onLog?("[WS] Connection attempt ignored - current state: \(state.description)")
            return
        }
        
        state = .connecting
        onLog?("[WS] Connecting to: \(baseURL)")

        do {
            // Sanitize the JWT token first (inline implementation)
            let cleanToken = jwtToken.components(separatedBy: .whitespacesAndNewlines).joined().trimmingCharacters(in: .whitespacesAndNewlines)
            let maskedToken = cleanToken.count > 6 ? "***\(cleanToken.suffix(6))" : "***"
            onLog?("[WS] Using token: \(maskedToken)")
            
            // Validate JWT structure (3 parts separated by dots)
            let tokenParts = cleanToken.components(separatedBy: ".")
            guard tokenParts.count == 3 && tokenParts.allSatisfy({ !$0.isEmpty }) else {
                throw NSError(domain: "BackendIngestWS", code: -4, userInfo: [NSLocalizedDescriptionKey: "Invalid JWT token structure"])
            }
            
            // Build WebSocket URL with source parameter (inline implementation)
            let path = "/api/v1/ws/ingest/meetings/\(meetingId)"
            
            // Parse base URL and construct WebSocket URL
            guard let baseURLObj = URL(string: baseURL) else {
                throw NSError(domain: "BackendIngestWS", code: -1, userInfo: [NSLocalizedDescriptionKey: "Invalid base URL format"])
            }
            
            // Build WebSocket URL components
            var components = URLComponents()
            
            // Determine scheme (ws for local, wss for prod)
            let isLocal = baseURL.contains("localhost") || baseURL.contains("127.0.0.1")
            components.scheme = isLocal ? "ws" : "wss"
            
            // Set host (force IPv4 for localhost)
            let host = baseURLObj.host ?? "127.0.0.1"
            components.host = host == "localhost" ? "127.0.0.1" : host
            
            // Set port
            components.port = baseURLObj.port ?? (isLocal ? 8000 : nil)
            
            // Set path
            components.path = path
            
            // Add source query parameter
            components.queryItems = [URLQueryItem(name: "source", value: source)]
            
            guard let wsURL = components.url else {
                throw NSError(domain: "BackendIngestWS", code: -2, userInfo: [NSLocalizedDescriptionKey: "Failed to build WebSocket URL"])
            }
            
            onLog?("[WS] Built WebSocket URL: \(wsURL.absoluteString)")
            
            // Create URL request with Authorization header (header-first approach)
            var request = URLRequest(url: wsURL)
            request.setValue("Bearer \(cleanToken)", forHTTPHeaderField: "Authorization")
            request.setValue("websocket", forHTTPHeaderField: "Upgrade")
            request.setValue("upgrade", forHTTPHeaderField: "Connection")
            request.setValue("13", forHTTPHeaderField: "Sec-WebSocket-Version")
            
            onLog?("[WS] Using Bearer token in Authorization header")
            
            // Create WebSocket task with request (includes headers)
            let task = session.webSocketTask(with: request)
            
            self.task = task
            task.resume()
            onLog?("✅ WebSocket task created and resumed")
            
        } catch {
            onError?("[WS] Failed to create WebSocket task: \(error.localizedDescription)")
            state = .disconnected
            scheduleReconnect()
            return
        }

        // Start receive loop
        startReceiveLoop()

        // Send handshake (TEXT)
        do {
            let data = try JSONEncoder().encode(handshake)
            let txt = String(data: data, encoding: .utf8) ?? "{\"type\":\"handshake\"}"
            sendText(txt)
            onLog?("[WS] Handshake sent")
        } catch {
            onError?("[WS] Handshake encode error: \(error.localizedDescription)")
            state = .disconnected
            scheduleReconnect()
            return
        }
    }

    func sendPCM(_ pcm: Data, source: String) {
        // Guarded send - only send if connected
        guard canSend else {
            // Buffer PCM data if we're not connected but might reconnect
            if state == .connecting || state == .disconnected {
                pcmBuffer.add(pcm, source: source)
                onLog?("[WS] Buffered \(pcm.count) bytes PCM (\(source)) - state: \(state.description)")
            }
            return
        }

        sendPCMInternal(pcm, source: source)
    }
    
    private func sendPCMInternal(_ pcm: Data, source: String) {
        guard let task = task else { return }

        Task {
            await sendPCMAsync(pcm, task: task, source: source)
        }
    }
    
    private func sendPCMAsync(_ pcm: Data, task: URLSessionWebSocketTask, source: String) async {
        var offset = 0
        while offset < pcm.count {
            let end = min(offset + maxChunkBytes, pcm.count)
            let chunk = pcm.subdata(in: offset..<end)
            let msg = URLSessionWebSocketTask.Message.data(chunk)
            
            // Check if still connected before sending each chunk
            guard canSend else {
                onLog?("[WS] Send cancelled - connection lost during PCM transmission")
                return
            }
            
            do {
                try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<Void, Error>) in
                    task.send(msg) { [weak self] err in
                        if let err = err {
                            self?.onError?("❌ Failed to send PCM chunk (\(chunk.count)B, \(source)): \(err.localizedDescription)")
                            continuation.resume(throwing: err)
                        } else {
                            continuation.resume()
                        }
                    }
                }
            } catch {
                onError?("⚠️ PCM chunk send failed (\(source)), continuing: \(error.localizedDescription)")
                // On send error, trigger reconnection
                if state == .connected {
                    state = .disconnected
                    scheduleReconnect()
                }
                return
            }
            offset = end
        }
    }

    func sendText(_ text: String) {
        guard canSend else { 
            onLog?("[WS] Text send skipped - not connected")
            return 
        }
        
        task?.send(.string(text)) { [weak self] err in
            if let err = err {
                self?.onError?("[WS] Send text error: \(err.localizedDescription)")
                // On send error, trigger reconnection
                if self?.state == .connected {
                    self?.state = .disconnected
                    self?.scheduleReconnect()
                }
            } else {
                self?.onLog?("📤 Sent text (\(text.prefix(64))...)")
            }
        }
    }

    func close(sendFinalize: Bool = true) {
        guard state != .idle && state != .disconnected else { return }
        
        state = .closing
        
        // Cancel any pending reconnection
        retryTask?.cancel()
        retryTask = nil
        
        // Clear buffers on explicit close
        pcmBuffer.flush()
        
        if let task = task {
            if sendFinalize && state != .disconnected {
                // Send finalize message
                let finalizeJSON = #"{"type":"finalize"}"#
                task.send(.string(finalizeJSON)) { [weak self] _ in
                    self?.completeClose()
                }
                
                // Fallback timeout for close completion
                DispatchQueue.main.asyncAfter(deadline: .now() + 2.0) { [weak self] in
                    self?.completeClose()
                }
            } else {
                completeClose()
            }
        } else {
            completeClose()
        }
    }
    
    private func completeClose() {
        guard state == .closing else { return }
        
        task?.cancel(with: .goingAway, reason: nil)
        task = nil
        state = .disconnected
        
        onDisconnected?()
        onLog?("[WS] Connection closed")
    }
    
    deinit {
        close(sendFinalize: false)
        onLog?("[WS] BackendIngestWS deinitialized")
    }

    private func startReceiveLoop() {
        guard let task = task else { return }
        
        task.receive { [weak self] result in
            guard let self = self else { return }
            
            switch result {
            case .failure(let error):
                self.handleReceiveError(error)
                
            case .success(let message):
                self.handleReceiveMessage(message)
                
                // Continue receive loop if still connected
                if self.state == .connected || self.state == .connecting {
                    self.startReceiveLoop()
                }
            }
        }
    }
    
    private func handleReceiveError(_ error: Error) {
        let nsError = error as NSError
        onError?("[WS] Receive error: \(error.localizedDescription)")
        onLog?("[WS] Error code: \(nsError.code), domain: \(nsError.domain)")
        
        // Transition to disconnected state
        if state == .connected || state == .connecting {
            state = .disconnected
            
            // Check for specific errors that should trigger retry
            let shouldRetry = shouldRetryForError(nsError)
            
            if shouldRetry {
                onLog?("[WS] Error is retryable - scheduling reconnect")
                scheduleReconnect()
            } else {
                onLog?("[WS] Error is not retryable - giving up")
                onDisconnected?()
            }
        }
    }
    
    private func handleReceiveMessage(_ message: URLSessionWebSocketTask.Message) {
        switch message {
        case .string(let text):
            onLog?("📥 [text] \(text.prefix(140))")
            
            // Handle specific message types
            if let data = text.data(using: .utf8),
               let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
               let type = json["type"] as? String {
                
                switch type {
                case "connected":
                    // Server confirmed connection
                    if state == .connecting {
                        state = .connected
                        onConnected?()
                        onLog?("[WS] Connection confirmed by server")
                    }
                case "pong":
                    onLog?("[WS] Keep-alive pong received")
                case "error":
                    if let message = json["message"] as? String {
                        onError?("[WS] Server error: \(message)")
                    }
                default:
                    break
                }
            }
            
        case .data(let data):
            onLog?("📥 [data] \(data.count) bytes")
            
        @unknown default:
            onLog?("📥 [unknown message type]")
        }
    }
    
    private func shouldRetryForError(_ error: NSError) -> Bool {
        switch error.code {
        case -1011: // NSURLErrorBadServerResponse
            return true
        case -1004, 61: // Connection refused
            return true
        case -1001: // Request timeout
            return true
        case -1009: // Not connected to internet
            return false // Don't retry network issues
        case 1000...1015: // WebSocket close codes
            return error.code != 1000 // Don't retry normal close
        default:
            return true // Retry other errors
        }
    }
}