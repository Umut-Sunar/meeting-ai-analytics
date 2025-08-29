import Foundation
import Combine

@MainActor
final class AppState: ObservableObject {
    // UI parity fields (mirrors web/DesktopView.tsx)
    @Published var meetingId: String = ""
    @Published var deviceId: String = "mac-desktop-001"
    @Published var language: String = "tr"      // "tr" | "en" | "auto"
    @Published var aiMode: String = "standard"  // "standard" | "super"
    @Published var captureMic: Bool = true
    @Published var captureSystem: Bool = true
    
    // === Backend connection settings ===
    @Published var backendURLString: String = "ws://localhost:8000"  // dev default
    @Published var jwtToken: String = ""  // Loaded from Keychain; updated via Settings
    
    // Meeting state
    @Published var meetingState: MeetingState = .preMeeting
    @Published var meetingName: String = "Yeni Toplantı"
    
    // permissions & runtime
    @Published var isMicAuthorized: Bool = false
    @Published var isScreenAuthorized: Bool = false
    @Published var isCapturing: Bool = false
    
    // Translation settings
    @Published var showTranslation: Bool = false
    
    @Published var statusLines: [String] = []
    
    enum MeetingState {
        case preMeeting
        case inMeeting
    }
    
    func log(_ line: String) {
        let timestamp = DateFormatter.timeFormatter.string(from: Date())
        self.statusLines.append("[\(timestamp)] \(line)")
        if self.statusLines.count > 800 { 
            self.statusLines.removeFirst() 
        }
    }
    
    func clearTranscripts() {
        // Note: Transcript management is now handled by TranscriptWebSocketManager
        // This method is kept for compatibility but doesn't manage transcripts directly
        log("🧹 Transcript clear requested")
    }
}

extension DateFormatter {
    static let timeFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateFormat = "HH:mm:ss"
        return formatter
    }()
}
