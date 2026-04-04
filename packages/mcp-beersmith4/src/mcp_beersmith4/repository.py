"""Data access layer for BeerSmith 4 databases.

Queries SQLite tables and embedded JSON, returning typed BS4 models.
"""

from __future__ import annotations

import json
import time
from typing import Any

from mcp_beersmith4.database import DatabaseManager
from mcp_beersmith4.enums import (
    SCHEMA_GRAIN,
    SCHEMA_HOP,
    SCHEMA_MISC,
    SCHEMA_WATER,
    SCHEMA_YEAST,
)
from mcp_beersmith4.models import (
    BS4Age,
    BS4Carb,
    BS4Equipment,
    BS4Folder,
    BS4Grain,
    BS4Hop,
    BS4Mash,
    BS4Misc,
    BS4Recipe,
    BS4RecipeFull,
    BS4Style,
    BS4Water,
    BS4Yeast,
)


def _fix_unescaped_json_array(raw: str, key: str = "steps") -> str:
    """Fix BeerSmith's unescaped embedded JSON arrays.

    BeerSmith 4 serialises mash steps as an unescaped JSON array inside the
    mash JSON string, e.g.  ``"steps":"[{\"_Schema_\":...}]"`` — except the
    inner quotes are **not** escaped.  This makes the outer JSON invalid.

    We locate the ``"<key>":"[`` pattern, track bracket depth to find the
    matching ``]"``, extract the inner array, and splice a valid placeholder
    into the outer JSON so both can be parsed independently.
    """
    marker = f'"{key}":"'
    start = raw.find(marker)
    if start == -1:
        return raw  # field not present, nothing to fix

    array_start = start + len(marker)  # points at '['
    if array_start >= len(raw) or raw[array_start] != "[":
        return raw

    # Walk through tracking bracket depth (no [ or ] in BeerSmith values)
    depth = 0
    pos = array_start
    while pos < len(raw):
        ch = raw[pos]
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                break
        pos += 1

    if depth != 0:
        return raw  # unbalanced brackets, bail out

    # raw[array_start .. pos] is the inner array (inclusive)
    inner_array = raw[array_start : pos + 1]

    # The next char should be the closing '"' of the string value
    closing_quote = pos + 1
    if closing_quote >= len(raw) or raw[closing_quote] != '"':
        return raw

    # Rebuild: replace "steps":"[...inner...]" with "steps":<parsed>
    # by embedding the raw array directly (not as a string)
    fixed = raw[:start] + f'"{key}":' + inner_array + raw[closing_quote + 1 :]
    return fixed


def _parse_embedded_json(raw: str, model_cls: type) -> Any | None:
    """Safely parse a JSON-embedded field into a model."""
    if not raw or raw.strip() in ("", "{}"):
        return None
    try:
        data = json.loads(raw)
        return model_cls.model_validate(data)
    except json.JSONDecodeError:
        # BeerSmith may embed arrays (e.g. mash steps) without escaping
        try:
            fixed = _fix_unescaped_json_array(raw, "steps")
            data = json.loads(fixed)
            return model_cls.model_validate(data)
        except (json.JSONDecodeError, Exception):
            return None
    except Exception:
        return None


def _parse_ingredients_json(
    raw: str,
) -> tuple[list[BS4Grain], list[BS4Hop], list[BS4Yeast], list[BS4Misc], list[BS4Water]]:
    """Parse the Ingredients JSON array, routing items by _Schema_ field."""
    grains: list[BS4Grain] = []
    hops: list[BS4Hop] = []
    yeasts: list[BS4Yeast] = []
    miscs: list[BS4Misc] = []
    waters: list[BS4Water] = []

    if not raw or raw.strip() in ("", "[]"):
        return grains, hops, yeasts, miscs, waters

    try:
        items = json.loads(raw)
    except json.JSONDecodeError:
        return grains, hops, yeasts, miscs, waters

    for item in items:
        schema = item.get("_Schema_", "")
        if schema == SCHEMA_GRAIN:
            grains.append(BS4Grain.model_validate(item))
        elif schema == SCHEMA_HOP:
            hops.append(BS4Hop.model_validate(item))
        elif schema == SCHEMA_YEAST:
            yeasts.append(BS4Yeast.model_validate(item))
        elif schema == SCHEMA_MISC:
            miscs.append(BS4Misc.model_validate(item))
        elif schema == SCHEMA_WATER:
            waters.append(BS4Water.model_validate(item))

    return grains, hops, yeasts, miscs, waters


