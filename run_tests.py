#!/usr/bin/env python3
"""
Test runner for Sequential Think MCP Server
Comprehensive testing with performance benchmarks
"""

import asyncio
import time
import json
from pathlib import Path
import sys
import logging

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from sequential_think_mcp_server import (
    db_manager, ai_manager, ollama_client, sequential_think,
    enhance_prompt, search_prompts, classify_prompt, 
    get_prompt_recommendations, get_database_stats
)
from core_utils import cache, cleanup_resources

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PerformanceTester:
    """Performance testing and benchmarking utilities"""
    
    def __init__(self):
        self.results = []
    
    async def time_operation(self, name: str, operation, *args, **kwargs):
        """Time an async operation and record results"""
        start_time = time.time()
        try:
            result = await operation(*args, **kwargs)
            duration = time.time() - start_time
            status = "SUCCESS"
            error = None
        except Exception as e:
            duration = time.time() - start_time
            status = "ERROR"
            error = str(e)
            result = None
        
        self.results.append({
            'operation': name,
            'duration': duration,
            'status': status,
            'error': error
        })
        
        logger.info(f"{name}: {duration:.3f}s [{status}]")
        return result
    
    def get_summary(self):
        """Get performance summary"""
        total_tests = len(self.results)
        successful = sum(1 for r in self.results if r['status'] == 'SUCCESS')
        failed = total_tests - successful
        avg_duration = sum(r['duration'] for r in self.results) / max(1, total_tests)
        
        return {
            'total_tests': total_tests,
            'successful': successful,
            'failed': failed,
            'success_rate': successful / max(1, total_tests),
            'average_duration': avg_duration,
            'results': self.results
        }

async def test_database_operations():
    """Test database initialization and operations"""
    logger.info("🗄️  Testing Database Operations")
    
    tester = PerformanceTester()
    
    # Test database initialization
    await tester.time_operation("Database Initialization", db_manager.init_database)
    
    # Test search operations
    test_queries = [
        ("python", None, None),
        ("react debugging", "development", "L3"),
        ("system design", None, "L4"),
        ("", None, None),  # Should handle empty query gracefully
    ]
    
    for query, category, complexity in test_queries:
        await tester.time_operation(
            f"Search Query: '{query}'",
            db_manager.search_prompts,
            query, category, complexity, 0.0, 5
        )
    
    # Test prompt storage
    test_analysis = {
        'id': 'test_prompt_001',
        'original_prompt': 'Test prompt for storage',
        'optimized_prompt': 'Enhanced: Test prompt for storage with improvements',
        'complexity': 'L2',
        'context': 'C2',
        'domain': 'testing',
        'effectiveness': 0.8,
        'quality_score': 0.7,
        'improvements': ['Added clarity', 'Improved structure'],
        'timestamp': '2025-01-01T00:00:00'
    }
    
    await tester.time_operation("Store Prompt Analysis", db_manager.store_prompt_analysis, test_analysis)
    
    return tester.get_summary()

async def test_ai_services():
    """Test AI service integrations"""
    logger.info("🤖 Testing AI Services")
    
    tester = PerformanceTester()
    
    # Test prompt enhancement
    test_prompts = [
        ("Help me debug this React component", "development"),
        ("Write a function to sort an array", "coding"),
        ("Explain quantum computing", "science"),
    ]
    
    for prompt, domain in test_prompts:
        await tester.time_operation(
            f"AI Enhancement: '{prompt[:30]}...'",
            ai_manager.enhance_prompt_with_ai,
            prompt, domain
        )
    
    return tester.get_summary()

async def test_ollama_integration():
    """Test Ollama local LLM integration"""
    logger.info("🦙 Testing Ollama Integration")
    
    tester = PerformanceTester()
    
    # Test Ollama availability
    await tester.time_operation("Ollama Availability Check", ollama_client.is_available)
    
    # Test model listing
    await tester.time_operation("List Ollama Models", ollama_client.list_models)
    
    # Test generation if available
    if await ollama_client.is_available():
        models = await ollama_client.list_models()
        if models:
            await tester.time_operation(
                "Ollama Generation Test",
                ollama_client.generate,
                models[0],
                "Explain the concept of recursion in programming",
                "You are a helpful programming tutor"
            )
    
    return tester.get_summary()

async def test_mcp_tools():
    """Test MCP tool implementations"""
    logger.info("🔧 Testing MCP Tools")
    
    tester = PerformanceTester()
    
    # Test enhance_prompt tool
    await tester.time_operation(
        "MCP Tool: enhance_prompt",
        enhance_prompt,
        "Help me optimize database queries",
        "development",
        "L3"
    )
    
    # Test search_prompts tool
    await tester.time_operation(
        "MCP Tool: search_prompts", 
        search_prompts,
        "database optimization",
        None,
        "L3",
        0.0,
        5
    )
    
    # Test classify_prompt tool
    await tester.time_operation(
        "MCP Tool: classify_prompt",
        classify_prompt,
        "Design a microservices architecture for an e-commerce platform"
    )
    
    # Test get_prompt_recommendations tool
    await tester.time_operation(
        "MCP Tool: get_prompt_recommendations",
        get_prompt_recommendations,
        "development",
        "L4",
        3
    )
    
    # Test get_database_stats tool
    await tester.time_operation(
        "MCP Tool: get_database_stats",
        get_database_stats
    )
    
    return tester.get_summary()

