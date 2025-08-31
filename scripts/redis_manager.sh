#!/usr/bin/env bash
set -euo pipefail

# Redis Manager Script
# Comprehensive Redis management for development environment

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Default configuration
: "${REDIS_PASSWORD:=dev_redis_password}"
: "${USE_DOCKER_REDIS:=1}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Redis port usage
check_redis_port() {
    local port=${1:-6379}
    local output
    
    if command_exists lsof; then
        output=$(lsof -i ":$port" 2>/dev/null || true)
        if [ -n "$output" ]; then
            echo "$output"
            return 0
        fi
    fi
    
    return 1
}

# Get Redis process info
get_redis_info() {
    local port_info
    port_info=$(check_redis_port 6379)
    
    if [ -n "$port_info" ]; then
        echo "📊 Redis processes on port 6379:"
        echo "$port_info" | while IFS= read -r line; do
            echo "   $line"
        done
        
        # Determine Redis type
        if echo "$port_info" | grep -q -i "docker\|com.docker"; then
            log_info "Docker Redis detected"
            return 1  # Docker Redis
        else
            log_info "Host Redis detected"
            return 2  # Host Redis
        fi
    else
        log_warning "No Redis process found on port 6379"
        return 0  # No Redis
    fi
}

# Test Redis connection
test_redis_connection() {
    local password="$1"
    local timeout=5
    
    log_info "Testing Redis connection with password..."
    
    # Suppress password warning for cleaner output
    if timeout "$timeout" redis-cli -a "$password" ping 2>/dev/null | grep -q "PONG"; then
        log_success "Redis connection successful (with password)"
        return 0
    elif timeout "$timeout" redis-cli ping 2>/dev/null | grep -q "PONG"; then
        log_warning "Redis connection successful (without password)"
        return 1
    else
        log_error "Redis connection failed"
        return 2
    fi
}

# Start Docker Redis
start_docker_redis() {
    log_info "Starting Docker Redis..."
    
    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker is not running. Please start Docker first."
        return 1
    fi
    
    # Set environment variable for docker-compose
    export REDIS_PASSWORD="$REDIS_PASSWORD"
    
    # Start Redis container
    cd "$PROJECT_ROOT"
    if docker compose -f docker-compose.dev.yml up -d redis; then
        log_success "Docker Redis container started"
        
        # Wait for Redis to be ready
        log_info "Waiting for Redis to be ready..."
        local attempts=0
        local max_attempts=30
        
        while [ $attempts -lt $max_attempts ]; do
            if test_redis_connection "$REDIS_PASSWORD"; then
                log_success "Docker Redis is ready and accessible"
                return 0
            fi
            
            sleep 1
            attempts=$((attempts + 1))
        done
        
        log_error "Docker Redis failed to become ready within ${max_attempts}s"
        return 1
    else
        log_error "Failed to start Docker Redis container"
        return 1
    fi
}

# Stop Docker Redis
stop_docker_redis() {
    log_info "Stopping Docker Redis..."
    
    cd "$PROJECT_ROOT"
    if docker compose -f docker-compose.dev.yml down redis; then
        log_success "Docker Redis container stopped"
        return 0
    else
        log_error "Failed to stop Docker Redis container"
        return 1
    fi
}

# Start Host Redis
start_host_redis() {
    log_info "Starting Host Redis..."
    
    # Check if Redis is installed
    if ! command_exists redis-server; then
        log_error "Redis not installed. Install with: brew install redis"
        return 1
    fi
    
    # Use the existing start_redis.sh script
    if [ -f "$PROJECT_ROOT/scripts/start_redis.sh" ]; then
        export USE_DOCKER_REDIS=0
        export REDIS_PASSWORD="$REDIS_PASSWORD"
        
        if "$PROJECT_ROOT/scripts/start_redis.sh"; then
            log_success "Host Redis started successfully"
            return 0
        else
            log_error "Failed to start Host Redis"
            return 1
        fi
    else
        log_error "start_redis.sh script not found"
        return 1
    fi
}

