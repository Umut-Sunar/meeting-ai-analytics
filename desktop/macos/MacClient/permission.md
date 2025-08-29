# macOS Screen Recording Permission Management

## 📋 Genel Bakış

macOS'ta Screen Recording izinleri, Apple'ın TCC (Transparency, Consent, and Control) sistemi tarafından yönetilir. Bu sistem, kullanıcı gizliliğini korumak için uygulamaların sistem kaynaklarına erişimini kontrol eder.

## 🔍 Mevcut Sorun Analizi

### Yaşanan Hata:
```
Screen recording permission check failed: Error Domain=com.apple.ScreenCaptureKit.SCStreamErrorDomain Code=-3801 
"Kullanıcı uygulama, pencere ve ekran resmi çekme için TCC'leri reddetti"
```

### Hata Kodu Anlamı:
- **-3801**: TCC (Transparency, Consent, and Control) tarafından erişim reddedildi
- Bu hata, uygulamanın Screen Recording iznine sahip olmadığını gösterir

## 🏗️ Bundle ID Yönetimi

### Mevcut Bundle ID Yapılandırması:

**Info.plist:**
```xml
<key>CFBundleIdentifier</key>
<string>com.meetingai.macclient</string>
```

**Xcode Project (project.pbxproj):**
```
PRODUCT_BUNDLE_IDENTIFIER = com.meetingai.macclient;
PRODUCT_NAME = MacClient;
```

### Bundle ID Tutarlılığı:
- ✅ **Info.plist**: `com.meetingai.macclient`
- ✅ **Xcode Project**: `com.meetingai.macclient`
- ✅ **PermissionManager**: `com.meetingai.macclient`
- ✅ **Scripts**: `com.meetingai.macclient`

## 🔧 Permission Management Kodları

### 1. PermissionManager.swift (Ana Sınıf)

```swift
class PermissionManager: ObservableObject {
    static let shared = PermissionManager()
    private let bundleID = "com.meetingai.macclient"
    
    // Screen Recording permission kontrolü
    func checkScreenRecordingPermission() -> Bool {
        if #available(macOS 11.0, *) {
            return SCScreenshotManager.captureSampleBuffer(
                contentFilter: SCContentFilter(),
                configuration: SCStreamConfiguration()
            ) != nil
        } else {
            return CGPreflightScreenCaptureAccess()
        }
    }
    
    // Permission talep etme
    func requestScreenRecordingPermission() {
        if #available(macOS 11.0, *) {
            // ScreenCaptureKit kullanımı otomatik olarak permission dialog açar
            Task {
                do {
                    let availableContent = try await SCShareableContent.excludingDesktopWindows(
                        false, onScreenWindowsOnly: true
                    )
                    // Bu çağrı permission dialog'unu tetikler
                } catch {
                    print("Permission request failed: \(error)")
                }
            }
        } else {
            // Eski macOS versiyonları için
            CGRequestScreenCaptureAccess()
        }
    }
}
```

### 2. PermissionsService.swift (Basitleştirilmiş Interface)

```swift
import ScreenCaptureKit

class PermissionsService {
    static func checkScreenRecordingPermission() -> Bool {
        return PermissionManager.shared.checkScreenRecordingPermission()
    }
    
    static func requestScreenRecordingPermission() {
        PermissionManager.shared.requestScreenRecordingPermission()
    }
}
```

### 3. SystemAudioCaptureSC.swift (Kullanım Yeri)

```swift
private func checkPermissions() -> Bool {
    // PermissionsService üzerinden kontrol
    let hasPermission = PermissionsService.checkScreenRecordingPermission()
    
    if !hasPermission {
        print("❌ Screen recording permission denied")
        PermissionsService.requestScreenRecordingPermission()
        return false
    }
    
    return true
}
```

## 🛠️ TCC Reset ve Temizleme Yöntemleri

### 1. Enhanced Permission Fix Script

**Konum:** `/Scripts/fix_screen_recording_permissions_enhanced.sh`

