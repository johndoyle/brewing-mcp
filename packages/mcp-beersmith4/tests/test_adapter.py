"""Tests for BeerSmith4Adapter (BS4 → brewing-common conversion)."""

from __future__ import annotations

from brewing_common.models import HopUse as CommonHopUse, IngredientType, YeastForm as CommonYeastForm

from mcp_beersmith4.adapter import BeerSmith4Adapter
from mcp_beersmith4.models import (
    BS4Age,
    BS4Equipment,
    BS4Grain,
    BS4Hop,
    BS4Mash,
    BS4Recipe,
    BS4RecipeFull,
    BS4Style,
    BS4Yeast,
)


def _make_full_recipe() -> BS4RecipeFull:
    recipe = BS4Recipe(
        permid=100,
        name="Test IPA",
        type=2,
        og_measured=1.065,
        fg_measured=1.012,
        og_measured_set=1,
        fg_measured_set=1,
        notes="Test notes",
    )
    equipment = BS4Equipment(
        name="My Kettle",
        batch_vol=640.0,  # fl oz
        boil_vol=896.0,
        boil_time=60.0,
        efficiency=72.0,
    )
    style = BS4Style(
        name="American IPA",
        guide="BJCP 2021",
        min_color=6.0,
        max_color=14.0,
    )
    age = BS4Age(
        name="Ale, Two Stage",
        prim_temp=67.0,  # °F
        prim_days=14.0,
    )
    return BS4RecipeFull(
        recipe=recipe,
        equipment=equipment,
        style=style,
        age=age,
        grains=[
            BS4Grain(name="Pale Malt", amount=176.0, color=2.0, yield_pct=79.0),
            BS4Grain(name="Crystal 60L", amount=16.0, color=60.0, yield_pct=74.0),
        ],
        hops=[
            BS4Hop(name="Cascade", amount=2.0, alpha=5.5, boil_time=60.0, use=0),
            BS4Hop(name="Citra", amount=1.5, alpha=12.0, boil_time=0.0, use=4),
        ],
        yeasts=[
            BS4Yeast(name="US-05", form=1, min_attenuation=73.0, max_attenuation=77.0),
        ],
    )


class TestBeerSmith4Adapter:
    def test_recipe_to_common(self):
        adapter = BeerSmith4Adapter()
        full = _make_full_recipe()
        common = adapter.recipe_to_common(full)

        assert common.name == "Test IPA"
        assert common.source_system == "beersmith4"
        assert common.source_id == "100"
        assert common.style == "American IPA"
        assert common.style_guide == "BJCP 2021"
        assert common.notes == "Test notes"

    def test_batch_size_conversion(self):
        adapter = BeerSmith4Adapter()
        full = _make_full_recipe()
        common = adapter.recipe_to_common(full)
        # 640 fl oz ~ 18.93 L
        assert abs(common.batch_size_l - 18.93) < 0.1

    def test_grain_conversion(self):
        adapter = BeerSmith4Adapter()
        full = _make_full_recipe()
        common = adapter.recipe_to_common(full)
        grains = common.grains
        assert len(grains) == 2
        assert grains[0].name == "Pale Malt"
        assert grains[0].type == IngredientType.GRAIN
        # 176 oz * 28.35 g/oz ≈ 4989.5 g
        assert abs(grains[0].amount_g - 4989.5) < 5

    def test_hop_use_mapping(self):
        adapter = BeerSmith4Adapter()
        full = _make_full_recipe()
        common = adapter.recipe_to_common(full)
        hops = common.hops
        assert len(hops) == 2
        assert hops[0].use == CommonHopUse.BOIL
        assert hops[1].use == CommonHopUse.AROMA

    def test_yeast_form_mapping(self):
        adapter = BeerSmith4Adapter()
        full = _make_full_recipe()
        common = adapter.recipe_to_common(full)
        yeasts = common.yeasts
        assert len(yeasts) == 1
        assert yeasts[0].form == CommonYeastForm.DRY
        assert yeasts[0].attenuation == 75.0

    def test_fermentation_temp(self):
        adapter = BeerSmith4Adapter()
        full = _make_full_recipe()
        common = adapter.recipe_to_common(full)
        # 67°F = 19.44°C
        assert common.fermentation_temp_c is not None
        assert abs(common.fermentation_temp_c - 19.44) < 0.1

    def test_og_fg_from_measured(self):
        adapter = BeerSmith4Adapter()
        full = _make_full_recipe()
        common = adapter.recipe_to_common(full)
        assert common.og == 1.065
        assert common.fg == 1.012

    def test_library_grain_to_common(self):
        adapter = BeerSmith4Adapter()
        grain = BS4Grain(permid=1, name="Pale Malt", color=2.0)
        ni = adapter.grain_to_common(grain)
        assert ni.amount_g == 0.0
        assert ni.type == IngredientType.GRAIN

    def test_library_hop_to_common(self):
        adapter = BeerSmith4Adapter()
        hop = BS4Hop(permid=1, name="Cascade", alpha=5.5)
        ni = adapter.hop_to_common(hop)
        assert ni.amount_g == 0.0
        assert ni.alpha_acid == 5.5
