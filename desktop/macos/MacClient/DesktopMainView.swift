import SwiftUI

struct DesktopMainView: View {
    @EnvironmentObject var appState: AppState
    @StateObject private var controller = CaptureController()
    
    var body: some View {
        VStack(spacing: 0) {
            // App Header
            HeaderView()
            
            // Main Content
            if appState.meetingState == .preMeeting {
                PreMeetingView(controller: controller)
            } else {
                InMeetingView(controller: controller)
            }
        }
        .background(Color(NSColor.controlBackgroundColor))
        .onAppear {
            checkInitialPermissions()
        }
    }
    
    private func checkInitialPermissions() {
        PermissionsService.checkMicAuthorized { granted in
            appState.isMicAuthorized = granted
            
            // Check screen recording permission asynchronously
            Task {
                if #available(macOS 13.0, *) {
                    let screenPermission = await PermissionsService.checkScreenRecordingPermission()
                    await MainActor.run {
                        appState.isScreenAuthorized = screenPermission
                    }
                } else {
                    await MainActor.run {
                        appState.isScreenAuthorized = false
                    }
                }
            }
        }
    }
}

struct HeaderView: View {
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
                Text("macOS Native")
                    .font(.caption)
                    .foregroundColor(.secondary)
                
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
                if !appState.meetingName.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                    appState.meetingState = .inMeeting
                    appState.clearTranscripts()
                    appState.log("🚀 Toplantı başlatıldı: \(appState.meetingName)")
                }
            }
            .buttonStyle(.borderedProminent)
            .disabled(appState.meetingName.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            
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
                
                // Right Panel: Transcript
                VStack(spacing: 0) {
                    HStack {
                        Text("Canlı Transkript")
                            .font(.headline)
                            .fontWeight(.semibold)
                        
                        Spacer()
                        
                        Toggle("Çeviri Göster", isOn: $appState.showTranslation)
                            .toggleStyle(.switch)
                    }
                    .padding()
                    .background(Color(NSColor.windowBackgroundColor))
                    .overlay(
                        Rectangle()
                            .frame(height: 1)
                            .foregroundColor(Color(NSColor.separatorColor)),
                        alignment: .bottom
                    )
                    
                    ScrollView {
                        LazyVStack(alignment: .leading, spacing: 12) {
                            ForEach(appState.transcriptItems) { item in
                                TranscriptItemView(item: item, showTranslation: appState.showTranslation)
                            }
                        }
                        .padding()
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                }
            }
        }
    }
}

struct TranscriptItemView: View {
    let item: TranscriptItem
    let showTranslation: Bool
    
    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            if !item.isYou {
                Circle()
                    .fill(Color.gray)
                    .frame(width: 32, height: 32)
                    .overlay(
                        Text("S")
                            .font(.caption)
                            .fontWeight(.bold)
                            .foregroundColor(.white)
                    )
            }
            
            VStack(alignment: item.isYou ? .trailing : .leading, spacing: 8) {
                HStack {
                    if !item.isYou {
                        Text(item.speaker)
                            .font(.caption)
                            .fontWeight(.semibold)
                            .foregroundColor(.secondary)
                    }
                    
                    Spacer()
                    
                    if item.isYou {
                        Text(item.speaker)
                            .font(.caption)
                            .fontWeight(.semibold)
                            .foregroundColor(.secondary)
                    }
                }
                
                Text(item.text)
                    .padding(12)
                    .background(item.isYou ? Color.blue : Color(NSColor.controlBackgroundColor))
                    .foregroundColor(item.isYou ? .white : .primary)
                    .clipShape(RoundedRectangle(cornerRadius: 12))
                
                if showTranslation, let translation = item.translation {
                    Text(translation)
                        .font(.caption)
                        .italic()
                        .foregroundColor(.secondary)
                        .padding(.horizontal, 12)
                }
            }
            
            if item.isYou {
                Circle()
                    .fill(Color.blue)
                    .frame(width: 32, height: 32)
                    .overlay(
                        Text("Y")
                            .font(.caption)
                            .fontWeight(.bold)
                            .foregroundColor(.white)
                    )
            }
        }
        .frame(maxWidth: .infinity, alignment: item.isYou ? .trailing : .leading)
    }
}

#Preview {
    DesktopMainView()
        .environmentObject(AppState())
        .frame(width: 1200, height: 800)
}
