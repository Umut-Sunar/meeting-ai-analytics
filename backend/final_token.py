#!/usr/bin/env python3
import jwt
import time
from datetime import datetime

def create_token():
    now = int(time.time())
    
    payload = {
        "user_id": "test-user-001",
        "tenant_id": "test-tenant-001", 
        "email": "test@example.com",
        "role": "user",
        "exp": now + 86400,  # 24 hours
        "iat": now,
        "aud": "meetings",
        "iss": "our-app"
    }
    
    # Backend'in kullandığı SECRET_KEY
    secret_key = "dev-only-change"
    
    token = jwt.encode(payload, secret_key, algorithm="HS256")
    
    print("🔑 24-HOUR JWT TOKEN:")
    print("=" * 120)
    print(token)
    print("=" * 120)
    print(f"Valid until: {datetime.fromtimestamp(now + 86400)}")
    
    return token

if __name__ == "__main__":
    create_token()
