#!/usr/bin/env python3
"""
Sequential Think MCP Server - Offline AI Assistant
Comprehensive offline AI assistant with local LLM capabilities and sequential thinking integration.
"""

import asyncio
import json
import os
import sqlite3
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional
import httpx
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from mcp.server.sse import SseServerTransport
from starlette.requests import Request
from starlette.routing import Mount, Route
from mcp.server import Server
import uvicorn

# Initialize FastMCP server for Sequential Think tools
mcp = FastMCP("sequential-think-ai")

# Constants
OLLAMA_BASE_URL = "http://localhost:11434"
SEQUENTIAL_THINK_PATH = Path(__file__).parent / "sequential-think"
PROMPTS_DB_PATH = Path(__file__).parent / "sequential_think_prompts.db"

class PromptDatabase:
    """SQLite-based prompt database for fast searching and classification."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the SQLite database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS prompts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    category TEXT NOT NULL,
                    complexity_level TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    tags TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS frameworks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    methodology TEXT NOT NULL,
                    use_cases TEXT NOT NULL,
                    complexity_range TEXT NOT NULL
                )
            """)
            
            # Create FTS5 virtual table for full-text search
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS prompts_fts USING fts5(
                    title, content, category, domain, tags, content=prompts
                )
            """)
            
            conn.commit()
    
    def search_prompts(self, query: str, category: Optional[str] = None, 
                      complexity: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search prompts using full-text search with filters."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            sql = """
                SELECT p.* FROM prompts p
                JOIN prompts_fts fts ON p.rowid = fts.rowid
                WHERE prompts_fts MATCH ?
            """
            params = [query]
            
            if category:
                sql += " AND p.category = ?"
                params.append(category)
            
            if complexity:
                sql += " AND p.complexity_level = ?"
                params.append(complexity)
            
            sql += " ORDER BY bm25(prompts_fts) LIMIT 10"
            
            cursor = conn.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]

class OllamaClient:
    """Client for interacting with local Ollama LLM."""
    
    def __init__(self, base_url: str = OLLAMA_BASE_URL):
        self.base_url = base_url
    
    async def is_available(self) -> bool:
        """Check if Ollama is running and available."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False
    
    async def list_models(self) -> List[str]:
        """List available local models."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    return [model['name'] for model in data.get('models', [])]
                return []
        except Exception:
            return []
    
    async def generate(self, model: str, prompt: str, system: Optional[str] = None) -> str:
        """Generate response using local LLM."""
        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False
            }
            
            if system:
                payload["system"] = system
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload
                )
                
                if response.status_code == 200:
                    return response.json().get('response', '')
                else:
                    return f"Error: HTTP {response.status_code}"
        except Exception as e:
            return f"Error: {str(e)}"

class SequentialThinkIntegration:
    """Integration layer for existing TypeScript sequential-think CLI."""
    
    def __init__(self, sequential_think_path: Path):
        self.path = sequential_think_path
        self.cli_path = self.path / "ai" / "cli.ts"
    
    async def call_sequential_think(self, prompt: str, thoughts: int = 5, 
                                  verbose: bool = True) -> str:
        """Call the TypeScript sequential-think CLI."""
        try:
            if not self.cli_path.exists():
                return "Sequential Think CLI not found. Please ensure it's installed."
            
            cmd = [
                "npx", "ts-node", str(self.cli_path),
                "enhance",
                "-p", prompt,
                "-t", str(thoughts)
            ]
            
            if verbose:
                cmd.append("-v")
            
            result = subprocess.run(
                cmd,
                cwd=str(self.path),
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                return result.stdout
            else:
                return f"Error: {result.stderr}"
        except subprocess.TimeoutExpired:
            return "Error: Sequential think process timed out"
        except Exception as e:
            return f"Error: {str(e)}"

# Initialize components
prompt_db = PromptDatabase(PROMPTS_DB_PATH)
ollama_client = OllamaClient()
sequential_think = SequentialThinkIntegration(SEQUENTIAL_THINK_PATH)

@mcp.tool()
async def enhance_prompt(prompt: str, complexity_level: str = "L3", 
                        use_local_llm: bool = True, model: str = "llama3.2:1b") -> str:
    """
    Enhance a prompt using AI-powered optimization.
    
    Args:
        prompt: The original prompt to enhance
        complexity_level: Complexity level (L1-L5)
        use_local_llm: Whether to use local LLM or TypeScript CLI
        model: Local LLM model to use (if use_local_llm=True)
    
    Returns:
        Enhanced prompt with systematic improvements
    """
    if use_local_llm and await ollama_client.is_available():
        system_prompt = f"""
        You are an expert prompt engineer specializing in sequential thinking methodologies.
        Enhance the given prompt to achieve {complexity_level} complexity level:
        
        L1-L2: Simple, focused problems (1-4 steps)
        L3-L4: Complex problems requiring systematic analysis (5-10 steps)
        L5: Architectural decisions with organization-wide impact (10+ steps)
        
        Provide a clear, structured, and actionable enhanced prompt.
        """
        
        enhanced = await ollama_client.generate(
            model=model,
            prompt=f"Original prompt: {prompt}\n\nEnhance this prompt:",
            system=system_prompt
        )
        
        return f"Enhanced Prompt ({complexity_level}):\n{enhanced}"
    else:
        # Fallback to TypeScript CLI
        return await sequential_think.call_sequential_think(prompt)

@mcp.tool()
async def classify_prompt(prompt: str) -> str:
    """
    Classify a prompt's complexity and provide context analysis.
    
    Args:
        prompt: The prompt to classify
    
    Returns:
        Classification results with complexity level and recommendations
    """
    if not await ollama_client.is_available():
        return "Local LLM not available. Classification requires Ollama to be running."
    
    models = await ollama_client.list_models()
    if not models:
        return "No local models available. Please install a model using: ollama pull llama3.2:1b"
    
    system_prompt = """
    Analyze the given prompt and classify it according to Sequential Thinking complexity levels:
    
    L1: Simple tasks (1-2 steps) - Basic questions, direct requests
    L2: Moderate tasks (3-4 steps) - Simple problem-solving, basic analysis
    L3: Complex tasks (5-7 steps) - Multi-step analysis, moderate complexity
    L4: Advanced tasks (8-10 steps) - Complex problem-solving, architectural decisions
    L5: Expert tasks (10+ steps) - Organization-wide impact, comprehensive analysis
    
    Provide:
    1. Complexity Level (L1-L5)
    2. Domain Classification
    3. Recommended approach
    4. Key considerations
    """
    
    classification = await ollama_client.generate(
        model=models[0],
        prompt=f"Classify this prompt: {prompt}",
        system=system_prompt
    )
    
    return f"Prompt Classification:\n{classification}"

@mcp.tool()
async def search_prompts(query: str, category: Optional[str] = None, 
                        complexity: Optional[str] = None, limit: int = 5) -> str:
    """
    Search the prompt database for relevant examples.
    
    Args:
        query: Search query
        category: Filter by category (optional)
        complexity: Filter by complexity level (optional)
        limit: Maximum number of results
    
    Returns:
        Formatted search results with relevant prompts
    """
    results = prompt_db.search_prompts(query, category, complexity)
    
    if not results:
        return f"No prompts found for query: {query}"
    
    formatted_results = []
    for i, result in enumerate(results[:limit], 1):
        formatted_results.append(f"""
{i}. {result['title']} ({result['complexity_level']})
   Category: {result['category']} | Domain: {result['domain']}
   Content: {result['content'][:200]}...
   Tags: {result['tags']}
