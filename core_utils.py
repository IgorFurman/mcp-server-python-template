#!/usr/bin/env python3
"""
Core utilities for Sequential Think MCP Server
High-quality utility functions focused on performance and maintainability
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, AsyncGenerator, Callable
import httpx
import sqlite3
from functools import wraps
import time
import os
import threading
from queue import Queue, Empty
import aiosqlite

logger = logging.getLogger(__name__)

# =============================================================================
# CONNECTION POOLING
# =============================================================================

class ConnectionPool:
    """Async SQLite connection pool for improved performance"""

    def __init__(self, db_path: str, max_connections: int = 20, min_connections: int = 5):
        self.db_path = db_path
        self.max_connections = max_connections
        self.min_connections = min_connections
        self._pool = asyncio.Queue(maxsize=max_connections)
        self._created_connections = 0
        self._lock = asyncio.Lock()
        self._initialized = False

    async def initialize(self):
        """Initialize the connection pool"""
        if self._initialized:
            return

        async with self._lock:
            if self._initialized:
                return

            # Create minimum connections
            for _ in range(self.min_connections):
                conn = await aiosqlite.connect(self.db_path)
                await conn.execute("PRAGMA journal_mode=WAL")
                await conn.execute("PRAGMA synchronous=NORMAL")
                await conn.execute("PRAGMA cache_size=10000")
                await conn.execute("PRAGMA temp_store=memory")
                await self._pool.put(conn)
                self._created_connections += 1

            self._initialized = True
            logger.info(f"✅ Connection pool initialized with {self.min_connections} connections")

    async def get_connection(self) -> aiosqlite.Connection:
        """Get a connection from the pool"""
        if not self._initialized:
            await self.initialize()

        try:
            # Try to get existing connection
            conn = await asyncio.wait_for(self._pool.get(), timeout=1.0)
            return conn
        except asyncio.TimeoutError:
            # Create new connection if under limit
            if self._created_connections < self.max_connections:
                async with self._lock:
                    if self._created_connections < self.max_connections:
                        conn = await aiosqlite.connect(self.db_path)
                        await conn.execute("PRAGMA journal_mode=WAL")
                        await conn.execute("PRAGMA synchronous=NORMAL")
                        await conn.execute("PRAGMA cache_size=10000")
                        await conn.execute("PRAGMA temp_store=memory")
                        self._created_connections += 1
                        logger.debug(f"Created new connection, total: {self._created_connections}")
                        return conn

            # Wait longer if at max capacity
            return await self._pool.get()

    async def return_connection(self, conn: aiosqlite.Connection):
        """Return a connection to the pool"""
        try:
            await self._pool.put(conn)
        except asyncio.QueueFull:
            # Close connection if pool is full
            await conn.close()
            self._created_connections -= 1

    @asynccontextmanager
    async def connection(self):
        """Context manager for getting and returning connections"""
        conn = await self.get_connection()
        try:
            yield conn
        finally:
            await self.return_connection(conn)

    async def close_all(self):
        """Close all connections in the pool"""
        while not self._pool.empty():
            try:
                conn = await asyncio.wait_for(self._pool.get(), timeout=0.1)
                await conn.close()
            except asyncio.TimeoutError:
                break

        self._created_connections = 0
        self._initialized = False
        logger.info("🧹 All database connections closed")

# Global connection pool instance
_db_pool = None

def get_db_pool() -> ConnectionPool:
    """Get the global database connection pool"""
    global _db_pool
    if _db_pool is None:
        # Get configuration from environment
        max_conn = int(os.getenv('DATABASE_POOL_SIZE', '20'))
        min_conn = int(os.getenv('DATABASE_MIN_CONNECTIONS', '5'))

        db_path = Path(__file__).parent / "sequential_think_prompts.db"
        _db_pool = ConnectionPool(str(db_path), max_conn, min_conn)
        logger.info(f"📊 Database pool configured: {min_conn}-{max_conn} connections")

    return _db_pool

# =============================================================================
# CONFIGURATION AND ENUMS
# =============================================================================

class ComplexityLevel(Enum):
    """Standardized complexity levels"""
    L1 = "L1"  # Simple (1-2 steps)
    L2 = "L2"  # Basic (3-4 steps)
    L3 = "L3"  # Intermediate (5-7 steps)
    L4 = "L4"  # Advanced (8-10 steps)
    L5 = "L5"  # Expert (10+ steps)

    @classmethod
    def is_valid(cls, level: str) -> bool:
        return level.upper() in [item.value for item in cls]

    @classmethod
    def normalize(cls, level: str) -> str:
        level = level.upper().strip()
        return level if cls.is_valid(level) else "L3"

class ContextLevel(Enum):
    """Context complexity levels"""
    C1 = "C1"  # General
    C2 = "C2"  # Specific
    C3 = "C3"  # Technical
    C4 = "C4"  # Professional
    C5 = "C5"  # Specialized

@dataclass
class ServerConfig:
    """Centralized server configuration"""
    # Database settings
    db_path: str = "sequential_think_prompts.db"
    db_pool_size: int = 10
    db_timeout: float = 30.0

    # API settings
    openai_api_key: Optional[str] = None
    deepseek_api_key: Optional[str] = None
    api_timeout: float = 30.0
    api_retries: int = 3

    # Ollama settings
    ollama_base_url: str = "http://localhost:11434"
    ollama_timeout: float = 120.0

    # Performance settings
    max_results: int = 100
    default_limit: int = 10
    cache_ttl: int = 300  # 5 minutes

    # Path settings
    base_path: Path = field(default_factory=lambda: Path(__file__).parent)
    sequential_think_path: Path = field(init=False)

    def __post_init__(self):
        self.sequential_think_path = self.base_path / "sequential-think"

# =============================================================================
# CUSTOM EXCEPTIONS
# =============================================================================

class SequentialThinkError(Exception):
    """Base exception for Sequential Think operations"""
    pass

class DatabaseError(SequentialThinkError):
    """Database operation errors"""
    pass

class AIServiceError(SequentialThinkError):
    """AI service errors"""
    pass

class ValidationError(SequentialThinkError):
    """Input validation errors"""
    pass

class ResourceError(SequentialThinkError):
    """Resource management errors"""
    pass

# =============================================================================
# PERFORMANCE UTILITIES
# =============================================================================

def performance_monitor(func_name: str = None):
    """Decorator to monitor function performance"""
    def decorator(func: Callable) -> Callable:
        name = func_name or f"{func.__module__}.{func.__name__}"

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                logger.debug(f"Function {name} completed in {duration:.3f}s")
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"Function {name} failed after {duration:.3f}s: {e}")
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                logger.debug(f"Function {name} completed in {duration:.3f}s")
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"Function {name} failed after {duration:.3f}s: {e}")
                raise

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

class Cache:
    """Simple in-memory cache with TTL"""

    def __init__(self, default_ttl: int = 300):
        self.default_ttl = default_ttl
        self._cache: Dict[str, Dict[str, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired"""
        if key in self._cache:
            entry = self._cache[key]
            if time.time() < entry['expires']:
                return entry['value']
            else:
                del self._cache[key]
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set cached value with TTL"""
        ttl = ttl or self.default_ttl
        self._cache[key] = {
            'value': value,
            'expires': time.time() + ttl
        }

    def clear(self) -> None:
        """Clear all cached entries"""
        self._cache.clear()

    def cleanup_expired(self) -> int:
        """Remove expired entries, return number removed"""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self._cache.items()
            if current_time >= entry['expires']
        ]
        for key in expired_keys:
            del self._cache[key]
        return len(expired_keys)

# =============================================================================
# DATABASE UTILITIES
# =============================================================================

class DatabasePool:
    """SQLite connection pool for better resource management"""

    def __init__(self, db_path: str, pool_size: int = 10, timeout: float = 30.0):
        self.db_path = db_path
        self.pool_size = pool_size
        self.timeout = timeout
        self._pool: List[sqlite3.Connection] = []
        self._pool_lock = asyncio.Lock()
        self._initialized = False

    async def initialize(self):
        """Initialize the connection pool"""
        if self._initialized:
            return

        async with self._pool_lock:
            if self._initialized:
                return

            for _ in range(self.pool_size):
                conn = await asyncio.to_thread(self._create_connection)
                self._pool.append(conn)

            self._initialized = True
            logger.info(f"Database pool initialized with {self.pool_size} connections")

    def _create_connection(self) -> sqlite3.Connection:
        """Create a new database connection with optimizations"""
        conn = sqlite3.connect(
            self.db_path,
            timeout=self.timeout,
            check_same_thread=False
        )

        # SQLite optimizations
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=10000")
        conn.execute("PRAGMA temp_store=MEMORY")

        return conn

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[sqlite3.Connection, None]:
        """Get a connection from the pool"""
        if not self._initialized:
            await self.initialize()

        async with self._pool_lock:
            if not self._pool:
                # Create temporary connection if pool exhausted
                conn = await asyncio.to_thread(self._create_connection)
                try:
                    yield conn
                finally:
                    await asyncio.to_thread(conn.close)
                return

            conn = self._pool.pop()

        try:
            yield conn
        finally:
            async with self._pool_lock:
                if len(self._pool) < self.pool_size:
                    self._pool.append(conn)
                else:
                    await asyncio.to_thread(conn.close)

    async def close_all(self):
        """Close all connections in the pool"""
        async with self._pool_lock:
            for conn in self._pool:
                await asyncio.to_thread(conn.close)
            self._pool.clear()
            self._initialized = False

# =============================================================================
# HTTP CLIENT UTILITIES
# =============================================================================

class HTTPClientManager:
    """Managed HTTP client with connection pooling and retry logic"""

    def __init__(self, timeout: float = 30.0, retries: int = 3):
        self.timeout = timeout
        self.retries = retries
        self._clients: Dict[str, httpx.AsyncClient] = {}

    def get_client(self, base_url: str, headers: Optional[Dict[str, str]] = None) -> httpx.AsyncClient:
        """Get or create HTTP client for base URL"""
        key = f"{base_url}:{hash(str(sorted((headers or {}).items())))}"

        if key not in self._clients:
            self._clients[key] = httpx.AsyncClient(
                base_url=base_url,
                headers=headers or {},
                timeout=httpx.Timeout(self.timeout),
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=100)
            )

        return self._clients[key]

    async def request_with_retry(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        **kwargs
    ) -> httpx.Response:
        """Make HTTP request with retry logic"""
        last_exception = None

        for attempt in range(self.retries + 1):
            try:
                response = await client.request(method, url, **kwargs)
                response.raise_for_status()
                return response
            except Exception as e:
                last_exception = e
                if attempt < self.retries:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Request failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Request failed after {self.retries + 1} attempts: {e}")

        raise AIServiceError(f"HTTP request failed after {self.retries + 1} attempts: {last_exception}")

    async def close_all(self):
        """Close all HTTP clients"""
        for client in self._clients.values():
            await client.aclose()
        self._clients.clear()

# =============================================================================
# DATA VALIDATION AND TRANSFORMATION
# =============================================================================

class DataTransformer:
    """High-quality data transformation utilities"""

    @staticmethod
    def normalize_prompt(prompt: str) -> str:
        """Normalize prompt text for consistency"""
        if not prompt:
            return ""

        # Normalize whitespace
        normalized = ' '.join(prompt.split())

        # Remove excessive punctuation
        import re
        normalized = re.sub(r'[.!?]{3,}', '...', normalized)
        normalized = re.sub(r'[,;:]{2,}', ',', normalized)

        return normalized.strip()

    @staticmethod
    def calculate_quality_score(
        effectiveness: float,
        usage_count: int,
        success_rate: float,
        complexity_bonus: float = 0.0
    ) -> float:
        """Calculate composite quality score"""
        # Base score from effectiveness
        base_score = effectiveness * 0.6

        # Usage bonus (logarithmic scaling)
        import math
        usage_bonus = min(0.2, math.log10(max(1, usage_count)) * 0.1)

        # Success rate bonus
        success_bonus = success_rate * 0.15

        # Complexity bonus
        complexity_bonus = min(0.05, complexity_bonus)

        total_score = base_score + usage_bonus + success_bonus + complexity_bonus
        return min(1.0, max(0.0, total_score))

    @staticmethod
    def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
        """Extract relevant keywords from text"""
        import re
        from collections import Counter

        # Simple keyword extraction
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())

        # Filter common words
        stop_words = {
            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had',
            'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his',
            'how', 'its', 'may', 'new', 'now', 'old', 'see', 'two', 'who', 'boy',
            'did', 'man', 'way', 'she', 'too', 'any', 'may', 'say', 'use', 'her'
        }

        filtered_words = [word for word in words if word not in stop_words and len(word) > 3]

        # Get most common words
        word_counts = Counter(filtered_words)
        return [word for word, _ in word_counts.most_common(max_keywords)]

    @staticmethod
    def format_search_results(results: List[Dict[str, Any]], query: str) -> str:
        """Format search results with rich formatting"""
        if not results:
            return f"No results found for query: '{query}'"

        formatted_results = []
        for i, result in enumerate(results, 1):
            # Quality indicators
            quality_score = result.get('quality_score', 0.0)
            effectiveness_score = result.get('effectiveness_score', 0.0)

            quality_emoji = "🟢" if quality_score >= 0.8 else "🟡" if quality_score >= 0.6 else "🔴"
            effectiveness_stars = "⭐" * min(5, int(effectiveness_score * 5))

            # Content preview
            content = result.get('content', '')
            preview = content[:150] + "..." if len(content) > 150 else content

            formatted_results.append(f"""
{i}. {quality_emoji} {result.get('title', 'Untitled')} ({result.get('complexity_level', 'N/A')})
   Domain: {result.get('domain', 'N/A')}
   Quality: {quality_score:.2f} | Effectiveness: {effectiveness_stars} ({effectiveness_score:.2f})
   Preview: {preview}
   Tags: {result.get('tags', 'N/A')}
