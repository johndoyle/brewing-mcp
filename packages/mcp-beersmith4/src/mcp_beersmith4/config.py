"""Configuration management for BeerSmith 4 MCP server."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class BeerSmith4Config:
    """Configuration for BeerSmith 4 integration."""

    data_path: Path
    read_only: bool = True

    def __post_init__(self):
        self.data_path = Path(self.data_path).expanduser()

    @property
    def main_db(self) -> Path:
        return self.data_path / "BeerSmith.sqlite"

    @property
    def archive_db(self) -> Path:
        return self.data_path / "Archive.sqlite"

    @property
    def default_recipe_db(self) -> Path:
        return self.data_path / "DefRecipe.sqlite"

    @property
    def opts_db(self) -> Path:
        return self.data_path / "Opts.sqlite"

    @property
    def reports_db(self) -> Path:
        return self.data_path / "Reports.sqlite"

    @property
    def backup_dir(self) -> Path:
        return self.data_path / "Backups"


def get_config() -> BeerSmith4Config:
    """
    Get BeerSmith 4 configuration from environment or defaults.

    Environment variables:
        BEERSMITH4_PATH: Path to BeerSmith 4 data folder
        BEERSMITH4_READ_ONLY: Set to "false" to enable writes (default: true)
    """
    data_path = os.environ.get("BEERSMITH4_PATH")

    if not data_path:
        common_paths = [
            # macOS sandboxed container (standard)
            Path.home()
            / "Library"
            / "Containers"
            / "BeerSmith-LLC.BeerSmith4"
            / "Data"
            / "Library"
            / "Application Support"
            / "BeerSmith4",
            # macOS non-sandboxed fallback
            Path.home() / "Library" / "Application Support" / "BeerSmith4",
            # Linux
            Path.home() / ".beersmith4",
            # Windows
            Path.home() / "Documents" / "BeerSmith4",
        ]
        for path in common_paths:
            if path.exists() and (path / "BeerSmith.sqlite").exists():
                data_path = str(path)
                break

    if not data_path:
        raise ValueError(
            "BEERSMITH4_PATH environment variable not set and "
            "no default BeerSmith 4 installation found"
        )

    read_only_str = os.environ.get("BEERSMITH4_READ_ONLY", "true")
    read_only = read_only_str.lower() not in ("false", "0", "no")

    return BeerSmith4Config(
        data_path=Path(data_path),
        read_only=read_only,
    )
