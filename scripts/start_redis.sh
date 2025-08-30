#!/usr/bin/env bash
set -euo pipefail

# Host Redis startup script with password configuration
# Prevents conflicts with Docker Redis

: "${REDIS_PASSWORD:=dev_redis_password}"

# Check if Docker Redis should be used instead
if [ "${USE_DOCKER_REDIS:-1}" = "1" ]; then
    echo "⏭️  USE_DOCKER_REDIS=1 → not starting host Redis"
    echo "💡 Use Docker Redis: export REDIS_PASSWORD=dev_redis_password && docker compose -f docker-compose.dev.yml up -d redis"
    exit 0
fi

echo "🧩 Starting host Redis with password..."
echo "🔑 Using password: ${REDIS_PASSWORD}"

# Check if Redis is already running
if pgrep -x "redis-server" >/dev/null; then
    echo "🔍 Redis process found, checking configuration..."
    
    # Test if Redis is accessible with password
    if redis-cli -a "$REDIS_PASSWORD" ping >/dev/null 2>&1; then
        echo "✅ Host Redis already running with correct password"
        exit 0
    fi
    
    # Test if Redis is running without password
    if redis-cli ping >/dev/null 2>&1; then
        echo "⚠️ Host Redis running without password. Applying password..."
        if redis-cli CONFIG SET requirepass "$REDIS_PASSWORD" >/dev/null 2>&1; then
            echo "🔒 Password applied to running Redis"
            # Verify password works
            if redis-cli -a "$REDIS_PASSWORD" ping >/dev/null 2>&1; then
                echo "✅ Password verification successful"
                exit 0
            fi
        fi
    fi
    
    echo "♻️ Redis configuration issue. Restarting host Redis..."
    redis-cli shutdown >/dev/null 2>&1 || true
    sleep 2
fi

# Check if Redis is installed
if ! command -v redis-server &> /dev/null; then
    echo "❌ Redis not installed. Installing via Homebrew..."
    if command -v brew &> /dev/null; then
        brew install redis
    else
        echo "❌ Homebrew not found. Please install Redis manually:"
        echo "   brew install redis"
        echo "   or visit: https://redis.io/download"
        exit 1
    fi
fi

# Start Redis server
echo "🚀 Starting Redis server..."
redis-server --daemonize yes

# Wait for Redis to start
sleep 2

# Apply password configuration
echo "🔒 Configuring Redis password..."
if redis-cli CONFIG SET requirepass "$REDIS_PASSWORD" >/dev/null 2>&1; then
    echo "✅ Password configuration applied"
else
    echo "❌ Failed to set Redis password"
    redis-cli shutdown >/dev/null 2>&1 || true
    exit 1
fi

# Verify password works
if redis-cli -a "$REDIS_PASSWORD" ping >/dev/null 2>&1; then
    echo "✅ Host Redis started successfully with password"
    echo "📊 Redis is running on localhost:6379 (password: ${REDIS_PASSWORD})"
    echo "🧪 Test connection: redis-cli -a $REDIS_PASSWORD ping"
else
    echo "❌ Password verification failed"
    redis-cli shutdown >/dev/null 2>&1 || true
    exit 1
fi

echo "🎉 Host Redis is ready!"
echo "📝 To stop: redis-cli -a $REDIS_PASSWORD shutdown"
