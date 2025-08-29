#!/usr/bin/env python3
"""
🔍 Debug Deepgram Bağlantısı - Gerçek Test
==========================================

Bu test GERÇEK Deepgram bağlantısını test eder ve logları izler.
Halüsinasyon yok, sadece gerçek veriler.
"""

import asyncio
import json
import websockets
import jwt
import time
import sys
import subprocess
import threading
from datetime import datetime

# Backend imports
sys.path.insert(0, '.')
from app.core.config import get_settings

def generate_jwt_token() -> str:
    """JWT token üret"""
    settings = get_settings()
    payload = {
        "user_id": "debug-user",
        "tenant_id": "debug-tenant", 
        "email": "debug@test.com",
        "role": "user",
        "exp": int(time.time()) + 3600,
        "iat": int(time.time()),
        "aud": settings.JWT_AUDIENCE,
        "iss": settings.JWT_ISSUER
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

async def test_single_deepgram_connection():
    """Tek bir Deepgram bağlantısını debug et"""
    
    print("🔍 DEBUG: Deepgram Bağlantısı Test Ediliyor...")
    print("=" * 60)
    
    # 1. Deepgram API key kontrol
    settings = get_settings()
    if not settings.DEEPGRAM_API_KEY:
        print("❌ DEEPGRAM_API_KEY bulunamadı!")
        return False
        
    print(f"✅ API Key: {settings.DEEPGRAM_API_KEY[:20]}...")
    print(f"📍 Endpoint: {settings.DEEPGRAM_ENDPOINT}")
    
    # 2. Backend WebSocket bağlantısı
    jwt_token = generate_jwt_token()
    meeting_id = f"debug-{int(time.time())}"
    
    print(f"\n📋 Meeting ID: {meeting_id}")
    print(f"🔑 JWT: {jwt_token[:30]}...")
    
    # 3. WebSocket bağlan
    url = f"ws://localhost:8000/api/v1/ws/ingest/meetings/{meeting_id}?source=mic"
    print(f"\n🔗 Connecting to: {url}")
    
    try:
        async with websockets.connect(
            url,
            additional_headers={"Authorization": f"Bearer {jwt_token}"}
        ) as ws:
            print("✅ WebSocket connected")
            
            # 4. Handshake gönder
            handshake = {
                "type": "handshake",
                "source": "mic",
                "sample_rate": 48000,
                "channels": 1,
                "language": "tr",
                "ai_mode": "standard",
                "device_id": "debug-device"
            }
            
            await ws.send(json.dumps(handshake))
            print("📤 Handshake sent")
            
            # 5. Response'ları dinle
            print("\n👂 Listening for responses...")
            responses = []
            
            for i in range(5):  # 5 mesaj bekle
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=3.0)
                    responses.append(response)
                    
                    try:
                        data = json.loads(response)
                        print(f"📨 Response {i+1}: {data}")
                        
                        # Success message arıyoruz
                        if data.get('status') == 'success':
                            print(f"🎉 SUCCESS MESSAGE ALINDI!")
                            print(f"   Session ID: {data.get('session_id')}")
                            
                            # Test PCM gönder
                            print(f"\n🎵 Test PCM data gönderiliyor...")
                            test_pcm = b'\x00\x01' * 960  # 20ms sample at 48kHz
                            await ws.send(test_pcm)
                            print(f"✅ PCM data sent: {len(test_pcm)} bytes")
                            
                            # Transcript bekle
                            print(f"👂 Transcript bekleniyor...")
                            await asyncio.sleep(2)
                            break
                            
                    except json.JSONDecodeError:
                        print(f"📨 Non-JSON Response {i+1}: {response[:100]}...")
                        
                except asyncio.TimeoutError:
                    print(f"⏰ Timeout on response {i+1}")
                    
            return len(responses) > 0
            
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        return False

async def check_backend_logs():
    """Backend loglarını kontrol et"""
    print(f"\n📋 Backend Log Kontrol:")
    print("-" * 40)
    
    # Backend process'i bul
    try:
        result = subprocess.run([
            "ps", "aux"
        ], capture_output=True, text=True)
        
        for line in result.stdout.split('\n'):
            if 'uvicorn' in line and 'app.main:app' in line:
                print(f"✅ Backend running: PID {line.split()[1]}")
                return True
                
        print(f"❌ Backend process bulunamadı!")
        return False
        
    except Exception as e:
        print(f"❌ Process check error: {e}")
        return False

async def main():
    """Ana test fonksiyonu"""
    print("🚀 DEBUG: Deepgram Integration Test")
    print("=" * 60)
    
    # 1. Backend kontrol
    backend_ok = await check_backend_logs()
    if not backend_ok:
        print("❌ Backend çalışmıyor!")
        return
    
    # 2. Deepgram test
    success = await test_single_deepgram_connection()
    
    # 3. Sonuç
    print(f"\n{'=' * 60}")
    if success:
        print("✅ TEST TAMAMLANDI - Responses alındı")
        print("💡 Backend terminal loglarını kontrol edin:")
        print("   - '🔗 Connecting to Deepgram' mesajını arayın")
        print("   - '✅ Deepgram connected' mesajını arayın")
    else:
        print("❌ TEST BAŞARISIZ - Bağlantı kurulamadı")
    
    print(f"\n📊 HALÜSİNASYON KONTROLÜ:")
    print(f"   - WebSocket bağlantısı: {'✅' if success else '❌'}")
    print(f"   - Deepgram dashboard kontrol edin")
    print(f"   - Backend terminal loglarını kontrol edin")

if __name__ == "__main__":
    asyncio.run(main())