class RecipeRepository:
    """Access recipes from M_RECIPE and M_CLOUD tables."""

    def __init__(self, db: DatabaseManager):
        self._db = db

    def list_recipes(
        self,
        folder: str | None = None,
        search: str | None = None,
        recipe_type: int | None = None,
        source: str = "local",
    ) -> list[BS4Recipe]:
        """List recipe summaries.

        Args:
            folder: Filter by folder path substring.
            search: Filter by name substring (case-insensitive).
            recipe_type: Filter by F_R_TYPE enum value.
            source: 'local' for M_RECIPE, 'cloud' for M_CLOUD.
        """
        table = "M_CLOUD" if source == "cloud" else "M_RECIPE"
        conditions: list[str] = []
        params: list[Any] = []

        if folder:
            conditions.append("F_R_FOLDER_NAME LIKE ?")
            params.append(f"%{folder}%")
        if search:
            conditions.append("F_R_NAME LIKE ?")
            params.append(f"%{search}%")
        if recipe_type is not None:
            conditions.append("F_R_TYPE = ?")
            params.append(recipe_type)

        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"SELECT * FROM [{table}]{where} ORDER BY F_R_NAME"  # noqa: S608
        rows = self._db.query(sql, tuple(params))
        return [BS4Recipe.model_validate(r) for r in rows]

    def get_recipe(
        self,
        identifier: str | int,
        source: str = "local",
    ) -> BS4RecipeFull | None:
        """Get a fully-parsed recipe by ID or name.

        Args:
            identifier: _PERMID_ (int) or recipe name (str).
            source: 'local' or 'cloud'.
        """
        table = "M_CLOUD" if source == "cloud" else "M_RECIPE"

        if isinstance(identifier, int) or (
            isinstance(identifier, str) and identifier.isdigit()
        ):
            row = self._db.query_one(
                f"SELECT * FROM [{table}] WHERE _PERMID_ = ?",  # noqa: S608
                (int(identifier),),
            )
        else:
            row = self._db.query_one(
                f"SELECT * FROM [{table}] WHERE F_R_NAME = ? COLLATE NOCASE",  # noqa: S608
                (identifier,),
            )

        if not row:
            return None

        recipe = BS4Recipe.model_validate(row)
        equipment = _parse_embedded_json(recipe.equipment_raw, BS4Equipment)
        style = _parse_embedded_json(recipe.style_raw, BS4Style)
        mash = _parse_embedded_json(recipe.mash_raw, BS4Mash)
        carb = _parse_embedded_json(recipe.carb_raw, BS4Carb)
        age = _parse_embedded_json(recipe.age_raw, BS4Age)
        grains, hops, yeasts, miscs, waters = _parse_ingredients_json(
            recipe.ingredients_raw
        )

        # Infer boil time from equipment if not on recipe
        if recipe.boil_time is None and equipment:
            recipe = recipe.model_copy(update={"boil_time": equipment.boil_time})

        return BS4RecipeFull(
            recipe=recipe,
            equipment=equipment,
            style=style,
            mash=mash,
            carb=carb,
            age=age,
            grains=grains,
            hops=hops,
            yeasts=yeasts,
            miscs=miscs,
            waters=waters,
        )

    def search_recipes(
        self,
        query: str | None = None,
        ingredient: str | None = None,
        style: str | None = None,
        source: str = "local",
    ) -> list[BS4RecipeFull]:
        """Multi-criteria search returning full recipes.

        At least one criterion must be provided.
        """
        candidates = self.list_recipes(search=query, source=source)
        results: list[BS4RecipeFull] = []

        for summary in candidates:
            full = self.get_recipe(summary.permid, source=source)
            if not full:
                continue
            if style and full.style and style.lower() not in full.style.name.lower():
                continue
            if ingredient:
                names = (
                    [g.name for g in full.grains]
                    + [h.name for h in full.hops]
                    + [y.name for y in full.yeasts]
                    + [m.name for m in full.miscs]
                )
                if not any(ingredient.lower() in n.lower() for n in names):
                    continue
            results.append(full)

        # If only ingredient/style filter without name query, search all
        if not query and (ingredient or style):
            all_recipes = self.list_recipes(source=source)
            seen = {r.recipe.permid for r in results}
            for summary in all_recipes:
                if summary.permid in seen:
                    continue
                full = self.get_recipe(summary.permid, source=source)
                if not full:
                    continue
                if style and full.style and style.lower() not in full.style.name.lower():
                    continue
                if ingredient:
                    names = (
                        [g.name for g in full.grains]
                        + [h.name for h in full.hops]
                        + [y.name for y in full.yeasts]
                        + [m.name for m in full.miscs]
                    )
                    if not any(ingredient.lower() in n.lower() for n in names):
                        continue
                results.append(full)

        return results

    def create_recipe(
        self,
        recipe_data: dict[str, Any],
        equipment_json: str = "{}",
        style_json: str = "{}",
        mash_json: str = "{}",
        carb_json: str = "{}",
        age_json: str = "{}",
        ingredients_json: str = "[]",
    ) -> int:
        """Insert a new recipe and return its _PERMID_.

        Creates a pre-write backup automatically.
        """
        self._db.create_backup()
        permid = self._db.next_permid("M_RECIPE")
        mod = str(int(time.time()))

        recipe_data.update(
            {
                "_PERMID_": permid,
                "_MOD_": mod,
                "F_R_EQUIPMENT": equipment_json,
                "F_R_STYLE": style_json,
                "F_R_MASH": mash_json,
                "F_R_CARB": carb_json,
                "F_R_AGE": age_json,
                "Ingredients": ingredients_json,
            }
        )

        columns = ", ".join(f"[{k}]" for k in recipe_data)
        placeholders = ", ".join("?" for _ in recipe_data)
        sql = f"INSERT INTO M_RECIPE ({columns}) VALUES ({placeholders})"

        with self._db.write_connection() as conn:
            conn.execute(sql, tuple(recipe_data.values()))

        return permid

    def update_recipe(
        self,
        permid: int,
        updates: dict[str, Any],
    ) -> bool:
        """Update an existing recipe.

        Creates a pre-write backup automatically.

        Returns:
            True if a row was updated.
        """
        self._db.create_backup()
        updates["_MOD_"] = str(int(time.time()))

        set_clause = ", ".join(f"[{k}] = ?" for k in updates)
        sql = f"UPDATE M_RECIPE SET {set_clause} WHERE _PERMID_ = ?"
        params = tuple(updates.values()) + (permid,)

        with self._db.write_connection() as conn:
            cur = conn.execute(sql, params)
            return cur.rowcount > 0


