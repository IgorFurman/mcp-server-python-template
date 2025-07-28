# Docker Deployment Guide for MCP Sequential Think Server

## Quick Start

### 1. Build and Test Locally
```bash
cd /home/slimmite/Dokumenty/mpc-server/mcp-server-python-template

# Build the Docker image
docker build -t mcp-sequential-think .

# Run locally for testing
docker run -p 7071:7071 -v $(pwd)/sequential_think_prompts.db:/app/sequential_think_prompts.db mcp-sequential-think
```

### 2. Quick Deployment
```bash
# Use the quick deployment script
./quick-deploy.sh
```

### 3. Docker Compose Deployment
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Push to Docker Registry

### Docker Hub
```bash
# Login to Docker Hub
docker login

# Edit build-and-push.sh and replace "your-registry" with your Docker Hub username
# Example: REGISTRY="yourusername"

# Build and push
./build-and-push.sh latest
```

### GitHub Container Registry
```bash
# Login to GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Build and push manually
docker build -t ghcr.io/igorfurman/mcp-sequential-think:latest .
docker push ghcr.io/igorfurman/mcp-sequential-think:latest
```

## Available Files

- `Dockerfile` - Main production-ready Dockerfile
- `Dockerfile.production` - Multi-stage optimized build
- `docker-compose.yml` - Complete stack deployment
- `.dockerignore` - Optimizes build context
- `build-and-push.sh` - Automated build and push script
- `quick-deploy.sh` - Quick local deployment script

## Configuration

### Environment Variables
- `MCP_TRANSPORT` - Transport mode (stdio/sse)
- `MCP_HOST` - Host to bind to (default: 0.0.0.0)
- `MCP_PORT` - Port to listen on (default: 7071)
- `PYTHONPATH` - Python path (default: /app)

### Ports
- `7070` - Main MCP server (SSE mode)
- `7071` - Sequential Think server (SSE mode)

### Volumes
- `./sequential_think_prompts.db:/app/sequential_think_prompts.db` - Database persistence

## Usage Examples

### Run with custom command
```bash
docker run -p 7071:7071 mcp-sequential-think python sequential_think_server.py --transport sse --host 0.0.0.0 --port 7071
```

### Run in stdio mode (for Claude Desktop integration)
```bash
docker run -it mcp-sequential-think python sequential_think_server.py --transport stdio
```

### Production deployment with persistent data
```bash
docker run -d \
  --name mcp-production \
  --restart unless-stopped \
  -p 7071:7071 \
  -v /data/mcp:/app/data \
  -e MCP_TRANSPORT=sse \
  mcp-sequential-think
```

## Troubleshooting

### Check container logs
```bash
docker logs mcp-sequential-think-container
```

### Access container shell
```bash
docker exec -it mcp-sequential-think-container bash
```

### Rebuild after changes
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```
