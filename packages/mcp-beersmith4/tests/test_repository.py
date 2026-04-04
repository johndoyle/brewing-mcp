"""Tests for repository layer."""

from __future__ import annotations

import pytest

from mcp_beersmith4.config import BeerSmith4Config
from mcp_beersmith4.database import DatabaseManager
from mcp_beersmith4.repository import (
    FolderRepository,
    IngredientRepository,
    ProfileRepository,
    RecipeRepository,
    _fix_unescaped_json_array,
)


@pytest.fixture()
def recipe_repo(db: DatabaseManager) -> RecipeRepository:
    return RecipeRepository(db)


@pytest.fixture()
def ingredient_repo(db: DatabaseManager) -> IngredientRepository:
    return IngredientRepository(db)


@pytest.fixture()
def profile_repo(db: DatabaseManager) -> ProfileRepository:
    return ProfileRepository(db)


@pytest.fixture()
def folder_repo(db: DatabaseManager) -> FolderRepository:
    return FolderRepository(db)


class TestRecipeRepository:
    def test_list_recipes(self, recipe_repo: RecipeRepository):
        recipes = recipe_repo.list_recipes()
        assert len(recipes) == 1
        assert recipes[0].name == "Test IPA"

    def test_list_recipes_search(self, recipe_repo: RecipeRepository):
        assert len(recipe_repo.list_recipes(search="IPA")) == 1
        assert len(recipe_repo.list_recipes(search="Stout")) == 0

    def test_get_recipe_by_id(self, recipe_repo: RecipeRepository):
        full = recipe_repo.get_recipe(100)
        assert full is not None
        assert full.recipe.name == "Test IPA"
        assert len(full.grains) == 2
        assert len(full.hops) == 2
        assert len(full.yeasts) == 1

    def test_get_recipe_by_name(self, recipe_repo: RecipeRepository):
        full = recipe_repo.get_recipe("Test IPA")
        assert full is not None
        assert full.recipe.permid == 100

    def test_get_recipe_not_found(self, recipe_repo: RecipeRepository):
        assert recipe_repo.get_recipe("Nonexistent") is None

    def test_get_recipe_parses_equipment(self, recipe_repo: RecipeRepository):
        full = recipe_repo.get_recipe(100)
        assert full is not None
        assert full.equipment is not None
        assert full.equipment.name == "My Brew Kettle (5 Gal)"

    def test_get_recipe_parses_style(self, recipe_repo: RecipeRepository):
        full = recipe_repo.get_recipe(100)
        assert full is not None
        assert full.style is not None
        assert full.style.name == "American IPA"

    def test_get_recipe_parses_mash(self, recipe_repo: RecipeRepository):
        full = recipe_repo.get_recipe(100)
        assert full is not None
        assert full.mash is not None
        assert full.mash.name == "Single Infusion, Medium Body"
        steps = full.mash.steps
        assert len(steps) >= 1
        assert steps[0].name == "Mash In"

    def test_get_recipe_parses_age(self, recipe_repo: RecipeRepository):
        full = recipe_repo.get_recipe(100)
        assert full is not None
        assert full.age is not None
        assert full.age.name == "Ale, Two Stage"

    def test_recipe_ingredient_types(self, recipe_repo: RecipeRepository):
        full = recipe_repo.get_recipe(100)
        assert full is not None
        assert full.grains[0].name == "Pale Malt (2 Row) US"
        assert full.hops[0].name == "Cascade"
        assert full.yeasts[0].name == "Safale US-05"

    def test_search_recipes_by_ingredient(self, recipe_repo: RecipeRepository):
        results = recipe_repo.search_recipes(ingredient="Cascade")
        assert len(results) == 1
        assert results[0].recipe.name == "Test IPA"

    def test_search_recipes_by_style(self, recipe_repo: RecipeRepository):
        results = recipe_repo.search_recipes(style="IPA")
        assert len(results) == 1

    def test_create_recipe(self, recipe_repo: RecipeRepository):
        permid = recipe_repo.create_recipe(
            recipe_data={"F_R_NAME": "New Recipe", "F_R_TYPE": 2},
        )
        assert permid > 0
        full = recipe_repo.get_recipe(permid)
        assert full is not None
        assert full.recipe.name == "New Recipe"

    def test_update_recipe(self, recipe_repo: RecipeRepository):
        success = recipe_repo.update_recipe(100, {"F_R_NOTES": "Updated notes"})
        assert success
        full = recipe_repo.get_recipe(100)
        assert full is not None
        assert full.recipe.notes == "Updated notes"


