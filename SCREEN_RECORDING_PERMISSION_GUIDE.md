# 🔐 Screen Recording İzni Rehberi

## ❌ Mevcut Sorun
```
[ERROR] -[RPDaemonProxy fetchShareableContentWithOption:windowID:currentProcess:withCompletionHandler:]_block_invoke:902 error: 4097
```

**Error 4097** = Screen Recording izni reddedilmiş veya verilmemiş.

## ✅ Çözüm Adımları

### 1. System Preferences'ı Aç
```bash
# Terminal'den açmak için:
open "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture"
```

### 2. Manuel Açma
1. **System Preferences** → **Security & Privacy**
2. **Privacy** sekmesi
3. Sol taraftan **Screen Recording** seç
4. Kilit simgesine tıklayıp şifreyi gir
5. **MacClient** uygulamasını listede bul
6. Yanındaki checkbox'ı işaretle ✅

### 3. Uygulama Yeniden Başlatma
- MacClient uygulamasını tamamen kapat
- Tekrar başlat
- İzin değişiklikleri aktif olacak

## 🧪 Test Etme

İzin verildikten sonra logları kontrol et:
```
[SC] ✅ SystemAudioCaptureSC başlatıldı
[DEBUG] 🔊 Sistem ses akışı başladı
```

## 📋 Alternatif Kontrol

Terminal'den izin durumunu kontrol et:
```bash
# Screen Recording izinlerini listele
sqlite3 ~/Library/Application\ Support/com.apple.TCC/TCC.db "SELECT client,auth_value FROM access WHERE service='kTCCServiceScreenCapture';"
```

## ⚠️ Önemli Notlar

- **macOS Monterey+**: İzin verme işlemi daha katı
- **Sandbox**: Uygulama sandbox'ta ise ek ayarlar gerekebilir  
- **Xcode**: Development sırasında imzalama gerekebilir

## 🔄 Sorun Devam Ederse

1. **TCC veritabanını sıfırla**:
   ```bash
   sudo tccutil reset ScreenCapture
   ```

2. **Uygulamayı yeniden başlat**

3. **İzin tekrar iste**
