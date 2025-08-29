import SwiftUI

struct DesktopMainView: View {
    @EnvironmentObject var appState: AppState
    @StateObject private var controller = CaptureController()
    @State private var showSettings = false
    
    var body: some View {
        VStack(spacing: 0) {
            // App Header
            HeaderView(showSettings: $showSettings)
            
            // Main Content
            if appState.meetingState == .preMeeting {
                PreMeetingView(controller: controller)
            } else {
                InMeetingView(controller: controller)
            }
        }
        .background(Color(NSColor.controlBackgroundColor))
        .sheet(isPresented: $showSettings) {
            SettingsView()
                .environmentObject(appState)
        }
        .onAppear {
            checkInitialPermissions()
        }
    }
    
    private func checkInitialPermissions() {
        // Check microphone permission
        PermissionsService.checkMicAuthorized { granted in
            Task { @MainActor in
                appState.isMicAuthorized = granted
            }
        }
        
        // Check screen recording permission using reliable async method
        Task { @MainActor in
            appState.isScreenAuthorized = await PermissionsService.hasScreenRecordingPermission()
            appState.log("🚀 MacClient started successfully")
        }
    }
}

struct HeaderView: View {
    @Binding var showSettings: Bool
    
    var body: some View {
        HStack {
            HStack(spacing: 12) {
                Image(systemName: "mic.fill")
                    .foregroundColor(.white)
                    .frame(width: 20, height: 20)
                    .padding(8)
                    .background(Color.blue)
                    .clipShape(RoundedRectangle(cornerRadius: 8))
                
                Text("MeetingAI Desktop")
                    .font(.headline)
                    .fontWeight(.bold)
            }
            
            Spacer()
            
            HStack(spacing: 16) {
                Text("Backend WebSocket Mode")
                    .font(.caption)
                    .foregroundColor(.secondary)
                
                Button(action: {
                    print("🔧 Settings button tapped")
                    showSettings = true
                }) {
                    HStack(spacing: 6) {
                        Image(systemName: "gearshape.fill")
                        Text("Settings")
                    }
                    .font(.caption)
                }
                .buttonStyle(.bordered)
                
                Button("Analytics") {
                    // Analytics action
                }
                .buttonStyle(.link)
            }
        }
        .padding()
        .background(Color(NSColor.windowBackgroundColor))
        .overlay(
            Rectangle()
                .frame(height: 1)
                .foregroundColor(Color(NSColor.separatorColor)),
            alignment: .bottom
        )
    }
}

struct PreMeetingView: View {
    @EnvironmentObject var appState: AppState
    let controller: CaptureController
    
