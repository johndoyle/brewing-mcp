# Brewing MCP Platform

A modular MCP (Model Context Protocol) platform for brewing software integrations. Connect Claude to your brewing tools with consistent behaviour and shared utilities.

## Architecture

```text
┌─────────────────────────────────────────┐
│           Claude / MCP Client           │
└─────────────┬───────────┬───────────────┘
              │           │           │
     ┌────────▼──┐  ┌─────▼─────┐  ┌──▼────────┐
     │ BeerSmith │  │ Brewfather│  │   Grocy   │
     │    MCP    │  │    MCP    │  │    MCP    │
     └────────┬──┘  └─────┬─────┘  └──┬────────┘
              │           │           │
     ┌────────▼───────────▼───────────▼────────┐
     │       brewing-common (shared lib)       │
     │  - Ingredient normalisation             │
     │  - Unit conversion                      │
     │  - Fuzzy matching utilities             │
     └─────────────────────────────────────────┘
```

## Packages

| Package | Description | Status |
| ------- | ----------- | ------ |
| `brewing-common` | Shared library with models, units, and matching | ✅ Complete |
| `mcp-beersmith` | BeerSmith recipe and ingredient integration | ✅ Complete |
| `mcp-grocy` | Grocy inventory and stock management | ✅ Complete |
| `mcp-brewfather` | Brewfather recipe and batch tracking | 📋 Planned |

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager

### Installation

```bash
# Clone the repository
git clone https://github.com/johndoyle/brewing-mcp.git
cd brewing-mcp

# Install all packages in development mode
make install

# Or manually with uv
uv sync
```

### Setup & Configuration

For detailed setup instructions see:
- **[CONFIG.md](docs/CONFIG.md)** - Configuration file reference
- **[SETUP_GUIDE.md](docs/SETUP_GUIDE.md)** - Environment setup and Claude Desktop integration

All configuration is now in the root [`config.json`](config.json) file:

```json
{
  "paths": {
    "beersmith": "/path/to/BeerSmith3",
    "uv": "/path/to/uv"
  },
  "grocy": {
    "url": "http://localhost:9283",
    "api_key": "your-api-key"
  },
  "currency": {
    "default": "GBP",
    "beersmith": "GBP",
    "grocy": "GBP",
    "exchange_rates": {
      "USD": 0.79,
      "EUR": 0.86
    }
  }
}
```

### Running an MCP Server

```bash
# Run the BeerSmith MCP server
uv run --package mcp-beersmith python -m mcp_beersmith

# Run the Grocy MCP server (requires GROCY_URL and GROCY_API_KEY)
uv run --package mcp-grocy python -m mcp_grocy
```

## Development

### Setup

```bash
# Install development dependencies
make install

# Set up pre-commit hooks
make setup-hooks
```

### Commands

```bash
make test          # Run all tests
make lint          # Run linting (ruff + mypy)
make format        # Format code with ruff
make check         # Run all checks (lint + test)
```

### Project Structure

```text
brewing-mcp/
├── pyproject.toml              # Workspace root
├── packages/
│   ├── brewing-common/         # Shared library
│   │   └── src/brewing_common/
│   ├── mcp-beersmith/          # BeerSmith MCP
│   │   └── src/mcp_beersmith/
│   ├── mcp-grocy/              # Grocy MCP
│   │   └── src/mcp_grocy/
│   └── mcp-brewfather/         # Brewfather MCP
│       └── src/mcp_brewfather/
```

## Configuration

The MCP servers use environment variables for configuration. See **[SETUP_GUIDE.md](SETUP_GUIDE.md)** for detailed setup instructions by operating system.

**Environment Variables**:

- `BEERSMITH_PATH` - Path to BeerSmith data folder (optional, auto-detected)
- `BEERSMITH_BACKUP_PATH` - Path for backups (optional)
- `GROCY_URL` - Grocy server URL (required)
- `GROCY_API_KEY` - Grocy API key (required)
- `BREWFATHER_USER_ID` - Brewfather user ID (required)
- `BREWFATHER_API_KEY` - Brewfather API key (required)

## License

MIT
