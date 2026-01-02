"""
Tests for brewing-common data models.
"""

import pytest
from datetime import datetime
from brewing_common.models import (
    IngredientType,
    HopUse,
    YeastForm,
    NormalisedIngredient,
    Recipe,
    Batch,
    InventoryItem,
)


class TestNormalisedIngredient:
    """Tests for NormalisedIngredient model."""

    def test_create_grain(self):
        grain = NormalisedIngredient(
            name="Maris Otter",
            type=IngredientType.GRAIN,
            amount_g=5000.0,
            color_ebc=5.9,
            source_system="beersmith",
        )
        assert grain.name == "Maris Otter"
        assert grain.type == IngredientType.GRAIN
        assert grain.amount_g == 5000.0
        assert grain.color_ebc == 5.9

    def test_create_hop(self):
        hop = NormalisedIngredient(
            name="Cascade",
            type=IngredientType.HOP,
            amount_g=50.0,
            alpha_acid=5.5,
            use=HopUse.BOIL,
            time_minutes=60,
            source_system="brewfather",
        )
        assert hop.name == "Cascade"
        assert hop.alpha_acid == 5.5
        assert hop.use == HopUse.BOIL
        assert hop.time_minutes == 60

    def test_create_yeast(self):
        yeast = NormalisedIngredient(
            name="US-05",
            type=IngredientType.YEAST,
            amount_g=1.0,
            form=YeastForm.DRY,
            attenuation=81.0,
            source_system="grocy",
        )
        assert yeast.name == "US-05"
        assert yeast.form == YeastForm.DRY
        assert yeast.attenuation == 81.0

    def test_immutable(self):
        grain = NormalisedIngredient(
            name="Pale Malt",
            type=IngredientType.GRAIN,
            amount_g=4000.0,
            source_system="test",
        )
        with pytest.raises(Exception):  # Pydantic ValidationError
            grain.name = "Different Malt"


class TestRecipe:
    """Tests for Recipe model."""

    def test_create_recipe(self):
        recipe = Recipe(
            name="American IPA",
            style="IPA",
            batch_size_l=19.0,
            og=1.065,
            fg=1.012,
            ibu=65,
            abv=7.0,
            source_system="beersmith",
        )
        assert recipe.name == "American IPA"
        assert recipe.batch_size_l == 19.0

    def test_recipe_with_ingredients(self):
        ingredients = [
            NormalisedIngredient(
                name="2-Row",
                type=IngredientType.GRAIN,
                amount_g=5000.0,
                source_system="test",
            ),
            NormalisedIngredient(
                name="Cascade",
                type=IngredientType.HOP,
                amount_g=50.0,
                alpha_acid=5.5,
                use=HopUse.BOIL,
                source_system="test",
            ),
        ]
        recipe = Recipe(
            name="Test Recipe",
            batch_size_l=19.0,
            ingredients=ingredients,
            source_system="test",
        )
        assert len(recipe.ingredients) == 2
        assert len(recipe.grains) == 1
        assert len(recipe.hops) == 1

    def test_ingredient_properties(self):
        recipe = Recipe(
            name="Test",
            batch_size_l=19.0,
            ingredients=[
                NormalisedIngredient(
                    name="Grain1",
                    type=IngredientType.GRAIN,
                    amount_g=4000,
                    source_system="test",
                ),
                NormalisedIngredient(
                    name="Grain2",
                    type=IngredientType.GRAIN,
                    amount_g=500,
                    source_system="test",
                ),
                NormalisedIngredient(
                    name="Hop1",
                    type=IngredientType.HOP,
                    amount_g=30,
                    source_system="test",
                ),
                NormalisedIngredient(
                    name="Yeast1",
                    type=IngredientType.YEAST,
                    amount_g=1,
                    source_system="test",
                ),
            ],
            source_system="test",
        )
        assert len(recipe.grains) == 2
        assert len(recipe.hops) == 1
        assert len(recipe.yeasts) == 1


class TestBatch:
    """Tests for Batch model."""

    def test_create_batch(self):
        batch = Batch(
            name="Batch #42",
            recipe_name="American IPA",
            brew_date=datetime.now(),
            actual_og=1.062,
            status="fermenting",
            source_system="brewfather",
        )
        assert batch.name == "Batch #42"
        assert batch.status == "fermenting"


class TestInventoryItem:
    """Tests for InventoryItem model."""

    def test_create_inventory(self):
        ingredient = NormalisedIngredient(
            name="Cascade",
            type=IngredientType.HOP,
            amount_g=0,
            source_system="grocy",
        )
        inventory = InventoryItem(
            ingredient=ingredient,
            quantity_g=250.0,
            min_stock_g=100.0,
            source_system="grocy",
        )
        assert inventory.quantity_g == 250.0
        assert not inventory.is_low_stock

    def test_low_stock(self):
        ingredient = NormalisedIngredient(
            name="Cascade",
            type=IngredientType.HOP,
            amount_g=0,
            source_system="grocy",
        )
        inventory = InventoryItem(
            ingredient=ingredient,
            quantity_g=50.0,
            min_stock_g=100.0,
            source_system="grocy",
        )
        assert inventory.is_low_stock

    def test_expired(self):
        ingredient = NormalisedIngredient(
            name="Cascade",
            type=IngredientType.HOP,
            amount_g=0,
            source_system="grocy",
        )
        inventory = InventoryItem(
            ingredient=ingredient,
            quantity_g=100.0,
            best_before=datetime(2020, 1, 1),
            source_system="grocy",
        )
        assert inventory.is_expired
