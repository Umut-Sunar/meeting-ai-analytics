# Analytics System Makefile
# Development and maintenance tasks

.PHONY: audit help clean test setup

# Default target
help:
	@echo "📋 Available targets:"
	@echo "  audit    - Run repository audit for Redis/WebSocket issues"
	@echo "  setup    - Setup development environment"
	@echo "  test     - Run integration tests"
	@echo "  clean    - Clean temporary files"
	@echo "  help     - Show this help message"

# Repository audit
audit:
	@echo "🔍 Running repository audit..."
	python3 tools/audit_repo.py

# Development environment setup
setup:
	@echo "🚀 Setting up development environment..."
	@echo "📦 Backend setup..."
	cd backend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt
	@echo "🐳 Docker services..."
	docker compose -f docker-compose.dev.yml up -d
	@echo "✅ Setup complete!"

# Integration tests
test:
	@echo "🧪 Running integration tests..."
	cd backend && source venv/bin/activate && PYTHONPATH=. ./quick_test.sh

# Clean temporary files
clean:
	@echo "🧹 Cleaning temporary files..."
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name ".DS_Store" -delete 2>/dev/null || true
	rm -f dump.rdb
	@echo "✅ Cleanup complete!"

# Legacy Redis targets (kept for compatibility)
redis-logs:
	@echo "📋 Redis logs..."
	docker logs meeting-ai-redis --tail 20

redis-conflict-check:
	@echo "🔍 Checking for Redis conflicts..."
	@echo "Port 6379 usage:"
	@lsof -i :6379 || echo "No Redis running on port 6379"
	@echo ""
	@echo "Redis processes:"
	@pgrep -fl redis-server || echo "No host Redis processes found"
	@echo ""
	@echo "Docker Redis status:"
	@docker ps --filter name=meeting-ai-redis --format "table {{.Names}}\t{{.Status}}" || echo "No Docker Redis container"

# Backend management
backend-start:
	@echo "🚀 Starting backend..."
	cd backend && source venv/bin/activate && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

backend-test:
	@echo "🧪 Testing backend health..."
	curl -s http://localhost:8000/api/v1/health | python3 -m json.tool

# System management
system-start:
	@echo "🚀 Starting full system..."
	./start_system.sh

system-stop:
	@echo "🛑 Stopping system..."
	docker compose -f docker-compose.dev.yml down
	pkill -f "uvicorn app.main:app" || true

# Redis management
redis-start:
	@echo "🚀 Starting Redis..."
	./scripts/redis_manager.sh start

redis-stop:
	@echo "🛑 Stopping Redis..."
	./scripts/redis_manager.sh stop

redis-restart:
	@echo "♻️ Restarting Redis..."
	./scripts/redis_manager.sh restart

redis-docker:
	@echo "🐳 Starting Docker Redis..."
	./scripts/redis_manager.sh docker

redis-host:
	@echo "🏠 Starting Host Redis..."
	./scripts/redis_manager.sh host

redis-status:
	@echo "📊 Redis status..."
	./scripts/redis_manager.sh status

redis-test:
	@echo "🧪 Testing Redis integration..."
	./scripts/redis_manager.sh test

redis-cleanup-new:
	@echo "🧹 Cleaning up all Redis instances..."
	./scripts/redis_manager.sh cleanup

# Development utilities
logs:
	@echo "📋 System logs..."
	docker compose -f docker-compose.dev.yml logs --tail 20

status:
	@echo "📊 System status..."
	@echo "🐳 Docker containers:"
	docker compose -f docker-compose.dev.yml ps
	@echo ""
	@echo "🔌 Port usage:"
	lsof -i :8000 -i :6379 -i :5432 || echo "No services running on main ports"
	@echo ""
	@echo "📊 Redis detailed status:"
	./scripts/redis_manager.sh status
