"""
MCP tool definitions for Brewfather.
"""

from datetime import datetime
from fastmcp import FastMCP

from brewing_common.models import Recipe, NormalisedIngredient
from brewing_common.matching import match_string, match_objects

from mcp_brewfather.client import BrewfatherClient
from mcp_brewfather.adapter import BrewfatherAdapter
from mcp_brewfather.config import get_config


def register_tools(mcp: FastMCP) -> None:
    """Register all Brewfather MCP tools."""

    @mcp.tool()
    async def list_recipes(
        limit: int = 50,
        include_archived: bool = False,
    ) -> list[dict]:
        """
        List all Brewfather recipes.

        Args:
            limit: Maximum recipes to return (default 50)
            include_archived: Include archived recipes

        Returns:
            List of recipe summaries
        """
        config = get_config()
        client = BrewfatherClient(config)
        adapter = BrewfatherAdapter()

        recipes = await client.get_recipes(
            limit=limit,
            include_archived=include_archived,
        )

        return [
            {
                "id": r.get("_id"),
                "name": r.get("name"),
                "style": r.get("style", {}).get("name"),
                "batch_size_l": r.get("batchSize"),
                "og": r.get("og"),
                "fg": r.get("fg"),
                "ibu": r.get("ibu"),
                "abv": r.get("abv"),
                "color_ebc": r.get("color"),
            }
            for r in recipes
        ]

    @mcp.tool()
    async def get_recipe(identifier: str) -> dict | None:
        """
        Get a specific recipe by name (fuzzy) or ID.

        Args:
            identifier: Recipe name or ID

        Returns:
            Full recipe details or None if not found
        """
        config = get_config()
        client = BrewfatherClient(config)
        adapter = BrewfatherAdapter()

        # First try as ID (Brewfather IDs are alphanumeric)
        if len(identifier) > 10 and identifier.isalnum():
            try:
                raw = await client.get_recipe(identifier)
                recipe = adapter.to_recipe(raw)
                return _recipe_to_dict(recipe)
            except Exception:
                pass

        # Fuzzy match by name
        recipes = await client.get_recipes(limit=100)
        matches = match_objects(
            identifier,
            recipes,
            key=lambda r: r.get("name", ""),
            threshold=0.6,
            limit=1,
        )

        if not matches:
            return None

        matched_recipe, confidence = matches[0]
        raw = await client.get_recipe(matched_recipe["_id"])
        recipe = adapter.to_recipe(raw)

        result = _recipe_to_dict(recipe)
        result["match_confidence"] = confidence
        return result

    @mcp.tool()
    async def search_recipes(
        query: str,
        field: str = "name",
        limit: int = 10,
    ) -> list[dict]:
        """
        Search recipes by name or style.

        Args:
            query: Search query
            field: Field to search (name, style)
            limit: Maximum results

        Returns:
            List of matching recipes with confidence
        """
        config = get_config()
        client = BrewfatherClient(config)

        recipes = await client.get_recipes(limit=100)

        if field == "style":
            search_values = [r.get("style", {}).get("name", "") for r in recipes]
        else:
            search_values = [r.get("name", "") for r in recipes]

        matches = match_string(query, search_values, threshold=0.5, limit=limit)

        results = []
        for match_value, confidence in matches:
            idx = search_values.index(match_value)
            r = recipes[idx]
            results.append({
                "id": r.get("_id"),
                "name": r.get("name"),
                "style": r.get("style", {}).get("name"),
                "og": r.get("og"),
                "ibu": r.get("ibu"),
                "match_confidence": confidence,
            })

        return results

    @mcp.tool()
    async def list_batches(
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """
        List brewing batches.

        Args:
            status: Filter by status (Planning, Brewing, Fermenting, Conditioning, Completed)
            limit: Maximum batches to return

        Returns:
            List of batch summaries
        """
        config = get_config()
        client = BrewfatherClient(config)

        batches = await client.get_batches(status=status, limit=limit)

        return [
            {
                "id": b.get("_id"),
                "name": b.get("name"),
                "recipe_name": b.get("recipe", {}).get("name"),
                "status": b.get("status"),
                "brew_date": b.get("brewDate"),
                "og": b.get("measuredOg"),
                "fg": b.get("measuredFg"),
                "abv": b.get("measuredAbv"),
            }
            for b in batches
        ]

    @mcp.tool()
    async def get_batch(identifier: str) -> dict | None:
        """
        Get batch details including fermentation data.

        Args:
            identifier: Batch name or ID

        Returns:
            Full batch details or None if not found
        """
        config = get_config()
        client = BrewfatherClient(config)
        adapter = BrewfatherAdapter()

        # Try as ID first
        if len(identifier) > 10 and identifier.isalnum():
            try:
                raw = await client.get_batch(identifier)
                batch = adapter.to_batch(raw)
                return _batch_to_dict(batch, raw)
            except Exception:
                pass

        # Fuzzy match by name
        batches = await client.get_batches(limit=100)
        matches = match_objects(
            identifier,
            batches,
            key=lambda b: b.get("name", ""),
            threshold=0.6,
            limit=1,
        )

        if not matches:
            return None

        matched_batch, confidence = matches[0]
        raw = await client.get_batch(matched_batch["_id"])
        batch = adapter.to_batch(raw)

        result = _batch_to_dict(batch, raw)
        result["match_confidence"] = confidence
        return result

    @mcp.tool()
    async def create_batch(
        recipe_id: str,
        brew_date: str | None = None,
        batch_name: str | None = None,
    ) -> dict:
        """
        Create a new batch from a recipe.

        Args:
            recipe_id: Recipe ID
            brew_date: Brew date (ISO format, defaults to today)
            batch_name: Custom batch name

        Returns:
            Created batch details
        """
        config = get_config()
        client = BrewfatherClient(config)

        if not brew_date:
            brew_date = datetime.now().strftime("%Y-%m-%d")

        result = await client.create_batch(
            recipe_id=recipe_id,
            name=batch_name,
            brew_date=brew_date,
        )

        return {
            "success": True,
            "batch_id": result.get("_id"),
            "name": result.get("name"),
            "recipe": result.get("recipe", {}).get("name"),
            "brew_date": brew_date,
        }

    @mcp.tool()
    async def log_reading(
        batch_id: str,
        gravity: float | None = None,
        temperature: float | None = None,
        note: str | None = None,
    ) -> dict:
        """
        Log a gravity or temperature reading to a batch.

        Args:
            batch_id: Batch ID
            gravity: Gravity reading (e.g., 1.050)
            temperature: Temperature in Celsius
            note: Optional note

        Returns:
            Confirmation
        """
        config = get_config()
        client = BrewfatherClient(config)

        if gravity is None and temperature is None:
            return {"error": "Must provide gravity or temperature"}

        result = await client.add_batch_reading(
            batch_id=batch_id,
            gravity=gravity,
            temperature=temperature,
            note=note,
        )

        return {
            "success": True,
            "reading": {
                "gravity": gravity,
                "temperature": temperature,
                "note": note,
            },
        }

    @mcp.tool()
    async def import_recipe(recipe: dict) -> dict:
        """
        Import a recipe from normalised format (e.g., from BeerSmith).

        The recipe should be in brewing-common normalised format.

        Args:
            recipe: Normalised recipe object

        Returns:
            Created recipe details
        """
        config = get_config()
        client = BrewfatherClient(config)
        adapter = BrewfatherAdapter()

        # Convert from normalised to Brewfather format
        brewfather_recipe = adapter.from_recipe(recipe)

        result = await client.create_recipe(brewfather_recipe)

        return {
            "success": True,
            "recipe_id": result.get("_id"),
            "name": result.get("name"),
        }


def _recipe_to_dict(recipe: Recipe) -> dict:
    """Convert a Recipe to a response dict."""
    return {
        "name": recipe.name,
        "style": recipe.style,
        "batch_size_l": recipe.batch_size_l,
        "boil_time_min": recipe.boil_time_min,
        "efficiency": recipe.efficiency,
        "og": recipe.og,
        "fg": recipe.fg,
        "ibu": recipe.ibu,
        "abv": recipe.abv,
        "color_ebc": recipe.color_ebc,
        "mash_temp_c": recipe.mash_temp_c,
        "fermentation_temp_c": recipe.fermentation_temp_c,
        "ingredients": [
            {
                "name": i.name,
                "type": i.type.value,
                "amount_g": i.amount_g,
                "color_ebc": i.color_ebc,
                "alpha_acid": i.alpha_acid,
                "use": i.use.value if i.use else None,
                "time_minutes": i.time_minutes,
            }
            for i in recipe.ingredients
        ],
        "notes": recipe.notes,
    }


def _batch_to_dict(batch, raw: dict) -> dict:
    """Convert a Batch to a response dict."""
    return {
        "name": batch.name,
        "recipe_name": batch.recipe_name,
        "status": batch.status,
        "brew_date": batch.brew_date.isoformat() if batch.brew_date else None,
        "og_target": raw.get("recipe", {}).get("og"),
        "og_actual": batch.actual_og,
        "fg_target": raw.get("recipe", {}).get("fg"),
        "fg_actual": batch.actual_fg,
        "abv_actual": batch.actual_abv,
        "notes": batch.notes,
    }
