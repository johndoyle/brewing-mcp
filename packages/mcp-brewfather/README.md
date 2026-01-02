# mcp-brewfather

MCP server for Brewfather recipe and batch tracking integration.

## Features

- **Recipe Management**: List, search, and view Brewfather recipes
- **Batch Tracking**: View active batches and fermentation progress
- **Recipe Import**: Import recipes from BeerSmith (via normalised format)
- **Inventory Sync**: Check ingredient availability against Grocy
- **Brew Day Tools**: Create batches, log readings

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

Or in `~/.config/brewing-mcp/config.toml`:

```toml
[brewfather]
user_id = "your-user-id"
api_key = "your-api-key"
```

### Getting Your Brewfather API Key

1. Go to Brewfather settings
2. Navigate to "API" section
3. Generate a new API key
4. Note your User ID (also shown on the API page)

### Running

```bash
# From the brewing-mcp root
uv run --package mcp-brewfather python -m mcp_brewfather
```

## Tools

### list_recipes

List all Brewfather recipes.

**Parameters:**

- `limit` (optional): Maximum recipes to return (default 50)
- `include_archived` (optional): Include archived recipes

### get_recipe

Get a specific recipe by name or ID.

**Parameters:**

- `identifier` (required): Recipe name (fuzzy) or ID

### search_recipes

Search recipes by name, style, or ingredient.

**Parameters:**

- `query` (required): Search query
- `field` (optional): Field to search (name, style)

### list_batches

List brewing batches.

**Parameters:**

- `status` (optional): Filter by status (planning, brewing, fermenting, conditioning, completed)
- `limit` (optional): Maximum batches to return

### get_batch

Get batch details including fermentation data.

**Parameters:**

- `identifier` (required): Batch name or ID

### create_batch

Create a new batch from a recipe.

**Parameters:**

- `recipe_id` (required): Recipe ID
- `brew_date` (optional): Brew date (ISO format, defaults to today)
- `batch_name` (optional): Custom batch name

### log_reading

Log a gravity or temperature reading to a batch.

**Parameters:**

- `batch_id` (required): Batch ID
- `gravity` (optional): Gravity reading (e.g., 1.050)
- `temperature` (optional): Temperature in Celsius
- `note` (optional): Reading note

### import_recipe

Import a recipe from normalised format (e.g., from BeerSmith).

**Parameters:**

- `recipe` (required): Normalised recipe object

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

Brewfather API has rate limits. This server implements:

- Request caching (5 minute TTL for read operations)
- Automatic retry with exponential backoff
- Request queuing to prevent bursts
