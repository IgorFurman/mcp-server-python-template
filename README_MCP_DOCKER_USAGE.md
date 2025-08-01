# Sequential Think MCP Server - Docker Usage Guide

🐳 **MCP Server running on Docker at port 7071** - Ready for integration with Claude Desktop and other MCP clients.

## 🚀 Current Status

✅ **MCP Server is RUNNING on port 7071**
```bash
Container: mcp-ollama-enhanced
Status: Running
Port: 7071 (HTTP/SSE)
Health: http://localhost:7071/health
```

## 🔌 MCP Integration

### Claude Desktop Configuration

Add this to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "sequential-think": {
      "command": "docker",
      "args": [
        "exec", 
        "-i", 
        "mcp-ollama-enhanced", 
        "python", 
        "sequential_think_mcp_server.py", 
        "--transport", 
        "stdio"
      ]
    }
  }
}
```

**OR** using HTTP transport:

```json
{
  "mcpServers": {
    "sequential-think-http": {
      "url": "http://localhost:7071/sse",
      "transport": "sse"
    }
  }
}
```

### MCP Client Connection

For any MCP client, connect to:
- **URL**: `http://localhost:7071/sse`
- **Transport**: Server-Sent Events (SSE)
- **Protocol**: MCP 1.0

## 🛠️ Available MCP Tools

Your Sequential Think MCP server provides these tools:

### 1. **enhance_prompt**
```json
{
  "name": "enhance_prompt",
  "description": "AI-powered prompt enhancement with multiple fallback options",
  "inputSchema": {
    "type": "object",
    "properties": {
      "prompt": {"type": "string", "description": "The original prompt to enhance"},
      "domain": {"type": "string", "default": "general"},
      "complexity_level": {"type": "string", "default": "L3"},
      "use_local_llm": {"type": "boolean", "default": false}
    }
  }
}
```

### 2. **classify_prompt**
```json
{
  "name": "classify_prompt",
  "description": "Classify a prompt's complexity and context levels",
  "inputSchema": {
    "type": "object",
    "properties": {
      "prompt": {"type": "string", "description": "The prompt to classify"}
    }
  }
}
```

### 3. **search_prompts**
```json
{
  "name": "search_prompts",
  "description": "Search the prompt database for relevant examples",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {"type": "string", "description": "Search terms"},
      "domain": {"type": "string", "description": "Optional domain filter"},
      "limit": {"type": "integer", "default": 10}
    }
  }
}
```

### 4. **get_framework_guidance**
```json
{
  "name": "get_framework_guidance",
  "description": "Get structured thinking framework guidance for a topic",
  "inputSchema": {
    "type": "object",
    "properties": {
      "topic": {"type": "string", "description": "The topic or problem area"}
    }
  }
}
```

### 5. **update_prompt_metrics**
```json
{
  "name": "update_prompt_metrics",
  "description": "Update usage metrics for a prompt",
  "inputSchema": {
    "type": "object",
    "properties": {
      "prompt_id": {"type": "string"},
      "successful": {"type": "boolean"},
      "steps": {"type": "integer", "default": 0},
      "user_rating": {"type": "number"},
      "categories": {"type": "array", "items": {"type": "string"}}
    }
  }
}
```

## 💻 Usage in Different Development Environments

### React/TypeScript Projects

Create `.mcp-config.json` in your project root:
```json
{
  "servers": {
    "sequential-think": {
      "url": "http://localhost:7071/sse",
      "transport": "sse"
    }
  }
}
```

Example usage with MCP client:
```javascript
// Using MCP client library
import { Client } from '@modelcontextprotocol/sdk';

const client = new Client({
  url: 'http://localhost:7071/sse',
  transport: 'sse'
});

// Enhance React-specific prompts
const enhanced = await client.callTool('enhance_prompt', {
  prompt: 'Optimize React component performance',
  domain: 'Development.Frontend.ReactTypeScript',
  complexity_level: 'L3'
});
```

### Python Projects

```python
import httpx
import json

class SequentialThinkMCP:
    def __init__(self, base_url="http://localhost:7071"):
        self.base_url = base_url
        self.client = httpx.AsyncClient()
    
    async def enhance_prompt(self, prompt, domain="general"):
        response = await self.client.post(
            f"{self.base_url}/mcp/tools/call",
            json={
                "method": "tools/call",
                "params": {
                    "name": "enhance_prompt",
                    "arguments": {
                        "prompt": prompt,
                        "domain": domain
                    }
                }
            }
        )
        return response.json()
    
    async def search_prompts(self, query, limit=10):
        response = await self.client.post(
            f"{self.base_url}/mcp/tools/call",
            json={
                "method": "tools/call", 
                "params": {
                    "name": "search_prompts",
                    "arguments": {
                        "query": query,
                        "limit": limit
                    }
                }
            }
        )
        return response.json()

# Usage in ML projects
async def main():
    mcp = SequentialThinkMCP()
    
    # Enhance ML prompts
    result = await mcp.enhance_prompt(
        "Build machine learning pipeline for image classification",
        domain="Development.ML.ModelTraining"
    )
    print(result)
    
    # Search for existing ML patterns
    patterns = await mcp.search_prompts("neural network optimization")
    print(patterns)
```

### VS Code Integration

