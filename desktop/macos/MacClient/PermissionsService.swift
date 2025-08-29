import AVFoundation
import AppKit
import ScreenCaptureKit

enum PermissionsService {
    static func checkMicAuthorized(completion: @escaping (Bool)->Void) {
        switch AVCaptureDevice.authorizationStatus(for: .audio) {
        case .authorized: completion(true)
        case .notDetermined:
            AVCaptureDevice.requestAccess(for: .audio) { completion($0) }
        default: completion(false)
        }
    }
    
    static func openScreenRecordingPrefs() {
        if let url = URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture") {
            NSWorkspace.shared.open(url)
        }
    }

    /// Asenkron ve güvenilir izin kontrolü - SCShareableContent kullanır
    @available(macOS 13.0, *)
    static func hasScreenRecordingPermission() async -> Bool {
        do { 
            _ = try await SCShareableContent.current
            return true
        } catch { 
            return false 
        }
    }

    /// İsteğe bağlı: sistem diyaloğunu tetiklemek için (bazı sürümlerde gösterir)
    static func requestScreenRecordingPermission() -> Bool {
        CGRequestScreenCaptureAccess()
    }
}
