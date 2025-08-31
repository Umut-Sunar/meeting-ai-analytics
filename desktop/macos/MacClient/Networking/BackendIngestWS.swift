import Foundation

/// Backend Ingest WebSocket client with proper handshake protocol
/// Features: State machine, handshake-first protocol, guarded send, exponential backoff reconnect
final class BackendIngestWS {
    
    // MARK: - State Machine
    
    enum WSState {
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
    
    // MARK: - Properties
    
    private var state: WSState = .idle {
        didSet {
            onLog?("[WS] State: \(oldValue.description) → \(state.description)")
        }
    }
    
    private var task: URLSessionWebSocketTask?
    private var isReady = false // becomes true after 'handshake-ack'
    private var handshakeTimer: DispatchSourceTimer?
    private var reconnectAttempts = 0
    private var pendingPCM = [Data]() // optional short ring-buffer ≤500ms
    
    private let session: URLSession = {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30
        config.timeoutIntervalForResource = 60
        return URLSession(configuration: config)
    }()
    
    // Keep-alive
    private var keepAliveTimer: Timer?
    private let keepAliveInterval: TimeInterval = 30.0
    
    // Connection parameters for reconnection
    private var connectionParams: (url: URL, meetingId: String, source: String)?
    
    // Callbacks
    var onLog: ((String) -> Void)?
    var onError: ((String) -> Void)?
    var onConnected: (() -> Void)?
    var onDisconnected: (() -> Void)?
    
    // MARK: - Public API
    
    var isConnected: Bool {
        return state == .connected && isReady
    }

    
    func connect(url: URL, meetingId: String, source: String) {
        onLog?("[WS] Connect requested for meeting: \(meetingId), source: \(source)")
        
        // If already connecting/connected, gracefully close old connection first
        if state == .connecting || state == .connected {
            onLog?("[WS] Closing existing connection before new connect")
            closeInternal(code: .goingAway, reason: "new connection")
        }
        
        // Store connection params for reconnection
        connectionParams = (url, meetingId, source)
        
        // Clear state for new connection
        pendingPCM.removeAll()
        isReady = false
        reconnectAttempts = 0
        
        // Start connecting
        state = .connecting
        task = session.webSocketTask(with: url)
        task?.resume()
        
        onLog?("[WS] WebSocket task started for: \(url.absoluteString)")
        
        // Immediately send handshake (bypass isReady guard)
        sendHandshake(meetingId: meetingId, source: source)
        
        // Start receive loop
        startReceiveLoop()
        
        // Start handshake timeout timer (5 seconds)
        startHandshakeTimer()
    }
    
    func sendPCM(_ data: Data, source: String) {
        // Guard: must be connected AND ready (after handshake-ack)
        guard state == .connected && isReady && task != nil else {
            // Buffer PCM data if we have space (≤500ms)
            if pendingPCM.count < 50 { // rough limit for 500ms at 16kHz
                pendingPCM.append(data)
            }
            return
        }
        
        // Send PCM as binary frame
        task?.send(.data(data)) { [weak self] error in
            if let error = error {
                self?.onError?("[WS] PCM send error: \(error)")
                self?.handleConnectionError()
            }
        }
    }
    
    func pause() {
        onLog?("[WS] Paused - stopping PCM feed (no finalize, no close)")
        // Just stop feeding PCM - do NOT call finalize, do NOT close WS
        // The connection stays alive for when resume() is called
    }
    
    func resume() {
        onLog?("[WS] Resumed - continuing PCM feed")
        // Continue normally - if reconnect occurred meanwhile, handshake will happen
        // No special action needed here
    }
    
    func stop() {
        onLog?("[WS] Stop requested")
        
        if state == .connected {
            // Send finalize message before closing
            let finalizeMsg = ["type": "finalize"]
            sendRaw(finalizeMsg)
        }
        
        closeInternal(code: .goingAway, reason: "stop")
    }
    
    // MARK: - Private Methods
    
    private func sendRaw(_ message: [String: Any]) {
        // Guard ONLY state and task - DO NOT check isReady
        guard state == .connected && task != nil else {
            onLog?("[WS] Cannot send raw message - not connected or no task")
            return
        }
        
        do {
            let data = try JSONSerialization.data(withJSONObject: message)
            task?.send(.string(String(data: data, encoding: .utf8) ?? "{}")) { [weak self] error in
                if let error = error {
                    self?.onError?("[WS] Raw message send error: \(error)")
                    self?.handleConnectionError()
                }
            }
        } catch {
            onError?("[WS] Failed to serialize message: \(error)")
        }
    }
    
    private func sendHandshake(meetingId: String, source: String) {
        onLog?("[WS] Sending handshake for meeting: \(meetingId), source: \(source)")
        
        let deviceId = "macclient-\(source)-\(UUID().uuidString.prefix(8))"
        let handshakeMsg: [String: Any] = [
            "type": "handshake",
            "meeting_id": meetingId,
            "device_id": deviceId,
            "source": source == "system" ? "sys" : source, // normalize system -> sys
            "codec": "pcm_s16le",
            "sample_rate": 16000,
            "channels": 1,
            "client": "macclient",
            "version": "1.0.0" // AppVersion.string if available
        ]
        
        sendRaw(handshakeMsg)
    }

    
    private func startReceiveLoop() {
        guard let task = task else { return }
        
        task.receive { [weak self] result in
            guard let self = self else { return }
            
            switch result {
            case .success(let message):
                self.handleMessage(message)
                // Continue receiving
                if self.state == .connected || self.state == .connecting {
                    self.startReceiveLoop()
                }
                
            case .failure(let error):
                self.onError?("[WS] Receive error: \(error)")
                self.handleConnectionError()
            }
        }
    }
    
