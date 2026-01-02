"""Adapter for converting BeerSmith data to brewing-common models."""

from brewing_common.models import (
    HopUse,
    IngredientType,
    NormalisedIngredient,
    Recipe as CommonRecipe,
    YeastForm,
)
from brewing_common.units import (
    MassUnit,
    TemperatureUnit,
    VolumeUnit,
    convert_mass,
    convert_temperature,
    convert_volume,
    srm_to_ebc,
)

from mcp_beersmith.models import (
    Grain,
    Hop,
    Misc,
    Recipe,
    RecipeGrain,
    RecipeHop,
    RecipeMisc,
    RecipeYeast,
    Yeast,
)


class BeerSmithAdapter:
    """
    Converts BeerSmith models to brewing-common normalised models.

    Handles unit conversions (BeerSmith uses US units) and data mapping.
    """

    SOURCE_SYSTEM = "beersmith"

    def recipe_to_common(self, recipe: Recipe) -> CommonRecipe:
        """
        Convert a BeerSmith Recipe to a normalised CommonRecipe.

        Args:
            recipe: BeerSmith Recipe model

        Returns:
            Normalised CommonRecipe instance
        """
        # Convert batch size from gallons to litres
        batch_size_l = recipe.batch_size_liters

        # Convert color from SRM to EBC
        color_ebc = srm_to_ebc(recipe.color_srm) if recipe.color_srm else None

        # Convert all ingredients
        ingredients: list[NormalisedIngredient] = []

        for grain in recipe.grains:
            ingredients.append(self._grain_to_common(grain))

        for hop in recipe.hops:
            ingredients.append(self._hop_to_common(hop))

        for yeast in recipe.yeasts:
            ingredients.append(self._yeast_to_common(yeast))

        for misc in recipe.miscs:
            ingredients.append(self._misc_to_common(misc))

        # Get mash temp from first mash step if available
        mash_temp_c = None
        if recipe.mash and recipe.mash.steps:
            first_step = recipe.mash.steps[0]
            if first_step.temp_f:
                mash_temp_c = convert_temperature(
                    first_step.temp_f,
                    TemperatureUnit.F,
                    TemperatureUnit.C,
                )

        return CommonRecipe(
            name=recipe.name,
            style=recipe.style.name if recipe.style else None,
            batch_size_l=batch_size_l or 19.0,
            boil_time_min=int(recipe.boil_time) if recipe.boil_time else 60,
            efficiency=recipe.efficiency,
            og=recipe.og,
            fg=recipe.fg,
            ibu=recipe.ibu,
            abv=recipe.abv,
            color_ebc=color_ebc,
            mash_temp_c=mash_temp_c,
            fermentation_temp_c=None,  # BeerSmith stores this elsewhere
            ingredients=ingredients,
            notes=recipe.notes,
            source_system=self.SOURCE_SYSTEM,
            source_id=recipe.id,
        )

    def _grain_to_common(self, grain: RecipeGrain) -> NormalisedIngredient:
        """Convert a recipe grain ingredient."""
        amount_g = grain.amount_grams

        # Convert color from Lovibond to EBC
        color_ebc = None
        if grain.color:
            # Lovibond to EBC: EBC ≈ Lovibond × 1.97
            color_ebc = grain.color * 1.97

        return NormalisedIngredient(
            name=grain.name,
            type=IngredientType.GRAIN,
            amount_g=amount_g,
            color_ebc=color_ebc,
            source_system=self.SOURCE_SYSTEM,
        )

    def _hop_to_common(self, hop: RecipeHop) -> NormalisedIngredient:
        """Convert a recipe hop ingredient."""
        amount_g = hop.amount_grams

        # Map BeerSmith hop use to our enum
        use_mapping = {
            0: HopUse.BOIL,
            1: HopUse.DRY_HOP,
            2: HopUse.MASH,
            3: HopUse.FIRST_WORT,
            4: HopUse.AROMA,
        }
        use = use_mapping.get(hop.use, HopUse.BOIL)

        return NormalisedIngredient(
            name=hop.name,
            type=IngredientType.HOP,
            amount_g=amount_g,
            alpha_acid=hop.alpha,
            use=use,
            time_minutes=int(hop.boil_time) if hop.boil_time else None,
            source_system=self.SOURCE_SYSTEM,
        )

    def _yeast_to_common(self, yeast: RecipeYeast) -> NormalisedIngredient:
        """Convert a recipe yeast ingredient."""
        # Map form
        form_mapping = {
            0: YeastForm.LIQUID,
            1: YeastForm.DRY,
            2: YeastForm.SLURRY,
            3: YeastForm.CULTURE,
        }
        form = form_mapping.get(yeast.form, YeastForm.DRY)

        return NormalisedIngredient(
            name=yeast.name,
            type=IngredientType.YEAST,
            amount_g=yeast.amount,  # Actually units, not grams
            form=form,
            attenuation=yeast.attenuation,
            source_system=self.SOURCE_SYSTEM,
        )

    def _misc_to_common(self, misc: RecipeMisc) -> NormalisedIngredient:
        """Convert a misc ingredient."""
        return NormalisedIngredient(
            name=misc.name,
            type=IngredientType.MISC,
            amount_g=misc.amount,
            time_minutes=int(misc.time) if misc.time else None,
            source_system=self.SOURCE_SYSTEM,
        )

    def hop_to_common(self, hop: Hop) -> NormalisedIngredient:
        """
        Convert a library hop to a normalised ingredient.

        Used for library ingredients (not recipe amounts).
        """
        return NormalisedIngredient(
            name=hop.name,
            type=IngredientType.HOP,
            amount_g=0.0,
            alpha_acid=hop.alpha,
            source_system=self.SOURCE_SYSTEM,
        )

    def grain_to_common(self, grain: Grain) -> NormalisedIngredient:
        """
        Convert a library grain to a normalised ingredient.
        """
        color_ebc = None
        if grain.color:
            color_ebc = grain.color * 1.97

        return NormalisedIngredient(
            name=grain.name,
            type=IngredientType.GRAIN,
            amount_g=0.0,
            color_ebc=color_ebc,
            source_system=self.SOURCE_SYSTEM,
        )

    def yeast_to_common(self, yeast: Yeast) -> NormalisedIngredient:
        """
        Convert a library yeast to a normalised ingredient.
        """
        form_mapping = {
            0: YeastForm.LIQUID,
            1: YeastForm.DRY,
            2: YeastForm.SLURRY,
            3: YeastForm.CULTURE,
        }
        form = form_mapping.get(yeast.form, YeastForm.DRY)

        return NormalisedIngredient(
            name=yeast.name,
            type=IngredientType.YEAST,
            amount_g=0.0,
            form=form,
            attenuation=yeast.attenuation,
            source_system=self.SOURCE_SYSTEM,
        )

    def misc_to_common(self, misc: Misc) -> NormalisedIngredient:
        """
        Convert a library misc to a normalised ingredient.
        """
        return NormalisedIngredient(
            name=misc.name,
            type=IngredientType.MISC,
            amount_g=0.0,
            source_system=self.SOURCE_SYSTEM,
        )
