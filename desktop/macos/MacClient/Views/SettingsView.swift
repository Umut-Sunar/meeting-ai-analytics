import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var appState: AppState
    @State private var tempURL = ""
    @State private var tempJWT = ""
    @State private var showingJWTAlert = false
    @State private var showingConnectionAlert = false
    @State private var connectionTestResult = ""
    @State private var connectionTestSuccess = false
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Text("Settings")
                    .font(.title2)
                    .fontWeight(.bold)
                
                Spacer()
                
                Button("Done") {
                    dismiss()
                }
                .keyboardShortcut(.escape)
            }
            .padding()
            .background(Color(NSColor.controlBackgroundColor))
            
            Divider()
            
            // Content
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    // Backend Configuration
                    GroupBox("Backend Configuration") {
                        VStack(alignment: .leading, spacing: 16) {
                            // WebSocket URL
                            VStack(alignment: .leading, spacing: 6) {
                                Text("WebSocket Base URL")
                                    .font(.headline)
                                TextField("ws://localhost:8000", text: $tempURL)
                                    .textFieldStyle(.roundedBorder)
                                    .frame(maxWidth: .infinity)
                                Text("Production: Use wss:// for secure connections")
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                            }
                            
                            // JWT Token
                            VStack(alignment: .leading, spacing: 6) {
                                Text("JWT Token")
                                    .font(.headline)
                                SecureField("Paste JWT token here", text: $tempJWT)
                                    .textFieldStyle(.roundedBorder)
                                    .frame(maxWidth: .infinity)
                                Text("Get from: backend/scripts/generate_keys.py")
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                            }
                        }
                        .padding()
                    }
                    
                    // Actions
                    GroupBox("Actions") {
                        VStack(spacing: 12) {
                            HStack {
                                Button("Test Connection") {
                                    testConnection()
                                }
                                .disabled(tempURL.isEmpty)
                                .buttonStyle(.bordered)
                                
                                Spacer()
                                
                                Button("Clear JWT") {
                                    KeychainStore.deleteJWT()
                                    tempJWT = ""
                                    appState.jwtToken = ""
                                    appState.log("🗑️ JWT token cleared")
                                }
                                .foregroundColor(.red)
                                .buttonStyle(.bordered)
                            }
                            
                            Button("Save Settings") {
                                saveSettings()
                            }
                            .buttonStyle(.borderedProminent)
                            .frame(maxWidth: .infinity)
                        }
                        .padding()
                    }
                    
                    // Note
                    Text("Note: Use HTTPS/WSS in production. JWT tokens are stored securely in Keychain.")
                        .font(.caption)
                        .foregroundColor(.secondary)
                        .multilineTextAlignment(.center)
                        .frame(maxWidth: .infinity)
                }
                .padding()
            }
        }
        .frame(width: 600, height: 450)
        .background(Color(NSColor.windowBackgroundColor))
        .onAppear {
            loadCurrentSettings()
        }
        .alert("Connection Test Result", isPresented: $showingConnectionAlert) {
            Button("OK") { }
        } message: {
            Text(connectionTestResult)
        }
    }
    
    private func loadCurrentSettings() {
        tempURL = appState.backendURLString
        
        // Load JWT from Keychain if not already loaded
        let stored = KeychainStore.loadJWT()
        if !stored.isEmpty {
            appState.jwtToken = stored
        }
        tempJWT = appState.jwtToken
    }
    
    private func saveSettings() {
        // Update backend URL
        if !tempURL.isEmpty {
            appState.backendURLString = tempURL
        }
        
        // Update and save JWT token
        if !tempJWT.isEmpty {
            appState.jwtToken = tempJWT
            KeychainStore.saveJWT(tempJWT)
            appState.log("🔐 JWT token saved to Keychain")
        }
        
        appState.log("⚙️ Backend settings updated")
        appState.log("📡 Backend URL: \(appState.backendURLString)")
        appState.log("🔑 JWT: \(appState.jwtToken.isEmpty ? "Not set" : "***\(appState.jwtToken.suffix(8))")")
    }
    
    private func testConnection() {
        appState.log("🔍 Testing backend connection...")
        
        // Basic URL validation
        guard let url = URL(string: tempURL) else {
            appState.log("❌ Invalid URL format")
            showConnectionResult(success: false, message: "Invalid URL format")
            return
        }
        
        guard url.scheme == "ws" || url.scheme == "wss" || url.scheme == "http" || url.scheme == "https" else {
            appState.log("❌ URL must use valid scheme (ws/wss/http/https)")
            showConnectionResult(success: false, message: "Invalid URL scheme")
            return
        }
        
        // JWT validation and sanitization
        if tempJWT.isEmpty {
            appState.log("❌ JWT token is required")
            showConnectionResult(success: false, message: "JWT token is required")
            return
        }
        
        // Sanitize the JWT token (inline implementation)
        let cleanToken = tempJWT.components(separatedBy: .whitespacesAndNewlines).joined().trimmingCharacters(in: .whitespacesAndNewlines)
        
        // Validate JWT structure (3 parts separated by dots)
        let tokenParts = cleanToken.components(separatedBy: ".")
        if tokenParts.count != 3 || tokenParts.contains(where: { $0.isEmpty }) {
            appState.log("❌ Invalid JWT token format")
            showConnectionResult(success: false, message: "Invalid JWT token format")
            return
        }
        
        let maskedToken = cleanToken.count > 6 ? "***\(cleanToken.suffix(6))" : "***"
        appState.log("✅ URL format valid: \(url.absoluteString)")
        appState.log("🔑 JWT token provided: \(maskedToken)")
        
        // Test backend health endpoint first
        testBackendHealth { healthSuccess in
            if healthSuccess {
                // Test WebSocket connection with JWT
                self.testWebSocketConnection(cleanToken: cleanToken)
            } else {
                DispatchQueue.main.async {
                    self.showConnectionResult(success: false, message: "Backend is not running or unreachable")
                }
            }
        }
    }
    
    private func testBackendHealth(completion: @escaping (Bool) -> Void) {
        // Convert WS URL to HTTP for health check
        var healthURL = tempURL
        if healthURL.hasPrefix("ws://") {
            healthURL = healthURL.replacingOccurrences(of: "ws://", with: "http://")
        } else if healthURL.hasPrefix("wss://") {
            healthURL = healthURL.replacingOccurrences(of: "wss://", with: "https://")
        }
        
        // Add health endpoint
        let healthEndpoint = "\(healthURL)/api/v1/health"
        
        guard let url = URL(string: healthEndpoint) else {
            completion(false)
            return
        }
        
        appState.log("🏥 Testing health endpoint: \(healthEndpoint)")
        
        let task = URLSession.shared.dataTask(with: url) { data, response, error in
            DispatchQueue.main.async {
                if let error = error {
                    self.appState.log("❌ Health check failed: \(error.localizedDescription)")
                    completion(false)
                    return
                }
                
                if let httpResponse = response as? HTTPURLResponse {
                    if httpResponse.statusCode == 200 {
                        self.appState.log("✅ Backend health OK (HTTP 200)")
                        completion(true)
                    } else {
                        self.appState.log("❌ Backend health failed (HTTP \(httpResponse.statusCode))")
                        completion(false)
                    }
                } else {
                    completion(false)
                }
            }
        }
        
        task.resume()
    }
    
    private func testWebSocketConnection(cleanToken: String) {
        appState.log("🔌 Testing WebSocket connection with JWT...")
        
        // Create test WebSocket connection
        let testWS = BackendIngestWS()
        
        var connectionTested = false
        
        testWS.onConnected = {
            guard !connectionTested else { return }
            connectionTested = true
            
            DispatchQueue.main.async {
                self.appState.log("✅ WebSocket connection successful!")
                self.showConnectionResult(success: true, message: "Connection successful! Backend is ready.")
                testWS.stop()
            }
        }
        
        testWS.onError = { error in
            guard !connectionTested else { return }
            connectionTested = true
            
            DispatchQueue.main.async {
                self.appState.log("❌ WebSocket connection failed: \(error)")
                
                if error.contains("403") || error.contains("Forbidden") {
                    self.showConnectionResult(success: false, message: "JWT token is invalid or expired")
                } else if error.contains("Connection refused") {
                    self.showConnectionResult(success: false, message: "Backend WebSocket not available")
                } else {
                    self.showConnectionResult(success: false, message: "Connection failed: \(error)")
                }
                
                testWS.stop()
            }
        }
        
        testWS.onLog = { message in
            DispatchQueue.main.async {
                self.appState.log("🔍 Test: \(message)")
            }
        }
        
        // Test connection with new API
        guard let testURL = buildTestWebSocketURL(baseURL: tempURL, jwtToken: cleanToken) else {
            self.appState.log("❌ Failed to build test WebSocket URL")
            return
        }
        
        testWS.connect(url: testURL, meetingId: "test-connection", source: "mic")
        
        // Timeout after 10 seconds
        DispatchQueue.main.asyncAfter(deadline: .now() + 10) {
            guard !connectionTested else { return }
            connectionTested = true
            
            self.appState.log("⏰ Connection test timeout")
            self.showConnectionResult(success: false, message: "Connection test timeout (10s)")
            testWS.stop()
        }
    }
    
    private func buildTestWebSocketURL(baseURL: String, jwtToken: String) -> URL? {
        // Parse base URL
        guard let baseURLObj = URL(string: baseURL) else {
            return nil
        }
        
        // Build WebSocket URL components
        var components = URLComponents()
        
        // Determine scheme (ws for local, wss for prod)
        let isLocal = baseURL.contains("localhost") || baseURL.contains("127.0.0.1")
        components.scheme = isLocal ? "ws" : "wss"
        
        // Set host (force IPv4 for localhost)
        let host = baseURLObj.host ?? "127.0.0.1"
        components.host = host == "localhost" ? "127.0.0.1" : host
        
        // Set port
        components.port = baseURLObj.port ?? (isLocal ? 8000 : nil)
        
        // Set path
        components.path = "/api/v1/ws/ingest/meetings/test-connection"
        
        // Add query parameters
        components.queryItems = [
            URLQueryItem(name: "source", value: "mic"),
            URLQueryItem(name: "token", value: jwtToken)
        ]
        
        return components.url
    }
    
    private func showConnectionResult(success: Bool, message: String) {
        connectionTestResult = message
        connectionTestSuccess = success
        showingConnectionAlert = true
        
        if success {
            appState.log("🎉 Connection test PASSED")
        } else {
            appState.log("💥 Connection test FAILED")
        }
    }
}

#Preview {
    SettingsView()
        .environmentObject(AppState())
}