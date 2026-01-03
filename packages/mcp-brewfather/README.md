# mcp-brewfather

MCP server for Brewfather recipe and batch tracking integration.

## Features

- **Recipe Management**: List, search, and view Brewfather recipes
- **Batch Tracking**: View active batches and fermentation progress
- **Batch Management**: Update status, log measurements, track brew tracker
- **Fermentation Monitoring**: Log and retrieve gravity/temperature readings
- **Inventory Management**: Full CRUD for fermentables, hops, yeasts, and miscs
- **Recipe Import**: Import recipes from BeerSmith (via normalised format)

## Setup

### Prerequisites

- Brewfather Premium account (API access required)
- Brewfather API key
- Python 3.12+

### Configuration

Set environment variables:

```bash
export BREWFATHER_USER_ID="your-user-id"
export BREWFATHER_API_KEY="your-api-key"
```

### Getting Your Brewfather API Key

1. Go to Brewfather settings
2. Navigate to "API" section
3. Generate a new API key with desired scopes
4. Note your User ID (also shown on the API page)

### Running

```bash
# From the brewing-mcp root
uv run --package mcp-brewfather python -m mcp_brewfather
```

## Tools (25 total)

### Recipe Tools

| Tool | Description |
|------|-------------|
| `list_recipes` | List all Brewfather recipes with optional limit and archive filter |
| `get_recipe` | Get a specific recipe by name (fuzzy) or ID |
| `search_recipes` | Search recipes by name or style |
| `import_recipe` | Import a recipe from normalised format (e.g., from BeerSmith) |

### Batch Tools

| Tool | Description |
|------|-------------|
| `list_batches` | List batches with optional status filter |
| `get_batch` | Get batch details including fermentation data |
| `create_batch` | Create a new batch from a recipe |
| `update_batch_status` | Update batch status (Planning, Brewing, Fermenting, etc.) |
| `update_batch_measurements` | Update measured OG, FG, batch size, efficiency |
| `get_active_batches` | Get all currently active batches with latest readings |

### Fermentation Tracking

| Tool | Description |
|------|-------------|
| `log_reading` | Log a gravity or temperature reading to a batch |
| `get_batch_readings` | Get all fermentation readings for a batch |
| `get_last_reading` | Get the most recent reading for a batch |
| `get_brewtracker` | Get brew tracker status (step-by-step progress) |

### Inventory - Listing

| Tool | Description |
|------|-------------|
| `list_fermentables` | List fermentables (grains, sugars, extracts) with inventory |
| `list_hops` | List hops with alpha acid and inventory |
| `list_yeasts` | List yeasts with attenuation and inventory |
| `list_miscs` | List misc items (water agents, fining, spices) |
| `get_inventory_item` | Get details for a specific inventory item |
| `get_inventory_summary` | Get summary of all inventory with counts |
| `search_inventory` | Search inventory by name across all types |

### Inventory - Updates

| Tool | Description |
|------|-------------|
| `update_fermentable_inventory` | Set or adjust fermentable inventory (kg) |
| `update_hop_inventory` | Set or adjust hop inventory (grams) |
| `update_yeast_inventory` | Set or adjust yeast inventory (packages) |
| `update_misc_inventory` | Set or adjust misc item inventory |

## API Scopes

Different operations require different API scopes:

| Scope | Operations |
|-------|------------|
| Read Recipes | list_recipes, get_recipe, search_recipes |
| Read Batches | list_batches, get_batch, get_batch_readings, get_brewtracker |
| Edit Batches | create_batch, update_batch_status, update_batch_measurements, log_reading |
| Read Inventory | list_*, get_inventory_*, search_inventory |
| Edit Inventory | update_*_inventory |

## Claude Desktop Configuration

```json
{
  "mcpServers": {
    "brewfather": {
      "command": "uv",
      "args": [
        "run",
        "--directory", "/path/to/brewing-mcp",
        "--package", "mcp-brewfather",
        "python", "-m", "mcp_brewfather"
      ],
      "env": {
        "BREWFATHER_USER_ID": "your-user-id",
        "BREWFATHER_API_KEY": "your-api-key"
      }
    }
  }
}
```

## API Rate Limits

Brewfather API limits: 500 calls per hour per API key. The server handles:

- Automatic pagination for large result sets
- Returns HTTP 429 with Retry-After header when exceeded
