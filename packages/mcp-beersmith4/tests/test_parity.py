"""Parity bridge tests: verify BS4 normalised output matches brewing-common contract.

These tests validate that BeerSmith 4 adapter produces the same normalised format
that any compliant source system (including BeerSmith 3) would produce, ensuring
cross-system comparisons and downstream consumers (e.g. Grocy sync) work correctly.

Does NOT import any BS3 code — validates against the brewing_common contract directly.
"""

from __future__ import annotations

import pytest
from brewing_common.models import (
    HopUse as CommonHopUse,
    IngredientType,
    NormalisedIngredient,
    Recipe as CommonRecipe,
    YeastForm as CommonYeastForm,
)

from mcp_beersmith4.adapter import BeerSmith4Adapter
from mcp_beersmith4.models import (
    BS4Age,
    BS4Equipment,
    BS4Grain,
    BS4Hop,
    BS4Mash,
    BS4Misc,
    BS4Recipe,
    BS4RecipeFull,
    BS4Style,
    BS4Yeast,
)

import json


def _make_american_ipa() -> BS4RecipeFull:
    """Build a canonical American IPA that mirrors a typical BS3 recipe."""
    recipe = BS4Recipe(
        permid=42,
        name="Parity Test IPA",
        type=2,  # AllGrain
        og_measured=1.062,
        fg_measured=1.010,
        og_measured_set=1,
        fg_measured_set=1,
        notes="Parity test",
    )
    equipment = BS4Equipment(
        name="10 Gal Mash Tun",
        batch_vol=640.0,  # 5 gal in fl oz
        boil_vol=896.0,
        boil_time=60.0,
        efficiency=72.0,
    )
    style = BS4Style(
        name="American IPA",
        category="IPA",
        guide="BJCP 2021",
        number="21A",
        min_og=1.056,
        max_og=1.070,
        min_fg=1.008,
        max_fg=1.014,
        min_ibu=40.0,
        max_ibu=70.0,
        min_color=6.0,
        max_color=14.0,
    )
    mash = BS4Mash(
        name="Single Infusion",
        ph=5.4,
        sparge_temp=168.0,
        steps_raw=json.dumps([
            {
                "F_MS_NAME": "Saccharification",
                "F_MS_TYPE": "0",
                "F_MS_STEP_TEMP": "152.0",
                "F_MS_STEP_TIME": "60.0",
            },
        ]),
    )
    age = BS4Age(
        name="Ale",
        prim_temp=67.0,
        prim_days=14.0,
        sec_temp=67.0,
        sec_days=7.0,
    )
    grains = [
        BS4Grain(
            permid=1,
            name="Pale Malt (2 Row) US",
            origin="US",
            amount=192.0,  # 12 lbs in oz
            color=2.0,
            yield_pct=79.0,
            type=0,
        ),
        BS4Grain(
            permid=2,
            name="Crystal 40L",
            origin="US",
            amount=16.0,  # 1 lb in oz
            color=40.0,
            yield_pct=74.0,
            type=0,
        ),
    ]
    hops = [
        BS4Hop(
            permid=10,
            name="Centennial",
            origin="US",
            amount=1.5,  # oz
            alpha=10.0,
            boil_time=60.0,
            use=0,  # Boil
            form=0,  # Pellet
        ),
        BS4Hop(
            permid=11,
            name="Cascade",
            origin="US",
            amount=1.0,
            alpha=5.5,
            boil_time=15.0,
            use=0,  # Boil
            form=0,
        ),
        BS4Hop(
            permid=12,
            name="Citra",
            origin="US",
            amount=2.0,
            alpha=12.0,
            boil_time=0.0,
            use=1,  # Dry Hop
            form=0,
        ),
        BS4Hop(
            permid=13,
            name="Simcoe",
            origin="US",
            amount=0.5,
            alpha=13.0,
            boil_time=60.0,
            use=3,  # First Wort
            form=0,
        ),
    ]
    yeasts = [
        BS4Yeast(
            permid=20,
            name="Safale US-05",
            lab="Fermentis",
            product_id="US-05",
            form=1,  # Dry
            min_attenuation=73.0,
            max_attenuation=77.0,
        ),
    ]
    miscs = [
        BS4Misc(
            permid=30,
            name="Irish Moss",
            amount=0.5,
            time=15.0,
            type=2,
            use=0,
        ),
    ]
    return BS4RecipeFull(
        recipe=recipe,
        equipment=equipment,
        style=style,
        mash=mash,
        age=age,
        grains=grains,
        hops=hops,
        yeasts=yeasts,
        miscs=miscs,
    )


