#!/usr/bin/env bash
set -euo pipefail

# Full Integration Test Suite
# Tests complete Redis + Backend + WebSocket integration

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Test configuration
: "${REDIS_PASSWORD:=dev_redis_password}"
: "${USE_DOCKER_REDIS:=1}"
: "${BACKEND_URL:=http://localhost:8000}"
: "${WS_URL:=ws://localhost:8000}"

# Test results tracking
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_test() {
    echo -e "${PURPLE}🧪 $1${NC}"
}

# Test result tracking
test_result() {
    local test_name="$1"
    local success="$2"
    local message="${3:-}"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    if [ "$success" = "true" ]; then
        PASSED_TESTS=$((PASSED_TESTS + 1))
        log_success "$test_name"
        [ -n "$message" ] && echo "   └─ $message"
    else
        FAILED_TESTS=$((FAILED_TESTS + 1))
        log_error "$test_name"
        [ -n "$message" ] && echo "   └─ $message"
    fi
}

# Wait for service to be ready
wait_for_service() {
    local service_name="$1"
    local check_command="$2"
    local max_attempts="${3:-30}"
    local attempt=0
    
    log_info "Waiting for $service_name to be ready..."
    
    while [ $attempt -lt $max_attempts ]; do
        if eval "$check_command" >/dev/null 2>&1; then
            log_success "$service_name is ready"
            return 0
        fi
        
        sleep 1
        attempt=$((attempt + 1))
        
        if [ $((attempt % 10)) -eq 0 ]; then
            log_info "Still waiting for $service_name... (${attempt}/${max_attempts})"
        fi
    done
    
    log_error "$service_name failed to become ready within ${max_attempts}s"
    return 1
}

# Test Redis setup
test_redis_setup() {
    log_test "Testing Redis Setup"
    echo "===================="
    
    # Test Redis manager script
    if [ -f "$PROJECT_ROOT/scripts/redis_manager.sh" ]; then
        test_result "Redis manager script exists" "true"
        
        # Make script executable
        chmod +x "$PROJECT_ROOT/scripts/redis_manager.sh"
        
        # Test Redis status (allow it to show output)
        if "$PROJECT_ROOT/scripts/redis_manager.sh" status; then
            test_result "Redis manager status check" "true"
        else
            test_result "Redis manager status check" "false" "Status check failed"
        fi
    else
        test_result "Redis manager script exists" "false" "Script not found"
    fi
    
    # Test Redis connection
    if redis-cli -a "$REDIS_PASSWORD" ping >/dev/null 2>&1; then
        test_result "Redis connection with password" "true"
    else
        test_result "Redis connection with password" "false" "Connection failed"
    fi
    
    echo ""
}

# Test Docker services
test_docker_services() {
    log_test "Testing Docker Services"
    echo "======================="
    
    # Check Docker availability
    if docker info >/dev/null 2>&1; then
        test_result "Docker availability" "true"
    else
        test_result "Docker availability" "false" "Docker not running"
        return 1
    fi
    
    # Check docker-compose file
    if [ -f "$PROJECT_ROOT/docker-compose.dev.yml" ]; then
        test_result "Docker Compose file exists" "true"
    else
        test_result "Docker Compose file exists" "false"
        return 1
    fi
    
    # Start Docker services
    cd "$PROJECT_ROOT"
    export REDIS_PASSWORD="$REDIS_PASSWORD"
    
    if docker compose -f docker-compose.dev.yml up -d redis postgres minio >/dev/null 2>&1; then
        test_result "Docker services start" "true"
    else
        test_result "Docker services start" "false" "Failed to start services"
        return 1
    fi
    
    # Wait for services to be ready
    wait_for_service "Redis" "redis-cli -a $REDIS_PASSWORD ping"
    wait_for_service "PostgreSQL" "pg_isready -h localhost -p 5432 -U meeting_ai"
    wait_for_service "MinIO" "curl -f http://localhost:9000/minio/health/live"
    
    # Test service connections
    if redis-cli -a "$REDIS_PASSWORD" ping >/dev/null 2>&1; then
        test_result "Redis service connection" "true"
    else
        test_result "Redis service connection" "false"
    fi
    
    if pg_isready -h localhost -p 5432 -U meeting_ai >/dev/null 2>&1; then
        test_result "PostgreSQL service connection" "true"
    else
        test_result "PostgreSQL service connection" "false"
    fi
    
    if curl -f http://localhost:9000/minio/health/live >/dev/null 2>&1; then
        test_result "MinIO service connection" "true"
    else
        test_result "MinIO service connection" "false"
    fi
    
    echo ""
}

