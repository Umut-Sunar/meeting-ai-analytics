#!/usr/bin/env python3
"""
Debug JWT token validation
"""

from app.core.security import decode_jwt_token, SecurityError
from datetime import datetime

def test_jwt_token():
    jwt_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoidGVzdC11c2VyLTAwMSIsInRlbmFudF9pZCI6InRlc3QtdGVuYW50LTAwMSIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsInJvbGUiOiJ1c2VyIiwiZXhwIjoxNzU2NjgzMzUzLCJpYXQiOjE3NTY1OTY5NTMsImF1ZCI6Im1lZXRpbmdzIiwiaXNzIjoib3VyLWFwcCJ9.jVeHk5a52u_zogEg-nQuRkYNACdln0ytOoO5BIACDgMRBlaQq82bvXEl_Ua3P2wqp0OOe_de9-5oOznlaO6C-_8P7RofhlLCYiOnjWDnOoY0EMBtr8o1MotawacYcNc2Vkyd7t_7kqKGW_oF9gGe6I_RQ-Tq6ummOnJ9WLeuOQhnH6EesE6PVxTdMdw2P4XahcSTB3BzDYeedPrx3U_BUFfzDPiqv4QQlVJNCrlHM0TyfjrQm9EcjLRDgARM2jlz2Ig9b7jiwWdP-SI9q4IsxhliS6ZxGDETypEvzFNSBXRC17Iz8nd-pgpTwHhdlnH9JiH8hIZ4hgT-FrInK0r7VQ"
    
    print("🔍 Testing JWT Token Validation")
    print("=" * 50)
    
    try:
        claims = decode_jwt_token(jwt_token)
        print("✅ JWT Token is VALID!")
        print(f"   User ID: {claims.user_id}")
        print(f"   Tenant ID: {claims.tenant_id}")
        print(f"   Email: {claims.email}")
        print(f"   Role: {claims.role}")
        print(f"   Expires: {datetime.fromtimestamp(claims.exp).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Audience: {claims.aud}")
        print(f"   Issuer: {claims.iss}")
        
        # Check if token is expired
        now = datetime.now().timestamp()
        if claims.exp < now:
            print("❌ Token is EXPIRED!")
        else:
            print("✅ Token is still valid")
            
    except SecurityError as e:
        print(f"❌ JWT Token INVALID: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    test_jwt_token()
