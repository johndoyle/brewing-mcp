"""
Configuration management for Brewfather MCP server.
"""

import os
from dataclasses import dataclass

from brewing_common.exceptions import ConfigurationError


@dataclass
class BrewfatherConfig:
    """Configuration for Brewfather integration."""

    user_id: str
    api_key: str

    @property
    def base_url(self) -> str:
        """Get the Brewfather API base URL."""
        return "https://api.brewfather.app/v2"


def get_config() -> BrewfatherConfig:
    """
    Get Brewfather configuration from environment.

    Environment variables:
        BREWFATHER_USER_ID: Brewfather user ID
        BREWFATHER_API_KEY: Brewfather API key

    Returns:
        BrewfatherConfig instance

    Raises:
        ConfigurationError: If required configuration is missing
    """
    user_id = os.environ.get("BREWFATHER_USER_ID")
    api_key = os.environ.get("BREWFATHER_API_KEY")

    if not user_id:
        raise ConfigurationError(
            "BREWFATHER_USER_ID environment variable not set. "
            "Find your User ID in Brewfather Settings → API"
        )

    if not api_key:
        raise ConfigurationError(
            "BREWFATHER_API_KEY environment variable not set. "
            "Generate an API key in Brewfather Settings → API"
        )

    return BrewfatherConfig(user_id=user_id, api_key=api_key)
