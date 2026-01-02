"""
Shared data models for brewing integrations.

All models use Pydantic v2 for validation and serialisation.
Amounts are normalised to metric units (grams, litres, Celsius).
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, ConfigDict


class IngredientType(str, Enum):
    """Type of brewing ingredient."""

    GRAIN = "grain"
    HOP = "hop"
    YEAST = "yeast"
    ADJUNCT = "adjunct"
    WATER = "water"
    MISC = "misc"


class HopUse(str, Enum):
    """How a hop is used in the brewing process."""

    BOIL = "boil"
    DRY_HOP = "dry_hop"
    MASH = "mash"
    FIRST_WORT = "first_wort"
    WHIRLPOOL = "whirlpool"
    AROMA = "aroma"


class YeastForm(str, Enum):
    """Physical form of yeast."""

    DRY = "dry"
    LIQUID = "liquid"
    SLURRY = "slurry"
    CULTURE = "culture"


class NormalisedIngredient(BaseModel):
    """
    Common representation of a brewing ingredient across all systems.

    Amounts are normalised to grams for solids and millilitres for liquids.
    """

    model_config = ConfigDict(frozen=True)

    name: str = Field(..., description="Ingredient name")
    type: IngredientType = Field(..., description="Type of ingredient")
    amount_g: float = Field(
        ...,
        ge=0,
        description="Amount in grams (or units for yeast packets)",
    )

    # Grain-specific attributes
    color_ebc: float | None = Field(
        default=None,
        ge=0,
        description="Colour in EBC units (grains only)",
    )
    potential_ppg: float | None = Field(
        default=None,
        ge=0,
        description="Potential gravity points per pound per gallon",
    )

    # Hop-specific attributes
    alpha_acid: float | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Alpha acid percentage (hops only)",
    )
    use: HopUse | None = Field(
        default=None,
        description="How the hop is used (hops only)",
    )
    time_minutes: int | None = Field(
        default=None,
        ge=0,
        description="Contact/boil time in minutes",
    )

    # Yeast-specific attributes
    form: YeastForm | None = Field(
        default=None,
        description="Physical form of yeast (yeast only)",
    )
    attenuation: float | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Expected attenuation percentage",
    )

    # Source tracking
    source_system: str = Field(
        ...,
        description="Source system identifier (beersmith, grocy, brewfather)",
    )
    source_id: str | None = Field(
        default=None,
        description="Original ID in the source system",
    )

    # Additional metadata
    notes: str | None = Field(default=None, description="Additional notes")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional system-specific metadata",
    )


class Recipe(BaseModel):
    """
    Normalised recipe representation.

    Volumes in litres, temperatures in Celsius.
    """

    model_config = ConfigDict(frozen=True)

    name: str = Field(..., description="Recipe name")
    style: str | None = Field(default=None, description="Beer style")
    style_guide: str | None = Field(
        default=None,
        description="Style guide (e.g., BJCP 2021)",
    )

    # Batch parameters
    batch_size_l: float = Field(..., gt=0, description="Target batch size in litres")
    boil_size_l: float | None = Field(
        default=None,
        gt=0,
        description="Pre-boil volume in litres",
    )
    boil_time_min: int | None = Field(
        default=None,
        ge=0,
        description="Boil time in minutes",
    )
    efficiency: float | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Brewhouse efficiency percentage",
    )

    # Calculated/target values
    og: float | None = Field(
        default=None,
        ge=1.0,
        description="Original gravity",
    )
    fg: float | None = Field(
        default=None,
        ge=1.0,
        description="Final gravity",
    )
    ibu: float | None = Field(
        default=None,
        ge=0,
        description="International Bitterness Units",
    )
    abv: float | None = Field(
        default=None,
        ge=0,
        description="Alcohol by volume percentage",
    )
    color_ebc: float | None = Field(
        default=None,
        ge=0,
        description="Colour in EBC units",
    )

    # Ingredients
    ingredients: list[NormalisedIngredient] = Field(
        default_factory=list,
        description="Recipe ingredients",
    )

    # Mash and fermentation
    mash_temp_c: float | None = Field(
        default=None,
        description="Primary mash temperature in Celsius",
    )
    fermentation_temp_c: float | None = Field(
        default=None,
        description="Primary fermentation temperature in Celsius",
    )

    # Source tracking
    source_system: str = Field(
        ...,
        description="Source system identifier",
    )
    source_id: str | None = Field(
        default=None,
        description="Original ID in the source system",
    )

    # Timestamps
    created_at: datetime | None = Field(default=None)
    updated_at: datetime | None = Field(default=None)

    # Additional metadata
    notes: str | None = Field(default=None, description="Recipe notes")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional system-specific metadata",
    )

    @property
    def grains(self) -> list[NormalisedIngredient]:
        """Get all grain ingredients."""
        return [i for i in self.ingredients if i.type == IngredientType.GRAIN]

    @property
    def hops(self) -> list[NormalisedIngredient]:
        """Get all hop ingredients."""
        return [i for i in self.ingredients if i.type == IngredientType.HOP]

    @property
    def yeasts(self) -> list[NormalisedIngredient]:
        """Get all yeast ingredients."""
        return [i for i in self.ingredients if i.type == IngredientType.YEAST]


class Batch(BaseModel):
    """
    A brewed batch/session.

    Tracks actual values vs recipe targets.
    """

    model_config = ConfigDict(frozen=True)

    name: str = Field(..., description="Batch name/identifier")
    recipe_name: str | None = Field(default=None, description="Source recipe name")
    recipe_id: str | None = Field(default=None, description="Source recipe ID")

    # Brew day values
    brew_date: datetime | None = Field(default=None)
    actual_batch_size_l: float | None = Field(default=None, gt=0)
    actual_og: float | None = Field(default=None, ge=1.0)
    actual_fg: float | None = Field(default=None, ge=1.0)
    actual_abv: float | None = Field(default=None, ge=0)

    # Status
    status: str | None = Field(
        default=None,
        description="Current status (fermenting, conditioning, complete)",
    )

    # Source tracking
    source_system: str = Field(..., description="Source system identifier")
    source_id: str | None = Field(default=None)

    # Additional metadata
    notes: str | None = Field(default=None)
    metadata: dict[str, Any] = Field(default_factory=dict)


class InventoryItem(BaseModel):
    """
    Inventory record for an ingredient.

    Tracks stock levels and can be matched against recipe requirements.
    """

    model_config = ConfigDict(frozen=True)

    ingredient: NormalisedIngredient = Field(..., description="The ingredient")
    quantity_g: float = Field(
        ...,
        ge=0,
        description="Current stock in grams",
    )

    # Stock management
    min_stock_g: float | None = Field(
        default=None,
        ge=0,
        description="Minimum stock level (for alerts)",
    )
    location: str | None = Field(
        default=None,
        description="Storage location",
    )

    # Tracking
    best_before: datetime | None = Field(default=None)
    purchase_date: datetime | None = Field(default=None)
    price_per_kg: float | None = Field(default=None, ge=0)

    # Source tracking
    source_system: str = Field(..., description="Source system identifier")
    source_id: str | None = Field(default=None)

    @property
    def is_low_stock(self) -> bool:
        """Check if stock is below minimum threshold."""
        if self.min_stock_g is None:
            return False
        return self.quantity_g < self.min_stock_g

    @property
    def is_expired(self) -> bool:
        """Check if ingredient is past best before date."""
        if self.best_before is None:
            return False
        return datetime.now() > self.best_before