""".strip())

        # Add summary statistics
        avg_quality = sum(r.get('quality_score', 0) for r in results) / len(results)
        high_quality_count = sum(1 for r in results if r.get('quality_score', 0) >= 0.8)

        summary = f"""
📊 Found {len(results)} results for '{query}'
📈 Average quality: {avg_quality:.2f} | High-quality results: {high_quality_count}
"""

        return summary + "\n" + "\n".join(formatted_results)

# =============================================================================
# GLOBAL INSTANCES
# =============================================================================

# Global configuration
config = ServerConfig()

# Global cache instance
cache = Cache(default_ttl=config.cache_ttl)

# Global HTTP client manager
http_manager = HTTPClientManager(
    timeout=config.api_timeout,
    retries=config.api_retries
)

# Global database pool (initialized lazily)
db_pool: Optional[DatabasePool] = None

async def get_db_pool() -> DatabasePool:
    """Get global database pool, initializing if needed"""
    global db_pool
    if db_pool is None:
        db_pool = DatabasePool(
            db_path=config.db_path,
            pool_size=config.db_pool_size,
            timeout=config.db_timeout
        )
        await db_pool.initialize()
    return db_pool

# Cleanup function for graceful shutdown
async def cleanup_resources():
    """Clean up all global resources"""
    global db_pool

    logger.info("Cleaning up resources...")

    if db_pool:
        await db_pool.close_all()
        db_pool = None

    await http_manager.close_all()
    cache.clear()

    logger.info("Resource cleanup completed")
