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

    # === Batch Management Tools ===

    @mcp.tool()
    async def update_batch_status(
        batch_id: str,
        status: str,
    ) -> dict:
        """
        Update the status of a batch.

        Args:
            batch_id: Batch ID
            status: New status (Planning, Brewing, Fermenting, Conditioning, Completed, Archived)

        Returns:
            Confirmation with updated batch info
        """
        config = get_config()
        client = BrewfatherClient(config)

        valid_statuses = ["Planning", "Brewing", "Fermenting", "Conditioning", "Completed", "Archived"]
        if status not in valid_statuses:
            return {"error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"}

        result = await client.update_batch_status(batch_id, status)

        return {
            "success": True,
            "batch_id": batch_id,
            "new_status": status,
            "name": result.get("name"),
        }

    @mcp.tool()
    async def update_batch_measurements(
        batch_id: str,
        measured_og: float | None = None,
        measured_fg: float | None = None,
        measured_batch_size: float | None = None,
        measured_efficiency: float | None = None,
    ) -> dict:
        """
        Update measured values for a batch.

        Args:
            batch_id: Batch ID
            measured_og: Measured original gravity (e.g., 1.055)
            measured_fg: Measured final gravity (e.g., 1.010)
            measured_batch_size: Measured batch size in liters
            measured_efficiency: Measured efficiency percentage

        Returns:
            Confirmation with updated values
        """
        config = get_config()
        client = BrewfatherClient(config)

        result = await client.update_batch_measurements(
            batch_id,
            measured_og=measured_og,
            measured_fg=measured_fg,
            measured_batch_size=measured_batch_size,
            measured_efficiency=measured_efficiency,
        )

        return {
            "success": True,
            "batch_id": batch_id,
            "updated": {
                "measured_og": measured_og,
                "measured_fg": measured_fg,
                "measured_batch_size": measured_batch_size,
                "measured_efficiency": measured_efficiency,
            },
        }

    @mcp.tool()
    async def get_batch_readings(batch_id: str) -> list[dict]:
        """
        Get all fermentation readings for a batch.

        Args:
            batch_id: Batch ID

        Returns:
            List of readings with gravity, temperature, and timestamps
        """
        config = get_config()
        client = BrewfatherClient(config)

        readings = await client.get_batch_readings(batch_id)

        return [
            {
                "timestamp": r.get("time"),
                "gravity": r.get("sg"),
                "temperature": r.get("temp"),
                "comment": r.get("comment"),
                "device": r.get("deviceType"),
            }
            for r in readings
        ]

    @mcp.tool()
    async def get_last_reading(batch_id: str) -> dict | None:
        """
        Get the most recent fermentation reading for a batch.

        Args:
            batch_id: Batch ID

        Returns:
            Latest reading or None if no readings exist
        """
        config = get_config()
        client = BrewfatherClient(config)

        reading = await client.get_last_reading(batch_id)

        if not reading:
            return None

        return {
            "timestamp": reading.get("time"),
            "gravity": reading.get("sg"),
            "temperature": reading.get("temp"),
            "comment": reading.get("comment"),
            "device": reading.get("deviceType"),
        }

    @mcp.tool()
    async def get_brewtracker(batch_id: str) -> dict:
        """
        Get brew tracker status for a batch (shows step-by-step brewing progress).

        Args:
            batch_id: Batch ID

        Returns:
            Brew tracker status including current step and completion state
        """
        config = get_config()
        client = BrewfatherClient(config)

        tracker = await client.get_brewtracker(batch_id)

        return tracker

    # === Inventory Tools ===

    @mcp.tool()
    async def list_fermentables(
        limit: int = 50,
        inventory_only: bool = False,
    ) -> list[dict]:
        """
        List fermentables (grains, sugars, extracts) in inventory.

        Args:
            limit: Maximum items to return (max 50)
            inventory_only: Only show items with inventory > 0

        Returns:
            List of fermentables with inventory amounts
        """
        config = get_config()
        client = BrewfatherClient(config)

        items = await client.list_fermentables(limit=limit, inventory_only=inventory_only)

        return [
            {
                "id": f.get("_id"),
                "name": f.get("name"),
                "type": f.get("type"),
                "color_ebc": f.get("color"),
                "potential": f.get("potential"),
                "origin": f.get("origin"),
                "supplier": f.get("supplier"),
                "inventory_kg": f.get("inventory", 0),
            }
            for f in items
        ]

    @mcp.tool()
    async def list_hops(
        limit: int = 50,
        inventory_only: bool = False,
    ) -> list[dict]:
        """
        List hops in inventory.

        Args:
            limit: Maximum items to return (max 50)
            inventory_only: Only show items with inventory > 0

        Returns:
            List of hops with inventory amounts
        """
        config = get_config()
        client = BrewfatherClient(config)

        items = await client.list_hops(limit=limit, inventory_only=inventory_only)

        return [
            {
                "id": h.get("_id"),
                "name": h.get("name"),
                "alpha": h.get("alpha"),
                "type": h.get("type"),
                "origin": h.get("origin"),
                "year": h.get("year"),
                "inventory_g": h.get("inventory", 0),
            }
            for h in items
        ]

    @mcp.tool()
    async def list_yeasts(
        limit: int = 50,
        inventory_only: bool = False,
    ) -> list[dict]:
        """
        List yeasts in inventory.

        Args:
            limit: Maximum items to return (max 50)
            inventory_only: Only show items with inventory > 0

        Returns:
            List of yeasts with inventory amounts
        """
        config = get_config()
        client = BrewfatherClient(config)

        items = await client.list_yeasts(limit=limit, inventory_only=inventory_only)

        return [
            {
                "id": y.get("_id"),
                "name": y.get("name"),
                "laboratory": y.get("laboratory"),
                "productId": y.get("productId"),
                "type": y.get("type"),
                "form": y.get("form"),
                "attenuation": y.get("attenuation"),
                "inventory_packages": y.get("inventory", 0),
            }
            for y in items
        ]

    @mcp.tool()
    async def list_miscs(
        limit: int = 50,
        inventory_only: bool = False,
    ) -> list[dict]:
        """
        List miscellaneous items (water agents, fining, spices) in inventory.

        Args:
            limit: Maximum items to return (max 50)
            inventory_only: Only show items with inventory > 0

        Returns:
            List of misc items with inventory amounts
        """
        config = get_config()
        client = BrewfatherClient(config)

        items = await client.list_miscs(limit=limit, inventory_only=inventory_only)

        return [
            {
                "id": m.get("_id"),
                "name": m.get("name"),
                "type": m.get("type"),
                "use": m.get("use"),
                "inventory": m.get("inventory", 0),
                "unit": m.get("unit"),
            }
            for m in items
        ]

    @mcp.tool()
    async def get_inventory_item(
        item_type: str,
        item_id: str,
    ) -> dict | None:
        """
        Get details for a specific inventory item.

        Args:
            item_type: Type of item (fermentables, hops, yeasts, miscs)
            item_id: Item ID

        Returns:
            Full item details or None if not found
        """
        config = get_config()
        client = BrewfatherClient(config)

        valid_types = ["fermentables", "hops", "yeasts", "miscs"]
        if item_type not in valid_types:
            return {"error": f"Invalid item type. Must be one of: {', '.join(valid_types)}"}

        try:
            return await client.get_inventory_item(item_type, item_id)
        except Exception:
            return None

    @mcp.tool()
    async def update_fermentable_inventory(
        item_id: str,
        amount_kg: float | None = None,
        adjust_kg: float | None = None,
    ) -> dict:
        """
        Update fermentable inventory amount.

        Args:
            item_id: Fermentable ID
            amount_kg: Set inventory to this exact amount (kg)
            adjust_kg: Adjust inventory by this amount (positive to add, negative to subtract)

        Returns:
            Confirmation with new inventory amount
        """
        config = get_config()
        client = BrewfatherClient(config)

        if amount_kg is None and adjust_kg is None:
            return {"error": "Must provide either amount_kg or adjust_kg"}

        result = await client.update_fermentable_inventory(
            item_id,
            inventory=amount_kg,
            inventory_adjust=adjust_kg,
        )

        return {
            "success": True,
            "item_id": item_id,
            "name": result.get("name"),
            "new_inventory_kg": result.get("inventory"),
        }

    @mcp.tool()
    async def update_hop_inventory(
        item_id: str,
        amount_g: float | None = None,
        adjust_g: float | None = None,
    ) -> dict:
        """
        Update hop inventory amount.

        Args:
            item_id: Hop ID
            amount_g: Set inventory to this exact amount (grams)
            adjust_g: Adjust inventory by this amount (positive to add, negative to subtract)

        Returns:
            Confirmation with new inventory amount
        """
        config = get_config()
        client = BrewfatherClient(config)

        if amount_g is None and adjust_g is None:
            return {"error": "Must provide either amount_g or adjust_g"}

        result = await client.update_hop_inventory(
            item_id,
            inventory=amount_g,
            inventory_adjust=adjust_g,
        )

        return {
            "success": True,
            "item_id": item_id,
            "name": result.get("name"),
            "new_inventory_g": result.get("inventory"),
        }

    @mcp.tool()
    async def update_yeast_inventory(
        item_id: str,
        amount_packages: float | None = None,
        adjust_packages: float | None = None,
    ) -> dict:
        """
        Update yeast inventory amount.

        Args:
            item_id: Yeast ID
            amount_packages: Set inventory to this exact number of packages
            adjust_packages: Adjust inventory by this amount (positive to add, negative to subtract)

        Returns:
            Confirmation with new inventory amount
        """
        config = get_config()
        client = BrewfatherClient(config)

        if amount_packages is None and adjust_packages is None:
            return {"error": "Must provide either amount_packages or adjust_packages"}

        result = await client.update_yeast_inventory(
            item_id,
            inventory=amount_packages,
            inventory_adjust=adjust_packages,
        )

        return {
            "success": True,
            "item_id": item_id,
            "name": result.get("name"),
            "new_inventory_packages": result.get("inventory"),
        }

    @mcp.tool()
    async def update_misc_inventory(
        item_id: str,
        amount: float | None = None,
        adjust: float | None = None,
    ) -> dict:
        """
        Update misc item inventory amount.

        Args:
            item_id: Misc item ID
            amount: Set inventory to this exact amount (in item's native unit)
            adjust: Adjust inventory by this amount (positive to add, negative to subtract)

        Returns:
            Confirmation with new inventory amount
        """
        config = get_config()
        client = BrewfatherClient(config)

        if amount is None and adjust is None:
            return {"error": "Must provide either amount or adjust"}

        result = await client.update_misc_inventory(
            item_id,
            inventory=amount,
            inventory_adjust=adjust,
        )

        return {
            "success": True,
            "item_id": item_id,
            "name": result.get("name"),
            "new_inventory": result.get("inventory"),
            "unit": result.get("unit"),
        }

    # === Summary/Dashboard Tools ===

    @mcp.tool()
    async def get_inventory_summary() -> dict:
        """
        Get a summary of inventory across all ingredient types.

        Returns:
            Counts of items with inventory > 0 for each type
        """
        config = get_config()
        client = BrewfatherClient(config)

        fermentables = await client.list_fermentables(inventory_only=True)
        hops = await client.list_hops(inventory_only=True)
        yeasts = await client.list_yeasts(inventory_only=True)
        miscs = await client.list_miscs(inventory_only=True)

        return {
            "fermentables": {
                "count": len(fermentables),
                "items": [{"name": f.get("name"), "amount_kg": f.get("inventory", 0)} for f in fermentables[:10]],
            },
            "hops": {
                "count": len(hops),
                "items": [{"name": h.get("name"), "amount_g": h.get("inventory", 0)} for h in hops[:10]],
            },
            "yeasts": {
                "count": len(yeasts),
                "items": [{"name": y.get("name"), "packages": y.get("inventory", 0)} for y in yeasts[:10]],
            },
            "miscs": {
                "count": len(miscs),
                "items": [{"name": m.get("name"), "amount": m.get("inventory", 0)} for m in miscs[:10]],
            },
        }

    @mcp.tool()
    async def get_active_batches() -> list[dict]:
        """
        Get all currently active batches (Brewing, Fermenting, or Conditioning).

        Returns:
            List of active batches with fermentation readings
        """
        config = get_config()
        client = BrewfatherClient(config)

        results = []
        for status in ["Brewing", "Fermenting", "Conditioning"]:
            batches = await client.get_batches(status=status, limit=50)
            for b in batches:
                # Get latest reading for each batch
                last_reading = await client.get_last_reading(b.get("_id"))

                batch_info = {
                    "id": b.get("_id"),
                    "name": b.get("name"),
                    "recipe_name": b.get("recipe", {}).get("name"),
                    "status": b.get("status"),
                    "brew_date": b.get("brewDate"),
                    "measured_og": b.get("measuredOg"),
                }

                if last_reading:
                    batch_info["last_reading"] = {
                        "gravity": last_reading.get("sg"),
                        "temperature": last_reading.get("temp"),
                        "timestamp": last_reading.get("time"),
                    }

                results.append(batch_info)

        return results

    @mcp.tool()
    async def search_inventory(
        query: str,
        item_type: str | None = None,
    ) -> list[dict]:
        """
        Search inventory by name across all or specific ingredient types.

        Args:
            query: Search term
            item_type: Optional filter by type (fermentables, hops, yeasts, miscs)

        Returns:
            Matching items with their inventory amounts
        """
        config = get_config()
        client = BrewfatherClient(config)

        results = []
        query_lower = query.lower()

        types_to_search = [item_type] if item_type else ["fermentables", "hops", "yeasts", "miscs"]

        for inv_type in types_to_search:
            if inv_type == "fermentables":
                items = await client.list_fermentables(limit=50)
                for item in items:
                    if query_lower in item.get("name", "").lower():
                        results.append({
                            "type": "fermentable",
                            "id": item.get("_id"),
                            "name": item.get("name"),
                            "inventory": item.get("inventory", 0),
                            "unit": "kg",
                        })
            elif inv_type == "hops":
                items = await client.list_hops(limit=50)
                for item in items:
                    if query_lower in item.get("name", "").lower():
                        results.append({
                            "type": "hop",
                            "id": item.get("_id"),
                            "name": item.get("name"),
                            "inventory": item.get("inventory", 0),
                            "unit": "g",
                        })
            elif inv_type == "yeasts":
                items = await client.list_yeasts(limit=50)
                for item in items:
                    if query_lower in item.get("name", "").lower():
                        results.append({
                            "type": "yeast",
                            "id": item.get("_id"),
                            "name": item.get("name"),
                            "inventory": item.get("inventory", 0),
                            "unit": "packages",
                        })
            elif inv_type == "miscs":
                items = await client.list_miscs(limit=50)
                for item in items:
                    if query_lower in item.get("name", "").lower():
                        results.append({
                            "type": "misc",
                            "id": item.get("_id"),
                            "name": item.get("name"),
                            "inventory": item.get("inventory", 0),
                            "unit": item.get("unit", ""),
                        })

        return results


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
