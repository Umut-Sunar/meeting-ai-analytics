# 🎯 Cursor Prompt: macOS İzin Yönetimi Birleştirme

## ROLE
Senior macOS engineer specializing in permissions, ScreenCaptureKit, and AVFoundation.

## GOAL
Mikrofon ve ekran kaydı (hoparlör/sistem sesi) izin akışını tek ve güvenilir bir mimaride topla. Kullanıcı "Kaydı Başlat" dediğinde izin yoksa otomatik yönlendir, izin varsa akışı başlat. Sequoia'nın haftalık yeniden onay gereksinimini ve development build/TCC önbellek sorunlarını ele al.

## 🚀 QUICK START
**Mevcut kod hazır!** Sadece entegrasyon gerekiyor:
1. `PermissionManager` → `AppState`'e ekle
2. UI butonlarını mevcut fonksiyonlara bağla  
3. Unified permission check flow oluştur

## 📁 KAPSAM / DOSYALAR

### Mevcut Dosyalar (Kullan/İyileştir):
- `PermissionsService.swift` — ✅ Hazır: `checkMicAuthorized()`, `hasScreenRecordingPermission()`, `openScreenRecordingPrefs()`
- `AudioAssist_V1_Sources/PermissionManager.swift` — ✅ Hazır: Sequoia/DerivedData/TCC logic, `requestPermissionWithGuidance()`, periyodik kontrol
- `SystemAudioCaptureSC.swift` — ✅ Mevcut: SCStream implementation, downmix/PCM çıkış
- `MicCapture.swift` — ✅ Mevcut: mikrofon capture logic
- `DesktopMainView.swift` — 🔄 Güncellenecek: UI butonları ve durum göstergeleri ekle
- `AppState.swift` — 🔄 Güncellenecek: izin durumları için @Published properties

## 🔧 YAPILACAK DEĞİŞİKLİKLER

### 1. 🎤 Mikrofon İzni – Tek Kapı
- `PermissionsService.checkMicAuthorized` zaten var; ilk launch'ta ve "Kaydı Başlat" aksiyonunda çağır
- `notDetermined` ise request edip sonucuna göre devam et (fonksiyon mevcut)
- `Info.plist`'te `NSMicrophoneUsageDescription` mesajı yoksa ekle

### 2. 🖥️ Ekran Kaydı İzni – Güvenilir Kontrol + Yönlendirme
- İzin kontrolü için **yalnızca** `SCShareableContent.current` tabanlı asenkron yolu kullan
- Mevcut `hasScreenRecordingPermission()` fonksiyonunu kullan
- İzin yoksa:
  - `PermissionsService.openScreenRecordingPrefs()` ile ayarları aç
  - Kullanıcıya "Ayarı açtık, onay sonrası uygulamayı yeniden başlatın" mesajını göster
- `SystemAudioCaptureSC.start()` zaten bu akışı yapıyor; tüm çağrıları bu tek kapıdan geçir
- **Başka yerlerde CGPreflight kullanma**

### 3. 🔄 Sequoia (macOS 15+) Haftalık Yenileme Uyarısı
- `PermissionManager` içindeki Sequoia rehberlik/uyarı log'larını UI'dan tetiklenebilir yap
- "İzinleri Kontrol Et" butonu ekle
- `lastSuccessfulCheck` 7 günü geçtiyse uyarı göster
- Periyodik kontrol timer'ı zaten var; `AppState`'e "son başarılı kontrol" bilgisini yaz

### 4. 🛠️ Development Build / TCC Cache (DerivedData) Akışı
- `PermissionManager`'daki development rehberliğini "Yardım" modaliyle sun
- "/Applications'a kopyalayın, fix_screen_recording_permissions.sh kullanın" metinleri hazır
- "Geliştirici Modunda İzinleri Onar" butonu ekle

