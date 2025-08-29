# 🔍 MacClient Screen Recording İzni - Kapsamlı Analiz ve Çözüm Rehberi

## 📋 Mevcut Durum Analizi

### ✅ Doğru Yapılandırılmış Kısımlar

#### 1. Bundle ID Tutarlılığı
- **Info.plist**: `com.meetingai.macclient` ✅
- **Xcode Project**: `com.meetingai.macclient` ✅  
- **PermissionManager**: `com.meetingai.macclient` ✅
- **Scripts**: `com.meetingai.macclient` ✅

#### 2. Info.plist Yapılandırması
```xml
<!-- ✅ DOĞRU: Gerekli permission descriptions mevcut -->
<key>NSScreenCaptureDescription</key>
<string>Sistem sesini yakalamak için ekran kayıt iznine ihtiyacımız var.</string>

<key>NSMicrophoneUsageDescription</key>
<string>Mikrofonu toplantı asistanı için kullanacağız.</string>

<key>NSAudioCaptureUsageDescription</key>
<string>Sistem sesini toplantı asistanı için yakalayacağız.</string>

<!-- ✅ DOĞRU: Minimum macOS version -->
<key>LSMinimumSystemVersion</key>
<string>13.0</string>
```

#### 3. Entitlements.plist Yapılandırması
```xml
<!-- ✅ DOĞRU: Sandbox devre dışı (screen recording için gerekli) -->
<key>com.apple.security.app-sandbox</key>
<false/>

<!-- ✅ DOĞRU: Audio input permission -->
<key>com.apple.security.device.audio-input</key>
<true/>

<!-- ✅ DOĞRU: Screen recording için gelişmiş entitlements -->
<key>com.apple.security.temporary-exception.shared-preference.read-write</key>
<array>
    <string>com.apple.TCC</string>
</array>

<key>com.apple.security.temporary-exception.mach-lookup.global-name</key>
<array>
    <string>com.apple.windowserver.active</string>
    <string>com.apple.tccd</string>
</array>
```

#### 4. Modern Permission Management
```swift
// ✅ DOĞRU: Asenkron ve güvenilir permission check
@available(macOS 13.0, *)
static func hasScreenRecordingPermission() async -> Bool {
    do { 
        _ = try await SCShareableContent.current
        return true
    } catch { 
        return false 
    }
}
```

### 🚨 Tespit Edilen Sorunlar ve Eksiklikler

#### 1. **KRİTİK SORUN**: Info.plist'te Duplicate Keys
```xml
<!-- ❌ SORUN: Duplicate keys mevcut -->
<key>LSMinimumSystemVersion</key>
<string>13.0</string>
<!-- ... diğer keys ... -->
<key>LSMinimumSystemVersion</key>  <!-- ❌ DUPLICATE -->
<string>13.0</string>

<key>NSScreenCaptureDescription</key>
<string>Sistem sesini yakalamak için ekran kayıt iznine ihtiyacımız var.</string>
<!-- ... diğer keys ... -->
<key>NSScreenCaptureDescription</key>  <!-- ❌ DUPLICATE -->
<string>MacClient needs screen recording permission to capture system audio for meeting transcription.</string>
```

#### 2. **SORUN**: Inconsistent Permission Check Methods
```swift
// ❌ SORUN: SystemAudioCaptureSC'de async check kullanılıyor
guard await PermissionsService.hasScreenRecordingPermission() else {
    // ...
}

// ❌ SORUN: Ama PermissionManager'da sync CGPreflightScreenCaptureAccess kullanılıyor
// Bu tutarsızlık permission cache sorunlarına yol açabilir
```

#### 3. **SORUN**: Error 4097 Handling Eksik
```swift
// ❌ EKSIK: RPDaemonProxy error 4097 için özel handling yok
// Bu error özellikle macOS 15+ Sequoia'da sık görülüyor
```

#### 4. **SORUN**: Development Build Detection Eksik
```swift
// ❌ EKSIK: Development build detection ve özel handling yok
// DerivedData path değişiklikleri için özel strateji yok
```

#### 5. **SORUN**: macOS Sequoia (15.0+) Özel Durumları
```swift
// ❌ EKSIK: Haftalık permission renewal kontrolü yok
// ❌ EKSIK: Sequoia-specific permission strategies yok
```

## 🛠️ Önerilen Düzeltmeler

