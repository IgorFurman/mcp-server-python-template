# Sequential Think MCP Server - Offline AI Assistant

A comprehensive offline AI assistant that integrates Sequential Thinking methodologies with local LLM capabilities through the Model Context Protocol (MCP).

## Features

### 🧠 AI-Powered Tools
- **Prompt Enhancement** - AI-powered prompt optimization using local LLMs
- **Complexity Classification** - Automatic prompt complexity analysis (L1-L5)
- **Framework Guidance** - Access to Sequential Thinking frameworks
- **Prompt Search** - SQLite-based full-text search of prompt database

### 🔒 Privacy-First Design
- **100% Offline** - No data sent to external services
- **Local LLM Integration** - Uses Ollama for AI processing
- **SQLite Database** - Local prompt storage and search
- **TypeScript Integration** - Leverages existing Sequential Think CLI

### 🛠️ MCP Integration
- **Dual Transport** - Supports stdio and SSE transport modes
- **Claude Desktop** - Ready for Claude Desktop integration
- **FastMCP Framework** - Built on robust MCP foundation

## Quick Start2

### 1. Setup

```bash
# Initialize the database and load sample prompts
python setup_sequential_think.py

# Install Ollama (for local LLM capabilities)
# Visit: https://ollama.ai/

# Install a local model
ollama pull llama3.2:1b
```

### 2. Run the Server

```bash
# Run with stdio transport (for CLI integration)
python sequential_think_server.py --transport stdio

# Run with SSE transport (for web applications)
python sequential_think_server.py --transport sse --host 0.0.0.0 --port 7071
```

### 3. Claude Desktop Integration

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "sequential-think-ai": {
      "command": "python",
      "args": ["/path/to/sequential_think_server.py"],
      "cwd": "/path/to/mcp-server-python-template",
      "env": {
        "PATH": "/path/to/.venv/bin:/usr/bin:/bin"
      }
    }
  }
}
```

## Available Tools

### `enhance_prompt`
Enhance prompts using AI-powered optimization.

```python
enhance_prompt(
    prompt="How do I optimize my React app?",
    complexity_level="L3",
    use_local_llm=True,
    model="llama3.2:1b"
)
```

### `classify_prompt`
Classify prompts by complexity and provide analysis.

```python
classify_prompt(prompt="Design a microservices architecture")
# Returns: L5 classification with recommendations
```

### `search_prompts`
Search the prompt database for relevant examples.

```python
search_prompts(
    query="React performance",
    category="Development",
    complexity="L3"
)
```

### `get_framework_guidance`
Get guidance on Sequential Thinking frameworks.

```python
get_framework_guidance("Enhanced Debugging")
# Returns: Framework methodology and usage instructions
```

### `check_ollama_status`
Check local LLM availability and models.

```python
check_ollama_status()
# Returns: Ollama status and available models
```

### `run_sequential_think_cli`
Run the TypeScript Sequential Think CLI directly.

```python
run_sequential_think_cli(
    prompt="Optimize database queries",
    thoughts=8
)
```

## Architecture

```
Sequential Think MCP Server
├── Local LLM (Ollama)          # AI processing
├── SQLite Database             # Prompt storage
├── TypeScript Integration      # Existing CLI
└── MCP Interface              # Tool exposure
```

### Components

1. **OllamaClient** - Manages local LLM communication
2. **PromptDatabase** - SQLite-based prompt storage with FTS5 search
3. **SequentialThinkIntegration** - TypeScript CLI wrapper
4. **MCP Tools** - FastMCP-based tool definitions

## Database Schema

### Prompts Table
- `id` - Primary key
- `title` - Prompt title
- `content` - Full prompt content
- `category` - Prompt category
- `complexity_level` - L1-L5 complexity classification
- `domain` - Technical domain
- `tags` - Searchable tags

### Frameworks Table
- `id` - Primary key
- `name` - Framework name
- `description` - Framework description
- `methodology` - Implementation methodology
- `use_cases` - Applicable use cases
- `complexity_range` - Complexity level range

## Configuration

### Environment Variables
- `OLLAMA_BASE_URL` - Ollama server URL (default: http://localhost:11434)

### Command Line Options
```bash
python sequential_think_server.py [options]

Options:
  --transport {stdio,sse}  Transport mode (default: stdio)
  --host HOST             Host for SSE mode (default: 0.0.0.0)
  --port PORT             Port for SSE mode (default: 7071)
  --setup-db              Initialize database only
