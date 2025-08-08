#!/usr/bin/env python3
"""
Comprehensive Health Check System for MCP Unified Services
Monitors all services, databases, AI backends, and system resources
"""

import asyncio
import json
import logging
import time
import psutil
import httpx
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import aiosqlite
import redis
from pathlib import Path

logger = logging.getLogger(__name__)

class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"

@dataclass
class HealthCheck:
    """Individual health check result"""
    name: str
    status: HealthStatus
    message: str
    timestamp: float
    response_time_ms: Optional[int] = None
    details: Optional[Dict] = None

@dataclass
class SystemResources:
    """System resource metrics"""
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    load_average: List[float]
    available_memory_gb: float
    available_disk_gb: float

class HealthMonitor:
    """Comprehensive health monitoring system"""

    def __init__(self):
        self.checks: Dict[str, HealthCheck] = {}
        self.client = httpx.AsyncClient(timeout=10.0)
        self.redis_client = None
        self.last_full_check = 0
        self.check_interval = 30  # seconds

        # Service endpoints
        self.service_endpoints = {
            "mcp-server": "http://localhost:7071/health",
            "mcp-server-template": "http://localhost:7072/health",
            "frontend": "http://localhost:3000/health",
            "ollama": "http://localhost:11434/api/tags",
            "one-api": "http://localhost:3000/api/status",
            "anything-llm": "http://localhost:3001/api/system/check",
            "prometheus": "http://localhost:9090/-/healthy",
            "grafana": "http://localhost:3001/api/health"
        }

        # Initialize Redis connection
        try:
            self.redis_client = redis.from_url("redis://localhost:6379", socket_timeout=5)
            self.redis_client.ping()
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            self.redis_client = None

    async def check_service_health(self, service_name: str, endpoint: str) -> HealthCheck:
        """Check health of a specific service"""
        start_time = time.time()

        try:
            response = await self.client.get(endpoint)
            response_time = int((time.time() - start_time) * 1000)

            if response.status_code == 200:
                return HealthCheck(
                    name=service_name,
                    status=HealthStatus.HEALTHY,
                    message="Service responding normally",
                    timestamp=time.time(),
                    response_time_ms=response_time,
                    details={"status_code": response.status_code}
                )
            else:
                return HealthCheck(
                    name=service_name,
                    status=HealthStatus.WARNING,
                    message=f"Service responding with status {response.status_code}",
                    timestamp=time.time(),
                    response_time_ms=response_time,
                    details={"status_code": response.status_code}
                )

        except asyncio.TimeoutError:
            return HealthCheck(
                name=service_name,
                status=HealthStatus.CRITICAL,
                message="Service timeout",
                timestamp=time.time(),
                details={"error": "timeout"}
            )
        except Exception as e:
            return HealthCheck(
                name=service_name,
                status=HealthStatus.CRITICAL,
                message=f"Service unreachable: {str(e)}",
                timestamp=time.time(),
                details={"error": str(e)}
            )

    async def check_database_health(self) -> HealthCheck:
        """Check SQLite database health"""
        start_time = time.time()
        db_path = Path(__file__).parent / "sequential_think_prompts.db"

        try:
            if not db_path.exists():
                return HealthCheck(
                    name="database",
                    status=HealthStatus.CRITICAL,
                    message="Database file not found",
                    timestamp=time.time(),
                    details={"path": str(db_path)}
                )

            async with aiosqlite.connect(str(db_path)) as conn:
                # Test basic query
                cursor = await conn.execute("SELECT COUNT(*) FROM prompts")
                result = await cursor.fetchone()
                prompt_count = result[0] if result else 0

                # Check database size
                db_size_mb = db_path.stat().st_size / (1024 * 1024)

                response_time = int((time.time() - start_time) * 1000)

                return HealthCheck(
                    name="database",
                    status=HealthStatus.HEALTHY,
                    message=f"Database operational with {prompt_count} prompts",
                    timestamp=time.time(),
                    response_time_ms=response_time,
                    details={
                        "prompt_count": prompt_count,
                        "size_mb": round(db_size_mb, 2),
                        "path": str(db_path)
                    }
                )

        except Exception as e:
            return HealthCheck(
                name="database",
                status=HealthStatus.CRITICAL,
                message=f"Database error: {str(e)}",
                timestamp=time.time(),
                details={"error": str(e)}
            )

    async def check_redis_health(self) -> HealthCheck:
        """Check Redis cache health"""
        start_time = time.time()

        if not self.redis_client:
            return HealthCheck(
                name="redis",
                status=HealthStatus.WARNING,
                message="Redis not configured",
                timestamp=time.time(),
                details={"status": "disabled"}
            )

        try:
            # Test ping
            self.redis_client.ping()

            # Get info
            info = self.redis_client.info()
            response_time = int((time.time() - start_time) * 1000)

            # Check memory usage
            used_memory_mb = info.get('used_memory', 0) / (1024 * 1024)
            max_memory_mb = info.get('maxmemory', 0) / (1024 * 1024)

            status = HealthStatus.HEALTHY
            message = "Redis operational"

            # Check if memory usage is high
            if max_memory_mb > 0 and (used_memory_mb / max_memory_mb) > 0.8:
                status = HealthStatus.WARNING
                message = "Redis memory usage high"

            return HealthCheck(
                name="redis",
                status=status,
                message=message,
                timestamp=time.time(),
                response_time_ms=response_time,
                details={
                    "used_memory_mb": round(used_memory_mb, 2),
                    "max_memory_mb": round(max_memory_mb, 2),
                    "connected_clients": info.get('connected_clients', 0),
                    "total_commands": info.get('total_commands_processed', 0)
                }
            )

        except Exception as e:
            return HealthCheck(
                name="redis",
                status=HealthStatus.CRITICAL,
                message=f"Redis error: {str(e)}",
                timestamp=time.time(),
                details={"error": str(e)}
            )

    def check_system_resources(self) -> HealthCheck:
        """Check system resource health"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)

            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            available_memory_gb = memory.available / (1024**3)

            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            available_disk_gb = disk.free / (1024**3)

            # Load average
            load_avg = list(psutil.getloadavg())

            # Determine status
            status = HealthStatus.HEALTHY
            issues = []

            if cpu_percent > 80:
                status = HealthStatus.WARNING
                issues.append(f"High CPU usage: {cpu_percent}%")

            if memory_percent > 85:
                status = HealthStatus.WARNING
                issues.append(f"High memory usage: {memory_percent}%")

            if disk_percent > 90:
                status = HealthStatus.CRITICAL
                issues.append(f"Low disk space: {disk_percent}% used")

            if available_memory_gb < 1:
                status = HealthStatus.CRITICAL
                issues.append(f"Low available memory: {available_memory_gb:.1f}GB")

            message = "System resources normal" if not issues else "; ".join(issues)

            return HealthCheck(
                name="system_resources",
                status=status,
                message=message,
                timestamp=time.time(),
                details={
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory_percent,
                    "disk_percent": disk_percent,
                    "available_memory_gb": round(available_memory_gb, 2),
                    "available_disk_gb": round(available_disk_gb, 2),
                    "load_average": load_avg
                }
            )

        except Exception as e:
            return HealthCheck(
                name="system_resources",
                status=HealthStatus.CRITICAL,
                message=f"System check error: {str(e)}",
                timestamp=time.time(),
                details={"error": str(e)}
            )

    async def check_ai_backends(self) -> List[HealthCheck]:
        """Check AI backend health"""
        checks = []

        # Check Ollama
        ollama_check = await self.check_service_health("ollama", "http://localhost:11434/api/tags")
        if ollama_check.status == HealthStatus.HEALTHY:
            try:
                # Get model list
                response = await self.client.get("http://localhost:11434/api/tags")
                models = response.json().get('models', [])
                ollama_check.details['models'] = [m.get('name', 'unknown') for m in models]
                ollama_check.details['model_count'] = len(models)
            except:
                pass
        checks.append(ollama_check)

        # Check external APIs (without making actual calls)
        import os

        # OpenAI
        if os.getenv('OPENAI_API_KEY'):
            checks.append(HealthCheck(
                name="openai_api",
                status=HealthStatus.HEALTHY,
                message="API key configured",
                timestamp=time.time(),
                details={"configured": True}
            ))
        else:
            checks.append(HealthCheck(
                name="openai_api",
                status=HealthStatus.WARNING,
                message="API key not configured",
                timestamp=time.time(),
                details={"configured": False}
            ))

        # DeepSeek
        if os.getenv('DEEPSEEK_API_KEY'):
            checks.append(HealthCheck(
                name="deepseek_api",
                status=HealthStatus.HEALTHY,
                message="API key configured",
                timestamp=time.time(),
                details={"configured": True}
            ))
        else:
            checks.append(HealthCheck(
                name="deepseek_api",
                status=HealthStatus.WARNING,
                message="API key not configured",
                timestamp=time.time(),
                details={"configured": False}
            ))

        return checks

    async def run_full_health_check(self) -> Dict[str, Any]:
        """Run comprehensive health check on all systems"""
        start_time = time.time()
        checks = {}

        logger.info("🏥 Running comprehensive health check...")

        # System resources (synchronous)
        checks['system_resources'] = self.check_system_resources()

        # Database check
        checks['database'] = await self.check_database_health()

        # Redis check
        checks['redis'] = await self.check_redis_health()

        # Service checks (parallel)
        service_tasks = [
            self.check_service_health(service, endpoint)
            for service, endpoint in self.service_endpoints.items()
        ]
        service_results = await asyncio.gather(*service_tasks, return_exceptions=True)

        for i, result in enumerate(service_results):
            service_name = list(self.service_endpoints.keys())[i]
            if isinstance(result, Exception):
                checks[service_name] = HealthCheck(
                    name=service_name,
                    status=HealthStatus.CRITICAL,
                    message=f"Health check failed: {str(result)}",
                    timestamp=time.time(),
                    details={"error": str(result)}
                )
            else:
                checks[service_name] = result

        # AI backend checks
        ai_checks = await self.check_ai_backends()
        for check in ai_checks:
            checks[check.name] = check

        # Calculate overall status
        statuses = [check.status for check in checks.values()]

        if HealthStatus.CRITICAL in statuses:
            overall_status = HealthStatus.CRITICAL
        elif HealthStatus.WARNING in statuses:
            overall_status = HealthStatus.WARNING
        else:
            overall_status = HealthStatus.HEALTHY

        # Count by status
        status_counts = {
            "healthy": len([s for s in statuses if s == HealthStatus.HEALTHY]),
            "warning": len([s for s in statuses if s == HealthStatus.WARNING]),
            "critical": len([s for s in statuses if s == HealthStatus.CRITICAL]),
            "unknown": len([s for s in statuses if s == HealthStatus.UNKNOWN])
        }

        total_time = round((time.time() - start_time) * 1000)

        result = {
            "overall_status": overall_status.value,
            "timestamp": datetime.now().isoformat(),
            "check_duration_ms": total_time,
            "status_counts": status_counts,
            "checks": {name: asdict(check) for name, check in checks.items()},
            "summary": {
                "total_checks": len(checks),
                "healthy_services": status_counts["healthy"],
                "services_with_issues": status_counts["warning"] + status_counts["critical"]
            }
        }

        # Update internal state
        self.checks = checks
        self.last_full_check = time.time()

        logger.info(f"✅ Health check completed in {total_time}ms - Status: {overall_status.value}")

        return result

    async def get_quick_status(self) -> Dict[str, Any]:
        """Get quick status overview"""
        if time.time() - self.last_full_check > self.check_interval:
            return await self.run_full_health_check()

        # Return cached results with age
        age_seconds = int(time.time() - self.last_full_check)

        return {
            "status": "cached",
            "age_seconds": age_seconds,
            "last_check": datetime.fromtimestamp(self.last_full_check).isoformat(),
            "checks_count": len(self.checks),
            "suggestion": "Run full health check for latest status"
        }

    async def get_service_status(self, service_name: str) -> Optional[Dict]:
        """Get status of a specific service"""
        if service_name in self.checks:
            return asdict(self.checks[service_name])

        # Run specific check
        if service_name in self.service_endpoints:
            check = await self.check_service_health(service_name, self.service_endpoints[service_name])
            self.checks[service_name] = check
            return asdict(check)

        return None

    async def close(self):
        """Clean up resources"""
        await self.client.aclose()
        if self.redis_client:
            self.redis_client.close()

# Global health monitor instance
health_monitor = HealthMonitor()
