import AVFoundation
import CoreAudio

/// Events from AudioEngine to UI
enum AudioEngineEvent {
    case microphoneConnected
    case systemAudioConnected
    case microphoneDisconnected
    case systemAudioDisconnected
    case error(Error, source: AudioSourceType)
    case results(String, source: AudioSourceType) // JSON transcript results
    case metadata(String, source: AudioSourceType) // JSON metadata
    case finalized(String, source: AudioSourceType) // JSON from finalize command
}

/// Audio transport modes
enum AudioTransportMode {
    case backendWS    // Route PCM to backend WebSocket (default)
    case deepgram     // Direct Deepgram connection (legacy)
}

/// Coordinates audio capture from multiple sources and processing pipeline
/// Supports both backend WebSocket routing and direct Deepgram connections
class AudioEngine {
    
    // MARK: - Properties
    
    private var microphoneClient: DeepgramClient?
    private var systemAudioClient: DeepgramClient?
    private let micCapture: MicCapture
    private let systemAudioCapture: SystemAudioCaptureSC

    private var isRunning = false
    private var currentConfig: DGConfig?
    
    // Transport mode - controls whether to use backend WS or direct Deepgram
    private let transportMode: AudioTransportMode
    
    // Event callback for UI updates
    var onEvent: ((AudioEngineEvent) -> Void)?
    
    // PCM callbacks for backend routing
    var onMicPCM: ((Data) -> Void)?
    var onSystemPCM: ((Data) -> Void)?
    
    // MARK: - Initialization
    
    init(config: DGConfig, transportMode: AudioTransportMode = .backendWS) {
        print("[DEBUG] AudioEngine initialized with config, transport: \(transportMode)")
        
        self.currentConfig = config
        self.transportMode = transportMode
        
        // Initialize audio capture components
        self.micCapture = MicCapture()
        self.systemAudioCapture = SystemAudioCaptureSC()
        
        // Only create Deepgram clients in direct mode
        if transportMode == .deepgram {
            createDeepgramClients(with: config)
            setupDeepgramEvents()
            print("[DEBUG] ✅ Deepgram clients created (direct mode)")
        } else {
            print("[DEBUG] ✅ Backend WebSocket mode - Deepgram clients disabled")
        }
    }
    

    
    deinit {
        print("[DEBUG] 🔧 AudioEngine deinitializing...")
        
        // Stop all streams safely
        if isRunning {
            stop()
        }
        
        // Clean up references
        onEvent = nil
        microphoneClient = nil
        systemAudioClient = nil
        currentConfig = nil
        
        print("[DEBUG] 🔧 AudioEngine deinitialized safely")
    }
    
    /// Update configuration when language changes
    func updateConfiguration(with newConfig: DGConfig) {
        // Check if configuration actually changed
        let configChanged = currentConfig == nil || 
                          currentConfig?.model != newConfig.model ||
                          currentConfig?.language != newConfig.language
        
        if configChanged {
            print("[DEBUG] 🔄 Configuration changed - updating Deepgram clients")
            print("[DEBUG] 🔄 New model: \(newConfig.model), language: \(newConfig.language)")
            
            self.currentConfig = newConfig
            
            // Recreate Deepgram clients with new config
            createDeepgramClients(with: newConfig)
            
            // If currently running, restart with new config
            if isRunning {
                print("[DEBUG] 🔄 Audio engine running - restarting with new language config")
                restartWithNewLanguage()
            }
        } else {
            print("[DEBUG] ✅ Configuration unchanged - no update needed")
        }
    }
    
    /// Create Deepgram clients with given configuration (only in .deepgram mode)
    private func createDeepgramClients(with config: DGConfig) {
        guard transportMode == .deepgram else {
            print("[DEBUG] ⚠️ Skipping Deepgram client creation - backend WebSocket mode")
            return
        }
        
        // Clean up existing clients
        microphoneClient?.closeSocket()
        systemAudioClient?.closeSocket()
        
        // Create separate configs for each source
        let micConfig = config.withSource(.microphone)
        let sysConfig = config.withSource(.systemAudio)
        
        // Initialize dual Deepgram clients
        self.microphoneClient = DeepgramClient(config: micConfig, sourceType: .microphone)
        self.systemAudioClient = DeepgramClient(config: sysConfig, sourceType: .systemAudio)
        
        setupDeepgramEvents()
        
        print("[DEBUG] ✅ Deepgram clients created with language: \(config.language), model: \(config.model)")
    }
    
