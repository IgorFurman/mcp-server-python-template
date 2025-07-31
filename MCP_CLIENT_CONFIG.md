# MCP Client Configuration for Sequential Think Server

## SSE Transport Configuration

### Claude Desktop Configuration

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "sequential-think-server": {
      "command": "docker",
      "args": [
        "run", "-p", "7071:7071",
        "igorfurman/mcp-sequential-think:latest",
        "python", "sequential_think_server.py", 
        "--transport", "sse", 
        "--host", "0.0.0.0", 
        "--port", "7071"
      ],
      "env": {
        "MCP_TRANSPORT": "sse"
      }
    }
  }
}
```

### Direct SSE Connection

For direct SSE connections, use:

**Base URL**: `http://localhost:7071`

**Endpoints**:
- **Root**: `GET /` - Server info and available endpoints
- **Health**: `GET /health` - Health check for monitoring
- **SSE**: `/sse` - Main MCP SSE endpoint
- **Messages**: `POST /messages/` - Message handling

### Testing the Server

```bash
# 1. Check server status
curl http://localhost:7071/

# 2. Health check
curl http://localhost:7071/health

# 3. Test SSE connection (requires MCP client)
# Connect to: http://localhost:7071/sse
```

### Expected Responses

**Root endpoint (`/`)**:
```json
{
  "service": "Sequential Think MCP Server",
  "version": "1.0.0", 
  "status": "running",
  "endpoints": {
    "sse": "/sse",
    "messages": "/messages/",
    "health": "/health"
  },
  "transport": "sse"
}
```

**Health endpoint (`/health`)**:
```json
{
  "status": "healthy",
  "database": "ok",
  "service": "Sequential Think MCP Server"
}
```

### Container Deployment

```bash
# Run with Docker
docker run -p 7071:7071 igorfurman/mcp-sequential-think:latest

# Run with Docker Compose
docker-compose up -d sequential-think-server

# Check logs
docker-compose logs -f sequential-think-server
```

### Troubleshooting

1. **404 Errors**: Ensure you're connecting to the correct endpoints
2. **Connection Refused**: Check that port 7071 is properly exposed
3. **Health Check Fails**: Verify the `/health` endpoint returns 200 OK
4. **SSE Connection Issues**: Confirm MCP client is using `/sse` endpoint

### Environment Variables

- `MCP_TRANSPORT=sse` - Force SSE transport mode
- `MCP_HOST=0.0.0.0` - Bind to all interfaces
- `MCP_PORT=7071` - Port for SSE server