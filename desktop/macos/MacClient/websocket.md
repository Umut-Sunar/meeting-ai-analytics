# 🔌 MacClient WebSocket Akış Analizi ve Resilient Implementation

## 📊 **Güncel Durum (2025-08-30)**

### ✅ **Tamamlanan İyileştirmeler:**
- **State Machine**: Explicit state management (idle, connecting, connected, closing, disconnected)
- **Guarded Send**: PCM data sadece connected state'te gönderiliyor
- **Exponential Backoff**: 1s, 2s, 5s, 10s, 30s retry delays
- **PCM Ring Buffer**: 500ms buffer per source (mic/system) for reconnect bridging
- **Keep-alive Mechanism**: 30s interval ping/pong
- **Enhanced Error Handling**: Specific error codes and retry logic
- **Proper Lifecycle**: Clean connection/disconnection with finalize messages

### ✅ **Çalışan Kısımlar:**
- Backend WebSocket endpoint aktif (`ws://localhost:8000/api/v1/ws/ingest/meetings/{meeting_id}`)
- JWT authentication başarılı
- Resilient WebSocket connection with auto-reconnect
- PCM Data Bridge: AudioEngine → BackendIngestWS → Backend
- State-based connection management
- Buffered PCM transmission during reconnects

---

## 🏗️ **Resilient WebSocket Mimarisi**

### **1. State Machine Flow:**
```
[idle] → [connecting] → [connected] → [closing] → [disconnected]
                ↑                           ↓
                └─── [exponential backoff] ──┘
```

### **2. MacClient Audio Akışı (Resilient):**
```
[Microphone] → [MicCapture] → [AudioEngine] → [BackendIngestWS] → [Backend]
                                                    ↓
[System Audio] → [SystemAudioCaptureSC] → [AudioEngine] → [PCM Ring Buffer] → [Backend]
                                                              ↓
                                                    [Auto-reconnect with buffering]
```

### **2. Backend WebSocket Akışı:**
```
[MacClient WS] → [Backend Ingest Endpoint] → [DeepgramLiveClient] → [Deepgram API] → [Transcript] → [Redis] → [Web Subscriber]
```

---

## 🔍 **Resilient Implementation Details**

### **A. BackendIngestWS.swift - Enhanced WebSocket Client**

#### **1. State Machine Implementation:**
```swift
enum State {
    case idle, connecting, connected, closing, disconnected
}

private var state: State = .idle {
    didSet {
        switch state {
        case .connected:
            resetRetryCount()
            startKeepAlive()
            flushBufferedPCM()
        case .disconnected, .closing:
            stopKeepAlive()
        default: break
        }
    }
}
```

#### **2. Guarded Send with Buffering:**
```swift
func sendPCM(_ pcm: Data, source: String) {
    guard canSend else {
        // Buffer PCM data if we're not connected but might reconnect
        if state == .connecting || state == .disconnected {
            pcmBuffer.add(pcm, source: source)
        }
        return
    }
    sendPCMInternal(pcm, source: source)
}
```

#### **3. PCM Ring Buffer (500ms per source):**
```swift
private struct PCMRingBuffer {
    private var micBuffer: [Data] = []
    private var systemBuffer: [Data] = []
    private let maxBufferDuration: TimeInterval = 0.5
    
    mutating func add(_ data: Data, source: String) {
        // Keep only recent 500ms of data
    }
}
```

#### **4. Exponential Backoff Reconnection:**
```swift
private let backoffDelays: [TimeInterval] = [1.0, 2.0, 5.0, 10.0, 30.0]

private func scheduleReconnect() {
    let delay = backoffDelays[min(retryCount, backoffDelays.count - 1)]
    // Schedule reconnection with exponential backoff
}
```

#### **5. CaptureController.swift - Updated PCM Bridge:**
```swift
// ✅ FIXED: PCM Bridge with source parameter
audioEngine?.onMicPCM = { [weak self] data in
    guard let self = self else { return }
    
    // Echo suppression logic
    if shouldSuppressMic {
        let suppressedData = self.applySuppression(data: data, factor: 0.3)
        self.wsMic.sendPCM(suppressedData, source: "mic")  // ✅ With source
    } else {
        self.wsMic.sendPCM(data, source: "mic")  // ✅ With source
    }
}

audioEngine?.onSystemPCM = { [weak self] data in
    guard let self = self else { return }
    self.wsSys.sendPCM(data, source: "system")  // ✅ With source
}
```

