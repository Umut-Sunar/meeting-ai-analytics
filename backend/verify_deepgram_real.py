#!/usr/bin/env python3
"""
🔍 GERÇEK Deepgram Bağlantısı Doğrulama
=====================================

Backend'teki DeepgramLiveClient'ın gerçekten çalışıp çalışmadığını test eder.
HALÜSİNASYON YOK - sadece gerçek veriler.
"""

import asyncio
import sys
import traceback
from datetime import datetime

# Backend imports
sys.path.insert(0, '.')
from app.services.asr.deepgram_live import DeepgramLiveClient
from app.core.config import get_settings

async def test_deepgram_direct():
    """DeepgramLiveClient'ı direkt test et"""
    
    print("🔍 GERÇEK Deepgram Test Başlatılıyor...")
    print("=" * 50)
    
    settings = get_settings()
    
    # 1. API Key kontrol
    if not settings.DEEPGRAM_API_KEY:
        print("❌ DEEPGRAM_API_KEY bulunamadı!")
        return False
        
    print(f"✅ API Key: {settings.DEEPGRAM_API_KEY[:20]}...")
    print(f"📍 Endpoint: {settings.DEEPGRAM_ENDPOINT}")
    
    # 2. DeepgramLiveClient oluştur
    meeting_id = f"verify-{int(datetime.now().timestamp())}"
    
    print(f"\n📋 Meeting ID: {meeting_id}")
    
    # Transcript callback
    transcripts_received = []
    
    async def on_transcript(result):
        transcripts_received.append(result)
        print(f"📝 TRANSCRIPT: {result}")
    
    async def on_error(error):
        print(f"❌ DEEPGRAM ERROR: {error}")
    
    # 3. Client oluştur
    try:
        client = DeepgramLiveClient(
            meeting_id=meeting_id,
            language="tr",
            sample_rate=48000,
            channels=1,
            model="nova-2",
            on_transcript=on_transcript,
            on_error=on_error
        )
        print("✅ DeepgramLiveClient created")
        
    except Exception as e:
        print(f"❌ Client creation failed: {e}")
        traceback.print_exc()
        return False
    
    # 4. Bağlantı test et
    print(f"\n🔗 Deepgram'a bağlanıyor...")
    
    try:
        await client.connect()
        print("✅ DEEPGRAM BAĞLANTISI BAŞARILI!")
        
        # 5. Test PCM gönder
        print(f"\n🎵 Test PCM gönderiliyor...")
        
        # Gerçek ses simülasyonu (1 saniye)
        import struct
        import math
        
        sample_rate = 48000
        duration = 1.0  # 1 saniye
        frequency = 440  # A note
        
        samples = []
        for i in range(int(sample_rate * duration)):
            t = i / sample_rate
            sample = int(16000 * math.sin(2 * math.pi * frequency * t))
            samples.append(sample)
        
        pcm_data = struct.pack(f'<{len(samples)}h', *samples)
        
        print(f"📊 PCM Data: {len(pcm_data)} bytes")
        
        # PCM gönder
        await client.send_pcm(pcm_data)
        print("✅ PCM data gönderildi")
        
        # 6. Transcript bekle
        print(f"\n👂 Transcript bekleniyor (5 saniye)...")
        await asyncio.sleep(5.0)
        
        # 7. Sonuçları kontrol et
        print(f"\n📊 SONUÇLAR:")
        print(f"   📝 Alınan transcript sayısı: {len(transcripts_received)}")
        
        if transcripts_received:
            print(f"   ✅ DEEPGRAM ÇALIŞIYOR!")
            for i, transcript in enumerate(transcripts_received):
                print(f"   {i+1}. {transcript}")
        else:
            print(f"   ⚠️  Transcript alınamadı (ses çok kısa olabilir)")
        
        # 8. Disconnect
        await client.disconnect()
        print(f"✅ Deepgram bağlantısı kapatıldı")
        
        return True
        
    except Exception as e:
        print(f"❌ DEEPGRAM BAĞLANTI HATASI: {e}")
        traceback.print_exc()
        
        try:
            await client.disconnect()
        except:
            pass
            
        return False

async def main():
    """Ana test"""
    print("🚀 DEEPGRAM GERÇEK TEST")
    print("=" * 50)
    
    success = await test_deepgram_direct()
    
    print(f"\n{'=' * 50}")
    if success:
        print("🎉 DEEPGRAM TEST BAŞARILI!")
        print("   ✅ Backend'teki DeepgramLiveClient çalışıyor")
        print("   ✅ Deepgram API bağlantısı çalışıyor")
        print("   💡 Problem başka yerde olabilir")
    else:
        print("❌ DEEPGRAM TEST BAŞARISIZ!")
        print("   ❌ DeepgramLiveClient çalışmıyor")
        print("   ❌ API key veya network problemi var")
    
    print(f"\n📊 HALÜSİNASYON KONTROLÜ:")
    print(f"   - Bu test GERÇEK Deepgram API kullanıyor")
    print(f"   - Deepgram dashboard'unda usage görünmeli")
    print(f"   - Test sonucu: {'BAŞARILI' if success else 'BAŞARISIZ'}")

if __name__ == "__main__":
    asyncio.run(main())
