# Configuration Cleanup Summary

## Changes Made

### 1. Created Consolidated Configuration
- **New File**: [`config.json`](../config.json) in root directory
- All configuration now in one place: paths, Grocy settings, currency, units
- Easier to manage and update than multiple config files

### 2. Updated Code to Use Root Config
- Modified [`packages/mcp-beersmith/src/mcp_beersmith/tools.py`](../packages/mcp-beersmith/src/mcp_beersmith/tools.py)
- `_load_currency_config()` now reads from root `config.json`
- Fallback support for old `currency_config.json` (backed up)

### 3. Removed Test Files
Deleted temporary test/debug scripts:
- ❌ `test_servers.py`
- ❌ `debug_mcp.py`
- ❌ `test_price_conversion.py`
- ❌ `test_grocy_api.py`

These were one-off debugging scripts no longer needed.

### 4. Created New Documentation
- **[docs/CONFIG.md](CONFIG.md)** - Comprehensive configuration reference
- Updated [docs/GROCY_CURRENCY.md](GROCY_CURRENCY.md) - Now references root config
- Updated [README.md](../README.md) - Points to new config structure

### 5. Backed Up Old Config
- Moved `packages/mcp-beersmith/src/mcp_beersmith/currency_config.json`
- To: `currency_config.json.backup`
- Still used as fallback if root config not found

## Benefits

1. **Single Source of Truth**: All configuration in root `config.json`
2. **Easier Updates**: One file to edit instead of searching through packages
3. **Better Organization**: Clear structure with `paths`, `grocy`, `currency`, `units` sections
4. **Cleaner Repository**: Removed temporary test files
5. **Better Documentation**: New CONFIG.md provides complete reference

## Configuration Structure

```json
{
  "paths": {
    "beersmith": "/path/to/BeerSmith3",
    "uv": "/path/to/uv"
  },
  "grocy": {
    "url": "http://server:9283",
    "api_key": "your-key"
  },
  "currency": {
    "default": "GBP",
    "beersmith": "GBP",
    "grocy": "GBP",
    "exchange_rates": {
      "USD": 0.79,
      "EUR": 0.86
    }
  },
  "units": {
    "default_weight": "kg"
  }
}
```

## Migration Notes

- Old `currency_config.json` backed up and still works as fallback
- No changes needed to Claude Desktop config
- Code automatically detects and uses root config
- All existing functionality preserved

## Next Steps

1. Update your local `config.json` with your settings
2. Delete `currency_config.json.backup` when ready (optional)
3. Use [docs/CONFIG.md](docs/CONFIG.md) as reference for all configuration

## Documentation Index

- [CONFIG.md](CONFIG.md) - Complete configuration reference
- [PRICE_CONVERSION.md](PRICE_CONVERSION.md) - BeerSmith price storage format
- [GROCY_CURRENCY.md](GROCY_CURRENCY.md) - Currency detection for price sync
- [SETUP_GUIDE.md](SETUP_GUIDE.md) - Initial setup and environment configuration
