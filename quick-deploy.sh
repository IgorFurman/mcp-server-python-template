#!/bin/bash
# quick-deploy.sh

set -e

# Quick deployment script
IMAGE_NAME="mcp-sequential-think"
CONTAINER_NAME="mcp-sequential-think-container"

echo "Stopping existing container if running..."
docker stop ${CONTAINER_NAME} 2>/dev/null || true
docker rm ${CONTAINER_NAME} 2>/dev/null || true

echo "Building and running new container..."
docker build -t ${IMAGE_NAME} .

# Run in SSE mode for containerized deployment
docker run -d \
  --name ${CONTAINER_NAME} \
  -p 7071:7071 \
  -v $(pwd)/sequential_think_prompts.db:/app/sequential_think_prompts.db \
  ${IMAGE_NAME} \
  python sequential_think_server.py --transport sse --host 0.0.0.0 --port 7071

echo "Container started successfully!"
echo "Sequential Think Server available at: http://localhost:7071"

# Show logs
docker logs -f ${CONTAINER_NAME}
