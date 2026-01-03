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
| `mcp-beersmith` | BeerSmith recipe and ingredient integration | ✅ Complete (30 tools) |
| `mcp-grocy` | Grocy inventory and stock management | ✅ Complete (50 tools) |
| `mcp-brewfather` | Brewfather recipe and batch tracking | ✅ Complete (25 tools) |

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

All configuration is in the root [`config.json`](config.json) file:

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

---

## BeerSmith MCP Tools (30 tools)

Full integration with BeerSmith 3 for recipe management, ingredient lookup, and profile configuration.

### Recipe Management
| Tool | Description |
|------|-------------|
| `list_recipes` | List all recipes with optional folder/search filter |
| `get_recipe` | Get full recipe details by name or ID |
| `create_recipe` | Create a new recipe with ingredients, profiles, and save to BeerSmith |
| `search_recipes` | Search recipes across all folders |

### Ingredients
| Tool | Description |
|------|-------------|
| `list_grains` | List grains with optional search and type filter |
| `get_grain` | Get specific grain details |
| `list_hops` | List hops with optional search and type filter |
| `get_hop` | Get specific hop details |
| `list_yeasts` | List yeasts with optional search and lab filter |
| `get_yeast` | Get specific yeast details |
| `list_misc_ingredients` | List miscellaneous ingredients |
| `match_ingredients` | Fuzzy match ingredient names to BeerSmith database |

### Profiles
| Tool | Description |
|------|-------------|
| `list_equipment` | List all equipment profiles (including user-defined) |
| `get_equipment` | Get specific equipment profile |
| `list_mash_profiles` | List all mash profiles |
| `get_mash_profile` | Get specific mash profile with steps |
| `list_carbonation_profiles` | List carbonation/priming profiles |
| `get_carbonation_profile` | Get specific carbonation profile |
| `list_age_profiles` | List fermentation/aging profiles |
| `get_age_profile` | Get specific age profile with temperature schedule |
| `list_water_profiles` | List water chemistry profiles |
| `get_water_profile` | Get specific water profile |
| `get_default_recipe_settings` | Get BeerSmith's default profile selections from DefRecipe.bsopt |

### Styles
| Tool | Description |
|------|-------------|
| `list_styles` | List beer styles with optional search filter |
| `get_style` | Get specific style with guidelines |

### Utilities
| Tool | Description |
|------|-------------|
| `update_ingredient` | Update ingredient properties (e.g., price) |
| `suggest_recipe` | Get recipe suggestions based on available inventory |
| `compare_prices` | Compare BeerSmith prices with Grocy inventory |

### Key Features
- **User-defined profile support**: Properly parses BeerSmith's non-standard XML with multiple root elements
- **Default recipe integration**: Reads BeerSmith's DefRecipe.bsopt for user preferences
- **Smart defaults**: Falls back through BeerSmith defaults → MCP recipe defaults → hardcoded defaults
- **Direct recipe creation**: Saves recipes directly to BeerSmith's Recipe.bsmx in "MCP Created" folder
- **Backup system**: Creates timestamped backups before modifying BeerSmith files

---

## Grocy MCP Tools (50 tools)

Full integration with Grocy for inventory management, recipes, chores, tasks, and more.

### System
| Tool | Description |
|------|-------------|
| `get_system_info` | Get Grocy version and system details |
| `get_system_config` | Get system configuration including currency settings |
| `get_quantity_units` | List all quantity units |
| `get_userfields` | Get custom userfield definitions for entity types |

### Stock Management
| Tool | Description |
|------|-------------|
| `get_stock` | Get current stock for all products with optional category filter |
| `get_volatile_stock` | Get expiring, expired, and low stock products |
| `get_product_stock` | Get stock details for a specific product |
| `add_product` | Add stock (purchase) with price, date, location |
| `consume_product` | Consume stock with optional spoiled flag |
| `transfer_product` | Transfer stock between locations |
| `inventory_product` | Set absolute stock amount (stocktaking) |
| `open_product` | Mark product as opened |
| `get_product_by_barcode` | Look up product by barcode |
| `get_product_entries` | Get stock entry history (purchases, prices, locations) |
| `match_product_by_name` | Fuzzy product matching with confidence scores |
| `bulk_get_stock` | Get stock for multiple products in one call |

### Shopping List
| Tool | Description |
|------|-------------|
| `get_shopping_list` | Get all shopping list items |
| `add_to_shopping_list` | Add item by product name |
| `remove_from_shopping_list` | Remove item by ID |
| `clear_shopping_list` | Clear entire shopping list |
| `add_missing_products_to_shopping_list` | Add all products below minimum stock |
| `add_expired_products_to_shopping_list` | Add all expired products |
| `bulk_add_to_shopping_list` | Add multiple items at once |

### Recipes
| Tool | Description |
|------|-------------|
| `get_recipes` | List all recipes |
| `get_recipe` | Get recipe with ingredients |
| `get_recipe_fulfillment` | Check if stock fulfills recipe requirements |
| `consume_recipe` | Consume all recipe ingredients from stock |
| `add_recipe_to_shopping_list` | Add missing recipe ingredients to shopping list |
| `create_recipe_with_ingredients` | Create recipe with all ingredients in one operation |
| `get_recipe_with_stock_status` | Get recipe with complete stock levels for each ingredient |