    var body: some View {
        VStack(spacing: 24) {
            Spacer()
            
            VStack(spacing: 16) {
                Image(systemName: "mic.fill")
                    .font(.system(size: 32))
                    .foregroundColor(.white)
                    .frame(width: 64, height: 64)
                    .background(Color.blue)
                    .clipShape(Circle())
                
                Text("Toplantınızı Hazırlayın")
                    .font(.title)
                    .fontWeight(.bold)
                
                Text("Toplantı adı, dil ve AI asistan ayarlarını yapılandırın.")
                    .font(.body)
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
            }
            
            VStack(spacing: 20) {
                // Meeting Configuration
                GroupBox("Toplantı Ayarları") {
                    VStack(alignment: .leading, spacing: 12) {
                        HStack {
                            Text("Meeting ID:")
                                .frame(width: 120, alignment: .leading)
                            TextField("örn. 3f9a-...", text: $appState.meetingId)
                                .textFieldStyle(.roundedBorder)
                        }
                        
                        HStack {
                            Text("Device ID:")
                                .frame(width: 120, alignment: .leading)
                            TextField("örn. mac-01", text: $appState.deviceId)
                                .textFieldStyle(.roundedBorder)
                        }
                        
                        HStack {
                            Text("Toplantı Adı:")
                                .frame(width: 120, alignment: .leading)
                            TextField("Yeni Toplantı", text: $appState.meetingName)
                                .textFieldStyle(.roundedBorder)
                        }
                        
                        HStack {
                            Text("Dil:")
                                .frame(width: 120, alignment: .leading)
                            Picker("", selection: $appState.language) {
                                Text("Türkçe").tag("tr")
                                Text("English").tag("en")
                                Text("Auto").tag("auto")
                            }
                            .pickerStyle(.segmented)
                            .frame(width: 200)
                            
                            Spacer()
                            
                            Text("AI Mode:")
                            Picker("", selection: $appState.aiMode) {
                                Text("Standard").tag("standard")
                                Text("Super").tag("super")
                            }
                            .pickerStyle(.segmented)
                            .frame(width: 200)
                        }
                        
                        HStack {
                            Text("Kaynaklar:")
                                .frame(width: 120, alignment: .leading)
                            Toggle("Mikrofon", isOn: $appState.captureMic)
                            Toggle("Sistem Sesi", isOn: $appState.captureSystem)
                            Spacer()
                        }
                    }
                    .padding()
                }
                
                // Permissions
                GroupBox("İzinler") {
                    VStack(spacing: 12) {
                        HStack {
                            Button("Mikrofon İzni Kontrol Et") {
                                PermissionsService.checkMicAuthorized { granted in
                                    appState.isMicAuthorized = granted
                                    appState.log(granted ? "✅ Mikrofon izni verildi" : "❌ Mikrofon izni reddedildi")
                                }
                            }
                            
                            Image(systemName: appState.isMicAuthorized ? "checkmark.circle.fill" : "xmark.circle.fill")
                                .foregroundColor(appState.isMicAuthorized ? .green : .red)
                            
                            Spacer()
                            
                            Button("Ekran Kaydı İzni") {
                                PermissionsService.openScreenRecordingPrefs()
                                appState.log("ℹ️ Ekran kaydı izni için Sistem Ayarları açıldı.")
                            }
                            
                            Image(systemName: appState.isScreenAuthorized ? "checkmark.circle.fill" : "xmark.circle.fill")
                                .foregroundColor(appState.isScreenAuthorized ? .green : .red)
                        }
                    }
                    .padding()
                }
            }
            .frame(maxWidth: 600)
            
            Button("Toplantıyı Başlat") {
                // Validate required fields
                let name = appState.meetingName.trimmingCharacters(in: .whitespacesAndNewlines)
                let meetingId = appState.meetingId.trimmingCharacters(in: .whitespacesAndNewlines)
                let deviceId = appState.deviceId.trimmingCharacters(in: .whitespacesAndNewlines)
                let backendURL = appState.backendURLString.trimmingCharacters(in: .whitespacesAndNewlines)
                
                var validationErrors: [String] = []
                
                if name.isEmpty { validationErrors.append("Meeting Name") }
                if meetingId.isEmpty { validationErrors.append("Meeting ID") }
                if deviceId.isEmpty { validationErrors.append("Device ID") }
                if backendURL.isEmpty { validationErrors.append("Backend URL") }
                if appState.jwtToken.isEmpty { validationErrors.append("JWT Token") }
                
                if !validationErrors.isEmpty {
                    appState.log("❌ Missing required fields: \(validationErrors.joined(separator: ", "))")
                    appState.log("💡 Please check Settings for Backend URL and JWT Token")
                    return
                }
                
                if !appState.isMicAuthorized {
                    appState.log("❌ Microphone permission required")
                    return
                }
                
                appState.meetingState = .inMeeting
                appState.clearTranscripts()
                appState.log("🚀 Meeting started: \(name)")
                appState.log("📡 Backend: \(backendURL)")
                appState.log("🆔 Meeting ID: \(meetingId)")
            }
            .buttonStyle(.borderedProminent)
            .disabled(
                appState.meetingName.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ||
                appState.meetingId.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ||
                appState.deviceId.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ||
                appState.backendURLString.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ||
                !appState.isMicAuthorized
            )
            
            Spacer()
        }
        .padding()
    }
}

struct InMeetingView: View {
    @EnvironmentObject var appState: AppState
    let controller: CaptureController
    
