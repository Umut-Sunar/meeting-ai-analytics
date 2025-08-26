import SwiftUI

@main
struct MacClientApp: App {
    @StateObject private var appState = AppState()
    
    var body: some Scene {
        WindowGroup {
            DesktopMainView()
                .environmentObject(appState)
                .frame(minWidth: 1200, minHeight: 800)
        }
        .windowStyle(.automatic)
        .windowResizability(.contentSize)
    }
}
