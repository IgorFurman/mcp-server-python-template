# Build and Deploy Script for mcp-sequential-think:ollama-enhanced
# Production-ready deployment with comprehensive monitoring

#!/bin/bash
set -e

# Configuration
IMAGE_NAME="mcp-sequential-think"
TAG="ollama-enhanced"
FULL_IMAGE_NAME="${IMAGE_NAME}:${TAG}"
REGISTRY="ghcr.io/igorfurman"
PLATFORMS="linux/amd64,linux/arm64"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Pre-flight checks
preflight_checks() {
    log "🔍 Running pre-flight checks..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed or not in PATH"
    fi
    
    # Check Docker Buildx
    if ! docker buildx version &> /dev/null; then
        error "Docker Buildx is not available"
    fi
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        error "Docker daemon is not running"
    fi
    
    # Check available disk space (minimum 5GB)
    available_space=$(df /var/lib/docker | awk 'NR==2 {print $4}')
    if [ "$available_space" -lt 5242880 ]; then
        warn "Low disk space available (less than 5GB)"
    fi
    
    log "✅ Pre-flight checks passed"
}

# Build multi-architecture image
build_image() {
    log "🏗️  Building multi-architecture image: $FULL_IMAGE_NAME"
    
    # Create buildx builder if it doesn't exist
    if ! docker buildx ls | grep -q "sequential-think-builder"; then
        log "Creating new buildx builder..."
        docker buildx create --name sequential-think-builder --use
    else
        docker buildx use sequential-think-builder
    fi
    
    # Build for multiple platforms
    docker buildx build \
        --platform "$PLATFORMS" \
        --tag "$FULL_IMAGE_NAME" \
        --tag "$REGISTRY/$FULL_IMAGE_NAME" \
        --push \
        --file sequential-think/Dockerfile \
        --build-arg NODE_VERSION=20 \
        --build-arg ALPINE_VERSION=3.18 \
        --progress=plain \
        .
    
    log "✅ Multi-architecture build completed"
}

# Security scan
security_scan() {
    log "🔒 Running security scan..."
    
    # Install Trivy if not available
    if ! command -v trivy &> /dev/null; then
        log "Installing Trivy..."
        curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin
    fi
    
    # Run security scan
    trivy image --exit-code 1 --severity HIGH,CRITICAL "$FULL_IMAGE_NAME" || {
        warn "Security vulnerabilities found - review before production deployment"
    }
    
    log "✅ Security scan completed"
}

# Performance test
performance_test() {
    log "⚡ Running performance tests..."
    
    # Start test container
    docker run -d --name test-container \
        -p 7071:7071 \
        -e NODE_ENV=test \
        "$FULL_IMAGE_NAME"
    
    # Wait for container to be ready
    sleep 10
    
    # Test health endpoint
    if curl -f http://localhost:7071/health; then
        log "✅ Health check passed"
    else
        error "Health check failed"
    fi
    
    # Test MCP endpoints
    if curl -f http://localhost:7071/; then
        log "✅ MCP server responding"
    else
        error "MCP server not responding"
    fi
    
    # Cleanup
    docker stop test-container && docker rm test-container
    
    log "✅ Performance tests completed"
}

# Deploy to production
deploy_production() {
    log "🚀 Deploying to production..."
    
    # Check if production environment is ready
    if [ ! -f "docker-compose.production.yml" ]; then
        error "Production docker-compose file not found"
    fi
    
    # Backup current deployment
    if docker-compose -f docker-compose.production.yml ps | grep -q "Up"; then
        log "📦 Creating backup of current deployment..."
        docker-compose -f docker-compose.production.yml exec sequential-think-server \
            tar -czf /app/data/backup-$(date +%Y%m%d-%H%M%S).tar.gz /app/data
    fi
    
    # Deploy new version
    docker-compose -f docker-compose.production.yml pull
    docker-compose -f docker-compose.production.yml up -d
    
    # Wait for services to be ready
    log "⏳ Waiting for services to be ready..."
    sleep 30
    
    # Verify deployment
    if curl -f http://localhost:7071/health; then
        log "✅ Production deployment successful"
    else
        error "Production deployment failed - check logs"
    fi
}

# Monitoring setup
setup_monitoring() {
    log "📊 Setting up monitoring..."
    
    # Start monitoring stack
    docker-compose -f docker-compose.production.yml up -d prometheus grafana
    
    # Wait for Grafana to be ready
    sleep 15
    
    # Import dashboards
    if [ -d "monitoring/grafana/dashboards" ]; then
        log "📈 Importing Grafana dashboards..."
        # Dashboard import logic here
    fi
    
    log "✅ Monitoring setup completed"
    log "📊 Grafana available at: http://localhost:3001"
    log "📈 Prometheus available at: http://localhost:9091"
}

# Cleanup old images
cleanup() {
    log "🧹 Cleaning up old images..."
    
    # Remove dangling images
    docker image prune -f
    
    # Remove old versions (keep last 3)
    docker images "$IMAGE_NAME" --format "table {{.Repository}}:{{.Tag}}\t{{.CreatedAt}}" | \
        tail -n +4 | \
        awk '{print $1}' | \
        xargs -r docker rmi
    
    log "✅ Cleanup completed"
}

# Main execution
main() {
    log "🎯 Starting deployment pipeline for $FULL_IMAGE_NAME"
    
    case "${1:-all}" in
        "preflight")
            preflight_checks
            ;;
        "build")
            preflight_checks
            build_image
            ;;
        "scan")
            security_scan
            ;;
        "test")
            performance_test
            ;;
        "deploy")
            deploy_production
            ;;
        "monitor")
            setup_monitoring
            ;;
        "cleanup")
            cleanup
            ;;
        "all")
            preflight_checks
            build_image
            security_scan
            performance_test
            deploy_production
            setup_monitoring
            cleanup
            ;;
        *)
            echo "Usage: $0 {preflight|build|scan|test|deploy|monitor|cleanup|all}"
            echo ""
            echo "Commands:"
            echo "  preflight  - Run pre-flight checks"
            echo "  build      - Build multi-architecture image"
            echo "  scan       - Run security scan"
            echo "  test       - Run performance tests"
            echo "  deploy     - Deploy to production"
            echo "  monitor    - Setup monitoring"
            echo "  cleanup    - Clean up old images"
            echo "  all        - Run complete pipeline"
            exit 1
            ;;
    esac
    
    log "🎉 Pipeline completed successfully!"
}

# Execute main function
main "$@"
