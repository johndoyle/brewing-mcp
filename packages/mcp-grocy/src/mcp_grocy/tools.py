"""MCP tool definitions for Grocy."""

from fastmcp import FastMCP

from mcp_grocy.adapter import GrocyAdapter
from mcp_grocy.client import GrocyClient
from mcp_grocy.config import get_config


def _get_client() -> GrocyClient:
    """Get a configured Grocy client."""
    return GrocyClient(get_config())


def _get_adapter() -> GrocyAdapter:
    """Get a Grocy adapter."""
    return GrocyAdapter()


def register_tools(mcp: FastMCP) -> None:
    """Register all Grocy MCP tools."""

    # ==================== System ====================

    @mcp.tool()
    async def get_system_info() -> dict:
        """
        Get Grocy system information.

        Returns version, database path, and other system details.
        """
        client = _get_client()
        return await client.get_system_info()

    @mcp.tool()
    async def get_system_config() -> dict:
        """
        Get Grocy system configuration settings.

        Returns all configuration values including:
        - CURRENCY: The currency symbol (e.g., "GBP", "USD", "EUR")
        - FEATURE_FLAG_* settings
        - BASE_URL and other system settings

        This is useful for determining the currency when syncing prices to BeerSmith.
        """
        client = _get_client()
        return await client.get_system_config()

    # ==================== Stock Management ====================

    @mcp.tool()
    async def get_stock(category: str | None = None) -> list[dict]:
        """
        Get current stock for all products.

        Args:
            category: Optional product group/category filter

        Returns all products with current stock levels.
        """
        client = _get_client()
        adapter = _get_adapter()

        stock = await client.get_stock()
        products = await client.get_products()
        product_map = {p["id"]: p for p in products}

        if category:
            groups = await client.get_product_groups()
            group_ids = [
                g["id"] for g in groups
                if category.lower() in g.get("name", "").lower()
            ]
            product_map = {
                pid: p for pid, p in product_map.items()
                if p.get("product_group_id") in group_ids
            }

        results = []
        for item in stock:
            product_id = item.get("product_id")
            if product_id not in product_map:
                continue

            product = product_map[product_id]
            results.append({
                "id": product_id,
                "name": product.get("name"),
                "amount": item.get("amount"),
                "amount_opened": item.get("amount_opened"),
                "is_aggregated_amount": item.get("is_aggregated_amount"),
                "best_before_date": item.get("best_before_date"),
                "product_group": product.get("product_group_id"),
            })

        return results

    @mcp.tool()
    async def get_volatile_stock() -> dict:
        """
        Get volatile stock information.

        Returns products that are expiring soon, already expired,
        below minimum stock, and products opened.
        """
        client = _get_client()
        return await client.get_volatile_stock()

    @mcp.tool()
    async def get_product_stock(name: str) -> dict | None:
        """
        Get stock details for a specific product.

        Args:
            name: Product name (fuzzy matched)

        Returns stock details or None if not found.
        """
        client = _get_client()

        products = await client.get_products()
        name_lower = name.lower()

        # Find matching product
        matched = None
        for p in products:
            if name_lower == p.get("name", "").lower():
                matched = p
                break
            if name_lower in p.get("name", "").lower():
                matched = p

        if not matched:
            return None

        stock_info = await client.get_product_stock(matched["id"])
        return {
            "product": matched.get("name"),
            "id": matched["id"],
            **stock_info,
        }

    @mcp.tool()
    async def add_product(
        name: str,
        amount: float,
        best_before_date: str | None = None,
        price: float | None = None,
        location_id: int | None = None,
    ) -> dict:
        """
        Add stock for a product (purchase).

        Args:
            name: Product name
            amount: Amount to add
            best_before_date: Best before date (YYYY-MM-DD)
            price: Unit price
            location_id: Storage location ID

        Returns transaction confirmation.
        """
        client = _get_client()

        products = await client.get_products()
        name_lower = name.lower()

        matched = None
        for p in products:
            if name_lower in p.get("name", "").lower():
                matched = p
                break

        if not matched:
            return {"error": f"Product '{name}' not found"}

        result = await client.add_product_stock(
            product_id=matched["id"],
            amount=amount,
            best_before_date=best_before_date,
            price=price,
            location_id=location_id,
        )

        return {
            "success": True,
            "product": matched.get("name"),
            "amount_added": amount,
            "transaction": result,
        }

    @mcp.tool()
    async def consume_product(
        name: str,
        amount: float,
        spoiled: bool = False,
    ) -> dict:
        """
        Consume stock for a product.

        Args:
            name: Product name
            amount: Amount to consume
            spoiled: Whether the stock was spoiled

        Returns transaction confirmation.
        """
        client = _get_client()

        products = await client.get_products()
        name_lower = name.lower()

        matched = None
        for p in products:
            if name_lower in p.get("name", "").lower():
                matched = p
                break

        if not matched:
            return {"error": f"Product '{name}' not found"}

        result = await client.consume_product_stock(
            product_id=matched["id"],
            amount=amount,
            spoiled=spoiled,
        )

        return {
            "success": True,
            "product": matched.get("name"),
            "amount_consumed": amount,
            "transaction": result,
        }

    @mcp.tool()
    async def transfer_product(
        name: str,
        amount: float,
        from_location: str,
        to_location: str,
    ) -> dict:
        """
        Transfer stock between locations.

        Args:
            name: Product name
            amount: Amount to transfer
            from_location: Source location name
            to_location: Destination location name

        Returns transaction confirmation.
        """
        client = _get_client()

        products = await client.get_products()
        locations = await client.get_locations()

        # Find product
        name_lower = name.lower()
        matched_product = None
        for p in products:
            if name_lower in p.get("name", "").lower():
                matched_product = p
                break

        if not matched_product:
            return {"error": f"Product '{name}' not found"}

        # Find locations
        from_loc = None
        to_loc = None
        for loc in locations:
            if from_location.lower() in loc.get("name", "").lower():
                from_loc = loc
            if to_location.lower() in loc.get("name", "").lower():
                to_loc = loc

        if not from_loc:
            return {"error": f"Location '{from_location}' not found"}
        if not to_loc:
            return {"error": f"Location '{to_location}' not found"}

        result = await client.transfer_product_stock(
            product_id=matched_product["id"],
            amount=amount,
            location_id_from=from_loc["id"],
            location_id_to=to_loc["id"],
        )

        return {
            "success": True,
            "product": matched_product.get("name"),
            "amount": amount,
            "from": from_loc.get("name"),
            "to": to_loc.get("name"),
        }

    @mcp.tool()
    async def inventory_product(
        name: str,
        new_amount: float,
        best_before_date: str | None = None,
    ) -> dict:
        """
        Set inventory level for a product (stocktaking).

        Args:
            name: Product name
            new_amount: New stock amount
            best_before_date: Best before date (YYYY-MM-DD)

        Returns transaction confirmation.
        """
        client = _get_client()

        products = await client.get_products()
        name_lower = name.lower()

        matched = None
        for p in products:
            if name_lower in p.get("name", "").lower():
                matched = p
                break

        if not matched:
            return {"error": f"Product '{name}' not found"}

        result = await client.inventory_product(
            product_id=matched["id"],
            new_amount=new_amount,
            best_before_date=best_before_date,
        )

        return {
            "success": True,
            "product": matched.get("name"),
            "new_amount": new_amount,
        }

    @mcp.tool()
    async def open_product(name: str, amount: float = 1) -> dict:
        """
        Mark a product as opened.

        Args:
            name: Product name
            amount: Amount to mark as opened (default 1)

        Returns confirmation.
        """
        client = _get_client()

        products = await client.get_products()
        name_lower = name.lower()

        matched = None
        for p in products:
            if name_lower in p.get("name", "").lower():
                matched = p
                break

        if not matched:
            return {"error": f"Product '{name}' not found"}

        result = await client.open_product(matched["id"], amount)

        return {
            "success": True,
            "product": matched.get("name"),
            "amount_opened": amount,
        }

    @mcp.tool()
    async def get_product_by_barcode(barcode: str) -> dict | None:
        """
        Look up a product by its barcode.

        Args:
            barcode: Product barcode to search

        Returns product details with stock info, or None if not found.
        """
        client = _get_client()
        try:
            result = await client.get_product_by_barcode(barcode)
            return {
                "product_id": result.get("product", {}).get("id"),
                "product_name": result.get("product", {}).get("name"),
                "barcode": barcode,
                "stock_amount": result.get("stock_amount"),
                "stock_amount_opened": result.get("stock_amount_opened"),
                "product": result.get("product"),
            }
        except Exception:
            return None

    @mcp.tool()
    async def get_product_entries(name: str) -> list[dict]:
        """
        Get all stock entries for a product (purchase history).

        Args:
            name: Product name

        Returns list of stock entries with purchase dates, prices, locations, etc.
        """
        client = _get_client()

        products = await client.get_products()
        name_lower = name.lower()

        matched = None
        for p in products:
            if name_lower in p.get("name", "").lower():
                matched = p
                break

        if not matched:
            return []

        entries = await client.get_product_stock_entries(matched["id"])
        locations = await client.get_locations()
        loc_map = {loc["id"]: loc.get("name") for loc in locations}

        return [
            {
                "id": e.get("id"),
                "amount": e.get("amount"),
                "best_before_date": e.get("best_before_date"),
                "purchased_date": e.get("purchased_date"),
                "price": e.get("price"),
                "location": loc_map.get(e.get("location_id"), "Unknown"),
                "open": e.get("open", 0) == 1,
                "note": e.get("note"),
            }
            for e in entries
        ]

    @mcp.tool()
    async def match_product_by_name(
        name: str,
        threshold: float = 70.0,
    ) -> dict | None:
        """
        Find the best matching product using fuzzy string matching.

        Args:
            name: Product name to search for
            threshold: Minimum match score (0-100) required

        Returns best matching product with confidence score, or None if no match.
        """
        client = _get_client()
        products = await client.get_products()

        if not products:
            return None

        name_lower = name.lower()
        best_match = None
        best_score = 0

        for p in products:
            product_name = p.get("name", "").lower()

            # Exact match
            if name_lower == product_name:
                return {
                    "product": p,
                    "score": 100.0,
                    "match_type": "exact",
                }

            # Contains match
            if name_lower in product_name or product_name in name_lower:
                score = 90.0 if name_lower in product_name else 80.0
                if score > best_score:
                    best_score = score
                    best_match = p

            # Word overlap scoring
            name_words = set(name_lower.split())
            product_words = set(product_name.split())
            overlap = len(name_words & product_words)
            total = len(name_words | product_words)
            if total > 0:
                word_score = (overlap / total) * 100
                if word_score > best_score:
                    best_score = word_score
                    best_match = p

        if best_match and best_score >= threshold:
            return {
                "product": best_match,
                "score": best_score,
                "match_type": "fuzzy",
            }

        return None

    # ==================== Shopping List ====================

    @mcp.tool()
    async def get_shopping_list() -> list[dict]:
        """
        Get current shopping list.

        Returns all items on the shopping list with product details.
        """
        client = _get_client()

        items = await client.get_shopping_list()
        products = await client.get_products()
        product_map = {p["id"]: p for p in products}

        return [
            {
                "id": item.get("id"),
                "product": product_map.get(item["product_id"], {}).get("name", "Unknown"),
                "product_id": item.get("product_id"),
                "amount": item.get("amount"),
                "note": item.get("note"),
                "done": item.get("done", 0) == 1,
            }
            for item in items
        ]

    @mcp.tool()
    async def add_to_shopping_list(
        name: str,
        amount: float,
        note: str | None = None,
    ) -> dict:
        """
        Add an item to the shopping list.

        Args:
            name: Product name
            amount: Amount needed
            note: Optional note

        Returns confirmation.
        """
        client = _get_client()

        products = await client.get_products()
        name_lower = name.lower()

        matched = None
        for p in products:
            if name_lower in p.get("name", "").lower():
                matched = p
                break

        if not matched:
            return {"error": f"Product '{name}' not found"}

        result = await client.add_to_shopping_list(
            product_id=matched["id"],
            amount=amount,
            note=note,
        )

        return {
            "success": True,
            "product": matched.get("name"),
            "amount": amount,
        }

    @mcp.tool()
    async def remove_from_shopping_list(item_id: int) -> dict:
        """
        Remove an item from the shopping list.

        Args:
            item_id: Shopping list item ID

        Returns confirmation.
        """
        client = _get_client()
        await client.remove_from_shopping_list(item_id)
        return {"success": True, "removed_id": item_id}

    @mcp.tool()
    async def clear_shopping_list() -> dict:
        """
        Clear all items from the shopping list.

        Returns confirmation.
        """
        client = _get_client()
        await client.clear_shopping_list()
        return {"success": True, "message": "Shopping list cleared"}

    @mcp.tool()
    async def add_missing_products_to_shopping_list() -> dict:
        """
        Add all products below minimum stock to the shopping list.

        Returns confirmation.
        """
        client = _get_client()
        await client.add_missing_products_to_shopping_list()
        return {"success": True, "message": "Missing products added to shopping list"}

    @mcp.tool()
    async def add_expired_products_to_shopping_list() -> dict:
        """
        Add all expired products to the shopping list.

        This is useful for quickly identifying and replacing expired stock.

        Returns confirmation.
        """
        client = _get_client()
        await client.add_expired_products_to_shopping_list()
        return {"success": True, "message": "Expired products added to shopping list"}

    @mcp.tool()
    async def bulk_add_to_shopping_list(items: list[dict]) -> dict:
        """
        Add multiple items to the shopping list at once.

        Args:
            items: List of items, each with 'name' (product name) and 'amount',
                   optionally 'note'

        Returns summary of added items.
        """
        client = _get_client()
        products = await client.get_products()
        product_map = {p.get("name", "").lower(): p for p in products}

        added = []
        not_found = []

        for item in items:
            name = item.get("name", "")
            amount = item.get("amount", 1)
            note = item.get("note")

            # Find product
            name_lower = name.lower()
            matched = product_map.get(name_lower)
            if not matched:
                for pname, prod in product_map.items():
                    if name_lower in pname:
                        matched = prod
                        break

            if matched:
                await client.add_to_shopping_list(
                    product_id=matched["id"],
                    amount=amount,
                    note=note,
                )
                added.append({"name": matched.get("name"), "amount": amount})
            else:
                not_found.append(name)

        return {
            "success": True,
            "added": added,
            "not_found": not_found,
            "total_added": len(added),
        }

    # ==================== Recipes ====================

    @mcp.tool()
    async def get_recipes() -> list[dict]:
        """
        Get all recipes.

        Returns list of recipes with basic info.
        """
        client = _get_client()
        recipes = await client.get_recipes()
        return [
            {
                "id": r.get("id"),
                "name": r.get("name"),
                "description": r.get("description"),
                "servings": r.get("base_servings"),
            }
            for r in recipes
        ]

    @mcp.tool()
    async def get_recipe(name_or_id: str | int) -> dict | None:
        """
        Get a specific recipe with ingredients.

        Args:
            name_or_id: Recipe name or ID

        Returns recipe with ingredients.
        """
        client = _get_client()
        recipes = await client.get_recipes()

        matched = None
        if isinstance(name_or_id, int) or name_or_id.isdigit():
            recipe_id = int(name_or_id)
            matched = next((r for r in recipes if r["id"] == recipe_id), None)
        else:
            name_lower = name_or_id.lower()
            for r in recipes:
                if name_lower in r.get("name", "").lower():
                    matched = r
                    break

        if not matched:
            return None

        # Get ingredients
        positions = await client.get_recipe_positions(matched["id"])
        products = await client.get_products()
        product_map = {p["id"]: p for p in products}

        ingredients = []
        for pos in positions:
            product = product_map.get(pos.get("product_id"), {})
            ingredients.append({
                "product": product.get("name", "Unknown"),
                "amount": pos.get("amount"),
                "note": pos.get("note"),
            })

        return {
            "id": matched.get("id"),
            "name": matched.get("name"),
            "description": matched.get("description"),
            "servings": matched.get("base_servings"),
            "ingredients": ingredients,
        }

    @mcp.tool()
    async def get_recipe_fulfillment(name_or_id: str | int) -> dict | None:
        """
        Check if you have enough stock to make a recipe.

        Args:
            name_or_id: Recipe name or ID

        Returns fulfillment status for each ingredient.
        """
        client = _get_client()
        recipes = await client.get_recipes()

        matched = None
        if isinstance(name_or_id, int) or (isinstance(name_or_id, str) and name_or_id.isdigit()):
            recipe_id = int(name_or_id)
            matched = next((r for r in recipes if r["id"] == recipe_id), None)
        else:
            name_lower = str(name_or_id).lower()
            for r in recipes:
                if name_lower in r.get("name", "").lower():
                    matched = r
                    break

        if not matched:
            return None

        fulfillment = await client.get_recipe_fulfillment(matched["id"])
        return {
            "recipe": matched.get("name"),
            "is_fulfilled": fulfillment.get("recipe_fulfillment") == 1,
            "missing_products": fulfillment.get("missing_products_count", 0),
            "details": fulfillment,
        }

    @mcp.tool()
    async def consume_recipe(name_or_id: str | int) -> dict:
        """
        Consume all ingredients for a recipe from stock.

        Args:
            name_or_id: Recipe name or ID

        Returns confirmation.
        """
        client = _get_client()
        recipes = await client.get_recipes()

        matched = None
        if isinstance(name_or_id, int) or (isinstance(name_or_id, str) and name_or_id.isdigit()):
            recipe_id = int(name_or_id)
            matched = next((r for r in recipes if r["id"] == recipe_id), None)
        else:
            name_lower = str(name_or_id).lower()
            for r in recipes:
                if name_lower in r.get("name", "").lower():
                    matched = r
                    break

        if not matched:
            return {"error": "Recipe not found"}

        result = await client.consume_recipe(matched["id"])
        return {
            "success": True,
            "recipe": matched.get("name"),
            "consumed": True,
        }

    @mcp.tool()
    async def add_recipe_to_shopping_list(name_or_id: str | int) -> dict:
        """
        Add missing ingredients for a recipe to the shopping list.

        Args:
            name_or_id: Recipe name or ID

        Returns confirmation.
        """
        client = _get_client()
        recipes = await client.get_recipes()

        matched = None
        if isinstance(name_or_id, int) or (isinstance(name_or_id, str) and name_or_id.isdigit()):
            recipe_id = int(name_or_id)
            matched = next((r for r in recipes if r["id"] == recipe_id), None)
        else:
            name_lower = str(name_or_id).lower()
            for r in recipes:
                if name_lower in r.get("name", "").lower():
                    matched = r
                    break

        if not matched:
            return {"error": "Recipe not found"}

        await client.add_recipe_to_shopping_list(matched["id"])
        return {
            "success": True,
            "recipe": matched.get("name"),
            "message": "Missing ingredients added to shopping list",
        }

    @mcp.tool()
    async def create_recipe_with_ingredients(
        name: str,
        ingredients: list[dict],
        description: str | None = None,
        servings: int = 1,
    ) -> dict:
        """
        Create a new recipe with ingredients in one operation.

        Args:
            name: Recipe name
            ingredients: List of ingredients, each with:
                - name: Product name
                - amount: Amount required
                - note: Optional note
            description: Recipe description
            servings: Number of servings (default 1)

        Returns created recipe with ingredient status.
        """
        client = _get_client()

        # Create the recipe first
        recipe_data = {
            "name": name,
            "base_servings": servings,
        }
        if description:
            recipe_data["description"] = description

        recipe_result = await client.create_recipe(recipe_data)
        recipe_id = recipe_result.get("created_object_id")

        if not recipe_id:
            return {"error": "Failed to create recipe"}

        # Get products for matching
        products = await client.get_products()
        product_map = {p.get("name", "").lower(): p for p in products}

        added_ingredients = []
        not_found_ingredients = []

        for ing in ingredients:
            ing_name = ing.get("name", "")
            amount = ing.get("amount", 1)
            note = ing.get("note")

            # Find matching product
            name_lower = ing_name.lower()
            matched = product_map.get(name_lower)
            if not matched:
                for pname, prod in product_map.items():
                    if name_lower in pname or pname in name_lower:
                        matched = prod
                        break

            if matched:
                await client.add_recipe_ingredient(
                    recipe_id=recipe_id,
                    product_id=matched["id"],
                    amount=amount,
                    note=note,
                )
                added_ingredients.append({
                    "name": matched.get("name"),
                    "amount": amount,
                })
            else:
                not_found_ingredients.append(ing_name)

        return {
            "success": True,
            "recipe_id": recipe_id,
            "recipe_name": name,
            "ingredients_added": added_ingredients,
            "ingredients_not_found": not_found_ingredients,
        }

    @mcp.tool()
    async def get_recipe_with_stock_status(name_or_id: str | int) -> dict | None:
        """
        Get recipe with complete stock status for all ingredients.

        Args:
            name_or_id: Recipe name or ID

        Returns recipe with fulfillment status and stock levels for each ingredient.
        """
        client = _get_client()
        recipes = await client.get_recipes()

        matched = None
        if isinstance(name_or_id, int) or (isinstance(name_or_id, str) and name_or_id.isdigit()):
            recipe_id = int(name_or_id)
            matched = next((r for r in recipes if r["id"] == recipe_id), None)
        else:
            name_lower = str(name_or_id).lower()
            for r in recipes:
                if name_lower in r.get("name", "").lower():
                    matched = r
                    break

        if not matched:
            return None

        # Get ingredients
        positions = await client.get_recipe_positions(matched["id"])
        products = await client.get_products()
        product_map = {p["id"]: p for p in products}

        # Get current stock
        stock = await client.get_stock()
        stock_map = {s.get("product_id"): s for s in stock}

        # Get fulfillment
        fulfillment = await client.get_recipe_fulfillment(matched["id"])

        ingredients_status = []
        for pos in positions:
            product_id = pos.get("product_id")
            product = product_map.get(product_id, {})
            stock_item = stock_map.get(product_id, {})

            required = pos.get("amount", 0)
            in_stock = stock_item.get("amount", 0)

            ingredients_status.append({
                "product": product.get("name", "Unknown"),
                "required": required,
                "in_stock": in_stock,
                "missing": max(0, required - in_stock),
                "fulfilled": in_stock >= required,
            })

        return {
            "id": matched.get("id"),
            "name": matched.get("name"),
            "description": matched.get("description"),
            "servings": matched.get("base_servings"),
            "is_fulfilled": fulfillment.get("recipe_fulfillment") == 1,
            "missing_products_count": fulfillment.get("missing_products_count", 0),
            "ingredients": ingredients_status,
        }

    # ==================== Chores ====================

    @mcp.tool()
    async def get_chores() -> list[dict]:
        """
        Get all chores with current status.

        Returns list of chores with next due dates.
        """
        client = _get_client()
        chores = await client.get_current_chores()
        return [
            {
                "id": c.get("chore_id"),
                "name": c.get("chore_name"),
                "next_estimated_execution_time": c.get("next_estimated_execution_time"),
                "last_tracked_time": c.get("last_tracked_time"),
                "track_count": c.get("track_count"),
            }
            for c in chores
        ]

    @mcp.tool()
    async def get_chore_details(name_or_id: str | int) -> dict | None:
        """
        Get detailed information about a specific chore.

        Args:
            name_or_id: Chore name or ID

        Returns chore details including next execution, history, etc.
        """
        client = _get_client()
        chores = await client.get_chores()

        matched = None
        if isinstance(name_or_id, int) or (isinstance(name_or_id, str) and name_or_id.isdigit()):
            chore_id = int(name_or_id)
            matched = next((c for c in chores if c["id"] == chore_id), None)
        else:
            name_lower = str(name_or_id).lower()
            for c in chores:
                if name_lower in c.get("name", "").lower():
                    matched = c
                    break

        if not matched:
            return None

        # Get detailed chore info
        chore_details = await client.get_chore(matched["id"])
        return {
            "id": matched.get("id"),
            "name": matched.get("name"),
            "description": matched.get("description"),
            "period_type": matched.get("period_type"),
            "period_days": matched.get("period_days"),
            "details": chore_details,
        }

    @mcp.tool()
    async def execute_chore(name_or_id: str | int) -> dict:
        """
        Mark a chore as executed.

        Args:
            name_or_id: Chore name or ID

        Returns confirmation.
        """
        client = _get_client()
        chores = await client.get_chores()

        matched = None
        if isinstance(name_or_id, int) or (isinstance(name_or_id, str) and name_or_id.isdigit()):
            chore_id = int(name_or_id)
            matched = next((c for c in chores if c["id"] == chore_id), None)
        else:
            name_lower = str(name_or_id).lower()
            for c in chores:
                if name_lower in c.get("name", "").lower():
                    matched = c
                    break

        if not matched:
            return {"error": "Chore not found"}

        await client.execute_chore(matched["id"])
        return {
            "success": True,
            "chore": matched.get("name"),
            "executed": True,
        }

    # ==================== Tasks ====================

    @mcp.tool()
    async def get_tasks() -> list[dict]:
        """
        Get all tasks.

        Returns list of tasks with status.
        """
        client = _get_client()
        tasks = await client.get_tasks()
        return [
            {
                "id": t.get("id"),
                "name": t.get("name"),
                "description": t.get("description"),
                "due_date": t.get("due_date"),
                "done": t.get("done", 0) == 1,
            }
            for t in tasks
        ]

    @mcp.tool()
    async def create_task(
        name: str,
        description: str | None = None,
        due_date: str | None = None,
    ) -> dict:
        """
        Create a new task.

        Args:
            name: Task name
            description: Task description
            due_date: Due date (YYYY-MM-DD)

        Returns created task.
        """
        client = _get_client()

        task_data = {"name": name}
        if description:
            task_data["description"] = description
        if due_date:
            task_data["due_date"] = due_date

        result = await client.create_task(task_data)
        return {"success": True, "task": result}

    @mcp.tool()
    async def complete_task(task_id: int) -> dict:
        """
        Mark a task as completed.

        Args:
            task_id: Task ID

        Returns confirmation.
        """
        client = _get_client()
        await client.complete_task(task_id)
        return {"success": True, "task_id": task_id, "completed": True}

    # ==================== Batteries ====================

    @mcp.tool()
    async def get_batteries() -> list[dict]:
        """
        Get all batteries with current charge status.

        Returns list of batteries with last charge dates.
        """
        client = _get_client()
        batteries = await client.get_current_batteries()
        return [
            {
                "id": b.get("battery_id"),
                "name": b.get("battery_name"),
                "last_tracked_time": b.get("last_tracked_time"),
                "next_estimated_charge_time": b.get("next_estimated_charge_time"),
            }
            for b in batteries
        ]

    @mcp.tool()
    async def get_battery_details(name_or_id: str | int) -> dict | None:
        """
        Get detailed information about a specific battery.

        Args:
            name_or_id: Battery name or ID

        Returns battery details including charge cycle info.
        """
        client = _get_client()
        batteries = await client.get_batteries()

        matched = None
        if isinstance(name_or_id, int) or (isinstance(name_or_id, str) and name_or_id.isdigit()):
            battery_id = int(name_or_id)
            matched = next((b for b in batteries if b["id"] == battery_id), None)
        else:
            name_lower = str(name_or_id).lower()
            for b in batteries:
                if name_lower in b.get("name", "").lower():
                    matched = b
                    break

        if not matched:
            return None

        # Get detailed battery info
        battery_details = await client.get_battery(matched["id"])
        return {
            "id": matched.get("id"),
            "name": matched.get("name"),
            "description": matched.get("description"),
            "charge_interval_days": matched.get("charge_interval_days"),
            "details": battery_details,
        }

    @mcp.tool()
    async def charge_battery(name_or_id: str | int) -> dict:
        """
        Track a battery charge.

        Args:
            name_or_id: Battery name or ID

        Returns confirmation.
        """
        client = _get_client()
        batteries = await client.get_batteries()

        matched = None
        if isinstance(name_or_id, int) or (isinstance(name_or_id, str) and name_or_id.isdigit()):
            battery_id = int(name_or_id)
            matched = next((b for b in batteries if b["id"] == battery_id), None)
        else:
            name_lower = str(name_or_id).lower()
            for b in batteries:
                if name_lower in b.get("name", "").lower():
                    matched = b
                    break

        if not matched:
            return {"error": "Battery not found"}

        await client.charge_battery(matched["id"])
        return {
            "success": True,
            "battery": matched.get("name"),
            "charged": True,
        }

    # ==================== Locations ====================

    @mcp.tool()
    async def get_locations() -> list[dict]:
        """
        Get all storage locations.

        Returns list of locations.
        """
        client = _get_client()
        locations = await client.get_locations()
        return [
            {
                "id": loc.get("id"),
                "name": loc.get("name"),
                "description": loc.get("description"),
                "is_freezer": loc.get("is_freezer", 0) == 1,
            }
            for loc in locations
        ]

    @mcp.tool()
    async def get_location_stock(name_or_id: str | int) -> list[dict]:
        """
        Get stock at a specific location.

        Args:
            name_or_id: Location name or ID

        Returns list of products at that location.
        """
        client = _get_client()
        locations = await client.get_locations()

        matched = None
        if isinstance(name_or_id, int) or (isinstance(name_or_id, str) and name_or_id.isdigit()):
            loc_id = int(name_or_id)
            matched = next((loc for loc in locations if loc["id"] == loc_id), None)
        else:
            name_lower = str(name_or_id).lower()
            for loc in locations:
                if name_lower in loc.get("name", "").lower():
                    matched = loc
                    break

        if not matched:
            return []

        stock = await client.get_location_stock(matched["id"])
        products = await client.get_products()
        product_map = {p["id"]: p for p in products}

        return [
            {
                "product": product_map.get(s.get("product_id"), {}).get("name", "Unknown"),
                "amount": s.get("amount"),
                "best_before_date": s.get("best_before_date"),
            }
            for s in stock
        ]

    # ==================== Product Groups ====================

    @mcp.tool()
    async def get_product_groups() -> list[dict]:
        """
        Get all product groups/categories.

        Returns list of product groups.
        """
        client = _get_client()
        groups = await client.get_product_groups()
        return [
            {
                "id": g.get("id"),
                "name": g.get("name"),
                "description": g.get("description"),
            }
            for g in groups
        ]

    # ==================== Products ====================

    @mcp.tool()
    async def get_products(search: str | None = None) -> list[dict]:
        """
        Get all products, optionally filtered by search term.

        Args:
            search: Optional search term to filter products

        Returns list of products.
        """
        client = _get_client()
        products = await client.get_products()

        if search:
            search_lower = search.lower()
            products = [p for p in products if search_lower in p.get("name", "").lower()]

        return [
            {
                "id": p.get("id"),
                "name": p.get("name"),
                "description": p.get("description"),
                "product_group_id": p.get("product_group_id"),
                "min_stock_amount": p.get("min_stock_amount"),
            }
            for p in products
        ]

    @mcp.tool()
    async def create_product(
        name: str,
        description: str | None = None,
        product_group_id: int | None = None,
        min_stock_amount: float = 0,
    ) -> dict:
        """
        Create a new product.

        Args:
            name: Product name
            description: Product description
            product_group_id: Product group ID
            min_stock_amount: Minimum stock level

        Returns created product.
        """
        client = _get_client()

        # Get default quantity unit
        units = await client.get_quantity_units()
        default_unit = units[0]["id"] if units else 1

        product_data = {
            "name": name,
            "qu_id_purchase": default_unit,
            "qu_id_stock": default_unit,
            "qu_factor_purchase_to_stock": 1,
            "min_stock_amount": min_stock_amount,
        }
        if description:
            product_data["description"] = description
        if product_group_id:
            product_data["product_group_id"] = product_group_id

        result = await client.create_product(product_data)
        return {"success": True, "product": result}

    # ==================== Generic CRUD ====================

    @mcp.tool()
    async def list_entities(entity_type: str) -> list[dict]:
        """
        List all entities of a specific type.

        Args:
            entity_type: Entity type (products, locations, product_groups, etc.)

        Returns list of entities.
        """
        client = _get_client()
        return await client.list_entities(entity_type)

    @mcp.tool()
    async def get_entity(entity_type: str, entity_id: int) -> dict:
        """
        Get a specific entity by type and ID.

        Args:
            entity_type: Entity type
            entity_id: Entity ID

        Returns entity details.
        """
        client = _get_client()
        return await client.get_entity(entity_type, entity_id)

    @mcp.tool()
    async def create_entity(entity_type: str, data: dict) -> dict:
        """
        Create a new entity.

        Args:
            entity_type: Entity type
            data: Entity data

        Returns created entity.
        """
        client = _get_client()
        result = await client.create_entity(entity_type, data)
        return {"success": True, "entity": result}

    @mcp.tool()
    async def update_entity(entity_type: str, entity_id: int, data: dict) -> dict:
        """
        Update an entity.

        Args:
            entity_type: Entity type
            entity_id: Entity ID
            data: Updated data

        Returns confirmation.
        """
        client = _get_client()
        await client.update_entity(entity_type, entity_id, data)
        return {"success": True, "entity_type": entity_type, "entity_id": entity_id}

    @mcp.tool()
    async def delete_entity(entity_type: str, entity_id: int) -> dict:
        """
        Delete an entity.

        Args:
            entity_type: Entity type
            entity_id: Entity ID

        Returns confirmation.
        """
        client = _get_client()
        await client.delete_entity(entity_type, entity_id)
        return {"success": True, "deleted": True, "entity_type": entity_type, "entity_id": entity_id}

    # ==================== Bulk Operations ====================

    @mcp.tool()
    async def bulk_get_stock(names: list[str]) -> list[dict]:
        """
        Get stock for multiple products in a single call.

        Args:
            names: List of product names to check

        Returns stock status for each product.
        """
        client = _get_client()
        products = await client.get_products()
        stock = await client.get_stock()

        product_map = {p.get("name", "").lower(): p for p in products}
        stock_map = {s.get("product_id"): s for s in stock}

        results = []
        for name in names:
            name_lower = name.lower()

            # Find product
            matched = product_map.get(name_lower)
            if not matched:
                for pname, prod in product_map.items():
                    if name_lower in pname:
                        matched = prod
                        break

            if matched:
                stock_item = stock_map.get(matched["id"], {})
                results.append({
                    "name": matched.get("name"),
                    "product_id": matched.get("id"),
                    "amount": stock_item.get("amount", 0),
                    "amount_opened": stock_item.get("amount_opened", 0),
                    "best_before_date": stock_item.get("best_before_date"),
                    "found": True,
                })
            else:
                results.append({
                    "name": name,
                    "found": False,
                })

        return results

    # ==================== BeerSmith Integration ====================

    @mcp.tool()
    async def list_brewing_ingredients(
        category: str | None = None,
        include_prices: bool = True,
    ) -> list[dict]:
        """
        List brewing ingredients from Grocy with pricing for BeerSmith integration.

        Args:
            category: Filter by product group (e.g., "Hops", "Grains", "Yeast")
            include_prices: Include price information from stock entries

        Returns list of brewing ingredients with prices suitable for BeerSmith import.
        """
        client = _get_client()

        products = await client.get_products()
        groups = await client.get_product_groups()
        stock = await client.get_stock()

        group_map = {g["id"]: g.get("name") for g in groups}
        stock_map = {s.get("product_id"): s for s in stock}

        # Filter by category if specified
        if category:
            category_lower = category.lower()
            target_group_ids = [
                g["id"] for g in groups
                if category_lower in g.get("name", "").lower()
            ]
            products = [
                p for p in products
                if p.get("product_group_id") in target_group_ids
            ]

        results = []
        for product in products:
            product_id = product.get("id")
            stock_item = stock_map.get(product_id, {})

            entry = {
                "id": product_id,
                "name": product.get("name"),
                "description": product.get("description"),
                "category": group_map.get(product.get("product_group_id"), "Uncategorized"),
                "in_stock": stock_item.get("amount", 0),
                "min_stock": product.get("min_stock_amount", 0),
            }

            if include_prices:
                # Try to get price from stock entries
                try:
                    entries = await client.get_product_stock_entries(product_id)
                    if entries:
                        # Get most recent price
                        prices = [e.get("price") for e in entries if e.get("price")]
                        if prices:
                            entry["last_price"] = prices[-1]
                            entry["avg_price"] = sum(prices) / len(prices)
                except Exception:
                    pass

            results.append(entry)

        return results

    @mcp.tool()
    async def get_quantity_units() -> list[dict]:
        """
        Get all quantity units defined in Grocy.

        Returns list of quantity units with their properties.
        """
        client = _get_client()
        units = await client.get_quantity_units()
        return [
            {
                "id": u.get("id"),
                "name": u.get("name"),
                "name_plural": u.get("name_plural"),
                "description": u.get("description"),
            }
            for u in units
        ]

    @mcp.tool()
    async def get_userfields(entity_type: str) -> list[dict]:
        """
        Get custom userfields for an entity type.

        Args:
            entity_type: Entity type (products, recipes, chores, etc.)

        Returns list of userfield definitions.
        """
        client = _get_client()
        try:
            userfields = await client.list_entities("userfields")
            return [
                uf for uf in userfields
                if uf.get("entity") == entity_type
            ]
        except Exception:
            return []
