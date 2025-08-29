import Foundation

/// Coordinates audio capture and routes PCM data to backend WebSocket
final class CaptureController: ObservableObject {
    
    // MARK: - Properties
    
    private var audioEngine: AudioEngine?
    
    // 🔵 İki ayrı WebSocket - Mic ve System için
    private let wsMic = BackendIngestWS()
    private let wsSys = BackendIngestWS()
    
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
            sampleRate: 48000,
            channels: 1,
            language: appState.language
        )
        
        // Backend-only mode: Deepgram clients disabled
        audioEngine = AudioEngine(config: config, transportMode: .backendWS)
        
        // 🔌 PCM Bridge: MIC
        audioEngine?.onMicPCM = { [weak self] data in
            self?.wsMic.sendPCM(data)
        }
        
        // 🔌 PCM Bridge: SYSTEM
        audioEngine?.onSystemPCM = { [weak self] data in
            self?.wsSys.sendPCM(data)
        }
        
        // WebSocket callbacks (enhanced logging)
        setupWebSocketCallbacks(for: wsMic, appState: appState, source: "MIC")
        setupWebSocketCallbacks(for: wsSys, appState: appState, source: "SYS")
        
        // MIC WebSocket (isteğe bağlı)
        if appState.captureMic {
            let hs = BackendIngestWS.Handshake(
                source: "mic",
                sample_rate: 48000,
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
                sample_rate: 48000,
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
            }
        }
        
        ws.onConnected = { [weak appState] in
            Task { @MainActor in
                appState?.log("✅ [\(source)] WebSocket connected")
            }
        }
        
        ws.onDisconnected = { [weak appState] in
            Task { @MainActor in
                appState?.log("🔌 [\(source)] WebSocket disconnected")
            }
        }
    }
}