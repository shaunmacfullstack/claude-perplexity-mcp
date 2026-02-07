"""
Configuration management for Perplexity MCP Server.

Handles environment variable loading, API key validation, and secure logging.
All API keys are sanitized before logging to prevent exposure.
"""

import os
import logging
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Configure logger
logger = logging.getLogger(__name__)


class Config:
    """Secure configuration manager for Perplexity MCP Server."""

    def __init__(self) -> None:
        """
        Load and validate configuration from environment variables.

        Raises:
            ValueError: If required configuration is missing or invalid.
        """
        # Load environment variables from .env file
        env_path = Path(__file__).parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            logger.info("Loaded environment variables from .env file")
        else:
            load_dotenv()  # Try loading from environment
            logger.warning(
                ".env file not found. Using system environment variables."
            )

        # Load and validate API key
        self.api_key = self._load_api_key()

        # Load optional configuration with defaults
        self.default_model = os.getenv("DEFAULT_MODEL", "sonar-pro")
        self.cache_enabled = (
            os.getenv("CACHE_ENABLED", "false").lower() == "true"
        )
        self.log_level = os.getenv("LOG_LEVEL", "INFO").upper()

        # Log configuration (with sanitized API key)
        logger.info(
            f"Configuration loaded: model={self.default_model}, "
            f"cache_enabled={self.cache_enabled}, log_level={self.log_level}"
        )
        logger.info(f"API key loaded: {self._sanitize_for_logs(self.api_key)}")

    def _load_api_key(self) -> str:
        """
        Load and validate Perplexity API key from environment.

        Returns:
            str: The API key if valid.

        Raises:
            ValueError: If API key is missing or invalid format.
        """
        api_key = os.getenv("PERPLEXITY_API_KEY")

        if not api_key:
            raise ValueError(
                "PERPLEXITY_API_KEY not found in environment. "
                "Copy .env.example to .env and add your API key."
            )

        # Validate API key format
        self._validate_api_key(api_key)

        return api_key

    def _validate_api_key(self, key: str) -> None:
        """
        Validate API key format without exposing the full key.

        Args:
            key: The API key to validate.

        Raises:
            ValueError: If API key format is invalid.
        """
        if not isinstance(key, str):
            raise ValueError(
                "PERPLEXITY_API_KEY must be a string. "
                "Check your .env file configuration."
            )

        if not key.startswith("pplx-"):
            raise ValueError(
                "PERPLEXITY_API_KEY must start with 'pplx-'. "
                f"Got key starting with: {key[:4] if len(key) >= 4 else 'invalid'}"
            )

        if len(key) < 20:  # Minimum reasonable length for API key
            raise ValueError(
                "PERPLEXITY_API_KEY appears to be too short. "
                "Please verify your API key is correct."
            )

    def _sanitize_for_logs(self, key: str) -> str:
        """
        Return sanitized version of API key for safe logging.

        Format: first 4 chars + "..." + last 4 chars

        Args:
            key: The API key to sanitize.

        Returns:
            str: Sanitized key safe for logging.
        """
        if not key or len(key) < 8:
            return "****"
        return f"{key[:4]}...{key[-4:]}"

    def get_api_key(self) -> str:
        """
        Get the Perplexity API key.

        Returns:
            str: The API key.
        """
        return self.api_key


# Global config instance (lazy initialization)
_config: Optional[Config] = None


def get_config() -> Config:
    """
    Get the global configuration instance.

    Returns:
        Config: The configuration instance.
    """
    global _config
    if _config is None:
        _config = Config()
    return _config