### 1. Info.plist Temizleme (KRİTİK)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <!-- Bundle Configuration -->
    <key>CFBundleDevelopmentRegion</key>
    <string>$(DEVELOPMENT_LANGUAGE)</string>
    <key>CFBundleExecutable</key>
    <string>$(EXECUTABLE_NAME)</string>
    <key>CFBundleIdentifier</key>
    <string>$(PRODUCT_BUNDLE_IDENTIFIER)</string>
    <key>CFBundleName</key>
    <string>MacClient</string>
    <key>CFBundleDisplayName</key>
    <string>MacClient</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundleVersion</key>
    <string>1</string>
    
    <!-- System Requirements -->
    <key>LSMinimumSystemVersion</key>
    <string>13.0</string>
    <key>LSApplicationCategoryType</key>
    <string>public.app-category.productivity</string>
    
    <!-- Permission Descriptions -->
    <key>NSScreenCaptureDescription</key>
    <string>MacClient needs screen recording permission to capture system audio for meeting transcription.</string>
    <key>NSMicrophoneUsageDescription</key>
    <string>Mikrofonu toplantı asistanı için kullanacağız.</string>
    <key>NSAudioCaptureUsageDescription</key>
    <string>Sistem sesini toplantı asistanı için yakalayacağız.</string>
    
    <!-- App Configuration -->
    <key>NSPrincipalClass</key>
    <string>NSApplication</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSSupportsAutomaticGraphicsSwitching</key>
    <true/>
    
    <!-- Network Security -->
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
            </dict>
        </dict>
    </dict>
    
    <!-- Environment Variables -->
    <key>DEEPGRAM_API_KEY</key>
    <string>$(DEEPGRAM_API_KEY)</string>
</dict>
</plist>
```

### 2. Enhanced PermissionManager Implementation

```swift
@available(macOS 13.0, *)
@MainActor
class PermissionManager: ObservableObject {
    
    // MARK: - Published Properties
    @Published var hasScreenRecordingPermission = false
    @Published var lastPermissionCheck = Date()
    @Published var permissionCheckInProgress = false
    @Published var needsWeeklyRenewal = false
    
    // MARK: - Private Properties
    private let bundleID: String
    private let bundlePath: String
    private let isDevelopmentBuild: Bool
    private let isSequoiaOrLater: Bool
    private var permissionTimer: Timer?
    private var lastSuccessfulCheck = Date.distantPast
    
    // MARK: - Initialization
    init() {
        self.bundleID = Bundle.main.bundleIdentifier ?? "com.meetingai.macclient"
        self.bundlePath = Bundle.main.bundlePath
        self.isDevelopmentBuild = bundlePath.contains("DerivedData")
        
        // macOS version detection
        if #available(macOS 15.0, *) {
            self.isSequoiaOrLater = true
        } else {
            self.isSequoiaOrLater = false
        }
        
