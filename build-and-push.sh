#!/bin/bash
# build-and-push.sh

set -e

# Configuration
IMAGE_NAME="mcp-sequential-think"
REGISTRY="your-registry" # Replace with your registry (docker.io, ghcr.io, etc.)
TAG=${1:-latest}
FULL_IMAGE_NAME="${REGISTRY}/${IMAGE_NAME}:${TAG}"

echo "Building Docker image: ${FULL_IMAGE_NAME}"

# Build the image
docker build -t "${IMAGE_NAME}:${TAG}" -f Dockerfile .

# Tag for registry
docker tag "${IMAGE_NAME}:${TAG}" "${FULL_IMAGE_NAME}"

# Push to registry
echo "Pushing to registry..."
docker push "${FULL_IMAGE_NAME}"

echo "Successfully pushed ${FULL_IMAGE_NAME}"

# Optional: Clean up local images
# docker rmi "${IMAGE_NAME}:${TAG}" "${FULL_IMAGE_NAME}"
