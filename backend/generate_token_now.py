#!/usr/bin/env python3
import sys
import time
import jwt
from datetime import datetime, timedelta

sys.path.insert(0, '.')

def create_long_jwt():
    """Create 24-hour JWT token manually"""
    
    # Current timestamp
    now = int(time.time())
    
    # Payload with 24-hour expiry
    payload = {
        "user_id": "test-user-001",
        "tenant_id": "test-tenant-001", 
        "email": "test@example.com",
        "role": "user",
        "exp": now + 86400,  # 24 hours from now
        "iat": now,
        "aud": "meetings",  # Default audience
        "iss": "our-app"    # Default issuer
    }
    
    # Use HS256 with default secret key
    secret_key = "your-secret-key-here-please-change-in-production"
    
    token = jwt.encode(payload, secret_key, algorithm="HS256")
    
    expiry_time = datetime.fromtimestamp(now + 86400)
    
    print("=" * 80)
    print("🔑 24-HOUR JWT TOKEN FOR BACKEND")
    print("=" * 80)
    print(f"Token: {token}")
    print("=" * 80)
    print(f"✅ Created at: {datetime.fromtimestamp(now).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"✅ Expires at: {expiry_time.strftime('%Y-%m-%d %H:%M:%S')} (24 hours)")
    print("✅ User: test@example.com")
    print("✅ Role: user")
    print("✅ Tenant: test-tenant-001")
    print("=" * 80)
    print("\n🚀 COPY THIS TOKEN AND USE IN MACCLIENT!")
    
    return token

if __name__ == "__main__":
    create_long_jwt()