    private func handleMessage(_ message: URLSessionWebSocketTask.Message) {
        switch message {
        case .string(let text):
            handleTextMessage(text)
        case .data(let data):
            onLog?("[WS] Received binary data: \(data.count) bytes")
        @unknown default:
            onLog?("[WS] Received unknown message type")
        }
    }
    
    private func handleTextMessage(_ text: String) {
        guard let data = text.data(using: .utf8),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let type = json["type"] as? String else {
            onLog?("[WS] Invalid JSON message: \(text)")
            return
        }
        
        onLog?("[WS] Received message type: \(type)")
        
        switch type {
        case "handshake-ack":
            handleHandshakeAck(json)
        case "ping":
            handlePing()
        default:
            onLog?("[WS] Unhandled message type: \(type)")
        }
    }
    
    private func handleHandshakeAck(_ json: [String: Any]) {
        guard let ok = json["ok"] as? Bool, ok == true else {
            onError?("[WS] Handshake failed: \(json)")
            handleConnectionError()
            return
        }
        
        onLog?("[WS] Handshake acknowledged - connection ready!")
        
        // Set ready state
        isReady = true
        state = .connected
        
        // Cancel handshake timer
        cancelHandshakeTimer()
        
        // Start keep-alive
        startKeepAlive()
        
        // Flush pending PCM
        flushPendingPCM()
        
        // Notify connection success
        onConnected?()
    }
    
    private func handlePing() {
        onLog?("[WS] Received ping, sending pong")
        let pongMsg = ["type": "pong"]
        sendRaw(pongMsg)
    }
    
    private func startHandshakeTimer() {
        cancelHandshakeTimer()
        
        handshakeTimer = DispatchSource.makeTimerSource(queue: .main)
        handshakeTimer?.schedule(deadline: .now() + 5.0) // 5 second timeout
        handshakeTimer?.setEventHandler { [weak self] in
            self?.onError?("[WS] Handshake timeout - no ack received")
            self?.handleConnectionError()
        }
        handshakeTimer?.resume()
        
        onLog?("[WS] Handshake timer started (5s timeout)")
    }
    
    private func cancelHandshakeTimer() {
        handshakeTimer?.cancel()
        handshakeTimer = nil
    }
    
    private func startKeepAlive() {
        stopKeepAlive()
        
        keepAliveTimer = Timer.scheduledTimer(withTimeInterval: keepAliveInterval, repeats: true) { [weak self] _ in
            guard let self = self, self.state == .connected else { return }
            
            let pingMsg = ["type": "ping"]
            self.sendRaw(pingMsg)
        }
        
        onLog?("[WS] Keep-alive started (\(keepAliveInterval)s interval)")
    }
    
    private func stopKeepAlive() {
        keepAliveTimer?.invalidate()
        keepAliveTimer = nil
    }
    
    private func flushPendingPCM() {
        guard !pendingPCM.isEmpty else { return }
        
        onLog?("[WS] Flushing \(pendingPCM.count) pending PCM chunks")
        
        for data in pendingPCM {
            task?.send(.data(data)) { [weak self] error in
                if let error = error {
                    self?.onError?("[WS] Pending PCM send error: \(error)")
                }
            }
        }
        
        pendingPCM.removeAll()
    }
    
    private func handleConnectionError() {
        onLog?("[WS] Handling connection error")
        
        // Clean up current connection
        closeInternal(code: .protocolError, reason: "error")
        
        // Schedule reconnect with exponential backoff
        scheduleReconnect()
    }
    
    private func scheduleReconnect() {
        guard let params = connectionParams else {
            onLog?("[WS] No connection params for reconnect")
            return
        }
        
        reconnectAttempts += 1
        let maxAttempts = 5
        
        if reconnectAttempts > maxAttempts {
            onError?("[WS] Max reconnect attempts (\(maxAttempts)) reached")
            return
        }
        
        // Exponential backoff: 1s, 2s, 5s, 10s, 30s with jitter
        let baseDelays: [TimeInterval] = [1.0, 2.0, 5.0, 10.0, 30.0]
        let delayIndex = min(reconnectAttempts - 1, baseDelays.count - 1)
        let baseDelay = baseDelays[delayIndex]
        let jitter = Double.random(in: 0.8...1.2) // ±20% jitter
        let delay = baseDelay * jitter
        
        onLog?("[WS] Scheduling reconnect attempt \(reconnectAttempts)/\(maxAttempts) in \(String(format: "%.1f", delay))s")
        
        DispatchQueue.main.asyncAfter(deadline: .now() + delay) { [weak self] in
            guard let self = self else { return }
            self.connect(url: params.url, meetingId: params.meetingId, source: params.source)
        }
    }
    
    private func closeInternal(code: URLSessionWebSocketTask.CloseCode, reason: String) {
        // Ensure single close
        guard state != .closing && state != .disconnected else { return }
        
        onLog?("[WS] Closing connection: \(reason)")
        
        state = .closing
        
        // Clean up timers
        cancelHandshakeTimer()
        stopKeepAlive()
        
        // Close WebSocket
        task?.cancel(with: code, reason: reason.data(using: .utf8))
        task = nil
        
        // Update state
        state = .disconnected
        isReady = false
        
        // Clear pending data
        pendingPCM.removeAll()
        
        // Notify disconnection
        onDisconnected?()
    }
    
    deinit {
        onLog?("[WS] BackendIngestWS deinit")
        stop()
    }
}