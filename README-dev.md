# Development Setup Guide

This guide covers the development setup for the Analytics System with Docker services.

## Prerequisites

- Docker and Docker Compose
- Python 3.11+
- Node.js 18+ (for web frontend)
- macOS (for MacClient)

## Services Overview

The system uses the following Docker services:
- **PostgreSQL**: Main database
- **Redis**: Cache and pub/sub messaging
- **MinIO**: Object storage
- **pgAdmin**: Database management UI

## Redis (Docker, password)

### Local Redis (Docker, password)

1. **Set Redis password environment variable:**
```bash
export REDIS_PASSWORD=dev_redis_password
```

2. **Start Redis container:**
```bash
docker compose -f docker-compose.dev.yml up -d redis
```

3. **Test Redis connection:**
```bash
redis-cli -a $REDIS_PASSWORD PING
# Should return: PONG
```

### Backend Configuration

The backend must use the following Redis configuration in `.env`:

```bash
REDIS_PASSWORD=dev_redis_password
REDIS_URL=redis://:${REDIS_PASSWORD}@localhost:6379/0
REDIS_REQUIRED=true
```

### Avoid Double Redis

**Important**: Ensure no host Redis is running before starting Docker Redis:

```bash
# Check for running Redis processes
lsof -i :6379

# Stop local Redis if running
redis-cli shutdown
# or
sudo pkill -f redis-server

# Then start Docker Redis
docker compose -f docker-compose.dev.yml up -d redis
```

See "Avoid double Redis" section below for more details.

### Avoid Double Redis

**Critical**: Only run ONE Redis instance at a time to prevent conflicts.

#### Using Docker Redis (Recommended)
```bash
# Set environment variable to use Docker Redis
export USE_DOCKER_REDIS=1

# Start Docker Redis
export REDIS_PASSWORD=dev_redis_password
docker compose -f docker-compose.dev.yml up -d redis

# Stop any host Redis if running
brew services stop redis 2>/dev/null || true
pkill -f redis-server 2>/dev/null || true
```

#### Using Host Redis (Alternative)
```bash
# Set environment variable to use host Redis
export USE_DOCKER_REDIS=0
export REDIS_PASSWORD=dev_redis_password

# Stop Docker Redis if running
docker compose -f docker-compose.dev.yml down redis

# Start host Redis with password
./scripts/start_redis.sh
```

#### Conflict Detection
```bash
# Check what Redis instances are running
lsof -i :6379

# Should show only ONE Redis process:
# - Docker: com.docker.backend
# - Host: redis-server
```

#### Troubleshooting
- **Multiple Redis detected**: Stop all and restart with chosen method
- **Connection refused**: Check if Redis is running on port 6379
- **AUTH failed**: Verify password matches in .env and Redis config

## Full System Startup

### 1. Start All Docker Services

```bash
# Set environment variables
export REDIS_PASSWORD=dev_redis_password

# Start all services
docker compose -f docker-compose.dev.yml up -d

# Check service status
docker compose -f docker-compose.dev.yml ps
```

### 2. Start Backend

```bash
cd backend

# Create .env from example (if not exists)
cp env.example .env

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Test System

```bash
# Run integration tests
cd backend
./quick_test.sh
```

## Service URLs

- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **pgAdmin**: http://localhost:5050
  - Email: admin@meeting-ai.dev
  - Password: admin_password_123
- **MinIO Console**: http://localhost:9001
  - Username: minioadmin
  - Password: dev_minio_password_123

## WebSocket Endpoints

- **Transcript**: `ws://localhost:8000/api/v1/ws/meetings/{meeting_id}`
- **Audio Ingest (Mic)**: `ws://localhost:8000/api/v1/ws/ingest/meetings/{meeting_id}?source=mic`
- **Audio Ingest (System)**: `ws://localhost:8000/api/v1/ws/ingest/meetings/{meeting_id}?source=sys`

## Troubleshooting

### Redis Connection Issues

1. **Check Redis container status:**
```bash
docker logs meeting-ai-redis
```

2. **Test Redis connection:**
```bash
redis-cli -a $REDIS_PASSWORD ping
```

3. **Verify environment variables:**
```bash
echo $REDIS_PASSWORD
```

### Backend Issues

1. **Check backend logs for Redis errors**
2. **Verify `.env` file contains correct Redis URL**
3. **Ensure Docker Redis is running and accessible**

### Port Conflicts

If you get "port already in use" errors:

```bash
# Check what's using the port
lsof -i :6379  # for Redis
lsof -i :5432  # for PostgreSQL
lsof -i :8000  # for Backend

# Stop conflicting processes
sudo pkill -f redis-server
sudo pkill -f postgres
sudo pkill -f uvicorn
```

## Development Workflow

1. **Start Docker services**: `docker compose -f docker-compose.dev.yml up -d`
2. **Start backend**: `cd backend && source venv/bin/activate && python -m uvicorn app.main:app --reload`
3. **Run tests**: `cd backend && ./quick_test.sh`
4. **Start MacClient**: Open Xcode project and run
5. **Start web frontend**: `cd web && npm run dev`

## Stopping Services

```bash
# Stop all Docker services
docker compose -f docker-compose.dev.yml down

# Stop backend (Ctrl+C in terminal)

# Remove volumes (if needed)
docker compose -f docker-compose.dev.yml down -v
```
