#!/usr/bin/env python3
"""
Configuration loader with validation and environment variable support
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)

@dataclass
class ConfigManager:
    """Centralized configuration management with validation"""
    
    config_path: Path = field(default_factory=lambda: Path("config.yaml"))
    _config: Optional[Dict[str, Any]] = field(default=None, init=False)
    
    def __post_init__(self):
        self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file with environment variable substitution"""
        if not self.config_path.exists():
            logger.warning(f"Config file {self.config_path} not found, using defaults")
            self._config = self._get_default_config()
            return self._config
        
        try:
            with open(self.config_path, 'r') as f:
                raw_config = yaml.safe_load(f)
            
            # Substitute environment variables
            self._config = self._substitute_env_vars(raw_config)
            
            # Validate configuration
            self._validate_config(self._config)
            
            logger.info(f"Configuration loaded from {self.config_path}")
            return self._config
            
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            logger.info("Using default configuration")
            self._config = self._get_default_config()
            return self._config
    
    def _substitute_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively substitute environment variables in config"""
        if isinstance(config, dict):
            return {k: self._substitute_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._substitute_env_vars(item) for item in config]
        elif isinstance(config, str) and config.startswith('${') and config.endswith('}'):
            # Environment variable substitution
            env_var = config[2:-1]
            default_value = None
            
            if ':' in env_var:
                env_var, default_value = env_var.split(':', 1)
            
            return os.getenv(env_var, default_value)
        else:
            return config
    
    def _validate_config(self, config: Dict[str, Any]) -> None:
        """Validate configuration structure and values"""
        required_sections = ['database', 'ai_services', 'performance', 'server']
        
        for section in required_sections:
            if section not in config:
                raise ValueError(f"Missing required config section: {section}")
        
        # Validate database config
        db_config = config['database']
        if not isinstance(db_config.get('pool_size', 10), int) or db_config.get('pool_size', 10) < 1:
            raise ValueError("database.pool_size must be a positive integer")
        
        # Validate performance config
        perf_config = config['performance']
        if not isinstance(perf_config.get('cache_ttl', 300), int) or perf_config.get('cache_ttl', 300) < 0:
            raise ValueError("performance.cache_ttl must be a non-negative integer")
        
        logger.debug("Configuration validation passed")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            'database': {
                'path': 'sequential_think_prompts.db',
                'pool_size': 10,
                'timeout': 30.0,
                'enable_wal': True,
                'cache_size': 10000
            },
            'ai_services': {
                'openai': {
                    'enabled': True,
                    'api_key_env': 'OPENAI_API_KEY',
                    'base_url': 'https://api.openai.com/v1',
                    'default_model': 'gpt-3.5-turbo',
                    'timeout': 30.0,
                    'max_retries': 3
                },
                'deepseek': {
                    'enabled': True,
                    'api_key_env': 'DEEPSEEK_API_KEY',
                    'base_url': 'https://api.deepseek.com/v1',
                    'default_model': 'deepseek-coder',
                    'timeout': 30.0,
                    'max_retries': 3
                }
            },
            'ollama': {
                'enabled': True,
                'base_url': 'http://localhost:11434',
                'timeout': 120.0,
                'preferred_models': ['llama3.2:1b', 'llama3.2:3b']
            },
            'performance': {
                'cache_enabled': True,
                'cache_ttl': 300,
                'cache_max_size': 1000,
                'max_results_per_query': 100,
                'default_limit': 10
            },
            'server': {
                'default_transport': 'stdio',
                'sse_host': '0.0.0.0',
                'sse_port': 7071
            },
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            },
            'features': {
                'sequential_think_cli': {
                    'enabled': True,
                    'path': 'sequential-think/ai/cli.ts',
                    'timeout': 60.0,
                    'max_thoughts': 20
                },
                'prompt_enhancement': {
                    'enabled': True,
                    'auto_store_results': True,
                    'enable_keyword_extraction': True,
                    'quality_threshold': 0.7
                }
            }
        }
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """Get configuration value using dot notation (e.g., 'database.pool_size')"""
        if self._config is None:
            self.load_config()
        
        keys = key_path.split('.')
        value = self._config
        
        try:
            for key in keys:
                value = value[key] # type: ignore
            return value
        except (KeyError, TypeError):
            return default
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """Get entire configuration section"""
        return self.get(section, {})
    
    def reload(self) -> None:
        """Reload configuration from file"""
        self.load_config()
        logger.info("Configuration reloaded")
    
    def is_feature_enabled(self, feature_path: str) -> bool:
        """Check if a feature is enabled"""
        return self.get(f'features.{feature_path}.enabled', False)
    
    def get_api_key(self, service: str) -> Optional[str]:
        """Get API key for a service from environment"""
        env_var = self.get(f'ai_services.{service}.api_key_env')
        if env_var:
            return os.getenv(env_var)
        return None

# Global configuration instance
config_manager = ConfigManager()

# Convenience functions
def get_config(key_path: str, default: Any = None) -> Any:
    """Get configuration value using dot notation"""
    return config_manager.get(key_path, default)

def get_section(section: str) -> Dict[str, Any]:
    """Get configuration section"""
    return config_manager.get_section(section)

def is_feature_enabled(feature_path: str) -> bool:
    """Check if feature is enabled"""
    return config_manager.is_feature_enabled(feature_path)

def get_api_key(service: str) -> Optional[str]:
    """Get API key for service"""
    return config_manager.get_api_key(service)