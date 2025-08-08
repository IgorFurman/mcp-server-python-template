#!/usr/bin/env python3
"""
AI Service Router - Intelligent routing and load balancing for AI backends
Supports Ollama, OpenAI, DeepSeek with automatic failover and load balancing
"""

import asyncio
import json
import logging
import time
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import httpx
import os
from redis_cache import cache, AICache

logger = logging.getLogger(__name__)

class AIBackend(Enum):
    """Supported AI backends"""
    OLLAMA = "ollama"
    OPENAI = "openai"
    DEEPSEEK = "deepseek"

class TaskType(Enum):
    """Types of AI tasks for routing optimization"""
    CODE_ANALYSIS = "code_analysis"
    COMPLEX_THINKING = "complex_thinking"
    GENERAL = "general"
    PROMPT_ENHANCEMENT = "prompt_enhancement"
    CLASSIFICATION = "classification"

@dataclass
class AIBackendConfig:
    """Configuration for an AI backend"""
    name: str
    base_url: str
    api_key: Optional[str]
    models: Dict[str, str]  # task_type -> model_name
    max_concurrent: int = 5
    timeout: int = 30
    priority: int = 1  # Lower = higher priority
    enabled: bool = True
    health_endpoint: str = ""

@dataclass
class AIRequest:
    """AI request structure"""
    prompt: str
    task_type: TaskType
    model_preference: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: float = 0.7
    system_prompt: Optional[str] = None

@dataclass
class AIResponse:
    """AI response structure"""
    content: str
    model: str
    backend: str
    latency_ms: int
    tokens_used: Optional[int] = None
    cached: bool = False

