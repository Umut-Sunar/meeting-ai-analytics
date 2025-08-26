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

    @available(macOS 13.0, *)
    static func checkScreenRecordingPermission() async -> Bool {
        do {
            let content = try await SCShareableContent.current
            return !content.displays.isEmpty
        } catch {
            print("Screen recording permission check failed: \(error)")
            return false
        }
    }
    
    @available(macOS 13.0, *)
    static func requestScreenRecordingPermission() -> Bool {
        return CGRequestScreenCaptureAccess()
    }
}
