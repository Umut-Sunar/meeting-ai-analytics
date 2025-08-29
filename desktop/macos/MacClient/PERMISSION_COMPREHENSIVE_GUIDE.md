# 🔒 MacClient Ekran Kaydı İzni Kapsamlı Rehberi

## 📋 Genel Bakış

Bu rehber, MacClient uygulamasında yaşanan ekran kaydı izni sorunlarını ve çözümlerini detaylı olarak açıklar. macOS'ta Screen Recording izinleri, Apple'ın TCC (Transparency, Consent, and Control) sistemi tarafından yönetilir.

## 🚨 Yaşanan Ana Sorunlar

### 1. Build Sonrası İzin Kaybı
- **Problem**: Uygulamayı build ettiğimde bir önceki izni görmüyor
- **Durum**: Sistem ayarlarında MacClient isminde bir izin olmasına rağmen önyüzde izin yok gözüküyor
- **Root Cause**: Xcode development build'lerinde bundle path sürekli değişiyor

### 2. Otomatik İzin Ekleme Sorunu
- **Problem**: İzni silip, bilgisayarı kapatıp açıp, tekrar uygulamayı run ettiğimde ekran izni kaydı butonuna bastığımda izni sistem ayarlarına otomatik olarak getirmiyor
- **Root Cause**: TCC cache sorunları ve permission request mekanizmasının doğru çalışmaması

## 🏗️ Teknik Mimari ve Kod Yapısı

### 1. Ana İzin Yönetimi Sınıfları

#### PermissionManager.swift (Ana Sınıf)
```swift
@available(macOS 13.0, *)
@MainActor
class PermissionManager: ObservableObject {
    
    // Bundle bilgileri
    private let bundleID: String
    private let bundlePath: String
    private let executablePath: String
    private let isDevelopmentBuild: Bool
    private let isSequoiaOrLater: Bool
    
    // İzin durumu
    @Published var hasScreenRecordingPermission = false
    @Published var lastPermissionCheck = Date()
    @Published var permissionCheckInProgress = false
    
    // Periyodik kontrol
    private let permissionCheckInterval: TimeInterval = 900 // 15 dakika
    private var permissionTimer: Timer?
    private var lastSuccessfulCheck = Date.distantPast
}
```

#### PermissionsService.swift (Basitleştirilmiş Interface)
```swift
enum PermissionsService {
    /// En güvenilir ön-kontrol: sistemde izin açık mı?
    static func hasScreenRecordingPermission() -> Bool {
        CGPreflightScreenCaptureAccess()
    }
    
    /// İzni isteme (kabul edilse dahi genellikle uygulamayı yeniden başlatmak gerekir)
    @discardableResult
    static func requestScreenRecordingPermission() -> Bool {
        CGRequestScreenCaptureAccess()
    }
    
    /// System Settings'i aç
    static func openScreenRecordingPrefs() {
        if let url = URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture") {
            NSWorkspace.shared.open(url)
        }
    }
}
```

#### SystemAudioCaptureSC.swift (Kullanım Yeri)
```swift
@available(macOS 13.0, *)
final class SystemAudioCaptureSC: NSObject, SCStreamOutput, SCStreamDelegate {
    
    /// Get current permission status using PermissionsService
    func hasPermission() -> Bool {
        return PermissionsService.hasScreenRecordingPermission()
    }
    
    /// Request permission using PermissionsService
    func requestPermission() -> Bool {
        return PermissionsService.requestScreenRecordingPermission()
    }
    
    func start() async throws {
        // 1) Ön-kontrol
        guard PermissionsService.hasScreenRecordingPermission() else {
            print("[SC] ❌ Screen Recording OFF – opening System Settings")
            PermissionsService.openScreenRecordingPrefs()
            throw NSError(
                domain: "SC", code: -3,
                userInfo: [NSLocalizedDescriptionKey:
                    "Screen recording permission required. System Settings opened. " +
                    "After granting, QUIT the app completely and relaunch."]
            )
        }
        
        // 2) SCShareableContent ile izin kontrolü
        let content = try await SCShareableContent.current
        
        // 3) SCStream oluşturma ve başlatma
        // ... stream creation code
    }
}
```

