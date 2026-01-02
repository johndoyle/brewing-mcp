# Documentation Structure

All documentation has been organized into the `docs/` directory for a cleaner root structure.

## Documentation Files

| File | Purpose |
|------|---------|
| [CONFIG.md](CONFIG.md) | Configuration file reference and setup |
| [SETUP_GUIDE.md](SETUP_GUIDE.md) | Environment setup and Claude Desktop integration |
| [GROCY_CURRENCY.md](GROCY_CURRENCY.md) | Currency detection for price syncing |
| [PRICE_CONVERSION.md](PRICE_CONVERSION.md) | BeerSmith price storage format and conversions |
| [PLAN.md](PLAN.md) | Implementation plan and architecture |
| [CLEANUP_SUMMARY.md](CLEANUP_SUMMARY.md) | Summary of recent configuration cleanup |

## Quick Navigation

### Getting Started
1. Start with [../README.md](../README.md) for project overview
2. Follow [CONFIG.md](CONFIG.md) to set up configuration
3. Use [SETUP_GUIDE.md](SETUP_GUIDE.md) for environment setup

### Understanding Price Conversions
- [PRICE_CONVERSION.md](PRICE_CONVERSION.md) - How BeerSmith stores prices
- [GROCY_CURRENCY.md](GROCY_CURRENCY.md) - Currency detection when syncing

### Project Details
- [PLAN.md](PLAN.md) - Architecture and implementation phases

## Root Files

The root directory now contains only essential files:

```
brewing-mcp/
├── README.md                 # Project overview
├── config.json              # Your configuration (in .gitignore)
├── config.example.json      # Configuration template
├── claude_desktop_config.json
├── pyproject.toml          # Project configuration
├── Makefile                # Common commands
└── docs/                   # All documentation
    ├── CONFIG.md
    ├── SETUP_GUIDE.md
    ├── GROCY_CURRENCY.md
    ├── PRICE_CONVERSION.md
    ├── PLAN.md
    └── CLEANUP_SUMMARY.md
```

## Links in Documentation

All documentation files have been updated with correct relative paths:
- Files reference `../config.json` for the root configuration
- Cross-document links use relative paths (e.g., `PRICE_CONVERSION.md` not `docs/PRICE_CONVERSION.md`)
- README.md correctly points to `docs/` subdirectory files
