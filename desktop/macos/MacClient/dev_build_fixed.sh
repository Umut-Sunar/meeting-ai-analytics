#!/bin/bash
set -e

echo "🔧 MacClient Fixed Path Build Starting..."
echo "========================================"

PROJECT_DIR="/Users/doganumutsunar/analytics-system/desktop/macos/MacClient"
FIXED_APP_PATH="/Applications/MacClient-Dev.app"
SCHEME="MacClient"

cd "$PROJECT_DIR"

# Clean previous build
echo "🧹 Cleaning previous build..."
xcodebuild -project MacClient.xcodeproj -scheme "$SCHEME" -configuration Debug clean -quiet

# Build the project
echo "🔧 Building MacClient..."
xcodebuild -project MacClient.xcodeproj -scheme "$SCHEME" -configuration Debug -derivedDataPath ./DerivedData -quiet

# Find the built app
BUILT_APP=$(find ./DerivedData/Build/Products/Debug -name "MacClient.app" -type d | head -1)

if [ -z "$BUILT_APP" ]; then
    echo "❌ Build failed - MacClient.app not found!"
    exit 1
fi

echo "📱 Built app found: $BUILT_APP"

# Remove old fixed app if exists
if [ -e "$FIXED_APP_PATH" ]; then
    echo "🗑️  Removing old fixed app..."
    sudo rm -rf "$FIXED_APP_PATH"
fi

# Copy to fixed location
echo "📋 Copying to fixed location..."
sudo cp -R "$BUILT_APP" "$FIXED_APP_PATH"

# Set proper permissions
sudo chown -R $(whoami):staff "$FIXED_APP_PATH"
sudo chmod +x "$FIXED_APP_PATH/Contents/MacOS/MacClient"

echo "✅ MacClient ready at: $FIXED_APP_PATH"
echo "🔒 TCC permissions will persist across builds!"
echo ""
