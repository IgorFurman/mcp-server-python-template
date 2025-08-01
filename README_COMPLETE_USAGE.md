# Sequential Think MCP Server - Complete Usage Guide

A comprehensive AI-powered prompt enhancement and sequential thinking system that works across all your development environments - React, Python, ML, and more.

## 🌟 What is this?

This is an MCP (Model Context Protocol) server that provides:
- **AI-powered prompt enhancement** - Transform basic prompts into sophisticated, structured queries
- **Prompt database** - Searchable collection of optimized prompts for different domains
- **Local LLM integration** - Works with Ollama for offline AI capabilities
- **Cross-project compatibility** - Use from any React, Python, ML, or other development environment

## 🚀 Quick Start

### 1. System-wide CLI Access

The CLI is already installed system-wide and available from anywhere:

```bash
# Check database statistics
sequential-think-cli stats

# Enhance a prompt for React development
sequential-think-cli enhance "How to optimize React component performance?"

# Search for existing prompts
sequential-think-cli search "react hooks"

# Classify prompt complexity
sequential-think-cli classify "Build a machine learning pipeline for image recognition"
```

### 2. Docker Container (Production Ready)

```bash
# Run the complete MCP server
docker run -d --name mcp-sequential-think \
    --restart unless-stopped \
    --network host \
    -v ./data:/app/data \
    mcp-sequential-think:ollama-enhanced
```

### 3. Claude Desktop Integration

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "sequential-think": {
      "command": "python",
      "args": ["/home/slimmite/Dokumenty/mpc-server/mcp-server-python-template/sequential_think_server.py"],
      "cwd": "/home/slimmite/Dokumenty/mpc-server/mcp-server-python-template",
      "env": {
        "PATH": "/home/slimmite/Dokumenty/mpc-server/mcp-server-python-template/.venv/bin:/usr/bin:/bin"
      }
    }
  }
}
```

## 📋 Usage Across Different Projects

### 🔵 React/TypeScript Projects

#### Component Optimization
```bash
cd ~/my-react-app

# Get optimized prompts for React performance
sequential-think-cli enhance "My React component rerenders too often, how to fix it?"

# Search for React-specific patterns
sequential-think-cli search "react performance"
sequential-think-cli search "state management"
sequential-think-cli search "typescript errors"
```

#### Common React Use Cases
```bash
# State management issues
sequential-think-cli enhance "How to manage complex state in React with multiple components sharing data?"

# Performance debugging
sequential-think-cli enhance "My React app is slow, how to identify and fix performance bottlenecks?"

# Testing strategies
sequential-think-cli enhance "How to write comprehensive tests for React components with hooks?"
```

### 🐍 Python Projects

#### Data Science & ML
```bash
cd ~/my-python-project

# ML pipeline optimization
sequential-think-cli enhance "How to build a scalable machine learning pipeline for real-time predictions?"

# Data preprocessing
sequential-think-cli enhance "Clean and prepare messy CSV data for machine learning model training"

# Model evaluation
sequential-think-cli search "model evaluation"
sequential-think-cli enhance "How to properly evaluate and compare different ML models?"
```

#### Backend Development
```bash
# API design
sequential-think-cli enhance "Design a RESTful API for user authentication and authorization"

# Database optimization
sequential-think-cli enhance "Optimize PostgreSQL queries for large datasets"

# Error handling
sequential-think-cli search "error handling python"
```

### 🤖 Machine Learning Projects

#### Model Development
```bash
cd ~/ml-research

# Feature engineering
sequential-think-cli enhance "How to engineer features for time series forecasting with seasonal patterns?"

# Model selection
sequential-think-cli enhance "Compare different neural network architectures for computer vision tasks"

# Hyperparameter tuning
sequential-think-cli search "hyperparameter optimization"
```

#### MLOps & Deployment
```bash
# Model deployment
sequential-think-cli enhance "Deploy machine learning model to production with monitoring and rollback capabilities"

# Data versioning
sequential-think-cli enhance "Implement data versioning and experiment tracking for ML projects"
```

### 🔧 DevOps & Infrastructure

```bash
cd ~/infrastructure