### 5. 🎥 SystemAudioCaptureSC Stabilizasyonu
- `VideoOutputHandler`'i **her zaman** SCStream'e ekle (frame drop önleme için zorunlu)
- Start akışı sıralaması:
  1. İzin kontrolü → `SCShareableContent.current`
  2. Display seçimi → `SCContentFilter`
  3. `SCStreamConfiguration` (audio: 48k/2ch)
  4. Output'ları ekle → capture başlat
- Çıkışta downmix Int16 mono 48k (double-convert etme)
- Cihaz değişimlerinde otomatik yeniden başlatma aktif kalsın

### 6. 🖼️ UI / Durum Paneli (DesktopMainView.swift'te)
**Mevcut InMeetingView → GroupBox("Durum") içine ekle:**
```swift
HStack {
    Text("Mikrofon:")
    Spacer()
    Text(appState.isMicAuthorized ? "✅ Aktif" : "❌ İzin Yok")
}
HStack {
    Text("Sistem Sesi:")
    Spacer() 
    Text(appState.isScreenAuthorized ? "✅ Aktif" : "❌ İzin Yok")
}
```

**Yeni Butonlar (PreMeetingView → GroupBox("İzinler") içine):**
- "İzinleri Kontrol Et" → `permissionManager.checkPermissionStatus()`
- "Ekran Kaydı Ayarlarını Aç" → `PermissionsService.openScreenRecordingPrefs()`
- "Geliştirici Modunda İzinleri Onar" → `permissionManager.requestPermissionWithGuidance()`

### 7. 📝 Loglama
Mevcut log scrollview'ına (`statusLines`) tüm izin kararlarını tek formatta yaz:
```
[PERM] Mikrofon izni kontrol edildi: ✅
[SC] Ekran kaydı izni reddedildi, ayarlar açılıyor...
[MIC] Mikrofon capture başlatıldı
```

## ✅ KABUL KRİTERLERİ (Manual Test)

### İlk Açılış
- Mikrofon izni yoksa sistem prompt gelir
- İzin verince mikrofon kaydı başlayabilir

### "Kaydı Başlat" Akışı
- Ekran kaydı izni yoksa ayarlar açılır ve UI'da net uyarı görünür
- İzin verip app'i yeniden başlatınca "Sistem Sesi: ✅" olur

### Sequoia Haftalık Yenileme
- 7 günü geçmişse "yenileme uyarısı" çıkar
- "İzinleri Kontrol Et" butonu sonrası uyarı log'da görülür

### Development Build
- "Geliştirici Modunda İzinleri Onar" butonu rehberliği gösterir
- DerivedData/TCC senaryosu açıklanır

### SystemAudioCaptureSC Stabilite
- Frame drop sebebiyle hata log'u gelmez (VideoOutputHandler aktif)
- PCM çıkışı Int16 mono 48k olarak gider
- Deepgram/Backend tarafında sample rate uyumsuzluğu görülmez

## 🎯 COMMIT MESAJI
```
feat(permissions): unify mic+screen recording flow; Sequoia weekly renewal & TCC dev fixes; enforce VideoOutputHandler; robust UI actions/logs
```

## 📋 IMPLEMENTATION CHECKLIST

### Phase 1: Core Permission Logic
- [ ] Unify microphone permission flow in single entry point
- [ ] Implement reliable screen recording permission check (SCShareableContent only)
- [ ] Add permission status UI indicators

### Phase 2: Sequoia & Development Support
- [ ] Add weekly renewal warning system
- [ ] Implement development build TCC cache guidance
- [ ] Create "Developer Mode Permission Repair" button

### Phase 3: SystemAudioCaptureSC Hardening
- [ ] Enforce VideoOutputHandler for frame drop prevention
- [ ] Standardize Int16 mono 48k output pipeline
- [ ] Maintain device change auto-restart

### Phase 4: UI & UX Polish
- [ ] Add permission control buttons to main UI
- [ ] Implement structured logging format
- [ ] Create help modal for development scenarios