# Test backend setup
test_backend_setup() {
    log_test "Testing Backend Setup"
    echo "===================="
    
    cd "$PROJECT_ROOT/backend"
    
    # Check virtual environment
    if [ -d "venv" ]; then
        test_result "Virtual environment exists" "true"
    else
        log_info "Creating virtual environment..."
        python3 -m venv venv
        test_result "Virtual environment creation" "true"
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Check requirements
    if [ -f "requirements.txt" ]; then
        test_result "Requirements file exists" "true"
        
        # Install dependencies if needed
        if [ ! -f "venv/.deps_installed" ]; then
            log_info "Installing dependencies..."
            pip install -r requirements.txt >/dev/null 2>&1
            touch venv/.deps_installed
        fi
        test_result "Dependencies installation" "true"
    else
        test_result "Requirements file exists" "false"
    fi
    
    # Check .env file
    if [ -f ".env" ]; then
        test_result "Environment file exists" "true"
    else
        if [ -f "env.example" ]; then
            cp env.example .env
            test_result "Environment file creation" "true"
        else
            test_result "Environment file creation" "false" "env.example not found"
        fi
    fi
    
    echo ""
}

# Test backend startup
test_backend_startup() {
    log_test "Testing Backend Startup"
    echo "======================"
    
    cd "$PROJECT_ROOT/backend"
    source venv/bin/activate
    
    # Start backend in background
    log_info "Starting backend server..."
    python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
    BACKEND_PID=$!
    
    # Wait for backend to be ready
    if wait_for_service "Backend" "curl -f $BACKEND_URL/api/v1/health" 60; then
        test_result "Backend startup" "true"
    else
        test_result "Backend startup" "false" "Backend failed to start"
        kill $BACKEND_PID 2>/dev/null || true
        return 1
    fi
    
    # Test health endpoints
    if curl -f "$BACKEND_URL/api/v1/health" >/dev/null 2>&1; then
        test_result "Health endpoint" "true"
    else
        test_result "Health endpoint" "false"
    fi
    
    if curl -f "$BACKEND_URL/api/v1/health/detailed" >/dev/null 2>&1; then
        test_result "Detailed health endpoint" "true"
    else
        test_result "Detailed health endpoint" "false"
    fi
    
    # Test API documentation
    if curl -f "$BACKEND_URL/docs" >/dev/null 2>&1; then
        test_result "API documentation" "true"
    else
        test_result "API documentation" "false"
    fi
    
    echo ""
    return 0
}

# Test Redis integration
test_redis_integration() {
    log_test "Testing Redis Integration"
    echo "========================"
    
    cd "$PROJECT_ROOT/backend"
    source venv/bin/activate
    
    # Run Redis integration tests
    if [ -f "test_redis_integration.py" ]; then
        if python test_redis_integration.py >/dev/null 2>&1; then
            test_result "Redis integration tests" "true"
        else
            test_result "Redis integration tests" "false" "Integration tests failed"
        fi
    else
        test_result "Redis integration test file" "false" "test_redis_integration.py not found"
    fi
    
    echo ""
}

