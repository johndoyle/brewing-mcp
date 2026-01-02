# brewing-common

Shared library for the brewing-mcp platform. Provides consistent models, unit conversion, and fuzzy matching across all MCP servers.

## Features

- **Data Models**: Normalised representations for ingredients, recipes, and inventory
- **Unit Conversion**: Comprehensive mass, volume, temperature, and colour conversions
- **Fuzzy Matching**: Ingredient name matching with configurable thresholds
- **Protocols**: Abstract interfaces for backend implementations

## Usage

```python
from brewing_common.models import NormalisedIngredient, IngredientType
from brewing_common.units import convert_mass, MassUnit, srm_to_ebc
from brewing_common.matching import match_string, normalise_ingredient_name

# Create a normalised ingredient
ingredient = NormalisedIngredient(
    name="Cascade",
    type=IngredientType.HOP,
    amount_g=50.0,
    alpha_acid=5.5,
    source_system="beersmith",
)

# Convert units
weight_kg = convert_mass(1.0, MassUnit.LB, MassUnit.KG)  # 0.453592

# Colour conversion
ebc = srm_to_ebc(10.0)  # 19.7

# Fuzzy matching
matches = match_string("casade", ["Cascade", "Centennial", "Citra"])
# [("Cascade", 0.92)]

# Name normalisation
canonical = normalise_ingredient_name("Safale US-05")  # "us-05"
```

## Modules

- `models.py` - Pydantic models for ingredients, recipes, batches
- `units.py` - Unit conversion utilities
- `matching.py` - Fuzzy string matching and ingredient normalisation
- `protocols.py` - Abstract interfaces for backend systems
- `exceptions.py` - Shared exception types
