import SwiftUI
import Foundation

// MARK: - Transcript Models
struct TranscriptItem: Identifiable, Codable {
    let id = UUID()
    let speaker: String
    let text: String
    let source: TranscriptSource
    let timestamp: Date
    let confidence: Double?
    
    enum TranscriptSource: String, Codable, CaseIterable {
        case mic = "mic"
        case sys = "sys"
        
        var displayName: String {
            switch self {
            case .mic: return "Mikrofon"
            case .sys: return "Sistem Sesi"
            }
        }
        
        var icon: String {
            switch self {
            case .mic: return "🎤"
            case .sys: return "🔊"
            }
        }
        
        var color: Color {
            switch self {
            case .mic: return .blue
            case .sys: return .green
            }
        }
    }
}

struct TranscriptMessage: Codable {
    let type: String
    let meeting_id: String?
    let source: String?
    let segment_no: Int?
    let start_ms: Int?
    let end_ms: Int?
    let speaker: String?
    let text: String?
    let confidence: Double?
    let meta: [String: String]?
    let ts: String?
    
    // Check if this is a final transcript
    var is_final: Bool {
        return type == "transcript.final"
    }
}

// MARK: - Transcript WebSocket Manager
class TranscriptWebSocketManager: ObservableObject {
    @Published var transcripts: [TranscriptItem] = []
    @Published var connectionStatus: ConnectionStatus = .disconnected
    @Published var errorMessage: String?
    
    private var webSocketTask: URLSessionWebSocketTask?
    private let urlSession = URLSession(configuration: .default)
    
    enum ConnectionStatus {
        case disconnected
        case connecting
        case connected
        
        var displayText: String {
            switch self {
            case .disconnected: return "Bağlı Değil"
            case .connecting: return "Bağlanıyor..."
            case .connected: return "Backend Bağlı"
            }
        }
        
        var color: Color {
            switch self {
            case .disconnected: return .red
            case .connecting: return .orange
            case .connected: return .green
            }
        }
    }
    
    func connect(backendURL: String, meetingId: String, jwtToken: String = "") {
        guard connectionStatus != .connected else { return }
        
        // Clean URL and construct WebSocket URL properly
        let cleanURL = backendURL.trimmingCharacters(in: .whitespacesAndNewlines)
            .replacingOccurrences(of: "http://", with: "")
            .replacingOccurrences(of: "https://", with: "")
            .replacingOccurrences(of: "ws://", with: "")
            .replacingOccurrences(of: "wss://", with: "")
        
        let wsURLString = "ws://\(cleanURL)/api/v1/transcript/\(meetingId)"
        
        guard let url = URL(string: wsURLString) else {
            DispatchQueue.main.async {
                self.errorMessage = "Invalid WebSocket URL: \(wsURLString)"
            }
            return
        }
        
        connectionStatus = .connecting
        errorMessage = nil
        
        print("🌐 Connecting to transcript WebSocket: \(wsURLString)")
        
        // Create URLRequest with Authorization header if JWT token is provided
        var request = URLRequest(url: url)
        if !jwtToken.isEmpty {
            // Sanitize JWT token
            let cleanToken = jwtToken.components(separatedBy: .whitespacesAndNewlines).joined()
            request.setValue("Bearer \(cleanToken)", forHTTPHeaderField: "Authorization")
            print("🔑 Using JWT token for transcript WebSocket authentication")
        }
        
        webSocketTask = urlSession.webSocketTask(with: request)
        webSocketTask?.resume()
        
        // Start receiving messages
        receiveMessage()
        
        DispatchQueue.main.async {
            self.connectionStatus = .connected
        }
    }
    
    func disconnect() {
        webSocketTask?.cancel(with: .goingAway, reason: nil)
        webSocketTask = nil
        
        DispatchQueue.main.async {
            self.connectionStatus = .disconnected
        }
    }
    
    private func receiveMessage() {
        webSocketTask?.receive { [weak self] result in
            switch result {
            case .success(let message):
                switch message {
                case .string(let text):
                    self?.handleTextMessage(text)
                case .data(let data):
                    if let text = String(data: data, encoding: .utf8) {
                        self?.handleTextMessage(text)
                    }
                @unknown default:
                    break
                }
                
                // Continue receiving
                self?.receiveMessage()
                
            case .failure(let error):
                print("❌ WebSocket receive error: \(error)")
                DispatchQueue.main.async {
                    self?.connectionStatus = .disconnected
                    self?.errorMessage = "Connection error: \(error.localizedDescription)"
                }
            }
        }
    }
    
