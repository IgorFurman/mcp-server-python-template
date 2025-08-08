#!/usr/bin/env python3
"""
Sequential Think MCP Server - Consolidated High-Quality Implementation
Combines AI-powered prompt enhancement with local LLM capabilities and sophisticated database operations.
"""

import asyncio
import json
import logging
import os
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import httpx
import uvicorn
from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport
from mcp.server import Server
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Mount, Route

# Import our high-quality utilities
from core_utils import (
    ServerConfig, ComplexityLevel, ContextLevel,
    SequentialThinkError, DatabaseError, AIServiceError, ValidationError,
    performance_monitor, Cache, DatabasePool, HTTPClientManager, DataTransformer,
    config, cache, http_manager, get_db_pool, cleanup_resources
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("sequential-think-mcp-server")

# =============================================================================
# ENHANCED DATABASE OPERATIONS
# =============================================================================


class EnhancedDatabaseManager:
    """High-performance database manager with optimized queries and caching"""

    def __init__(self):
        self.cache = cache

    async def init_database(self):
        """Initialize database schema with optimizations"""
        db_pool = await get_db_pool()

        async with db_pool.get_connection() as conn:
            # Create main tables
            await asyncio.to_thread(conn.execute, '''
                CREATE TABLE IF NOT EXISTS prompts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    hash TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    original_prompt TEXT,
                    enhanced_prompt TEXT,
                    category TEXT NOT NULL,
                    complexity_level TEXT NOT NULL CHECK (complexity_level IN ('L1', 'L2', 'L3', 'L4', 'L5')),
                    context_level TEXT DEFAULT 'C2' CHECK (context_level IN ('C1', 'C2', 'C3', 'C4', 'C5')),
                    domain TEXT NOT NULL,
                    tags TEXT DEFAULT '',
                    effectiveness_score REAL DEFAULT 0.7 CHECK (effectiveness_score BETWEEN 0.0 AND 1.0),
                    quality_score REAL DEFAULT 0.7 CHECK (quality_score BETWEEN 0.0 AND 1.0),
                    usage_count INTEGER DEFAULT 0,
                    success_rate REAL DEFAULT 0.0 CHECK (success_rate BETWEEN 0.0 AND 1.0),
                    source_file TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            await asyncio.to_thread(conn.execute, '''
                CREATE TABLE IF NOT EXISTS prompt_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prompt_id INTEGER REFERENCES prompts(id),
                    successful BOOLEAN NOT NULL,
                    steps INTEGER DEFAULT 0,
                    user_rating REAL CHECK (user_rating BETWEEN 0.0 AND 5.0),
                    categories TEXT DEFAULT '[]',
                    execution_time REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            await asyncio.to_thread(conn.execute, '''
                CREATE TABLE IF NOT EXISTS frameworks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT NOT NULL,
                    methodology TEXT NOT NULL,
                    use_cases TEXT NOT NULL,
                    complexity_range TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Create optimized indexes
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_prompts_domain ON prompts(domain)",
                "CREATE INDEX IF NOT EXISTS idx_prompts_complexity ON prompts(complexity_level)",
                "CREATE INDEX IF NOT EXISTS idx_prompts_quality ON prompts(quality_score)",
                "CREATE INDEX IF NOT EXISTS idx_prompts_effectiveness ON prompts(effectiveness_score)",
                "CREATE INDEX IF NOT EXISTS idx_prompts_hash ON prompts(hash)",
                "CREATE INDEX IF NOT EXISTS idx_metrics_prompt_id ON prompt_metrics(prompt_id)",
                "CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON prompt_metrics(timestamp)"
            ]

            for index_sql in indexes:
                await asyncio.to_thread(conn.execute, index_sql)

            # Create FTS5 virtual table for full-text search
            await asyncio.to_thread(conn.execute, '''
                CREATE VIRTUAL TABLE IF NOT EXISTS prompts_fts USING fts5(
                    title, content, domain, tags, category,
                    content=prompts,
                    tokenize='unicode61 remove_diacritics 2'
                )
            ''')

            # Create trigger to keep FTS in sync
            await asyncio.to_thread(conn.execute, '''
                CREATE TRIGGER IF NOT EXISTS prompts_fts_insert AFTER INSERT ON prompts BEGIN
                    INSERT INTO prompts_fts(rowid, title, content, domain, tags, category)
                    VALUES (new.id, new.title, new.content, new.domain, new.tags, new.category);
                END
            ''')

            await asyncio.to_thread(conn.execute, '''
                CREATE TRIGGER IF NOT EXISTS prompts_fts_update AFTER UPDATE ON prompts BEGIN
                    UPDATE prompts_fts SET
                        title = new.title,
                        content = new.content,
                        domain = new.domain,
                        tags = new.tags,
                        category = new.category
                    WHERE rowid = new.id;
                END
            ''')

            await asyncio.to_thread(conn.execute, '''
                CREATE TRIGGER IF NOT EXISTS prompts_fts_delete AFTER DELETE ON prompts BEGIN
                    DELETE FROM prompts_fts WHERE rowid = old.id;
                END
            ''')

            await asyncio.to_thread(conn.commit)
            logger.info("Database initialized with optimized schema")

    @performance_monitor("search_prompts")
    async def search_prompts(
        self,
        query: str,
        category: Optional[str] = None,
        complexity: Optional[str] = None,
        min_effectiveness: float = 0.0,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Enhanced search with FTS, caching, and relevance scoring"""

        # Create cache key
        cache_key = f"search:{query}:{category}:{complexity}:{min_effectiveness}:{limit}"
        cached_result = self.cache.get(cache_key)
        if cached_result:
            return cached_result

        db_pool = await get_db_pool()

        async with db_pool.get_connection() as conn:
            conn.row_factory = sqlite3.Row

            # Try FTS search first
            try:
                sql = '''
                    SELECT p.*,
                           (p.effectiveness_score * p.quality_score * p.usage_count * 0.1) as relevance_score,
                           bm25(prompts_fts) as fts_score
                    FROM prompts p
                    JOIN prompts_fts fts ON p.id = fts.rowid
                    WHERE prompts_fts MATCH ?
                '''
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

                sql += " ORDER BY relevance_score DESC, fts_score LIMIT ?"
                params.append(limit)

                cursor = await asyncio.to_thread(conn.execute, sql, params)
                results = [dict(row) for row in await asyncio.to_thread(cursor.fetchall)]

                if results:
                    self.cache.set(cache_key, results)
                    return results

            except Exception as e:
                logger.warning(f"FTS search failed, falling back to LIKE: {e}")

            # Fallback to LIKE search
            sql = '''
                SELECT *,
                       (effectiveness_score * quality_score * usage_count * 0.1) as relevance_score
                FROM prompts
                WHERE (content LIKE ? OR title LIKE ? OR domain LIKE ? OR tags LIKE ?)
            '''
            like_query = f"%{query}%"
            params = [like_query, like_query, like_query, like_query]

            if category:
                sql += " AND category = ?"
                params.append(category)

            if complexity:
                sql += " AND complexity_level = ?"
                params.append(complexity)

            if min_effectiveness > 0:
                sql += " AND effectiveness_score >= ?"
                params.append(min_effectiveness)

            sql += " ORDER BY relevance_score DESC LIMIT ?"
            params.append(limit)

            cursor = await asyncio.to_thread(conn.execute, sql, params)
            results = [dict(row) for row in await asyncio.to_thread(cursor.fetchall)]

            self.cache.set(cache_key, results)
            return results

    @performance_monitor("store_prompt_analysis")
    async def store_prompt_analysis(self, analysis: Dict[str, Any]) -> str:
        """Store enhanced prompt analysis with deduplication"""
        db_pool = await get_db_pool()

        # Generate content hash for deduplication
        import hashlib
        content_hash = hashlib.md5(
            analysis['original_prompt'].encode()).hexdigest()

        async with db_pool.get_connection() as conn:
            # Check if prompt already exists
            cursor = await asyncio.to_thread(
                conn.execute,
                "SELECT id FROM prompts WHERE hash = ?",
                (content_hash,)
            )
            existing = await asyncio.to_thread(cursor.fetchone)

            if existing:
                # Update existing prompt
                await asyncio.to_thread(conn.execute, '''
                    UPDATE prompts SET
                        enhanced_prompt = ?, effectiveness_score = ?, quality_score = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE hash = ?
                ''', (
                    analysis.get('optimized_prompt', ''),
                    analysis.get('effectiveness', 0.7),
                    analysis.get('quality_score', 0.7),
                    content_hash
                ))
                prompt_id = existing[0]
            else:
                # Insert new prompt
                await asyncio.to_thread(conn.execute, '''
                    INSERT INTO prompts
                    (hash, title, content, original_prompt, enhanced_prompt, category,
                     complexity_level, context_level, domain, effectiveness_score, quality_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    content_hash,
                    analysis.get('title', 'Enhanced Prompt'),
                    analysis['original_prompt'],
                    analysis['original_prompt'],
                    analysis.get('optimized_prompt', ''),
                    analysis.get('category', 'general'),
                    analysis.get('complexity', 'L3'),
                    analysis.get('context', 'C2'),
                    analysis.get('domain', 'general'),
                    analysis.get('effectiveness', 0.7),
                    analysis.get('quality_score', 0.7)
                ))

                cursor = await asyncio.to_thread(conn.execute, "SELECT last_insert_rowid()")
                prompt_id = (await asyncio.to_thread(cursor.fetchone))[0]

            await asyncio.to_thread(conn.commit)

            # Clear relevant cache entries
            self.cache.clear()

            return str(prompt_id)

# =============================================================================
# AI SERVICE INTEGRATIONS
# =============================================================================


class EnhancedAIServiceManager:
    """High-performance AI service manager with connection pooling and caching"""

    def __init__(self):
        self.http_manager = http_manager
        self.cache = cache

        # Initialize clients
        self.openai_client = None
        self.deepseek_client = None

        if config.openai_api_key:
            self.openai_client = self.http_manager.get_client(
                "https://api.openai.com/v1",
                {"Authorization": f"Bearer {config.openai_api_key}"}
            )

        if config.deepseek_api_key:
            self.deepseek_client = self.http_manager.get_client(
                "https://api.deepseek.com/v1",
                {"Authorization": f"Bearer {config.deepseek_api_key}"}
            )

    @performance_monitor("enhance_prompt_with_ai")
    async def enhance_prompt_with_ai(self, prompt: str, domain: str = "general") -> Dict[str, Any]:
        """Enhanced AI prompt optimization with caching and retry logic"""

        # Check cache first
        cache_key = f"enhance:{hash(prompt)}:{domain}"
        cached_result = self.cache.get(cache_key)
        if cached_result:
            return cached_result

        # Normalize prompt
        normalized_prompt = DataTransformer.normalize_prompt(prompt)

        enhancement_prompt = f"""
        Analyze and enhance the following prompt for maximum effectiveness:

        Original: "{normalized_prompt}"
        Domain: {domain}

        Provide analysis in JSON format:
        {{
            "complexity": "L1|L2|L3|L4|L5",
            "context": "C1|C2|C3|C4|C5",
            "effectiveness": 0.0-1.0,
            "quality_score": 0.0-1.0,
            "improvements": ["specific improvement 1", "improvement 2"],
            "optimized_prompt": "enhanced version with clear structure and actionable steps",
            "keywords": ["key1", "key2", "key3"],
            "estimated_steps": number_of_thinking_steps_needed
        }}
        """

        # Try services in order of preference
        services = [
            (self.deepseek_client, "deepseek-coder"),
            (self.openai_client, "gpt-3.5-turbo")
        ]

        for client, model in services:
            if not client:
                continue

            try:
                response = await self.http_manager.request_with_retry(
                    client, "POST", "/chat/completions",
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": "You are an expert prompt engineer. Respond only with valid JSON."},
                            {"role": "user", "content": enhancement_prompt}
                        ],
                        "temperature": 0.3,
                        "max_tokens": 1500
                    }
                )

                result = response.json()
                content = result['choices'][0]['message']['content']

                try:
                    enhancement_data = json.loads(content)

                    # Validate and normalize the response
                    enhancement_data['complexity'] = ComplexityLevel.normalize(
                        enhancement_data.get('complexity', 'L3')
                    )
                    enhancement_data['effectiveness'] = max(0.0, min(1.0,
                                                                     enhancement_data.get(
                                                                         'effectiveness', 0.7)
                                                                     ))
                    enhancement_data['quality_score'] = DataTransformer.calculate_quality_score(
                        enhancement_data['effectiveness'], 1, 1.0
                    )

                    # Extract keywords if not provided
                    if 'keywords' not in enhancement_data:
                        enhancement_data['keywords'] = DataTransformer.extract_keywords(
                            enhancement_data.get('optimized_prompt', prompt)
                        )

                    # Cache the result
                    self.cache.set(cache_key, enhancement_data)
                    return enhancement_data

                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse AI response as JSON: {e}")
                    continue

            except Exception as e:
                logger.warning(f"AI service {model} failed: {e}")
                continue

        # Fallback enhancement
        fallback_result = {
            "complexity": "L3",
            "context": "C2",
            "effectiveness": 0.6,
            "quality_score": 0.6,
            "improvements": ["Add specific examples", "Include success criteria", "Structure with clear steps"],
            "optimized_prompt": f"Enhanced: {normalized_prompt}\n\nPlease provide:\n1. Specific, actionable steps\n2. Clear success criteria\n3. Relevant examples\n4. Expected outcomes",
            "keywords": DataTransformer.extract_keywords(prompt),
            "estimated_steps": 5
        }

        self.cache.set(cache_key, fallback_result)
        return fallback_result