### 2. Info.plist Yapılandırması

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <!-- Bundle Identifier -->
    <key>CFBundleIdentifier</key>
    <string>com.meetingai.macclient</string>
    
    <!-- Screen Recording Permission Description -->
    <key>NSScreenCaptureDescription</key>
    <string>MacClient needs screen recording permission to capture system audio for meeting transcription.</string>
    
    <!-- Microphone Permission Description -->
    <key>NSMicrophoneUsageDescription</key>
    <string>Mikrofonu toplantı asistanı için kullanacağız.</string>
    
    <!-- Audio Capture Permission Description -->
    <key>NSAudioCaptureUsageDescription</key>
    <string>Sistem sesini toplantı asistanı için yakalayacağız.</string>
    
    <!-- Minimum macOS Version -->
    <key>LSMinimumSystemVersion</key>
    <string>13.0</string>
</dict>
</plist>
```

### 3. Xcode Project Yapılandırması

```bash
# project.pbxproj içinde olması gerekenler:
PRODUCT_BUNDLE_IDENTIFIER = com.meetingai.macclient;
PRODUCT_NAME = MacClient;
DEVELOPMENT_TEAM = [YOUR_TEAM_ID];
CODE_SIGN_STYLE = Automatic;
```

## 🔍 İzin Kontrol Mekanizmaları

### 1. CGPreflightScreenCaptureAccess() - Hızlı Kontrol
```swift
// ✅ Hızlı ama güvenilir olmayan kontrol
let hasPermission = CGPreflightScreenCaptureAccess()
```
**Avantajlar**: Hızlı, senkron
**Dezavantajlar**: TCC cache'e bağımlı, eski veri döndürebilir

### 2. SCShareableContent.current - Güvenilir Kontrol
```swift
// ✅ En güvenilir kontrol yöntemi
do {
    let content = try await SCShareableContent.current
    let hasDisplays = !content.displays.isEmpty
    return hasDisplays
} catch {
    // İzin yok veya başka bir hata
    return false
}
```
**Avantajlar**: Gerçek zamanlı, güvenilir
**Dezavantajlar**: Asenkron, biraz yavaş

### 3. SCStream Test - Kesin Kontrol
```swift
// ✅ En kesin kontrol: Gerçek SCStream oluşturma testi
private func performRealSCStreamPermissionTest() async -> Bool {
    do {
        let content = try await SCShareableContent.current
        guard let display = content.displays.first else { return false }
        
        let filter = SCContentFilter(display: display, excludingApplications: [], exceptingWindows: [])
        let config = SCStreamConfiguration()
        config.capturesAudio = true
        
        let testStream = SCStream(filter: filter, configuration: config, delegate: nil)
        try testStream.addStreamOutput(TestStreamOutput(), type: .audio, sampleHandlerQueue: testQueue)
        
        return true
    } catch {
        return false
    }
}
```

## 🚨 Sorun Analizi ve Çözümler

### 1. Development Build İzin Kaybı Sorunu

#### Root Cause
```bash
# Her Xcode build'inde uygulama farklı path'e gidiyor:
~/Library/Developer/Xcode/DerivedData/MacClient-abc123/Build/Products/Debug/MacClient.app
~/Library/Developer/Xcode/DerivedData/MacClient-def456/Build/Products/Debug/MacClient.app
~/Library/Developer/Xcode/DerivedData/MacClient-ghi789/Build/Products/Debug/MacClient.app
```

#### Çözüm 1: Stable Location Kullanımı
```bash
# 1. Uygulamayı /Applications'a kopyala
sudo cp -R ~/Library/Developer/Xcode/DerivedData/MacClient-*/Build/Products/Debug/MacClient.app /Applications/