""")
    
    return f"Found {len(results)} prompts:\n" + "\n".join(formatted_results)

@mcp.tool()
async def get_framework_guidance(framework_name: str) -> str:
    """
    Get guidance on using specific Sequential Thinking frameworks.
    
    Args:
        framework_name: Name of the framework (e.g., "Enhanced Debugging", "Prompt Taxonomy")
    
    Returns:
        Framework guidance and usage instructions
    """
    frameworks = {
        "Enhanced Debugging": {
            "description": "5-phase systematic debugging methodology",
            "phases": [
                "Phase 1: Problem Identification & Evidence Collection",
                "Phase 2: Hypothesis Formation & Validation",
                "Phase 3: Root Cause Analysis",
                "Phase 4: Solution Implementation",
                "Phase 5: Verification & Documentation"
            ],
            "usage": "sequentialthinking -t 8 'Execute comprehensive debugging analysis for [problem]'"
        },
        "Prompt Taxonomy": {
            "description": "Multi-dimensional classification system with L1-L5 complexity levels",
            "levels": {
                "L1-L2": "Simple, focused problems (1-4 steps)",
                "L3-L4": "Complex problems requiring systematic analysis (5-10 steps)",
                "L5": "Architectural decisions with organization-wide impact (10+ steps)"
            },
            "usage": "sequentialthinking -t [level] 'Domain.Subdomain - [Action] considering [Context]'"
        },
        "Cross-Reference System": {
            "description": "Semantic relationship mapping with prerequisite tracking",
            "features": [
                "Prerequisite identification",
                "Progression tracking",
                "Knowledge dependency mapping",
                "Adaptive learning paths"
            ],
            "usage": "Use cross-references to build systematic learning paths"
        },
        "Implementation Protocol": {
            "description": "16-week enhancement roadmap with validation criteria",
            "phases": [
                "Foundation (Weeks 1-4): Core infrastructure",
                "Enhancement (Weeks 5-8): Feature development",
                "Integration (Weeks 9-12): System integration",
                "Optimization (Weeks 13-16): Performance tuning"
            ],
            "usage": "Follow systematic implementation phases with success metrics"
        }
    }
    
    if framework_name not in frameworks:
        available = ", ".join(frameworks.keys())
        return f"Framework '{framework_name}' not found. Available frameworks: {available}"
    
    framework = frameworks[framework_name]
    result = f"## {framework_name} Framework\n\n"
    result += f"**Description:** {framework['description']}\n\n"
    
    if 'phases' in framework:
        result += "**Phases:**\n"
        for phase in framework['phases']:
            result += f"- {phase}\n"
        result += "\n"
    
    if 'levels' in framework:
        result += "**Complexity Levels:**\n"
        for level, desc in framework['levels'].items():
            result += f"- {level}: {desc}\n"
        result += "\n"
    
    if 'features' in framework:
        result += "**Features:**\n"
        for feature in framework['features']:
            result += f"- {feature}\n"
        result += "\n"
    
    result += f"**Usage:** {framework['usage']}"
    
    return result

@mcp.tool()
async def check_ollama_status() -> str:
    """
    Check the status of the local Ollama LLM service.
    
    Returns:
        Status information about Ollama and available models
    """
    is_available = await ollama_client.is_available()
    
    if not is_available:
        return """