Create `.vscode/tasks.json`:
```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Enhance Prompt with MCP",
      "type": "shell",
      "command": "curl",
      "args": [
        "-X", "POST",
        "http://localhost:7071/mcp/tools/call",
        "-H", "Content-Type: application/json",
        "-d", "{\"method\":\"tools/call\",\"params\":{\"name\":\"enhance_prompt\",\"arguments\":{\"prompt\":\"${input:prompt}\",\"domain\":\"${input:domain}\"}}}"
      ],
      "group": "build",
      "presentation": {
        "echo": true,
        "reveal": "always",
        "focus": false,
        "panel": "new"
      }
    }
  ],
  "inputs": [
    {
      "id": "prompt",
      "description": "Enter your prompt",
      "default": "",
      "type": "promptString"
    },
    {
      "id": "domain",
      "description": "Select domain",
      "default": "general",
      "type": "pickString",
      "options": [
        "general",
        "Development.Frontend.ReactTypeScript", 
        "Development.Backend.Python",
        "Development.ML.ModelTraining",
        "DevOps.Infrastructure.CloudNative",
        "Data.Analytics.Processing"
      ]
    }
  ]
}
```

## 🔄 Container Management

### Start/Stop/Restart Container
```bash
# Check status
docker ps --filter name=mcp-ollama-enhanced

# Stop container
docker stop mcp-ollama-enhanced

# Start container  
docker start mcp-ollama-enhanced

# Restart container
docker restart mcp-ollama-enhanced

# View logs
docker logs -f mcp-ollama-enhanced

# View real-time stats
docker stats mcp-ollama-enhanced
```

### Update Container
```bash
# Pull latest changes and rebuild
git pull
docker build -t mcp-sequential-think:ollama-enhanced .

# Stop old container
docker stop mcp-ollama-enhanced
docker rm mcp-ollama-enhanced

# Start new container
docker run -d --name mcp-ollama-enhanced --restart unless-stopped \
  -p 7071:7071 -v "$(pwd)/data/mcp:/app/data" \
  mcp-sequential-think:ollama-enhanced \
  python sequential_think_server.py --transport sse --host 0.0.0.0 --port 7071
```

## 🌐 Network Configuration

### Port Mapping
- **Host Port**: 7071
- **Container Port**: 7071  
- **Protocol**: HTTP/SSE
- **Access**: http://localhost:7071

### Health Check
```bash
# Basic health check
curl http://localhost:7071/health

# Expected response:
# {"status":"healthy","database":"ok","service":"Sequential Think MCP Server"}
```

### Firewall Configuration (if needed)
```bash
# Ubuntu/Debian
sudo ufw allow 7071

# CentOS/RHEL
sudo firewall-cmd --add-port=7071/tcp --permanent
sudo firewall-cmd --reload
```

## 📊 Monitoring & Logs

### Real-time Monitoring
```bash
# Container stats
docker stats mcp-ollama-enhanced

# Live logs
docker logs -f mcp-ollama-enhanced

# Container info
docker inspect mcp-ollama-enhanced
```

### Log Analysis
```bash
# Recent logs
docker logs --tail 50 mcp-ollama-enhanced

# Logs with timestamps
docker logs -t mcp-ollama-enhanced

# Search for errors
docker logs mcp-ollama-enhanced 2>&1 | grep -i error
```

## 🔒 Security Considerations

### Container Security
- Container runs as non-root user (`mcpuser`)
- Limited network exposure (only port 7071)
- Data volume mounted with appropriate permissions
- Regular security updates via base image updates

### Network Security
```bash
# Run on localhost only (more secure)
docker run -d --name mcp-ollama-enhanced \
  -p 127.0.0.1:7071:7071 \
  -v "$(pwd)/data/mcp:/app/data" \
  mcp-sequential-think:ollama-enhanced \
  python sequential_think_server.py --transport sse --host 0.0.0.0 --port 7071
```

## 🚨 Troubleshooting

### Common Issues

#### Container Won't Start
```bash
# Check if port is already in use
netstat -tulnp | grep 7071

# Check Docker logs
docker logs mcp-ollama-enhanced

# Check container status
docker ps -a --filter name=mcp-ollama-enhanced
```

#### MCP Connection Issues
```bash
# Verify server is responding
curl http://localhost:7071/health

# Check if SSE endpoint is accessible
curl -N http://localhost:7071/sse

# Test with verbose output
curl -v http://localhost:7071/health
```

#### Database Issues
```bash
# Check database file in container
docker exec mcp-ollama-enhanced ls -la /app/sequential_think_prompts.db

# Check database permissions
docker exec mcp-ollama-enhanced stat /app/sequential_think_prompts.db

# Reinitialize database
docker exec mcp-ollama-enhanced python setup_sequential_think.py
```

## 📈 Performance Optimization

### Resource Allocation
```bash
# Run with specific resource limits
docker run -d --name mcp-ollama-enhanced \
  --memory=2g --cpus=2 \
  -p 7071:7071 \
  -v "$(pwd)/data/mcp:/app/data" \
  mcp-sequential-think:ollama-enhanced \
  python sequential_think_server.py --transport sse --host 0.0.0.0 --port 7071
```

### Caching & Persistence
- Database is persisted in `./data/mcp/` volume
- Container automatically restarts on failure
- Health checks ensure service availability

## 🎯 Next Steps

1. **Test MCP integration** with Claude Desktop using the provided configuration
2. **Integrate with your projects** using the language-specific examples
3. **Monitor performance** using Docker stats and logs
4. **Scale as needed** by adjusting resource limits

Your MCP server is now **ready for production use** across all your development environments! 🚀

## 📞 Support

For issues:
1. Check container logs: `docker logs mcp-ollama-enhanced`
2. Verify health endpoint: `curl http://localhost:7071/health`  
3. Test MCP tools using the provided examples
4. Review this documentation for configuration details