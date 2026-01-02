"""
brewing-common: Shared library for brewing MCP servers.

Provides consistent models, unit conversion, and fuzzy matching
across all brewing platform integrations.
"""

from brewing_common.models import (
    IngredientType,
    HopUse,
    YeastForm,
    NormalisedIngredient,
    Recipe,
    Batch,
    InventoryItem,
)
from brewing_common.units import (
    MassUnit,
    VolumeUnit,
    TemperatureUnit,
    convert_mass,
    convert_volume,
    convert_temperature,
    srm_to_ebc,
    ebc_to_srm,
    lovibond_to_ebc,
    ebc_to_lovibond,
)
from brewing_common.matching import (
    match_string,
    match_objects,
    normalise_ingredient_name,
)
from brewing_common.exceptions import (
    BrewingCommonError,
    UnitConversionError,
    MatchingError,
    ValidationError,
)

__version__ = "0.1.0"

__all__ = [
    # Models
    "IngredientType",
    "HopUse",
    "YeastForm",
    "NormalisedIngredient",
    "Recipe",
    "Batch",
    "InventoryItem",
    # Units
    "MassUnit",
    "VolumeUnit",
    "TemperatureUnit",
    "convert_mass",
    "convert_volume",
    "convert_temperature",
    "srm_to_ebc",
    "ebc_to_srm",
    "lovibond_to_ebc",
    "ebc_to_lovibond",
    # Matching
    "match_string",
    "match_objects",
    "normalise_ingredient_name",
    # Exceptions
    "BrewingCommonError",
    "UnitConversionError",
    "MatchingError",
    "ValidationError",
]