class TestIngredientRepository:
    def test_list_grains(self, ingredient_repo: IngredientRepository):
        grains = ingredient_repo.list_grains()
        assert len(grains) == 3

    def test_list_grains_search(self, ingredient_repo: IngredientRepository):
        grains = ingredient_repo.list_grains(search="Pale")
        assert len(grains) == 1
        assert grains[0].name == "Pale Malt (2 Row) US"

    def test_get_grain_by_id(self, ingredient_repo: IngredientRepository):
        g = ingredient_repo.get_grain(1)
        assert g is not None
        assert g.name == "Pale Malt (2 Row) US"

    def test_get_grain_by_name(self, ingredient_repo: IngredientRepository):
        g = ingredient_repo.get_grain("Crystal 60L")
        assert g is not None
        assert g.color == 60.0

    def test_list_hops(self, ingredient_repo: IngredientRepository):
        hops = ingredient_repo.list_hops()
        assert len(hops) == 3

    def test_get_hop(self, ingredient_repo: IngredientRepository):
        h = ingredient_repo.get_hop("Cascade")
        assert h is not None
        assert h.alpha == 5.5

    def test_list_yeasts(self, ingredient_repo: IngredientRepository):
        yeasts = ingredient_repo.list_yeasts()
        assert len(yeasts) == 2

    def test_get_yeast(self, ingredient_repo: IngredientRepository):
        y = ingredient_repo.get_yeast("Safale US-05")
        assert y is not None
        assert y.lab == "Fermentis"


class TestProfileRepository:
    def test_list_equipment(self, profile_repo: ProfileRepository):
        eq = profile_repo.list_equipment()
        assert len(eq) == 1
        assert eq[0].name == "My Brew Kettle (5 Gal)"

    def test_get_equipment(self, profile_repo: ProfileRepository):
        e = profile_repo.get_equipment("My Brew Kettle (5 Gal)")
        assert e is not None
        assert e.efficiency == 72.0

    def test_list_styles(self, profile_repo: ProfileRepository):
        styles = profile_repo.list_styles()
        assert len(styles) == 1

    def test_list_mash_profiles(self, profile_repo: ProfileRepository):
        mashes = profile_repo.list_mash_profiles()
        assert len(mashes) == 1
        assert mashes[0].name == "Single Infusion, Medium Body"
        assert len(mashes[0].steps) == 2


class TestFolderRepository:
    def test_list_cloud_folders(self, folder_repo: FolderRepository):
        folders = folder_repo.list_cloud_folders()
        assert len(folders) == 3

    def test_folder_tree(self, folder_repo: FolderRepository):
        tree = folder_repo.get_folder_tree(source="cloud")
        assert len(tree) == 1  # "My Recipes" is the root
        root = tree[0]
        assert root["name"] == "My Recipes"
        assert len(root["children"]) == 2
        child_names = {c["name"] for c in root["children"]}
        assert child_names == {"IPAs", "Stouts"}


class TestFixUnescapedJsonArray:
    """Tests for _fix_unescaped_json_array handling BeerSmith's raw embedded arrays."""

    def test_already_valid_json(self):
        import json
        valid = json.dumps({"F_MH_NAME": "Test", "steps": [{"name": "a"}]})
        assert _fix_unescaped_json_array(valid) == valid

    def test_no_steps_field(self):
        raw = '{"F_MH_NAME":"Test","F_MH_PH":"5.4"}'
        assert _fix_unescaped_json_array(raw) == raw

    def test_fixes_unescaped_steps(self):
        import json
        # BeerSmith format: steps value has unescaped inner quotes
        raw = (
            '{"F_MH_NAME":"Single Infusion",'
            '"steps":"[{\\"_Schema_\\":\\"7432\\",\\"F_MS_NAME\\":\\"Mash In\\"}]",'  # noqa: this won't work
            '"F_MH_PH":"5.4"}'
        )
        # Actually build the broken format BeerSmith produces:
        # The inner array quotes are NOT escaped
        raw = (
            '{"F_MH_NAME":"Single Infusion",'
            '"steps":"[{"_Schema_":"7432","F_MS_NAME":"Mash In","F_MS_TYPE":"0"}]",'
            '"F_MH_PH":"5.4"}'
        )
        fixed = _fix_unescaped_json_array(raw)
        data = json.loads(fixed)
        assert data["F_MH_NAME"] == "Single Infusion"
        assert data["F_MH_PH"] == "5.4"
        assert len(data["steps"]) == 1
        assert data["steps"][0]["F_MS_NAME"] == "Mash In"

    def test_fixes_multiple_steps(self):
        import json
        raw = (
            '{"F_MH_NAME":"Two Step",'
            '"steps":"[{"_Schema_":"7432","F_MS_NAME":"Saccharification","F_MS_TYPE":"0"},'
            '{"_Schema_":"7432","F_MS_NAME":"Mash Out","F_MS_TYPE":"2"}]",'
            '"F_MH_PH":"5.2"}'
        )
        fixed = _fix_unescaped_json_array(raw)
        data = json.loads(fixed)
        assert len(data["steps"]) == 2
        assert data["steps"][0]["F_MS_NAME"] == "Saccharification"
        assert data["steps"][1]["F_MS_NAME"] == "Mash Out"
