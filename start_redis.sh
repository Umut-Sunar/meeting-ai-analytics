#!/bin/bash

# Start Redis server for analytics system
# This script starts Redis with the configuration needed for the backend

echo "🚀 Starting Redis server for analytics system..."

# Check if Redis is already running
if pgrep -x "redis-server" > /dev/null; then
    echo "✅ Redis is already running"
    redis-cli -a dev_redis_password ping 2>/dev/null || echo "⚠️ Redis running but may need restart for password"
    exit 0
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

# Start Redis server with password for development
echo "🔧 Starting Redis server with password for development..."
redis-server --port 6379 --requirepass dev_redis_password --daemonize yes

# Wait a moment for Redis to start
sleep 2

# Test connection
echo "🔍 Testing Redis connection..."
if redis-cli -a dev_redis_password ping > /dev/null 2>&1; then
    echo "✅ Redis server started successfully!"
    echo "📊 Redis is running on localhost:6379 (password: dev_redis_password)"
else
    echo "❌ Failed to start Redis server"
    exit 1
fi

echo "🎉 Redis is ready for the analytics system!"
echo "📝 To stop Redis: redis-cli shutdown"
