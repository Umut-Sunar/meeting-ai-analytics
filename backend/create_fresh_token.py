#!/usr/bin/env python3
"""
Create a fresh 24-hour JWT token for immediate testing
"""
import jwt
import time
from datetime import datetime, timedelta

def create_fresh_token():
    # Current timestamp (December 2024)
    now = int(time.time())
    
    # 24 hours from now
    exp = now + 86400
    
    payload = {
        "user_id": "test-user-001",
        "tenant_id": "test-tenant-001", 
        "email": "test@example.com",
        "role": "user",
        "exp": exp,
        "iat": now,
        "aud": "meetings",
        "iss": "our-app"
    }
    
    # Secret key from backend config
    secret_key = "dev-only-change"
    
    token = jwt.encode(payload, secret_key, algorithm="HS256")
    
    print("🔑 FRESH 24-HOUR JWT TOKEN")
    print("=" * 80)
    print(token)
    print("=" * 80)
    print(f"Created: {datetime.fromtimestamp(now).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Expires: {datetime.fromtimestamp(exp).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Valid for: 24 hours")
    print("=" * 80)
    
    return token

if __name__ == "__main__":
    create_fresh_token()