# 2. Quarantine flag'i kaldır
sudo xattr -dr com.apple.quarantine /Applications/MacClient.app

# 3. Launch Services'i yenile
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f /Applications/MacClient.app
```

#### Çözüm 2: Archive & Export
1. **Xcode → Product → Archive**
2. **Window → Organizer**
3. **"Distribute App" → "Copy App"**
4. **Applications klasörüne kaydet**

### 2. TCC Cache Sorunları

#### TCC Database Temizleme
```bash
# 1. TCC entries'leri temizle
sudo tccutil reset ScreenCapture com.meetingai.macclient
sudo tccutil reset Microphone com.meetingai.macclient
sudo tccutil reset All com.meetingai.macclient

# 2. TCC daemon'ı yeniden başlat
sudo killall tccd

# 3. Dock'u yeniden başlat (TCC refresh için)
killall Dock
```

#### Otomatik TCC Reset Script
```bash
#!/bin/bash
echo "🚨 AUTOMATIC TCC RESET FOR MACCLIENT"

# Bundle identifier
BUNDLE_ID="com.meetingai.macclient"

# TCC entries'leri temizle
sqlite3 ~/Library/Application\ Support/com.apple.TCC/TCC.db "DELETE FROM access WHERE client='$BUNDLE_ID';" 2>/dev/null || true

