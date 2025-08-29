#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

from app.core.config import get_settings

settings = get_settings()
print(f"Backend is using SECRET_KEY: '{settings.SECRET_KEY}'")
print(f"JWT_AUDIENCE: '{settings.JWT_AUDIENCE}'")
print(f"JWT_ISSUER: '{settings.JWT_ISSUER}'")

# Test creating a token with this secret
import jwt
import time

payload = {
    "user_id": "test-user-001",
    "tenant_id": "test-tenant-001", 
    "email": "test@example.com",
    "role": "user",
    "exp": int(time.time()) + 86400,  # 24 hours
    "iat": int(time.time()),
    "aud": settings.JWT_AUDIENCE,
    "iss": settings.JWT_ISSUER
}

correct_token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
print(f"\nCorrect token with backend's actual SECRET_KEY:")
print(correct_token)
