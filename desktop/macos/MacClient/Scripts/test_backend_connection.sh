#!/bin/bash
# Test script for MacClient → Backend WebSocket connection

echo "🔧 Testing Backend WebSocket Connection"
echo "======================================="

# Check if backend is running
echo "📡 Checking if backend is running..."
if curl -s http://localhost:8000/api/v1/health > /dev/null; then
    echo "✅ Backend is running at http://localhost:8000"
else
    echo "❌ Backend is not running. Please start it with:"
    echo "   cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
    exit 1
fi

# Generate JWT token
echo ""
echo "🔐 Generating JWT token..."
cd "$(dirname "$0")"
if python3 generate_dev_jwt.py; then
    echo ""
    echo "✅ JWT token generated successfully!"
    echo "📋 Token has been saved to Scripts/dev_jwt_token.txt"
    echo ""
    echo "🎯 Next steps:"
    echo "1. Copy the JWT token"
    echo "2. Open MacClient in Xcode"
    echo "3. Run the app"
    echo "4. Click Settings and paste the JWT token"
    echo "5. Set Backend URL to: ws://localhost:8000"
    echo "6. Set Meeting ID (e.g., test-001) and Device ID"
    echo "7. Click 'Start Meeting' then 'Start' to begin capture"
    echo ""
    echo "🔍 Monitor backend logs for WebSocket connections"
    echo "🎧 Test with audio to see real-time transcription"
else
    echo "❌ Failed to generate JWT token"
    exit 1
fi