class IngredientRepository:
    """Access ingredient libraries (M_GRAIN, M_HOPS, M_YEAST, M_MISC, M_WATER)."""

    def __init__(self, db: DatabaseManager):
        self._db = db

    # ── Grains ────────────────────────────────────────────────────────

    def list_grains(self, search: str | None = None) -> list[BS4Grain]:
        sql = "SELECT * FROM M_GRAIN"
        params: tuple[Any, ...] = ()
        if search:
            sql += " WHERE F_G_NAME LIKE ?"
            params = (f"%{search}%",)
        sql += " ORDER BY F_G_NAME"
        return [BS4Grain.model_validate(r) for r in self._db.query(sql, params)]

    def get_grain(self, identifier: str | int) -> BS4Grain | None:
        if isinstance(identifier, int) or (
            isinstance(identifier, str) and identifier.isdigit()
        ):
            row = self._db.query_one(
                "SELECT * FROM M_GRAIN WHERE _PERMID_ = ?", (int(identifier),)
            )
        else:
            row = self._db.query_one(
                "SELECT * FROM M_GRAIN WHERE F_G_NAME = ? COLLATE NOCASE",
                (identifier,),
            )
        return BS4Grain.model_validate(row) if row else None

    # ── Hops ──────────────────────────────────────────────────────────

    def list_hops(self, search: str | None = None) -> list[BS4Hop]:
        sql = "SELECT * FROM M_HOPS"
        params: tuple[Any, ...] = ()
        if search:
            sql += " WHERE F_H_NAME LIKE ?"
            params = (f"%{search}%",)
        sql += " ORDER BY F_H_NAME"
        return [BS4Hop.model_validate(r) for r in self._db.query(sql, params)]

    def get_hop(self, identifier: str | int) -> BS4Hop | None:
        if isinstance(identifier, int) or (
            isinstance(identifier, str) and identifier.isdigit()
        ):
            row = self._db.query_one(
                "SELECT * FROM M_HOPS WHERE _PERMID_ = ?", (int(identifier),)
            )
        else:
            row = self._db.query_one(
                "SELECT * FROM M_HOPS WHERE F_H_NAME = ? COLLATE NOCASE",
                (identifier,),
            )
        return BS4Hop.model_validate(row) if row else None

    # ── Yeasts ────────────────────────────────────────────────────────

    def list_yeasts(self, search: str | None = None) -> list[BS4Yeast]:
        sql = "SELECT * FROM M_YEAST"
        params: tuple[Any, ...] = ()
        if search:
            sql += " WHERE F_Y_NAME LIKE ?"
            params = (f"%{search}%",)
        sql += " ORDER BY F_Y_NAME"
        return [BS4Yeast.model_validate(r) for r in self._db.query(sql, params)]

    def get_yeast(self, identifier: str | int) -> BS4Yeast | None:
        if isinstance(identifier, int) or (
            isinstance(identifier, str) and identifier.isdigit()
        ):
            row = self._db.query_one(
                "SELECT * FROM M_YEAST WHERE _PERMID_ = ?", (int(identifier),)
            )
        else:
            row = self._db.query_one(
                "SELECT * FROM M_YEAST WHERE F_Y_NAME = ? COLLATE NOCASE",
                (identifier,),
            )
        return BS4Yeast.model_validate(row) if row else None

    # ── Misc ──────────────────────────────────────────────────────────

    def list_miscs(self, search: str | None = None) -> list[BS4Misc]:
        sql = "SELECT * FROM M_MISC"
        params: tuple[Any, ...] = ()
        if search:
            sql += " WHERE F_M_NAME LIKE ?"
            params = (f"%{search}%",)
        sql += " ORDER BY F_M_NAME"
        return [BS4Misc.model_validate(r) for r in self._db.query(sql, params)]

    # ── Water ─────────────────────────────────────────────────────────

    def list_waters(self, search: str | None = None) -> list[BS4Water]:
        sql = "SELECT * FROM M_WATER"
        params: tuple[Any, ...] = ()
        if search:
            sql += " WHERE F_W_NAME LIKE ?"
            params = (f"%{search}%",)
        sql += " ORDER BY F_W_NAME"
        return [BS4Water.model_validate(r) for r in self._db.query(sql, params)]


