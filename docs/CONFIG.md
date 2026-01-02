# Configuration Reference

All configuration is now consolidated in the root [`config.json`](../config.json) file for easier management.

## config.json Structure

```json
{
  "paths": {
    "beersmith": "/Users/john/Library/Application Support/BeerSmith3",
    "uv": "/Users/john/.local/bin/uv"
  },
  "grocy": {
    "url": "http://192.168.24.24:9283",
    "api_key": "your-api-key-here"
  },
  "currency": {
    "default": "GBP",
    "beersmith": "GBP",
    "grocy": "GBP",
    "exchange_rates": {
      "USD": 0.79,
      "EUR": 0.86,
      "CAD": 0.58,
      "AUD": 0.51
    }
  },
  "units": {
    "default_weight": "kg"
  }
}
```

## Configuration Fields

### paths

| Field | Description | Example |
|-------|-------------|---------|
| `beersmith` | BeerSmith 3 data directory | `/Users/john/Library/Application Support/BeerSmith3` (macOS)<br>`C:\Users\john\Documents\BeerSmith3` (Windows) |
| `uv` | Full path to uv command | `/Users/john/.local/bin/uv` (macOS)<br>`C:\Users\john\.local\bin\uv.exe` (Windows) |

**Note**: The full `uv` path is required for Claude Desktop because it has a limited PATH.

### grocy

| Field | Description | Example |
|-------|-------------|---------|
| `url` | Grocy server URL including port | `http://192.168.24.24:9283` |
| `api_key` | Grocy API key from Settings → API keys | `GTQl...` |

### currency

| Field | Description | Example |
|-------|-------------|---------|
| `default` | Your local currency | `GBP`, `USD`, `EUR` |
| `beersmith` | Currency BeerSmith displays | Usually same as `default` |
| `grocy` | Currency Grocy uses | Query with `get_system_config()` tool |
| `exchange_rates` | Conversion rates FROM currency TO default | `{"EUR": 0.86}` means €1 = £0.86 |

**Important**: Exchange rates convert FROM the listed currency TO your default currency.

### units

| Field | Description | Example |
|-------|-------------|---------|
| `default_weight` | Preferred weight unit | `kg` (metric), `lb` (imperial), `g` (grams) |

## Platform-Specific Paths

### macOS

```json
{
  "paths": {
    "beersmith": "/Users/YOUR_USERNAME/Library/Application Support/BeerSmith3",
    "uv": "/Users/YOUR_USERNAME/.local/bin/uv"
  }
}
```

**Finding uv path**:
```bash
which uv
```

### Windows

```json
{
  "paths": {
    "beersmith": "C:\\Users\\YOUR_USERNAME\\Documents\\BeerSmith3",
    "uv": "C:\\Users\\YOUR_USERNAME\\.local\\bin\\uv.exe"
  }
}
```

**Finding uv path** (PowerShell):
```powershell
(Get-Command uv).Source
```

### Linux

```json
{
  "paths": {
    "beersmith": "/home/YOUR_USERNAME/.beersmith3",
    "uv": "/home/YOUR_USERNAME/.local/bin/uv"
  }
}
```

## Getting Configuration Values

### Grocy Currency

To detect Grocy's currency setting:

```bash
# Using MCP tool
get_system_config()
# Look for: "CURRENCY": "GBP"

# Or direct API call
curl -H "GROCY-API-KEY: your-key" \
  http://your-grocy:9283/api/system/config | jq '.CURRENCY'
```

Then update `config.json`:
```json
{
  "currency": {
    "grocy": "GBP"
  }
}
```

### Exchange Rates

Update exchange rates to convert FROM each currency TO your default currency.

**Example**: If your default is GBP and you want to convert EUR:
- Current rate: €1 = £0.86
- Config: `"EUR": 0.86`

**Finding rates**:
- [xe.com](https://www.xe.com)
- [exchangerate-api.com](https://www.exchangerate-api.com)

## Legacy Configuration

The old `currency_config.json` in `packages/mcp-beersmith/src/mcp_beersmith/` is still supported as a fallback, but using the root `config.json` is recommended for easier management.

## Related Documentation

- [Price Conversion Guide](PRICE_CONVERSION.md) - Understanding BeerSmith's $/oz storage
- [Grocy Currency Detection](GROCY_CURRENCY.md) - Syncing prices between systems
- [Setup Guide](../SETUP_GUIDE.md) - Initial installation and environment setup

## Quick Setup Checklist

1. ✅ Copy [`config.json`](../config.json) to your local installation
2. ✅ Update `paths.beersmith` for your OS
3. ✅ Update `paths.uv` with output of `which uv` (macOS/Linux) or `(Get-Command uv).Source` (Windows)
4. ✅ Set `grocy.url` and `grocy.api_key` if using Grocy
5. ✅ Set `currency.default` to your local currency
6. ✅ Query Grocy with `get_system_config()` and update `currency.grocy`
7. ✅ Update `currency.exchange_rates` if converting between currencies
8. ✅ Restart Claude Desktop to load new configuration
