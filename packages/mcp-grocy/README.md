# mcp-grocy

MCP server for Grocy inventory and stock management integration.

## Features

- **Inventory Management**: Track brewing ingredient stock levels
- **Recipe Availability**: Check if you have ingredients for a recipe
- **Shopping Lists**: Add missing ingredients to shopping lists
- **Stock Operations**: Add stock purchases, consume ingredients
- **Fuzzy Matching**: Match recipe ingredients to Grocy products

## Setup

### Prerequisites

- Grocy server running (local or remote)
- Grocy API key
- Python 3.12+

### Configuration

Set environment variables:

```bash
export GROCY_URL="http://localhost:9283"
export GROCY_API_KEY="your-api-key-here"
```

Or in `~/.config/brewing-mcp/config.toml`:

```toml
[grocy]
url = "http://localhost:9283"
api_key = "your-api-key"
```

### Getting Your Grocy API Key

1. Open Grocy in your browser
2. Go to Settings → Manage API keys
3. Create a new API key
4. Copy the key to your configuration

### Running

```bash
# From the brewing-mcp root
uv run --package mcp-grocy python -m mcp_grocy
```

## Tools

### get_inventory

Get all brewing ingredient stock levels.

**Parameters:**

- `category` (optional): Filter by product category

### get_stock

Get stock level for a specific ingredient.

**Parameters:**

- `name` (required): Ingredient name (uses fuzzy matching)

### check_recipe

Check if you have enough stock for a recipe.

**Parameters:**

- `ingredients` (required): List of ingredient objects with name and amount_g

### add_stock

Add a stock purchase.

**Parameters:**

- `name` (required): Product name
- `amount_g` (required): Amount in grams
- `price` (optional): Purchase price
- `best_before` (optional): Best before date (ISO format)

### consume_stock

Consume stock (e.g., for a brew day).

**Parameters:**

- `name` (required): Product name
- `amount_g` (required): Amount in grams

### add_to_shopping_list

Add an ingredient to the shopping list.

**Parameters:**

- `name` (required): Ingredient name
- `amount_g` (required): Amount needed
- `note` (optional): Additional note

### get_shopping_list

Get current shopping list.

### add_recipe_shortages

Add all missing ingredients for a recipe to shopping list.

**Parameters:**

- `ingredients` (required): List of ingredient objects with name and amount_g

## Claude Desktop Configuration

```json
{
  "mcpServers": {
    "grocy": {
      "command": "uv",
      "args": [
        "run",
        "--directory", "/path/to/brewing-mcp",
        "--package", "mcp-grocy",
        "python", "-m", "mcp_grocy"
      ],
      "env": {
        "GROCY_URL": "http://localhost:9283",
        "GROCY_API_KEY": "your-api-key"
      }
    }
  }
}
```
