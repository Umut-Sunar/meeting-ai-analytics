#!/usr/bin/env python3
"""
Test Deepgram API direkt bağlantısı
"""
import asyncio
import websockets
import json
import os
import sys

# Backend path ekle
sys.path.insert(0, '.')

from app.core.config import get_settings

async def test_deepgram_direct():
    """Deepgram API'ye direkt bağlanıp test eder"""
    settings = get_settings()
    
    if not settings.DEEPGRAM_API_KEY:
        print('❌ Deepgram API key not set')
        return False
        
    print(f'✅ Deepgram API Key: {settings.DEEPGRAM_API_KEY[:20]}...')
    
    headers = {"Authorization": f"Token {settings.DEEPGRAM_API_KEY}"}
    params = {
        "model": "nova-2",
        "language": "tr", 
        "punctuate": "true",
        "encoding": "linear16",
        "sample_rate": "48000"
    }
    
    param_string = "&".join([f"{k}={v}" for k, v in params.items()])
    url = f"wss://api.deepgram.com/v1/listen?{param_string}"
    
    try:
        print(f'🔗 Connecting to: {url[:80]}...')
        async with websockets.connect(url, extra_headers=headers) as ws:
            print('✅ Deepgram connection successful!')
            
            # Test audio gönder
            test_chunk = b'\x00' * 1024  # 1KB sessizlik
            await ws.send(test_chunk)
            print('✅ Test audio sent')
            
            # Yanıt bekle
            try:
                response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                print(f'✅ Deepgram response: {response[:100]}...')
                return True
            except asyncio.TimeoutError:
                print('⚠️  No response (normal for silence)')
                return True
                
    except Exception as e:
        print(f'❌ Deepgram error: {e}')
        return False

if __name__ == "__main__":
    success = asyncio.run(test_deepgram_direct())
    sys.exit(0 if success else 1)
