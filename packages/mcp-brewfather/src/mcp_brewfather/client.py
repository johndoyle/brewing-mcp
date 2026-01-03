"""
Brewfather API client.
"""

import base64
from typing import Any
import httpx

from mcp_brewfather.config import BrewfatherConfig


class BrewfatherClient:
    """
    Client for interacting with the Brewfather REST API.

    See: https://docs.brewfather.app/api
    """

    def __init__(self, config: BrewfatherConfig):
        """
        Initialize the Brewfather client.

        Args:
            config: Brewfather configuration with credentials
        """
        self.config = config
        self.base_url = config.base_url

        # Brewfather uses Basic auth with user_id:api_key
        credentials = f"{config.user_id}:{config.api_key}"
        encoded = base64.b64encode(credentials.encode()).decode()

        self.headers = {
            "Authorization": f"Basic {encoded}",
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
        url = f"{self.base_url}{endpoint}"

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method,
                url,
                headers=self.headers,
                timeout=30.0,
                **kwargs,
            )
            response.raise_for_status()

            if response.status_code == 204:
                return None
            return response.json()

    # Recipes

    async def get_recipes(
        self,
        limit: int = 50,
        include_archived: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Get all recipes.

        Args:
            limit: Maximum recipes to return
            include_archived: Include archived recipes

        Returns:
            List of recipe objects
        """
        params = {"limit": limit}
        if include_archived:
            params["include"] = "archived"

        return await self._request("GET", "/recipes", params=params)

    async def get_recipe(self, recipe_id: str) -> dict[str, Any]:
        """
        Get a specific recipe by ID.

        Args:
            recipe_id: Recipe ID

        Returns:
            Recipe object
        """
        return await self._request("GET", f"/recipes/{recipe_id}")

    async def create_recipe(self, recipe: dict[str, Any]) -> dict[str, Any]:
        """
        Create a new recipe.

        Args:
            recipe: Recipe data

        Returns:
            Created recipe with ID
        """
        return await self._request("POST", "/recipes", json=recipe)

    async def update_recipe(
        self,
        recipe_id: str,
        recipe: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Update an existing recipe.

        Args:
            recipe_id: Recipe ID
            recipe: Updated recipe data

        Returns:
            Updated recipe
        """
        return await self._request("PATCH", f"/recipes/{recipe_id}", json=recipe)

    # Batches

    async def get_batches(
        self,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Get all batches.

        Args:
            status: Filter by status (Planning, Brewing, Fermenting, Conditioning, Completed)
            limit: Maximum batches to return

        Returns:
            List of batch objects
        """
        params = {"limit": limit}
        if status:
            params["status"] = status

        return await self._request("GET", "/batches", params=params)

    async def get_batch(self, batch_id: str) -> dict[str, Any]:
        """
        Get a specific batch by ID.

        Args:
            batch_id: Batch ID

        Returns:
            Batch object with full details
        """
        return await self._request("GET", f"/batches/{batch_id}")

    async def create_batch(
        self,
        recipe_id: str,
        name: str | None = None,
        brew_date: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a new batch from a recipe.

        Args:
            recipe_id: Recipe ID to brew
            name: Custom batch name
            brew_date: Brew date (ISO format)

        Returns:
            Created batch with ID
        """
        data = {"recipe": recipe_id}
        if name:
            data["name"] = name
        if brew_date:
            data["brewDate"] = brew_date

        return await self._request("POST", "/batches", json=data)

    async def update_batch(
        self,
        batch_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Update a batch.

        Args:
            batch_id: Batch ID
            updates: Fields to update

        Returns:
            Updated batch
        """
        return await self._request("PATCH", f"/batches/{batch_id}", json=updates)

    # Batch readings

    async def get_batch_readings(self, batch_id: str) -> list[dict[str, Any]]:
        """
        Get fermentation readings for a batch.

        Args:
            batch_id: Batch ID

        Returns:
            List of readings
        """
        return await self._request("GET", f"/batches/{batch_id}/readings")

    async def add_batch_reading(
        self,
        batch_id: str,
        gravity: float | None = None,
        temperature: float | None = None,
        note: str | None = None,
    ) -> dict[str, Any]:
        """
        Add a reading to a batch.

        Args:
            batch_id: Batch ID
            gravity: Gravity reading (e.g., 1.050)
            temperature: Temperature in Celsius
            note: Optional note

        Returns:
            Created reading
        """
        data = {}
        if gravity is not None:
            data["sg"] = gravity
        if temperature is not None:
            data["temp"] = temperature
        if note:
            data["comment"] = note

        return await self._request(
            "POST",
            f"/batches/{batch_id}/readings",
            json=data,
        )

    # Inventory (Premium feature)

    async def get_inventory(self) -> list[dict[str, Any]]:
        """
        Get inventory items.

        Returns:
            List of inventory items
        """
        return await self._request("GET", "/inventory")

    async def get_inventory_item(
        self,
        item_type: str,
        item_id: str,
    ) -> dict[str, Any]:
        """
        Get a specific inventory item.

        Args:
            item_type: Item type (fermentables, hops, yeasts, miscs)
            item_id: Item ID

        Returns:
            Inventory item details
        """
        return await self._request("GET", f"/inventory/{item_type}/{item_id}")

    # Additional Batch endpoints

    async def get_last_reading(self, batch_id: str) -> dict[str, Any] | None:
        """
        Get the last/latest reading for a batch.

        Args:
            batch_id: Batch ID

        Returns:
            Latest reading or None if no readings
        """
        try:
            return await self._request("GET", f"/batches/{batch_id}/readings/last")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise

    async def get_brewtracker(self, batch_id: str) -> dict[str, Any]:
        """
        Get brew tracker status for a batch.

        Args:
            batch_id: Batch ID

        Returns:
            Brew tracker status
        """
        return await self._request("GET", f"/batches/{batch_id}/brewtracker")

    async def update_batch_status(
        self,
        batch_id: str,
        status: str,
    ) -> dict[str, Any]:
        """
        Update batch status.

        Args:
            batch_id: Batch ID
            status: New status (Planning, Brewing, Fermenting, Conditioning, Completed, Archived)

        Returns:
            Updated batch
        """
        return await self._request("PATCH", f"/batches/{batch_id}", json={"status": status})

    async def update_batch_measurements(
        self,
        batch_id: str,
        measured_og: float | None = None,
        measured_fg: float | None = None,
        measured_batch_size: float | None = None,
        measured_boil_size: float | None = None,
        measured_efficiency: float | None = None,
        measured_abv: float | None = None,
        brew_date: int | None = None,
        fermentation_start_date: int | None = None,
        bottling_date: int | None = None,
    ) -> dict[str, Any]:
        """
        Update batch measurements.

        Args:
            batch_id: Batch ID
            measured_og: Measured original gravity
            measured_fg: Measured final gravity
            measured_batch_size: Measured batch size in liters
            measured_boil_size: Measured pre-boil size in liters
            measured_efficiency: Measured efficiency percentage
            measured_abv: Measured ABV percentage
            brew_date: Brew date as Unix timestamp (milliseconds)
            fermentation_start_date: Fermentation start date as Unix timestamp (ms)
            bottling_date: Bottling/kegging date as Unix timestamp (ms)

        Returns:
            Updated batch
        """
        data = {}
        if measured_og is not None:
            data["measuredOg"] = measured_og
        if measured_fg is not None:
            data["measuredFg"] = measured_fg
        if measured_batch_size is not None:
            data["measuredBatchSize"] = measured_batch_size
        if measured_boil_size is not None:
            data["measuredBoilSize"] = measured_boil_size
        if measured_efficiency is not None:
            data["measuredEfficiency"] = measured_efficiency
        if measured_abv is not None:
            data["measuredAbv"] = measured_abv
        if brew_date is not None:
            data["brewDate"] = brew_date
        if fermentation_start_date is not None:
            data["fermentationStartDate"] = fermentation_start_date
        if bottling_date is not None:
            data["bottlingDate"] = bottling_date

        return await self._request("PATCH", f"/batches/{batch_id}", json=data)

    # Inventory list endpoints with pagination

    async def list_fermentables(
        self,
        limit: int = 50,
        start_after: str | None = None,
        inventory_only: bool = False,
        include_inventory_amounts: bool = True,
    ) -> list[dict[str, Any]]:
        """
        List fermentables in inventory.

        Args:
            limit: Max items to return (max 50)
            start_after: ID to start after for pagination
            inventory_only: Only include items with inventory > 0
            include_inventory_amounts: Include inventory field

        Returns:
            List of fermentables
        """
        params = {"limit": min(limit, 50)}
        if start_after:
            params["start_after"] = start_after
        if inventory_only:
            params["inventory"] = "true"
        if include_inventory_amounts:
            params["include"] = "inventory"

        return await self._request("GET", "/inventory/fermentables", params=params)

    async def list_hops(
        self,
        limit: int = 50,
        start_after: str | None = None,
        inventory_only: bool = False,
        include_inventory_amounts: bool = True,
    ) -> list[dict[str, Any]]:
        """
        List hops in inventory.

        Args:
            limit: Max items to return (max 50)
            start_after: ID to start after for pagination
            inventory_only: Only include items with inventory > 0
            include_inventory_amounts: Include inventory field

        Returns:
            List of hops
        """
        params = {"limit": min(limit, 50)}
        if start_after:
            params["start_after"] = start_after
        if inventory_only:
            params["inventory"] = "true"
        if include_inventory_amounts:
            params["include"] = "inventory"

        return await self._request("GET", "/inventory/hops", params=params)

    async def list_yeasts(
        self,
        limit: int = 50,
        start_after: str | None = None,
        inventory_only: bool = False,
        include_inventory_amounts: bool = True,
    ) -> list[dict[str, Any]]:
        """
        List yeasts in inventory.

        Args:
            limit: Max items to return (max 50)
            start_after: ID to start after for pagination
            inventory_only: Only include items with inventory > 0
            include_inventory_amounts: Include inventory field

        Returns:
            List of yeasts
        """
        params = {"limit": min(limit, 50)}
        if start_after:
            params["start_after"] = start_after
        if inventory_only:
            params["inventory"] = "true"
        if include_inventory_amounts:
            params["include"] = "inventory"

        return await self._request("GET", "/inventory/yeasts", params=params)

    async def list_miscs(
        self,
        limit: int = 50,
        start_after: str | None = None,
        inventory_only: bool = False,
        include_inventory_amounts: bool = True,
    ) -> list[dict[str, Any]]:
        """
        List misc items in inventory.

        Args:
            limit: Max items to return (max 50)
            start_after: ID to start after for pagination
            inventory_only: Only include items with inventory > 0
            include_inventory_amounts: Include inventory field

        Returns:
            List of misc items
        """
        params = {"limit": min(limit, 50)}
        if start_after:
            params["start_after"] = start_after
        if inventory_only:
            params["inventory"] = "true"
        if include_inventory_amounts:
            params["include"] = "inventory"

        return await self._request("GET", "/inventory/miscs", params=params)

    # Inventory update endpoints

    async def update_fermentable_inventory(
        self,
        item_id: str,
        inventory: float | None = None,
        inventory_adjust: float | None = None,
    ) -> dict[str, Any]:
        """
        Update fermentable inventory amount.

        Args:
            item_id: Fermentable ID
            inventory: Set inventory to this value (kg)
            inventory_adjust: Adjust inventory by this amount (kg)

        Returns:
            Updated item
        """
        data = {}
        if inventory is not None:
            data["inventory"] = inventory
        elif inventory_adjust is not None:
            data["inventory_adjust"] = inventory_adjust

        return await self._request("PATCH", f"/inventory/fermentables/{item_id}", json=data)

    async def update_hop_inventory(
        self,
        item_id: str,
        inventory: float | None = None,
        inventory_adjust: float | None = None,
    ) -> dict[str, Any]:
        """
        Update hop inventory amount.

        Args:
            item_id: Hop ID
            inventory: Set inventory to this value (grams)
            inventory_adjust: Adjust inventory by this amount (grams)

        Returns:
            Updated item
        """
        data = {}
        if inventory is not None:
            data["inventory"] = inventory
        elif inventory_adjust is not None:
            data["inventory_adjust"] = inventory_adjust

        return await self._request("PATCH", f"/inventory/hops/{item_id}", json=data)

    async def update_yeast_inventory(
        self,
        item_id: str,
        inventory: float | None = None,
        inventory_adjust: float | None = None,
    ) -> dict[str, Any]:
        """
        Update yeast inventory amount.

        Args:
            item_id: Yeast ID
            inventory: Set inventory to this value (packages)
            inventory_adjust: Adjust inventory by this amount (packages)

        Returns:
            Updated item
        """
        data = {}
        if inventory is not None:
            data["inventory"] = inventory
        elif inventory_adjust is not None:
            data["inventory_adjust"] = inventory_adjust

        return await self._request("PATCH", f"/inventory/yeasts/{item_id}", json=data)

    async def update_misc_inventory(
        self,
        item_id: str,
        inventory: float | None = None,
        inventory_adjust: float | None = None,
    ) -> dict[str, Any]:
        """
        Update misc item inventory amount.

        Args:
            item_id: Misc item ID
            inventory: Set inventory to this value
            inventory_adjust: Adjust inventory by this amount

        Returns:
            Updated item
        """
        data = {}
        if inventory is not None:
            data["inventory"] = inventory
        elif inventory_adjust is not None:
            data["inventory_adjust"] = inventory_adjust

        return await self._request("PATCH", f"/inventory/miscs/{item_id}", json=data)

    # Paginated list helpers

    async def get_all_batches(
        self,
        status: str | None = None,
        complete: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Get all batches with automatic pagination.

        Args:
            status: Filter by status
            complete: Include complete batch data

        Returns:
            All batches
        """
        all_batches = []
        start_after = None

        while True:
            params = {"limit": 50}
            if status:
                params["status"] = status
            if complete:
                params["complete"] = "true"
            if start_after:
                params["start_after"] = start_after

            batches = await self._request("GET", "/batches", params=params)
            if not batches:
                break

            all_batches.extend(batches)
            if len(batches) < 50:
                break

            start_after = batches[-1].get("_id")

        return all_batches

    async def get_all_recipes(
        self,
        include_archived: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Get all recipes with automatic pagination.

        Args:
            include_archived: Include archived recipes

        Returns:
            All recipes
        """
        all_recipes = []
        start_after = None

        while True:
            params = {"limit": 50}
            if include_archived:
                params["include"] = "archived"
            if start_after:
                params["start_after"] = start_after

            recipes = await self._request("GET", "/recipes", params=params)
            if not recipes:
                break

            all_recipes.extend(recipes)
            if len(recipes) < 50:
                break

            start_after = recipes[-1].get("_id")

        return all_recipes
