#!/bin/bash

echo "🔍 Ekran Kaydı İzni Kontrol Scripti"
echo "=================================="

# TCC veritabanından ekran kaydı izinlerini kontrol et
echo "📋 Mevcut ekran kaydı izinleri:"
sudo sqlite3 /Library/Application\ Support/com.apple.TCC/TCC.db "SELECT client, auth_value FROM access WHERE service='kTCCServiceScreenCapture';" 2>/dev/null || echo "❌ TCC veritabanına erişim reddedildi"

echo ""
echo "🔧 Manuel Kontrol Adımları:"
echo "1. Sistem Ayarları → Gizlilik ve Güvenlik → Ekran Kaydı"
echo "2. MacClient'ı listede bulun"
echo "3. Yanındaki checkbox'ı işaretleyin"
echo "4. MacClient'ı tamamen kapatın (Cmd+Q)"
echo "5. MacClient'ı yeniden başlatın"

echo ""
echo "⚠️  Önemli Notlar:"
echo "- macOS 15 Sequoia'da izinler haftalık yenilenir"
echo "- Development build'lerde TCC cache sorunu olabilir"
echo "- İzin verdikten sonra mutlaka uygulamayı yeniden başlatın"

echo ""
echo "🧪 Test Komutu:"
echo "MacClient'ta sistem audio capture başlatmayı deneyin"
echo "Console.app'te 'RPDaemonProxy' hatalarını kontrol edin"