# Permission cache'i temizle
rm -rf ~/Library/Caches/com.apple.TCC/* 2>/dev/null || true

# Dock'u yeniden başlat
killall Dock 2>/dev/null || true

echo "✅ TCC reset completed"
```

### 3. Permission Request Mekanizması

#### Gelişmiş İzin İsteme
```swift
func requestPermissionWithGuidance() async -> Bool {
    // 1. macOS versiyonuna göre rehberlik
    if isSequoiaOrLater {
        await showSequoiaPermissionGuidance()
    }
    
    // 2. Development build için özel strateji
    if isDevelopmentBuild {
        await showDevelopmentBuildGuidance()
    }
    
    // 3. Gelişmiş izin isteği
    let granted = await performEnhancedPermissionRequest()
    
    // 4. Sonuç kontrolü
    hasScreenRecordingPermission = granted
    lastPermissionCheck = Date()
    
    return granted
}
```

#### Development Build İzin Stratejisi
```swift
private func performDevelopmentBuildPermissionRequest() async -> Bool {
    // Multiple attempts with progressive delays
    for attempt in 1...5 {
        print("[PermissionManager] 🔒 Development permission attempt \(attempt)/5...")
        
        let granted = CGRequestScreenCaptureAccess()
        
        // Immediate check
        let immediateStatus = await performEnhancedPermissionCheck()
        if immediateStatus { return true }
        
        // Progressive wait times
        let waitTime = UInt64(attempt * 300_000_000) // 0.3s, 0.6s, 0.9s, etc.
        try? await Task.sleep(nanoseconds: waitTime)
        
        // Delayed check
        let delayedStatus = await performEnhancedPermissionCheck()
        if delayedStatus { return true }
    }
    
    return false
}
```

## 🔧 Otomatik Çözüm Scriptleri

### 1. fix_all_permissions.sh
```bash
#!/bin/bash
echo "🔧 MacClient TCC Permission Auto-Fix Script"

# DerivedData'dan app'i bulup kopyala
DERIVED_APP=$(find ~/Library/Developer/Xcode/DerivedData -name "MacClient.app" -type d 2>/dev/null | head -1)
if [ -n "$DERIVED_APP" ]; then
    sudo rm -rf /Applications/MacClient.app
    sudo cp -R "$DERIVED_APP" /Applications/
    sudo chown -R $(whoami):staff /Applications/MacClient.app
fi

# TCC permissions'ı sıfırla
sudo tccutil reset ScreenCapture com.meetingai.macclient
sudo tccutil reset Microphone com.meetingai.macclient
sudo tccutil reset All com.meetingai.macclient

# TCC daemon'ı yeniden başlat
sudo killall tccd
sleep 3

# Quarantine flag'i kaldır
sudo xattr -dr com.apple.quarantine /Applications/MacClient.app

# Launch Services'i yenile
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f /Applications/MacClient.app

# System Settings'i aç
open "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture" &

# MacClient'ı başlat
open /Applications/MacClient.app
```

### 2. enhanced_reset_permissions.sh
```bash
#!/bin/bash
echo "🚨 ENHANCED PERMISSION RESET FOR MACCLIENT"

BUNDLE_ID="com.meetingai.macclient"

# 1. TCC database'ini temizle
echo "🗑️ Cleaning TCC database..."
sudo sqlite3 ~/Library/Application\ Support/com.apple.TCC/TCC.db "DELETE FROM access WHERE client='$BUNDLE_ID';" 2>/dev/null || true

# 2. Permission cache'i temizle
echo "🧹 Clearing permission cache..."
rm -rf ~/Library/Caches/com.apple.TCC/* 2>/dev/null || true

# 3. DerivedData'yı temizle
echo "🧹 Clearing Xcode DerivedData..."
rm -rf ~/Library/Developer/Xcode/DerivedData/MacClient-* 2>/dev/null || true

# 4. System services'i yenile
echo "🔄 Refreshing system services..."
sudo killall tccd 2>/dev/null || true
killall Dock 2>/dev/null || true

# 5. Launch Services'i yenile
echo "🔄 Refreshing Launch Services..."
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f /Applications/MacClient.app 2>/dev/null || true

echo "✅ Enhanced permission reset completed"
```

## 🍎 macOS Sequoia (15.0+) Özel Durumları

### Haftalık İzin Yenileme Gerekliliği
```swift
// macOS 15+ için haftalık izin kontrolü
private func startPeriodicPermissionCheck() {
    let interval = isSequoiaOrLater ? 900.0 : 1800.0 // 15 min vs 30 min
    
    permissionTimer = Timer.scheduledTimer(withTimeInterval: interval, repeats: true) { _ in
        Task { @MainActor in
            await self.checkPermissionStatus()
        }
    }
}

// Haftalık yenileme kontrolü
func getPermissionStatusInfo() -> PermissionStatusInfo {
    return PermissionStatusInfo(
        hasPermission: hasScreenRecordingPermission,
        lastCheck: lastPermissionCheck,
        lastSuccessfulCheck: lastSuccessfulCheck,
        needsWeeklyRenewal: isSequoiaOrLater && Date().timeIntervalSince(lastSuccessfulCheck) > 604800 // 7 days
    )
}
```

### Sequoia Rehberliği
```swift
private func showSequoiaPermissionGuidance() async {
    print("[PermissionManager] 🍎 macOS Sequoia guidance:")
    print("[PermissionManager] 💡 Weekly permission renewal required on macOS 15+")
    
    if Date().timeIntervalSince(lastSuccessfulCheck) > 604800 { // 7 days
        print("[PermissionManager] ⚠️ Permission may have expired (> 7 days since last success)")
    }
}
```

## 🍎 macOS Sequoia (15.0+) Özel Notu: Daha Sık Yeniden Onay

**macOS 15'te Apple, ekran yakalama/TCC tarafında daha sık yeniden onay akışları getiriyor:**

- **Kullanıcılar "haftalık/aylık tekrar" olarak raporluyor**
- **Bu, geliştirme sürecinde "izin vardı, yine gitti" hissini doğurabiliyor**

**Plan**: Periyodik izin kontrolü ve izin biterse kullanıcıyı uyarı + ayarları aç + yeniden başlat akışına yönlendir.

> 💡 **Topluluk raporları**: Daring Fireball, Lapcat Software, Swift Forums

## 🧪 Test ve Debug Yöntemleri

### 1. İzin Durumu Testi
```swift
// PermissionManager'dan detaylı bilgi al
let statusInfo = permissionManager.getPermissionStatusInfo()
print("Bundle ID: \(statusInfo.bundleID)")
print("Bundle Path: \(statusInfo.bundlePath)")
print("Is Development Build: \(statusInfo.isDevelopmentBuild)")
print("Needs Weekly Renewal: \(statusInfo.needsWeeklyRenewal)")
```

## ✅ Hızlı Doğrulama Checklist'i

### 1. Tek Kopya Kontrolü
```bash
mdfind "kMDItemCFBundleIdentifier == 'com.meetingai.macclient'"
```
**✅ Sadece `/Applications/MacClient.app` kalmalı**

### 2. İzin Sıfırlama
```bash
sudo tccutil reset ScreenCapture com.meetingai.macclient
sudo killall tccd
```

### 3. System Settings'te MacClient'i Aç
**✅ Uygulamayı tam kapatıp yeniden aç**

### 4. SCShareableContent Testi
**✅ Uygulama açıldığında `SCShareableContent.current` başarılı mı? (displays > 0)**

### 5. SCStream Testi
**✅ SCStream addOutput testinde -3801 yok → izin etkin**

### 6. SwiftUI Uyarısı
**✅ SwiftUI uyarısı kayboldu mu? (@MainActor + .receive(on:) sonrası)**

### 2. TCC Database Kontrolü
```bash
# TCC database'ini kontrol et
sudo sqlite3 ~/Library/Application\ Support/com.apple.TCC/TCC.db "SELECT * FROM access WHERE service='kTCCServiceScreenCapture';"

# Bundle ID'yi kontrol et
codesign -d -r- /Applications/MacClient.app

# Permissions'ları listele
tccutil list ScreenCapture
```

### 3. Console Log Analizi
```bash
# Console'da izin ile ilgili logları ara
log stream --predicate 'subsystem == "com.apple.TCC"' --level debug

# MacClient loglarını ara
log stream --predicate 'process == "MacClient"' --level info
```

## 🚀 HIZLI ÇÖZÜM ADIMLARI (ÖNERİLEN SIRA)

### ⚠️ KRİTİK: Tek Kopya Prensibi
**Yalnızca /Applications altındaki tek kopyayı çalıştırın!**

- **❌ DerivedData'daki kopyayı kapatın**
- **✅ Finder'dan /Applications'taki tek MacClient.app'i açın**

**Neden?** İki farklı kopya (DerivedData + Applications) TCC tarafında ayrı kayıtlar yarattığı için izin davranışı tutarsız olur. Apple TCC izinlerinin "uygulama binarisine" bağlı çalıştığını unutmayın.

#### Doğrulama (Terminal):
```bash
mdfind "kMDItemCFBundleIdentifier == 'com.meetingai.macclient'"
```
**Çıktıda sadece `/Applications/MacClient.app` kalmalı.**

### 🔄 Adım 1: İzni Sıfırla → Tek Kopyayı Yeniden Yetkilendir

```bash
# Terminal'de çalıştır
sudo tccutil reset ScreenCapture com.meetingai.macclient
sudo killall tccd
```

### ⚙️ Adım 2: System Settings'te İzin Ver
1. **System Settings → Privacy & Security → Screen Recording**
2. **➕ MacClient'ı ekle/işaretle**

### ⚠️ Adım 3: Uygulamayı Tamamen Yeniden Başlat
**Apple davranışı gereği, bu izin uygulama tamamen kapatılıp yeniden açılmadan etkinleşmez:**

- **QUIT et (Cmd+Q)**
- **Yeniden aç**

> 💡 **Not**: Bu nokta Apple ortamında yaygın bir gereklilik; geliştirici deneyimleri ve Apple yönergeleri bu davranışı doğruluyor.

### 🧪 Adım 4: İzin Kontrolünü "Gerçek" Yöntemle Yap

**CGPreflightScreenCaptureAccess() hızlı ama önbelleğe takılabiliyor.** Apple'ın ScreenCaptureKit dokümantasyonuna göre asıl güvenilir test:

1. **SCShareableContent.current** (başarılıysa displays > 0)
2. **SCStream oluşturmayı deneme**

Sen zaten bu yolu büyük oranda kullanıyorsun; hata kodu **-3801**, `SCStreamErrorDomain.permissionDenied`'e karşılık geliyor.

## 📋 Detaylı Sorun Giderme Adımları

### Adım 1: Hızlı Kontrol
1. **Uygulamayı tamamen kapat**
2. **System Settings → Privacy & Security → Screen Recording**
3. **MacClient'ın listede olup olmadığını kontrol et**

### Adım 2: TCC Cache Temizleme
```bash
# Terminal'de çalıştır
sudo tccutil reset ScreenCapture com.meetingai.macclient
sudo killall tccd
```

### Adım 3: Stable Location'a Taşıma
```bash
# fix_all_permissions.sh scriptini çalıştır
chmod +x fix_all_permissions.sh
./fix_all_permissions.sh
```

### Adım 4: Manuel İzin Ekleme
1. **System Settings → Privacy & Security → Screen Recording**
2. **🔓 Kilit simgesine tıkla**
3. **➕ "+" butonuna tıkla**
4. **/Applications/MacClient.app dosyasını seç**
5. **✅ MacClient'ın yanındaki checkbox'ı işaretle**

