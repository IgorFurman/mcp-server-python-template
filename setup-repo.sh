#!/bin/bash
# Sequential Think MCP Setup Script
# Usage: ./setup-repo.sh /path/to/your/repo

REPO_PATH="${1:-$(pwd)}"
MCP_SERVER_PATH="/home/slimmite/Dokumenty/mpc-server/mcp-server-python-template"

echo "🔧 Setting up Sequential Think MCP for: $REPO_PATH"

# Create .vscode directory if it doesn't exist
mkdir -p "$REPO_PATH/.vscode"

# Create Claude Code MCP configuration
cat > "$REPO_PATH/.claude_code_mcp.json" << EOF
{
  "mcpServers": {
    "sequential-think": {
      "command": "python",
      "args": ["$MCP_SERVER_PATH/sequential_think_mcp_server.py"],
      "cwd": "$MCP_SERVER_PATH",
      "env": {
        "PATH": "$MCP_SERVER_PATH/.venv/bin:/usr/bin:/bin"
      }
    }
  }
}
EOF

# Create VS Code settings
cat > "$REPO_PATH/.vscode/settings.json" << EOF
{
  "mcp.servers": {
    "sequential-think": {
      "command": "python",
      "args": ["$MCP_SERVER_PATH/sequential_think_mcp_server.py"],
      "cwd": "$MCP_SERVER_PATH"
    }
  }
}
EOF

echo "✅ Sequential Think MCP configured for:"
echo "   - Claude Code CLI (.claude_code_mcp.json)"
echo "   - VS Code (.vscode/settings.json)"
echo ""
echo "🚀 Available tools:"
echo "   - enhance_prompt() - AI-powered prompt enhancement"
echo "   - search_prompts() - Search 249 high-quality prompts"
echo "   - get_database_stats() - View prompt database statistics"
echo "   - get_framework_guidance() - Access debugging frameworks"
echo ""
echo "📋 CLI Usage: sequential-think enhance 'your prompt here'"