# Container optimization
sequential-think-cli enhance "Optimize Docker containers for production deployment with security best practices"

# CI/CD pipelines
sequential-think-cli enhance "Design CI/CD pipeline for microservices with automated testing and deployment"

# Monitoring setup
sequential-think-cli search "monitoring observability"
```

### 📊 Data Analytics Projects

```bash
cd ~/analytics-project

# Data visualization
sequential-think-cli enhance "Create interactive dashboards for business intelligence with real-time data"

# Statistical analysis
sequential-think-cli enhance "Perform statistical analysis on customer behavior data to identify patterns"
```

## 🛠️ Advanced Usage

### Custom Prompt Categories

The system organizes prompts by domain:
- `Development.Frontend.ReactTypeScript`
- `Development.Backend.Python`
- `Development.ML.ModelTraining`
- `DevOps.Infrastructure.CloudNative`
- `Data.Analytics.Processing`

### Complexity Levels

Prompts are classified by complexity:
- **L1-L2**: Simple, focused tasks (1-4 steps)
- **L3-L4**: Complex analysis requiring systematic approach (5-10 steps)
- **L5**: Comprehensive architectural decisions (10+ steps)

### Integration with IDEs

#### VS Code Integration
```json
// Add to VS Code tasks.json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Enhance Prompt",
      "type": "shell",
      "command": "sequential-think-cli",
      "args": ["enhance", "${input:promptText}"],
      "group": "build"
    }
  ],
  "inputs": [
    {
      "id": "promptText",
      "description": "Enter prompt to enhance",
      "default": "",
      "type": "promptString"
    }
  ]
}
```

#### JetBrains IDEs (PyCharm, WebStorm)
Create external tools:
- Program: `sequential-think-cli`
- Arguments: `enhance "$SELECTION$"`
- Working directory: `$ProjectFileDir$`

### API Usage (Programmatic)

#### Python Integration
```python
import subprocess
import json

def enhance_prompt(prompt, domain="general"):
    result = subprocess.run([
        'sequential-think-cli', 'enhance', prompt
    ], capture_output=True, text=True)
    return result.stdout

# Usage in your Python scripts
enhanced = enhance_prompt("Optimize my pandas dataframe operations")
print(enhanced)
```

#### Node.js Integration
```javascript
const { exec } = require('child_process');

function enhancePrompt(prompt) {
    return new Promise((resolve, reject) => {
        exec(`sequential-think-cli enhance "${prompt}"`, (error, stdout, stderr) => {
            if (error) reject(error);
            else resolve(stdout);
        });
    });
}

// Usage in your Node.js projects
enhancePrompt("How to optimize React component rendering?")
    .then(enhanced => console.log(enhanced));
```

## 🔄 Workflow Examples

### Daily Development Workflow

```bash
# Morning: Plan your development tasks
sequential-think-cli enhance "Plan development tasks for implementing user authentication in React app"

# During development: Get specific help
sequential-think-cli search "react authentication"
sequential-think-cli enhance "Handle JWT token refresh in React with automatic retry"

# Code review: Improve your prompts for AI assistance
sequential-think-cli enhance "Review this React component for performance issues and suggest improvements"

# End of day: Document and reflect
sequential-think-cli enhance "Document today's development decisions and create task list for tomorrow"
```

### Project Setup Workflow

```bash
# New React project
cd ~/new-react-project
sequential-think-cli enhance "Set up new React TypeScript project with best practices, testing, and CI/CD"

# New Python ML project  
cd ~/new-ml-project
sequential-think-cli enhance "Initialize new machine learning project structure with data versioning and experiment tracking"

# New API project
cd ~/new-api-project
sequential-think-cli enhance "Set up new Python FastAPI project with database, authentication, and documentation"
```

## 📊 Database Management

### View Current Statistics
```bash
sequential-think-cli stats
```

### Update Prompt Database
```bash
cd /home/slimmite/Dokumenty/mpc-server/mcp-server-python-template
python sync_prompt_data.py
```

### Backup Database
```bash
# Database is automatically backed up to ./backups/
ls backups/
```

## 🐳 Docker Deployment Options

### Development Mode
```bash
docker run -it --rm \
    --network host \
    -v "$(pwd):/workspace" \
    mcp-sequential-think:ollama-enhanced \
    python sequential_think_server.py --transport stdio
