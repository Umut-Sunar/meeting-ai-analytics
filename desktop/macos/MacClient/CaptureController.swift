import Foundation
import Combine

final class CaptureController: ObservableObject {
    private var cancellables = Set<AnyCancellable>()
    private var audioEngine: AudioEngine?

    func start(appState: AppState) {
        appState.log("🚀 Start requested")

        // 1) İzin kontrolü
        guard appState.isMicAuthorized else {
            appState.log("❌ Başlatılamadı: Mikrofon izni yok.")
            return
        }

        // 2) API Key kontrolü
        if !APIKeyManager.hasValidAPIKey() {
            appState.log("❌ Başlatılamadı: DEEPGRAM_API_KEY eksik.")
            return
        }

        // 3) AudioEngine oluştur
        let config = makeDGConfig()
        audioEngine = AudioEngine(config: config)
        
        // 4) Event handler'ı ayarla
        audioEngine?.onEvent = { [weak self] event in
            self?.handleAudioEngineEvent(event, appState: appState)
        }

        // 5) Başlat
        audioEngine?.start()
        appState.isCapturing = true
        appState.log("✅ Capture started.")
    }

    func stop(appState: AppState) {
        appState.log("🛑 Stop requested")
        audioEngine?.stop()
        appState.isCapturing = false
        appState.log("✅ Capture stopped.")
    }

    // MARK: - AudioEngine Event Handling
    private func handleAudioEngineEvent(_ event: AudioEngineEvent, appState: AppState) {
        DispatchQueue.main.async {
            switch event {
            case .microphoneConnected:
                appState.log("🎤 Mikrofon Deepgram'e bağlandı.")
            case .systemAudioConnected:
                appState.log("🔊 Sistem sesi Deepgram'e bağlandı.")
            case .microphoneDisconnected:
                appState.log("🎤 Mikrofon Deepgram bağlantısı kesildi.")
            case .systemAudioDisconnected:
                appState.log("🔊 Sistem sesi Deepgram bağlantısı kesildi.")
            case .error(let error, let source):
                appState.log("❌ \(source.debugId) Hatası: \(error.localizedDescription)")
            case .results(let json, let source):
                self.parseDeepgramResults(json, source: source, appState: appState)
            case .metadata(let json, let source):
                appState.log("ℹ️ \(source.debugId) Metadata: \(json.prefix(100))...")
            case .finalized(let json, let source):
                appState.log("✅ \(source.debugId) Finalize: \(json.prefix(100))...")
                self.parseDeepgramResults(json, source: source, appState: appState, isFinal: true)
            }
        }
    }

    private func parseDeepgramResults(_ jsonString: String, source: AudioSourceType, appState: AppState, isFinal: Bool = false) {
        do {
            guard let jsonData = jsonString.data(using: .utf8) else {
                appState.log("❌ JSON data conversion failed.")
                return
            }
            let json = try JSONSerialization.jsonObject(with: jsonData, options: []) as? [String: Any]

            guard let results = json?["channel"] as? [String: Any],
                  let alternatives = results["alternatives"] as? [[String: Any]],
                  let firstAlternative = alternatives.first,
                  let transcript = firstAlternative["transcript"] as? String,
                  !transcript.isEmpty else {
                return
            }

            let speaker = (source == .microphone) ? "You" : "Them"
            appState.log("📝 \(isFinal ? "Final" : "Partial") (\(source.debugId)): \(transcript)")

            // Add to transcript items if final
            if isFinal {
                let transcriptItem = TranscriptItem(
                    speaker: speaker,
                    text: transcript,
                    translation: nil,
                    isYou: source == .microphone
                )
                appState.addTranscript(transcriptItem)
            }
        } catch {
            appState.log("❌ JSON parse error: \(error.localizedDescription)")
        }
    }
}