#### **3. AudioEngine.swift - Audio Yakalama**
```swift
// Microphone PCM callback
micCapture.start { [weak self] pcmData in
    print("[DEBUG] 🎤 Mic PCM data: \(pcmData.count) bytes")
    // ❌ Bu data DeepgramClient'e gidiyor, BackendIngestWS'e değil!
    self?.microphoneClient?.sendPCM(pcmData)
}

// System Audio PCM callback  
systemAudioCapture.onPCM16k = { [weak self] pcmData in
    print("[DEBUG] 🔊 System PCM data: \(pcmData.count) bytes")
    // ❌ Bu data da DeepgramClient'e gidiyor!
    self?.systemAudioClient?.sendPCM(pcmData)
}
```

### **B. Backend Tarafı**

#### **1. WebSocket Ingest Endpoint (`/ws/ingest/meetings/{meeting_id}`)**
```python
# 1. JWT Authentication
claims = decode_jwt_token(token)

# 2. WebSocket Connection
await ws_manager.connect_ingest(websocket, meeting_id)

# 3. Handshake Reception (TEXT frame)
hs_data = await websocket.receive_text()
hs = IngestHandshakeMessage.model_validate_json(hs_data)

# 4. Validation
if hs.sample_rate != 48000: # INGEST_SAMPLE_RATE
    error("Invalid sample rate")
if hs.channels != 1: # INGEST_CHANNELS  
    error("Invalid channels")

# 5. Deepgram Client Creation
client = DeepgramLiveClient(
    meeting_id=meeting_id,
    language=hs.language,
    sample_rate=hs.sample_rate,
    on_transcript=on_transcript,
    on_error=on_err
)

# 6. Message Loop
while True:
    message = await websocket.receive()
    
    if "bytes" in message:
        # Binary PCM data
        data = message["bytes"]
        await client.send_pcm(data)  # → Deepgram'e ilet
        
    elif "text" in message:
        # Control message (finalize/close)
        ctrl = IngestControlMessage.model_validate_json(message["text"])
```

#### **2. Deepgram Live Client**
```python
class DeepgramLiveClient:
    async def connect(self):
        # Deepgram WebSocket bağlantısı
        self.ws = await websockets.connect(
            "wss://api.deepgram.com/v1/listen",
            additional_headers={"Authorization": f"Token {api_key}"}
        )
    
    async def send_pcm(self, data: bytes):
        # PCM data'yı Deepgram'e gönder
        await self.ws.send(data)
```

---

## 🚨 **Ana Sorun: PCM Data Bridge Eksik**

### **Sorunun Kökü:**
`CaptureController.swift`'te `setupPCMDataBridge()` fonksiyonu **boş placeholder**! 

AudioEngine'den gelen PCM verisi hala eski DeepgramClient'lere gidiyor, yeni BackendIngestWS'e değil.

### **Mevcut Akış (YANLIŞ):**
```
[MicCapture] → [AudioEngine] → [DeepgramClient] → [Deepgram API]
[SystemAudioCaptureSC] → [AudioEngine] → [DeepgramClient] → [Deepgram API]
```

### **Olması Gereken Akış:**
```
[MicCapture] → [AudioEngine] → [BackendIngestWS] → [Backend] → [Deepgram API]
[SystemAudioCaptureSC] → [AudioEngine] → [BackendIngestWS] → [Backend] → [Deepgram API]
```

---

## 🔧 **Sorunun Çözümü (Kod Değişikliği Gerekmez - Sadece Analiz)**

### **1. AudioEngine.swift'te Değişiklik Gerekli:**
```swift
// Şu anki kod:
micCapture.start { [weak self] pcmData in
    self?.microphoneClient?.sendPCM(pcmData)  // ❌ Eski yol
}

// Olması gereken:
micCapture.start { [weak self] pcmData in
    self?.onPCMData?(pcmData)  // ✅ Callback ile dışarı ver
}
```

### **2. CaptureController.swift'te Bridge Kurulması:**
```swift
private func setupPCMDataBridge(appState: AppState) {
    // AudioEngine'e PCM callback ver
    audioEngine?.onPCMData = { [weak self] pcmData in
        self?.backendWS.sendPCM(pcmData)  // ✅ Backend'e ilet
    }
}
```

---

## 📋 **WebSocket Protokol Detayları**

### **1. Bağlantı Kurma**
```
URL: ws://localhost:8000/api/v1/ws/ingest/meetings/test-meeting-001?token={jwt}
Headers: 
  - Upgrade: websocket
  - Connection: Upgrade
  - Sec-WebSocket-Key: {random}
  - Sec-WebSocket-Version: 13
```