```

### Production Mode
```bash
docker run -d \
    --name mcp-sequential-think-prod \
    --restart unless-stopped \
    -p 7071:7071 \
    -v mcp-data:/app/data \
    mcp-sequential-think:ollama-enhanced \
    python sequential_think_server.py --transport sse --port 7071
```

### Docker Compose
```yaml
version: '3.8'
services:
  sequential-think:
    image: mcp-sequential-think:ollama-enhanced
    container_name: mcp-sequential-think
    restart: unless-stopped
    ports:
      - "7071:7071"
    volumes:
      - ./data:/app/data
    environment:
      - TRANSPORT=sse
      - PORT=7071
    command: python sequential_think_server.py --transport sse --port 7071
```

## 🔧 Configuration

### Environment Variables
```bash
export SEQUENTIAL_THINK_DB_PATH="/custom/path/to/database.db"
export SEQUENTIAL_THINK_LOG_LEVEL="DEBUG"
export OLLAMA_HOST="http://localhost:11434"
```

### Custom Configuration File
Create `config.yaml`:
```yaml
database:
  path: "./custom_prompts.db"
  backup_enabled: true
  
ai_services:
  ollama:
    host: "http://localhost:11434"
    models: ["llama3.2:1b", "mistral:7b"]
  
logging:
  level: "INFO"
  file: "./logs/sequential-think.log"
```

## 🚨 Troubleshooting

### Common Issues

#### CLI Not Found
```bash
# Check if CLI is in PATH
which sequential-think-cli

# If not found, recreate symlink
sudo ln -sf "$(pwd)/sequential-think-cli" /usr/local/bin/sequential-think-cli
```

#### Database Issues
```bash
# Check database permissions
ls -la sequential_think_prompts.db

# Reinitialize if corrupted
rm sequential_think_prompts.db
python setup_sequential_think.py
```

#### Docker Container Won't Start
```bash
# Check logs
docker logs mcp-sequential-think

# Remove and recreate
docker rm -f mcp-sequential-think
docker run -d --name mcp-sequential-think --network host -v ./data:/app/data mcp-sequential-think:ollama-enhanced
```

### Performance Optimization

#### For Large Projects
```bash
# Use domain-specific searches
sequential-think-cli search "react" | head -10

# Cache frequently used prompts locally
mkdir ~/.sequential-think-cache
```

#### For Remote Development
```bash
# Run server in background
nohup python sequential_think_server.py --transport sse --port 7071 &

# Access via HTTP API
curl -X POST http://localhost:7071/enhance -d '{"prompt": "your prompt here"}'
```

## 📈 Analytics & Metrics

### Usage Statistics
The system tracks:
- Prompt enhancement requests
- Search queries
- Most used domains
- Complexity distribution

### Export Data
```bash
# Export all prompts
python -c "
import sqlite3, json
conn = sqlite3.connect('sequential_think_prompts.db')
conn.row_factory = sqlite3.Row
cursor = conn.execute('SELECT * FROM prompts')
data = [dict(row) for row in cursor.fetchall()]
with open('prompts_export.json', 'w') as f:
    json.dump(data, f, indent=2)
print('Exported to prompts_export.json')
"
```

## 🤝 Contributing

### Adding New Prompts
1. Create prompts in markdown format in `sequential-think/domains/`
2. Run sync: `python sync_prompt_data.py`
3. Test: `sequential-think-cli search "your-new-domain"`

### Custom Domains
Add new domain categories by creating files:
```
sequential-think/domains/
├── custom_domain_name_prompts.md
└── another_domain_prompts.md
```

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:
1. Check this README
2. Look at existing prompts: `sequential-think-cli search "your-topic"`
3. Check Docker logs: `docker logs mcp-sequential-think`
4. Create an issue in the repository

---

**Happy coding with AI-enhanced prompts! 🚀**