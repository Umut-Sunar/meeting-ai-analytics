#!/bin/bash

# TCC Cache Fix Script for MacClient Screen Recording Permissions
# This fixes the common issue where development builds don't appear in System Preferences

echo "🔒 MacClient TCC Permission Fix Script"
echo "======================================"

# Get bundle identifier
BUNDLE_ID="com.meetingai.macclient"
APP_NAME="MacClient"

echo "📱 Bundle ID: $BUNDLE_ID"
echo "🏷️  App Name: $APP_NAME"

# Check if running with sudo
if [ "$EUID" -ne 0 ]; then
    echo "⚠️  This script needs sudo access to reset TCC permissions"
    echo "🔄 Re-running with sudo..."
    sudo "$0" "$@"
    exit $?
fi

echo ""
echo "🧹 Step 1: Clearing TCC cache for Screen Recording..."

# Reset Screen Recording permissions for our bundle ID
tccutil reset ScreenCapture "$BUNDLE_ID" 2>/dev/null || echo "   (No existing permissions to reset)"

# Reset all Screen Recording permissions (more aggressive)
echo "🧹 Step 2: Full Screen Recording TCC reset..."
tccutil reset ScreenCapture 2>/dev/null || echo "   (TCC reset completed)"

echo ""
echo "🔄 Step 3: Restarting TCC daemon..."
killall tccd 2>/dev/null || echo "   (TCC daemon restarted)"

echo ""
echo "🏗️  Step 4: Build and install to stable location..."

# Find the Xcode project
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
echo "📁 Project directory: $PROJECT_DIR"

# Build the app to a stable location
STABLE_APP_PATH="/Applications/$APP_NAME.app"

if [ -d "$PROJECT_DIR/MacClient.xcodeproj" ]; then
    echo "🔨 Building app to stable location..."
    
    # Remove old stable app
    rm -rf "$STABLE_APP_PATH" 2>/dev/null
    
    # Build using xcodebuild
    cd "$PROJECT_DIR"
    xcodebuild -project MacClient.xcodeproj -scheme MacClient -configuration Debug -derivedDataPath ./build clean build
    
    # Copy to Applications
    if [ -d "./build/Build/Products/Debug/$APP_NAME.app" ]; then
        cp -R "./build/Build/Products/Debug/$APP_NAME.app" "$STABLE_APP_PATH"
        echo "✅ App installed to: $STABLE_APP_PATH"
        
        # Set proper permissions
        chmod +x "$STABLE_APP_PATH/Contents/MacOS/$APP_NAME"
        
        echo ""
        echo "🎯 SUCCESS! Next steps:"
        echo "1. 🖥️  Open System Preferences → Security & Privacy → Privacy → Screen Recording"
        echo "2. 🔓 Click the lock to make changes"
        echo "3. ➕ Click '+' and add: $STABLE_APP_PATH"
        echo "4. ✅ Enable the checkbox for $APP_NAME"
        echo "5. 🚀 Run the app from: $STABLE_APP_PATH"
        echo ""
        echo "💡 Always run from /Applications/ to avoid TCC cache issues!"
        
    else
        echo "❌ Build failed. Try building manually in Xcode first."
    fi
else
    echo "❌ Xcode project not found at: $PROJECT_DIR/MacClient.xcodeproj"
fi

echo ""
echo "🔄 Step 5: Final TCC refresh..."
sleep 2
killall tccd 2>/dev/null

echo "✅ TCC fix script completed!"
echo ""
echo "⚠️  IMPORTANT: You may need to restart your Mac for changes to take full effect."
