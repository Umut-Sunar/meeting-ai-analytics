#!/usr/bin/env python3
"""
🔍 Handshake Validation Test
===========================

Backend'teki handshake validation'ın çalışıp çalışmadığını test eder.
"""

import json
import sys

# Backend imports
sys.path.insert(0, '.')
from app.services.ws.messages import IngestHandshakeMessage

def test_handshake_validation():
    """Handshake validation test et"""
    
    print("🔍 Handshake Validation Test")
    print("=" * 40)
    
    # Test handshake (debug_deepgram_test.py'den)
    handshake = {
        "type": "handshake",
        "source": "mic",
        "sample_rate": 48000,
        "channels": 1,
        "language": "tr",
        "ai_mode": "standard",
        "device_id": "debug-device"
    }
    
    print(f"📤 Test Handshake:")
    print(json.dumps(handshake, indent=2))
    
    # JSON serialize
    try:
        hs_data = json.dumps(handshake)
        print(f"\n✅ JSON serialization OK")
    except Exception as e:
        print(f"\n❌ JSON serialization failed: {e}")
        return False
    
    # Pydantic validation
    try:
        hs = IngestHandshakeMessage.model_validate_json(hs_data)
        print(f"✅ Pydantic validation OK")
        print(f"   Source: {hs.source}")
        print(f"   Sample rate: {hs.sample_rate}")
        print(f"   Language: {hs.language}")
        return True
        
    except Exception as e:
        print(f"❌ Pydantic validation FAILED: {e}")
        
        # Detailed error
        try:
            import traceback
            traceback.print_exc()
        except:
            pass
            
        return False

if __name__ == "__main__":
    success = test_handshake_validation()
    
    print(f"\n{'=' * 40}")
    if success:
        print("✅ HANDSHAKE VALIDATION ÇALIŞIYOR")
        print("   Problem başka yerde")
    else:
        print("❌ HANDSHAKE VALIDATION BAŞARISIZ")
        print("   Bu yüzden Deepgram connection açılmıyor!")
