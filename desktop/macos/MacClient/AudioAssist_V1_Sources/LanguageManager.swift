import Foundation

/// Supported languages for transcription
enum SupportedLanguage: String, CaseIterable {
    case turkish = "tr"
    case english = "en"
    
    /// Display name for UI
    var displayName: String {
        switch self {
        case .turkish:
            return "Türkçe"
        case .english:
            return "English"
        }
    }
    
    /// Flag emoji for UI
    var flag: String {
        switch self {
        case .turkish:
            return "🇹🇷"
        case .english:
            return "🇺🇸"
        }
    }
    
    /// Deepgram language code
    var deepgramLanguageCode: String {
        return self.rawValue
    }
    
    /// Recommended Deepgram model based on language
    var recommendedModel: String {
        switch self {
        case .turkish:
            return "nova-2"  // Best for Turkish
        case .english:
            return "nova-3"  // Best for English
        }
    }
    
    /// Model options available for this language
    var availableModels: [String] {
        switch self {
        case .turkish:
            return ["nova-2"]  // Only nova-2 supports Turkish
        case .english:
            return [
                "nova-3",
                "nova-3-general", 
                "nova-3-medical",
                "nova-2",
                "nova-2-general",
                "nova-2-meeting",
                "nova-2-phonecall",
                "nova-2-finance",
                "nova-2-conversationalai",
                "nova-2-voicemail",
                "nova-2-video",
                "nova-2-medical",
                "nova-2-drivethru",
                "nova-2-automotive",
                "nova-2-atc"
            ]
        }
    }
}

/// Language preference manager
class LanguageManager: ObservableObject {
    @Published var selectedLanguage: SupportedLanguage {
        didSet {
            saveLanguagePreference()
            print("[LanguageManager] 🌍 Language changed to: \(selectedLanguage.displayName) (\(selectedLanguage.deepgramLanguageCode))")
            print("[LanguageManager] 🎯 Recommended model: \(selectedLanguage.recommendedModel)")
        }
    }
    
    private let userDefaultsKey = "AudioAssist_SelectedLanguage"
    
    init() {
        // Load saved language preference or default to Turkish
        if let savedLanguage = UserDefaults.standard.string(forKey: userDefaultsKey),
           let language = SupportedLanguage(rawValue: savedLanguage) {
            self.selectedLanguage = language
            print("[LanguageManager] 💾 Loaded saved language: \(language.displayName)")
        } else {
            self.selectedLanguage = .turkish  // Default to Turkish
            print("[LanguageManager] 🆕 No saved language, defaulting to Turkish")
        }
    }
    
    /// Save language preference to UserDefaults
    private func saveLanguagePreference() {
        UserDefaults.standard.set(selectedLanguage.rawValue, forKey: userDefaultsKey)
        print("[LanguageManager] 💾 Language preference saved: \(selectedLanguage.rawValue)")
    }
    
    /// Get Deepgram configuration for current language
    func getDeepgramConfig() -> DGConfig {
        let apiKey = APIKeyManager.getDeepgramAPIKey()
        let language = selectedLanguage
        
        let config = DGConfig(
            apiKey: apiKey,
            sampleRate: 48000,
            channels: 1,
            multichannel: false,
            model: language.recommendedModel,
            language: language.deepgramLanguageCode,
            interim: true,
            endpointingMs: 300,
            punctuate: true,
            smartFormat: true,
            diarize: true
        )
        
        print("[LanguageManager] ⚙️ Generated config for \(language.displayName):")
        print("[LanguageManager] ⚙️   - Model: \(config.model)")
        print("[LanguageManager] ⚙️   - Language: \(config.language)")
        print("[LanguageManager] ⚙️   - Sample Rate: \(config.sampleRate) Hz")
        
        return config
    }
    
    /// Check if a model is available for current language
    func isModelAvailable(_ model: String) -> Bool {
        return selectedLanguage.availableModels.contains(model)
    }
    
    /// Get all available models for current language
    func getAvailableModels() -> [String] {
        return selectedLanguage.availableModels
    }
    
    /// Get model description for UI
    func getModelDescription(_ model: String) -> String {
        switch model {
        case "nova-3", "nova-3-general":
            return "Nova-3: Highest performance, multilingual"
        case "nova-3-medical":
            return "Nova-3 Medical: Specialized for medical terminology"
        case "nova-2", "nova-2-general":
            return "Nova-2: Great for non-English, filler words"
        case "nova-2-meeting":
            return "Nova-2 Meeting: Optimized for meetings"
        case "nova-2-phonecall":
            return "Nova-2 Phone: Optimized for phone calls"
        case "nova-2-medical":
            return "Nova-2 Medical: Medical terminology"
        case "nova-2-finance":
            return "Nova-2 Finance: Financial terminology"
        default:
            return model.capitalized
        }
    }
}

/// Extension to create language-aware DGConfig
extension DGConfig {
    /// Create configuration using LanguageManager
    /// - Parameter languageManager: Current language manager instance
    /// - Returns: Language-optimized DGConfig
    static func from(_ languageManager: LanguageManager) -> DGConfig {
        return languageManager.getDeepgramConfig()
    }
}
