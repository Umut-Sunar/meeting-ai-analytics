import Foundation

/// Coordinates audio capture and routes PCM data to backend WebSocket
final class CaptureController: ObservableObject {
    
    // MARK: - Properties
    
    private var audioEngine: AudioEngine?
    
    // 🔵 İki ayrı WebSocket - Mic ve System için
    private let wsMic = BackendIngestWS()
    private let wsSys = BackendIngestWS()
    
    // 🚨 ECHO CANCELLATION: Simple energy-based suppression
    private var systemAudioLevel: Float = 0.0
    private var micAudioLevel: Float = 0.0
    private let echoThreshold: Float = 0.3  // If system audio is 30% of mic level, suppress mic
    private let energyDecayFactor: Float = 0.9  // Decay factor for audio level tracking
    private var lastSystemAudioTime: Date = Date()
    private var lastMicAudioTime: Date = Date()
    private let echoDelayWindow: TimeInterval = 0.1  // 100ms window for echo detection
    
    // MARK: - Echo Cancellation Helpers
    
    /// Calculate RMS energy of PCM data for echo detection
    private func calculateAudioEnergy(data: Data) -> Float {
        guard data.count >= 2 else { return 0.0 }
        
        let samples = data.withUnsafeBytes { bytes in
            Array(bytes.bindMemory(to: Int16.self))
        }
        
        let sumSquares = samples.reduce(Float(0.0)) { sum, sample in
            let normalized = Float(sample) / Float(Int16.max)
            return sum + normalized * normalized
        }
        
        let rms = sqrtf(sumSquares / Float(samples.count))
        return rms
    }
    
    /// Apply volume suppression to PCM data
    private func applySuppression(data: Data, factor: Float) -> Data {
        var suppressedData = Data(capacity: data.count)
        
        data.withUnsafeBytes { bytes in
            let samples = bytes.bindMemory(to: Int16.self)
            for sample in samples {
                let suppressedSample = Int16(Float(sample) * factor)
                suppressedData.append(contentsOf: withUnsafeBytes(of: suppressedSample.littleEndian) { Array($0) })
            }
        }
        
        return suppressedData
    }
    
    // MARK: - Public Methods
    
    @MainActor
    func start(appState: AppState) {
        guard !appState.isCapturing else { return }
        
        Task {
            await startAsync(appState: appState)
        }
    }
    
