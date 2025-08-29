// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "MacClient",
    platforms: [
        .macOS(.v13)
    ],
    products: [
        .executable(
            name: "MacClient",
            targets: ["MacClient"]
        ),
    ],
    dependencies: [
        // Add any external dependencies here
    ],
    targets: [
        .executableTarget(
            name: "MacClient",
            dependencies: [],
            path: ".",
            sources: [
                "App.swift",
                "AppState.swift", 
                "PermissionsService.swift",
                "CaptureController.swift",
                "DesktopMainView.swift",
                "Networking/BackendIngestWS.swift",
                "Security/KeychainStore.swift",
                "Views/SettingsView.swift",
                "AudioAssist_V1_Sources/AudioEngine.swift",
                "AudioAssist_V1_Sources/DeepgramClient.swift",
                "AudioAssist_V1_Sources/LanguageManager.swift",
                "AudioAssist_V1_Sources/MicCapture.swift",
                "AudioAssist_V1_Sources/SystemAudioCaptureSC.swift",
                "AudioAssist_V1_Sources/AudioSourceType.swift",
                "AudioAssist_V1_Sources/PermissionManager.swift",
                "AudioAssist_V1_Sources/APIKeyManager.swift",
                "AudioAssist_V1_Sources/Resampler.swift"
            ]
        ),
    ]
)
