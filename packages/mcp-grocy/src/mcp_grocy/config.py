"""
Configuration management for Grocy MCP server.
"""

import os
from dataclasses import dataclass

from brewing_common.exceptions import ConfigurationError


@dataclass
class GrocyConfig:
    """Configuration for Grocy integration."""

    url: str
    api_key: str

    def __post_init__(self):
        # Ensure URL doesn't have trailing slash
        self.url = self.url.rstrip("/")


def get_config() -> GrocyConfig:
    """
    Get Grocy configuration from environment.

    Environment variables:
        GROCY_URL: Grocy server URL
        GROCY_API_KEY: Grocy API key

    Returns:
        GrocyConfig instance

    Raises:
        ConfigurationError: If required configuration is missing
    """
    url = os.environ.get("GROCY_URL")
    api_key = os.environ.get("GROCY_API_KEY")

    if not url:
        raise ConfigurationError(
            "GROCY_URL environment variable not set. "
            "Set it to your Grocy server URL (e.g., http://localhost:9283)"
        )

    if not api_key:
        raise ConfigurationError(
            "GROCY_API_KEY environment variable not set. "
            "Get your API key from Grocy: Settings → Manage API keys"
        )

    return GrocyConfig(url=url, api_key=api_key)