Ollama Status: ❌ Not Available

To set up Ollama for offline AI capabilities:

1. Install Ollama: https://ollama.ai/
2. Start Ollama: ollama serve
3. Install a model: ollama pull llama3.2:1b
4. Verify: ollama list

The Sequential Think server will work with the TypeScript CLI as fallback.
"""
    
    models = await ollama_client.list_models()
    
    status = "Ollama Status: ✅ Available\n\n"
    
    if models:
        status += "Available Models:\n"
        for model in models:
            status += f"- {model}\n"
        status += "\nReady for offline AI enhancement!"
    else:
        status += "No models installed. Install a model with: ollama pull llama3.2:1b"
    
    return status

@mcp.tool()
async def run_sequential_think_cli(prompt: str, thoughts: int = 5) -> str:
    """
    Run the TypeScript Sequential Think CLI directly.
    
    Args:
        prompt: The prompt to process
        thoughts: Number of thinking steps (1-20)
    
    Returns:
        Sequential thinking analysis results
    """
    return await sequential_think.call_sequential_think(prompt, thoughts, verbose=True)

def create_starlette_app(mcp_server: Server, *, debug: bool = False) -> Starlette:
    """Create a Starlette application for SSE transport."""
    sse = SseServerTransport("/messages/")
    
    async def handle_sse(request: Request) -> None:
        async with sse.connect_sse(
            request.scope,
            request.receive,
            request._send,
        ) as (read_stream, write_stream):
            await mcp_server.run(
                read_stream,
                write_stream,
                mcp_server.create_initialization_options(),
            )
    
    return Starlette(
        debug=debug,
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )

if __name__ == "__main__":
    mcp_server = mcp._mcp_server
    
    import argparse
    
    parser = argparse.ArgumentParser(description='Sequential Think MCP Server - Offline AI Assistant')
    parser.add_argument('--transport', choices=['stdio', 'sse'], default='stdio',
                       help='Transport mode (stdio or sse)')
    parser.add_argument('--host', default='0.0.0.0',
                       help='Host to bind to (for SSE mode)')
    parser.add_argument('--port', type=int, default=7071,
                       help='Port to listen on (for SSE mode)')
    parser.add_argument('--setup-db', action='store_true',
                       help='Initialize prompt database')
    
    args = parser.parse_args()
    
    if args.setup_db:
        print("Setting up prompt database...")
        prompt_db.init_database()
        print("Database initialized successfully!")
        exit(0)
    
    if args.transport == 'stdio':
        mcp.run(transport='stdio')
    else:
        starlette_app = create_starlette_app(mcp_server, debug=True)
        print(f"Sequential Think AI Server starting on http://{args.host}:{args.port}")
        uvicorn.run(starlette_app, host=args.host, port=args.port)