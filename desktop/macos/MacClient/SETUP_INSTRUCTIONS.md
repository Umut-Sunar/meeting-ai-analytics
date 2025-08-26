# MacClient Kurulum Talimatları

## ✅ Çözüm: "not applicable" Hatası

AudioAssist_V1 projesi bir **app target** olduğu için framework olarak linklenemez. Bu sorunu çözmek için **kaynak kodları doğrudan MacClient projesine dahil ettik**.

## 🚀 Kurulum Adımları

### 1. Xcode'da Projeyi Aç
```bash
cd /Users/doganumutsunar/analytics-system
open desktop/macos/MacClient/MacClient.xcodeproj
```

### 2. Proje Yapısını Kontrol Et
Xcode Project Navigator'da şu yapıyı görmelisiniz:

```
MacClient/
├── App.swift
├── AppState.swift
├── PermissionsService.swift
├── CaptureController.swift
├── DesktopMainView.swift
├── AudioAssist_V1_Sources/          # ✅ AudioAssist_V1 kaynak kodları
│   ├── AudioEngine.swift
│   ├── DeepgramClient.swift
│   ├── LanguageManager.swift
│   ├── MicCapture.swift
│   ├── SystemAudioCaptureSC.swift
│   ├── AudioSourceType.swift
│   ├── PermissionManager.swift
│   ├── APIKeyManager.swift
│   └── Resampler.swift
└── Resources/
    ├── Info.plist
    └── Entitlements.plist
```

### 3. Build & Run
1. **Target Seçimi**: MacClient target'ını seç
2. **Build**: ⌘+B ile projeyi derle
3. **Run**: ⌘+R ile uygulamayı çalıştır

## 🔧 Özellikler

### ✅ Artık Çalışan:
- **AudioEngine**: Mikrofon ve sistem sesi yakalama
- **DeepgramClient**: Real-time transkripsiyon
- **LanguageManager**: Türkçe/İngilizce dil desteği
- **Permission Management**: Mikrofon ve ekran kaydı izinleri
- **Real-time UI Updates**: Canlı transkript görüntüleme

### 🎯 Test Senaryosu:
1. **Uygulama Başlat**: MacClient.app çalıştır
2. **İzin Ver**: Mikrofon izni ver
3. **Toplantı Kur**: Meeting ID, Device ID, dil ayarla
4. **Toplantı Başlat**: "Toplantıyı Başlat" butonuna tıkla
5. **Kayıt Başlat**: "Başlat" butonu ile ses yakalamayı başlat
6. **Transkript Gör**: Real-time transkriptleri sağ panelde gör
7. **Logları Takip Et**: Sol panelde Deepgram bağlantı loglarını izle

## 🔑 API Key Konfigürasyonu

AudioAssist_V1'deki API key yönetimi kullanılır:

### Yöntem 1: Environment Variable
```bash
export DEEPGRAM_API_KEY="b284403be6755d63a0c2dc440464773186b10cea"
```

### Yöntem 2: .env Dosyası
```bash
echo "DEEPGRAM_API_KEY=b284403be6755d63a0c2dc440464773186b10cea" > .env
```

### Yöntem 3: Info.plist (Geliştirme için)
AudioAssist_V1 projesindeki Info.plist'e ekle:
```xml
<key>DEEPGRAM_API_KEY</key>
<string>b284403be6755d63a0c2dc440464773186b10cea</string>
```

## 🐛 Sorun Giderme

### Build Error: "Cannot find 'AudioEngine' in scope"
**Çözüm**: Xcode'da Clean Build Folder (⌘+Shift+K) yap, sonra tekrar build et.

### Permission Error: Mikrofon erişimi reddedildi
**Çözüm**: 
1. System Preferences → Security & Privacy → Microphone
2. MacClient uygulamasını listede bul ve işaretle

### Deepgram Connection Error
**Çözüm**:
1. API key'in doğru ayarlandığını kontrol et
2. Network bağlantısını test et
3. Logları kontrol et: "🔗 Connecting to: wss://api.deepgram.com..."

### Screen Recording Permission
**Çözüm**:
1. System Preferences → Security & Privacy → Screen Recording  
2. MacClient'ı manuel olarak ekle
3. Uygulamayı restart et

## 📊 Beklenen Log Çıktısı

Başarılı çalıştırma durumunda şu logları göreceksiniz:

```
[10:30:15] 🚀 Start requested
[10:30:15] 🌍 Dil ayarlandı: Türkçe
[10:30:16] 🔗 Connecting to: wss://api.deepgram.com/v1/listen?...
[10:30:16] 🎤 Mikrofon bağlandı
[10:30:16] 🔊 Sistem sesi bağlandı
[10:30:16] ✅ Capture started.
[10:30:17] 📝 Partial (mic): Merhaba
[10:30:18] 📝 Final (mic): Merhaba, bu bir test.
```

## 🎉 Başarı!

Bu adımları takip ettikten sonra:
- ✅ "not applicable" hatası çözüldü
- ✅ AudioAssist_V1 çekirdeği entegre edildi  
- ✅ Native macOS uygulaması çalışıyor
- ✅ Real-time Deepgram transkripsiyon aktif
- ✅ Web UI paritesi sağlandı

**MacClient artık tam işlevsel!** 🚀
