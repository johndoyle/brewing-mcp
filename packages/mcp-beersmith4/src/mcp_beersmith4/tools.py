"""MCP tool definitions for BeerSmith 4.

BS4-native tool surface — designed around BS4's SQLite data model,
not constrained by BS3 XML-era tools.
"""

from __future__ import annotations

import json
import time

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


def _stringify_for_beersmith(obj: object) -> object:
    """Recursively convert all non-string primitives to strings.

    BeerSmith 4 serialises its SQLite embedded JSON with every numeric value
    stored as a JSON string (e.g. ``"F_G_AMOUNT":"134.1000000"``).  Writing
    native JSON number types causes BeerSmith's C++ parser to corrupt the heap
    and crash.  All data built by this server must pass through this function
    before being written to the database.

    Floats are formatted to 7 decimal places to match BeerSmith's own format.
    """
    if isinstance(obj, dict):
        return {k: _stringify_for_beersmith(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_stringify_for_beersmith(v) for v in obj]
    if isinstance(obj, bool):
        return "1" if obj else "0"
    if isinstance(obj, float):
        return f"{obj:.7f}"
    if isinstance(obj, int):
        return str(obj)
    return obj


# DB bookkeeping columns that must NOT appear in embedded profile JSON blobs
_EMBED_EXCLUDE = frozenset({"_PERMID_", "_MOD_", "_CLOUDID_", "_EXTRA_"})

# Schema IDs used by BeerSmith 4 to identify embedded JSON object types
_SCHEMA_EQUIPMENT = "7430"
_SCHEMA_STYLE     = "7428"
_SCHEMA_MASH      = "7434"
_SCHEMA_CARB      = "7478"
_SCHEMA_AGE       = "7482"


def _build_embedded_profile_json(row: dict, schema_id: str) -> str:
    """Build a native-format embedded profile JSON from a raw DB row.

    Produces ``{"_Schema_":"NNNN","F_X_...":"value",...}`` matching
    BeerSmith 4's own serialisation: ``_Schema_`` first, all numeric values
    as strings, no internal DB bookkeeping fields.

    All string values (including columns like ``steps`` that contain a JSON
    array as a string) are stored as escaped JSON strings, matching BeerSmith
    4's own serialisation: ``"steps":"[...]"``.  Empty-string values are
    stored as ``""``.
    """
    # Build as a list of raw key:value fragments so we can mix string and
    # non-string JSON values correctly.
    fragments: list[str] = [f'"_Schema_":{json.dumps(schema_id)}']
    for k, v in row.items():
        if k in _EMBED_EXCLUDE:
            continue
        key_json = json.dumps(k)
        if k == "steps":
            # BeerSmith serialises mash steps as a raw (unescaped) JSON array
            # embedded within a JSON string value.  Inner quotes are intentionally
            # NOT escaped, matching BeerSmith's own proprietary format which the
            # _fix_unescaped_json_array reader handles on the way back out.
            step_val = v if isinstance(v, str) else "[]"
            fragments.append(f'"steps":"{step_val}"')
        elif isinstance(v, str):
            fragments.append(f"{key_json}:{json.dumps(v)}")
        else:
            fragments.append(f"{key_json}:{json.dumps(_stringify_for_beersmith(v))}")
    return "{" + ",".join(fragments) + "}"


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

        # Build embedded JSON for profiles from raw DB rows.
        # We query the raw table rows (not Pydantic models) so that every
        # column present in the native DB is included and _Schema_ is added,
        # matching BeerSmith 4's own serialisation format exactly.
        # BeerSmith 4 crashes on startup if any profile blob is missing
        # _Schema_, so we always fall back to the first available profile.
        def _profile_row(table: str, name_col: str, name: str | None) -> dict | None:
            if name:
                row = db.query_one(
                    f"SELECT * FROM {table} WHERE {name_col} = ? COLLATE NOCASE",  # noqa: S608
                    (name,),
                )
                if row:
                    return row
            # Fall back to the first available profile in the table
            return db.query_one(f"SELECT * FROM {table} ORDER BY _PERMID_ LIMIT 1")  # noqa: S608

        equip_row = _profile_row("M_EQUIPMENT", "F_E_NAME", equipment_name)
        equipment_json = _build_embedded_profile_json(equip_row, _SCHEMA_EQUIPMENT) if equip_row else "{}"

        style_json = "{}"
        if style_name:
            row = db.query_one(
                "SELECT * FROM M_STYLE WHERE F_S_NAME = ? COLLATE NOCASE",
                (style_name,),
            )
            if row:
                style_json = _build_embedded_profile_json(row, _SCHEMA_STYLE)

        mash_row = _profile_row("M_MASH", "F_MH_NAME", mash_profile_name)
        if mash_row:
            # BeerSmith always overrides F_MASH_39 to 1 when embedding a mash
            # profile inside a recipe.  The M_MASH library stores 0 as a
            # template default; leaving it as 0 causes BeerSmith to treat the
            # profile as uninitialised and crash when the user tries to edit it.
            mash_row["F_MASH_39"] = 1
            # Populate tun parameters from the equipment profile so that mash
            # infusion calculations (temperatures, volumes) are accurate.
            if equip_row:
                mash_row["F_MH_TUN_VOL"] = equip_row.get("F_E_MASH_VOL", mash_row.get("F_MH_TUN_VOL", 0.0))
                mash_row["F_MH_TUN_MASS"] = equip_row.get("F_E_TUN_MASS", mash_row.get("F_MH_TUN_MASS", 0.0))
                mash_row["F_MH_TUN_HC"] = equip_row.get("F_E_TUN_SPECIFIC_HEAT", mash_row.get("F_MH_TUN_HC", 0.0))
                mash_row["F_MH_TUN_DEADSPACE"] = equip_row.get("F_E_TUN_DEADSPACE", mash_row.get("F_MH_TUN_DEADSPACE", 0.0))
            mash_json = _build_embedded_profile_json(mash_row, _SCHEMA_MASH)
        else:
            mash_json = "{}"

        carb_row = db.query_one("SELECT * FROM M_CARB ORDER BY _PERMID_ LIMIT 1")
        carb_json = _build_embedded_profile_json(carb_row, _SCHEMA_CARB) if carb_row else "{}"

        age_row = db.query_one("SELECT * FROM M_AGE ORDER BY _PERMID_ LIMIT 1")
        age_json = _build_embedded_profile_json(age_row, _SCHEMA_AGE) if age_row else "{}"

        # Build ingredients JSON array from raw library rows so we get ALL
        # native columns (Pydantic model omits F_G_USE_SET, F_G_ACID_PCT,
        # F_G_LATE_EXTRACT, F_G_CONVERT_GRAIN etc. — BeerSmith asserts on them).
        EXCLUDE_ING = _EMBED_EXCLUDE  # same set
        ingredients: list[str] = []
        try:
            for order, g in enumerate(json.loads(grains_json)):
                row = db.query_one(
                    "SELECT * FROM M_GRAIN WHERE F_G_NAME = ? COLLATE NOCASE",
                    (g.get("name", ""),),
                )
                if row:
                    amount = g.get("amount_oz", 0)
                    frags = [f'"_Schema_":"7406"']
                    for k, v in row.items():
                        if k in EXCLUDE_ING:
                            continue
                        kj = json.dumps(k)
                        if k == "F_G_AMOUNT":
                            frags.append(f"{kj}:\"{amount:.7f}\"")
                        elif k == "F_G_IN_RECIPE":
                            frags.append(f"{kj}:\"1\"")
                        elif k == "F_ORDER":
                            frags.append(f"{kj}:\"{order}\"")
                        elif isinstance(v, str):
                            frags.append(f"{kj}:{json.dumps(v)}")
                        else:
                            frags.append(f"{kj}:{json.dumps(_stringify_for_beersmith(v))}")
                    ingredients.append("{" + ",".join(frags) + "}")

            for order, h in enumerate(json.loads(hops_json)):
                row = db.query_one(
                    "SELECT * FROM M_HOPS WHERE F_H_NAME = ? COLLATE NOCASE",
                    (h.get("name", ""),),
                )
                if row:
                    frags = ['"_Schema_":"7403"']
                    for k, v in row.items():
                        if k in EXCLUDE_ING:
                            continue
                        kj = json.dumps(k)
                        if k == "F_H_AMOUNT":
                            amt = h.get("amount_oz", 0)
                            frags.append(f"{kj}:\"{float(amt):.7f}\"")
                        elif k == "F_H_BOIL_TIME":
                            t = h.get("time", 60)
                            frags.append(f"{kj}:\"{float(t):.7f}\"")
                        elif k == "F_H_USE":
                            frags.append(f"{kj}:\"{h.get('use', 0)}\"")
                        elif k == "F_H_IN_RECIPE":
                            frags.append(f"{kj}:\"1\"")
                        elif k == "F_ORDER":
                            frags.append(f"{kj}:\"{order}\"")
                        elif isinstance(v, str):
                            frags.append(f"{kj}:{json.dumps(v)}")
                        else:
                            frags.append(f"{kj}:{json.dumps(_stringify_for_beersmith(v))}")
                    ingredients.append("{" + ",".join(frags) + "}")

            if yeast_name:
                row = db.query_one(
                    "SELECT * FROM M_YEAST WHERE F_Y_NAME = ? COLLATE NOCASE",
                    (yeast_name,),
                )
                if row:
                    frags = ['"_Schema_":"7426"']
                    for k, v in row.items():
                        if k in EXCLUDE_ING:
                            continue
                        kj = json.dumps(k)
                        if k == "F_Y_IN_RECIPE":
                            frags.append(f"{kj}:\"1\"")
                        elif isinstance(v, str):
                            frags.append(f"{kj}:{json.dumps(v)}")
                        else:
                            frags.append(f"{kj}:{json.dumps(_stringify_for_beersmith(v))}")
                    ingredients.append("{" + ",".join(frags) + "}")

        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON input: {e}"}

        ingredients_json = "[" + ",".join(ingredients) + "]"

        # F_R_BASE_GRAIN is a fixed "Malt" efficiency-reference template required
        # by BeerSmith 4 in every recipe.  It is identical across all native recipes.
        base_grain_json = (
            '{"_Schema_":"7406","F_G_NAME":"Malt","F_G_ORIGIN":"","F_G_SUPPLIER":"",'
            '"F_G_TYPE":"0","F_G_USE":"0","F_G_USE_SET":"1","F_G_ACID_PCT":"0.0000000",'
            '"F_G_IN_RECIPE":"0","F_G_INVENTORY":"0.0000000","F_G_AMOUNT":"16.0000000",'
            '"F_G_COLOR":"3.0000000","F_G_YIELD":"75.0000000","F_G_LATE_EXTRACT":"0.0000000",'
            '"F_G_PERCENT":"0.0000000","F_G_NOT_FERMENTABLE":"0","_CLOUD_STATE_":"0",'
            '"F_ORDER":"0","F_G_COARSE_FINE_DIFF":"1.5000000","F_G_MOISTURE":"4.0000000",'
            '"F_G_DIASTATIC_POWER":"120.0000000","F_G_PROTEIN":"11.7000000",'
            '"F_G_IBU_GAL_PER_LB":"0.0000000","F_G_ADD_AFTER_BOIL":"0",'
            '"F_G_RECOMMEND_MASH":"0","F_G_MAX_IN_BATCH":"100.0000000","F_G_NOTES":"",'
            '"F_G_BOIL_TIME":"60.0000000","F_G_PRICE":"1.5000000","F_G_CONVERT_GRAIN":""}'
        )

        # F_R_WINE_COLOR controls the glass graphic shown in BeerSmith's UI.
        # Beer types (Extract=0, PartialMash=1, AllGrain=2) use -1 for a beer
        # glass; all other types default to 0 (wine-style glass).
        wine_color = -1 if recipe_type in (0, 1, 2) else 0

        recipe_data = {
            "F_R_NAME": name,
            "F_R_TYPE": recipe_type,
            "F_R_BREWER": brewer,
            "F_R_NOTES": notes,
            "F_R_FOLDER_NAME": "MCP Created",
            "F_R_DATE": int(time.time()),
            "F_R_VERSION": 1.0,
            "F_R_WINE_COLOR": wine_color,
        }

        try:
            permid = recipe_repo.create_recipe(
                recipe_data=recipe_data,
                equipment_json=equipment_json,
                style_json=style_json,
                mash_json=mash_json,
                carb_json=carb_json,
                age_json=age_json,
                base_grain_json=base_grain_json,
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
