# MacClient - Native macOS MeetingAI Desktop

Bu proje, web/components/DesktopAppView.tsx ile UI paritesi sağlayan native macOS uygulamasıdır.

## Özellikler

- **Native SwiftUI UI**: Web versiyonu ile aynı davranış ve tasarım
- **AudioAssist_V1 Entegrasyonu**: Mevcut Deepgram çekirdeği kullanılır
- **Real-time Transcript**: Canlı transkript görüntüleme
- **Permission Management**: Mikrofon ve ekran kaydı izinleri
- **Multi-language Support**: Türkçe ve İngilizce desteği

## Gereksinimler

- macOS 13.0+
- Xcode 15.0+
- AudioAssist_V1 subproject (dahil edilmiş)

## Kurulum

1. **Xcode'da Projeyi Aç**:
   ```bash
   open desktop/macos/MacClient/MacClient.xcodeproj
   ```

2. **AudioAssist_V1 Subproject Ekle**:
   - Project Navigator'da sağ tık → "Add Files to 'MacClient'..."
   - `desktop/macos/AudioAssist_V1/AudioAssist/AudioAssist.xcodeproj` dosyasını seç
   - "Add to target" seçeneğini işaretle

3. **Framework Linkle**:
   - MacClient target → General → Frameworks, Libraries, and Embedded Content
   - "+" → AudioAssist_V1 framework'ünü ekle
   - "Embed & Sign" seç

4. **Build Dependencies**:
   - MacClient target → Build Phases → Target Dependencies
   - AudioAssist_V1 target'ını ekle

## Kullanım

### Pre-Meeting Kurulum
1. Meeting ID ve Device ID gir
2. Dil seçimi yap (tr/en/auto)
3. AI Mode seç (standard/super)
4. Mikrofon ve sistem sesi kaynaklarını aktifleştir
5. İzinleri kontrol et
6. "Toplantıyı Başlat" butonuna tıkla

### In-Meeting
1. "Başlat" butonu ile kayıt başlat
2. Real-time transkriptleri görüntüle
3. Logları takip et
4. "Durdur" ile kayıt durdur
5. "Toplantıyı Bitir" ile ana ekrana dön

## Kod Yapısı

```
MacClient/
├── App.swift                 # Main app entry point
├── AppState.swift           # Global state management
├── PermissionsService.swift # Permission handling
├── CaptureController.swift  # AudioAssist_V1 bridge
├── DesktopMainView.swift    # Main UI components
└── Resources/
    ├── Info.plist          # App configuration
    ├── Entitlements.plist  # Security permissions
    └── Assets.xcassets/    # App icons and colors
```

## AudioAssist_V1 Entegrasyonu

CaptureController, AudioAssist_V1 çekirdeği ile köprü görevi görür:

```swift
// Language configuration
languageManager.selectedLanguage = .turkish/.english
let config = languageManager.getDeepgramConfig()

// AudioEngine initialization
audioEngine = AudioEngine(config: config)
audioEngine?.onEvent = handleAudioEngineEvent
audioEngine?.start()
```

## UI Parity

Web DesktopAppView.tsx ile tam uyumluluk:
- Aynı form alanları ve validasyonlar
- Aynı durum geçişleri (pre-meeting ↔ in-meeting)
- Aynı transcript görüntüleme
- Aynı permission handling

Detaylar için: `docs/ui/desktop/README_UI_PARITY.md`

## Test

1. **Build & Run**: Xcode'da ⌘+R
2. **Permission Test**: Mikrofon ve ekran kaydı izinlerini kontrol et
3. **Deepgram Test**: AudioAssist_V1 API key'i ile bağlantı test et
4. **Transcript Test**: Real-time transkript akışını doğrula

## Sorun Giderme

### AudioAssist_V1 Import Hatası
```swift
#if canImport(AudioAssist_V1)
import AudioAssist_V1
#endif
```
Subproject doğru linklenene kadar mock mode çalışır.

### Permission Hatası
- System Preferences → Security & Privacy → Microphone/Screen Recording
- MacClient uygulamasını manuel olarak ekle

### Deepgram Bağlantı Hatası
- AudioAssist_V1 projesindeki API key'i kontrol et
- Network bağlantısını doğrula

## Geliştirme

Bu proje AudioAssist_V1'in mevcut Deepgram konfigürasyonunu kullanır:
- 48kHz sample rate
- nova-2 model (Türkçe için)
- Real-time interim results
- Speaker diarization

Yeni özellikler eklerken web parity'sini koruyun.