**Ana İşlevler:**
```bash
# TCC veritabanını reset etme
sudo tccutil reset ScreenCapture com.meetingai.macclient
sudo tccutil reset Microphone com.meetingai.macclient
sudo tccutil reset Camera com.meetingai.macclient

# TCC daemon'unu yeniden başlatma
sudo killall tccd

# Uygulama cache'lerini temizleme
rm -rf ~/Library/Caches/com.meetingai.macclient
rm -rf ~/Library/Saved\ Application\ State/com.meetingai.macclient.savedState

# Xcode DerivedData temizleme
rm -rf ~/Library/Developer/Xcode/DerivedData/MacClient-*
```

### 2. Manuel TCC Reset Komutları

```bash
# Tüm TCC izinlerini reset et
sudo tccutil reset All com.meetingai.macclient

# Sadece Screen Recording iznini reset et
sudo tccutil reset ScreenCapture com.meetingai.macclient

# TCC veritabanını kontrol et
sudo sqlite3 /Library/Application\ Support/com.apple.TCC/TCC.db \
"SELECT * FROM access WHERE client='com.meetingai.macclient';"
```

## 📱 App Bundle Yönetimi

### Sorunlu Durumlar:

1. **DerivedData'da Değişken Path:**
   ```
   ~/Library/Developer/Xcode/DerivedData/MacClient-[RANDOM]/Build/Products/Debug/MacClient.app
   ```
   - Her build'de farklı path
   - TCC bu path'i tanımıyor

2. **Applications Klasöründe Sabit Path:**
   ```
   /Applications/MacClient.app
   ```
   - Sabit path, TCC tarafından tanınır
   - Production deployment için ideal

### Çözüm Yaklaşımları:

**A) Archive ve Export (Önerilen):**
```bash
# Xcode'da Product → Archive
# Organizer'da Export → Development
# /Applications/'a kopyala
```

**B) Manual Copy:**
```bash
# Build sonrası DerivedData'dan kopyala
cp -R ~/Library/Developer/Xcode/DerivedData/MacClient-*/Build/Products/Debug/MacClient.app /Applications/
```

## 🔒 Entitlements ve Info.plist Yapılandırması

### Entitlements.plist:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <!-- Sandbox devre dışı (geliştirme için) -->
    <key>com.apple.security.app-sandbox</key>
    <false/>
    
    <!-- Audio ve Screen Recording izinleri -->
    <key>com.apple.security.device.audio-input</key>
    <true/>
    <key>com.apple.security.device.microphone</key>
    <true/>
    <key>com.apple.security.device.camera</key>
    <true/>
    
    <!-- Network erişimi -->
    <key>com.apple.security.network.client</key>
    <true/>
    
    <!-- JIT compilation -->
    <key>com.apple.security.cs.allow-jit</key>
    <true/>
    
    <!-- Apple Events -->
    <key>com.apple.security.automation.apple-events</key>
    <true/>
    
    <!-- TCC erişimi -->
    <key>com.apple.private.tcc.allow</key>
    <array>
        <string>kTCCServiceScreenCapture</string>
        <string>kTCCServiceMicrophone</string>
        <string>kTCCServiceCamera</string>
    </array>
    
    <!-- Library validation devre dışı -->
    <key>com.apple.security.cs.disable-library-validation</key>
    <true/>
</dict>
</plist>
```

### Info.plist:
```xml
<!-- Bundle Identifier -->
<key>CFBundleIdentifier</key>
<string>com.meetingai.macclient</string>

<!-- Bundle Name -->
<key>CFBundleName</key>
<string>MacClient</string>

<!-- Screen Recording açıklaması -->
<key>NSScreenCaptureDescription</key>
<string>This app needs screen recording permission to capture system audio for meeting transcription.</string>

<!-- Microphone açıklaması -->
<key>NSMicrophoneUsageDescription</key>
<string>This app needs microphone access to record audio for meeting transcription.</string>

<!-- App Transport Security (Development) -->
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSAllowsArbitraryLoads</key>
    <true/>
    <key>NSExceptionDomains</key>
    <dict>
        <key>localhost</key>
        <dict>
            <key>NSExceptionAllowsInsecureHTTPLoads</key>
            <true/>
            <key>NSExceptionMinimumTLSVersion</key>
            <string>TLSv1.0</string>
            <key>NSExceptionRequiresForwardSecrecy</key>
            <false/>
        </dict>
    </dict>
