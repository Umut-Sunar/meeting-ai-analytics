#!/bin/bash

# Stop Redis server for analytics system

echo "🛑 Stopping Redis server..."

# Check if Redis is running
if ! pgrep -x "redis-server" > /dev/null; then
    echo "⚠️ Redis is not running"
    exit 0
fi

# Stop Redis server
echo "🔧 Shutting down Redis server..."
if redis-cli shutdown > /dev/null 2>&1; then
    echo "✅ Redis server stopped successfully!"
else
    echo "⚠️ Failed to stop Redis gracefully, trying force kill..."
    pkill -f redis-server
    sleep 1
    if ! pgrep -x "redis-server" > /dev/null; then
        echo "✅ Redis server force stopped"
    else
        echo "❌ Failed to stop Redis server"
        exit 1
    fi
fi

echo "🎉 Redis stopped successfully!"