# =============================================================================
# OLLAMA LOCAL LLM INTEGRATION
# =============================================================================


class EnhancedOllamaClient:
    """High-performance Ollama client with connection pooling and model management"""

    def __init__(self):
        self.http_manager = http_manager
        self.client = self.http_manager.get_client(config.ollama_base_url)
        self.cache = cache
        self._available_models = None
        self._model_cache_time = 0

    @performance_monitor("check_availability")
    async def is_available(self) -> bool:
        """Check if Ollama service is available with caching"""
        cache_key = "ollama:availability"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            response = await self.client.get("/api/tags", timeout=5.0)
            available = response.status_code == 200
            self.cache.set(cache_key, available, ttl=60)  # Cache for 1 minute
            return available
        except Exception:
            self.cache.set(cache_key, False, ttl=60)
            return False

    @performance_monitor("list_models")
    async def list_models(self) -> List[str]:
        """List available models with caching"""
        current_time = datetime.now().timestamp()

        # Use cached models if recent
        if self._available_models and (current_time - self._model_cache_time) < 300:
            return self._available_models

        try:
            response = await self.client.get("/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = [model['name'] for model in data.get('models', [])]
                self._available_models = models
                self._model_cache_time = current_time
                return models
        except Exception as e:
            logger.error(f"Failed to list Ollama models: {e}")

        return []

    @performance_monitor("generate_response")
    async def generate(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 2000
    ) -> str:
        """Generate response with optimized parameters"""

        # Check cache
        cache_key = f"ollama:{model}:{hash(prompt)}:{hash(system or '')}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "num_predict": max_tokens
                }
            }

            if system:
                payload["system"] = system

            response = await self.client.post(
                "/api/generate",
                json=payload,
                timeout=config.ollama_timeout
            )

            if response.status_code == 200:
                result = response.json().get('response', '')
                # Cache successful responses
                self.cache.set(cache_key, result, ttl=1800)  # 30 minutes
                return result
            else:
                return f"Error: HTTP {response.status_code} - {response.text}"

        except Exception as e:
            error_msg = f"Ollama generation failed: {str(e)}"
            logger.error(error_msg)
            return error_msg

