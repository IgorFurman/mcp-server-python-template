#!/bin/bash
# Sequential Think MCP Server Startup Script
# Makes the server portable across all repositories

SERVER_DIR="/home/slimmite/Dokumenty/mpc-server/mcp-server-python-template"
VENV_PATH="$SERVER_DIR/.venv"

# Check if virtual environment exists
if [[ ! -d "$VENV_PATH" ]]; then
    echo "Error: Virtual environment not found at $VENV_PATH"
    echo "Run: python -m venv $VENV_PATH && source $VENV_PATH/bin/activate && pip install -e ."
    exit 1
fi

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "Starting Ollama service..."
    ollama serve > /dev/null 2>&1 &
    sleep 3
fi

# Activate virtual environment and run server
cd "$SERVER_DIR"
source "$VENV_PATH/bin/activate"
exec python sequential_think_server.py --transport stdio