    private func handleTextMessage(_ text: String) {
        print("📥 Received transcript message: \(text)")
        
        // Parse transcript message
        guard let data = text.data(using: .utf8) else { return }
        
        do {
            let message = try JSONDecoder().decode(TranscriptMessage.self, from: data)
            
            // Handle ping messages
            if message.type == "ping" {
                print("💓 Received ping message")
                return
            }
            
            // Skip messages without required transcript fields
            guard let meetingId = message.meeting_id,
                  let source = message.source,
                  let text = message.text,
                  let ts = message.ts else {
                print("⚠️ Skipping message with missing required fields")
                return
            }
            
            // Process both final and partial transcripts
            // Final transcripts are permanent, partial ones are temporary
            let isPartial = !message.is_final
            
            let sourceType = TranscriptItem.TranscriptSource(rawValue: source) ?? .mic
            let timestamp = ISO8601DateFormatter().date(from: ts) ?? Date()
            
            let item = TranscriptItem(
                speaker: message.speaker ?? sourceType.displayName,
                text: text,
                source: sourceType,
                timestamp: timestamp,
                confidence: message.confidence
            )
            
            DispatchQueue.main.async {
                if isPartial {
                    // For partial transcripts, replace the last item if it's from the same source and segment
                    if let lastIndex = self.transcripts.lastIndex(where: { 
                        $0.source == sourceType && $0.timestamp.timeIntervalSince(timestamp) < 5.0 
                    }) {
                        self.transcripts[lastIndex] = item
                        print("🔄 Updated partial transcript: \(item.speaker) - \(message.text)")
                    } else {
                        self.transcripts.append(item)
                        print("📝 Added partial transcript: \(item.speaker) - \(message.text)")
                    }
                } else {
                    // Final transcripts are always appended
                    self.transcripts.append(item)
                    print("✅ Added final transcript: \(item.speaker) - \(message.text)")
                }
            }
            
        } catch {
            print("❌ Failed to parse transcript message: \(error)")
            print("📄 Raw message: \(text)")
        }
    }
}

// MARK: - Transcript View Components
struct TranscriptItemView: View {
    let item: TranscriptItem
    
    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            // Source icon
            Text(item.source.icon)
                .font(.title2)
                .frame(width: 32, height: 32)
                .background(item.source.color.opacity(0.1))
                .clipShape(Circle())
                .overlay(
                    Circle()
                        .stroke(item.source.color, lineWidth: 2)
                )
            
            VStack(alignment: .leading, spacing: 4) {
                // Header
                HStack {
                    Text(item.speaker)
                        .font(.caption)
                        .fontWeight(.semibold)
                        .foregroundColor(item.source.color)
                    
                    Spacer()
                    
                    Text(item.timestamp, style: .time)
                        .font(.caption2)
                        .foregroundColor(.secondary)
                }
                
                // Transcript text
                Text(item.text)
                    .font(.body)
                    .foregroundColor(.primary)
                    .multilineTextAlignment(.leading)
                
                // Confidence indicator
                if let confidence = item.confidence {
                    HStack {
                        Text("Güven: \(Int(confidence * 100))%")
                            .font(.caption2)
                            .foregroundColor(.secondary)
                        Spacer()
                    }
                }
            }
            
            Spacer()
        }
        .padding(.vertical, 8)
        .padding(.horizontal, 12)
        .background(Color(NSColor.controlBackgroundColor))
        .cornerRadius(8)
    }
}

// MARK: - Main Transcript View
struct TranscriptView: View {
    @StateObject private var wsManager = TranscriptWebSocketManager()
    @ObservedObject var appState: AppState
    
    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Text("Live Transcript")
                    .font(.title2)
                    .fontWeight(.bold)
                
                Spacer()
                
