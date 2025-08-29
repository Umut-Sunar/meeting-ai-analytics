# 🔒 MacClient TCC Permission Fix - Manual Steps

## Problem
MacClient uygulaması System Preferences → Security & Privacy → Screen Recording listesinde görünmüyor.

## Root Cause
- Her Xcode build'inde uygulama yeni bir path'e gidiyor (DerivedData)
- macOS bunu farklı bir uygulama olarak görüyor
- TCC cache eski path'leri hatırlıyor

## ✅ Solution Steps

### Step 1: TCC Cache Temizleme (TAMAMLANDI ✅)
```bash
sudo tccutil reset ScreenCapture com.meetingai.macclient
sudo killall tccd
```

### Step 2: Stable Location'a Build
1. **Xcode'da MacClient projesini aç**
2. **Product → Archive** (veya ⌘+Shift+B)
3. **Organizer'da "Distribute App" → "Copy App"**
4. **Uygulamayı `/Applications/MacClient.app` olarak kaydet**

### Step 3: System Preferences'ta İzin Ver
1. **System Preferences → Security & Privacy → Privacy → Screen Recording**
2. **🔓 Kilit simgesine tıkla ve şifreni gir**
3. **➕ "+" butonuna tıkla**
4. **`/Applications/MacClient.app` dosyasını seç**
5. **✅ MacClient'ın yanındaki checkbox'ı işaretle**

### Step 4: Uygulamayı Stable Location'dan Çalıştır
- **❌ Xcode'dan Run yapma (⌘+R)**
- **✅ `/Applications/MacClient.app` dosyasını çift tıklayarak çalıştır**

## 🔄 Alternative: Archive & Export

Eğer yukarıdaki adımlar çalışmazsa:

1. **Xcode → Product → Archive**
2. **Window → Organizer**
3. **MacClient archive'ını seç**
4. **"Distribute App" → "Copy App"**
5. **"Export" → Applications klasörüne kaydet**

## 🚨 Important Notes

- **Development builds** her seferinde farklı path'e gidiyor
- **Stable location** (/Applications) kullanmak zorunlu
- **TCC permissions** path-based çalışıyor
- **macOS Sequoia** haftalık permission renewal gerektirebilir

## 🧪 Test

Stable location'dan çalıştırdıktan sonra:

1. **MacClient'ı aç**
2. **"Capture System Audio" seçeneğini işaretle**
3. **"Start Meeting" butonuna tıkla**
4. **Eğer permission dialog çıkarsa "Allow" de**
5. **System Preferences'ta MacClient'ın listelendiğini kontrol et**

## 🔧 Debug

Eğer hala çalışmazsa:

```bash
# TCC database'ini kontrol et
sudo sqlite3 /Library/Application\ Support/com.apple.TCC/TCC.db "SELECT * FROM access WHERE service='kTCCServiceScreenCapture';"

# Bundle ID'yi kontrol et
codesign -d -r- /Applications/MacClient.app

# Permissions'ları kontrol et
tccutil list ScreenCapture
```

## 📞 Support

Bu adımları takip ettikten sonra hala sorun varsa:
- Mac'i restart et
- TCC database'i corrupt olabilir (nadir)
- Bundle signing sorunu olabilir
