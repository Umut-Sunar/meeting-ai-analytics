# 🎯 macOS İzin Yönetimi Birleştirme

**ROLE**: Senior macOS engineer  
**GOAL**: Mikrofon ve ekran kaydı izin akışını tek mimaride topla. "Kaydı Başlat" → izin yoksa yönlendir, varsa başlat. Sequoia haftalık yenileme + development TCC sorunları çöz.

## 🚀 MEVCUT KOD HAZIR - SADECE ENTEGRASYON
1. `PermissionManager` → `AppState`'e ekle
2. UI butonlarını mevcut fonksiyonlara bağla
3. Unified permission check flow oluştur

## 📁 DOSYALAR
- ✅ `PermissionsService.swift` - `checkMicAuthorized()`, `hasScreenRecordingPermission()` 
- ✅ `AudioAssist_V1_Sources/PermissionManager.swift` - Sequoia/TCC logic, `requestPermissionWithGuidance()`
- 🔄 `AppState.swift` - PermissionManager entegrasyonu ekle
- 🔄 `DesktopMainView.swift` - UI butonları ekle

## 🔧 YAPILACAKLAR

### 1. AppState.swift'e ekle:
```swift
@StateObject private var permissionManager = PermissionManager()
```

### 2. DesktopMainView → PreMeetingView → GroupBox("İzinler") içine butonlar:
```swift
Button("İzinleri Kontrol Et") { 
    Task { await permissionManager.checkPermissionStatus() }
}
Button("Ekran Kaydı Ayarlarını Aç") { 
    PermissionsService.openScreenRecordingPrefs() 
}
Button("Geliştirici Modunda İzinleri Onar") { 
    Task { await permissionManager.requestPermissionWithGuidance() }
}
```

### 3. Unified Permission Check (CaptureController'da):
```swift
// Mikrofon kontrolü
PermissionsService.checkMicAuthorized { granted in
    appState.isMicAuthorized = granted
}

// Ekran kaydı kontrolü  
let hasScreen = await PermissionsService.hasScreenRecordingPermission()
appState.isScreenAuthorized = hasScreen
```

### 4. Sequoia Haftalık Uyarı:
```swift
let info = permissionManager.getPermissionStatusInfo()
if info.needsWeeklyRenewal {
    appState.log("[PERM] ⚠️ Sequoia haftalık yenileme gerekli")
}
```

### 5. Structured Logging:
```swift
appState.log("[PERM] Mikrofon izni: \(granted ? "✅" : "❌")")
appState.log("[SC] Ekran kaydı izni: \(hasScreen ? "✅" : "❌")")
```

## ✅ KABUL KRİTERLERİ
- İlk açılışta mikrofon izni prompt gelir
- "Kaydı Başlat" → ekran izni yoksa ayarlar açılır + uyarı
- Sequoia'da 7 gün sonra yenileme uyarısı
- Development build'de TCC rehberliği
- SystemAudioCaptureSC frame drop yok (VideoOutputHandler aktif)
- PCM çıkış Int16 mono 48k

**COMMIT**: `feat(permissions): unify mic+screen recording flow; Sequoia weekly renewal & TCC dev fixes`