### Adım 5: Uygulamayı Yeniden Başlat
- **❌ Xcode'dan Run yapma**
- **✅ /Applications/MacClient.app dosyasını çift tıklayarak çalıştır**

## 🚨 Yaygın Hata Kodları ve Çözümleri

### -3801: TCC Erişim Reddi (Permission Denied)
```swift
if nsError.domain == "com.apple.ScreenCaptureKit.SCStreamErrorDomain" && nsError.code == -3801 {
    print("[SC] 🚨 CONFIRMED: Permission denied (TCC error -3801)")
    
    // Kullanıcıya "Screen Recording iznini açtım" dese bile 
    // uygulamayı tam kapatıp yeniden açması gerektiğini yazılı/sesli anlat
    
    // Ardından Preferences sayfasını butonla aç
    if let url = URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture") {
        NSWorkspace.shared.open(url)
    }
    
    return false
}
```

**-3801 için Apple'ın hata kodu ekran yakalama izninin reddi anlamına geliyor; uygulama içi düzeltme mümkün değil, kullanıcı aksiyonu gerekiyor.**

### -3802: İzin Henüz Etkin Değil
```swift
// Yeni verilen iznin aynı process'te etkinleşmemesi
throw NSError(
    domain: "SC", code: -3801,
    userInfo: [NSLocalizedDescriptionKey:
        "Screen Recording permission denied or not yet effective. " +
        "If you have just granted it, QUIT the app completely and relaunch."]
)
```