class ProfileRepository:
    """Access equipment, style, mash, carb, and age profile libraries."""

    def __init__(self, db: DatabaseManager):
        self._db = db

    # ── Equipment ─────────────────────────────────────────────────────

    def list_equipment(self, search: str | None = None) -> list[BS4Equipment]:
        sql = "SELECT * FROM M_EQUIPMENT"
        params: tuple[Any, ...] = ()
        if search:
            sql += " WHERE F_E_NAME LIKE ?"
            params = (f"%{search}%",)
        sql += " ORDER BY F_E_NAME"
        return [BS4Equipment.model_validate(r) for r in self._db.query(sql, params)]

    def get_equipment(self, identifier: str | int) -> BS4Equipment | None:
        if isinstance(identifier, int) or (
            isinstance(identifier, str) and identifier.isdigit()
        ):
            row = self._db.query_one(
                "SELECT * FROM M_EQUIPMENT WHERE _PERMID_ = ?", (int(identifier),)
            )
        else:
            row = self._db.query_one(
                "SELECT * FROM M_EQUIPMENT WHERE F_E_NAME = ? COLLATE NOCASE",
                (identifier,),
            )
        return BS4Equipment.model_validate(row) if row else None

    # ── Styles ────────────────────────────────────────────────────────

    def list_styles(self, search: str | None = None) -> list[BS4Style]:
        sql = "SELECT * FROM M_STYLE"
        params: tuple[Any, ...] = ()
        if search:
            sql += " WHERE F_S_NAME LIKE ?"
            params = (f"%{search}%",)
        sql += " ORDER BY F_S_NAME"
        return [BS4Style.model_validate(r) for r in self._db.query(sql, params)]

    def get_style(self, identifier: str | int) -> BS4Style | None:
        if isinstance(identifier, int) or (
            isinstance(identifier, str) and identifier.isdigit()
        ):
            row = self._db.query_one(
                "SELECT * FROM M_STYLE WHERE _PERMID_ = ?", (int(identifier),)
            )
        else:
            row = self._db.query_one(
                "SELECT * FROM M_STYLE WHERE F_S_NAME = ? COLLATE NOCASE",
                (identifier,),
            )
        return BS4Style.model_validate(row) if row else None

    # ── Mash Profiles ─────────────────────────────────────────────────

    def list_mash_profiles(self, search: str | None = None) -> list[BS4Mash]:
        sql = "SELECT * FROM M_MASH"
        params: tuple[Any, ...] = ()
        if search:
            sql += " WHERE F_MH_NAME LIKE ?"
            params = (f"%{search}%",)
        sql += " ORDER BY F_MH_NAME"
        return [BS4Mash.model_validate(r) for r in self._db.query(sql, params)]

    def get_mash_profile(self, identifier: str | int) -> BS4Mash | None:
        if isinstance(identifier, int) or (
            isinstance(identifier, str) and identifier.isdigit()
        ):
            row = self._db.query_one(
                "SELECT * FROM M_MASH WHERE _PERMID_ = ?", (int(identifier),)
            )
        else:
            row = self._db.query_one(
                "SELECT * FROM M_MASH WHERE F_MH_NAME = ? COLLATE NOCASE",
                (identifier,),
            )
        return BS4Mash.model_validate(row) if row else None

    # ── Carbonation Profiles ──────────────────────────────────────────

    def list_carb_profiles(self) -> list[BS4Carb]:
        return [
            BS4Carb.model_validate(r)
            for r in self._db.query("SELECT * FROM M_CARB ORDER BY F_C_NAME")
        ]

    # ── Age/Fermentation Profiles ─────────────────────────────────────

    def list_age_profiles(self) -> list[BS4Age]:
        return [
            BS4Age.model_validate(r)
            for r in self._db.query("SELECT * FROM M_AGE ORDER BY F_A_NAME")
        ]


