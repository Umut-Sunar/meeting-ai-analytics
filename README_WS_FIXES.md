# WebSocket Connection Fixes - Analytics System

## 🔍 Problems Identified

### 1. JWT Secret Key Mismatch (403 Forbidden)
- **Root Cause**: Different SECRET_KEY values between token generation and backend validation
- **Token Generator**: `"your-secret-key-here-please-change-in-production"`
- **Backend Config**: `"dev-only-change"`
- **Solution**: Created `fix_jwt_secret.py` that uses the same SECRET_KEY as backend

### 2. WebSocket URL Scheme Issues (-1011 Bad Server Response)
- **Root Cause**: Using `http://` scheme instead of `ws://` for WebSocket connections
- **MacClient Error**: NSURLErrorDomain Code=-1011 WebSocket handshake failure
- **Solution**: Implemented `WSURLBuilder` for proper scheme handling

### 3. Token Transport & Sanitization
- **Root Cause**: JWT tokens with newlines (%0A) in query parameters
- **Solution**: 
  - Token sanitization via `TokenSanitizer`
  - Authorization header (Bearer token) as primary method
  - Query parameter as fallback

## ✅ Fixes Implemented

### Phase 1: Core Infrastructure

1. **JWT Token Generator** (`fix_jwt_secret.py`)
   ```bash
   cd backend && python fix_jwt_secret.py
   ```
   - Uses backend's actual SECRET_KEY: `"dev-only-change"`
   - Validates token after creation
   - 24-hour expiry

2. **Token Sanitizer** (`Security/TokenSanitizer.swift`)
   ```swift
   let cleanToken = TokenSanitizer.sanitize(rawToken)
   let masked = TokenSanitizer.maskForLogging(cleanToken)
   ```
   - Removes newlines and whitespace
   - URL decoding for encoded characters
   - Safe logging with masking

3. **WebSocket URL Builder** (`Networking/WSURLBuilder.swift`)
   ```swift
   let url = WSURLBuilder.buildLocal(
       host: "127.0.0.1",
       port: 8000,
       path: "/api/v1/ws/ingest/meetings/test-connection"
   )
   ```
   - Enforces `ws://` (local) and `wss://` (production) schemes
   - Environment-aware configuration
   - Proper URL component handling

4. **Backend Authorization Support** (`app/routers/ws.py`)
   - Authorization header support: `Bearer <JWT>`
   - Query parameter fallback
   - Token sanitization on backend

### Phase 2: Updated Components

1. **BackendIngestWS.swift**
   - Uses `WSURLBuilder` for URL construction
   - Token sanitization with `TokenSanitizer`
   - Authorization header as primary transport
   - Proper WebSocket headers

2. **SettingsView.swift**
   - JWT validation and sanitization
   - Improved error messages
   - Masked token logging

## 🧪 Testing

### 1. Generate Correct JWT Token
```bash
cd /Users/doganumutsunar/analytics-system/backend
source .venv/bin/activate
python debug_secret_key.py  # Shows backend's actual SECRET_KEY and generates correct token
```

**WORKING JWT TOKEN (24 hours):**
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoidGVzdC11c2VyLTAwMSIsInRlbmFudF9pZCI6InRlc3QtdGVuYW50LTAwMSIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsInJvbGUiOiJ1c2VyIiwiZXhwIjoxNzU2NDk0MjY5LCJpYXQiOjE3NTY0MDc4NjksImF1ZCI6Im1lZXRpbmdzIiwiaXNzIjoib3VyLWFwcCJ9.n2p7AUS7IHhIYgWh0yidugcKNR0tK59baRpHi-tAwgc
```

### 2. Use Token in MacClient
1. Copy the generated token
2. Open MacClient Settings
3. Paste token in JWT field
4. Set WebSocket URL: `ws://localhost:8000`
5. Click "Test Connection"

### 3. Expected Results
- ✅ Backend health check passes (HTTP 200)
- ✅ WebSocket connection succeeds (101 Switching Protocols)
- ✅ No more 403 Forbidden errors
- ✅ No more -1011 handshake failures

## 🔧 Backend Logs to Monitor

### Success Pattern:
```
INFO: [WS][INGEST] Using Authorization header token for meeting test-connection
INFO: [WS][INGEST] Auth success: test@example.com (meeting: test-connection)
INFO: 127.0.0.1:xxxxx - "WebSocket /api/v1/ws/ingest/meetings/test-connection" 101
INFO: [WS][INGEST] WebSocket accepted for meeting test-connection
```

### CLI Test Success:
```bash
curl -i --http1.1 \
  -H "Connection: Upgrade" -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Version: 13" -H "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==" \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  "http://127.0.0.1:8000/api/v1/ws/ingest/meetings/test-connection"

# Returns: HTTP/1.1 101 Switching Protocols ✅
```

### Previous Error Pattern (Fixed):
```
INFO: 127.0.0.1:xxxxx - "WebSocket /api/v1/ws/ingest/meetings/test-connection?token=..." 403
INFO: connection rejected (403 Forbidden)
```

## 🚀 Deployment Notes

### Local Development
- Use `ws://127.0.0.1:8000`
- Backend serves on port 8000
- Docker containers must be running (PostgreSQL, Redis, MinIO)

### Production
- Use `wss://your-domain.com`
- Ensure valid TLS certificates
- Update `WSURLBuilder.Environment.production.defaultHost`

## 📋 Quick Troubleshooting Checklist

- [ ] Backend running on correct port (8000)
- [ ] Docker containers healthy (PostgreSQL, Redis, MinIO)
- [ ] JWT token generated with correct SECRET_KEY
- [ ] Token properly sanitized (no newlines)
- [ ] WebSocket URL uses `ws://` or `wss://` scheme
- [ ] Authorization header properly formatted
- [ ] Backend logs show 101 Switching Protocols

## 🔄 Updated Memory

The analytics system JWT validation issue has been resolved:
1. ✅ Fixed syntax error in SettingsView.swift line 175
2. ✅ JWT validation now uses consistent SECRET_KEY
3. ✅ WebSocket URLs properly use ws:// scheme  
4. ✅ Authorization header-first token transport
5. ✅ Token sanitization prevents newline issues
6. ✅ Improved error messages for connection failures

Next improvements could include /whoami endpoint and comprehensive quick start guide.