async def test_cache_performance():
    """Test caching system performance"""
    logger.info("⚡ Testing Cache Performance")
    
    tester = PerformanceTester()
    
    # Test cache operations
    test_data = {
        'key1': 'Simple string value',
        'key2': {'complex': 'dictionary', 'with': ['nested', 'data']},
        'key3': list(range(1000))  # Larger data structure
    }
    
    # Test cache set operations
    for key, value in test_data.items():
        cache.set(key, value)
        await tester.time_operation(f"Cache Set: {key}", asyncio.sleep, 0)  # Immediate
    
    # Test cache get operations (should be very fast)
    for key in test_data.keys():
        result = cache.get(key)
        await tester.time_operation(f"Cache Get: {key}", asyncio.sleep, 0)  # Immediate
        if result is None:
            logger.warning(f"Cache miss for key: {key}")
    
    # Test cache cleanup
    expired_count = cache.cleanup_expired()
    await tester.time_operation("Cache Cleanup", asyncio.sleep, 0)  # Immediate
    logger.info(f"Cleaned up {expired_count} expired cache entries")
    
    return tester.get_summary()

async def test_error_handling():
    """Test error handling and resilience"""
    logger.info("🛡️  Testing Error Handling")
    
    tester = PerformanceTester()
    
    # Test various error conditions
    error_tests = [
        ("Empty Prompt Enhancement", enhance_prompt, "", "test"),
        ("Invalid Complexity Search", search_prompts, "test", None, "INVALID", 0.0, 5),
        ("Negative Limit Search", search_prompts, "test", None, None, 0.0, -1),
        ("Very Long Prompt", enhance_prompt, "x" * 50000, "test"),  # Extremely long prompt
    ]
    
    for test_name, func, *args in error_tests:
        await tester.time_operation(test_name, func, *args)
    
    return tester.get_summary()

async def run_comprehensive_tests():
    """Run all tests and generate comprehensive report"""
    logger.info("🚀 Starting Comprehensive Test Suite")
    
    test_suites = [
        ("Database Operations", test_database_operations),
        ("AI Services", test_ai_services), 
        ("Ollama Integration", test_ollama_integration),
        ("MCP Tools", test_mcp_tools),
        ("Cache Performance", test_cache_performance),
        ("Error Handling", test_error_handling),
    ]
    
    overall_start = time.time()
    suite_results = {}
    
    for suite_name, test_func in test_suites:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running {suite_name} Tests")
        logger.info(f"{'='*50}")
        
        try:
            suite_results[suite_name] = await test_func()
        except Exception as e:
            logger.error(f"Test suite {suite_name} failed: {e}")
            suite_results[suite_name] = {
                'total_tests': 0,
                'successful': 0,
                'failed': 1,
                'success_rate': 0.0,
                'average_duration': 0.0,
                'error': str(e)
            }
    
    overall_duration = time.time() - overall_start
    
    # Generate comprehensive report
    total_tests = sum(result['total_tests'] for result in suite_results.values())
    total_successful = sum(result['successful'] for result in suite_results.values())
    total_failed = sum(result['failed'] for result in suite_results.values())
    overall_success_rate = total_successful / max(1, total_tests)
    
    report = {
        'test_run_summary': {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_duration': overall_duration,
            'total_tests': total_tests,
            'successful': total_successful,
            'failed': total_failed,
            'success_rate': overall_success_rate
        },
        'suite_results': suite_results
    }
    
    # Save report
    report_path = Path('test_results.json')
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    # Print summary
    logger.info(f"\n{'='*60}")
    logger.info("📊 COMPREHENSIVE TEST SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Total Duration: {overall_duration:.2f}s")
    logger.info(f"Total Tests: {total_tests}")
    logger.info(f"Successful: {total_successful}")
    logger.info(f"Failed: {total_failed}")
    logger.info(f"Success Rate: {overall_success_rate:.1%}")
    logger.info(f"Report saved to: {report_path}")
    
    # Performance insights
    logger.info(f"\n🔍 PERFORMANCE INSIGHTS")
    for suite_name, result in suite_results.items():
        if 'average_duration' in result:
            logger.info(f"{suite_name}: Avg {result['average_duration']:.3f}s per operation")
    
    logger.info(f"\n🎉 Test suite completed!")
    
    return report

if __name__ == "__main__":
    async def main():
        try:
            report = await run_comprehensive_tests()
            return 0 if report['test_run_summary']['success_rate'] > 0.8 else 1
        except Exception as e:
            logger.error(f"Test suite failed: {e}")
            return 1
        finally:
            await cleanup_resources()
    
    exit_code = asyncio.run(main())
    sys.exit(exit_code)