## 🔍 KEY TECHNICAL REQUIREMENTS

### Permission Architecture
- **Single Source of Truth**: All permission checks through designated entry points
- **Async/Await**: Use modern Swift concurrency for permission checks
- **Error Handling**: Graceful degradation with clear user messaging

### macOS Version Compatibility
- **Sequoia (15.0+)**: Handle weekly renewal requirements
- **Ventura/Sonoma (13.0-14.x)**: Standard permission flow
- **Development Builds**: Special TCC cache handling

### Audio Pipeline Integrity
- **Sample Rate**: Consistent 48kHz throughout pipeline
- **Format**: Int16 mono output to prevent conversion issues
- **Device Changes**: Automatic restart on audio device switching

---

## 🔧 MEVCUT KOD YAPISI (Referans)

### PermissionsService.swift (Hazır Fonksiyonlar):
```swift
// ✅ Kullan: Mikrofon izni kontrolü
static func checkMicAuthorized(completion: @escaping (Bool)->Void)

// ✅ Kullan: Ekran kaydı izni kontrolü (güvenilir)
@available(macOS 13.0, *)
static func hasScreenRecordingPermission() async -> Bool

// ✅ Kullan: Sistem ayarlarını aç
static func openScreenRecordingPrefs()
```

### PermissionManager.swift (Mevcut Özellikler):
```swift
// ✅ Hazır: Sequoia haftalık yenileme kontrolü
func getPermissionStatusInfo() -> PermissionStatusInfo {
    // needsWeeklyRenewal: Date().timeIntervalSince(lastSuccessfulCheck) > 604800
}

// ✅ Hazır: Development build rehberliği
func requestPermissionWithGuidance() async -> Bool {
    if isDevelopmentBuild {
        await showDevelopmentBuildGuidance()
    }
}

// ✅ Hazır: Periyodik kontrol (15 dakika)
private let permissionCheckInterval: TimeInterval = 900
```

### AppState.swift (Mevcut Properties):
```swift
// ✅ Mevcut: Temel izin durumları
@Published var isMicAuthorized: Bool = false
@Published var isScreenAuthorized: Bool = false
@Published var isCapturing: Bool = false

// 🔄 Eklenecek: PermissionManager entegrasyonu
@StateObject private var permissionManager = PermissionManager()
```

### DesktopMainView.swift (Mevcut UI Yapısı):
```swift
// ✅ Mevcut: Durum göstergesi (InMeetingView içinde)
GroupBox("Durum") {
    VStack(alignment: .leading, spacing: 8) {
        HStack {
            Text("Mikrofon:")
            Spacer()
            Text(appState.isMicAuthorized ? "✅ Aktif" : "❌ İzin Yok")
        }
        // 🔄 Sistem Sesi satırı zaten var, sadece güncelle
    }
}

// ✅ Mevcut: İzin butonları (PreMeetingView içinde)
GroupBox("İzinler") {
    VStack(spacing: 12) {
        HStack {
            Button("Mikrofon İzni Kontrol Et") { /* mevcut kod */ }
            // 🔄 Yeni butonlar buraya eklenecek
        }
    }
}
```

---

## 🎯 IMPLEMENTATION PRIORITY

### 🔥 HIGH PRIORITY (Hemen):
1. **PermissionManager'ı AppState'e entegre et**
2. **UI butonlarını PermissionManager fonksiyonlarına bağla**
3. **Unified permission check flow oluştur**

### ⚡ MEDIUM PRIORITY (Bu hafta):
4. **Sequoia haftalık yenileme uyarısı UI'da göster**
5. **Development build rehberliği modal ekle**
6. **SystemAudioCaptureSC VideoOutputHandler enforce et**

### 📋 LOW PRIORITY (Gelecek):
7. **Structured logging format standardize et**
8. **Periyodik kontrol timer'ını UI'da göster**

---

**🚀 READY TO IMPLEMENT**: Copy this prompt to Cursor and start with Phase 1!
