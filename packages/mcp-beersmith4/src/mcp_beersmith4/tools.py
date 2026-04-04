"""MCP tool definitions for BeerSmith 4.

BS4-native tool surface — designed around BS4's SQLite data model,
not constrained by BS3 XML-era tools.
"""

from __future__ import annotations

import json

from fastmcp import FastMCP

from mcp_beersmith4.adapter import BeerSmith4Adapter
from mcp_beersmith4.config import get_config
from mcp_beersmith4.database import DatabaseManager
from mcp_beersmith4.repository import (
    FolderRepository,
    IngredientRepository,
    ProfileRepository,
    RecipeRepository,
)


def _get_db() -> DatabaseManager:
    config = get_config()
    return DatabaseManager(config)


def _get_recipe_repo() -> RecipeRepository:
    return RecipeRepository(_get_db())


def _get_ingredient_repo() -> IngredientRepository:
    return IngredientRepository(_get_db())


def _get_profile_repo() -> ProfileRepository:
    return ProfileRepository(_get_db())


def _get_folder_repo() -> FolderRepository:
    return FolderRepository(_get_db())


def _get_adapter() -> BeerSmith4Adapter:
    return BeerSmith4Adapter()


def register_tools(mcp: FastMCP) -> None:
    """Register all BeerSmith 4 MCP tools."""

    # ── Recipe tools ──────────────────────────────────────────────────

    @mcp.tool()
    def bs4_list_recipes(
        folder: str | None = None,
        search: str | None = None,
        recipe_type: int | None = None,
        source: str = "local",
    ) -> list[dict]:
        """List BeerSmith 4 recipes.

        Args:
            folder: Filter by folder name substring (optional).
            search: Filter by recipe name substring, case-insensitive (optional).
            recipe_type: Filter by type: 0=Extract, 1=PartialMash, 2=AllGrain,
                         3=Cider, 4=Mead, 5=Wine (optional).
            source: 'local' for M_RECIPE, 'cloud' for synced cloud recipes.

        Returns list of recipe summaries with name, type, brewer, and dates.
        """
        repo = _get_recipe_repo()
        recipes = repo.list_recipes(
            folder=folder, search=search, recipe_type=recipe_type, source=source
        )
        return [
            {
                "id": r.permid,
                "name": r.name,
                "type": r.recipe_type.name,
                "brewer": r.brewer,
                "folder": r.folder_name,
                "date": str(r.brew_date) if r.brew_date else None,
                "og_measured": r.og_measured if r.og_measured_set else None,
                "fg_measured": r.fg_measured if r.fg_measured_set else None,
            }
            for r in recipes
        ]

    @mcp.tool()
    def bs4_get_recipe(
        name_or_id: str,
        source: str = "local",
    ) -> dict | None:
        """Get a BeerSmith 4 recipe with full details including all ingredients.

        Args:
            name_or_id: Recipe name or numeric _PERMID_ ID.
            source: 'local' or 'cloud'.

        Returns full recipe with equipment, style, mash, ingredients, etc.
        """
        repo = _get_recipe_repo()
        full = repo.get_recipe(name_or_id, source=source)
        if not full:
            return None

        r = full.recipe
        result: dict = {
            "id": r.permid,
            "name": r.name,
            "type": r.recipe_type.name,
            "brewer": r.brewer,
            "folder": r.folder_name,
            "date": str(r.brew_date) if r.brew_date else None,
            "notes": r.notes,
            "og_measured": r.og_measured if r.og_measured_set else None,
            "fg_measured": r.fg_measured if r.fg_measured_set else None,
            "carb_vols": r.carb_vols,
        }

        if full.equipment:
            e = full.equipment
            result["equipment"] = {
                "name": e.name,
                "type": e.equip_type.name,
                "batch_vol_l": round(e.batch_vol_l, 2),
                "boil_time": e.boil_time,
                "efficiency": e.efficiency,
            }

        if full.style:
            s = full.style
            result["style"] = {
                "name": s.name,
                "category": s.category,
                "guide": s.guide,
                "og_range": [s.min_og, s.max_og],
                "fg_range": [s.min_fg, s.max_fg],
                "ibu_range": [s.min_ibu, s.max_ibu],
                "color_range_srm": [s.min_color, s.max_color],
                "abv_range": [s.min_abv, s.max_abv],
            }

        if full.mash:
            m = full.mash
            result["mash"] = {
                "name": m.name,
                "sparge_temp_f": m.sparge_temp,
                "ph": m.ph,
                "steps": [
                    {
                        "name": st.name,
                        "type": st.step_type.name,
                        "temp_f": st.step_temp,
                        "time_min": st.step_time,
                    }
                    for st in m.steps
                ],
            }

        result["grains"] = [
            {
                "name": g.name,
                "type": g.grain_type.name,
                "amount_oz": g.amount,
                "amount_g": round(g.amount_g, 1),
                "color_srm": g.color,
                "yield_pct": g.yield_pct,
                "percent": g.percent,
            }
            for g in full.grains
        ]

        result["hops"] = [
            {
                "name": h.name,
                "use": h.hop_use.name,
                "form": h.hop_form.name,
                "alpha": h.alpha,
                "amount_oz": h.amount,
                "amount_g": round(h.amount_g, 1),
                "time": h.boil_time,
            }
            for h in full.hops
        ]

        result["yeasts"] = [
            {
                "name": y.name,
                "lab": y.lab,
                "product_id": y.product_id,
                "type": y.yeast_type.name,
                "form": y.yeast_form.name,
                "attenuation": y.avg_attenuation,
            }
            for y in full.yeasts
        ]

        result["miscs"] = [
            {
                "name": m.name,
                "type": m.misc_type.name,
                "amount": m.amount,
                "time": m.time,
                "use": m.misc_use.name,
            }
            for m in full.miscs
        ]

        if full.waters:
            result["waters"] = [
                {
                    "name": w.name,
                    "amount_floz": w.amount,
                    "calcium": w.calcium,
                    "magnesium": w.magnesium,
                    "sodium": w.sodium,
                    "sulfate": w.sulfate,
                    "chloride": w.chloride,
                    "bicarb": w.bicarb,
                    "ph": w.ph,
                }
                for w in full.waters
            ]

        if full.age:
            a = full.age
            result["fermentation"] = {
                "name": a.name,
                "primary_temp_f": a.prim_temp,
                "primary_days": a.prim_days,
                "secondary_temp_f": a.sec_temp,
                "secondary_days": a.sec_days,
            }

        if full.carb:
            c = full.carb
            result["carbonation"] = {
                "name": c.name,
                "type": c.type,
                "carb_rate": c.carb_rate,
            }

        return result

    @mcp.tool()
    def bs4_search_recipes(
        query: str | None = None,
        ingredient: str | None = None,
        style: str | None = None,
        source: str = "local",
    ) -> list[dict]:
        """Search BeerSmith 4 recipes by name, ingredient, and/or style.

        At least one search criterion must be provided.

        Args:
            query: Search by recipe name substring (optional).
            ingredient: Search for recipes containing this ingredient (optional).
            style: Search for recipes matching this style name (optional).
            source: 'local' or 'cloud'.

        Returns list of matching recipe summaries.
        """
        if not any([query, ingredient, style]):
            return [{"error": "At least one search criterion required"}]

        repo = _get_recipe_repo()
        results = repo.search_recipes(
            query=query, ingredient=ingredient, style=style, source=source
        )
        return [
            {
                "id": full.recipe.permid,
                "name": full.recipe.name,
                "type": full.recipe.recipe_type.name,
                "style": full.style.name if full.style else None,
                "grains": [g.name for g in full.grains],
                "hops": [h.name for h in full.hops],
                "yeasts": [y.name for y in full.yeasts],
            }
            for full in results
        ]

    @mcp.tool()
    def bs4_get_recipe_normalised(
        name_or_id: str,
        source: str = "local",
    ) -> dict | None:
        """Get a BeerSmith 4 recipe in brewing-common normalised format.

        Returns the recipe converted to metric units with standardised
        ingredient types, suitable for cross-system comparison.

        Args:
            name_or_id: Recipe name or numeric _PERMID_ ID.
            source: 'local' or 'cloud'.
        """
        repo = _get_recipe_repo()
        full = repo.get_recipe(name_or_id, source=source)
        if not full:
            return None

        adapter = _get_adapter()
        common = adapter.recipe_to_common(full)
        return common.model_dump()

    # ── Ingredient library tools ──────────────────────────────────────

    @mcp.tool()
    def bs4_list_ingredients(
        ingredient_type: str = "grain",
        search: str | None = None,
    ) -> list[dict]:
        """List ingredients from BeerSmith 4 ingredient library.

        Args:
            ingredient_type: One of 'grain', 'hop', 'yeast', 'misc', 'water'.
            search: Filter by name substring (optional).

        Returns list of ingredients with key properties.
        """
        repo = _get_ingredient_repo()

        if ingredient_type == "grain":
            items = repo.list_grains(search)
            return [
                {
                    "id": g.permid,
                    "name": g.name,
                    "origin": g.origin,
                    "type": g.grain_type.name,
                    "color_srm": g.color,
                    "yield_pct": g.yield_pct,
                    "supplier": g.supplier,
                }
                for g in items
            ]
        elif ingredient_type == "hop":
            items = repo.list_hops(search)
            return [
                {
                    "id": h.permid,
                    "name": h.name,
                    "origin": h.origin,
                    "alpha": h.alpha,
                    "type": h.hop_type.name,
                    "form": h.hop_form.name,
                }
                for h in items
            ]
        elif ingredient_type == "yeast":
            items = repo.list_yeasts(search)
            return [
                {
                    "id": y.permid,
                    "name": y.name,
                    "lab": y.lab,
                    "product_id": y.product_id,
                    "type": y.yeast_type.name,
                    "form": y.yeast_form.name,
                    "attenuation": y.avg_attenuation,
                }
                for y in items
            ]
        elif ingredient_type == "misc":
            items = repo.list_miscs(search)
            return [
                {
                    "id": m.permid,
                    "name": m.name,
                    "type": m.misc_type.name,
                }
                for m in items
            ]
        elif ingredient_type == "water":
            items = repo.list_waters(search)
            return [
                {
                    "id": w.permid,
                    "name": w.name,
                    "calcium": w.calcium,
                    "sulfate": w.sulfate,
                    "chloride": w.chloride,
                }
                for w in items
            ]
        else:
            return [{"error": f"Unknown type '{ingredient_type}'. Use: grain, hop, yeast, misc, water"}]

    @mcp.tool()
    def bs4_get_ingredient(
        name_or_id: str,
        ingredient_type: str = "grain",
    ) -> dict | None:
        """Get detailed info for a specific ingredient from the library.

        Args:
            name_or_id: Ingredient name or numeric _PERMID_ ID.
            ingredient_type: One of 'grain', 'hop', 'yeast'.
        """
        repo = _get_ingredient_repo()

        if ingredient_type == "grain":
            g = repo.get_grain(name_or_id)
            return g.model_dump(by_alias=False) if g else None
        elif ingredient_type == "hop":
            h = repo.get_hop(name_or_id)
            return h.model_dump(by_alias=False) if h else None
        elif ingredient_type == "yeast":
            y = repo.get_yeast(name_or_id)
            return y.model_dump(by_alias=False) if y else None
        return None

    # ── Profile tools ─────────────────────────────────────────────────

    @mcp.tool()
    def bs4_list_equipment(search: str | None = None) -> list[dict]:
        """List equipment profiles from BeerSmith 4.

        Args:
            search: Filter by name substring (optional).
        """
        repo = _get_profile_repo()
        return [
            {
                "id": e.permid,
                "name": e.name,
                "type": e.equip_type.name,
                "batch_vol_l": round(e.batch_vol_l, 2),
                "boil_time": e.boil_time,
                "efficiency": e.efficiency,
            }
            for e in repo.list_equipment(search)
        ]

    @mcp.tool()
    def bs4_list_styles(search: str | None = None) -> list[dict]:
        """List beer styles from BeerSmith 4.

        Args:
            search: Filter by name substring (optional).
        """
        repo = _get_profile_repo()
        return [
            {
                "id": s.permid,
                "name": s.name,
                "category": s.category,
                "guide": s.guide,
                "type": s.style_type.name,
                "og_range": [s.min_og, s.max_og],
                "ibu_range": [s.min_ibu, s.max_ibu],
            }
            for s in repo.list_styles(search)
        ]

    @mcp.tool()
    def bs4_list_mash_profiles(search: str | None = None) -> list[dict]:
        """List mash profiles from BeerSmith 4.

        Args:
            search: Filter by name substring (optional).
        """
        repo = _get_profile_repo()
        return [
            {
                "id": m.permid,
                "name": m.name,
                "sparge_temp_f": m.sparge_temp,
                "ph": m.ph,
                "steps": [
                    {
                        "name": st.name,
                        "type": st.step_type.name,
                        "temp_f": st.step_temp,
                        "time_min": st.step_time,
                    }
                    for st in m.steps
                ],
            }
            for m in repo.list_mash_profiles(search)
        ]

    # ── Folder tools ──────────────────────────────────────────────────

    @mcp.tool()
    def bs4_list_folders(source: str = "cloud") -> list[dict]:
        """List recipe folders in BeerSmith 4.

        Args:
            source: 'local' for M_FOLDER, 'cloud' for M_CLOUD_FOLDER.

        Returns hierarchical folder tree.
        """
        repo = _get_folder_repo()
        return repo.get_folder_tree(source=source)

    # ── Write tools ───────────────────────────────────────────────────

    @mcp.tool()
    def bs4_create_recipe(
        name: str,
        recipe_type: int = 2,
        equipment_name: str | None = None,
        style_name: str | None = None,
        mash_profile_name: str | None = None,
        grains_json: str = "[]",
        hops_json: str = "[]",
        yeast_name: str | None = None,
        brewer: str = "",
        notes: str = "",
        dry_run: bool = False,
    ) -> dict:
        """Create a new recipe in BeerSmith 4.

        Write access must be enabled (BEERSMITH4_READ_ONLY=false).
        A backup is created automatically before writing.

        Args:
            name: Recipe name.
            recipe_type: 0=Extract, 1=PartialMash, 2=AllGrain, 3=Cider, 4=Mead, 5=Wine.
            equipment_name: Equipment profile name to embed (optional).
            style_name: Beer style name to embed (optional).
            mash_profile_name: Mash profile name to embed (optional).
            grains_json: JSON array of grains: [{"name": "...", "amount_oz": ...}].
            hops_json: JSON array of hops: [{"name": "...", "amount_oz": ..., "alpha": ..., "time": ..., "use": 0}].
            yeast_name: Yeast name to add (optional).
            brewer: Brewer name (optional).
            notes: Recipe notes (optional).
            dry_run: If true, validate the write without persisting changes.

        Returns dict with new recipe ID and confirmation.
        """
        config = get_config()
        db = DatabaseManager(config)
        recipe_repo = RecipeRepository(db)
        profile_repo = ProfileRepository(db)
        ingredient_repo = IngredientRepository(db)

        # Build embedded JSON for profiles
        equipment_json = "{}"
        if equipment_name:
            equip = profile_repo.get_equipment(equipment_name)
            if equip:
                equipment_json = equip.model_dump_json(by_alias=True)

        style_json = "{}"
        if style_name:
            sty = profile_repo.get_style(style_name)
            if sty:
                style_json = sty.model_dump_json(by_alias=True)

        mash_json = "{}"
        if mash_profile_name:
            mash = profile_repo.get_mash_profile(mash_profile_name)
            if mash:
                mash_json = mash.model_dump_json(by_alias=True)

        # Build ingredients JSON array
        ingredients: list[dict] = []
        try:
            for g in json.loads(grains_json):
                lib_grain = ingredient_repo.get_grain(g.get("name", ""))
                if lib_grain:
                    d = json.loads(lib_grain.model_dump_json(by_alias=True))
                    d["_Schema_"] = "7406"
                    d["F_G_AMOUNT"] = str(g.get("amount_oz", 0))
                    d["F_G_IN_RECIPE"] = "1"
                    ingredients.append(d)

            for h in json.loads(hops_json):
                lib_hop = ingredient_repo.get_hop(h.get("name", ""))
                if lib_hop:
                    d = json.loads(lib_hop.model_dump_json(by_alias=True))
                    d["_Schema_"] = "7403"
                    d["F_H_AMOUNT"] = str(h.get("amount_oz", 0))
                    d["F_H_ALPHA"] = str(h.get("alpha", lib_hop.alpha))
                    d["F_H_BOIL_TIME"] = str(h.get("time", 60))
                    d["F_H_USE"] = str(h.get("use", 0))
                    d["F_H_IN_RECIPE"] = "1"
                    ingredients.append(d)

            if yeast_name:
                lib_yeast = ingredient_repo.get_yeast(yeast_name)
                if lib_yeast:
                    d = json.loads(lib_yeast.model_dump_json(by_alias=True))
                    d["_Schema_"] = "7426"
                    d["F_Y_IN_RECIPE"] = "1"
                    ingredients.append(d)

        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON input: {e}"}

        ingredients_json = json.dumps(ingredients)

        recipe_data = {
            "F_R_NAME": name,
            "F_R_TYPE": recipe_type,
            "F_R_BREWER": brewer,
            "F_R_NOTES": notes,
            "F_R_FOLDER_NAME": "MCP Created",
        }

        try:
            permid = recipe_repo.create_recipe(
                recipe_data=recipe_data,
                equipment_json=equipment_json,
                style_json=style_json,
                mash_json=mash_json,
                ingredients_json=ingredients_json,
                dry_run=dry_run,
            )
            if dry_run:
                return {
                    "success": True,
                    "dry_run": True,
                    "id": permid,
                    "name": name,
                    "message": f"Dry run: recipe '{name}' would be created with ID {permid} (not persisted)",
                }
            return {
                "success": True,
                "id": permid,
                "name": name,
                "message": f"Recipe '{name}' created with ID {permid}",
            }
        except PermissionError as e:
            return {"error": str(e)}
        except RuntimeError as e:
            return {"error": str(e)}

    @mcp.tool()
    def bs4_update_recipe(
        name_or_id: str,
        updates_json: str,
        dry_run: bool = False,
    ) -> dict:
        """Update an existing BeerSmith 4 recipe.

        Write access must be enabled (BEERSMITH4_READ_ONLY=false).
        A backup is created automatically before writing.

        Args:
            name_or_id: Recipe name or numeric _PERMID_ ID.
            updates_json: JSON object of fields to update.
                         Supported: F_R_NAME, F_R_BREWER, F_R_NOTES,
                         F_R_TYPE, Ingredients (full JSON array),
                         F_R_EQUIPMENT, F_R_STYLE, F_R_MASH (raw JSON).
            dry_run: If true, validate the write without persisting changes.

        Returns confirmation dict.
        """
        try:
            updates = json.loads(updates_json)
        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON: {e}"}

        # Safety: only allow known fields
        allowed = {
            "F_R_NAME",
            "F_R_BREWER",
            "F_R_NOTES",
            "F_R_TYPE",
            "F_R_DESCRIPTION",
            "F_R_FOLDER_NAME",
            "F_R_RATING",
            "F_R_OG_MEASURED",
            "F_R_FG_MEASURED",
            "F_R_OG_MEASURED_SET",
            "F_R_FG_MEASURED_SET",
            "F_R_CARB_VOLS",
            "Ingredients",
            "F_R_EQUIPMENT",
            "F_R_STYLE",
            "F_R_MASH",
            "F_R_CARB",
            "F_R_AGE",
        }
        filtered = {k: v for k, v in updates.items() if k in allowed}
        if not filtered:
            return {"error": f"No valid fields. Allowed: {sorted(allowed)}"}

        config = get_config()
        db = DatabaseManager(config)
        repo = RecipeRepository(db)

        # Resolve name to ID if needed
        existing = repo.get_recipe(name_or_id)
        if not existing:
            return {"error": f"Recipe '{name_or_id}' not found"}

        try:
            success = repo.update_recipe(existing.recipe.permid, filtered, dry_run=dry_run)
            if success:
                if dry_run:
                    return {
                        "success": True,
                        "dry_run": True,
                        "id": existing.recipe.permid,
                        "updated_fields": list(filtered.keys()),
                        "message": "Dry run: update validated but not persisted",
                    }
                return {
                    "success": True,
                    "id": existing.recipe.permid,
                    "updated_fields": list(filtered.keys()),
                }
            return {"error": "No rows updated"}
        except PermissionError as e:
            return {"error": str(e)}
        except RuntimeError as e:
            return {"error": str(e)}
