# Brewing MCP Platform - Implementation Plan

## Overview

A monorepo-based platform providing multiple MCP servers for brewing software integrations, with a shared library layer for consistent behaviour across all servers.

```
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
     │  - Shared data models                   │
     └─────────────────────────────────────────┘
```

## Technology Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Language | Python 3.12+ | Existing MCP server experience, excellent data wrangling libraries |
| MCP Framework | FastMCP | Simple, Pythonic API, good async support |
| Package Manager | uv | Fast, modern, excellent workspace support |
| Fuzzy Matching | RapidFuzz | Fast C++ implementation, good accuracy |
| Data Classes | Pydantic v2 | Validation, serialisation, schema generation |
| Testing | pytest + pytest-asyncio | Standard Python testing with async support |

## Repository Structure

```
brewing-mcp/
├── pyproject.toml              # Workspace root (uv workspace config)
├── uv.lock                     # Lockfile for reproducible builds
├── README.md                   # Project overview and quick start
├── PLAN.md                     # This file
├── Makefile                    # Common development commands
├── .pre-commit-config.yaml     # Linting and formatting hooks
├── .github/
│   └── workflows/
│       └── ci.yaml             # CI/CD pipeline
│
└── packages/
    ├── brewing-common/         # Shared library
    │   ├── pyproject.toml
    │   ├── README.md
    │   └── src/brewing_common/
    │       ├── __init__.py
    │       ├── models.py       # Shared data models (NormalisedIngredient, etc.)
    │       ├── units.py        # Unit conversion utilities
    │       ├── matching.py     # Fuzzy matching utilities
    │       ├── ingredients.py  # Ingredient normalisation logic
    │       ├── exceptions.py   # Shared exception types
    │       └── protocols.py    # Abstract interfaces for backends
    │
    ├── mcp-beersmith/          # BeerSmith MCP server
    │   ├── pyproject.toml
    │   ├── README.md
    │   └── src/mcp_beersmith/
    │       ├── __init__.py
    │       ├── server.py       # FastMCP server definition
    │       ├── parser.py       # BeerSmith XML parsing
    │       ├── tools.py        # MCP tool definitions
    │       └── adapter.py      # Converts to brewing-common models
    │
    ├── mcp-grocy/              # Grocy MCP server
    │   ├── pyproject.toml
    │   ├── README.md
    │   └── src/mcp_grocy/
    │       ├── __init__.py
    │       ├── server.py       # FastMCP server definition
    │       ├── client.py       # Grocy API client
    │       ├── tools.py        # MCP tool definitions
    │       └── adapter.py      # Converts to brewing-common models
    │
    └── mcp-brewfather/         # Brewfather MCP server (future)
        ├── pyproject.toml
        ├── README.md
        └── src/mcp_brewfather/
            ├── __init__.py
            ├── server.py       # FastMCP server definition
            ├── client.py       # Brewfather API client
            ├── tools.py        # MCP tool definitions
            └── adapter.py      # Converts to brewing-common models
```

## Implementation Phases

### Phase 1: Foundation (Week 1-2)

1. **Set up monorepo structure**
   - Create workspace `pyproject.toml` with uv
   - Configure development tooling (ruff, mypy, pre-commit)
   - Set up CI pipeline

2. **Implement brewing-common core**
   - Define shared data models (`NormalisedIngredient`, `Recipe`, etc.)
   - Implement comprehensive unit conversion
   - Build fuzzy matching utilities
   - Create abstract protocols for backends

### Phase 2: BeerSmith MCP (Week 2-3)

1. **Port existing BeerSmith functionality**
   - Migrate existing XML parser
   - Refactor to use brewing-common models
   - Add adapter layer for normalisation

2. **Enhance with new capabilities**
   - Recipe search and filtering
   - Ingredient inventory tracking
   - Session/batch history

### Phase 3: Grocy MCP (Week 3-4)

1. **Port existing Grocy functionality**
   - Migrate API client
   - Refactor to use brewing-common models
   - Add adapter layer

2. **Cross-system features**
   - Inventory sync from BeerSmith recipes
   - Stock level checking against recipe requirements
   - Shopping list generation