class TestNormalisedOutputContract:
    """The normalised output must conform to the brewing_common.Recipe schema
    regardless of whether the source is BS3 or BS4."""

    def test_recipe_is_common_recipe(self):
        adapter = BeerSmith4Adapter()
        common = adapter.recipe_to_common(_make_american_ipa())
        assert isinstance(common, CommonRecipe)

    def test_source_system_tag(self):
        adapter = BeerSmith4Adapter()
        common = adapter.recipe_to_common(_make_american_ipa())
        assert common.source_system == "beersmith4"
        assert common.source_id == "42"

    def test_all_ingredients_are_normalised(self):
        adapter = BeerSmith4Adapter()
        common = adapter.recipe_to_common(_make_american_ipa())
        for ing in common.ingredients:
            assert isinstance(ing, NormalisedIngredient)
            assert ing.source_system == "beersmith4"


class TestUnitConversionParity:
    """Unit conversions must produce metric values comparable to BS3 output."""

    def test_grain_amount_oz_to_grams(self):
        adapter = BeerSmith4Adapter()
        common = adapter.recipe_to_common(_make_american_ipa())
        pale = common.grains[0]
        # 192 oz * 28.3495 g/oz = 5443.1 g (12 lbs)
        assert abs(pale.amount_g - 5443.1) < 1.0

    def test_hop_amount_oz_to_grams(self):
        adapter = BeerSmith4Adapter()
        common = adapter.recipe_to_common(_make_american_ipa())
        centennial = common.hops[0]
        # 1.5 oz * 28.3495 = 42.52 g
        assert abs(centennial.amount_g - 42.52) < 0.5

    def test_batch_size_floz_to_litres(self):
        adapter = BeerSmith4Adapter()
        common = adapter.recipe_to_common(_make_american_ipa())
        # 640 fl oz = 18.927 L (5 US gallons)
        assert abs(common.batch_size_l - 18.927) < 0.1

    def test_boil_size_floz_to_litres(self):
        adapter = BeerSmith4Adapter()
        common = adapter.recipe_to_common(_make_american_ipa())
        # 896 fl oz = 26.50 L (7 US gallons)
        assert common.boil_size_l is not None
        assert abs(common.boil_size_l - 26.50) < 0.1

    def test_fermentation_temp_f_to_c(self):
        adapter = BeerSmith4Adapter()
        common = adapter.recipe_to_common(_make_american_ipa())
        # 67°F = 19.44°C
        assert common.fermentation_temp_c is not None
        assert abs(common.fermentation_temp_c - 19.44) < 0.1

    def test_mash_temp_f_to_c(self):
        adapter = BeerSmith4Adapter()
        common = adapter.recipe_to_common(_make_american_ipa())
        # 152°F = 66.67°C
        assert common.mash_temp_c is not None
        assert abs(common.mash_temp_c - 66.67) < 0.1

    def test_color_srm_to_ebc(self):
        adapter = BeerSmith4Adapter()
        common = adapter.recipe_to_common(_make_american_ipa())
        # Avg SRM (6+14)/2 = 10 → EBC = 10 * 1.97 = 19.7
        assert common.color_ebc is not None
        assert abs(common.color_ebc - 19.7) < 0.5

    def test_grain_color_srm_to_ebc(self):
        adapter = BeerSmith4Adapter()
        common = adapter.recipe_to_common(_make_american_ipa())
        pale = common.grains[0]
        # 2 SRM → 3.94 EBC
        assert pale.color_ebc is not None
        assert abs(pale.color_ebc - 3.94) < 0.1