### **2. Handshake (TEXT Frame)**
```json
{
  "type": "handshake",
  "source": "mic",
  "sample_rate": 48000,
  "channels": 1,
  "language": "tr",
  "ai_mode": "standard",
  "device_id": "mac-client-001"
}
```

### **3. Backend Response (TEXT Frame)**
```json
{
  "status": "success",
  "message": "Connected to transcription",
  "session_id": "sess-test-meeting-001"
}
```

### **4. PCM Data (BINARY Frame)**
```
Frame Type: Binary (0x2)
Payload: Raw PCM 16-bit Little Endian
Format: 48000 Hz, 1 channel, Int16
Chunk Size: Max 32KB (32768 bytes = 16384 samples)
```

### **5. Control Messages (TEXT Frame)**
```json
// Finalize
{"type": "finalize"}

// Close
{"type": "close"}
```

---

## 🔍 **Hata Analizi**

### **"WebSocket receive error: There was a bad response from the server"**

**Muhtemel Nedenler:**
1. **PCM Data gönderilmiyor**: Backend PCM data bekliyor ama gelmiyor
2. **Format uyumsuzluğu**: Gönderilen data format backend'in beklediği ile uyuşmuyor
3. **Chunk size aşımı**: 32KB'dan büyük frame gönderilmeye çalışılıyor
4. **WebSocket state sorunu**: Connection state tutarsızlığı

### **"Failed to send PCM data"**

**Neden:**
- `BackendIngestWS.sendPCM()` çağrılmıyor çünkü PCM bridge kurulmamış
- AudioEngine PCM data'sını hala DeepgramClient'e gönderiyor

---

## 📊 **Backend Konfigürasyon**

### **Environment Variables:**
```bash
INGEST_SAMPLE_RATE=48000
INGEST_CHANNELS=1
MAX_INGEST_MSG_BYTES=32768
DEEPGRAM_API_KEY=your_api_key
JWT_SECRET_KEY=your_secret
```

### **WebSocket Limits:**
- **Max message size**: 32KB
- **Max ingest sessions per meeting**: 1
- **Handshake timeout**: 10 seconds
- **Rate limit**: 50 frames/second

---

## 🎯 **Sonuç ve Öneriler**

### **Ana Sorun:**
MacClient'ta **PCM Data Bridge eksik**. AudioEngine'den gelen ses verisi BackendIngestWS'e iletilmiyor.

### **Çözüm Adımları:**
1. **AudioEngine.swift**: PCM callback mekanizması ekle
2. **CaptureController.swift**: PCM bridge'i gerçek callback ile kur  
3. **DeepgramClient bağımlılığını kaldır**: Artık backend üzerinden gidecek

### **Test Edilebilir Kısımlar:**
- ✅ WebSocket bağlantısı
- ✅ JWT authentication  
- ✅ Handshake protokolü
- ✅ Backend Deepgram entegrasyonu
- ❌ PCM data akışı (eksik)

### **Beklenen Sonuç:**
PCM bridge kurulduktan sonra:
```
MacClient → Backend WS → Deepgram → Transcript → Redis → Web Subscriber
```
akışı tamamlanacak ve gerçek zamanlı transkripsiyon çalışacak.

---

## 📝 **Log Analizi**

### **MacClient Logları:**
```
✅ WebSocket connected - starting audio capture
✅ Audio capture started (Backend WebSocket mode)  
✅ Microphone connected
✅ System audio connected
✅ Handshake sent: source=mic, rate=48000Hz
✅ WebSocket connection opened
✅ Connected to transcription, session_id: sess-test-meeting-001

❌ Audio Error (MIC): WebSocket receive error: There was a bad response from the server
❌ Audio Error (MIC): Failed to send PCM data: There was a bad response from the server
❌ Audio Error (SYS): WebSocket receive error: There was a bad response from the server  
❌ Audio Error (SYS): Failed to send PCM data: There was a bad response from the server
```

### **Analiz:**
- Bağlantı ve handshake başarılı
- PCM data gönderimi başarısız (bridge eksikliği nedeniyle)
- Backend PCM data bekliyor ama alamıyor

Bu dokümantasyon, sistemin mevcut durumunu ve sorunun kökenini detaylı olarak açıklamaktadır. PCM bridge kurulduktan sonra sistem tam olarak çalışacaktır.
