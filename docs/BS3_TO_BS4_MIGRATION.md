# BeerSmith 3 → BeerSmith 4 Migration Guide

This guide covers the conceptual and structural differences between the BS3 (`mcp-beersmith`) and BS4 (`mcp-beersmith4`) MCP packages.

## Key Differences

| Aspect | BeerSmith 3 | BeerSmith 4 |
|--------|-------------|-------------|
| Storage | XML (`.bsmx` files) | SQLite databases |
| Parsing | XML parser with XPath | SQL queries + JSON parsing |
| Ingredients | XML child elements | JSON array in TEXT column |
| Profiles | XML child elements | Embedded JSON objects |
| IDs | XML element order / name | `_PERMID_` integer |
| Config env | `BEERSMITH_PATH` | `BEERSMITH4_PATH` |
| Write support | No | Yes (with safety gates) |
| Tool prefix | `bs_*` | `bs4_*` |

## Running Both Together

BS3 and BS4 are fully independent packages. They can run simultaneously in Claude Desktop:

```json
{
  "mcpServers": {
    "beersmith": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/brewing-mcp/packages/mcp-beersmith", "mcp-beersmith"]
    },
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

There is no runtime dependency between them. They share only:
- `brewing-common` — normalised models, unit conversion, and matching utilities

## Tool Mapping

| BS3 Tool | BS4 Equivalent | Notes |
|----------|---------------|-------|
| `bs_list_recipes` | `bs4_list_recipes` | BS4 adds folder/type/source filters |
| `bs_get_recipe` | `bs4_get_recipe` | BS4 returns embedded JSON profiles |
| `bs_search_recipes` | `bs4_search_recipes` | BS4 supports ingredient + style criteria |
| `bs_get_normalised_recipe` | `bs4_get_recipe_normalised` | Both output `brewing_common.Recipe` |
| `bs_list_ingredients` | `bs4_list_ingredients` | Same type parameter |
| `bs_get_ingredient` | `bs4_get_ingredient` | BS4 uses `_PERMID_` or name |
| — | `bs4_list_equipment` | New in BS4 |
| — | `bs4_list_styles` | New in BS4 |
| — | `bs4_list_mash_profiles` | New in BS4 |
| — | `bs4_list_folders` | New in BS4 |
| — | `bs4_create_recipe` | Write support (BS4 only) |
| — | `bs4_update_recipe` | Write support (BS4 only) |

## Normalised Output

Both packages produce `brewing_common.Recipe` and `NormalisedIngredient` objects. The output is structurally identical — the only difference is `source_system`:
- BS3: `"beersmith"`
- BS4: `"beersmith4"`

This means downstream consumers (Grocy sync, cross-recipe comparison, etc.) work with either source transparently.

## Data Path Differences

### BeerSmith 3
- macOS: `~/Library/Application Support/BeerSmith3/`
- Data files: `*.bsmx` XML files (Recipe.bsmx, Grain.bsmx, etc.)

### BeerSmith 4
- macOS: `~/Library/Containers/BeerSmith-LLC.BeerSmith4/Data/Library/Application Support/BeerSmith4/`
- Data files: SQLite databases (BeerSmith.sqlite, Archive.sqlite, etc.)

## When to Use Which

- **BS3 only**: You only have BeerSmith 3 installed
- **BS4 only**: You only have BeerSmith 4 installed, or you need write support
- **Both**: You have both versions and want to query/compare recipes across them