### Phase 4: Brewfather MCP (Week 4-5)

1. **Implement Brewfather integration**
   - API client for Brewfather REST API
   - Recipe and batch sync
   - Fermentation tracking

2. **Cross-platform sync**
   - Import recipes from BeerSmith
   - Sync inventory with Grocy

### Phase 5: Polish & Documentation (Week 5-6)

1. **Testing & validation**
   - Comprehensive unit tests
   - Integration tests with mocked APIs
   - End-to-end testing with real data

2. **Documentation**
   - API documentation
   - Usage guides for each MCP server
   - Claude prompt examples

---

## brewing-common Module Details

### models.py - Shared Data Models

```python
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime

class IngredientType(str, Enum):
    GRAIN = "grain"
    HOP = "hop"
    YEAST = "yeast"
    ADJUNCT = "adjunct"
    WATER = "water"
    MISC = "misc"

class HopUse(str, Enum):
    BOIL = "boil"
    DRY_HOP = "dry_hop"
    MASH = "mash"
    FIRST_WORT = "first_wort"
    WHIRLPOOL = "whirlpool"

class NormalisedIngredient(BaseModel):
    """Common representation across all brewing systems."""
    name: str
    type: IngredientType
    amount_g: float = Field(..., description="Amount in grams (or units for yeast)")
    
    # Optional attributes depending on type
    color_ebc: float | None = None      # For grains
    alpha_acid: float | None = None     # For hops
    time_minutes: int | None = None     # Boil/steep time
    use: HopUse | None = None           # For hops
    
    # Source tracking
    source_system: str                  # "beersmith", "grocy", "brewfather"
    source_id: str | None = None

class Recipe(BaseModel):
    """Normalised recipe representation."""
    name: str
    style: str | None = None
    batch_size_l: float
    og: float | None = None
    fg: float | None = None
    ibu: float | None = None
    abv: float | None = None
    
    ingredients: list[NormalisedIngredient] = []
    
    source_system: str
    source_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
```

### units.py - Unit Conversion

```python
from enum import Enum
from typing import TypeVar

class MassUnit(str, Enum):
    KG = "kg"
    G = "g"
    LB = "lb"
    OZ = "oz"
    MG = "mg"

class VolumeUnit(str, Enum):
    L = "l"
    ML = "ml"
    GAL_US = "gal_us"
    GAL_UK = "gal_uk"
    QT = "qt"
    PT = "pt"
    FL_OZ = "fl_oz"

class TemperatureUnit(str, Enum):
    C = "c"
    F = "f"
    K = "k"

# Conversion constants to base units
MASS_TO_GRAMS = {
    MassUnit.KG: 1000.0,
    MassUnit.G: 1.0,
    MassUnit.LB: 453.592,
    MassUnit.OZ: 28.3495,
    MassUnit.MG: 0.001,
}

VOLUME_TO_LITRES = {
    VolumeUnit.L: 1.0,
    VolumeUnit.ML: 0.001,
    VolumeUnit.GAL_US: 3.78541,
    VolumeUnit.GAL_UK: 4.54609,
    VolumeUnit.QT: 0.946353,
    VolumeUnit.PT: 0.473176,
    VolumeUnit.FL_OZ: 0.0295735,
}

def convert_mass(value: float, from_unit: MassUnit, to_unit: MassUnit) -> float:
    """Convert between mass units."""
    grams = value * MASS_TO_GRAMS[from_unit]
    return grams / MASS_TO_GRAMS[to_unit]

def convert_volume(value: float, from_unit: VolumeUnit, to_unit: VolumeUnit) -> float:
    """Convert between volume units."""
    litres = value * VOLUME_TO_LITRES[from_unit]
    return litres / VOLUME_TO_LITRES[to_unit]

def convert_temperature(value: float, from_unit: TemperatureUnit, to_unit: TemperatureUnit) -> float:
    """Convert between temperature units."""
    # First convert to Celsius
    if from_unit == TemperatureUnit.F:
        celsius = (value - 32) * 5 / 9
    elif from_unit == TemperatureUnit.K:
        celsius = value - 273.15
    else:
        celsius = value
    
    # Then convert to target
    if to_unit == TemperatureUnit.F:
        return celsius * 9 / 5 + 32
    elif to_unit == TemperatureUnit.K:
        return celsius + 273.15
    return celsius

# Colour conversion
def srm_to_ebc(srm: float) -> float:
    """Convert SRM to EBC colour units."""
    return srm * 1.97

def ebc_to_srm(ebc: float) -> float:
    """Convert EBC to SRM colour units."""
    return ebc / 1.97

def lovibond_to_ebc(lovibond: float) -> float:
    """Convert Lovibond to EBC."""
    return (lovibond * 2.65 - 1.2) * 1.97

def ebc_to_lovibond(ebc: float) -> float:
    """Convert EBC to Lovibond."""
    return (ebc / 1.97 + 1.2) / 2.65
```

