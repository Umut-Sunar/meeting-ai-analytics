import Foundation

/// Backend Ingest WebSocket client for routing audio to backend instead of direct Deepgram
/// Protocol: TEXT frame for handshake/control, BINARY frame for PCM data
/// 
/// Uses WebSocketURLUtil for consistent URL normalization and scheme handling.
final class BackendIngestWS {
    
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

    private var task: URLSessionWebSocketTask?
    private let session: URLSession = {
        let cfg = URLSessionConfiguration.default
        cfg.timeoutIntervalForRequest = 30
        cfg.timeoutIntervalForResource = 60
        return URLSession(configuration: cfg)
    }()

    private let sendQueue = DispatchQueue(label: "ws.send.queue")
    private let maxChunkBytes = 32_000 // Backend MAX_INGEST_MSG_BYTES=32768 altında tut
    private(set) var isOpen = false

    // Retry logic
    private var retryCount = 0
    private let maxRetries = 5
    private var retryTask: Task<Void, Never>?
    private var isRetrying = false
    
    // Callbacks
    var onLog: ((String) -> Void)?
    var onError: ((String) -> Void)?
    var onConnected: (() -> Void)?
    var onDisconnected: (() -> Void)?


    
    /// Calculate exponential backoff delay
    private func getRetryDelay() -> TimeInterval {
        let baseDelay: TimeInterval = 0.5
        let maxDelay: TimeInterval = 10.0
        let delay = baseDelay * pow(2.0, Double(retryCount))
        return min(delay, maxDelay)
    }
    
    /// Retry connection with exponential backoff
    private func scheduleRetry(baseURL: String, meetingId: String, source: String, jwtToken: String, handshake: Handshake) {
        guard !isRetrying && retryCount < maxRetries else {
            onError?("Max retries (\(maxRetries)) exceeded")
            return
        }
        
        isRetrying = true
        retryCount += 1
        let delay = getRetryDelay()
        
        onLog?("[WS] Retry \(retryCount)/\(maxRetries) in \(String(format: "%.1f", delay))s...")
        
        retryTask = Task {
            try? await Task.sleep(nanoseconds: UInt64(delay * 1_000_000_000))
            await MainActor.run {
                self.isRetrying = false
                self.open(baseURL: baseURL, meetingId: meetingId, source: source, jwtToken: jwtToken, handshake: handshake)
            }
        }
    }

    func open(baseURL: String, meetingId: String, source: String, jwtToken: String, handshake: Handshake) {
        close(sendFinalize: false)
        
        onLog?("[WS] Attempting connection to: \(baseURL)")

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
            isOpen = true
            onLog?("✅ WebSocket connection initiated")
            
        } catch {
            onError?("Failed to create WebSocket task: \(error.localizedDescription)")
            scheduleRetry(baseURL: baseURL, meetingId: meetingId, source: source, jwtToken: jwtToken, handshake: handshake)
            return
        }

        // receive loop with error handling
        receiveLoopWithRetry(baseURL: baseURL, meetingId: meetingId, source: source, jwtToken: jwtToken, handshake: handshake)

        // send handshake (TEXT)
        do {
            let data = try JSONEncoder().encode(handshake)
            let txt = String(data: data, encoding: .utf8) ?? "{\"type\":\"handshake\"}"
            sendText(txt)
        } catch {
            onError?("Handshake encode error: \(error.localizedDescription)")
            scheduleRetry(baseURL: baseURL, meetingId: meetingId, source: source, jwtToken: jwtToken, handshake: handshake)
            return
        }

        // Reset retry count on successful connection
        retryCount = 0
        onConnected?()
    }

    func sendPCM(_ pcm: Data) {
        guard isOpen, let task = task else { return }

        sendQueue.async { [weak self, weak task] in
            guard let self, let task else { return }
            var offset = 0
            while offset < pcm.count {
                let end = min(offset + self.maxChunkBytes, pcm.count)
                let chunk = pcm.subdata(in: offset..<end)
                let msg = URLSessionWebSocketTask.Message.data(chunk)
                let sem = DispatchSemaphore(value: 0)
                task.send(msg) { err in
                    if let err = err {
                        self.onError?("❌ Failed to send PCM chunk (\(chunk.count)B): \(err.localizedDescription)")
                    }
                    sem.signal()
                }
                sem.wait()
                offset = end
            }
        }
    }

    func sendText(_ text: String) {
        guard isOpen else { return }
        task?.send(.string(text)) { [weak self] err in
            if let err = err {
                self?.onError?("WS send text error: \(err.localizedDescription)")
            } else {
                self?.onLog?("📤 sent text (\(text.prefix(64))...)")
            }
        }
    }

    func close(sendFinalize: Bool) {
        guard let task else { return }
        if sendFinalize {
            // finalize TEXT
            let finalizeJSON = #"{"type":"finalize"}"#
            task.send(.string(finalizeJSON)) { _ in }
        }
        isOpen = false
        task.cancel(with: .goingAway, reason: nil)
        onDisconnected?()
        self.task = nil
    }

    private func receiveLoop() {
        task?.receive { [weak self] result in
            guard let self else { return }
            switch result {
            case .failure(let err):
                self.onError?("WebSocket receive error: \(err.localizedDescription)")
            case .success(let msg):
                switch msg {
                case .string(let s):
                    self.onLog?("📥 [text] \(s.prefix(140))")
                case .data(let d):
                    self.onLog?("📥 [\(d.count) bytes]")
                @unknown default:
                    self.onLog?("📥 [unknown message]")
                }
            }
            // loop
            if self.isOpen { self.receiveLoop() }
        }
    }
    
    private func receiveLoopWithRetry(baseURL: String, meetingId: String, source: String, jwtToken: String, handshake: Handshake) {
        task?.receive { [weak self] result in
            guard let self else { return }
            switch result {
            case .failure(let err):
                let nsErr = err as NSError
                self.onError?("WebSocket receive error: \(err.localizedDescription)")
                self.onLog?("[WS] Error code: \(nsErr.code), domain: \(nsErr.domain)")
                
                // Check for specific errors that should trigger retry
                if nsErr.code == -1011 { // NSURLErrorBadServerResponse
                    self.onLog?("[WS] Bad server response (-1011) - will retry with fixed URL scheme")
                    self.scheduleRetry(baseURL: baseURL, meetingId: meetingId, source: source, jwtToken: jwtToken, handshake: handshake)
                    return
                }
                
                // Connection refused, network error, etc.
                if nsErr.code == -1004 || nsErr.code == 61 { // Connection refused
                    self.onLog?("[WS] Connection refused - will retry")
                    self.scheduleRetry(baseURL: baseURL, meetingId: meetingId, source: source, jwtToken: jwtToken, handshake: handshake)
                    return
                }
                
            case .success(let msg):
                switch msg {
                case .string(let s):
                    self.onLog?("📥 [text] \(s.prefix(140))")
                case .data(let d):
                    self.onLog?("📥 [\(d.count) bytes]")
                @unknown default:
                    self.onLog?("📥 [unknown message]")
                }
            }
            
            // Continue receive loop
            if self.isOpen { 
                self.receiveLoopWithRetry(baseURL: baseURL, meetingId: meetingId, source: source, jwtToken: jwtToken, handshake: handshake)
            }
        }
    }
}