        startPeriodicPermissionCheck()
    }
    
    // MARK: - Permission Management
    
    /// Comprehensive permission check with multiple strategies
    func checkPermissionStatus() async {
        guard !permissionCheckInProgress else { return }
        permissionCheckInProgress = true
        defer { permissionCheckInProgress = false }
        
        let hasPermission = await performEnhancedPermissionCheck()
        
        await MainActor.run {
            self.hasScreenRecordingPermission = hasPermission
            self.lastPermissionCheck = Date()
            
            if hasPermission {
                self.lastSuccessfulCheck = Date()
            }
            
            // Check if weekly renewal needed (Sequoia)
            if isSequoiaOrLater {
                let daysSinceLastSuccess = Date().timeIntervalSince(lastSuccessfulCheck) / 86400
                self.needsWeeklyRenewal = daysSinceLastSuccess > 7
            }
        }
    }
    
    /// Enhanced permission check with multiple validation methods
    private func performEnhancedPermissionCheck() async -> Bool {
        // 1. Quick preflight check (may be cached)
        let preflightResult = CGPreflightScreenCaptureAccess()
        
        // 2. Reliable SCShareableContent check
        do {
            let content = try await SCShareableContent.current
            let hasDisplays = !content.displays.isEmpty
            
            if hasDisplays {
                // 3. Real SCStream test for absolute certainty
                let streamTest = await performRealSCStreamPermissionTest()
                return streamTest
            } else {
                return false
            }
        } catch let error as NSError {
            // Handle specific error codes
            if error.domain == "com.apple.ScreenCaptureKit.SCStreamErrorDomain" {
                switch error.code {
                case -3801: // Permission denied
                    print("[PermissionManager] ❌ TCC Permission denied (-3801)")
                    return false
                case 4097: // RPDaemonProxy error (common in Sequoia)
                    print("[PermissionManager] ⚠️ RPDaemonProxy error (4097) - permission likely denied")
                    return false
                default:
                    print("[PermissionManager] ❌ SCShareableContent error: \(error.code)")
                    return false
                }
            }
            
            // Fallback to preflight for unknown errors
            return preflightResult
        }
    }
    
    /// Real SCStream permission test - most accurate method
    private func performRealSCStreamPermissionTest() async -> Bool {
        do {
            let content = try await SCShareableContent.current
            guard let display = content.displays.first else { return false }
            
            let filter = SCContentFilter(display: display, excludingApplications: [], exceptingWindows: [])
            let config = SCStreamConfiguration()
            config.capturesAudio = true
            
            let testStream = SCStream(filter: filter, configuration: config, delegate: nil)
            
            // Try to add a test output - this will fail if permission is denied
            let testQueue = DispatchQueue(label: "test.permission.queue")
            try testStream.addStreamOutput(TestStreamOutput(), type: .audio, sampleHandlerQueue: testQueue)
            
            return true
        } catch let error as NSError {
            if error.domain == "com.apple.ScreenCaptureKit.SCStreamErrorDomain" && error.code == -3801 {
                return false // Permission definitely denied
            }
            return false
        }
    }
    
    /// Request permission with development build awareness
    func requestPermissionWithGuidance() async -> Bool {
        // Development build specific guidance
        if isDevelopmentBuild {
            await showDevelopmentBuildGuidance()
        }
        
        // macOS Sequoia specific guidance
        if isSequoiaOrLater {
            await showSequoiaPermissionGuidance()
        }
        
        // Multiple permission request attempts for development builds
        let granted = await performEnhancedPermissionRequest()
        
        await checkPermissionStatus()
        return hasScreenRecordingPermission
    }
    
    /// Enhanced permission request with multiple attempts
    private func performEnhancedPermissionRequest() async -> Bool {
        if isDevelopmentBuild {
            return await performDevelopmentBuildPermissionRequest()
        } else {
            return performStandardPermissionRequest()
        }
    }
    
    /// Development build permission request with multiple attempts
    private func performDevelopmentBuildPermissionRequest() async -> Bool {
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
    
    /// Standard permission request
    private func performStandardPermissionRequest() -> Bool {
        return CGRequestScreenCaptureAccess()
    }
    
    // MARK: - Guidance Methods
    
    private func showDevelopmentBuildGuidance() async {
        print("[PermissionManager] 🔧 Development build detected:")
        print("[PermissionManager] 💡 Consider using Archive build for stable permissions")
        print("[PermissionManager] 💡 Multiple permission attempts will be made")
    }
    
    private func showSequoiaPermissionGuidance() async {
        print("[PermissionManager] 🍎 macOS Sequoia guidance:")
        print("[PermissionManager] 💡 Weekly permission renewal required on macOS 15+")
        
        if needsWeeklyRenewal {
            print("[PermissionManager] ⚠️ Permission may have expired (> 7 days since last success)")
        }
    }
    
    // MARK: - Periodic Monitoring
    
    private func startPeriodicPermissionCheck() {
        let interval = isSequoiaOrLater ? 900.0 : 1800.0 // 15 min vs 30 min
        
        permissionTimer = Timer.scheduledTimer(withTimeInterval: interval, repeats: true) { _ in
            Task { @MainActor in
                await self.checkPermissionStatus()
            }
        }
    }
    
    // MARK: - Public Interface
    
    func openSystemPreferences() {
        PermissionsService.openScreenRecordingPrefs()
    }
    
    func getPermissionStatusInfo() -> PermissionStatusInfo {
        return PermissionStatusInfo(
            hasPermission: hasScreenRecordingPermission,
            lastCheck: lastPermissionCheck,
            lastSuccessfulCheck: lastSuccessfulCheck,
            needsWeeklyRenewal: needsWeeklyRenewal,
            isDevelopmentBuild: isDevelopmentBuild,
            isSequoiaOrLater: isSequoiaOrLater,
            bundleID: bundleID,
            bundlePath: bundlePath
        )
    }
}

// MARK: - Supporting Types

struct PermissionStatusInfo {
    let hasPermission: Bool
    let lastCheck: Date
    let lastSuccessfulCheck: Date
    let needsWeeklyRenewal: Bool
    let isDevelopmentBuild: Bool
    let isSequoiaOrLater: Bool
    let bundleID: String
    let bundlePath: String
}

