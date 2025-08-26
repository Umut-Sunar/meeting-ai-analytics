import Foundation
import Combine

final class AppState: ObservableObject {
    // UI parity fields (mirrors web/DesktopView.tsx)
    @Published var meetingId: String = ""
    @Published var deviceId: String = "mac-desktop-001"
    @Published var language: String = "tr"      // "tr" | "en" | "auto"
    @Published var aiMode: String = "standard"  // "standard" | "super"
    @Published var captureMic: Bool = true
    @Published var captureSystem: Bool = true
    
    // Meeting state
    @Published var meetingState: MeetingState = .preMeeting
    @Published var meetingName: String = "Yeni Toplantı"
    
    // permissions & runtime
    @Published var isMicAuthorized: Bool = false
    @Published var isScreenAuthorized: Bool = false
    @Published var isCapturing: Bool = false
    
    // Transcript data
    @Published var transcriptItems: [TranscriptItem] = []
    @Published var showTranslation: Bool = false
    
    @Published var statusLines: [String] = []
    
    enum MeetingState {
        case preMeeting
        case inMeeting
    }
    
    func log(_ line: String) {
        DispatchQueue.main.async {
            let timestamp = DateFormatter.timeFormatter.string(from: Date())
            self.statusLines.append("[\(timestamp)] \(line)")
            if self.statusLines.count > 800 { 
                self.statusLines.removeFirst() 
            }
        }
    }
    
    func addTranscript(_ item: TranscriptItem) {
        DispatchQueue.main.async {
            self.transcriptItems.append(item)
        }
    }
    
    func clearTranscripts() {
        DispatchQueue.main.async {
            self.transcriptItems.removeAll()
        }
    }
}

struct TranscriptItem: Identifiable {
    let id = UUID()
    let speaker: String
    let text: String
    let translation: String?
    let timestamp: Date
    let isYou: Bool
    
    init(speaker: String, text: String, translation: String? = nil, isYou: Bool = false) {
        self.speaker = speaker
        self.text = text
        self.translation = translation
        self.timestamp = Date()
        self.isYou = isYou
    }
}

extension DateFormatter {
    static let timeFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateFormat = "HH:mm:ss"
        return formatter
    }()
}
