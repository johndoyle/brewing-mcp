"""Tests for BS4 Pydantic models."""

from __future__ import annotations

import json

from mcp_beersmith4.enums import GrainType, HopForm, HopUse, MashStepType, YeastForm
from mcp_beersmith4.models import (
    BS4Equipment,
    BS4Grain,
    BS4Hop,
    BS4Mash,
    BS4MashStep,
    BS4Recipe,
    BS4RecipeFull,
    BS4Yeast,
)


class TestBS4Grain:
    def test_from_dict(self):
        data = {
            "_PERMID_": 1,
            "F_G_NAME": "Pale Malt",
            "F_G_AMOUNT": 160.0,
            "F_G_COLOR": 2.0,
            "F_G_TYPE": 0,
            "F_G_YIELD": 79.0,
        }
        g = BS4Grain.model_validate(data)
        assert g.name == "Pale Malt"
        assert g.amount == 160.0
        assert g.grain_type == GrainType.GRAIN
        assert g.amount_oz == 160.0
        assert abs(g.amount_g - 4535.9) < 1

    def test_defaults(self):
        g = BS4Grain()
        assert g.name == ""
        assert g.amount == 0.0

    def test_populate_by_name(self):
        g = BS4Grain(name="Test", amount=10.0)
        assert g.name == "Test"


class TestBS4Hop:
    def test_hop_use_enum(self):
        h = BS4Hop(use=0)
        assert h.hop_use == HopUse.BOIL

        h2 = BS4Hop(use=4)
        assert h2.hop_use == HopUse.AROMA

    def test_hop_form_enum(self):
        h = BS4Hop(form=0)
        assert h.hop_form == HopForm.PELLET


class TestBS4Yeast:
    def test_avg_attenuation(self):
        y = BS4Yeast(min_attenuation=73.0, max_attenuation=77.0)
        assert y.avg_attenuation == 75.0

    def test_yeast_form(self):
        y = BS4Yeast(form=1)
        assert y.yeast_form == YeastForm.DRY


class TestBS4Mash:
    def test_steps_from_json_string(self):
        steps_str = json.dumps([
            {"F_MS_NAME": "Mash In", "F_MS_TYPE": "0", "F_MS_STEP_TEMP": "152.0", "F_MS_STEP_TIME": "60.0"},
            {"F_MS_NAME": "Mash Out", "F_MS_TYPE": "1", "F_MS_STEP_TEMP": "168.0", "F_MS_STEP_TIME": "10.0"},
        ])
        m = BS4Mash(name="Single Infusion", steps_raw=steps_str)
        assert len(m.steps) == 2
        assert m.steps[0].name == "Mash In"
        assert m.steps[0].step_type == MashStepType.INFUSION
        assert m.steps[1].step_type == MashStepType.TEMPERATURE

    def test_steps_from_list(self):
        """Validator should handle list input (coerce to JSON string)."""
        steps_list = [
            {"F_MS_NAME": "Mash In", "F_MS_TYPE": "0", "F_MS_STEP_TEMP": "152.0"},
        ]
        m = BS4Mash.model_validate({"F_MH_NAME": "Test", "steps": steps_list})
        assert len(m.steps) == 1

    def test_empty_steps(self):
        m = BS4Mash(name="Empty")
        assert m.steps == []


class TestBS4Equipment:
    def test_batch_vol_litres(self):
        e = BS4Equipment(batch_vol=640.0)
        assert abs(e.batch_vol_l - 18.93) < 0.1


class TestBS4Recipe:
    def test_recipe_type(self):
        r = BS4Recipe(type=2)
        assert r.recipe_type.name == "ALL_GRAIN"

    def test_from_row_dict(self):
        row = {
            "_PERMID_": 100,
            "F_R_NAME": "Test IPA",
            "F_R_TYPE": 2,
            "F_R_OG_MEASURED": 1.065,
            "F_R_OG_MEASURED_SET": 1,
            "Ingredients": "[]",
        }
        r = BS4Recipe.model_validate(row)
        assert r.name == "Test IPA"
        assert r.og_measured == 1.065
        assert r.og_measured_set == 1


class TestBS4RecipeFull:
    def test_construction(self):
        recipe = BS4Recipe(name="Test", type=2)
        full = BS4RecipeFull(
            recipe=recipe,
            grains=[BS4Grain(name="Pale Malt", amount=160.0)],
            hops=[BS4Hop(name="Cascade", amount=2.0, alpha=5.5)],
            yeasts=[BS4Yeast(name="US-05")],
        )
        assert len(full.grains) == 1
        assert len(full.hops) == 1
        assert full.equipment is None
