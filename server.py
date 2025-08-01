import asyncio
import sqlite3
import json
import os
from typing import Any, Dict, List, Optional
from datetime import datetime
import httpx
from mcp.server import FastMCP  # type: ignore
from starlette.applications import Starlette
from mcp.server.sse import SseServerTransport
from starlette.requests import Request
from starlette.routing import Mount, Route
from mcp.server import Server
import uvicorn

# Initialize FastMCP server for sequential thinking
mcp = FastMCP("sequential-think-server")

# Configuration
DB_PATH = "sequential_think_prompts.db"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")


class DatabaseManager:
    """Manages SQLite database operations for prompt storage and retrieval."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize the database with required tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS prompts (
                    id TEXT PRIMARY KEY,
                    original_prompt TEXT NOT NULL,
                    optimized_prompt TEXT,
                    complexity TEXT,
                    context TEXT,
                    domain TEXT,
                    effectiveness REAL,
                    improvements TEXT,
                    timestamp TEXT,
                    usage_count INTEGER DEFAULT 0,
                    success_rate REAL DEFAULT 0.0
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS prompt_metrics (
                    prompt_id TEXT,
                    successful BOOLEAN,
                    steps INTEGER,
                    user_rating REAL,
                    categories TEXT,
                    timestamp TEXT,
                    FOREIGN KEY (prompt_id) REFERENCES prompts (id)
                )
            ''')
            conn.commit()

    # type: ignore
    # type: ignore
    def search_prompts(self, query: str, domain: str = None, limit: int = 10) -> List[Dict]:
        """Search prompts by content, domain, or keywords."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            if domain:
                cursor = conn.execute('''
                    SELECT * FROM prompts 
                    WHERE (content LIKE ? OR enhanced_prompt LIKE ?) 
                    AND domain = ?
                    ORDER BY effectiveness_score DESC, usage_count DESC
                    LIMIT ?
                ''', (f'%{query}%', f'%{query}%', domain, limit))
            else:
                cursor = conn.execute('''
                    SELECT * FROM prompts 
                    WHERE content LIKE ? OR enhanced_prompt LIKE ?
                    OR domain LIKE ? OR tags LIKE ?
                    ORDER BY effectiveness_score DESC, usage_count DESC
                    LIMIT ?
                ''', (f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%', limit))

            return [dict(row) for row in cursor.fetchall()]

    def store_prompt_analysis(self, analysis: Dict) -> str:
        """Store prompt analysis in database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO prompts 
                (hash, title, content, original_prompt, enhanced_prompt, category, 
                 complexity_level, domain, tags, effectiveness_score, quality_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                analysis['id'],
                f"Enhanced: {analysis['original_prompt'][:50]}...",
                analysis['original_prompt'],
                analysis['original_prompt'],
                analysis['optimized_prompt'],
                analysis['domain'],
                analysis['complexity'],
                analysis['domain'],
                json.dumps(analysis['improvements']),
                analysis['effectiveness'],
                analysis['effectiveness']
            ))
            conn.commit()
        return analysis['id']

    def update_prompt_metrics(self, prompt_id: str, usage_data: Dict):
        """Update prompt usage metrics."""
        with sqlite3.connect(self.db_path) as conn:
            # Insert metrics record
            conn.execute('''
                INSERT INTO prompt_metrics 
                (prompt_id, successful, steps, user_rating, categories, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                prompt_id, usage_data['successful'], usage_data.get(
                    'steps', 0),
                usage_data.get('user_rating'),
                json.dumps(usage_data.get('categories', [])),
                datetime.now().isoformat()
            ))

            # Update aggregate metrics
            cursor = conn.execute('''
                SELECT COUNT(*) as total, 
                       SUM(CASE WHEN successful THEN 1 ELSE 0 END) as successful_count
                FROM prompt_metrics WHERE prompt_id = ?
            ''', (prompt_id,))

            row = cursor.fetchone()
            if row:
                total, successful_count = row
                success_rate = successful_count / total if total > 0 else 0.0

                conn.execute('''
                    UPDATE prompts 
                    SET usage_count = ?, success_rate = ?
                    WHERE id = ?
                ''', (total, success_rate, prompt_id))

            conn.commit()


class AIServiceManager:
    """Manages AI service integrations for prompt enhancement."""

    def __init__(self):
        self.openai_client = None
        self.deepseek_client = None

        if OPENAI_API_KEY:
            self.openai_client = httpx.AsyncClient(
                base_url="https://api.openai.com/v1",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"}
            )

        if DEEPSEEK_API_KEY:
            self.deepseek_client = httpx.AsyncClient(
                base_url="https://api.deepseek.com/v1",
                headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"}
            )

    async def enhance_prompt_with_ai(self, prompt: str, domain: str = "general") -> Dict:
        """Enhance prompt using available AI services."""
        enhancement_prompt = f"""
        Analyze and enhance the following prompt for better clarity, specificity, and effectiveness:

        Original Prompt: "{prompt}"
        Domain: {domain}

        Please provide:
        1. Complexity level (L1-L5): L1=Simple, L2=Basic, L3=Intermediate, L4=Advanced, L5=Expert
        2. Context level (C1-C5): C1=General, C2=Specific, C3=Technical, C4=Professional, C5=Specialized
        3. Effectiveness score (0.0-1.0)
        4. List of specific improvements
        5. Enhanced version of the prompt

        Respond in JSON format:
        {{
            "complexity": "L1|L2|L3|L4|L5",
            "context": "C1|C2|C3|C4|C5",
            "effectiveness": 0.0-1.0,
            "improvements": ["improvement1", "improvement2", ...],
            "optimized_prompt": "enhanced prompt text"
        }}
        """

        # Try DeepSeek first, then OpenAI
        for client, model in [(self.deepseek_client, "deepseek-chat"),
                              (self.openai_client, "gpt-3.5-turbo")]:
            if client:
                try:
                    response = await client.post(
                        "/chat/completions",
                        json={
                            "model": model,
                            "messages": [
                                {"role": "system", "content": "You are an expert prompt engineer. Respond only with valid JSON."},
                                {"role": "user", "content": enhancement_prompt}
                            ],
                            "temperature": 0.3,
                            "max_tokens": 1000
                        },
                        timeout=30.0
                    )

                    if response.status_code == 200:
                        result = response.json()
                        content = result['choices'][0]['message']['content']

                        # Parse JSON response
                        try:
                            enhancement_data = json.loads(content)
                            return enhancement_data
                        except json.JSONDecodeError:
                            # Fallback to basic enhancement
                            pass

                except Exception as e:
                    print(f"Error with {model}: {e}")
                    continue

        # Fallback enhancement if AI services fail
        return {
            "complexity": "L2",
            "context": "C2",
            "effectiveness": 0.6,
            "improvements": ["Make more specific", "Add clear success criteria"],
            "optimized_prompt": f"Enhanced version: {prompt} - Please provide specific, actionable steps and clear success criteria."
        }


# Initialize managers
db_manager = DatabaseManager()
ai_manager = AIServiceManager()


@mcp.tool()
async def enhance_prompt(prompt: str, domain: str = "general") -> str:
    """
    Enhance a prompt using AI-powered optimization.

    Args:
        prompt: The original prompt to enhance
        domain: The domain/category for context (e.g., "coding", "writing", "analysis")

    Returns:
        JSON string containing the enhanced prompt and analysis
    """
    try:
        # Get AI enhancement
        enhancement = await ai_manager.enhance_prompt_with_ai(prompt, domain)

        # Create analysis record
        analysis = {
            "id": f"prompt_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(prompt) % 10000}",
            "original_prompt": prompt,
            "optimized_prompt": enhancement["optimized_prompt"],
            "complexity": enhancement["complexity"],
            "context": enhancement["context"],
            "domain": domain,
            "effectiveness": enhancement["effectiveness"],
            "improvements": enhancement["improvements"],
            "timestamp": datetime.now().isoformat()
        }

        # Store in database
        db_manager.store_prompt_analysis(analysis)

        return json.dumps(analysis, indent=2)

    except Exception as e:
        return f"Error enhancing prompt: {str(e)}"


@mcp.tool()
async def classify_prompt(prompt: str) -> str:
    """
    Classify a prompt's complexity and context levels.

    Args:
        prompt: The prompt to classify

    Returns:
        JSON string with classification results
    """
    try:
        # Use AI service for classification
        enhancement = await ai_manager.enhance_prompt_with_ai(prompt, "classification")

        classification = {
            "prompt": prompt,
            "complexity": enhancement["complexity"],
            "context": enhancement["context"],
            "effectiveness": enhancement["effectiveness"],
            "analysis": "Complexity levels: L1=Simple, L2=Basic, L3=Intermediate, L4=Advanced, L5=Expert",
            "context_info": "Context levels: C1=General, C2=Specific, C3=Technical, C4=Professional, C5=Specialized"
        }

        return json.dumps(classification, indent=2)

    except Exception as e:
        return f"Error classifying prompt: {str(e)}"


@mcp.tool()
async def search_prompts(query: str, domain: str = None, limit: int = 10) -> str:  # type: ignore
    """
    Search the prompt database for relevant examples.

    Args:
        query: Search terms
        domain: Optional domain filter
        limit: Maximum number of results

    Returns:
        JSON string with search results
    """
    try:
        results = db_manager.search_prompts(query, domain, limit)

        return json.dumps({
            "query": query,
            "domain": domain,
            "results_count": len(results),
            "results": results
        }, indent=2)

    except Exception as e:
        return f"Error searching prompts: {str(e)}"


@mcp.tool()
async def get_framework_guidance(topic: str) -> str:
    """
    Get structured thinking framework guidance for a topic.

    Args:
        topic: The topic or problem area

    Returns:
        Structured guidance and framework recommendations
    """
    frameworks = {
        "problem_solving": {
            "steps": [
                "1. Define the problem clearly",
                "2. Gather relevant information",
                "3. Generate possible solutions",
                "4. Evaluate options systematically",
                "5. Implement the best solution",
                "6. Monitor and adjust as needed"
            ],
            "tools": ["Root cause analysis", "5 Whys", "Fishbone diagram"]
        },
        "decision_making": {
            "steps": [
                "1. Identify the decision to be made",
                "2. Gather relevant information",
                "3. Identify alternatives",
                "4. Weigh evidence and criteria",
                "5. Choose among alternatives",
                "6. Take action and monitor"
            ],
            "tools": ["Decision matrix", "Pros/cons analysis", "SWOT analysis"]
        },
        "analysis": {
            "steps": [
                "1. Define scope and objectives",
                "2. Collect and organize data",
                "3. Identify patterns and relationships",
                "4. Interpret findings",
                "5. Draw conclusions",
                "6. Make recommendations"
            ],
            "tools": ["Data visualization", "Statistical analysis", "Comparative analysis"]
        }
    }

    # Find best matching framework
    topic_lower = topic.lower()
    framework_key = "problem_solving"  # default

    for key in frameworks.keys():
        if key in topic_lower or any(word in topic_lower for word in key.split('_')):
            framework_key = key
            break

    guidance = {
        "topic": topic,
        "recommended_framework": framework_key,
        "framework": frameworks[framework_key],
        "additional_frameworks": list(frameworks.keys())
    }

    return json.dumps(guidance, indent=2)


@mcp.tool()
# pyright: ignore[reportArgumentType]
# type: ignore
# pyright: ignore[reportArgumentType]
async def update_prompt_metrics(prompt_id: str, successful: bool, steps: int = 0, user_rating: float = None, categories: List[str] = None) -> str:
    """
    Update usage metrics for a prompt.

    Args:
        prompt_id: ID of the prompt to update
        successful: Whether the prompt usage was successful
        steps: Number of steps taken
        user_rating: Optional user rating (0.0-5.0)
        categories: Optional list of categories

    Returns:
        Confirmation message
    """
    try:
        usage_data = {
            "successful": successful,
            "steps": steps,
            "user_rating": user_rating,
            "categories": categories or []
        }

        db_manager.update_prompt_metrics(prompt_id, usage_data)

        return f"Updated metrics for prompt {prompt_id}: successful={successful}, steps={steps}"

    except Exception as e:
        return f"Error updating metrics: {str(e)}"


def create_starlette_app(mcp_server: Server, *, debug: bool = False) -> Starlette:
    """Create a Starlette application that can serve the provided MCP server with SSE."""
    sse = SseServerTransport("/messages/")

    async def handle_sse(request: Request) -> None:
        """Handler for SSE connections."""
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
    import argparse

    parser = argparse.ArgumentParser(
        description='Sequential Thinking MCP Server')
    parser.add_argument('--transport', choices=['stdio', 'sse'], default='stdio',
                        help='Transport mode (stdio or sse)')
    parser.add_argument('--host', default='0.0.0.0',
                        help='Host to bind to (for SSE mode)')
    parser.add_argument('--port', type=int, default=7071,
                        help='Port to listen on (for SSE mode)')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug mode')
    args = parser.parse_args()

    if args.transport == 'stdio':
        mcp.run(transport='stdio')
    else:
        mcp_server = mcp._mcp_server
        starlette_app = create_starlette_app(mcp_server, debug=args.debug)
        uvicorn.run(starlette_app, host=args.host, port=args.port,
                    log_level="debug" if args.debug else "info")