## 🔄 Best Practices

### 1. İzin Kontrol Sırası
```swift
func checkPermissionStatus() async {
    // 1. Hızlı kontrol (CGPreflightScreenCaptureAccess)
    let preflightResult = CGPreflightScreenCaptureAccess()
    
    // 2. Güvenilir kontrol (SCShareableContent)
    do {
        let content = try await SCShareableContent.current
        let hasDisplays = !content.displays.isEmpty
        if hasDisplays {
            // 3. Kesin kontrol (SCStream test)
            let realPermissionTest = await performRealSCStreamPermissionTest()
            hasScreenRecordingPermission = realPermissionTest
        } else {
            hasScreenRecordingPermission = false
        }
    } catch {
        hasScreenRecordingPermission = false
    }
}
```

## 🔩 Kod Tarafında Önerilen Net Dokunuşlar

### Permission Check Tek Kaynaktan
**PermissionsService.hasScreenRecordingPermission()'ı şu sırayla uygula:**

```swift
// 1. SCShareableContent (başarılıysa displays > 0)
do {
    let content = try await SCShareableContent.current
    return !content.displays.isEmpty
} catch {
    // 2. Gerekirse "gerçek" SCStream addOutput testi (fail -> -3801)
    let streamTest = await performRealSCStreamPermissionTest()
    if streamTest { return true }
    
    // 3. Son çare "preflight" (cache'li olabilir)
    return CGPreflightScreenCaptureAccess()
}
```