### matching.py - Fuzzy Matching

```python
from rapidfuzz import fuzz, process
from typing import TypeVar, Callable

T = TypeVar("T")

def match_string(
    query: str,
    candidates: list[str],
    threshold: float = 0.7,
    limit: int = 5,
) -> list[tuple[str, float]]:
    """
    Match a query string against candidates using fuzzy matching.
    
    Returns list of (match, confidence) tuples above threshold.
    """
    if not candidates:
        return []
    
    results = process.extract(
        query,
        candidates,
        scorer=fuzz.token_sort_ratio,
        limit=limit,
    )
    return [
        (match, score / 100) 
        for match, score, _ in results 
        if score / 100 >= threshold
    ]

def match_objects(
    query: str,
    candidates: list[T],
    key: Callable[[T], str],
    threshold: float = 0.7,
    limit: int = 5,
) -> list[tuple[T, float]]:
    """
    Match a query string against objects using a key function.
    
    Returns list of (object, confidence) tuples above threshold.
    """
    if not candidates:
        return []
    
    # Build lookup from string to object
    string_to_obj: dict[str, T] = {key(obj): obj for obj in candidates}
    
    results = match_string(query, list(string_to_obj.keys()), threshold, limit)
    return [(string_to_obj[match], confidence) for match, confidence in results]

# Common ingredient name normalisations
INGREDIENT_ALIASES: dict[str, list[str]] = {
    "2-row": ["two-row", "2 row", "pale malt 2-row", "2-row pale"],
    "pilsner": ["pils", "pilsner malt", "pilsen"],
    "munich": ["munich malt", "münchner"],
    "cascade": ["cascade hops", "cascade (us)"],
    "centennial": ["centennial hops", "centennial (us)"],
    "citra": ["citra hops", "citra (us)"],
    "us-05": ["safale us-05", "us05", "american ale yeast"],
    "s-04": ["safale s-04", "s04", "english ale yeast"],
}

def normalise_ingredient_name(name: str) -> str:
    """
    Normalise an ingredient name to a canonical form.
    """
    name_lower = name.lower().strip()
    
    # Check if this matches any known alias
    for canonical, aliases in INGREDIENT_ALIASES.items():
        if name_lower == canonical or name_lower in aliases:
            return canonical
    
    return name_lower
```

### protocols.py - Backend Interfaces

