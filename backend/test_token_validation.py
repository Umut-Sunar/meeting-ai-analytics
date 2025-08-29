#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

from app.core.security import decode_jwt_token, SecurityError

# Test the correct token from debug_secret_key.py
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoidGVzdC11c2VyLTAwMSIsInRlbmFudF9pZCI6InRlc3QtdGVuYW50LTAwMSIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsInJvbGUiOiJ1c2VyIiwiZXhwIjoxNzU2NDk0MjY5LCJpYXQiOjE3NTY0MDc4NjksImF1ZCI6Im1lZXRpbmdzIiwiaXNzIjoib3VyLWFwcCJ9.n2p7AUS7IHhIYgWh0yidugcKNR0tK59baRpHi-tAwgc"

print("Testing JWT token validation with backend's decode_jwt_token function...")
print(f"Token: {token[:50]}...")

try:
    claims = decode_jwt_token(token)
    print("✅ SUCCESS: Token validated successfully!")
    print(f"User ID: {claims.user_id}")
    print(f"Email: {claims.email}")
    print(f"Tenant: {claims.tenant_id}")
    print(f"Role: {claims.role}")
except SecurityError as e:
    print(f"❌ FAILED: SecurityError - {e}")
except Exception as e:
    print(f"❌ FAILED: {type(e).__name__} - {e}")
