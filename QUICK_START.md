# 🚀 Analytics System - Quick Start Guide

## 📝 Prerequisites

- **macOS** (for desktop client)
- **Python 3.8+** 
- **Redis** (will be auto-installed via Homebrew if missing)
- **Xcode** (for macOS client development)

## 🏁 Quick Start (3 Steps)

### 1. Make Scripts Executable
```bash
chmod +x *.sh
```

### 2. Start the System
```bash
./start_system.sh
```

This will:
- ✅ Start Redis server (localhost:6379)
- ✅ Create Python virtual environment
- ✅ Install dependencies
- ✅ Start FastAPI backend (localhost:8000)

### 3. Open MacClient in Xcode
```bash
open desktop/macos/MacClient/MacClient.xcodeproj
```

## 🔧 Manual Control

### Start/Stop Redis Only
```bash
./start_redis.sh    # Start Redis
./stop_redis.sh     # Stop Redis
```

### Start Backend Only
```bash
cd backend
source venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 📊 System Status

### Check if Services are Running
```bash
# Redis
redis-cli ping

# Backend
curl http://localhost:8000/api/v1/health
```

### View Logs
```bash
# Backend logs (in terminal where you started it)
# Redis logs
redis-cli monitor
```

## 🎯 API Endpoints

- **Health Check:** http://localhost:8000/api/v1/health
- **API Docs:** http://localhost:8000/docs
- **WebSocket Ingest:** ws://localhost:8000/api/v1/ws/ingest/meetings/{meeting_id}
- **WebSocket Transcript:** ws://localhost:8000/api/v1/transcript/{meeting_id}

## 🚫 Troubleshooting

### Redis Connection Failed
```bash
# Check if Redis is running
ps aux | grep redis

# Restart Redis
./stop_redis.sh
./start_redis.sh
```

### Backend Won't Start
```bash
# Check Python version
python3 --version

# Recreate virtual environment
rm -rf backend/venv
./start_system.sh
```

### MacClient Build Errors
```bash
# Clean Xcode build
Product > Clean Build Folder (Cmd+Shift+K)

# Check Swift version
swift --version
```

## 📝 Configuration

### Backend Configuration
- **Config File:** `backend/app/core/config.py`
- **Environment:** `backend/.env`
- **Redis URL:** `redis://localhost:6379/0`
- **Sample Rate:** `16000 Hz` (standardized)

### MacClient Configuration
- **Target Sample Rate:** `16 kHz`
- **Echo Cancellation:** Enabled
- **Device Change Handling:** Automatic
- **WebSocket Retry:** Enabled with exponential backoff

## ✅ System Features

- 🎤 **Dual Audio Capture:** Microphone + System Audio
- 🔊 **Echo Cancellation:** Prevents mic/speaker feedback
- 🎧 **AirPods Support:** Automatic device change handling
- 🔄 **Auto-Restart:** Robust error recovery
- 📊 **Real-time Transcription:** Via Deepgram API
- 🔌 **WebSocket Streaming:** Low-latency audio transport
- 📊 **Redis Pub/Sub:** Real-time transcript distribution

## 🔒 Security Notes

- **Development Mode:** Redis runs without password
- **JWT Authentication:** Required for WebSocket connections
- **Local Network Only:** Backend binds to 0.0.0.0:8000

---

**🎉 System is now ready for development and testing!**
