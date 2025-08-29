#!/bin/bash
echo "🔧 MacClient TCC Permission Auto-Fix Script"
echo "=============================================="

# DerivedData'dan app'i bulup kopyalayalım
echo "📱 Finding and copying fresh app..."
DERIVED_APP=$(find ~/Library/Developer/Xcode/DerivedData -name "MacClient.app" -type d 2>/dev/null | head -1)
if [ -n "$DERIVED_APP" ]; then
    echo "📦 Found app at: $DERIVED_APP"
    sudo rm -rf /Applications/MacClient.app
    sudo cp -R "$DERIVED_APP" /Applications/
    sudo chown -R $(whoami):staff /Applications/MacClient.app
    echo "✅ App copied to: /Applications/MacClient.app"
else
    echo "❌ No MacClient.app found in DerivedData"
    echo "👉 Please run/build the project in Xcode first"
    exit 1
fi

# TCC permissions'ı sıfırla
echo "🧹 Resetting all TCC permissions..."
sudo tccutil reset ScreenCapture com.meetingai.macclient 2>/dev/null
sudo tccutil reset Microphone com.meetingai.macclient 2>/dev/null
sudo tccutil reset All com.meetingai.macclient 2>/dev/null
sudo tccutil reset ScreenCapture 2>/dev/null

# TCC daemon'ı yeniden başlat
echo "🔄 Restarting TCC daemon..."
sudo killall tccd 2>/dev/null
sleep 3

# Quarantine flag'i kaldır
echo "🔓 Removing quarantine attributes..."
sudo xattr -dr com.apple.quarantine /Applications/MacClient.app 2>/dev/null
sudo xattr -cr /Applications/MacClient.app 2>/dev/null

# Launch Services'i yenile
echo "🔄 Refreshing Launch Services..."
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f /Applications/MacClient.app

# System Settings'i aç
echo "⚙️ Opening System Settings..."
open "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture" &

# MacClient'ı başlat
echo "🚀 Launching MacClient from Applications..."
sleep 2
open /Applications/MacClient.app

echo ""
echo "✅ AUTO-FIX COMPLETED!"
echo "🎯 MacClient installed at: /Applications/MacClient.app"
echo "⚙️ System Settings opened to Screen Recording permissions"
echo "🚀 MacClient launched and should appear in permission list"
echo ""
echo "👉 If permission dialog appears, click 'Allow'"
