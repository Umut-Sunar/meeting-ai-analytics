#!/usr/bin/env python3
"""
Development JWT Token Generator for MacClient
Generates a JWT token that can be used for testing the MacClient → Backend WebSocket flow.
"""

import sys
import os
from pathlib import Path

# Add backend path to import backend modules
backend_path = Path(__file__).parent.parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

try:
    from app.core.security import create_dev_jwt_token
except ImportError as e:
    print(f"❌ Failed to import backend security module: {e}")
    print(f"Make sure you're running this from the project root and backend dependencies are installed.")
    sys.exit(1)

def main():
    """Generate development JWT token"""
    
    # Default development credentials
    user_id = "dev-user-001"
    tenant_id = "dev-tenant-001" 
    email = "dev@example.com"
    
    # Allow override via command line arguments
    if len(sys.argv) >= 2:
        user_id = sys.argv[1]
    if len(sys.argv) >= 3:
        tenant_id = sys.argv[2]
    if len(sys.argv) >= 4:
        email = sys.argv[3]
    
    try:
        print("🔐 Generating development JWT token...")
        print(f"👤 User ID: {user_id}")
        print(f"🏢 Tenant ID: {tenant_id}")
        print(f"📧 Email: {email}")
        print()
        
        # Generate JWT token
        token = create_dev_jwt_token(user_id, tenant_id, email)
        
        print("✅ JWT Token generated successfully!")
        print(f"🎫 Token: {token}")
        print()
        print("📋 Copy this token and paste it in MacClient Settings")
        print("💡 Token expires in 24 hours (development setting)")
        print()
        
        # Also save to a file for easy access
        token_file = Path(__file__).parent / "dev_jwt_token.txt"
        with open(token_file, 'w') as f:
            f.write(token)
        print(f"💾 Token also saved to: {token_file}")
        
    except Exception as e:
        print(f"❌ Failed to generate JWT token: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
