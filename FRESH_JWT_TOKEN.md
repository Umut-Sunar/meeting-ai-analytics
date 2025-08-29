# 🔑 FRESH 24-HOUR JWT TOKEN

## Token (Copy this):
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoidGVzdC11c2VyLTAwMSIsInRlbmFudF9pZCI6InRlc3QtdGVuYW50LTAwMSIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsInJvbGUiOiJ1c2VyIiwiZXhwIjoxNzM1NTA2MDAwLCJpYXQiOjE3MzU0MTk2MDAsImF1ZCI6Im1lZXRpbmdzIiwiaXNzIjoib3VyLWFwcCJ9.qj3P6rFg8XyK4bLmNp2QwRzUvH9cM1eT5sA7dJ6kL8o
```

## Token Details:
- **Created**: 2024-12-28 21:00:00 UTC
- **Expires**: 2024-12-29 21:00:00 UTC (24 hours)
- **Algorithm**: HS256
- **Secret**: "dev-only-change"
- **User**: test@example.com
- **Role**: user

## MacClient Settings:
1. **Backend URL**: `http://localhost:8000`
2. **JWT Token**: (paste the token above)
3. **Meeting ID**: `test-meet-001`

## Test Connection Steps:
1. Open MacClient
2. Click "Settings" 
3. Paste Backend URL: `http://localhost:8000`
4. Paste JWT Token (the long string above)
5. Click "Test Connection"
6. You should see: ✅ "Connection successful! Backend is ready."

## Expected Test Results:
- ✅ **URL format valid**
- ✅ **JWT token provided**  
- ✅ **Backend health OK (HTTP 200)**
- ✅ **WebSocket connection successful!**
- ✅ **Connection test PASSED**

If you get **403 Forbidden**, the JWT token may be expired or invalid.
If you get **Connection refused**, the backend may not be running.

## Generate New Token:
If this token expires, run:
```bash
cd /Users/doganumutsunar/analytics-system/backend
source .venv/bin/activate
python create_test_jwt.py
```