                // Connection status
                HStack(spacing: 8) {
                    Circle()
                        .fill(wsManager.connectionStatus.color)
                        .frame(width: 8, height: 8)
                    
                    Text(wsManager.connectionStatus.displayText)
                        .font(.caption)
                        .foregroundColor(.secondary)
                    
                    Button(wsManager.connectionStatus == .connected ? "Disconnect" : "Connect") {
                        if wsManager.connectionStatus == .connected {
                            wsManager.disconnect()
                        } else {
                            wsManager.connect(
                                backendURL: appState.backendURLString,
                                meetingId: appState.meetingId,
                                jwtToken: appState.jwtToken
                            )
                        }
                    }
                    .buttonStyle(.bordered)
                    .controlSize(.small)
                }
            }
            .padding()
            .background(Color(NSColor.windowBackgroundColor))
            
            Divider()
            
            // Error message
            if let errorMessage = wsManager.errorMessage {
                HStack {
                    Image(systemName: "exclamationmark.triangle")
                        .foregroundColor(.orange)
                    Text(errorMessage)
                        .font(.caption)
                        .foregroundColor(.secondary)
                    Spacer()
                }
                .padding()
                .background(Color.orange.opacity(0.1))
            }
            
            // Transcript content
            if wsManager.transcripts.isEmpty {
                // Empty state
                VStack(spacing: 16) {
                    Image(systemName: "text.bubble")
                        .font(.system(size: 48))
                        .foregroundColor(.secondary)
                    
                    Text("Transcript'ler burada görünecek")
                        .font(.headline)
                        .foregroundColor(.secondary)
                    
                    Text("MacClient'ta capture başlatın ve konuşmaya başlayın")
                        .font(.caption)
                        .foregroundColor(.secondary)
                        .multilineTextAlignment(.center)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                
            } else {
                // Dual column layout
                HStack(spacing: 1) {
                    // Mikrofon column
                    VStack(spacing: 0) {
                        // Column header
                        HStack {
                            Text("🎤")
                                .font(.title3)
                            Text("Mikrofon")
                                .font(.headline)
                                .foregroundColor(.blue)
                            Spacer()
                        }
                        .padding()
                        .background(Color.blue.opacity(0.1))
                        
                        // Transcript list
                        ScrollViewReader { proxy in
                            ScrollView {
                                LazyVStack(spacing: 8) {
                                    ForEach(wsManager.transcripts.filter { $0.source == .mic }) { item in
                                        TranscriptItemView(item: item)
                                            .id(item.id)
                                    }
                                }
                                .padding()
                            }
                            .onChange(of: wsManager.transcripts.count) { _ in
                                // Auto-scroll to latest mic transcript
                                if let lastMicItem = wsManager.transcripts.filter({ $0.source == .mic }).last {
                                    withAnimation(.easeOut(duration: 0.3)) {
                                        proxy.scrollTo(lastMicItem.id, anchor: .bottom)
                                    }
                                }
                            }
                        }
                    }
                    .frame(maxWidth: .infinity)
                    
                    Divider()
                    
                    // Sistem Sesi column
                    VStack(spacing: 0) {
                        // Column header
                        HStack {
                            Text("🔊")
                                .font(.title3)
                            Text("Sistem Sesi")
                                .font(.headline)
                                .foregroundColor(.green)
                            Spacer()
                        }
                        .padding()
                        .background(Color.green.opacity(0.1))
                        
                        // Transcript list
                        ScrollViewReader { proxy in
                            ScrollView {
                                LazyVStack(spacing: 8) {
                                    ForEach(wsManager.transcripts.filter { $0.source == .sys }) { item in
                                        TranscriptItemView(item: item)
                                            .id(item.id)
                                    }
                                }
                                .padding()
                            }
                            .onChange(of: wsManager.transcripts.count) { _ in
                                // Auto-scroll to latest sys transcript
                                if let lastSysItem = wsManager.transcripts.filter({ $0.source == .sys }).last {
                                    withAnimation(.easeOut(duration: 0.3)) {
                                        proxy.scrollTo(lastSysItem.id, anchor: .bottom)
                                    }
                                }
                            }
                        }
                    }
                    .frame(maxWidth: .infinity)
                }
            }
        }
        .onAppear {
            // Auto-connect if backend URL is available
            if !appState.backendURLString.isEmpty && !appState.meetingId.isEmpty {
                wsManager.connect(
                    backendURL: appState.backendURLString,
                    meetingId: appState.meetingId,
                    jwtToken: appState.jwtToken
                )
            }
        }
        .onDisappear {
            wsManager.disconnect()
        }
    }
}

// MARK: - Preview
struct TranscriptView_Previews: PreviewProvider {
    static var previews: some View {
        TranscriptView(appState: AppState())
            .frame(width: 800, height: 600)
    }
}