```

## Complexity Levels

The system uses a 5-level complexity classification:

- **L1-L2** (1-4 steps): Simple, focused problems
- **L3-L4** (5-10 steps): Complex problems requiring systematic analysis
- **L5** (10+ steps): Architectural decisions with organization-wide impact

## Sequential Thinking Frameworks

### Enhanced Debugging Framework
5-phase systematic debugging methodology:
1. Problem Identification & Evidence Collection
2. Hypothesis Formation & Validation
3. Root Cause Analysis
4. Solution Implementation
5. Verification & Documentation

### Prompt Taxonomy Classification
Multi-dimensional classification system with complexity matrices and domain mapping.

### Cross-Reference System
Semantic relationship mapping with prerequisite tracking and adaptive learning paths.

### Implementation Protocol
16-week enhancement roadmap with validation criteria and success metrics.

## Development

### Adding New Prompts
```python
# Use the setup script to add prompts programmatically
python -c "
from setup_sequential_think import *
# Add your prompts here
"

# Or use the search and classification tools to discover gaps
```

### Extending Frameworks
Add new frameworks to the `get_framework_guidance` tool by extending the frameworks dictionary.

### Local LLM Models
Recommended models for different use cases:
- **llama3.2:1b** - Fast, lightweight (recommended for development)
- **llama3.2:3b** - Balanced performance and quality
- **codellama:7b** - Specialized for code-related tasks

## Troubleshooting

### Ollama Not Available
- Install Ollama: https://ollama.ai/
- Start service: `ollama serve`
- Verify: `ollama list`

### TypeScript CLI Not Found
- Ensure `sequential-think` directory exists
- Install dependencies: `cd sequential-think && npm install`
- Build TypeScript: `npm run build`

### Database Issues
- Reinitialize: `python sequential_think_server.py --setup-db`
- Check permissions: Ensure write access to database directory

### MCP Connection Issues
- Verify Python environment and dependencies
- Check Claude Desktop configuration
- Test with stdio transport first

## Performance

### Database Optimization
- Uses SQLite FTS5 for fast full-text search
- Indexed on category, complexity, and domain
- Optimized for read-heavy workloads

### LLM Performance
- Local processing eliminates network latency
- Model size affects speed vs. quality tradeoff
- Concurrent request handling via asyncio

## Security

### Privacy Protection
- No external API calls for AI processing
- Local database storage
- No telemetry or usage tracking

### Best Practices
- Keep local models updated
- Secure database file permissions
- Use environment-specific configurations

## Contributing

1. Add new prompt categories to sample data
2. Extend framework definitions
3. Improve LLM integration
4. Add new MCP tools for specific use cases
5. Enhance search and classification algorithms

## License

MIT License - See LICENSE file for details.

## Support

For issues and feature requests, please use the GitHub repository or refer to the main MCP documentation.  I've successfully created a comprehensive offline AI assistant server that integrates Sequential Thinking methodologies with local LLM capabilities. Here's
  what was built:

  📁 Key Files Created

  - sequential_think_server.py - Main MCP server with 6 AI tools
  - setup_sequential_think.py - Database initialization with sample data
  - README_SEQUENTIAL_THINK.md - Comprehensive documentation
  - claude_desktop_config_example.json - Claude Desktop integration config

  🛠️ Available MCP Tools

  1. enhance_prompt - AI-powered prompt optimization using local LLMs
  2. classify_prompt - Automatic complexity analysis (L1-L5 levels)
  3. search_prompts - SQLite full-text search of prompt database
  4. get_framework_guidance - Access Sequential Thinking frameworks
  5. check_ollama_status - Monitor local LLM availability
  6. run_sequential_think_cli - Direct TypeScript CLI integration

  🔒 Privacy-First Architecture

  - 100% Offline - No external API calls, works entirely locally
  - Local LLM Integration - Uses Ollama for AI processing
  - SQLite Database - Fast full-text search with 10 sample prompts loaded
  - TypeScript Bridge - Leverages existing Sequential Think CLI system

  ⚡ Quick Start

  # 1. Setup database
  python setup_sequential_think.py

  # 2. Install Ollama (optional but recommended)
  # Visit: https://ollama.ai/
  # ollama pull llama3.2:1b

  # 3. Run server  
  source .venv/bin/activate
  python sequential_think_server.py --transport stdio

  🧠 Sequential Thinking Integration

  The system includes 4 core frameworks:
  - Enhanced Debugging (5-phase methodology)
  - Prompt Taxonomy (L1-L5 complexity classification)
  - Cross-Reference System (semantic relationship mapping)
  - Implementation Protocol (16-week development roadmap)

  The offline AI assistant is now ready for Claude Desktop integration and provides systematic thinking capabilities without any cloud dependencies!