### -3801 Yakalanınca Doğru UX
```swift
if nsError.domain == "com.apple.ScreenCaptureKit.SCStreamErrorDomain",
   nsError.code == -3801 {
    
    // UI: "İzni açtıktan sonra uygulamayı TAMAMEN kapatıp yeniden açın."
    showPermissionRestartAlert()
    
    // Preferences sayfasını aç
    PermissionsService.openScreenRecordingPrefs()
    
    return false
}
```

### Main Thread Garantisi
```swift
// PermissionManager, AppState, CaptureController gibi UI state değiştiren sınıflara @MainActor
@MainActor final class PermissionManager: ObservableObject { ... }
@MainActor final class AppState: ObservableObject { ... }
@MainActor final class CaptureController: ObservableObject { ... }

// Callback'lerde her set işlemini main thread'de yap
DispatchQueue.main.async { 
    self.appState.isCapturing = true 
}

// Combine akışlarında main thread garantisi
.receive(on: RunLoop.main)
.receive(on: DispatchQueue.main)
```

### Tek Kopya Prensibi (Geliştirme Alışkanlığı)
```swift
// Xcode'dan Run etmeden önce Finder'daki /Applications kopyasını kapat
// Geliştirme aşamasında tercihen yalnızca Xcode-run kopyasını çalıştır
// Kalıcı izin testleri için "Archive → Export → /Applications" yöntemiyle tek stabil konum kullan
```

### 2. Periyodik Kontrol
```swift
// Development build'lerde daha sık kontrol
let interval = isDevelopmentBuild ? 300.0 : 900.0 // 5 min vs 15 min

permissionTimer = Timer.scheduledTimer(withTimeInterval: interval, repeats: true) { _ in
    Task { @MainActor in
        await self.checkPermissionStatus()
    }
}
```

### 3. Kullanıcı Rehberliği
```swift
func requestPermissionWithGuidance() async -> Bool {
    // macOS versiyonuna göre rehberlik
    if isSequoiaOrLater {
        await showSequoiaPermissionGuidance()
    }
    
    // Development build için özel rehberlik
    if isDevelopmentBuild {
        await showDevelopmentBuildGuidance()
    }
    
    // İzin isteği
    return await performEnhancedPermissionRequest()
}
```

## 🚨 SwiftUI "Publishing changes from background threads" Uyarılarını Kesin

**Tüm @Published güncellemeleri main thread'de yapın:**

### Sınıf Seviyesinde @MainActor
```swift
@MainActor final class AppState: ObservableObject { ... }
@MainActor final class PermissionManager: ObservableObject { ... }
@MainActor final class CaptureController: ObservableObject { ... }
```

### Değişim Anında Main Thread Garantisi
```swift
// Callback'lerde her set işlemini main thread'de yap
DispatchQueue.main.async { 
    self.appState.isCapturing = true 
}

// veya async/await ile
await MainActor.run {
    self.hasScreenRecordingPermission = true
}
```

### Combine Akışlarında Main Thread
```swift
// Combine akışlarında main thread garantisi
.receive(on: RunLoop.main)
.receive(on: DispatchQueue.main)
```

> 💡 **Not**: Swift forumları ve Apple yönlendirmeleri bu gerekliliği net belirtiyor.

## 📞 Destek ve İletişim