/// Minimal SCStreamOutput implementation for permission testing
@available(macOS 13.0, *)
private class TestStreamOutput: NSObject, SCStreamOutput {
    func stream(_ stream: SCStream, didOutputSampleBuffer sampleBuffer: CMSampleBuffer, of type: SCStreamOutputType) {
        // No-op: We only need this for permission testing
    }
}
```

### 3. Enhanced Error Handling in SystemAudioCaptureSC

```swift
func start() async throws {
    print("[SC] ▶️ Starting SystemAudioCaptureSC...")
    
    // 1) Enhanced permission check with specific error handling
    guard await PermissionsService.hasScreenRecordingPermission() else {
        print("[SC] ❌ Screen Recording OFF – opening System Settings")
        PermissionsService.openScreenRecordingPrefs()
        throw NSError(
            domain: "SC", code: -3,
            userInfo: [NSLocalizedDescriptionKey:
                "Screen recording permission required. Opened System Settings. " +
                "After granting, quit and relaunch the app."]
        )
    }
    
    do {
        print("[SC] 🚀 requesting shareable content…")
        let content = try await SCShareableContent.current
        
        guard let display = content.displays.first else {
            throw NSError(domain: "SC", code: -1,
                          userInfo: [NSLocalizedDescriptionKey: "No displays found"])
        }
        
        // ... rest of implementation
        
    } catch let error as NSError {
        // Enhanced error handling for specific cases
        if error.domain == "com.apple.ScreenCaptureKit.SCStreamErrorDomain" {
            switch error.code {
            case -3801:
                throw NSError(
                    domain: "SC", code: -3801,
                    userInfo: [NSLocalizedDescriptionKey:
                        "Screen Recording permission denied. Please enable in System Settings → Privacy & Security → Screen Recording, then quit and relaunch the app."]
                )
            case 4097:
                throw NSError(
                    domain: "SC", code: 4097,
                    userInfo: [NSLocalizedDescriptionKey:
                        "RPDaemonProxy error (common in macOS 15+). Please check Screen Recording permission and restart the app."]
                )
            default:
                throw error
            }
        }
        throw error
    }
}
```

### 4. Updated Automated Fix Script

```bash
#!/bin/bash
echo "🔧 MacClient Enhanced Screen Recording Permission Fix"
echo "=================================================="

# App configuration
BUNDLE_ID="com.meetingai.macclient"
APP_NAME="MacClient"

# Detect macOS version
MACOS_VERSION=$(sw_vers -productVersion)
IS_SEQUOIA=$(echo "$MACOS_VERSION" | awk -F. '{if($1>=15) print "true"; else print "false"}')

echo "📱 Bundle ID: $BUNDLE_ID"
echo "🍎 macOS Version: $MACOS_VERSION"
echo "🍎 Is Sequoia+: $IS_SEQUOIA"

# Enhanced TCC reset for Sequoia
if [ "$IS_SEQUOIA" = "true" ]; then
    echo "🍎 Applying Sequoia-specific fixes..."
    
    # More aggressive TCC reset for Sequoia
    sudo tccutil reset All $BUNDLE_ID 2>/dev/null || true
    sudo tccutil reset ScreenCapture 2>/dev/null || true
    
    # Force TCC daemon restart (more important in Sequoia)
    sudo killall tccd 2>/dev/null || true
    sudo launchctl stop com.apple.tccd 2>/dev/null || true
    sleep 2
    sudo launchctl start com.apple.tccd 2>/dev/null || true
    
    echo "⚠️  Sequoia Note: Weekly permission renewal may be required"
fi

# Standard permission reset
echo "🔒 Resetting TCC permissions..."
sudo tccutil reset ScreenCapture $BUNDLE_ID 2>/dev/null || true
sudo tccutil reset Microphone $BUNDLE_ID 2>/dev/null || true

# Clean app data and caches
echo "🗑️  Cleaning app data..."
rm -rf ~/Library/Caches/$BUNDLE_ID 2>/dev/null || true
rm -rf ~/Library/Saved\ Application\ State/$BUNDLE_ID.savedState/ 2>/dev/null || true
rm -rf ~/Library/Preferences/$BUNDLE_ID.plist 2>/dev/null || true

