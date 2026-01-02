"""Grocy API client."""

from typing import Any

import httpx

from mcp_grocy.config import GrocyConfig


class GrocyClient:
    """
    Client for interacting with the Grocy REST API.

    See: https://github.com/grocy/grocy/wiki/API-Reference
    """

    def __init__(self, config: GrocyConfig):
        """
        Initialize the Grocy client.

        Args:
            config: Grocy configuration with URL and API key
        """
        self.config = config
        self.base_url = config.url.rstrip("/")
        self.headers = {
            "GROCY-API-KEY": config.api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs,
    ) -> Any:
        """Make an API request."""
        url = f"{self.base_url}/api{endpoint}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method,
                url,
                headers=self.headers,
                **kwargs,
            )
            response.raise_for_status()

            if response.status_code == 204:
                return None
            if not response.content:
                return None
            return response.json()

    # ==================== System ====================

    async def get_system_info(self) -> dict[str, Any]:
        """Get Grocy system information."""
        return await self._request("GET", "/system/info")

    async def get_system_config(self) -> dict[str, Any]:
        """Get Grocy system configuration."""
        return await self._request("GET", "/system/config")

    async def get_db_changed_time(self) -> dict[str, Any]:
        """Get last database change time."""
        return await self._request("GET", "/system/db-changed-time")

    # ==================== Products ====================

    async def get_products(self) -> list[dict[str, Any]]:
        """Get all products."""
        return await self._request("GET", "/objects/products")

    async def get_product(self, product_id: int) -> dict[str, Any]:
        """Get a specific product."""
        return await self._request("GET", f"/objects/products/{product_id}")

    async def create_product(self, product_data: dict[str, Any]) -> dict[str, Any]:
        """Create a new product."""
        return await self._request("POST", "/objects/products", json=product_data)

    async def update_product(self, product_id: int, product_data: dict[str, Any]) -> dict[str, Any]:
        """Update a product."""
        return await self._request("PUT", f"/objects/products/{product_id}", json=product_data)

    async def delete_product(self, product_id: int) -> None:
        """Delete a product."""
        await self._request("DELETE", f"/objects/products/{product_id}")

    async def search_products(self, query: str) -> list[dict[str, Any]]:
        """Search products by name."""
        products = await self.get_products()
        query_lower = query.lower()
        return [p for p in products if query_lower in p.get("name", "").lower()]

    # ==================== Stock ====================

    async def get_stock(self) -> list[dict[str, Any]]:
        """Get current stock for all products."""
        return await self._request("GET", "/stock")

    async def get_volatile_stock(self) -> dict[str, Any]:
        """Get volatile stock (expiring soon, already expired, etc.)."""
        return await self._request("GET", "/stock/volatile")

    async def get_product_stock(self, product_id: int) -> dict[str, Any]:
        """Get stock details for a specific product."""
        return await self._request("GET", f"/stock/products/{product_id}")

    async def get_product_price_history(self, product_id: int) -> list[dict[str, Any]]:
        """Get price history for a product."""
        return await self._request("GET", f"/stock/products/{product_id}/price-history")

    async def add_product_stock(
        self,
        product_id: int,
        amount: float,
        best_before_date: str | None = None,
        price: float | None = None,
        location_id: int | None = None,
        note: str | None = None,
    ) -> dict[str, Any]:
        """
        Add stock for a product (purchase).

        Args:
            product_id: Product ID
            amount: Amount to add
            best_before_date: Optional best before date (YYYY-MM-DD)
            price: Optional unit price
            location_id: Optional location ID
            note: Optional note

        Returns:
            Transaction details
        """
        data: dict[str, Any] = {"amount": amount}
        if best_before_date:
            data["best_before_date"] = best_before_date
        if price is not None:
            data["price"] = price
        if location_id is not None:
            data["location_id"] = location_id
        if note:
            data["note"] = note

        return await self._request(
            "POST",
            f"/stock/products/{product_id}/add",
            json=data,
        )

    async def consume_product_stock(
        self,
        product_id: int,
        amount: float,
        spoiled: bool = False,
        stock_entry_id: int | None = None,
        recipe_id: int | None = None,
        location_id: int | None = None,
    ) -> dict[str, Any]:
        """
        Consume stock for a product.

        Args:
            product_id: Product ID
            amount: Amount to consume
            spoiled: Whether the stock was spoiled
            stock_entry_id: Specific stock entry to consume from
            recipe_id: Recipe this consumption is for
            location_id: Location to consume from

        Returns:
            Transaction details
        """
        data: dict[str, Any] = {"amount": amount, "spoiled": spoiled}
        if stock_entry_id is not None:
            data["stock_entry_id"] = stock_entry_id
        if recipe_id is not None:
            data["recipe_id"] = recipe_id
        if location_id is not None:
            data["location_id"] = location_id

        return await self._request(
            "POST",
            f"/stock/products/{product_id}/consume",
            json=data,
        )

    async def transfer_product_stock(
        self,
        product_id: int,
        amount: float,
        location_id_from: int,
        location_id_to: int,
    ) -> dict[str, Any]:
        """Transfer stock between locations."""
        return await self._request(
            "POST",
            f"/stock/products/{product_id}/transfer",
            json={
                "amount": amount,
                "location_id_from": location_id_from,
                "location_id_to": location_id_to,
            },
        )

    async def inventory_product(
        self,
        product_id: int,
        new_amount: float,
        best_before_date: str | None = None,
        location_id: int | None = None,
    ) -> dict[str, Any]:
        """
        Set inventory level for a product (stocktaking).

        Args:
            product_id: Product ID
            new_amount: New stock amount
            best_before_date: Optional best before date
            location_id: Optional location ID

        Returns:
            Transaction details
        """
        data: dict[str, Any] = {"new_amount": new_amount}
        if best_before_date:
            data["best_before_date"] = best_before_date
        if location_id is not None:
            data["location_id"] = location_id

        return await self._request(
            "POST",
            f"/stock/products/{product_id}/inventory",
            json=data,
        )

    async def open_product(self, product_id: int, amount: float = 1) -> dict[str, Any]:
        """Mark a product as opened."""
        return await self._request(
            "POST",
            f"/stock/products/{product_id}/open",
            json={"amount": amount},
        )

    async def get_product_by_barcode(self, barcode: str) -> dict[str, Any]:
        """
        Look up a product by barcode.

        Args:
            barcode: Product barcode

        Returns:
            Product details with stock information
        """
        return await self._request("GET", f"/stock/products/by-barcode/{barcode}")

    async def get_product_stock_entries(self, product_id: int) -> list[dict[str, Any]]:
        """
        Get all stock entries for a product.

        Args:
            product_id: Product ID

        Returns:
            List of stock entries with details (purchase date, price, location, etc.)
        """
        return await self._request("GET", f"/stock/products/{product_id}/entries")

    async def add_expired_products_to_shopping_list(self, list_id: int = 1) -> None:
        """Add all expired products to shopping list."""
        await self._request(
            "POST",
            "/stock/shoppinglist/add-expired-products",
            json={"list_id": list_id},
        )

    async def add_overdue_products_to_shopping_list(self, list_id: int = 1) -> None:
        """Add all overdue products to shopping list."""
        await self._request(
            "POST",
            "/stock/shoppinglist/add-overdue-products",
            json={"list_id": list_id},
        )

    # ==================== Shopping List ====================

    async def get_shopping_list(self, list_id: int | None = None) -> list[dict[str, Any]]:
        """Get shopping list items."""
        items = await self._request("GET", "/objects/shopping_list")
        if list_id is not None:
            items = [i for i in items if i.get("shopping_list_id") == list_id]
        return items

    async def add_to_shopping_list(
        self,
        product_id: int,
        amount: float,
        note: str | None = None,
        shopping_list_id: int = 1,
    ) -> dict[str, Any]:
        """
        Add item to shopping list.

        Args:
            product_id: Product ID
            amount: Amount needed
            note: Optional note
            shopping_list_id: Shopping list ID (default 1)

        Returns:
            Created shopping list item
        """
        data: dict[str, Any] = {
            "product_id": product_id,
            "amount": amount,
            "shopping_list_id": shopping_list_id,
        }
        if note:
            data["note"] = note

        return await self._request("POST", "/objects/shopping_list", json=data)

    async def update_shopping_list_item(
        self,
        item_id: int,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        """Update a shopping list item."""
        return await self._request("PUT", f"/objects/shopping_list/{item_id}", json=updates)

    async def remove_from_shopping_list(self, item_id: int) -> None:
        """Remove item from shopping list."""
        await self._request("DELETE", f"/objects/shopping_list/{item_id}")

    async def clear_shopping_list(self, list_id: int = 1) -> None:
        """Clear all items from shopping list."""
        await self._request("POST", "/stock/shoppinglist/clear", json={"list_id": list_id})

    async def add_missing_products_to_shopping_list(self, list_id: int = 1) -> None:
        """Add all products below min stock to shopping list."""
        await self._request(
            "POST",
            "/stock/shoppinglist/add-missing-products",
            json={"list_id": list_id},
        )

    # ==================== Recipes ====================

    async def get_recipes(self) -> list[dict[str, Any]]:
        """Get all recipes."""
        return await self._request("GET", "/objects/recipes")

    async def get_recipe(self, recipe_id: int) -> dict[str, Any]:
        """Get a specific recipe."""
        return await self._request("GET", f"/objects/recipes/{recipe_id}")

    async def get_recipe_fulfillment(self, recipe_id: int) -> dict[str, Any]:
        """Get fulfillment status for a recipe."""
        return await self._request("GET", f"/recipes/{recipe_id}/fulfillment")

    async def get_all_recipes_fulfillment(self) -> list[dict[str, Any]]:
        """Get fulfillment status for all recipes."""
        return await self._request("GET", "/recipes/fulfillment")

    async def consume_recipe(self, recipe_id: int) -> dict[str, Any]:
        """Consume all ingredients for a recipe."""
        return await self._request("POST", f"/recipes/{recipe_id}/consume")

    async def add_recipe_to_shopping_list(
        self,
        recipe_id: int,
        excludes: list[int] | None = None,
    ) -> None:
        """Add recipe's missing ingredients to shopping list."""
        data: dict[str, Any] = {}
        if excludes:
            data["excludedProductIds"] = excludes
        await self._request(
            "POST",
            f"/recipes/{recipe_id}/add-not-fulfilled-products-to-shoppinglist",
            json=data,
        )

    async def create_recipe(self, recipe_data: dict[str, Any]) -> dict[str, Any]:
        """Create a new recipe."""
        return await self._request("POST", "/objects/recipes", json=recipe_data)

    async def get_recipe_positions(self, recipe_id: int) -> list[dict[str, Any]]:
        """Get ingredients for a recipe."""
        positions = await self._request("GET", "/objects/recipes_pos")
        return [p for p in positions if p.get("recipe_id") == recipe_id]

    async def add_recipe_ingredient(
        self,
        recipe_id: int,
        product_id: int,
        amount: float,
        note: str | None = None,
    ) -> dict[str, Any]:
        """Add ingredient to a recipe."""
        data: dict[str, Any] = {
            "recipe_id": recipe_id,
            "product_id": product_id,
            "amount": amount,
        }
        if note:
            data["note"] = note
        return await self._request("POST", "/objects/recipes_pos", json=data)

    # ==================== Chores ====================

    async def get_chores(self) -> list[dict[str, Any]]:
        """Get all chores."""
        return await self._request("GET", "/objects/chores")

    async def get_chore(self, chore_id: int) -> dict[str, Any]:
        """Get a specific chore."""
        return await self._request("GET", f"/chores/{chore_id}")

    async def execute_chore(
        self,
        chore_id: int,
        done_by: int | None = None,
        tracked_time: str | None = None,
    ) -> dict[str, Any]:
        """Mark a chore as executed."""
        data: dict[str, Any] = {}
        if done_by is not None:
            data["done_by"] = done_by
        if tracked_time:
            data["tracked_time"] = tracked_time
        return await self._request("POST", f"/chores/{chore_id}/execute", json=data)

    async def get_current_chores(self) -> list[dict[str, Any]]:
        """Get current chore status."""
        return await self._request("GET", "/chores")

    # ==================== Tasks ====================

    async def get_tasks(self) -> list[dict[str, Any]]:
        """Get all tasks."""
        return await self._request("GET", "/objects/tasks")

    async def get_task(self, task_id: int) -> dict[str, Any]:
        """Get a specific task."""
        return await self._request("GET", f"/objects/tasks/{task_id}")

    async def create_task(self, task_data: dict[str, Any]) -> dict[str, Any]:
        """Create a new task."""
        return await self._request("POST", "/objects/tasks", json=task_data)

    async def complete_task(self, task_id: int) -> dict[str, Any]:
        """Mark a task as completed."""
        return await self._request("POST", f"/tasks/{task_id}/complete")

    # ==================== Batteries ====================

    async def get_batteries(self) -> list[dict[str, Any]]:
        """Get all batteries."""
        return await self._request("GET", "/objects/batteries")

    async def get_battery(self, battery_id: int) -> dict[str, Any]:
        """Get battery charge status."""
        return await self._request("GET", f"/batteries/{battery_id}")

    async def charge_battery(self, battery_id: int, tracked_time: str | None = None) -> dict[str, Any]:
        """Track a battery charge."""
        data: dict[str, Any] = {}
        if tracked_time:
            data["tracked_time"] = tracked_time
        return await self._request("POST", f"/batteries/{battery_id}/charge", json=data)

    async def get_current_batteries(self) -> list[dict[str, Any]]:
        """Get current battery status for all batteries."""
        return await self._request("GET", "/batteries")

    # ==================== Locations ====================

    async def get_locations(self) -> list[dict[str, Any]]:
        """Get all storage locations."""
        return await self._request("GET", "/objects/locations")

    async def get_location(self, location_id: int) -> dict[str, Any]:
        """Get a specific location."""
        return await self._request("GET", f"/objects/locations/{location_id}")

    async def get_location_stock(self, location_id: int) -> list[dict[str, Any]]:
        """Get stock at a specific location."""
        return await self._request("GET", f"/stock/locations/{location_id}/entries")

    # ==================== Product Groups ====================

    async def get_product_groups(self) -> list[dict[str, Any]]:
        """Get all product groups."""
        return await self._request("GET", "/objects/product_groups")

    async def get_product_group(self, group_id: int) -> dict[str, Any]:
        """Get a specific product group."""
        return await self._request("GET", f"/objects/product_groups/{group_id}")

    # ==================== Quantity Units ====================

    async def get_quantity_units(self) -> list[dict[str, Any]]:
        """Get all quantity units."""
        return await self._request("GET", "/objects/quantity_units")

    async def get_quantity_unit_conversions(self) -> list[dict[str, Any]]:
        """Get quantity unit conversions."""
        return await self._request("GET", "/objects/quantity_unit_conversions")

    async def get_product_quantity_conversions(self, product_id: int) -> list[dict[str, Any]]:
        """Get quantity conversions for a specific product."""
        conversions = await self.get_quantity_unit_conversions()
        return [c for c in conversions if c.get("product_id") == product_id]

    # ==================== Generic CRUD ====================

    async def get_entity(self, entity_type: str, entity_id: int) -> dict[str, Any]:
        """Get a specific entity by type and ID."""
        return await self._request("GET", f"/objects/{entity_type}/{entity_id}")

    async def list_entities(self, entity_type: str) -> list[dict[str, Any]]:
        """List all entities of a type."""
        return await self._request("GET", f"/objects/{entity_type}")

    async def create_entity(self, entity_type: str, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new entity."""
        return await self._request("POST", f"/objects/{entity_type}", json=data)

    async def update_entity(
        self,
        entity_type: str,
        entity_id: int,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Update an entity."""
        return await self._request("PUT", f"/objects/{entity_type}/{entity_id}", json=data)

    async def delete_entity(self, entity_type: str, entity_id: int) -> None:
        """Delete an entity."""
        await self._request("DELETE", f"/objects/{entity_type}/{entity_id}")