class FolderRepository:
    """Access folder hierarchy from M_FOLDER and M_CLOUD_FOLDER."""

    def __init__(self, db: DatabaseManager):
        self._db = db

    def list_local_folders(self) -> list[BS4Folder]:
        return [
            BS4Folder.model_validate(r)
            for r in self._db.query("SELECT * FROM M_FOLDER ORDER BY F_F_NAME")
        ]

    def list_cloud_folders(self) -> list[BS4Folder]:
        return [
            BS4Folder.model_validate(r)
            for r in self._db.query("SELECT * FROM M_CLOUD_FOLDER ORDER BY F_F_NAME")
        ]

    def get_folder_tree(self, source: str = "cloud") -> list[dict]:
        """Return folder hierarchy as nested dicts."""
        folders = (
            self.list_cloud_folders()
            if source == "cloud"
            else self.list_local_folders()
        )
        by_id = {f.permid: f for f in folders}
        tree: list[dict] = []

        def _build(parent_id: int) -> list[dict]:
            children = []
            for f in folders:
                if f.parent == parent_id:
                    children.append(
                        {
                            "id": f.permid,
                            "name": f.name,
                            "children": _build(f.permid),
                        }
                    )
            return children

        # Top-level folders have parent=0
        for f in folders:
            if f.parent == 0 or f.parent not in by_id:
                tree.append(
                    {
                        "id": f.permid,
                        "name": f.name,
                        "children": _build(f.permid),
                    }
                )
        return tree


class OptionsRepository:
    """Access user options from Opts.sqlite."""

    def __init__(self, db: DatabaseManager, config: "BeerSmith4Config"):
        self._db = db
        self._config = config

    def get_all_options(self) -> dict[str, str]:
        rows = self._db.query(
            "SELECT R_OPTNAME, R_VALUE FROM sysopts ORDER BY R_OPTNAME",
            db_path=self._config.opts_db,
        )
        return {r["R_OPTNAME"]: r["R_VALUE"] for r in rows}

    def get_option(self, name: str) -> str | None:
        row = self._db.query_one(
            "SELECT R_VALUE FROM sysopts WHERE R_OPTNAME = ?",
            (name,),
            db_path=self._config.opts_db,
        )
        return row["R_VALUE"] if row else None
