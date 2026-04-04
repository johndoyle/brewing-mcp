"""Adapter for converting BeerSmith 4 models to brewing-common normalised models."""

from __future__ import annotations

from brewing_common.models import (
    HopUse as CommonHopUse,
    IngredientType,
    NormalisedIngredient,
    Recipe as CommonRecipe,
    YeastForm as CommonYeastForm,
)
from brewing_common.units import srm_to_ebc

from mcp_beersmith4.enums import HopUse, YeastForm
from mcp_beersmith4.models import (
    BS4Grain,
    BS4Hop,
    BS4Misc,
    BS4RecipeFull,
    BS4Yeast,
)


# BeerSmith internal unit: ounces → grams
_OZ_TO_G = 28.349523125
# BeerSmith internal unit: fluid ounces → litres
_FLOZ_TO_L = 0.0295735295625
# BeerSmith internal temperature: °F → °C
_F_TO_C = lambda f: (f - 32) * 5 / 9  # noqa: E731


HOP_USE_MAP: dict[int, CommonHopUse] = {
    HopUse.BOIL: CommonHopUse.BOIL,
    HopUse.DRY_HOP: CommonHopUse.DRY_HOP,
    HopUse.MASH: CommonHopUse.MASH,
    HopUse.FIRST_WORT: CommonHopUse.FIRST_WORT,
    HopUse.AROMA: CommonHopUse.AROMA,
}

YEAST_FORM_MAP: dict[int, CommonYeastForm] = {
    YeastForm.LIQUID: CommonYeastForm.LIQUID,
    YeastForm.DRY: CommonYeastForm.DRY,
}


class BeerSmith4Adapter:
    """Converts BeerSmith 4 domain models to brewing-common normalised models."""

    SOURCE_SYSTEM = "beersmith4"

    def recipe_to_common(self, full: BS4RecipeFull) -> CommonRecipe:
        """Convert a fully-parsed BS4 recipe to a normalised CommonRecipe."""
        recipe = full.recipe
        ingredients: list[NormalisedIngredient] = []

        for grain in full.grains:
            ingredients.append(self._grain_to_common(grain))
        for hop in full.hops:
            ingredients.append(self._hop_to_common(hop))
        for yeast in full.yeasts:
            ingredients.append(self._yeast_to_common(yeast))
        for misc in full.miscs:
            ingredients.append(self._misc_to_common(misc))

        # Batch volume from equipment (fl oz → litres)
        batch_size_l = 19.0  # fallback
        boil_size_l = None
        efficiency = None
        if full.equipment:
            batch_size_l = full.equipment.batch_vol * _FLOZ_TO_L or batch_size_l
            boil_size_l = full.equipment.boil_vol * _FLOZ_TO_L or None
            efficiency = full.equipment.efficiency or None

        # Color from style or recipe metadata
        color_ebc = None
        if full.style and full.style.min_color:
            avg_color = (full.style.min_color + full.style.max_color) / 2.0
            color_ebc = srm_to_ebc(avg_color)

        # Mash temperature from first mash step
        mash_temp_c = None
        if full.mash:
            steps = full.mash.steps
            if steps:
                mash_temp_c = _F_TO_C(steps[0].step_temp)

        # Fermentation temperature from age profile
        ferm_temp_c = None
        if full.age and full.age.prim_temp:
            ferm_temp_c = _F_TO_C(full.age.prim_temp)

        boil_time = int(recipe.boil_time) if recipe.boil_time else None
        if boil_time is None and full.equipment:
            boil_time = int(full.equipment.boil_time) if full.equipment.boil_time else 60

        return CommonRecipe(
            name=recipe.name,
            style=full.style.name if full.style else None,
            style_guide=full.style.guide if full.style else None,
            batch_size_l=batch_size_l,
            boil_size_l=boil_size_l,
            boil_time_min=boil_time,
            efficiency=efficiency,
            og=recipe.og_measured if recipe.og_measured_set else None,
            fg=recipe.fg_measured if recipe.fg_measured_set else None,
            color_ebc=color_ebc,
            mash_temp_c=mash_temp_c,
            fermentation_temp_c=ferm_temp_c,
            ingredients=ingredients,
            notes=recipe.notes or None,
            source_system=self.SOURCE_SYSTEM,
            source_id=str(recipe.permid),
        )

    # ── Ingredient conversions ────────────────────────────────────────

    def _grain_to_common(self, grain: BS4Grain) -> NormalisedIngredient:
        amount_g = grain.amount * _OZ_TO_G
        color_ebc = srm_to_ebc(grain.color) if grain.color else None

        return NormalisedIngredient(
            name=grain.name,
            type=IngredientType.GRAIN,
            amount_g=amount_g,
            color_ebc=color_ebc,
            source_system=self.SOURCE_SYSTEM,
            source_id=str(grain.permid) if grain.permid else None,
        )

    def _hop_to_common(self, hop: BS4Hop) -> NormalisedIngredient:
        amount_g = hop.amount * _OZ_TO_G
        use = HOP_USE_MAP.get(hop.use, CommonHopUse.BOIL)

        return NormalisedIngredient(
            name=hop.name,
            type=IngredientType.HOP,
            amount_g=amount_g,
            alpha_acid=hop.alpha,
            use=use,
            time_minutes=int(hop.boil_time) if hop.boil_time else None,
            source_system=self.SOURCE_SYSTEM,
            source_id=str(hop.permid) if hop.permid else None,
        )

    def _yeast_to_common(self, yeast: BS4Yeast) -> NormalisedIngredient:
        form = YEAST_FORM_MAP.get(yeast.form, CommonYeastForm.DRY)

        return NormalisedIngredient(
            name=yeast.name,
            type=IngredientType.YEAST,
            amount_g=yeast.amount,
            form=form,
            attenuation=yeast.avg_attenuation or None,
            source_system=self.SOURCE_SYSTEM,
            source_id=str(yeast.permid) if yeast.permid else None,
        )

    def _misc_to_common(self, misc: BS4Misc) -> NormalisedIngredient:
        return NormalisedIngredient(
            name=misc.name,
            type=IngredientType.MISC,
            amount_g=misc.amount,
            time_minutes=int(misc.time) if misc.time else None,
            source_system=self.SOURCE_SYSTEM,
            source_id=str(misc.permid) if misc.permid else None,
        )

    # ── Library ingredient conversions (no recipe amounts) ────────────

    def grain_to_common(self, grain: BS4Grain) -> NormalisedIngredient:
        color_ebc = srm_to_ebc(grain.color) if grain.color else None
        return NormalisedIngredient(
            name=grain.name,
            type=IngredientType.GRAIN,
            amount_g=0.0,
            color_ebc=color_ebc,
            source_system=self.SOURCE_SYSTEM,
            source_id=str(grain.permid) if grain.permid else None,
        )

    def hop_to_common(self, hop: BS4Hop) -> NormalisedIngredient:
        return NormalisedIngredient(
            name=hop.name,
            type=IngredientType.HOP,
            amount_g=0.0,
            alpha_acid=hop.alpha,
            source_system=self.SOURCE_SYSTEM,
            source_id=str(hop.permid) if hop.permid else None,
        )

    def yeast_to_common(self, yeast: BS4Yeast) -> NormalisedIngredient:
        form = YEAST_FORM_MAP.get(yeast.form, CommonYeastForm.DRY)
        return NormalisedIngredient(
            name=yeast.name,
            type=IngredientType.YEAST,
            amount_g=0.0,
            form=form,
            attenuation=yeast.avg_attenuation or None,
            source_system=self.SOURCE_SYSTEM,
            source_id=str(yeast.permid) if yeast.permid else None,
        )
