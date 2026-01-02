"""
Adapter for converting Brewfather data to brewing-common models.
"""

from datetime import datetime
from typing import Any

from brewing_common.models import (
    Recipe,
    NormalisedIngredient,
    Batch,
    IngredientType,
    HopUse,
    YeastForm,
)


class BrewfatherAdapter:
    """
    Converts Brewfather API responses to brewing-common normalised models
    and vice versa.

    Brewfather uses metric units (litres, kg, g) which aligns well with
    our normalised format.
    """

    SOURCE_SYSTEM = "brewfather"

    def to_recipe(self, raw: dict[str, Any]) -> Recipe:
        """
        Convert a Brewfather recipe to normalised format.

        Args:
            raw: Brewfather recipe API response

        Returns:
            Normalised Recipe
        """
        ingredients = []

        # Fermentables (grains)
        for f in raw.get("fermentables", []):
            ingredients.append(self._fermentable_to_ingredient(f))

        # Hops
        for h in raw.get("hops", []):
            ingredients.append(self._hop_to_ingredient(h))

        # Yeasts
        for y in raw.get("yeasts", []):
            ingredients.append(self._yeast_to_ingredient(y))

        # Miscs
        for m in raw.get("miscs", []):
            ingredients.append(self._misc_to_ingredient(m))

        return Recipe(
            name=raw.get("name", "Unknown"),
            style=raw.get("style", {}).get("name"),
            style_guide=raw.get("style", {}).get("category"),
            batch_size_l=raw.get("batchSize", 19.0),
            boil_size_l=raw.get("boilSize"),
            boil_time_min=raw.get("boilTime", 60),
            efficiency=raw.get("efficiency", 72),
            og=raw.get("og"),
            fg=raw.get("fg"),
            ibu=raw.get("ibu"),
            abv=raw.get("abv"),
            color_ebc=raw.get("color"),  # Brewfather uses EBC
            mash_temp_c=self._get_mash_temp(raw),
            fermentation_temp_c=self._get_ferment_temp(raw),
            ingredients=ingredients,
            notes=raw.get("notes"),
            source_system=self.SOURCE_SYSTEM,
            source_id=raw.get("_id"),
        )

    def _fermentable_to_ingredient(self, raw: dict[str, Any]) -> NormalisedIngredient:
        """Convert a Brewfather fermentable to normalised ingredient."""
        # Brewfather stores amounts in kg
        amount_kg = raw.get("amount", 0)
        amount_g = amount_kg * 1000

        return NormalisedIngredient(
            name=raw.get("name", "Unknown"),
            type=IngredientType.GRAIN,
            amount_g=amount_g,
            color_ebc=raw.get("color"),  # Already in EBC
            potential_ppg=raw.get("potential"),
            source_system=self.SOURCE_SYSTEM,
        )

    def _hop_to_ingredient(self, raw: dict[str, Any]) -> NormalisedIngredient:
        """Convert a Brewfather hop to normalised ingredient."""
        # Brewfather stores hop amounts in grams
        amount_g = raw.get("amount", 0)

        # Map use
        use_str = raw.get("use", "boil").lower()
        use_map = {
            "boil": HopUse.BOIL,
            "dry hop": HopUse.DRY_HOP,
            "mash": HopUse.MASH,
            "first wort": HopUse.FIRST_WORT,
            "whirlpool": HopUse.WHIRLPOOL,
            "aroma": HopUse.AROMA,
        }
        use = use_map.get(use_str, HopUse.BOIL)

        return NormalisedIngredient(
            name=raw.get("name", "Unknown"),
            type=IngredientType.HOP,
            amount_g=amount_g,
            alpha_acid=raw.get("alpha"),
            use=use,
            time_minutes=raw.get("time"),
            source_system=self.SOURCE_SYSTEM,
        )

    def _yeast_to_ingredient(self, raw: dict[str, Any]) -> NormalisedIngredient:
        """Convert a Brewfather yeast to normalised ingredient."""
        # Yeast amount is typically in packages/units
        amount = raw.get("amount", 1)

        # Map form
        form_str = raw.get("form", "dry").lower()
        form_map = {
            "dry": YeastForm.DRY,
            "liquid": YeastForm.LIQUID,
            "slurry": YeastForm.SLURRY,
            "culture": YeastForm.CULTURE,
        }
        form = form_map.get(form_str, YeastForm.DRY)

        return NormalisedIngredient(
            name=raw.get("name", "Unknown"),
            type=IngredientType.YEAST,
            amount_g=amount,  # Actually units, not grams
            form=form,
            attenuation=raw.get("attenuation"),
            source_system=self.SOURCE_SYSTEM,
        )

    def _misc_to_ingredient(self, raw: dict[str, Any]) -> NormalisedIngredient:
        """Convert a Brewfather misc to normalised ingredient."""
        # Misc amounts vary - try to normalise to grams
        amount = raw.get("amount", 0)
        unit = raw.get("unit", "g").lower()

        if unit == "kg":
            amount_g = amount * 1000
        elif unit == "oz":
            amount_g = amount * 28.3495
        elif unit == "ml":
            amount_g = amount  # Approximate
        else:
            amount_g = amount

        return NormalisedIngredient(
            name=raw.get("name", "Unknown"),
            type=IngredientType.MISC,
            amount_g=amount_g,
            time_minutes=raw.get("time"),
            source_system=self.SOURCE_SYSTEM,
        )

    def _get_mash_temp(self, raw: dict[str, Any]) -> float | None:
        """Extract primary mash temperature."""
        mash = raw.get("mash", {})
        steps = mash.get("steps", [])
        if steps:
            # Return first step temperature
            return steps[0].get("stepTemp")
        return None

    def _get_ferment_temp(self, raw: dict[str, Any]) -> float | None:
        """Extract primary fermentation temperature."""
        ferment = raw.get("fermentation", {})
        steps = ferment.get("steps", [])
        if steps:
            return steps[0].get("stepTemp")
        return None

    def to_batch(self, raw: dict[str, Any]) -> Batch:
        """
        Convert a Brewfather batch to normalised format.

        Args:
            raw: Brewfather batch API response

        Returns:
            Normalised Batch
        """
        brew_date = None
        if raw.get("brewDate"):
            try:
                # Brewfather uses milliseconds timestamp
                brew_date = datetime.fromtimestamp(raw["brewDate"] / 1000)
            except (ValueError, TypeError):
                pass

        return Batch(
            name=raw.get("name", "Unknown"),
            recipe_name=raw.get("recipe", {}).get("name"),
            recipe_id=raw.get("recipe", {}).get("_id"),
            brew_date=brew_date,
            actual_batch_size_l=raw.get("measuredBatchSize"),
            actual_og=raw.get("measuredOg"),
            actual_fg=raw.get("measuredFg"),
            actual_abv=raw.get("measuredAbv"),
            status=raw.get("status"),
            notes=raw.get("notes"),
            source_system=self.SOURCE_SYSTEM,
            source_id=raw.get("_id"),
        )

    def from_recipe(self, recipe: dict[str, Any]) -> dict[str, Any]:
        """
        Convert a normalised recipe dict to Brewfather format.

        Used for importing recipes into Brewfather.

        Args:
            recipe: Normalised recipe dictionary

        Returns:
            Brewfather recipe format
        """
        fermentables = []
        hops = []
        yeasts = []
        miscs = []

        for ing in recipe.get("ingredients", []):
            ing_type = ing.get("type", "misc")

            if ing_type == "grain":
                fermentables.append({
                    "name": ing.get("name"),
                    "amount": ing.get("amount_g", 0) / 1000,  # kg
                    "color": ing.get("color_ebc"),
                })
            elif ing_type == "hop":
                hops.append({
                    "name": ing.get("name"),
                    "amount": ing.get("amount_g", 0),  # g
                    "alpha": ing.get("alpha_acid"),
                    "time": ing.get("time_minutes"),
                    "use": ing.get("use", "Boil"),
                })
            elif ing_type == "yeast":
                yeasts.append({
                    "name": ing.get("name"),
                    "amount": ing.get("amount_g", 1),  # units
                    "attenuation": ing.get("attenuation"),
                })
            else:
                miscs.append({
                    "name": ing.get("name"),
                    "amount": ing.get("amount_g", 0),
                    "unit": "g",
                    "time": ing.get("time_minutes"),
                })

        return {
            "name": recipe.get("name"),
            "batchSize": recipe.get("batch_size_l", 19),
            "boilTime": recipe.get("boil_time_min", 60),
            "efficiency": recipe.get("efficiency", 72),
            "fermentables": fermentables,
            "hops": hops,
            "yeasts": yeasts,
            "miscs": miscs,
            "notes": recipe.get("notes"),
        }