</dict>
```

## 🚨 Yaygın Sorunlar ve Çözümleri

### 1. "App Listede Görünmüyor"

**Sebep:** Bundle ID tutarsızlığı veya app path problemi

**Çözüm:**
```bash
# Bundle ID kontrolü
defaults read /Applications/MacClient.app/Contents/Info.plist CFBundleIdentifier

# TCC reset
sudo tccutil reset ScreenCapture com.meetingai.macclient

# App'i yeniden register et
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f /Applications/MacClient.app
```

### 2. "Permission Verildi Ama Hala Hata"

**Sebep:** TCC cache sorunu veya app signature problemi

**Çözüm:**
```bash
# TCC daemon restart
sudo killall tccd

# App cache temizle
rm -rf ~/Library/Caches/com.meetingai.macclient

# App'i yeniden başlat
killall MacClient
```

### 3. "İki Ayrı Uygulama Açılıyor"

**Sebep:** DerivedData ve Applications'da farklı versiyonlar

**Çözüm:**
```bash
# Applications'daki eski versiyonu sil
rm -rf /Applications/MacClient.app

# DerivedData'dan yeni kopyala
cp -R ~/Library/Developer/Xcode/DerivedData/MacClient-*/Build/Products/Debug/MacClient.app /Applications/

# TCC reset
sudo tccutil reset All com.meetingai.macclient
```

## 🔍 Debug ve Troubleshooting

### TCC Durumunu Kontrol Etme:

```bash
# TCC veritabanını sorgula
sudo sqlite3 /Library/Application\ Support/com.apple.TCC/TCC.db \
"SELECT service, client, allowed, prompt_count FROM access WHERE client LIKE '%macclient%';"

# System log'ları kontrol et
log show --predicate 'subsystem == "com.apple.TCC"' --info --last 1h

# App'in TCC durumunu kontrol et
tccutil list ScreenCapture
```

### Permission Test Kodu:

```swift
func testAllPermissions() {
    // Screen Recording
    let screenPermission = PermissionManager.shared.checkScreenRecordingPermission()
    print("Screen Recording: \(screenPermission ? "✅" : "❌")")
    
    // Microphone
    let micPermission = AVCaptureDevice.authorizationStatus(for: .audio) == .authorized
    print("Microphone: \(micPermission ? "✅" : "❌")")
    
    // Bundle ID kontrolü
    let bundleID = Bundle.main.bundleIdentifier ?? "Unknown"
    print("Bundle ID: \(bundleID)")
    
    // App path kontrolü
    let appPath = Bundle.main.bundlePath
    print("App Path: \(appPath)")
}
```

## 📋 Checklist: Permission Sorunlarını Çözme

### ✅ Temel Kontroller:
- [ ] Bundle ID tutarlılığı (`com.meetingai.macclient`)
- [ ] Info.plist'te doğru açıklamalar
- [ ] Entitlements.plist doğru yapılandırılmış
- [ ] App `/Applications/` klasöründe

### ✅ TCC Reset:
- [ ] `sudo tccutil reset ScreenCapture com.meetingai.macclient`
- [ ] `sudo killall tccd`
- [ ] App cache temizlendi
- [ ] Xcode DerivedData temizlendi

### ✅ System Settings:
- [ ] Privacy & Security → Screen Recording açık
- [ ] MacClient listede görünüyor
- [ ] Checkbox işaretli
- [ ] Sistem yeniden başlatıldı (gerekirse)

### ✅ Code Level:
- [ ] PermissionManager doğru bundle ID kullanıyor
- [ ] Permission check'ler main thread'de
- [ ] Error handling uygun
- [ ] Debug log'ları aktif

## 🎯 Son Çare Yöntemleri

Eğer tüm yöntemler başarısız olursa:

1. **Sistem Yeniden Başlatma**
2. **Safe Mode'da TCC Reset**
3. **Yeni Bundle ID ile Test**
4. **Apple Developer Account ile Code Signing**

## 📞 Destek ve Kaynaklar

- **Apple TCC Documentation**: [Apple Developer TCC Guide]
- **ScreenCaptureKit Documentation**: [Apple ScreenCaptureKit]
- **macOS Security Guide**: [Apple Security Documentation]

---

**Not:** Bu dokümantasyon, mevcut MacClient projesinin permission sorunlarını çözmek için hazırlanmıştır. Üretim ortamında code signing ve notarization gerekebilir.
