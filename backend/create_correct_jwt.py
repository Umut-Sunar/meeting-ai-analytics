#!/usr/bin/env python3
"""
Create a correct JWT token using backend's own security functions
This ensures the token uses the same algorithm (RS256) as the backend expects
"""

from app.core.security import create_dev_jwt_token, decode_jwt_token
from datetime import datetime
import time

def create_and_test_jwt():
    print("🔑 Creating JWT Token with Backend's Security Functions")
    print("=" * 80)
    
    # Create token using backend's function (uses RS256 with private key)
    token = create_dev_jwt_token(
        user_id="test-user-001",
        tenant_id="test-tenant-001", 
        email="test@example.com",
        role="user"
    )
    
    print("Generated Token:")
    print(token)
    print()
    
    # Test the token immediately
    try:
        claims = decode_jwt_token(token)
        print("✅ Token Validation: SUCCESS")
        print(f"   User ID: {claims.user_id}")
        print(f"   Tenant ID: {claims.tenant_id}")
        print(f"   Email: {claims.email}")
        print(f"   Role: {claims.role}")
        print(f"   Expires: {datetime.fromtimestamp(claims.exp).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Algorithm: RS256 (with private key)")
        print()
        
        # Save to file
        with open("../CURRENT_JWT_TOKEN.txt", "w") as f:
            f.write(token)
        print("💾 Token saved to CURRENT_JWT_TOKEN.txt")
        
    except Exception as e:
        print(f"❌ Token Validation: FAILED - {e}")
        return None
    
    print("=" * 80)
    return token

if __name__ == "__main__":
    create_and_test_jwt()