# Development build specific cleanup
if ls ~/Library/Developer/Xcode/DerivedData/MacClient-* 1> /dev/null 2>&1; then
    echo "🔧 Development build detected - cleaning DerivedData..."
    rm -rf ~/Library/Developer/Xcode/DerivedData/MacClient-*
fi

# System cache refresh
echo "🔄 Refreshing system caches..."
sudo dscacheutil -flushcache 2>/dev/null || true
killall Dock 2>/dev/null || true

echo ""
echo "✅ Enhanced permission reset complete!"
echo ""
echo "📋 Next Steps:"
echo "1. 🔧 Open System Settings → Privacy & Security → Screen Recording"
echo "2. ➕ Add MacClient if not listed (use + button)"
echo "3. ✅ Enable the checkbox for MacClient"
echo "4. 🔄 Quit MacClient completely (Cmd+Q)"
echo "5. 🚀 Relaunch MacClient"

if [ "$IS_SEQUOIA" = "true" ]; then
    echo ""
    echo "🍎 Sequoia-Specific Notes:"
    echo "   - Permission may need weekly renewal"
    echo "   - Consider using Archive builds for stability"
    echo "   - Monitor for RPDaemonProxy errors (4097)"
fi

# Open System Settings
read -p "Open System Settings now? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    open "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture"
fi
```

## 🎯 Hızlı Çözüm Adımları (Güncellenmiş)

### 1. ⚠️ KRİTİK: Info.plist Duplicate Keys Temizleme
```bash
# Info.plist'teki duplicate key'leri temizle
# Yukarıdaki temizlenmiş Info.plist'i kullan
```

### 2. 🔄 Enhanced Permission Reset
```bash
# Enhanced fix script'ini çalıştır
chmod +x enhanced_permission_fix.sh
./enhanced_permission_fix.sh
```

### 3. ⚙️ System Settings'te İzin Ver
1. **System Settings → Privacy & Security → Screen Recording**
2. **➕ MacClient'ı ekle/işaretle**
3. **✅ Checkbox'ı aktif et**

### 4. ⚠️ Uygulamayı Tamamen Yeniden Başlat
- **QUIT et (Cmd+Q)**
- **Finder'dan /Applications/MacClient.app'i çalıştır**

### 5. 🧪 Verification
```swift
// Enhanced permission status kontrolü
let statusInfo = permissionManager.getPermissionStatusInfo()
print("Has Permission: \(statusInfo.hasPermission)")
print("Is Development Build: \(statusInfo.isDevelopmentBuild)")
print("Needs Weekly Renewal: \(statusInfo.needsWeeklyRenewal)")
```

## 🚨 macOS Sequoia (15.0+) Özel Notları

### Haftalık İzin Yenileme
- **macOS 15+**: Apple haftalık permission renewal gerektiriyor
- **Çözüm**: Periyodik kontrol ve kullanıcı uyarısı

### RPDaemonProxy Error 4097
- **Yaygın hata**: Sequoia'da sık görülüyor
- **Çözüm**: Enhanced error handling ve kullanıcı rehberliği

### Development Build Sorunları
- **Artmış instability**: Sequoia'da development build'lerde daha fazla sorun
- **Çözüm**: Archive build kullanımı önerisi

## 📊 Karşılaştırma: Önceki vs Yeni Yaklaşım

| Özellik | Önceki Yaklaşım | Yeni Yaklaşım |
|---------|----------------|---------------|
| **Permission Check** | Tek method (CGPreflight) | Multi-layered validation |
| **Error Handling** | Generic | Specific error codes |
| **macOS Sequoia** | Desteklenmiyor | Özel handling |
| **Development Build** | Fark edilmiyor | Özel strateji |
| **Info.plist** | Duplicate keys | Temizlenmiş |
| **Monitoring** | Yok | Periyodik kontrol |
| **User Guidance** | Minimal | Contextual rehberlik |

## 🎉 Sonuç

Bu kapsamlı analiz ve çözüm rehberi:

1. **✅ Mevcut sorunları tespit etti** (duplicate keys, inconsistent checks)
2. **🛠️ Gelişmiş çözümler sundu** (enhanced permission manager)
3. **🍎 macOS Sequoia desteği ekledi** (haftalık renewal, error 4097)
4. **🔧 Development build awareness** (DerivedData detection)
5. **📋 Otomatik fix script'leri güncelledi** (Sequoia-aware)

**Sonraki adım**: Bu düzeltmeleri uygulayarak screen recording permission sorunlarını kalıcı olarak çözmek.
