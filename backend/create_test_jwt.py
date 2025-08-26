#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

from app.core.security import create_dev_jwt_token

# Test JWT oluştur
token = create_dev_jwt_token(
    user_id="test-user-001",
    tenant_id="test-tenant-001", 
    email="test@example.com",
    role="user"
)

print(token)