```python
from abc import ABC, abstractmethod
from typing import Protocol

from .models import NormalisedIngredient, Recipe

class IngredientSource(Protocol):
    """Protocol for systems that can provide ingredients."""
    
    async def list_ingredients(
        self, 
        ingredient_type: str | None = None,
    ) -> list[NormalisedIngredient]:
        """List all available ingredients."""
        ...
    
    async def get_ingredient(
        self,
        identifier: str,
    ) -> NormalisedIngredient | None:
        """Get a specific ingredient by ID or name."""
        ...
    
    async def search_ingredients(
        self,
        query: str,
        threshold: float = 0.7,
    ) -> list[tuple[NormalisedIngredient, float]]:
        """Search ingredients with fuzzy matching."""
        ...

class RecipeSource(Protocol):
    """Protocol for systems that can provide recipes."""
    
    async def list_recipes(self) -> list[Recipe]:
        """List all available recipes."""
        ...
    
    async def get_recipe(self, identifier: str) -> Recipe | None:
        """Get a specific recipe by ID or name."""
        ...
    
    async def search_recipes(
        self,
        query: str,
        threshold: float = 0.7,
    ) -> list[tuple[Recipe, float]]:
        """Search recipes with fuzzy matching."""
        ...

class InventoryManager(Protocol):
    """Protocol for systems that can manage ingredient inventory."""
    
    async def get_stock(
        self,
        ingredient: NormalisedIngredient,
    ) -> float | None:
        """Get current stock level in grams."""
        ...
    
    async def add_stock(
        self,
        ingredient: NormalisedIngredient,
        amount_g: float,
    ) -> None:
        """Add to current stock."""
        ...
    
    async def consume_stock(
        self,
        ingredient: NormalisedIngredient,
        amount_g: float,
    ) -> None:
        """Remove from current stock."""
        ...
    
    async def check_recipe_availability(
        self,
        recipe: Recipe,
    ) -> dict[str, dict]:
        """Check stock levels against recipe requirements."""
        ...
```

---

## MCP Server Structure

Each MCP server follows the same pattern:

### server.py - FastMCP Server

```python
from fastmcp import FastMCP
from .tools import register_tools

mcp = FastMCP("mcp-beersmith")

# Register all tools
register_tools(mcp)

if __name__ == "__main__":
    mcp.run()
```

### tools.py - Tool Definitions

```python
from fastmcp import FastMCP
from brewing_common.models import Recipe, NormalisedIngredient

def register_tools(mcp: FastMCP):
    @mcp.tool()
    async def list_recipes() -> list[dict]:
        """List all BeerSmith recipes."""
        # Implementation using adapter
        ...
    
    @mcp.tool()
    async def get_recipe(name: str) -> dict | None:
        """Get a specific recipe by name with fuzzy matching."""
        ...
    
    @mcp.tool()
    async def search_ingredients(
        query: str,
        ingredient_type: str | None = None,
    ) -> list[dict]:
        """Search for ingredients with fuzzy matching."""
        ...
```

### adapter.py - Model Conversion

```python
from brewing_common.models import NormalisedIngredient, IngredientType
from brewing_common.units import convert_mass, MassUnit, lovibond_to_ebc

def beersmith_grain_to_normalised(grain: dict) -> NormalisedIngredient:
    """Convert a BeerSmith grain to normalised format."""
    return NormalisedIngredient(
        name=grain["name"],
        type=IngredientType.GRAIN,
        amount_g=convert_mass(
            grain["amount"], 
            MassUnit.LB, 
            MassUnit.G
        ) if grain.get("unit") == "lb" else grain["amount"],
        color_ebc=lovibond_to_ebc(grain["color"]) if grain.get("color") else None,
        source_system="beersmith",
        source_id=grain.get("id"),
    )
```

---

## Configuration

Each MCP server uses environment variables or a config file:

```toml
# ~/.config/brewing-mcp/config.toml

[beersmith]
library_path = "~/Documents/BeerSmith3/Library"
recipe_path = "~/Documents/BeerSmith3/Recipes"

[grocy]
url = "http://localhost:9283"
api_key = "your-api-key"

[brewfather]
user_id = "your-user-id"
api_key = "your-api-key"
```

---

## Next Steps

1. Review and approve this plan
2. Run `make setup` to initialise the monorepo
3. Begin implementing brewing-common
4. Migrate existing MCP servers to the new structure

---

## Open Questions

1. **Existing code**: Where are your current brewsmith-mcp-server and grocy-mcp-server located? We should review them for migration.

2. **BeerSmith version**: Are you using BeerSmith 2 or 3? The file formats differ slightly.

3. **Grocy setup**: Is Grocy running locally or on a server? What entities are you tracking (products, stock, recipes)?

4. **Brewfather**: Are you already using Brewfather, or is this for future expansion?

5. **Cross-system operations**: What specific sync operations do you need? Examples:
   - "Add missing ingredients from this recipe to Grocy shopping list"
   - "Check if I have enough stock for this BeerSmith recipe"
   - "Import this BeerSmith recipe to Brewfather"
