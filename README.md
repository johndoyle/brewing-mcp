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
| `brewing-common` | Shared library with models, units, and matching | 🚧 In Progress |
| `mcp-beersmith` | BeerSmith recipe and ingredient integration | 🚧 In Progress |
| `mcp-grocy` | Grocy inventory and stock management | 🚧 In Progress |
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

### Running an MCP Server

```bash
# Run the BeerSmith MCP server
uv run --package mcp-beersmith python -m mcp_beersmith

# Run the Grocy MCP server
uv run --package mcp-grocy python -m mcp_grocy
```

### Claude Desktop Configuration

Add to your `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "beersmith": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/brewing-mcp", "--package", "mcp-beersmith", "python", "-m", "mcp_beersmith"],
      "env": {
        "BEERSMITH_LIBRARY_PATH": "~/Documents/BeerSmith3/Library"
      }
    },
    "grocy": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/brewing-mcp", "--package", "mcp-grocy", "python", "-m", "mcp_grocy"],
      "env": {
        "GROCY_URL": "http://localhost:9283",
        "GROCY_API_KEY": "your-api-key"
      }
    }
  }
}
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

Create a config file at `~/.config/brewing-mcp/config.toml`:

```toml
[beersmith]
library_path = "~/Documents/BeerSmith3/Library"
recipe_path = "~/Documents/BeerSmith3/Recipes"

[grocy]
url = "http://localhost:9283"
api_key = "your-api-key"

[brewfather]
user_id = "your-user-id"
api_key = "your-api-key"
```

Or use environment variables:

- `BEERSMITH_LIBRARY_PATH` - Path to BeerSmith library folder
- `GROCY_URL` - Grocy server URL
- `GROCY_API_KEY` - Grocy API key
- `BREWFATHER_USER_ID` - Brewfather user ID
- `BREWFATHER_API_KEY` - Brewfather API key

## License

MIT
