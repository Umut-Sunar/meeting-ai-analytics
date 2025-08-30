#!/bin/bash

# Complete startup script for Analytics System
# Starts Redis and Backend in the correct order

echo "🚀 Starting Analytics System..."
echo "================================"

# Step 1: Start Redis
echo "📊 Step 1: Starting Redis..."
./start_redis.sh
if [ $? -ne 0 ]; then
    echo "❌ Failed to start Redis"
    exit 1
fi

echo ""
echo "📊 Step 2: Starting Backend..."
cd backend

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "🔧 Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies if needed
if [ ! -f "venv/.deps_installed" ]; then
    echo "📦 Installing Python dependencies..."
    pip install -r requirements.txt
    touch venv/.deps_installed
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "🔧 Creating .env file..."
    cp env.example .env
    echo "DATABASE_URL=sqlite:///./analytics.db" >> .env
fi

# Start backend server
echo "🚀 Starting FastAPI backend server..."
echo "Backend will be available at: http://localhost:8000"
echo "API docs will be available at: http://localhost:8000/docs"
echo ""
echo "📝 Press Ctrl+C to stop the backend"
echo "================================"

# Start with auto-reload for development
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