# Test WebSocket functionality
test_websocket_functionality() {
    log_test "Testing WebSocket Functionality"
    echo "==============================="
    
    cd "$PROJECT_ROOT/backend"
    source venv/bin/activate
    
    # Generate JWT token
    if [ -f "create_correct_jwt.py" ]; then
        python create_correct_jwt.py >/dev/null 2>&1
        test_result "JWT token generation" "true"
    else
        test_result "JWT token generation" "false" "create_correct_jwt.py not found"
    fi
    
    # Test WebSocket handshake
    if [ -f "test_handshake.py" ]; then
        if python test_handshake.py >/dev/null 2>&1; then
            test_result "WebSocket handshake tests" "true"
        else
            test_result "WebSocket handshake tests" "false" "Handshake tests failed"
        fi
    else
        test_result "WebSocket handshake test file" "false" "test_handshake.py not found"
    fi
    
    # Test WebSocket connection
    if [ -f "wscat_test.py" ]; then
        if python wscat_test.py >/dev/null 2>&1; then
            test_result "WebSocket connection test" "true"
        else
            test_result "WebSocket connection test" "false" "Connection test failed"
        fi
    else
        test_result "WebSocket connection test file" "false" "wscat_test.py not found"
    fi
    
    echo ""
}

# Test system integration
test_system_integration() {
    log_test "Testing System Integration"
    echo "=========================="
    
    # Test system startup script
    if [ -f "$PROJECT_ROOT/start_system.sh" ]; then
        test_result "System startup script exists" "true"
        chmod +x "$PROJECT_ROOT/start_system.sh"
    else
        test_result "System startup script exists" "false"
    fi
    
    # Test Makefile targets
    if [ -f "$PROJECT_ROOT/Makefile" ]; then
        test_result "Makefile exists" "true"
        
        # Test make targets
        if make -n redis-status >/dev/null 2>&1; then
            test_result "Makefile Redis targets" "true"
        else
            test_result "Makefile Redis targets" "false"
        fi
    else
        test_result "Makefile exists" "false"
    fi
    
    echo ""
}

# Cleanup function
cleanup() {
    # Only cleanup if we're exiting due to error or completion
    if [ "${CLEANUP_ON_EXIT:-true}" = "true" ]; then
        log_info "Cleaning up test environment..."
        
        # Kill backend if running
        if [ -n "${BACKEND_PID:-}" ]; then
            kill $BACKEND_PID 2>/dev/null || true
            wait $BACKEND_PID 2>/dev/null || true
        fi
        
        # Don't stop Docker services - leave them running for development
        # cd "$PROJECT_ROOT"
        # docker compose -f docker-compose.dev.yml down >/dev/null 2>&1 || true
        
        log_success "Cleanup completed"
    fi
}

# Print test summary
print_summary() {
    echo ""
    echo "🏁 Integration Test Summary"
    echo "=========================="
    echo "📊 Total Tests: $TOTAL_TESTS"
    echo "✅ Passed: $PASSED_TESTS"
    echo "❌ Failed: $FAILED_TESTS"
    
    if [ $FAILED_TESTS -eq 0 ]; then
        echo ""
        log_success "🎉 All integration tests passed!"
        echo "🚀 System is ready for development!"
        return 0
    else
        echo ""
        log_error "💥 Some integration tests failed!"
        echo "🔧 Please check the output above and fix the issues."
        return 1
    fi
}

# Main test runner
main() {
    echo "🧪 Full Integration Test Suite"
    echo "=============================="
    echo "🔑 Redis Password: $REDIS_PASSWORD"
    echo "🐳 Use Docker Redis: $USE_DOCKER_REDIS"
    echo "🌐 Backend URL: $BACKEND_URL"
    echo "🔌 WebSocket URL: $WS_URL"
    echo ""
    
    # Set trap for cleanup
    trap cleanup EXIT
    
    # Run test suites
    test_redis_setup
    test_docker_services
    test_backend_setup
    test_backend_startup
    test_redis_integration
    test_websocket_functionality
    test_system_integration
    
    # Print summary and exit with appropriate code
    if print_summary; then
        exit 0
    else
        exit 1
    fi
}

# Run main function
main "$@"
