#!/bin/bash
# Model Preloader Script for Ollama
# Ensures required models are available for Sequential Think MCP Server

set -e

OLLAMA_HOST=${OLLAMA_HOST:-"http://ollama:11434"}
REQUIRED_MODELS=(
    "deepseek-r1:8b"
    "deepseek-r1:14b" 
    "llama3.2:latest"
)

echo "🚀 Sequential Think MCP Server - Model Preloader"
echo "================================================"
echo "Ollama Host: $OLLAMA_HOST"
echo "Required Models: ${REQUIRED_MODELS[*]}"
echo ""

# Wait for Ollama to be ready
echo "⏳ Waiting for Ollama service..."
while ! curl -f "$OLLAMA_HOST/api/tags" >/dev/null 2>&1; do
    echo "   Ollama not ready, waiting 5 seconds..."
    sleep 5
done
echo "✅ Ollama service is ready!"

# Check and pull required models
for model in "${REQUIRED_MODELS[@]}"; do
    echo "🔍 Checking model: $model"
    
    if curl -s "$OLLAMA_HOST/api/tags" | grep -q "\"name\":\"$model\""; then
        echo "✅ Model $model already available"
    else
        echo "📥 Pulling model: $model"
        if curl -X POST "$OLLAMA_HOST/api/pull" \
           -H "Content-Type: application/json" \
           -d "{\"name\":\"$model\"}" | grep -q '"status":"success"'; then
            echo "✅ Successfully pulled $model"
        else
            echo "❌ Failed to pull $model"
            exit 1
        fi
    fi
done

echo ""
echo "🎉 All required models are ready!"
echo "📊 Available models:"
curl -s "$OLLAMA_HOST/api/tags" | jq -r '.models[].name' | sed 's/^/   - /'

echo ""
echo "🚀 Sequential Think MCP Server is ready for enhanced analysis!"
echo "   - React onboarding optimization: deepseek-r1:8b"
echo "   - Complex architectural analysis: deepseek-r1:14b"
echo "   - General purpose tasks: llama3.2:latest"
