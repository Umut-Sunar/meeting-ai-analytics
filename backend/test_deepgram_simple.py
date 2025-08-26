#!/usr/bin/env python3
"""
Simple Deepgram connection test
"""
import asyncio
import websockets
import json
import sys

# Backend path ekle
sys.path.insert(0, '.')

from app.core.config import get_settings

async def test_deepgram_simple():
    """Basit Deepgram bağlantı testi"""
    settings = get_settings()
    
    if not settings.DEEPGRAM_API_KEY:
        print('❌ Deepgram API key not set')
        return False
        
    print(f'✅ Deepgram API Key: {settings.DEEPGRAM_API_KEY[:20]}...')
    
    # Basit URL
    url = "wss://api.deepgram.com/v1/listen?model=nova-2&language=tr&encoding=linear16&sample_rate=48000"
    
    try:
        print(f'🔗 Connecting to Deepgram...')
        
        # Header manual olarak geç
        websocket = await websockets.connect(
            url, 
            additional_headers={
                "Authorization": f"Token {settings.DEEPGRAM_API_KEY}"
            }
        )
        print('✅ Deepgram connection successful!')
        
        # Test ses gönder
        test_chunk = b'\x00' * 512  # 512 byte sessizlik
        await websocket.send(test_chunk)
        print('✅ Test audio sent')
        
        # Yanıt bekle
        try:
            response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
            print(f'✅ Response: {response[:80]}...')
        except asyncio.TimeoutError:
            print('⚠️  No response (expected for silence)')
            
        await websocket.close()
        return True
                
    except Exception as e:
        print(f'❌ Deepgram error: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_deepgram_simple())
    sys.exit(0 if success else 1)