# =============================================================================
# TYPESCRIPT CLI INTEGRATION
# =============================================================================


class EnhancedSequentialThinkIntegration:
    """Optimized TypeScript CLI integration with input validation"""

    def __init__(self):
        self.cli_path = config.sequential_think_path / "ai" / "cli.ts"
        self.cache = cache

    @performance_monitor("call_sequential_think")
    async def call_sequential_think(
        self,
        prompt: str,
        thoughts: int = 5,
        verbose: bool = True
    ) -> str:
        """Call TypeScript CLI with proper validation and caching"""

        # Validate inputs
        if not prompt or len(prompt.strip()) == 0:
            raise ValidationError("Prompt cannot be empty")

        if not (1 <= thoughts <= 20):
            raise ValidationError("Thoughts must be between 1 and 20")

        # Check cache
        cache_key = f"sequential_think:{hash(prompt)}:{thoughts}:{verbose}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        if not self.cli_path.exists():
            raise ValidationError("Sequential Think CLI not found")

        # Normalize prompt to prevent issues
        normalized_prompt = DataTransformer.normalize_prompt(prompt)

        try:
            # Create safe command
            cmd = [
                "npx", "ts-node", str(self.cli_path),
                "enhance",
                "-p", normalized_prompt,
                "-t", str(thoughts)
            ]

            if verbose:
                cmd.append("-v")

            # Run with timeout and proper error handling
            result = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(config.sequential_think_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(result.communicate(), timeout=60.0)

            if result.returncode == 0:
                output = stdout.decode('utf-8', errors='replace')
                self.cache.set(cache_key, output, ttl=1800)  # 30 minutes
                return output
            else:
                error_output = stderr.decode('utf-8', errors='replace')
                raise AIServiceError(
                    f"Sequential Think CLI failed: {error_output}")

        except asyncio.TimeoutError:
            raise AIServiceError("Sequential Think CLI timed out")
        except Exception as e:
            raise AIServiceError(f"Sequential Think CLI error: {str(e)}")

# =============================================================================
# INITIALIZE COMPONENTS
# =============================================================================


db_manager = EnhancedDatabaseManager()
ai_manager = EnhancedAIServiceManager()
ollama_client = EnhancedOllamaClient()
sequential_think = EnhancedSequentialThinkIntegration()

# =============================================================================
# MCP TOOL IMPLEMENTATIONS
# =============================================================================


@mcp.tool()
async def enhance_prompt(
    prompt: str,
    domain: str = "general",
    complexity_level: str = "L3",
    use_local_llm: bool = False,
    model: str = "llama3.2:1b"
) -> str:
    """
    Enhance a prompt using AI-powered optimization with multiple fallback options.

    Args:
        prompt: The original prompt to enhance
        domain: Domain context (e.g., "coding", "writing", "analysis")
        complexity_level: Target complexity level (L1-L5)
        use_local_llm: Whether to prefer local LLM over cloud APIs
        model: Local LLM model name

    Returns:
        Enhanced prompt with comprehensive analysis
    """
    try:
        # Validate inputs
        if not prompt.strip():
            raise ValidationError("Prompt cannot be empty")

        complexity_level = ComplexityLevel.normalize(complexity_level)

        # Choose enhancement method based on preference and availability
        if use_local_llm and await ollama_client.is_available():
            system_prompt = f"""
            You are an expert prompt engineer specializing in {domain} domain.
            Enhance the prompt to achieve {complexity_level} complexity:

            L1-L2: Simple, focused tasks (1-4 steps)
            L3-L4: Complex analysis requiring systematic approach (5-10 steps)
            L5: Comprehensive architectural decisions (10+ steps)

            Provide clear, structured, actionable enhancement.
            """

            enhanced = await ollama_client.generate(
                model=model,
                prompt=f"Original prompt: {prompt}\n\nEnhance this prompt:",
                system=system_prompt
            )

            return f"Enhanced Prompt ({complexity_level}):\n{enhanced}"
        else:
            # Use cloud AI services
            enhancement = await ai_manager.enhance_prompt_with_ai(prompt, domain)

            # Create comprehensive analysis
            analysis = {
                "id": f"prompt_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "original_prompt": prompt,
                "optimized_prompt": enhancement["optimized_prompt"],
                "complexity": enhancement["complexity"],
                "context": enhancement.get("context", "C2"),
                "domain": domain,
                "effectiveness": enhancement["effectiveness"],
                "quality_score": enhancement["quality_score"],
                "improvements": enhancement["improvements"],
                "keywords": enhancement.get("keywords", []),
                "estimated_steps": enhancement.get("estimated_steps", 5),
                "timestamp": datetime.now().isoformat()
            }

            # Store analysis in database
            await db_manager.store_prompt_analysis(analysis)

            return json.dumps(analysis, indent=2)

    except Exception as e:
        logger.error(f"Error in enhance_prompt: {e}")
        raise AIServiceError(f"Enhancement failed: {str(e)}")


@mcp.tool()
async def search_prompts(
    query: str,
    category: Optional[str] = None,
    complexity: Optional[str] = None,
    min_effectiveness: float = 0.0,
    limit: int = 10
) -> str:
    """
    Search the prompt database with advanced filtering and relevance scoring.

    Args:
        query: Search terms
        category: Filter by category
        complexity: Filter by complexity level (L1-L5)
        min_effectiveness: Minimum effectiveness score (0.0-1.0)
        limit: Maximum results to return

    Returns:
        Formatted search results with quality metrics
    """
    try:
        # Validate inputs
        if not query.strip():
            raise ValidationError("Query cannot be empty")

        if complexity:
            complexity = ComplexityLevel.normalize(complexity)

        if not (0.0 <= min_effectiveness <= 1.0):
            raise ValidationError(
                "min_effectiveness must be between 0.0 and 1.0")

        if not (1 <= limit <= config.max_results):
            raise ValidationError(
                f"limit must be between 1 and {config.max_results}")

        # Perform search
        results = await db_manager.search_prompts(
            query, category, complexity, min_effectiveness, limit
        )

        if not results:
            suggestions = [
                "Try broader search terms",
                "Reduce filters (category, complexity, effectiveness)",
                "Check spelling and try synonyms"
            ]
            return f"No results found for '{query}'\n\nSuggestions:\n" + "\n".join(f"• {s}" for s in suggestions)

        # Format results with rich information
        return DataTransformer.format_search_results(results, query)

    except Exception as e:
        logger.error(f"Error in search_prompts: {e}")
        raise DatabaseError(f"Search failed: {str(e)}")


@mcp.tool()
async def classify_prompt(prompt: str, detailed: bool = True) -> str:
    """
    Classify prompt complexity and provide comprehensive analysis.

    Args:
        prompt: Prompt to analyze
        detailed: Whether to provide detailed analysis

    Returns:
        Classification results with recommendations
    """
    try:
        if not prompt.strip():
            raise ValidationError("Prompt cannot be empty")

        # Use AI for classification if available
        if await ollama_client.is_available():
            models = await ollama_client.list_models()
            if models:
                system_prompt = """
                Analyze this prompt and classify it according to Sequential Thinking complexity:

                L1: Simple tasks (1-2 steps) - Basic questions, direct requests
                L2: Moderate tasks (3-4 steps) - Simple problem-solving
                L3: Complex tasks (5-7 steps) - Multi-step analysis
                L4: Advanced tasks (8-10 steps) - Complex problem-solving
                L5: Expert tasks (10+ steps) - Comprehensive analysis

                Provide:
                1. Complexity Level (L1-L5)
                2. Context Level (C1-C5)
                3. Domain Classification
                4. Estimated thinking steps needed
                5. Key challenges and considerations
                """

                classification = await ollama_client.generate(
                    model=models[0],
                    prompt=f"Classify: {prompt}",
                    system=system_prompt
                )

                return f"Prompt Classification:\n{classification}"

        # Fallback to rule-based classification
        word_count = len(prompt.split())
        question_marks = prompt.count('?')
        complexity_indicators = ['analyze', 'compare',
                                 'evaluate', 'synthesize', 'design', 'architect']

        # Simple heuristic classification
        if word_count < 10 or question_marks == 1:
            complexity = "L1"
        elif word_count < 25:
            complexity = "L2"
        elif any(indicator in prompt.lower() for indicator in complexity_indicators):
            complexity = "L4"
        else:
            complexity = "L3"

        classification = {
            "complexity_level": complexity,
            "context_level": "C2",
            "word_count": word_count,
            "estimated_steps": {"L1": 2, "L2": 4, "L3": 6, "L4": 9, "L5": 12}.get(complexity, 6),
            "domain": "general",
            "keywords": DataTransformer.extract_keywords(prompt, 5)
        }

        if detailed:
            return json.dumps(classification, indent=2)
        else:
            return f"Classification: {complexity} ({classification['estimated_steps']} steps estimated)"

    except Exception as e:
        logger.error(f"Error in classify_prompt: {e}")
        raise AIServiceError(f"Classification failed: {str(e)}")


@mcp.tool()
async def get_prompt_recommendations(
    domain: Optional[str] = None,
    complexity: Optional[str] = None,
    limit: int = 5
) -> str:
    """
    Get high-quality prompt recommendations with filtering.

    Args:
        domain: Filter by domain
        complexity: Filter by complexity level
        limit: Maximum recommendations

    Returns:
        Curated list of high-quality prompts
    """
    try:
        if complexity:
            complexity = ComplexityLevel.normalize(complexity)

        if not (1 <= limit <= 20):
            raise ValidationError("limit must be between 1 and 20")

        db_pool = await get_db_pool()

        async with db_pool.get_connection() as conn:
            conn.row_factory = sqlite3.Row

            sql = '''
                SELECT *,
                       (effectiveness_score * 0.4 + quality_score * 0.4 + (usage_count * 0.01) + success_rate * 0.2) as recommendation_score
                FROM prompts
                WHERE effectiveness_score >= 0.7 AND quality_score >= 0.7
            '''
            params = []

            if domain:
                sql += " AND domain LIKE ?"
                params.append(f"%{domain}%")

            if complexity:
                sql += " AND complexity_level = ?"
                params.append(complexity)

            sql += " ORDER BY recommendation_score DESC LIMIT ?"
            params.append(limit)

            cursor = await asyncio.to_thread(conn.execute, sql, params)
            results = [dict(row) for row in await asyncio.to_thread(cursor.fetchall)]

        if not results:
            filter_desc = f" for domain '{domain}'" if domain else ""
            filter_desc += f" at complexity '{complexity}'" if complexity else ""
            return f"No high-quality recommendations found{filter_desc}"

        formatted_results = []
        for i, result in enumerate(results, 1):
            score = result.get('recommendation_score', 0)
            score_emoji = "🏆" if score >= 0.9 else "🥇" if score >= 0.8 else "🥈"

            formatted_results.append(f"""
{i}. {score_emoji} {result['title']} ({result['complexity_level']})
   Domain: {result['domain']} | Score: {score:.2f}
   Usage: {result.get('usage_count', 0)} times | Success: {result.get('success_rate', 0):.1%}
   Preview: {result['content'][:120]}...
""".strip())

        return f"🎯 Top {len(results)} Recommended Prompts:\n\n" + "\n\n".join(formatted_results)

    except Exception as e:
        logger.error(f"Error in get_prompt_recommendations: {e}")
        raise DatabaseError(f"Recommendations failed: {str(e)}")


@mcp.tool()
async def check_ollama_status() -> str:
    """Check Ollama service status and available models"""
    try:
        is_available = await ollama_client.is_available()

        if not is_available:
            return """
🔴 Ollama Status: Not Available

To enable local AI capabilities:
1. Install Ollama: https://ollama.ai/
2. Start service: ollama serve
3. Install model: ollama pull llama3.2:1b
4. Verify: ollama list

Fallback to cloud APIs and TypeScript CLI available.
"""

        models = await ollama_client.list_models()

        status = "🟢 Ollama Status: Available\n\n"

        if models:
            status += "📦 Available Models:\n"
            for model in models:
                status += f"  • {model}\n"
            status += "\n✅ Ready for local AI processing!"
        else:
            status += "⚠️  No models installed\nInstall with: ollama pull llama3.2:1b"

        return status

    except Exception as e:
        logger.error(f"Error checking Ollama status: {e}")
        return f"❌ Error checking Ollama: {str(e)}"


@mcp.tool()
async def run_sequential_think_cli(prompt: str, thoughts: int = 5) -> str:
    """
    Run the TypeScript Sequential Think CLI with validation.

    Args:
        prompt: Prompt to process
        thoughts: Number of thinking steps (1-20)

    Returns:
        Sequential thinking analysis
    """
    try:
        return await sequential_think.call_sequential_think(prompt, thoughts, verbose=True)
    except Exception as e:
        logger.error(f"Error in run_sequential_think_cli: {e}")
        raise AIServiceError(f"CLI execution failed: {str(e)}")


@mcp.tool()
async def get_database_stats() -> str:
    """Get comprehensive database statistics and health metrics"""
    try:
        db_pool = await get_db_pool()

        async with db_pool.get_connection() as conn:
            conn.row_factory = sqlite3.Row

            # Basic statistics
            stats_queries = {
                'total_prompts': "SELECT COUNT(*) as count FROM prompts",
                'avg_quality': "SELECT AVG(quality_score) as avg FROM prompts",
                'avg_effectiveness': "SELECT AVG(effectiveness_score) as avg FROM prompts",
                'high_quality': "SELECT COUNT(*) as count FROM prompts WHERE quality_score >= 0.8",
                'total_usage': "SELECT SUM(usage_count) as sum FROM prompts"
            }

            stats = {}
            for key, query in stats_queries.items():
                cursor = await asyncio.to_thread(conn.execute, query)
                result = await asyncio.to_thread(cursor.fetchone)
                stats[key] = result[0] if result[0] is not None else 0

            # Domain distribution
            cursor = await asyncio.to_thread(conn.execute, '''
                SELECT domain, COUNT(*) as count, AVG(quality_score) as avg_quality
                FROM prompts
                GROUP BY domain
                ORDER BY count DESC
                LIMIT 8
            ''')
            domains = await asyncio.to_thread(cursor.fetchall)

            # Complexity distribution
            cursor = await asyncio.to_thread(conn.execute, '''
                SELECT complexity_level, COUNT(*) as count, AVG(effectiveness_score) as avg_effectiveness
                FROM prompts
                GROUP BY complexity_level
                ORDER BY complexity_level
            ''')
            complexity_dist = await asyncio.to_thread(cursor.fetchall)

        # Format comprehensive report
        report = f"""
📊 Sequential Think Database Analytics

📈 Overview:
• Total Prompts: {stats['total_prompts']:,}
• Average Quality: {stats['avg_quality']:.3f}
• Average Effectiveness: {stats['avg_effectiveness']:.3f}
• High-Quality Prompts: {stats['high_quality']:,} ({stats['high_quality']/max(1, stats['total_prompts'])*100:.1f}%)
• Total Usage Count: {stats['total_usage']:,}

🏷️ Top Domains:
"""

        for domain in domains:
            percentage = (domain['count'] /
                          max(1, stats['total_prompts'])) * 100
            report += f"• {domain['domain']}: {domain['count']} prompts ({percentage:.1f}%) - Quality: {domain['avg_quality']:.2f}\n"

        report += "\n📊 Complexity Distribution:\n"
        for level in complexity_dist:
            percentage = (level['count'] /
                          max(1, stats['total_prompts'])) * 100
            report += f"• {level['complexity_level']}: {level['count']} prompts ({percentage:.1f}%) - Effectiveness: {level['avg_effectiveness']:.2f}\n"

        # Cache performance metrics
        expired_entries = cache.cleanup_expired()
        report += f"\n🚀 Performance:\n• Cache entries cleaned: {expired_entries}\n• Database pool initialized: ✅"

        return report

    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        raise DatabaseError(f"Stats retrieval failed: {str(e)}")

# =============================================================================
# SERVER SETUP AND STARTUP
# =============================================================================


def create_starlette_app(mcp_server: Server, *, debug: bool = False) -> Starlette:
    """Create optimized Starlette application for SSE transport"""
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


async def startup_sequence():
    """Perform startup initialization"""
    logger.info("🚀 Starting Sequential Think MCP Server...")

    try:
        # Initialize database
        await db_manager.init_database()
        logger.info("✅ Database initialized")

        # Check service availability
        ollama_available = await ollama_client.is_available()
        logger.info(f"🤖 Ollama available: {'✅' if ollama_available else '❌'}")

        if ollama_available:
            models = await ollama_client.list_models()
            logger.info(f"📦 Ollama models: {len(models)} available")

        # Test AI services
        ai_services = []
        if ai_manager.openai_client:
            ai_services.append("OpenAI")
        if ai_manager.deepseek_client:
            ai_services.append("DeepSeek")

        logger.info(
            f"🔌 AI Services: {', '.join(ai_services) if ai_services else 'None configured'}")

        # Check CLI availability
        cli_available = sequential_think.cli_path.exists()
        logger.info(f"⚡ TypeScript CLI: {'✅' if cli_available else '❌'}")

        logger.info("🌟 Sequential Think MCP Server ready!")

    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description='Sequential Think MCP Server - High Performance Edition')
    parser.add_argument('--transport', choices=['stdio', 'sse'], default='stdio',
                        help='Transport mode (stdio for CLI, sse for web)')
    parser.add_argument('--host', default='0.0.0.0', help='Host for SSE mode')
    parser.add_argument('--port', type=int, default=7071,
                        help='Port for SSE mode')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug mode')
    parser.add_argument('--init-db', action='store_true',
                        help='Initialize database and exit')

    args = parser.parse_args()

    # Configure logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    async def main():
        try:
            await startup_sequence()

            if args.init_db:
                logger.info("Database initialization completed")
                return

            if args.transport == 'stdio':
                mcp.run(transport='stdio')
            else:
                mcp_server = mcp._mcp_server
                app = create_starlette_app(mcp_server, debug=args.debug)

                logger.info(
                    f"🌐 Starting SSE server on http://{args.host}:{args.port}")

                # Use uvicorn server directly instead of uvicorn.run() to avoid event loop conflicts
                import uvicorn
                config = uvicorn.Config(
                    app,
                    host=args.host,
                    port=args.port,
                    log_level="debug" if args.debug else "info",
                    loop="asyncio"
                )
                server = uvicorn.Server(config)
                await server.serve()

        except KeyboardInterrupt:
            logger.info("⏹️  Shutdown requested")
        except Exception as e:
            logger.error(f"❌ Server error: {e}")
        finally:
            logger.info("🧹 Cleaning up resources...")
            await cleanup_resources()
            logger.info("👋 Sequential Think MCP Server stopped")

    # Handle event loop properly
    try:
        loop = asyncio.get_running_loop()
        # If we're already in an event loop, create a task
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.submit(lambda: asyncio.run(main())).result()
    except RuntimeError:
        # No event loop running, safe to use asyncio.run()
        asyncio.run(main())
