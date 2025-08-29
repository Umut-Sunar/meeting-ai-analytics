#!/usr/bin/env python3
"""
Backend ile aynı SECRET_KEY kullanan doğru JWT token oluşturur
"""
import sys
import time
import jwt
from datetime import datetime

sys.path.insert(0, '.')

def create_correct_jwt():
    """Backend ile aynı SECRET_KEY kullanarak JWT oluştur"""
    
    # Backend'in kullandığı aynı SECRET_KEY
    secret_key = "dev-only-change"  # config.py'deki değer
    
    now = int(time.time())
    
    payload = {
        "user_id": "test-user-001",
        "tenant_id": "test-tenant-001", 
        "email": "test@example.com",
        "role": "user",
        "exp": now + 86400,  # 24 saat
        "iat": now,
        "aud": "meetings",
        "iss": "our-app"
    }
    
    token = jwt.encode(payload, secret_key, algorithm="HS256")
    expiry_time = datetime.fromtimestamp(now + 86400)
    
    print("=" * 80)
    print("🔑 CORRECTED JWT TOKEN (matches backend SECRET_KEY)")
    print("=" * 80)
    print(f"Token: {token}")
    print("=" * 80)
    print(f"✅ Created at: {datetime.fromtimestamp(now).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"✅ Expires at: {expiry_time.strftime('%Y-%m-%d %H:%M:%S')} (24 hours)")
    print("✅ User: test@example.com")
    print("✅ Role: user")
    print("✅ Tenant: test-tenant-001")
    print("✅ SECRET_KEY: dev-only-change (matches backend)")
    print("=" * 80)
    
    # Test decoding
    try:
        decoded = jwt.decode(token, secret_key, algorithms=["HS256"], audience="meetings", issuer="our-app")
        print("✅ TOKEN VALIDATION: SUCCESS")
        print(f"✅ User ID: {decoded['user_id']}")
        print(f"✅ Email: {decoded['email']}")
    except Exception as e:
        print(f"❌ TOKEN VALIDATION FAILED: {e}")
    
    print("=" * 80)
    print("\n🚀 USE THIS TOKEN IN MACCLIENT!")
    return token

if __name__ == "__main__":
    create_correct_jwt()