    /// Restart audio engine with new language configuration
    private func restartWithNewLanguage() {
        print("[DEBUG] 🔄 Restarting audio engine for language change...")
        
        // Stop current streams
        stop()
        
        // Short delay to ensure clean shutdown
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) { [weak self] in
            // Restart with new configuration
            self?.start()
            print("[DEBUG] ✅ Audio engine restarted with new language configuration")
        }
    }
    
    // MARK: - Public API
    
    /// Start audio capture and dual Deepgram connections
    func start() {
        print("[DEBUG] 🚀 AudioEngine.start() called - Dual WebSocket mode")
        
        guard !isRunning else {
            print("[DEBUG] ⚠️ AudioEngine already running")
            return
        }
        
        guard let config = currentConfig else {
            print("[DEBUG] ❌ Cannot start AudioEngine: No valid configuration")
            onEvent?(.error(NSError(domain: "AudioEngine", code: -1, userInfo: [NSLocalizedDescriptionKey: "No valid configuration available"]), source: .microphone))
            return
        }
        
        // Check API key only for direct Deepgram mode
        if transportMode == .deepgram && !APIKeyManager.hasValidAPIKey() {
            print("[DEBUG] ❌ Cannot start AudioEngine: API key missing for Deepgram mode")
            let status = APIKeyManager.getAPIKeyStatus()
            print("[DEBUG] 🔍 API Key Status: source=\(status.source), key=\(status.maskedKey)")
            onEvent?(.error(NSError(domain: "AudioEngine", code: -1, userInfo: [NSLocalizedDescriptionKey: "DEEPGRAM_API_KEY is missing"]), source: .microphone))
            return
        } else if transportMode == .backendWS {
            print("[DEBUG] ✅ Backend WebSocket mode - skipping Deepgram API key check")
        }
        
        // Ensure clients exist (only for Deepgram mode)
        if transportMode == .deepgram && (microphoneClient == nil || systemAudioClient == nil) {
            print("[DEBUG] 🔄 Deepgram clients not initialized, creating them")
            createDeepgramClients(with: config)
        }
        
        print("[DEBUG] 🌍 Starting with language: \(config.language), model: \(config.model)")
        isRunning = true
        
        // Start both streams independently with error handling
        do {
            startMicrophoneStream()
            startSystemAudioStream()
            print("[DEBUG] ✅ AudioEngine dual stream initialization completed")
        } catch {
            print("[DEBUG] ❌ Error starting audio streams: \(error)")
            isRunning = false
            onEvent?(.error(error as NSError, source: .microphone))
        }
    }
    
    /// Start microphone stream
    private func startMicrophoneStream() {
        print("[DEBUG] 🎤 Starting microphone stream (transport: \(transportMode))...")
        
        // Connect to Deepgram only in direct mode
        if transportMode == .deepgram {
            guard let micClient = microphoneClient else {
                print("[DEBUG] ❌ Microphone client not available")
                return
            }
            
            // Connect microphone client to Deepgram
            micClient.connect { [weak self] event in
                self?.handleMicrophoneEvent(event)
            }
        }
        
        // Start microphone capture
        micCapture.start { [weak self] pcmData in
            guard let self = self else { return }
            
            switch self.transportMode {
            case .backendWS:
                // Route to backend WebSocket via callback
                self.onMicPCM?(pcmData)
            case .deepgram:
                // Send directly to Deepgram
                self.microphoneClient?.sendPCM(pcmData)
            }
        }
    }
    
    /// Start system audio stream
    private func startSystemAudioStream() {
        print("[DEBUG] 🔊 Starting system audio stream (transport: \(transportMode))...")
        
        // Connect to Deepgram only in direct mode
        if transportMode == .deepgram {
            guard let sysClient = systemAudioClient else {
                print("[DEBUG] ❌ System audio client not available")
                return
            }
            
            // Connect system audio client to Deepgram
            sysClient.connect { [weak self] event in
                self?.handleSystemAudioEvent(event)
            }
        }
        
        // Start system audio capture with ScreenCaptureKit
        Task {
            if #available(macOS 13.0, *) {
                do {
                    // Set up callback before starting
                    systemAudioCapture.onPCM16k = { [weak self] pcmData in
                        guard let self = self else { return }
                        
                        switch self.transportMode {
                        case .backendWS:
                            // Route to backend WebSocket via callback
                            self.onSystemPCM?(pcmData)
                        case .deepgram:
                            // Send directly to Deepgram
                            self.systemAudioClient?.sendPCM(pcmData)
                        }
                    }
                    
                    print("[DEBUG] 🔧 SystemAudioCapture callback set")
                    print("[DEBUG] 🎧 Automatic audio device change detection is built-in to SystemAudioCapture")
                    
                    try await systemAudioCapture.start()
                    print("[DEBUG] ✅ System audio capture started successfully")
                    print("[DEBUG] 🎧 System will automatically restart when audio output device changes (e.g., AirPods)")
                    
                } catch {
                    print("[DEBUG] ❌ Failed to start system audio capture: \(error)")
                    print("[DEBUG] 🔍 Error type: \(type(of: error))")
                    print("[DEBUG] 🔍 Error description: \(error.localizedDescription)")
                    
                    if let nsError = error as NSError? {
                        print("[DEBUG] 🔍 Error domain: \(nsError.domain)")
                        print("[DEBUG] 🔍 Error code: \(nsError.code)")
                        print("[DEBUG] 🔍 Error userInfo: \(nsError.userInfo)")
                    }
                    // Continue with microphone-only mode
                }
            } else {
                print("[DEBUG] ⚠️ ScreenCaptureKit requires macOS 13.0+")
            }
        }
    }
    
    /// Stop audio capture and close dual connections
    func stop() {
        print("[DEBUG] 🛑 AudioEngine.stop() called - Dual WebSocket mode")
        
        guard isRunning else {
            print("[DEBUG] ⚠️ AudioEngine already stopped")
            return
        }
        
        isRunning = false
        
        // Stop microphone capture and connection - safely
        print("[DEBUG] 🎤 Stopping microphone stream...")
        do {
            micCapture.stop()
            microphoneClient?.closeSocket()
            print("[DEBUG] ✅ Microphone stream stopped")
        } catch {
            print("[DEBUG] ⚠️ Error stopping microphone: \(error)")
        }
        
        // Stop system audio capture and connection - safely
        if #available(macOS 13.0, *) {
            print("[DEBUG] 🔊 Stopping system audio stream...")
            Task { @MainActor in
                do {
                    await systemAudioCapture.stop()
                    systemAudioClient?.closeSocket()
                    print("[DEBUG] ✅ System audio stream stopped")
                } catch {
                    print("[DEBUG] ⚠️ Error stopping system audio: \(error)")
                }
            }
        }
        
        print("[DEBUG] ✅ AudioEngine dual streams stopped successfully")
    }
    
    // MARK: - Private Methods
    
    private func setupDeepgramEvents() {
        // Dual stream event handling is configured in startMicrophoneStream() and startSystemAudioStream()
        print("[DEBUG] AudioEngine dual stream event handling configured")
    }
    
    /// Handle microphone Deepgram events
    private func handleMicrophoneEvent(_ event: DGEvent) {
        print("[DEBUG] AudioEngine received microphone event: \(event.description)")
        
        // Convert DGEvent to AudioEngineEvent and forward to UI
        switch event {
        case .connected(let source):
            onEvent?(.microphoneConnected)
            
        case .disconnected(let source):
            onEvent?(.microphoneDisconnected)
            
        case .error(let message, let source):
            let error = NSError(domain: "DeepgramError", code: -1, userInfo: [NSLocalizedDescriptionKey: message])
            onEvent?(.error(error, source: source))
            
        case .results(let json, let source):
            onEvent?(.results(json, source: source))
            
        case .metadata(let json, let source):
            onEvent?(.metadata(json, source: source))
            
        case .fromFinalize(let json, let source):
            onEvent?(.finalized(json, source: source))
        }
    }
    
    /// Handle system audio Deepgram events
    private func handleSystemAudioEvent(_ event: DGEvent) {
        print("[DEBUG] AudioEngine received system audio event: \(event.description)")
        
        // Convert DGEvent to AudioEngineEvent and forward to UI
        switch event {
        case .connected(let source):
            onEvent?(.systemAudioConnected)
            
        case .disconnected(let source):
            onEvent?(.systemAudioDisconnected)
            
        case .error(let message, let source):
            let error = NSError(domain: "DeepgramError", code: -1, userInfo: [NSLocalizedDescriptionKey: message])
            onEvent?(.error(error, source: source))
            
        case .results(let json, let source):
            onEvent?(.results(json, source: source))
            
        case .metadata(let json, let source):
            onEvent?(.metadata(json, source: source))
            
        case .fromFinalize(let json, let source):
            onEvent?(.finalized(json, source: source))
        }
    }
}

/// Legacy helper function - use LanguageManager.getDeepgramConfig() instead
@available(*, deprecated, message: "Use LanguageManager.getDeepgramConfig() instead")
func makeDGConfig() -> DGConfig {
    let apiKey = APIKeyManager.getDeepgramAPIKey()
    return DGConfig(
        apiKey: apiKey,
        sampleRate: 48000,  // Match successful project: 48kHz
        channels: 1,
        multichannel: false,
        model: "nova-2",    // Use nova-2 for Turkish support
        language: "tr",
        interim: true,
        endpointingMs: 300,
        punctuate: true,
        smartFormat: true,
        diarize: true       // Enable diarization like successful project
    )
}