class AIRouter:
    """Intelligent AI service router with load balancing and failover"""

    def __init__(self):
        self.backends: Dict[str, AIBackendConfig] = {}
        self.backend_health: Dict[str, bool] = {}
        self.backend_load: Dict[str, int] = {}  # Current concurrent requests
        self.performance_metrics: Dict[str, Dict] = {}
        self._client = httpx.AsyncClient(timeout=30.0)

        # Initialize backends from environment
        self._initialize_backends()

    def _initialize_backends(self):
        """Initialize AI backends from environment configuration"""

        # Ollama configuration
        ollama_url = os.getenv('OLLAMA_URL', 'http://localhost:11434')
        self.backends['ollama'] = AIBackendConfig(
            name='ollama',
            base_url=ollama_url,
            api_key=None,
            models={
                'code_analysis': 'deepseek-r1:8b',
                'complex_thinking': 'deepseek-r1:8b',
                'general': 'llama3.2:latest',
                'prompt_enhancement': 'deepseek-r1:8b',
                'classification': 'llama3.2:latest'
            },
            max_concurrent=10,
            timeout=60,
            priority=1,
            health_endpoint=f'{ollama_url}/api/tags'
        )

        # OpenAI configuration
        if os.getenv('OPENAI_API_KEY'):
            self.backends['openai'] = AIBackendConfig(
                name='openai',
                base_url='https://api.openai.com/v1',
                api_key=os.getenv('OPENAI_API_KEY'),
                models={
                    'code_analysis': 'gpt-4o',
                    'complex_thinking': 'o1-preview',
                    'general': 'gpt-4o-mini',
                    'prompt_enhancement': 'gpt-4o',
                    'classification': 'gpt-4o-mini'
                },
                max_concurrent=5,
                timeout=30,
                priority=2,
                health_endpoint='https://api.openai.com/v1/models'
            )

        # DeepSeek configuration
        if os.getenv('DEEPSEEK_API_KEY'):
            self.backends['deepseek'] = AIBackendConfig(
                name='deepseek',
                base_url='https://api.deepseek.com/v1',
                api_key=os.getenv('DEEPSEEK_API_KEY'),
                models={
                    'code_analysis': 'deepseek-chat',
                    'complex_thinking': 'deepseek-reasoner',
                    'general': 'deepseek-chat',
                    'prompt_enhancement': 'deepseek-chat',
                    'classification': 'deepseek-chat'
                },
                max_concurrent=5,
                timeout=30,
                priority=3,
                health_endpoint='https://api.deepseek.com/v1/models'
            )

        # Initialize health and load tracking
        for backend_name in self.backends:
            self.backend_health[backend_name] = True
            self.backend_load[backend_name] = 0
            self.performance_metrics[backend_name] = {
                'total_requests': 0,
                'successful_requests': 0,
                'avg_latency': 0,
                'last_success': time.time()
            }

        logger.info(f"🤖 AI Router initialized with {len(self.backends)} backends")

    async def health_check(self, backend_name: str) -> bool:
        """Check health of a specific backend"""
        if backend_name not in self.backends:
            return False

        backend = self.backends[backend_name]

        try:
            # Check cached status first
            cached_status = await AICache.get_model_status(backend_name)
            if cached_status and time.time() - cached_status.get('timestamp', 0) < 300:
                return cached_status.get('healthy', False)

            # Perform health check
            if backend.name == 'ollama':
                response = await self._client.get(backend.health_endpoint)
                healthy = response.status_code == 200
            else:
                headers = {'Authorization': f'Bearer {backend.api_key}'}
                response = await self._client.get(backend.health_endpoint, headers=headers)
                healthy = response.status_code == 200

            # Cache result
            await AICache.set_model_status(backend_name, {
                'healthy': healthy,
                'timestamp': time.time()
            }, ttl=300)

            self.backend_health[backend_name] = healthy
            return healthy

        except Exception as e:
            logger.warning(f"Health check failed for {backend_name}: {e}")
            self.backend_health[backend_name] = False
            return False

    async def select_backend(self, request: AIRequest) -> Optional[str]:
        """Select the best backend for a request based on health, load, and task type"""

        # Get available backends
        available_backends = []

        for backend_name, backend in self.backends.items():
            if not backend.enabled:
                continue

            # Check health
            if not self.backend_health.get(backend_name, False):
                if not await self.health_check(backend_name):
                    continue

            # Check load
            if self.backend_load.get(backend_name, 0) >= backend.max_concurrent:
                continue

            # Check if backend supports the task type
            if request.task_type.value not in backend.models:
                continue

            available_backends.append((backend_name, backend))

        if not available_backends:
            logger.error("❌ No available AI backends")
            return None

        # Sort by priority and load
        available_backends.sort(key=lambda x: (
            x[1].priority,  # Primary: priority
            self.backend_load.get(x[0], 0),  # Secondary: current load
            -self.performance_metrics.get(x[0], {}).get('successful_requests', 0)  # Tertiary: success rate
        ))

        selected_backend = available_backends[0][0]
        logger.debug(f"🎯 Selected backend: {selected_backend} for task: {request.task_type.value}")

        return selected_backend

    async def _make_ollama_request(self, backend: AIBackendConfig, request: AIRequest) -> AIResponse:
        """Make request to Ollama backend"""
        model = backend.models.get(request.task_type.value, 'llama3.2:latest')

        payload = {
            "model": model,
            "prompt": request.prompt,
            "stream": False
        }

        if request.system_prompt:
            payload["system"] = request.system_prompt

        start_time = time.time()

        response = await self._client.post(
            f"{backend.base_url}/api/generate",
            json=payload
        )

        latency_ms = int((time.time() - start_time) * 1000)

        if response.status_code != 200:
            raise Exception(f"Ollama request failed: {response.status_code}")

        result = response.json()

        return AIResponse(
            content=result.get('response', ''),
            model=model,
            backend='ollama',
            latency_ms=latency_ms
        )

    async def _make_openai_request(self, backend: AIBackendConfig, request: AIRequest) -> AIResponse:
        """Make request to OpenAI backend"""
        model = backend.models.get(request.task_type.value, 'gpt-4o-mini')

        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})

        payload = {
            "model": model,
            "messages": messages,
            "temperature": request.temperature
        }

        if request.max_tokens:
            payload["max_tokens"] = request.max_tokens

        headers = {
            "Authorization": f"Bearer {backend.api_key}",
            "Content-Type": "application/json"
        }

        start_time = time.time()

        response = await self._client.post(
            f"{backend.base_url}/chat/completions",
            json=payload,
            headers=headers
        )

        latency_ms = int((time.time() - start_time) * 1000)

        if response.status_code != 200:
            raise Exception(f"OpenAI request failed: {response.status_code}")

        result = response.json()

        return AIResponse(
            content=result["choices"][0]["message"]["content"],
            model=model,
            backend='openai',
            latency_ms=latency_ms,
            tokens_used=result.get("usage", {}).get("total_tokens")
        )

    async def _make_deepseek_request(self, backend: AIBackendConfig, request: AIRequest) -> AIResponse:
        """Make request to DeepSeek backend"""
        model = backend.models.get(request.task_type.value, 'deepseek-chat')

        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})

        payload = {
            "model": model,
            "messages": messages,
            "temperature": request.temperature
        }

        if request.max_tokens:
            payload["max_tokens"] = request.max_tokens

        headers = {
            "Authorization": f"Bearer {backend.api_key}",
            "Content-Type": "application/json"
        }

        start_time = time.time()

        response = await self._client.post(
            f"{backend.base_url}/chat/completions",
            json=payload,
            headers=headers
        )

        latency_ms = int((time.time() - start_time) * 1000)

        if response.status_code != 200:
            raise Exception(f"DeepSeek request failed: {response.status_code}")

        result = response.json()

        return AIResponse(
            content=result["choices"][0]["message"]["content"],
            model=model,
            backend='deepseek',
            latency_ms=latency_ms,
            tokens_used=result.get("usage", {}).get("total_tokens")
        )

    async def process_request(self, request: AIRequest) -> Optional[AIResponse]:
        """Process an AI request with intelligent routing and failover"""

        # Check cache first
        cache_key = f"{request.task_type.value}_{hash(request.prompt)}"
        cached_response = await AICache.get_ai_response(request.prompt, request.task_type.value)

        if cached_response:
            logger.debug("✅ Cache hit for AI request")
            return AIResponse(
                content=cached_response,
                model="cached",
                backend="cache",
                latency_ms=1,
                cached=True
            )

        # Try backends in order of preference
        attempted_backends = []

        while len(attempted_backends) < len(self.backends):
            backend_name = await self.select_backend(request)

            if not backend_name or backend_name in attempted_backends:
                break

            attempted_backends.append(backend_name)
            backend = self.backends[backend_name]

            # Increment load counter
            self.backend_load[backend_name] += 1

            try:
                # Route to appropriate backend
                if backend_name == 'ollama':
                    response = await self._make_ollama_request(backend, request)
                elif backend_name == 'openai':
                    response = await self._make_openai_request(backend, request)
                elif backend_name == 'deepseek':
                    response = await self._make_deepseek_request(backend, request)
                else:
                    raise Exception(f"Unknown backend: {backend_name}")

                # Update metrics
                self._update_metrics(backend_name, True, response.latency_ms)

                # Cache successful response
                await AICache.set_ai_response(
                    request.prompt,
                    response.content,
                    request.task_type.value,
                    ttl=7200  # 2 hours
                )

                logger.info(f"✅ AI request completed via {backend_name} in {response.latency_ms}ms")
                return response

            except Exception as e:
                logger.warning(f"❌ Backend {backend_name} failed: {e}")
                self._update_metrics(backend_name, False, 0)
                self.backend_health[backend_name] = False

            finally:
                # Decrement load counter
                self.backend_load[backend_name] -= 1

        logger.error("❌ All AI backends failed")
        return None

    def _update_metrics(self, backend_name: str, success: bool, latency_ms: int):
        """Update performance metrics for a backend"""
        metrics = self.performance_metrics[backend_name]

        metrics['total_requests'] += 1
        if success:
            metrics['successful_requests'] += 1
            metrics['last_success'] = time.time()

            # Update average latency
            current_avg = metrics.get('avg_latency', 0)
            total_success = metrics['successful_requests']
            metrics['avg_latency'] = (current_avg * (total_success - 1) + latency_ms) / total_success

    async def get_router_stats(self) -> Dict:
        """Get router statistics and health"""
        stats = {
            "backends": {},
            "total_requests": 0,
            "total_successful": 0
        }

        for backend_name, backend in self.backends.items():
            metrics = self.performance_metrics[backend_name]
            stats["backends"][backend_name] = {
                "enabled": backend.enabled,
                "healthy": self.backend_health[backend_name],
                "current_load": self.backend_load[backend_name],
                "max_concurrent": backend.max_concurrent,
                "total_requests": metrics['total_requests'],
                "successful_requests": metrics['successful_requests'],
                "success_rate": round(
                    metrics['successful_requests'] / max(1, metrics['total_requests']) * 100, 2
                ),
                "avg_latency_ms": round(metrics.get('avg_latency', 0), 2),
                "models": backend.models
            }

            stats["total_requests"] += metrics['total_requests']
            stats["total_successful"] += metrics['successful_requests']

        stats["overall_success_rate"] = round(
            stats["total_successful"] / max(1, stats["total_requests"]) * 100, 2
        )

        return stats

# Global router instance
ai_router = AIRouter()
