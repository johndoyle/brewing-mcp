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