### Log Dosyaları
```bash
# Console.app'de izin ile ilgili logları ara
subsystem:com.apple.TCC
process:MacClient
```

## 🤔 Neden Bu Çözümler İşe Yarıyor?

### -3801 Doğrudan "TCC Reddi" Demek
- **Bu durumda sadece kullanıcı izni + uygulamayı yeniden başlatma etkili olur**
- **Apple hata kodları**: `SCStreamError.Code.permissionDenied`

### SCShareableContent Gerçek Yetkiyi Sınar
- **"Preflight" bazı durumlarda cache'li/yanıltıcı olabilir**
- **Apple ScreenCaptureKit API**: En güvenilir test yöntemi

### Sequoia'da Sık Onay
- **Geliştirici raporları**: Sürecin daha sık tekrarı gerektiğini gösteriyor
- **Uygulamada periyodik kontrol ve yönlendirme akışı gerek**

### SwiftUI Publish Hatası
- **Apple/Swift topluluğunda bilinen kural**: ObservableObject değişiklikleri main thread'de publish edilmelidir

### "TUINSRemoteViewController..." Log'u
- **Bu satırlar genellikle sistem/servis kökenli (view service) bir uyarıdır**
- **Çoğu zaman uygulamanın kendi hatası değildir ve izin/TCC probleminden bağımsızdır**
- **Genelde yok sayılabilir; asıl blokaj -3801/TCC'dir**
- **Benzeri raporlar geliştirici forumlarında sıkça görülür**

### Debug Modu
```swift
// PermissionManager'da debug logları aktif et
print("[PermissionManager] 🔍 Debug: Bundle ID: \(bundleID)")
print("[PermissionManager] 🔍 Debug: Bundle Path: \(bundlePath)")
print("[PermissionManager] 🔍 Debug: Is Development Build: \(isDevelopmentBuild)")
```

### Otomatik Çözüm
```swift
// PermissionManager'da otomatik TCC reset
func performAutomaticTCCReset() async -> Bool {
    print("[PermissionManager] 🚨 AUTOMATIC TCC RESET - Starting...")
    
    // Otomatik reset script'ini çalıştır
    let resetSuccess = await executeAutomaticResetScript()
    
    if resetSuccess {
        await checkPermissionStatus()
        return hasScreenRecordingPermission
    }
    
    return false
}
```

---

## 📝 Özet

Bu rehber, MacClient uygulamasında yaşanan ekran kaydı izni sorunlarını kapsamlı olarak ele alır. Ana sorunlar:

1. **Development Build İzin Kaybı**: Her build'de bundle path değişiyor
2. **TCC Cache Sorunları**: Eski izin bilgileri cache'de kalıyor
3. **Otomatik İzin Ekleme**: Permission request mekanizması doğru çalışmıyor

**Çözümler**:
- **Tek kopya prensibi**: Sadece /Applications'daki kopyayı kullan
- TCC cache temizleme ve reset
- Gelişmiş izin kontrol mekanizmaları (SCShareableContent + SCStream test)
- Otomatik reset scriptleri

**🚀 Hızlı Çözüm Sırası**:
1. **Tek kopya kontrolü**: `mdfind` ile sadece /Applications/MacClient.app kalmalı
2. **İzin sıfırlama**: `sudo tccutil reset ScreenCapture com.meetingai.macclient`
3. **System Settings'te izin ver**: MacClient'ı ekle/işaretle
4. **Uygulamayı tamamen yeniden başlat**: QUIT (Cmd+Q) + yeniden aç
5. **SCShareableContent testi**: displays > 0 olmalı

**🔩 Kod İyileştirmeleri**:
- `@MainActor` kullanarak SwiftUI uyarılarını kes
- -3801 hata kodunda doğru UX akışı
- Periyodik izin kontrolü (özellikle macOS 15+ için)

Bu rehberi takip ederek izin sorunlarını çözebilir ve uygulamanızın düzgün çalışmasını sağlayabilirsiniz.