# Stop Host Redis
stop_host_redis() {
    log_info "Stopping Host Redis..."
    
    # Try graceful shutdown first
    if redis-cli -a "$REDIS_PASSWORD" shutdown >/dev/null 2>&1; then
        log_success "Host Redis stopped gracefully"
        return 0
    elif redis-cli shutdown >/dev/null 2>&1; then
        log_success "Host Redis stopped gracefully (no password)"
        return 0
    fi
    
    # Force kill if graceful shutdown failed
    if pkill -f redis-server >/dev/null 2>&1; then
        log_warning "Host Redis force-killed"
        return 0
    fi
    
    log_warning "No Host Redis process found to stop"
    return 1
}

# Clean up all Redis instances
cleanup_all_redis() {
    log_info "Cleaning up all Redis instances..."
    
    # Stop Docker Redis
    stop_docker_redis || true
    
    # Stop Host Redis
    stop_host_redis || true
    
    # Force kill any remaining Redis processes
    if pkill -f redis-server >/dev/null 2>&1; then
        log_warning "Force-killed remaining Redis processes"
    fi
    
    log_success "Redis cleanup completed"
}

# Status check
status_check() {
    echo "🔍 Redis Status Check"
    echo "===================="
    
    # Environment variables
    echo "📋 Environment:"
    echo "   REDIS_PASSWORD: ${REDIS_PASSWORD}"
    echo "   USE_DOCKER_REDIS: ${USE_DOCKER_REDIS}"
    echo ""
    
    # Port usage
    echo "🔌 Port 6379 Usage:"
    if get_redis_info; then
        echo ""
    fi
    
    # Connection test
    echo "🧪 Connection Test:"
    case $(test_redis_connection "$REDIS_PASSWORD"; echo $?) in
        0) log_success "Redis accessible with password" ;;
        1) log_warning "Redis accessible without password" ;;
        2) log_error "Redis not accessible" ;;
    esac
    
    # Docker status
    echo ""
    echo "🐳 Docker Redis Status:"
    cd "$PROJECT_ROOT"
    if docker compose -f docker-compose.dev.yml ps redis 2>/dev/null | grep -q "Up"; then
        log_success "Docker Redis container is running"
    else
        log_info "Docker Redis container is not running"
    fi
}

# Main function
main() {
    local command="${1:-status}"
    
    case "$command" in
        "start")
            if [ "$USE_DOCKER_REDIS" = "1" ]; then
                start_docker_redis
            else
                start_host_redis
            fi
            ;;
        "stop")
            if [ "$USE_DOCKER_REDIS" = "1" ]; then
                stop_docker_redis
            else
                stop_host_redis
            fi
            ;;
        "restart")
            main stop
            sleep 2
            main start
            ;;
        "docker")
            export USE_DOCKER_REDIS=1
            start_docker_redis
            ;;
        "host")
            export USE_DOCKER_REDIS=0
            start_host_redis
            ;;
        "cleanup")
            cleanup_all_redis
            ;;
        "status"|"info")
            status_check
            ;;
        "test")
            cd "$PROJECT_ROOT/backend"
            if [ -f "test_redis_integration.py" ]; then
                log_info "Running Redis integration tests..."
                python test_redis_integration.py
            else
                log_error "Redis integration test not found"
                exit 1
            fi
            ;;
        "help"|"-h"|"--help")
            echo "Redis Manager - Comprehensive Redis management for development"
            echo ""
            echo "Usage: $0 [command]"
            echo ""
            echo "Commands:"
            echo "  start     Start Redis (Docker or Host based on USE_DOCKER_REDIS)"
            echo "  stop      Stop Redis (Docker or Host based on USE_DOCKER_REDIS)"
            echo "  restart   Restart Redis"
            echo "  docker    Force start Docker Redis"
            echo "  host      Force start Host Redis"
            echo "  cleanup   Stop all Redis instances"
            echo "  status    Show Redis status and configuration"
            echo "  test      Run Redis integration tests"
            echo "  help      Show this help message"
            echo ""
            echo "Environment Variables:"
            echo "  REDIS_PASSWORD      Redis password (default: dev_redis_password)"
            echo "  USE_DOCKER_REDIS    Use Docker Redis if 1, Host Redis if 0 (default: 1)"
            echo ""
            echo "Examples:"
            echo "  $0 status                    # Check Redis status"
            echo "  $0 docker                    # Start Docker Redis"
            echo "  $0 host                      # Start Host Redis"
            echo "  REDIS_PASSWORD=mypass $0 start  # Start with custom password"
            ;;
        *)
            log_error "Unknown command: $command"
            echo "Use '$0 help' for usage information."
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