    var body: some View {
        VStack(spacing: 0) {
            // Meeting Header
            HStack {
                HStack(spacing: 8) {
                    Circle()
                        .fill(Color.red)
                        .frame(width: 12, height: 12)
                        .overlay(
                            Circle()
                                .fill(Color.red.opacity(0.3))
                                .scaleEffect(appState.isCapturing ? 1.5 : 1.0)
                                .animation(.easeInOut(duration: 1.0).repeatForever(autoreverses: true), value: appState.isCapturing)
                        )
                    
                    Text("Canlı: \(appState.meetingName)")
                        .font(.headline)
                        .fontWeight(.semibold)
                    
                    Text(appState.language.uppercased())
                        .font(.caption)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(Color.secondary.opacity(0.2))
                        .clipShape(RoundedRectangle(cornerRadius: 4))
                }
                
                Spacer()
                
                HStack(spacing: 16) {
                    Toggle("Super Mode", isOn: .constant(appState.aiMode == "super"))
                        .toggleStyle(.switch)
                    
                    Button(appState.isCapturing ? "Durdur" : "Başlat") {
                        if appState.isCapturing {
                            controller.stop(appState: appState)
                        } else {
                            controller.start(appState: appState)
                        }
                    }
                    .buttonStyle(.borderedProminent)
                    
                    Button("Toplantıyı Bitir") {
                        controller.stop(appState: appState)
                        appState.meetingState = .preMeeting
                        appState.log("🏁 Toplantı bitirildi")
                    }
                    .buttonStyle(.bordered)
                    .foregroundColor(.red)
                }
            }
            .padding()
            .background(Color(NSColor.windowBackgroundColor))
            .overlay(
                Rectangle()
                    .frame(height: 1)
                    .foregroundColor(Color(NSColor.separatorColor)),
                alignment: .bottom
            )
            
            // Main Content
            HSplitView {
                // Left Panel: Controls & Logs
                VStack(spacing: 16) {
                    // Status
                    GroupBox("Durum") {
                        VStack(alignment: .leading, spacing: 8) {
                            HStack {
                                Text("Mikrofon:")
                                Spacer()
                                Text(appState.isMicAuthorized ? "✅ Aktif" : "❌ İzin Yok")
                                    .foregroundColor(appState.isMicAuthorized ? .green : .red)
                            }
                            
                            HStack {
                                Text("Sistem Sesi:")
                                Spacer()
                                Text(appState.isScreenAuthorized ? "✅ Aktif" : "❌ İzin Yok")
                                    .foregroundColor(appState.isScreenAuthorized ? .green : .red)
                            }
                            
                            HStack {
                                Text("Kayıt:")
                                Spacer()
                                Text(appState.isCapturing ? "🔴 Kaydediliyor" : "⏹️ Durduruldu")
                                    .foregroundColor(appState.isCapturing ? .red : .secondary)
                            }
                        }
                        .padding()
                    }
                    
                    // Logs
                    GroupBox("Loglar") {
                        ScrollView {
                            ScrollViewReader { proxy in
                                LazyVStack(alignment: .leading, spacing: 2) {
                                    ForEach(Array(appState.statusLines.enumerated()), id: \.offset) { index, line in
                                        Text(line)
                                            .font(.system(.caption, design: .monospaced))
                                            .frame(maxWidth: .infinity, alignment: .leading)
                                            .id(index)
                                    }
                                }
                                .padding(8)
                                .onChange(of: appState.statusLines.count) { _ in
                                    if let lastIndex = appState.statusLines.indices.last {
                                        proxy.scrollTo(lastIndex, anchor: .bottom)
                                    }
                                }
                            }
                        }
                        .frame(minHeight: 200)
                    }
                    
                    Spacer()
                }
                .frame(minWidth: 300, maxWidth: 400)
                
                // Right Panel: Dual-Source Transcript
                TranscriptView(appState: appState)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
        }
    }
}

// Old TranscriptItemView removed - using new dual-source TranscriptView

#Preview {
    DesktopMainView()
        .environmentObject(AppState())
        .frame(width: 1200, height: 800)
}
