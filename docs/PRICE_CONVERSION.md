# Price Conversion Guide

## The Problem

When syncing prices between Grocy and BeerSmith, you need to handle:
1. **Unit differences**: Grocy uses grams/kg, BeerSmith displays in your preference (kg/lb)
2. **Currency differences**: Grocy may use EUR, BeerSmith may display GBP/USD
3. **BeerSmith's internal format**: ALL prices stored as price per OUNCE ($/oz or £/oz)

## How BeerSmith Stores Prices

**CRITICAL**: BeerSmith stores ALL ingredient prices as **price per ounce** ($/oz or £/oz), regardless of what it displays.

- Stored: `0.1063` (£/oz)
- Displays as: `£3.75/kg` (when metric units enabled)
- Calculation: `0.1063 × 35.274 = 3.75`

This applies to:
- ✓ Grains: £/oz
- ✓ Hops: £/oz  
- ✓ Misc: £/oz
- ✓ Yeast: £/package

## Using the Tool

### Basic Usage (Metric)

Convert a Grocy price (£3.75/kg) to BeerSmith format:

```
convert_ingredient_price(3.75, "grain", "kg", "GBP", "GBP")
```

Result:
```markdown
# Price Conversion for Grain

**Input:** GBP3.7500/kg

✓ No currency conversion needed (GBP=GBP)

## Step 2: Unit Conversion
- GBP3.7500/kg ÷ 35.2740 = GBP0.1063/oz
- Conversion: 1 kg = 35.2740 oz
- **IMPORTANT:** BeerSmith stores ALL prices as $/oz (or £/oz, €/oz)

## Result
**BeerSmith Price:** GBP0.1063/oz

✅ Ready to use:
```json
{"price": 0.1063}
```

Update command:
```
update_ingredient("grain", "Pilsner (2 Row) Ger", '{"price": 0.1063}')
```

### With Currency Conversion

Convert EUR to GBP:

```
convert_ingredient_price(25.0, "hop", "kg", "EUR", "GBP")
```

Result shows both currency and unit conversion steps.

### Grocy Gram Prices

Grocy often shows prices per gram (e.g., €0.003/g):

```
convert_ingredient_price(0.003, "grain", "g", "EUR", "GBP")
```

Result:
- €0.003/g × 0.86 (EUR→GBP) = £0.00258/g
- £0.00258/g ÷ 0.035274 (g→oz) = £0.0731/oz

## Configuration

Edit `currency_config.json`:

```json
{
  "default_currency": "GBP",
  "default_weight_unit": "kg",
  "beersmith_currency": "GBP",
  "exchange_rates": {
    "USD": 0.79,
    "EUR": 0.86,
    "CAD": 0.58,
    "AUD": 0.51
  }
}
```

Exchange rates convert FROM the currency TO `default_currency`.

## Common Scenarios

### Scenario 1: Grocy Grain Price (£3.75/kg)

```bash
# 1. Convert
convert_ingredient_price(3.75, "grain", "kg", "GBP", "GBP")
# Returns: {"price": 0.1063}

# 2. Update BeerSmith
update_ingredient("grain", "Pilsner (2 Row) Ger", '{"price": 0.1063}')

# 3. Verify
get_grain("Pilsner (2 Row) Ger")
# Shows: £0.1063/oz, £3.75/kg ✓
```

### Scenario 2: Grocy Hop Price (€25/kg) 

```bash
# 1. Convert EUR to GBP
convert_ingredient_price(25.0, "hop", "kg", "EUR", "GBP")
# Returns: {"price": 0.6095}

# 2. Update BeerSmith
update_ingredient("hop", "Cascade", '{"price": 0.6095}')

# 3. Verify
get_hop("Cascade")
# Shows: £0.6095/oz, £21.50/kg ✓
```

### Scenario 3: Grocy Gram Price (€0.003/g)

```bash
# 1. Convert grams + EUR to GBP/oz
convert_ingredient_price(0.003, "grain", "g", "EUR", "GBP")
# Returns: {"price": 0.0731}

# 2. Update BeerSmith
update_ingredient("grain", "Specialty Malt", '{"price": 0.0731}')
```

## Verification

After updating, verify the price appears correctly in BeerSmith:

```bash
get_grain("Pilsner (2 Row) Ger")
```

Check the pricing section:
- **Price (£/oz)**: Should match what you set (e.g., 0.1063)
- **Price (£/kg)**: Should match your original Grocy price (e.g., 3.75)

## Conversion Factors Reference

| From → To | Factor | Example |
|-----------|--------|---------|
| kg → oz | 35.274 | £3.75/kg ÷ 35.274 = £0.1063/oz |
| g → oz | 0.035274 | £0.003/g ÷ 0.035274 = £0.0850/oz |
| lb → oz | 16.0 | £1.70/lb ÷ 16 = £0.1063/oz |

## Common Mistakes

### ❌ Setting kg price directly
```
update_ingredient("grain", "Pilsner (2 Row) Ger", '{"price": 3.75}')
```
BeerSmith interprets as £3.75/oz → displays as £132.28/kg (35x too high!)

### ✅ Convert first
```
convert_ingredient_price(3.75, "grain", "kg", "GBP", "GBP")
# Returns 0.1063
update_ingredient("grain", "Pilsner (2 Row) Ger", '{"price": 0.1063}')
```
BeerSmith stores £0.1063/oz → displays as £3.75/kg ✓

## Summary

1. **Always convert prices to $/oz before updating BeerSmith**
2. **Use `convert_ingredient_price` for all conversions**
3. **BeerSmith stores in $/oz, displays by multiplying by 35.274 for metric**
4. **Support for kg, g, lb, oz as source units**
5. **Currency conversion handled automatically from config**

For more information, see the old documentation in `old/BeerSmith MCP Server/docs/`.