class TestHopUseParity:
    """Hop use categorisation must match the standard enum mapping."""

    def test_boil_hop(self):
        adapter = BeerSmith4Adapter()
        common = adapter.recipe_to_common(_make_american_ipa())
        centennial = common.hops[0]
        assert centennial.name == "Centennial"
        assert centennial.use == CommonHopUse.BOIL
        assert centennial.time_minutes == 60

    def test_dry_hop(self):
        adapter = BeerSmith4Adapter()
        common = adapter.recipe_to_common(_make_american_ipa())
        citra = common.hops[2]
        assert citra.name == "Citra"
        assert citra.use == CommonHopUse.DRY_HOP

    def test_first_wort_hop(self):
        adapter = BeerSmith4Adapter()
        common = adapter.recipe_to_common(_make_american_ipa())
        simcoe = common.hops[3]
        assert simcoe.name == "Simcoe"
        assert simcoe.use == CommonHopUse.FIRST_WORT

    def test_alpha_acid_preserved(self):
        adapter = BeerSmith4Adapter()
        common = adapter.recipe_to_common(_make_american_ipa())
        assert common.hops[0].alpha_acid == 10.0
        assert common.hops[2].alpha_acid == 12.0


class TestYeastParity:
    """Yeast normalisation must produce consistent form and attenuation."""

    def test_dry_yeast_form(self):
        adapter = BeerSmith4Adapter()
        common = adapter.recipe_to_common(_make_american_ipa())
        yeast = common.yeasts[0]
        assert yeast.form == CommonYeastForm.DRY

    def test_liquid_yeast_form(self):
        adapter = BeerSmith4Adapter()
        yeast = BS4Yeast(
            name="WLP001", lab="White Labs", form=0, min_attenuation=73.0, max_attenuation=80.0
        )
        ni = adapter._yeast_to_common(yeast)
        assert ni.form == CommonYeastForm.LIQUID

    def test_attenuation_is_average(self):
        adapter = BeerSmith4Adapter()
        common = adapter.recipe_to_common(_make_american_ipa())
        yeast = common.yeasts[0]
        # avg(73, 77) = 75
        assert yeast.attenuation == 75.0


class TestMiscParity:
    """Misc ingredient normalisation."""

    def test_misc_type_and_time(self):
        adapter = BeerSmith4Adapter()
        common = adapter.recipe_to_common(_make_american_ipa())
        miscs = [i for i in common.ingredients if i.type == IngredientType.MISC]
        assert len(miscs) == 1
        assert miscs[0].name == "Irish Moss"
        assert miscs[0].time_minutes == 15


class TestMeasuredValues:
    """OG/FG handling across measured-set flags."""

    def test_measured_og_fg_included(self):
        adapter = BeerSmith4Adapter()
        common = adapter.recipe_to_common(_make_american_ipa())
        assert common.og == 1.062
        assert common.fg == 1.010

    def test_unmeasured_og_fg_excluded(self):
        adapter = BeerSmith4Adapter()
        full = _make_american_ipa()
        # Clear measured-set flags
        full.recipe = full.recipe.model_copy(
            update={"og_measured_set": 0, "fg_measured_set": 0}
        )
        common = adapter.recipe_to_common(full)
        assert common.og is None
        assert common.fg is None


class TestIngredientCounts:
    """Ensure all recipe ingredients come through in normalised output."""

    def test_ingredient_type_counts(self):
        adapter = BeerSmith4Adapter()
        common = adapter.recipe_to_common(_make_american_ipa())
        assert len(common.grains) == 2
        assert len(common.hops) == 4
        assert len(common.yeasts) == 1
        assert len([i for i in common.ingredients if i.type == IngredientType.MISC]) == 1

    def test_total_ingredient_count(self):
        adapter = BeerSmith4Adapter()
        common = adapter.recipe_to_common(_make_american_ipa())
        # 2 grains + 4 hops + 1 yeast + 1 misc = 8
        assert len(common.ingredients) == 8
