# Currency Detection for Grocy-BeerSmith Integration

## The Problem

When syncing prices from Grocy to BeerSmith, the Grocy API doesn't include currency information in product data. This means we need another way to determine what currency the prices are in.

## Solutions

### Solution 1: Query Grocy System Config (Recommended)

Grocy stores its currency setting in the system configuration. You can query it:

```bash
# Get Grocy's system configuration
get_system_config()
```

Look for the `CURRENCY` field in the response:

```json
{
  "CURRENCY": "GBP",
  "FEATURE_FLAG_STOCK": "true",
  ...
}
```

Then update your [`config.json`](../config.json):

```json
{
  "currency": {
    "default": "GBP",
    "grocy": "GBP",
    "beersmith": "GBP"
  }
}
```

### Solution 2: Manual Configuration

If you know your Grocy currency, simply set it in [`config.json`](../config.json):

```json
{
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

### Solution 3: Store Currency in Product Userfields (Advanced)

You can use Grocy's custom userfields to store currency per product:

1. In Grocy, add a userfield to products called "currency"
2. Set it to "GBP", "USD", "EUR", etc. for each product
3. Query it when syncing prices

This is useful if you have products from multiple suppliers in different currencies.

## Recommended Workflow

### One-time Setup

1. **Query Grocy for its currency**:
   ```bash
   get_system_config()
   ```

2. **Update [`config.json`](../config.json)**:
   ```json
   {
     "currency": {
       "grocy": "GBP"  # or whatever Grocy returned
     }
   }
   ```

3. **Set exchange rates** (if different from BeerSmith):
   ```json
   {
     "currency": {
       "grocy": "EUR",
       "beersmith": "GBP",
       "exchange_rates": {
         "EUR": 0.86
       }
     }
   }
   ```

### When Syncing Prices

1. **Get product from Grocy**:
   ```bash
   get_product_stock(product_id)
   ```
   Returns: `price: 0.003` (no currency info)

2. **Use grocy_currency from config**:
   ```bash
   # Grocy price: €0.003/g
   # From config: grocy_currency = "EUR"
   
   convert_ingredient_price(
     0.003,           # price
     "grain",         # type
     "g",             # from_unit
     "EUR",           # from_currency (from config)
     "GBP"            # to_currency (BeerSmith)
   )
   ```

3. **Update BeerSmith**:
   ```bash
   update_ingredient("grain", "Pilsner Malt", '{"price": 0.0731}')
   ```

## Complete Example

### Scenario: Sync Grocy grain price to BeerSmith

**Given**:
- Grocy shows: `Barke Pilsner` at `3.75` per kilogram
- Grocy uses EUR (from system config)
- BeerSmith uses GBP

**Steps**:

```bash
# 1. Check Grocy's currency (one-time)
get_system_config()
# Returns: { "CURRENCY": "EUR", ... }

# 2. Update currency_config.json
# Set: "grocy_currency": "EUR"

# 3. Convert the price
convert_ingredient_price(
  3.75,      # price from Grocy
  "grain",   # ingredient type
  "kg",      # Grocy uses kg
  "EUR",     # grocy_currency from config
  "GBP"      # beersmith_currency from config
)

# Returns:
# - EUR 3.75/kg × 0.86 = GBP 3.23/kg
# - GBP 3.23/kg ÷ 35.274 = GBP 0.0915/oz
# Ready: {"price": 0.0915}

# 4. Update BeerSmith
update_ingredient("grain", "Pilsner (2 Row) Ger", '{"price": 0.0915}')

# 5. Verify
get_grain("Pilsner (2 Row) Ger")
# Shows: £0.0915/oz, £3.23/kg ✓
```

## Handling Different Currencies

### Same Currency (No Conversion)

If Grocy and BeerSmith both use GBP:

```json
{
  "currency": {
    "grocy": "GBP",
    "beersmith": "GBP"
  }
}
```

Only unit conversion needed:
```bash
convert_ingredient_price(3.75, "grain", "kg", "GBP", "GBP")
# £3.75/kg ÷ 35.274 = £0.1063/oz
```

### Different Currencies

If Grocy uses EUR and BeerSmith uses GBP:

```json
{
  "currency": {
    "grocy": "EUR",
    "beersmith": "GBP",
    "exchange_rates": {
      "EUR": 0.86
    }
  }
}
```

Both currency and unit conversion:
```bash
convert_ingredient_price(3.75, "grain", "kg", "EUR", "GBP")
# €3.75/kg × 0.86 = £3.23/kg
# £3.23/kg ÷ 35.274 = £0.0915/oz
```

## Automation Ideas

### Create a Helper Tool

You could create a wrapper that automatically uses the config:

```python
def sync_grocy_price_to_beersmith(
    grocy_price: float,
    grocy_unit: str,  # "g", "kg", etc.
    ingredient_type: str,
    ingredient_name: str
):
    """
    Sync a Grocy price to BeerSmith using configured currencies.
    """
    config = load_currency_config()
    
    # Convert using configured currencies
    result = convert_ingredient_price(
        grocy_price,
        ingredient_type,
        grocy_unit,
        config["grocy_currency"],
        config["beersmith_currency"]
    )
    
    # Extract converted price
    beersmith_price = extract_price_from_result(result)
    
    # Update BeerSmith
    update_ingredient(ingredient_type, ingredient_name, f'{{"price": {beersmith_price}}}')
```

### Batch Sync

For syncing many products:

```bash
# 1. Get all products from Grocy
products = get_products()

# 2. For each product with a price:
for product in products:
    if product["price"] > 0:
        # Determine ingredient type from product group
        type = map_product_group_to_ingredient_type(product["product_group_id"])
        
        # Convert price using config
        converted = convert_ingredient_price(
            product["price"],
            type,
            "g",  # Grocy default
            config["grocy_currency"],
            config["beersmith_currency"]
        )
        
        # Update BeerSmith
        update_ingredient(type, product["name"], ...)
```

## Configuration Reference

### currency_config.json Fields

| Field | Description | Example |
|-------|-------------|---------|
| `default_currency` | Your main currency | `"GBP"` |
| `default_weight_unit` | Your preferred weight unit | `"kg"` |
| `beersmith_currency` | Currency BeerSmith displays | `"GBP"` |
| `grocy_currency` | Currency Grocy uses | `"EUR"` |
| `exchange_rates` | Conversion rates TO default_currency | `{"EUR": 0.86}` |

### Query Grocy Currency

```bash
# Option 1: Use MCP tool
get_system_config()

# Option 2: Direct API (from terminal)
curl -H "GROCY-API-KEY: your-key" \
  http://your-grocy:9283/api/system/config \
  | jq '.CURRENCY'
```

### Update Configuration

Edit: [`config.json`](../config.json)

```json
{
  "currency": {
    "grocy": "EUR",
    "exchange_rates": {
      "EUR": 0.86,
      "USD": 0.79
    }
  }
}
```

## Summary

**Best Practice**:
1. ✅ Query Grocy's system config once: `get_system_config()`
2. ✅ Set `currency.grocy` in [`config.json`](../config.json)
3. ✅ Use `convert_ingredient_price` with configured currencies
4. ✅ Automate with helper functions if syncing frequently

**Key Points**:
- Grocy API doesn't include currency in product data
- Currency is stored in Grocy's system configuration
- Set `currency.grocy` in `config.json` once
- `convert_ingredient_price` handles both currency AND unit conversion
- Always verify prices after syncing

For more details, see [PRICE_CONVERSION.md](PRICE_CONVERSION.md).
