#!/usr/bin/env python3
"""
Sequential Think MCP Server - Offline AI Assistant
Comprehensive offline AI assistant with local LLM capabilities and sequential thinking integration.
"""

import asyncio
import functools
import json
import logging
import os
import sqlite3
import subprocess
import traceback
import uuid
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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP server for Sequential Think tools
mcp = FastMCP("sequential-think-ai")

# Error handling decorator


def error_handler(func_name: str):
    """Decorator for consistent error handling across MCP tools with unique wrapper names"""
    def decorator(func):
        @functools.wraps(func)  # Preserve original function metadata
        async def unique_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {func_name}: {str(e)}")
                logger.error(traceback.format_exc())
                return f"Error: {str(e)}. Please check logs for details."
        
        # Give each wrapper a unique name to prevent conflicts
        unique_wrapper.__name__ = f"wrapper_{func_name}_{uuid.uuid4().hex[:8]}"
        return unique_wrapper
    return decorator


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
                    effectiveness_score REAL DEFAULT 0.7,
                    quality_score REAL DEFAULT 0.7,
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

            # Add missing columns for existing databases
            try:
                conn.execute(
                    "ALTER TABLE prompts ADD COLUMN effectiveness_score REAL DEFAULT 0.7")
            except sqlite3.OperationalError:
                pass  # Column already exists

            try:
                conn.execute(
                    "ALTER TABLE prompts ADD COLUMN quality_score REAL DEFAULT 0.7")
            except sqlite3.OperationalError:
                pass  # Column already exists

            conn.commit()

    def search_prompts(self, query: str, category: Optional[str] = None,
                       complexity: Optional[str] = None, min_effectiveness: float = 0.0) -> List[Dict[str, Any]]:
        """Enhanced search with quality filtering and relevance scoring."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Try FTS search first, fallback to LIKE search if FTS fails
            try:
                sql = """
                    SELECT p.*, 
                           p.effectiveness_score * p.quality_score as relevance_score
                    FROM prompts p
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

                if min_effectiveness > 0:
                    sql += " AND p.effectiveness_score >= ?"
                    params.append(min_effectiveness)

                sql += " ORDER BY relevance_score DESC, bm25(prompts_fts) LIMIT 10"

                cursor = conn.execute(sql, params)
                results = [dict(row) for row in cursor.fetchall()]

                if results:
                    return results

            except Exception:
                # FTS failed, use fallback search
                pass

            # Fallback search using LIKE
            sql = """
                SELECT *, 
                       effectiveness_score * quality_score as relevance_score
                FROM prompts 
                WHERE (content LIKE ? OR title LIKE ? OR domain LIKE ?)
            """
            like_query = f"%{query}%"
            params = [like_query, like_query, like_query]

            if category:
                sql += " AND category = ?"
                params.append(category)

            if complexity:
                sql += " AND complexity_level = ?"
                params.append(complexity)

            if min_effectiveness > 0:
                sql += " AND effectiveness_score >= ?"
                params.append(min_effectiveness)

            sql += " ORDER BY relevance_score DESC LIMIT 10"

            cursor = conn.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_similar_prompts(self, prompt_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """Find prompts similar to the given prompt."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Get the reference prompt
            cursor = conn.execute(
                "SELECT * FROM prompts WHERE id = ?", (prompt_id,))
            reference = cursor.fetchone()

            if not reference:
                return []

            # Find similar prompts based on domain and complexity
            cursor = conn.execute("""
                SELECT *, 
                       ABS(effectiveness_score - ?) as effectiveness_diff,
                       CASE 
                           WHEN domain = ? THEN 3
                           WHEN domain LIKE ? THEN 2
                           ELSE 1
                       END as domain_similarity
                FROM prompts 
                WHERE id != ? 
                ORDER BY domain_similarity DESC, effectiveness_diff ASC
                LIMIT ?
            """, (
                reference['effectiveness_score'],
                reference['domain'],
                f"{reference['domain'].split('.')[0]}%",
                prompt_id,
                limit
            ))

            return [dict(row) for row in cursor.fetchall()]

    def get_recommendations(self, user_domain: str = None, complexity_preference: str = None) -> List[Dict[str, Any]]:
        """Get recommended high-quality prompts."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            sql = """
                SELECT *, 
                       (effectiveness_score * 0.6 + quality_score * 0.4) as recommendation_score
                FROM prompts 
                WHERE effectiveness_score >= 0.7 AND quality_score >= 0.7
            """
            params = []

            if user_domain:
                sql += " AND domain LIKE ?"
                params.append(f"%{user_domain}%")

            if complexity_preference:
                sql += " AND complexity_level = ?"
                params.append(complexity_preference)

            sql += " ORDER BY recommendation_score DESC LIMIT 10"

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
@error_handler("enhance_prompt")
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
@error_handler("classify_prompt")
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
@error_handler("search_prompts")
async def search_prompts(query: str, category: Optional[str] = None,
                         complexity: Optional[str] = None, limit: int = 5,
                         min_effectiveness: float = 0.0) -> str:
    """
    Search the prompt database for relevant examples with enhanced filtering.

    Args:
        query: Search query
        category: Filter by category (optional)
        complexity: Filter by complexity level (optional)
        limit: Maximum number of results
        min_effectiveness: Minimum effectiveness score filter (0.0-1.0)

    Returns:
        Formatted search results with relevant prompts including quality metrics
    """
    results = prompt_db.search_prompts(
        query, category, complexity, min_effectiveness)

    if not results:
        return f"No prompts found for query: '{query}' with the specified filters."

    formatted_results = []
    for i, result in enumerate(results[:limit], 1):
        # Format quality indicators
        quality_indicator = "🟢" if result.get(
            'quality_score', 0) >= 0.8 else "🟡" if result.get('quality_score', 0) >= 0.7 else "�"
        effectiveness_indicator = "⭐" * \
            min(5, int(result.get('effectiveness_score', 0) * 5))

        content_preview = result['content'][:150] + \
            "..." if len(result['content']) > 150 else result['content']

        formatted_results.append(f"""
{i}. {quality_indicator} {result['title']} ({result['complexity_level']})
   Domain: {result['domain']}
   Quality: {result.get('quality_score', 0):.2f} | Effectiveness: {effectiveness_indicator} ({result.get('effectiveness_score', 0):.2f})
   Content: {content_preview}
   Tags: {result.get('tags', 'N/A')}
""")

    # Add usage suggestions
    suggestions = []
    if len(results) < 3:
        suggestions.append(
            "💡 Try broader search terms or reduce filters for more results")

    high_quality = [r for r in results if r.get('quality_score', 0) >= 0.8]
    if high_quality:
        suggestions.append(f"✨ {len(high_quality)} high-quality prompts found")

    suggestion_text = "\n" + "\n".join(suggestions) if suggestions else ""

    return f"Found {len(results)} prompts for '{query}':\n" + "\n".join(formatted_results) + suggestion_text


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
@error_handler("get_similar_prompts")
async def get_similar_prompts(prompt_content: str, limit: int = 5) -> str:
    """
    Find prompts similar to the given content.

    Args:
        prompt_content: Content to find similar prompts for
        limit: Maximum number of similar prompts to return

    Returns:
        List of similar prompts with relevance scores
    """
    # First search for the closest match
    results = prompt_db.search_prompts(prompt_content[:100])

    if not results:
        return "No similar prompts found. Try using search_prompts with broader terms."

    # Get similar prompts based on the best match
    similar = prompt_db.get_similar_prompts(results[0]['id'], limit)

    if not similar:
        return "No similar prompts found in the database."

    formatted_results = []
    for i, result in enumerate(similar, 1):
        domain_match = "🎯" if result['domain'] == results[0]['domain'] else "🔍"
        effectiveness = "⭐" * \
            min(5, int(result.get('effectiveness_score', 0) * 5))

        formatted_results.append(f"""
{i}. {domain_match} {result['title']} ({result['complexity_level']})
   Domain: {result['domain']}
   Effectiveness: {effectiveness} ({result.get('effectiveness_score', 0):.2f})
   Content: {result['content'][:120]}...
""")

    return f"Similar prompts to your query:\n" + "\n".join(formatted_results)


@mcp.tool()
async def get_prompt_recommendations(domain: Optional[str] = None,
                                     complexity: Optional[str] = None,
                                     limit: int = 5) -> str:
    """
    Get high-quality prompt recommendations.

    Args:
        domain: Filter by domain (e.g., "Development", "DevOps")
        complexity: Filter by complexity level (L1-L5)
        limit: Maximum number of recommendations

    Returns:
        List of recommended high-quality prompts
    """
    recommendations = prompt_db.get_recommendations(domain, complexity)[:limit]

    if not recommendations:
        filter_text = f" for domain '{domain}'" if domain else ""
        filter_text += f" at complexity '{complexity}'" if complexity else ""
        return f"No high-quality recommendations found{filter_text}. Try broader criteria."

    formatted_results = []
    for i, result in enumerate(recommendations, 1):
        score = result.get('recommendation_score', 0)
        score_indicator = "🏆" if score >= 0.9 else "🥇" if score >= 0.8 else "🥈"
        effectiveness = "⭐" * \
            min(5, int(result.get('effectiveness_score', 0) * 5))

        formatted_results.append(f"""
{i}. {score_indicator} {result['title']} ({result['complexity_level']})
   Domain: {result['domain']}
   Recommendation Score: {score:.2f} | Effectiveness: {effectiveness}
   Content: {result['content'][:130]}...
   Why recommended: High quality ({result.get('quality_score', 0):.2f}) and effectiveness
""")

    return f"Top {len(recommendations)} recommended prompts:\n" + "\n".join(formatted_results)


@mcp.tool()
async def get_database_stats() -> str:
    """
    Get comprehensive statistics about the prompt database.

    Returns:
        Database statistics including quality metrics and domain distribution
    """
    with sqlite3.connect(PROMPTS_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        # Basic stats
        cursor = conn.execute("SELECT COUNT(*) as total FROM prompts")
        total = cursor.fetchone()['total']

        cursor = conn.execute(
            "SELECT AVG(quality_score) as avg_quality, AVG(effectiveness_score) as avg_effectiveness FROM prompts")
        scores = cursor.fetchone()

        # Quality distribution
        cursor = conn.execute("""
            SELECT 
                CASE 
                    WHEN quality_score >= 0.9 THEN 'Excellent (0.9+)'
                    WHEN quality_score >= 0.8 THEN 'Good (0.8-0.9)'
                    WHEN quality_score >= 0.7 THEN 'Fair (0.7-0.8)'
                    ELSE 'Poor (<0.7)'
                END as quality_range,
                COUNT(*) as count
            FROM prompts 
            GROUP BY quality_range
            ORDER BY MIN(quality_score) DESC
        """)
        quality_dist = cursor.fetchall()

        # Domain distribution
        cursor = conn.execute("""
            SELECT domain, COUNT(*) as count 
            FROM prompts 
            GROUP BY domain 
            ORDER BY count DESC 
            LIMIT 8
        """)
        domain_dist = cursor.fetchall()

        # Complexity distribution
        cursor = conn.execute("""
            SELECT complexity_level, COUNT(*) as count 
            FROM prompts 
            GROUP BY complexity_level 
            ORDER BY complexity_level
        """)
        complexity_dist = cursor.fetchall()

        stats = f"""
📊 Sequential Think Prompt Database Statistics

📈 Overview:
- Total Prompts: {total}
- Average Quality Score: {scores['avg_quality']:.3f}
- Average Effectiveness Score: {scores['avg_effectiveness']:.3f}

🎯 Quality Distribution:
"""

        for row in quality_dist:
            percentage = (row['count'] / total) * 100
            stats += f"- {row['quality_range']}: {row['count']} ({percentage:.1f}%)\n"

        stats += "\n🏷️ Top Domains:\n"
        for row in domain_dist:
            percentage = (row['count'] / total) * 100
            stats += f"- {row['domain']}: {row['count']} ({percentage:.1f}%)\n"

        stats += "\n📊 Complexity Levels:\n"
        for row in complexity_dist:
            percentage = (row['count'] / total) * 100
            stats += f"- {row['complexity_level']}: {row['count']} ({percentage:.1f}%)\n"

        return stats


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

    parser = argparse.ArgumentParser(
        description='Sequential Think MCP Server - Offline AI Assistant')
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
        print(
            f"Sequential Think AI Server starting on http://{args.host}:{args.port}")
        uvicorn.run(starlette_app, host=args.host, port=args.port)
