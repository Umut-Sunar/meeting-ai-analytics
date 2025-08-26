# Backend Startup Debug Guide

## 🚨 Problem: Backend Çalışmıyor

### Current Status
- ✅ Dependencies yüklendi
- ✅ JWT keys oluşturuldu  
- ✅ .env dosyası oluşturuldu
- ✅ Config extra="ignore" eklendi
- ❌ Backend başlamıyor

### 🔍 Debug Steps

#### 1. Check Current Processes
```bash
# Check if uvicorn is running
ps aux | grep uvicorn

# Check port 8000
lsof -i :8000

# Kill any existing processes
pkill -f uvicorn
```

#### 2. Check Docker Services
```bash
# Check if Docker services are running
docker compose -f docker-compose.dev.yml ps

# If not running, start them
docker compose -f docker-compose.dev.yml up -d

# Check logs
docker compose -f docker-compose.dev.yml logs postgres
docker compose -f docker-compose.dev.yml logs redis
docker compose -f docker-compose.dev.yml logs minio
```

#### 3. Test Database Connection
```bash
# Test PostgreSQL connection
docker exec -it analytics-system-postgres-1 psql -U postgres -d analytics_db -c "SELECT 1;"

# If database doesn't exist, create it
docker exec -it analytics-system-postgres-1 psql -U postgres -c "CREATE DATABASE analytics_db;"
```

#### 4. Test Redis Connection
```bash
# Test Redis connection
docker exec -it analytics-system-redis-1 redis-cli ping
```

#### 5. Check Python Environment
```bash
cd backend
source .venv/bin/activate

# Test imports
PYTHONPATH=. python -c "
try:
    from app.core.config import get_settings
    print('✅ Config import successful')
    settings = get_settings()
    print('✅ Settings loaded successfully')
except Exception as e:
    print(f'❌ Config error: {e}')
"

# Test database models
PYTHONPATH=. python -c "
try:
    from app.models import Base
    print('✅ Models import successful')
except Exception as e:
    print(f'❌ Models error: {e}')
"

# Test main app
PYTHONPATH=. python -c "
try:
    from app.main import app
    print('✅ App import successful')
except Exception as e:
    print(f'❌ App error: {e}')
"
```

#### 6. Run Database Migrations
```bash
cd backend
source .venv/bin/activate

# Check alembic status
PYTHONPATH=. alembic current

# Run migrations if needed
PYTHONPATH=. alembic upgrade head
```

#### 7. Manual Backend Start (Verbose)
```bash
cd backend
source .venv/bin/activate

# Start with debug logging
PYTHONPATH=. python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level debug
```

#### 8. Alternative Start Methods
```bash
# Method 1: Direct Python
cd backend
source .venv/bin/activate
PYTHONPATH=. python -c "
import uvicorn
from app.main import app
uvicorn.run(app, host='0.0.0.0', port=8000, reload=True)
"

# Method 2: FastAPI CLI
cd backend
source .venv/bin/activate
PYTHONPATH=. fastapi run app.main:app --port 8000

# Method 3: Gunicorn (if installed)
cd backend
source .venv/bin/activate
PYTHONPATH=. gunicorn app.main:app -w 1 -k uvicorn.workers.UnicornWorker --bind 0.0.0.0:8000
```

### 🔧 Common Fixes

#### Fix 1: Environment Variables
```bash
# Check .env file exists and has correct values
cd backend
cat .env

# Verify critical variables
grep -E "(DATABASE_URL|REDIS_URL|DEEPGRAM_API_KEY)" .env
```

#### Fix 2: Database Issues
```bash
# Reset database if needed
docker compose -f docker-compose.dev.yml down -v
docker compose -f docker-compose.dev.yml up -d postgres redis minio

# Wait for services to start
sleep 10

# Run migrations
cd backend
source .venv/bin/activate
PYTHONPATH=. alembic upgrade head

# Seed data
PYTHONPATH=. python seeds/initial_data.py
```

#### Fix 3: Port Conflicts
```bash
# Check what's using port 8000
lsof -i :8000

# Use different port if needed
PYTHONPATH=. uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

#### Fix 4: Permission Issues
```bash
# Fix file permissions
chmod +x scripts/*.py
chmod 600 keys/jwt.key
chmod 644 keys/jwt.pub
```

### 🧪 Test After Fix

#### 1. Health Check
```bash
curl http://localhost:8000/api/v1/health
```

#### 2. OpenAPI Docs
```bash
curl http://localhost:8000/docs
```

#### 3. WebSocket Test
```bash
# Terminal 1: Start subscriber
cd backend
PYTHONPATH=. python scripts/dev_subscribe_ws.py --meeting test-001

# Terminal 2: Send audio
cd backend  
PYTHONPATH=. python scripts/dev_send_pcm.py --meeting test-001 --create-test-wav --test-duration 5
```

### 📋 Checklist

- [ ] Docker services running (postgres, redis, minio)
- [ ] Database exists and migrations applied
- [ ] .env file exists with correct values
- [ ] Virtual environment activated
- [ ] PYTHONPATH set correctly
- [ ] No port conflicts
- [ ] JWT keys exist
- [ ] All dependencies installed
- [ ] No import errors
- [ ] Backend starts without errors
- [ ] Health endpoint responds
- [ ] WebSocket endpoints accessible

### 🆘 If Still Not Working

#### Get Full Error Log
```bash
cd backend
source .venv/bin/activate
PYTHONPATH=. python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level debug 2>&1 | tee startup.log
```

#### Check System Resources
```bash
# Check disk space
df -h

# Check memory
free -h

# Check Python version
python --version

# Check installed packages
pip list | grep -E "(fastapi|uvicorn|sqlalchemy|alembic|pydantic)"
```

#### Minimal Test App
Create `test_minimal.py`:
```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello World"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

Run it:
```bash
cd backend
source .venv/bin/activate
python test_minimal.py
```

If this works, the issue is in our application code. If not, it's an environment issue.

### 📞 Support Information

When asking for support, provide:

1. **Error logs** from startup attempt
2. **Environment info**:
   ```bash
   python --version
   pip --version
   docker --version
   uname -a
   ```
3. **Service status**:
   ```bash
   docker compose -f docker-compose.dev.yml ps
   ```
4. **Configuration**:
   ```bash
   cat .env | grep -v "API_KEY\|SECRET"
   ```
5. **Process info**:
   ```bash
   ps aux | grep -E "(uvicorn|python)"
   lsof -i :8000
   ```

This information will help identify the root cause of the startup issue.
