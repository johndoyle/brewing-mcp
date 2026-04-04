# BeerSmith 4 Integration

The `mcp-beersmith4` package provides direct SQLite integration with BeerSmith 4, operating independently of the BS3 XML-based package.

## Architecture

BeerSmith 4 stores all data in SQLite databases within its application container:

| Database | Contents |
|----------|----------|
| `BeerSmith.sqlite` | Recipes, ingredients, equipment, styles, mash profiles, folders |
| `Archive.sqlite` | Archived/historical recipes |
| `DefRecipe.sqlite` | Default recipe template |
| `Opts.sqlite` | User preferences (units, display settings) |
| `Reports.sqlite` | Custom report templates |

### Data Model

- Recipes are in `M_RECIPE` (local) and `M_CLOUD` (cloud-synced)
- Ingredients are embedded as JSON arrays in the recipe's `Ingredients` TEXT column
- Equipment, style, mash, carbonation, and age profiles are embedded JSON objects in recipe rows
- Library tables (`M_GRAIN`, `M_HOPS`, `M_YEAST`, `M_MISC`, `M_WATER`) hold reusable ingredient definitions
- `_Schema_` discriminates ingredient types: `7406`=Grain, `7403`=Hop, `7426`=Yeast, `7421`=Misc, `7423`=Water
- `_PERMID_` is the primary key, `_MOD_` tracks modification timestamps

### Internal Units

| Measurement | BS4 Unit |
|-------------|----------|
| Weight | Ounces (oz) |
| Volume | Fluid ounces (fl oz) |
| Temperature | Fahrenheit (°F) |
| Color | SRM |

The adapter converts to metric (grams, litres, °C, EBC) for the normalised output.

## MCP Tools

14 tools are registered. See [../packages/mcp-beersmith4/README.md](../packages/mcp-beersmith4/README.md) for the full tool reference.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `BEERSMITH4_PATH` | Auto-detected | Path to BS4 data folder |
| `BEERSMITH4_READ_ONLY` | `true` | Set to `false` to enable writes |

## Safety Controls

- **Read-only by default** — writes require explicit opt-in
- **Automatic backups** — created before every write operation
- **Schema fingerprinting** — detects schema drift from BeerSmith updates
- **Dry-run mode** — validate writes without persisting (`dry_run=true`)
- **Field allowlist** — only known-safe fields can be written
- **Rollback on failure** — transactions are rolled back on any error
