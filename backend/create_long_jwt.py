#!/usr/bin/env python3
"""
Create a long-lasting JWT token for development testing.
Token expires in 24 hours instead of 1 hour.
"""
import sys
import time
from datetime import datetime, timedelta

sys.path.insert(0, '.')

from app.core.security import create_dev_jwt_token

def main():
    # Create long-lasting JWT token
    token = create_dev_jwt_token(
        user_id="test-user-001",
        tenant_id="test-tenant-001", 
        email="test@example.com",
        role="user"
    )
    
    # Calculate expiry time for display
    expiry_time = datetime.now() + timedelta(hours=24)
    
    print("=" * 60)
    print("🔑 LONG-LASTING JWT TOKEN (24 HOURS)")
    print("=" * 60)
    print(f"Token: {token}")
    print("=" * 60)
    print(f"✅ Valid until: {expiry_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("✅ User: test@example.com")
    print("✅ Meeting ID: test-meet-001 (recommended)")
    print("✅ Backend URL: http://localhost:8000")
    print("=" * 60)
    print("\n🚀 Copy the token above and use it in MacClient!")

if __name__ == "__main__":
    main()
