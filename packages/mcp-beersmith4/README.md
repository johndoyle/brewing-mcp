# mcp-beersmith4

MCP server for **BeerSmith 4** — direct SQLite integration.

BeerSmith 4 stores data in SQLite databases (replacing BS3's XML format). This package reads the databases directly, providing recipe browsing, ingredient library access, and optional write support.

## Features

- **Recipe management**: List, search, and view full recipe details including embedded ingredients, equipment, style, mash profiles
- **Ingredient library**: Browse grains, hops, yeasts, misc, and water profiles
- **Profile access**: Equipment, styles, mash profiles
- **Folder navigation**: Hierarchical folder tree for recipe organisation
- **Write support**: Create and update recipes (with automatic backup)
- **Normalised output**: Convert to brewing-common format for cross-system comparison
- **Read-only by default**: Write operations require explicit opt-in

## Installation

```bash
uv pip install -e packages/mcp-beersmith4
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BEERSMITH4_PATH` | Auto-detected | Path to BeerSmith 4 data folder |
| `BEERSMITH4_READ_ONLY` | `true` | Set to `false` to enable write operations |

### Auto-detection

The server looks for BeerSmith 4 data in these locations:
- **macOS**: `~/Library/Containers/BeerSmith-LLC.BeerSmith4/Data/Library/Application Support/BeerSmith4`
- **Linux**: `~/.beersmith4`
- **Windows**: `~/Documents/BeerSmith4`

## MCP Tools

### Recipes
- `bs4_list_recipes` — List recipes with optional filters (folder, search, type, source)
- `bs4_get_recipe` — Get full recipe details by name or ID
- `bs4_search_recipes` — Multi-criteria search (name, ingredient, style)
- `bs4_get_recipe_normalised` — Get recipe in brewing-common metric format

### Ingredients
- `bs4_list_ingredients` — Browse ingredient library by type (grain/hop/yeast/misc/water)
- `bs4_get_ingredient` — Get detailed ingredient info

### Profiles
- `bs4_list_equipment` — List equipment profiles
- `bs4_list_styles` — List beer styles
- `bs4_list_mash_profiles` — List mash profiles with steps

### Folders
- `bs4_list_folders` — Get folder hierarchy

### Write Operations
- `bs4_create_recipe` — Create a new recipe (requires write access)
- `bs4_update_recipe` — Update an existing recipe (requires write access)

## Claude Desktop Configuration

```json
{
  "mcpServers": {
    "beersmith4": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/brewing-mcp/packages/mcp-beersmith4", "mcp-beersmith4"],
      "env": {
        "BEERSMITH4_READ_ONLY": "false"
      }
    }
  }
}
```

## BeerSmith 4 Data Model

### Databases
- `BeerSmith.sqlite` — Main database (recipes, ingredients, equipment, styles, mash profiles)
- `Archive.sqlite` — Archived recipes
- `DefRecipe.sqlite` — Default recipe template
- `Opts.sqlite` — User preferences (units, display settings)
- `Reports.sqlite` — Custom report templates

### Key Architecture
- Recipes store ingredients as **embedded JSON arrays** in the `Ingredients` TEXT column
- Equipment, style, mash, carbonation, and age profiles are **embedded JSON objects** in recipe rows
- Ingredient types are discriminated by `_Schema_` field: `7406`=Grain, `7403`=Hop, `7426`=Yeast, `7421`=Misc, `7423`=Water
- All weights in **ounces**, volumes in **fluid ounces**, temperatures in **°F** internally
- `_PERMID_` is the primary key, `_MOD_` tracks modification timestamps

## Safety

- **Read-only by default** — writes require `BEERSMITH4_READ_ONLY=false`
- **Automatic backups** — created before every write operation
- **Schema fingerprinting** — detects schema drift from BeerSmith updates
- **Field allowlist** — write operations only accept known safe fields
