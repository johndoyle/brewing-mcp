# mcp-beersmith

MCP server for BeerSmith recipe and ingredient integration.

## Features

- **Recipe Access**: Read and search BeerSmith recipes
- **Ingredient Library**: Access BeerSmith's ingredient database (grains, hops, yeasts)
- **Recipe Analysis**: Get recipe details including IBU, OG, FG, colour
- **Fuzzy Matching**: Find recipes and ingredients by approximate name

## Setup

### Prerequisites

- BeerSmith 3 installed with recipes/library files
- Python 3.12+

### Configuration

Set environment variables or create config file:

```bash
export BEERSMITH_LIBRARY_PATH="~/Documents/BeerSmith3/Library"
export BEERSMITH_RECIPE_PATH="~/Documents/BeerSmith3/Recipes"
```

Or in `~/.config/brewing-mcp/config.toml`:

```toml
[beersmith]
library_path = "~/Documents/BeerSmith3/Library"
recipe_path = "~/Documents/BeerSmith3/Recipes"
```

### Running

```bash
# From the brewing-mcp root
uv run --package mcp-beersmith python -m mcp_beersmith
```

## Tools

### list_recipes
List all available BeerSmith recipes.

### get_recipe
Get a specific recipe by name with fuzzy matching.

**Parameters:**
- `name` (required): Recipe name to search for
- `threshold` (optional): Match confidence threshold (0-1, default 0.7)

### search_recipes
Search recipes by name, style, or ingredient.

**Parameters:**
- `query` (required): Search query
- `field` (optional): Field to search (name, style, ingredient)
- `limit` (optional): Max results (default 10)

### list_ingredients
List ingredients from the BeerSmith library.

**Parameters:**
- `type` (optional): Filter by type (grain, hop, yeast, misc)

### get_ingredient
Get ingredient details by name.

**Parameters:**
- `name` (required): Ingredient name
- `type` (optional): Ingredient type for narrower search

### search_ingredients
Search for ingredients with fuzzy matching.

**Parameters:**
- `query` (required): Search query
- `type` (optional): Filter by type
- `threshold` (optional): Match confidence (0-1)

## Claude Desktop Configuration

```json
{
  "mcpServers": {
    "beersmith": {
      "command": "uv",
      "args": [
        "run",
        "--directory", "/path/to/brewing-mcp",
        "--package", "mcp-beersmith",
        "python", "-m", "mcp_beersmith"
      ],
      "env": {
        "BEERSMITH_LIBRARY_PATH": "~/Documents/BeerSmith3/Library"
      }
    }
  }
}
```