### Chores
| Tool | Description |
|------|-------------|
| `get_chores` | List all chores with status |
| `get_chore_details` | Get detailed chore information |
| `execute_chore` | Mark chore as executed |

### Tasks
| Tool | Description |
|------|-------------|
| `get_tasks` | List all tasks |
| `create_task` | Create new task with due date |
| `complete_task` | Mark task as completed |

### Batteries
| Tool | Description |
|------|-------------|
| `get_batteries` | List all batteries with charge status |
| `get_battery_details` | Get detailed battery information |
| `charge_battery` | Track battery charge |

### Locations
| Tool | Description |
|------|-------------|
| `get_locations` | List all storage locations |
| `get_location_stock` | Get all stock at a specific location |

### Products
| Tool | Description |
|------|-------------|
| `get_products` | List products with optional search |
| `create_product` | Create new product with defaults |
| `get_product_groups` | List product groups/categories |

### Generic CRUD
| Tool | Description |
|------|-------------|
| `list_entities` | List all entities of a type |
| `get_entity` | Get specific entity by ID |
| `create_entity` | Create new entity |
| `update_entity` | Update entity properties |
| `delete_entity` | Delete entity |

### BeerSmith Integration
| Tool | Description |
|------|-------------|
| `list_brewing_ingredients` | List brewing ingredients with pricing for BeerSmith import |

### Key Features
- **Name-based lookups**: All tools accept product/location names with fuzzy matching
- **Bulk operations**: Efficiently handle multiple items in single calls
- **Recipe integration**: Full recipe management with stock fulfillment tracking
- **Barcode support**: Scan barcodes to look up products
- **Price tracking**: Stock entries include purchase prices for cost analysis
- **BeerSmith sync**: Export ingredient prices for BeerSmith integration

---

## Brewfather MCP Tools (25 tools)

Full integration with Brewfather for cloud-based recipe management, batch tracking, and inventory.

### Recipe Tools
| Tool | Description |
|------|-------------|
| `list_recipes` | List all Brewfather recipes with optional limit and archive filter |
| `get_recipe` | Get a specific recipe by name (fuzzy) or ID |
| `search_recipes` | Search recipes by name or style |
| `import_recipe` | Import a recipe from normalised format (e.g., from BeerSmith) |

### Batch Management
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

### Key Features
- **Cloud-based**: Access recipes and batches from anywhere
- **Batch tracking**: Monitor fermentation progress with readings
- **Brew tracker**: Step-by-step brewing progress tracking
- **Inventory management**: Full CRUD for all ingredient types
- **API pagination**: Automatic handling of large result sets
- **Recipe import**: Import from BeerSmith via normalised format

---

## Running MCP Servers

Claude Desktop will launch MCP servers automatically. For development or testing:

```bash
# Run the BeerSmith MCP server
uv run --package mcp-beersmith python -m mcp_beersmith

# Run the Grocy MCP server
uv run --package mcp-grocy python -m mcp_grocy

# Run the Brewfather MCP server
uv run --package mcp-brewfather python -m mcp_brewfather
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
├── config.json                 # Unified configuration
├── packages/
│   ├── brewing-common/         # Shared library
│   │   └── src/brewing_common/
│   ├── mcp-beersmith/          # BeerSmith MCP (30 tools)
│   │   └── src/mcp_beersmith/
│   │       ├── server.py       # FastMCP server
│   │       ├── tools.py        # Tool definitions
│   │       ├── parser.py       # BeerSmith XML parser
│   │       └── models.py       # Pydantic models
│   ├── mcp-grocy/              # Grocy MCP (50 tools)
│   │   └── src/mcp_grocy/
│   │       ├── server.py       # FastMCP server
│   │       ├── tools.py        # Tool definitions
│   │       └── client.py       # Grocy API client
│   └── mcp-brewfather/         # Brewfather MCP (25 tools)
│       └── src/mcp_brewfather/
│           ├── server.py       # FastMCP server
│           ├── tools.py        # Tool definitions
│           ├── client.py       # Brewfather API client
│           └── adapter.py      # Normalised format adapter
└── docs/
    ├── CONFIG.md               # Configuration reference
    └── SETUP_GUIDE.md          # Setup instructions
```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `BEERSMITH_PATH` | Path to BeerSmith data folder | Auto-detected |
| `BEERSMITH_BACKUP_PATH` | Path for backups | Optional |
| `GROCY_URL` | Grocy server URL | Yes |
| `GROCY_API_KEY` | Grocy API key | Yes |
| `BREWFATHER_USER_ID` | Brewfather user ID | Yes |
| `BREWFATHER_API_KEY` | Brewfather API key | Yes |

### BeerSmith Data Files

The BeerSmith MCP reads and writes these files:
- `Recipe.bsmx` - Recipes (creates "MCP Created" folder)
- `Grain.bsmx`, `Hops.bsmx`, `Yeast.bsmx`, `Misc.bsmx` - Ingredients
- `Equipment.bsmx`, `Mash.bsmx`, `Carbonation.bsmx`, `Age.bsmx` - Profiles
- `Water.bsmx` - Water chemistry profiles
- `Styles.bsmx` - Beer style definitions
- `DefRecipe.bsopt` - User's default recipe settings

## License

MIT
