"""
Adapter for converting Grocy data to brewing-common models.
"""

from datetime import datetime
from typing import Any

from brewing_common.models import (
    NormalisedIngredient,
    IngredientType,
    InventoryItem,
)


class GrocyAdapter:
    """
    Converts Grocy API responses to brewing-common normalised models.

    Handles unit conversions from Grocy's flexible quantity units to grams.
    """

    SOURCE_SYSTEM = "grocy"

    # Default conversions when Grocy doesn't provide them
    # Maps common unit names to grams
    DEFAULT_UNIT_TO_GRAMS = {
        "kg": 1000.0,
        "g": 1.0,
        "lb": 453.592,
        "oz": 28.3495,
        "pack": 11.0,  # Yeast pack, approximate
        "packet": 11.0,
        "vial": 35.0,  # Liquid yeast vial, approximate
    }

    def to_inventory_item(
        self,
        product: dict[str, Any],
        stock_info: dict[str, Any],
    ) -> InventoryItem:
        """
        Convert Grocy product and stock info to an InventoryItem.

        Args:
            product: Grocy product object
            stock_info: Grocy stock information

        Returns:
            Normalised InventoryItem
        """
        ingredient = self._to_ingredient(product)

        # Convert stock amount to grams
        stock_amount = stock_info.get("amount", 0)
        quantity_g = self.convert_stock_to_grams(stock_amount, product)

        # Convert min stock to grams
        min_stock = product.get("min_stock_amount", 0)
        min_stock_g = self.convert_stock_to_grams(min_stock, product) if min_stock else None

        # Parse best before date
        best_before = None
        best_before_str = stock_info.get("best_before_date")
        if best_before_str and best_before_str != "2999-12-31":
            try:
                best_before = datetime.fromisoformat(best_before_str)
            except ValueError:
                pass

        return InventoryItem(
            ingredient=ingredient,
            quantity_g=quantity_g,
            min_stock_g=min_stock_g,
            location=stock_info.get("location", {}).get("name"),
            best_before=best_before,
            source_system=self.SOURCE_SYSTEM,
            source_id=str(product.get("id")),
        )

    def _to_ingredient(self, product: dict[str, Any]) -> NormalisedIngredient:
        """Convert a Grocy product to a NormalisedIngredient."""
        name = product.get("name", "Unknown")
        ingredient_type = self._guess_ingredient_type(name, product)

        return NormalisedIngredient(
            name=name,
            type=ingredient_type,
            amount_g=0.0,  # Will be set by InventoryItem
            source_system=self.SOURCE_SYSTEM,
            source_id=str(product.get("id")),
        )

    def _guess_ingredient_type(
        self,
        name: str,
        product: dict[str, Any],
    ) -> IngredientType:
        """
        Guess the ingredient type based on name and product group.

        This is heuristic - ideally Grocy products would have
        proper categorisation for brewing ingredients.
        """
        name_lower = name.lower()

        # Check for common indicators
        if any(x in name_lower for x in ["malt", "grain", "barley", "wheat", "oat", "rye"]):
            return IngredientType.GRAIN

        if any(x in name_lower for x in ["hop", "hops", "cascade", "citra", "simcoe", "mosaic"]):
            return IngredientType.HOP

        if any(x in name_lower for x in ["yeast", "safale", "wyeast", "white labs", "fermentis"]):
            return IngredientType.YEAST

        if any(x in name_lower for x in ["sugar", "honey", "syrup", "extract"]):
            return IngredientType.ADJUNCT

        return IngredientType.MISC

    def convert_stock_to_grams(
        self,
        amount: float,
        product: dict[str, Any],
    ) -> float:
        """
        Convert a stock amount to grams.

        Uses the product's quantity unit and conversion factors if available.

        Args:
            amount: Stock amount in product's unit
            product: Grocy product object

        Returns:
            Amount in grams
        """
        # Get the quantity unit name
        unit_name = product.get("qu_id_stock_name", "g").lower()

        # Check for Grocy-defined conversion
        # This would require fetching quantity_unit_conversions
        # For now, use defaults

        if unit_name in self.DEFAULT_UNIT_TO_GRAMS:
            return amount * self.DEFAULT_UNIT_TO_GRAMS[unit_name]

        # Fallback: assume grams
        return amount

    def convert_grams_to_stock(
        self,
        grams: float,
        product: dict[str, Any],
    ) -> float:
        """
        Convert grams to product's stock unit.

        Args:
            grams: Amount in grams
            product: Grocy product object

        Returns:
            Amount in product's stock unit
        """
        unit_name = product.get("qu_id_stock_name", "g").lower()

        if unit_name in self.DEFAULT_UNIT_TO_GRAMS:
            return grams / self.DEFAULT_UNIT_TO_GRAMS[unit_name]

        # Fallback: assume grams
        return grams
