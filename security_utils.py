#!/usr/bin/env python3
"""
Security utilities and input validation for Sequential Think MCP Server
"""

import re
import html
import json
import logging
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

logger = logging.getLogger(__name__)


class SecurityError(Exception):
    """Base exception for security-related errors"""
    pass


class InputValidationError(SecurityError):
    """Raised when input validation fails"""
    pass


class CommandInjectionError(SecurityError):
    """Raised when potential command injection is detected"""
    pass


class InputValidator:
    """Comprehensive input validation and sanitization"""

    # Dangerous patterns for command injection
    DANGEROUS_PATTERNS = [
        r'[;&|`$]',           # Shell metacharacters
        r'\$\(',              # Command substitution
        r'`[^`]*`',           # Backticks
        r'\|\s*\w+',          # Pipes to commands
        r'>\s*/\w+',          # Redirects to system paths
        r'<\s*/\w+',          # Input redirects from system paths
        r'\b(rm|del|format|shutdown|reboot|kill|sudo|su)\b',  # Dangerous commands
    ]

    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r"('\s*(or|and)\s*')",
        r"('\s*;\s*drop\s+table)",
        r"('\s*;\s*delete\s+from)",
        r"('\s*;\s*insert\s+into)",
        r"('\s*;\s*update\s+)",
        r"('\s*union\s+select)",
    ]

    @staticmethod
    def sanitize_shell_input(input_str: str, max_length: int = 1000) -> str:
        """
        Sanitize input to prevent command injection

        Args:
            input_str: Input string to sanitize
            max_length: Maximum allowed length

        Returns:
            Sanitized string safe for shell operations

        Raises:
            CommandInjectionError: If dangerous patterns detected
            InputValidationError: If input is invalid
        """
        if not isinstance(input_str, str):
            raise InputValidationError(
                f"Expected string, got {type(input_str)}")

        if len(input_str) > max_length:
            raise InputValidationError(
                f"Input too long: {len(input_str)} > {max_length}")

        # Check for dangerous patterns
        for pattern in InputValidator.DANGEROUS_PATTERNS:
            if re.search(pattern, input_str, re.IGNORECASE):
                logger.warning(f"Dangerous pattern detected: {pattern}")
                raise CommandInjectionError(
                    f"Input contains potentially dangerous pattern: {pattern}")

        # Remove null bytes and control characters
        sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', input_str)

        # HTML escape to prevent any HTML/JS injection if output goes to web
        sanitized = html.escape(sanitized)

        return sanitized.strip()

    @staticmethod
    def validate_prompt(prompt: str, max_length: int = 10000) -> str:
        """
        Validate and sanitize prompt input

        Args:
            prompt: User prompt to validate
            max_length: Maximum allowed prompt length

        Returns:
            Validated and sanitized prompt
        """
        if not prompt or not prompt.strip():
            raise InputValidationError("Prompt cannot be empty")

        if len(prompt) > max_length:
            raise InputValidationError(
                f"Prompt too long: {len(prompt)} > {max_length}")

        # Check for SQL injection patterns
        for pattern in InputValidator.SQL_INJECTION_PATTERNS:
            if re.search(pattern, prompt, re.IGNORECASE):
                raise InputValidationError(
                    f"Prompt contains potentially dangerous SQL pattern")

        # Remove excessive whitespace and control characters
        sanitized = re.sub(r'\s+', ' ', prompt.strip())
        sanitized = re.sub(
            r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', sanitized)

        return sanitized

    @staticmethod
    def validate_complexity_level(level: str) -> str:
        """Validate complexity level input"""
        if not isinstance(level, str):
            raise InputValidationError(
                f"Complexity level must be string, got {type(level)}")

        level = level.upper().strip()
        valid_levels = ['L1', 'L2', 'L3', 'L4', 'L5']

        if level not in valid_levels:
            raise InputValidationError(
                f"Invalid complexity level: {level}. Must be one of {valid_levels}")

        return level

    @staticmethod
    def validate_domain(domain: str, max_length: int = 100) -> str:
        """Validate domain input"""
        if not isinstance(domain, str):
            raise InputValidationError(
                f"Domain must be string, got {type(domain)}")

        if len(domain) > max_length:
            raise InputValidationError(
                f"Domain too long: {len(domain)} > {max_length}")

        # Allow alphanumeric, dots, underscores, hyphens
        if not re.match(r'^[a-zA-Z0-9._-]+$', domain):
            raise InputValidationError(f"Invalid domain format: {domain}")

        return domain.lower().strip()

    @staticmethod
    def validate_score(score: Union[float, int], min_val: float = 0.0, max_val: float = 1.0) -> float:
        """Validate effectiveness/quality scores"""
        try:
            score = float(score)
        except (ValueError, TypeError):
            raise InputValidationError(
                f"Score must be numeric, got {type(score)}")

        if not (min_val <= score <= max_val):
            raise InputValidationError(
                f"Score {score} not in range [{min_val}, {max_val}]")

        return score

    @staticmethod
    def validate_limit(limit: Union[int, str], max_limit: int = 100) -> int:
        """Validate result limit parameters"""
        try:
            limit = int(limit)
        except (ValueError, TypeError):
            raise InputValidationError(
                f"Limit must be integer, got {type(limit)}")

        if limit < 1:
            raise InputValidationError(f"Limit must be positive, got {limit}")

        if limit > max_limit:
            raise InputValidationError(
                f"Limit too high: {limit} > {max_limit}")

        return limit


class PathSecurity:
    """Path traversal and file security utilities"""

    @staticmethod
    def validate_safe_path(path: Union[str, Path], base_path: Path) -> Path:
        """
        Validate that a path is within the allowed base directory

        Args:
            path: Path to validate
            base_path: Base directory that path must be within

        Returns:
            Resolved safe path

        Raises:
            SecurityError: If path traversal detected
        """
        try:
            path = Path(path).resolve()
            base_path = base_path.resolve()

            # Check if path is within base_path
            try:
                path.relative_to(base_path)
            except ValueError:
                raise SecurityError(
                    f"Path traversal detected: {path} not within {base_path}")

            return path

        except Exception as e:
            raise SecurityError(f"Invalid path: {e}")

    @staticmethod
    def is_safe_filename(filename: str) -> bool:
        """Check if filename is safe (no path traversal, dangerous chars)"""
        if not filename or filename in ('.', '..'):
            return False

        # Check for path traversal
        if '/' in filename or '\\' in filename:
            return False

        # Check for dangerous characters
        dangerous_chars = ['<', '>', ':', '"', '|', '?', '*', '\x00']
        if any(char in filename for char in dangerous_chars):
            return False

        return True


def secure_json_loads(json_str: str, max_size: int = 1024 * 1024) -> Any:
    """
    Safely load JSON with size limits

    Args:
        json_str: JSON string to parse
        max_size: Maximum allowed JSON size in bytes

    Returns:
        Parsed JSON object

    Raises:
        InputValidationError: If JSON is invalid or too large
    """
    if len(json_str.encode('utf-8')) > max_size:
        raise InputValidationError(
            f"JSON too large: {len(json_str)} bytes > {max_size}")

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise InputValidationError(f"Invalid JSON: {e}")


def create_security_headers() -> Dict[str, str]:
    """Create security headers for HTTP responses"""
    return {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Content-Security-Policy': "default-src 'self'",
        'Referrer-Policy': 'strict-origin-when-cross-origin'
    }