    @MainActor
    private func startAsync(appState: AppState) async {
        // Validasyon
        guard !appState.meetingId.isEmpty,
              !appState.deviceId.isEmpty,
              !appState.backendURLString.isEmpty else {
            appState.log("❌ Meeting/Device/Backend boş olamaz")
            return
        }
        
        // JWT
        if appState.jwtToken.isEmpty {
            let loadedToken = KeychainStore.loadJWT()
            appState.jwtToken = loadedToken
        }
        
        appState.log("🚀 Starting capture with backend WebSocket...")
        
        // SYSTEM WebSocket için asenkron permission check
        if appState.captureSystem {
            let hasPermission = await PermissionsService.hasScreenRecordingPermission()
            guard hasPermission else {
                appState.log("❌ Screen Recording izni yok. Ayarlar açılıyor...")
                PermissionsService.openScreenRecordingPrefs()
                return
            }
        }
        
        // PCM bridge kurulmadan önce AudioEngine
        let config = DGConfig(
            apiKey: "dummy", // Backend kullandığımız için dummy (not used in backend mode)
            sampleRate: 16000,  // 🚨 FIXED: Standardized to 16kHz
            channels: 1,
            language: appState.language
        )
        
        // Backend-only mode: Deepgram clients disabled
        audioEngine = AudioEngine(config: config, transportMode: .backendWS)
        
        // 🔌 PCM Bridge: MIC (with echo cancellation)
        audioEngine?.onMicPCM = { [weak self] data in
            guard let self = self else { return }
            
            // Calculate mic audio energy
            let micEnergy = self.calculateAudioEnergy(data: data)
            self.micAudioLevel = self.micAudioLevel * self.energyDecayFactor + micEnergy * (1 - self.energyDecayFactor)
            self.lastMicAudioTime = Date()
            
            // Echo suppression: if system audio is active and recent, reduce mic sensitivity
            let timeSinceSystemAudio = Date().timeIntervalSince(self.lastSystemAudioTime)
            let shouldSuppressMic = timeSinceSystemAudio < self.echoDelayWindow && 
                                   self.systemAudioLevel > self.echoThreshold && 
                                   micEnergy < self.systemAudioLevel * 2.0  // Only suppress if mic isn't significantly louder
            
            if shouldSuppressMic {
                // Apply suppression by reducing volume or skipping transmission
                let suppressedData = self.applySuppression(data: data, factor: 0.3)  // 70% reduction
                self.wsMic.sendPCM(suppressedData, source: "mic")
                print("[DEBUG] 🔇 Echo suppression applied to mic audio (system level: \(String(format: "%.2f", self.systemAudioLevel)), mic level: \(String(format: "%.2f", micEnergy)))")
            } else {
                self.wsMic.sendPCM(data, source: "mic")
            }
        }
        
        // 🔌 PCM Bridge: SYSTEM (with energy tracking)
        audioEngine?.onSystemPCM = { [weak self] data in
            guard let self = self else { return }
            
            // Calculate system audio energy for echo detection
            let systemEnergy = self.calculateAudioEnergy(data: data)
            self.systemAudioLevel = self.systemAudioLevel * self.energyDecayFactor + systemEnergy * (1 - self.energyDecayFactor)
            self.lastSystemAudioTime = Date()
            
            self.wsSys.sendPCM(data, source: "system")
        }
        
        // WebSocket callbacks (enhanced logging)
        setupWebSocketCallbacks(for: wsMic, appState: appState, source: "MIC")
        setupWebSocketCallbacks(for: wsSys, appState: appState, source: "SYS")
        
        // MIC WebSocket (isteğe bağlı)
        if appState.captureMic {
            let hs = BackendIngestWS.Handshake(
                source: "mic",
                sample_rate: 16000,  // 🚨 FIXED: Standardized to 16kHz
                channels: 1,
                language: appState.language,
                ai_mode: appState.aiMode,
                device_id: appState.deviceId + "-mic"
            )
            wsMic.open(
                baseURL: appState.backendURLString,
                meetingId: appState.meetingId,
                source: "mic",
                jwtToken: appState.jwtToken,
                handshake: hs
            )
        }
        
        // SYSTEM WebSocket (isteğe bağlı) - Permission check zaten yukarıda yapıldı
        if appState.captureSystem {
            let hs = BackendIngestWS.Handshake(
                source: "system",
                sample_rate: 16000,  // 🚨 FIXED: Standardized to 16kHz
                channels: 1,
                language: appState.language,
                ai_mode: appState.aiMode,
                device_id: appState.deviceId + "-sys"
            )
            wsSys.open(
                baseURL: appState.backendURLString,
                meetingId: appState.meetingId,
                source: "sys",
                jwtToken: appState.jwtToken,
                handshake: hs
            )
        }
        
        // AudioEngine event handling
                audioEngine?.onEvent = { [weak appState] event in
            Task { @MainActor in
                switch event {
                case .microphoneConnected:
                    appState?.log("🎤 Microphone connected")
                case .systemAudioConnected:
                    appState?.log("🔊 System audio connected")
                case .microphoneDisconnected:
                    appState?.log("🎤 Microphone disconnected")
                case .systemAudioDisconnected:
                    appState?.log("🔊 System audio disconnected")
                case .error(let error, let source):
                    appState?.log("❌ Audio Error (\(source.debugId)): \(error.localizedDescription)")
                default:
                    break // Ignore transcript events since we're using backend WS
                }
            }
        }
        
        // TASK 3: Setup device change handling
        audioEngine?.onDeviceChange = { [weak appState] in
            Task { @MainActor in
                appState?.log("🎧 Audio device changed — streams auto-restarted")
            }
        }
        
        // TASK 8: Setup metric handling
        audioEngine?.onMetric = { [weak appState] name, value, tags in
            Task { @MainActor in
                let tagsStr = tags.map { "\($0.key)=\($0.value)" }.joined(separator: ", ")
                appState?.log("📊 Metric: \(name)=\(Int(value)) [\(tagsStr)]")
            }
        }
        
        // Start AudioEngine
        audioEngine?.start()
        
        appState.isCapturing = true
        appState.log("✅ Audio capture started (Backend WS mode, mic:\(appState.captureMic), sys:\(appState.captureSystem))")
    }
    
    @MainActor
    func stop(appState: AppState) {
        guard appState.isCapturing else { return }
        
        Task {
            appState.log("🛑 Stopping capture...")
            
            // Stop audio engine first
            audioEngine?.stop()
            audioEngine = nil
            
            // Close WebSockets with finalize
            wsMic.close(sendFinalize: true)
            wsSys.close(sendFinalize: true)
            
            appState.isCapturing = false
            appState.log("✅ Capture stopped")
        }
    }
    
    // MARK: - Private Helpers
    
    private func setupWebSocketCallbacks(for ws: BackendIngestWS, appState: AppState, source: String) {
        ws.onLog = { [weak appState] message in
            Task { @MainActor in
                appState?.log("[\(source)] \(message)")
            }
        }
        
        ws.onError = { [weak appState] error in
            Task { @MainActor in
                appState?.log("❌ [\(source)] WS Error: \(error)")
                
                // 🚨 FIXED: Handle specific connection errors
                if error.contains("Connection refused") {
                    appState?.log("⚠️ [\(source)] Backend server not running on port 8000")
                } else if error.contains("Redis not connected") {
                    appState?.log("⚠️ [\(source)] Redis service not available - transcript streaming disabled")
                } else if error.contains("Socket is not connected") {
                    appState?.log("⚠️ [\(source)] Network connection lost - will retry")
                }
            }
        }
        
        ws.onConnected = { [weak appState] in
            Task { @MainActor in
                appState?.log("✅ [\(source)] WebSocket connected successfully")
            }
        }
        
        ws.onDisconnected = { [weak appState] in
            Task { @MainActor in
                appState?.log("🔌 [\(source)] WebSocket disconnected - check backend server")
            }
        }
    }
}