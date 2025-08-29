#!/bin/bash

echo "🧪 MacClient Single Launch Test"
echo "==============================="

# Kill any existing instances
echo "🔄 Killing existing MacClient processes..."
killall MacClient 2>/dev/null || echo "   (No existing processes)"

# Wait a moment
sleep 1

# Check for processes before launch
echo "📊 Processes before launch:"
ps aux | grep -i macclient | grep -v grep || echo "   (No MacClient processes)"

echo ""
echo "🚀 Launching MacClient from Xcode build..."
echo "   Path: ~/Library/Developer/Xcode/DerivedData/MacClient-*/Build/Products/Debug/MacClient.app"

# Find the latest build
BUILD_PATH=$(find ~/Library/Developer/Xcode/DerivedData -name "MacClient.app" -path "*/Debug/*" 2>/dev/null | head -1)

if [ -n "$BUILD_PATH" ]; then
    echo "   Found: $BUILD_PATH"
    open "$BUILD_PATH"
    
    # Wait for launch
    sleep 3
    
    echo ""
    echo "📊 Processes after launch:"
    ps aux | grep -i macclient | grep -v grep
    
    PROCESS_COUNT=$(ps aux | grep -i macclient | grep -v grep | wc -l)
    echo ""
    echo "🎯 Total MacClient processes: $PROCESS_COUNT"
    
    if [ "$PROCESS_COUNT" -eq 1 ]; then
        echo "✅ SUCCESS: Single process launched!"
    else
        echo "❌ PROBLEM: Multiple processes detected!"
        echo ""
        echo "💡 Try these solutions:"
        echo "1. Clean Build Folder (⌘+Shift+K)"
        echo "2. Restart Xcode"
        echo "3. Restart Mac"
    fi
else
    echo "❌ No MacClient.app found in DerivedData"
    echo "💡 Build the project first (⌘+B)"
fi
