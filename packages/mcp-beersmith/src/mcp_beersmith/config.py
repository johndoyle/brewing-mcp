"""Configuration management for BeerSmith MCP server."""

import os
from pathlib import Path
from dataclasses import dataclass


@dataclass
class BeerSmithConfig:
    """Configuration for BeerSmith integration."""

    library_path: Path
    backup_path: Path | None = None

    def __post_init__(self):
        # Expand user paths
        self.library_path = Path(self.library_path).expanduser()
        if self.backup_path:
            self.backup_path = Path(self.backup_path).expanduser()


def get_config() -> BeerSmithConfig:
    """
    Get BeerSmith configuration from environment or config file.

    Environment variables:
        BEERSMITH_PATH: Path to BeerSmith data folder
        BEERSMITH_BACKUP_PATH: Path for backups (optional)

    Returns:
        BeerSmithConfig instance

    Raises:
        ValueError: If required configuration is missing
    """
    library_path = os.environ.get("BEERSMITH_PATH")

    if not library_path:
        # Try common default locations
        common_paths = [
            # macOS BeerSmith 3
            Path.home() / "Library" / "Application Support" / "BeerSmith3",
            # Linux
            Path.home() / ".beersmith3",
            # Windows
            Path.home() / "Documents" / "BeerSmith3",
            # Older versions
            Path.home() / "Library" / "Application Support" / "BeerSmith2",
            Path.home() / ".beersmith2",
        ]
        for path in common_paths:
            if path.exists():
                library_path = str(path)
                break

    if not library_path:
        raise ValueError(
            "BEERSMITH_PATH environment variable not set and "
            "no default BeerSmith installation found"
        )

    backup_path = os.environ.get("BEERSMITH_BACKUP_PATH")

    return BeerSmithConfig(
        library_path=Path(library_path),
        backup_path=Path(backup_path) if backup_path else None,
    )
