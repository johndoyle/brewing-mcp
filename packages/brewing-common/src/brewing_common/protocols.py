"""
Abstract protocols/interfaces for brewing backend implementations.

These protocols define the contract that each brewing system adapter
must implement, enabling consistent behaviour across BeerSmith, Grocy,
and Brewfather integrations.
"""

from abc import abstractmethod
from typing import Protocol, runtime_checkable

from brewing_common.models import (
    NormalisedIngredient,
    Recipe,
    Batch,
    InventoryItem,
)


@runtime_checkable
class IngredientSource(Protocol):
    """
    Protocol for systems that can provide ingredients.

    Implemented by: BeerSmith (library), Brewfather (inventory)
    """

    @abstractmethod
    async def list_ingredients(
        self,
        ingredient_type: str | None = None,
    ) -> list[NormalisedIngredient]:
        """
        List all available ingredients.

        Args:
            ingredient_type: Optional filter by type (grain, hop, yeast, etc.)

        Returns:
            List of normalised ingredients
        """
        ...

    @abstractmethod
    async def get_ingredient(
        self,
        identifier: str,
    ) -> NormalisedIngredient | None:
        """
        Get a specific ingredient by ID or name.

        Args:
            identifier: Ingredient ID or name

        Returns:
            Normalised ingredient or None if not found
        """
        ...

    @abstractmethod
    async def search_ingredients(
        self,
        query: str,
        threshold: float = 0.7,
    ) -> list[tuple[NormalisedIngredient, float]]:
        """
        Search ingredients with fuzzy matching.

        Args:
            query: Search query
            threshold: Minimum match confidence (0.0 to 1.0)

        Returns:
            List of (ingredient, confidence) tuples
        """
        ...


@runtime_checkable
class RecipeSource(Protocol):
    """
    Protocol for systems that can provide recipes.

    Implemented by: BeerSmith, Brewfather
    """

    @abstractmethod
    async def list_recipes(self) -> list[Recipe]:
        """
        List all available recipes.

        Returns:
            List of normalised recipes
        """
        ...

    @abstractmethod
    async def get_recipe(
        self,
        identifier: str,
    ) -> Recipe | None:
        """
        Get a specific recipe by ID or name.

        Args:
            identifier: Recipe ID or name

        Returns:
            Normalised recipe or None if not found
        """
        ...

    @abstractmethod
    async def search_recipes(
        self,
        query: str,
        threshold: float = 0.7,
    ) -> list[tuple[Recipe, float]]:
        """
        Search recipes with fuzzy matching.

        Args:
            query: Search query
            threshold: Minimum match confidence (0.0 to 1.0)

        Returns:
            List of (recipe, confidence) tuples
        """
        ...


@runtime_checkable
class RecipeWriter(Protocol):
    """
    Protocol for systems that can create/update recipes.

    Implemented by: Brewfather
    """

    @abstractmethod
    async def create_recipe(self, recipe: Recipe) -> str:
        """
        Create a new recipe.

        Args:
            recipe: Recipe to create

        Returns:
            ID of created recipe
        """
        ...

    @abstractmethod
    async def update_recipe(
        self,
        identifier: str,
        recipe: Recipe,
    ) -> None:
        """
        Update an existing recipe.

        Args:
            identifier: Recipe ID
            recipe: Updated recipe data
        """
        ...


@runtime_checkable
class InventoryManager(Protocol):
    """
    Protocol for systems that manage ingredient inventory.

    Implemented by: Grocy
    """

    @abstractmethod
    async def get_inventory(self) -> list[InventoryItem]:
        """
        Get all inventory items.

        Returns:
            List of inventory items with stock levels
        """
        ...

    @abstractmethod
    async def get_stock(
        self,
        ingredient: NormalisedIngredient,
    ) -> float | None:
        """
        Get current stock level for an ingredient.

        Args:
            ingredient: The ingredient to check

        Returns:
            Current stock in grams, or None if not tracked
        """
        ...

    @abstractmethod
    async def add_stock(
        self,
        ingredient: NormalisedIngredient,
        amount_g: float,
    ) -> None:
        """
        Add to current stock.

        Args:
            ingredient: The ingredient
            amount_g: Amount to add in grams
        """
        ...

    @abstractmethod
    async def consume_stock(
        self,
        ingredient: NormalisedIngredient,
        amount_g: float,
    ) -> None:
        """
        Remove from current stock.

        Args:
            ingredient: The ingredient
            amount_g: Amount to consume in grams
        """
        ...

    @abstractmethod
    async def check_recipe_availability(
        self,
        recipe: Recipe,
    ) -> dict[str, dict]:
        """
        Check stock levels against recipe requirements.

        Args:
            recipe: The recipe to check

        Returns:
            Dictionary mapping ingredient names to availability info:
            {
                "ingredient_name": {
                    "required_g": float,
                    "available_g": float,
                    "sufficient": bool,
                    "shortage_g": float | None
                }
            }
        """
        ...


@runtime_checkable
class BatchTracker(Protocol):
    """
    Protocol for systems that track brewing batches/sessions.

    Implemented by: Brewfather
    """

    @abstractmethod
    async def list_batches(
        self,
        status: str | None = None,
    ) -> list[Batch]:
        """
        List all batches.

        Args:
            status: Optional filter by status (fermenting, conditioning, complete)

        Returns:
            List of batches
        """
        ...

    @abstractmethod
    async def get_batch(
        self,
        identifier: str,
    ) -> Batch | None:
        """
        Get a specific batch.

        Args:
            identifier: Batch ID or name

        Returns:
            Batch or None if not found
        """
        ...

    @abstractmethod
    async def create_batch(
        self,
        recipe: Recipe,
        brew_date: str | None = None,
    ) -> str:
        """
        Create a new batch from a recipe.

        Args:
            recipe: The recipe to brew
            brew_date: Optional brew date (ISO format)

        Returns:
            ID of created batch
        """
        ...

    @abstractmethod
    async def update_batch(
        self,
        identifier: str,
        **updates,
    ) -> None:
        """
        Update batch data (gravity readings, status, etc.).

        Args:
            identifier: Batch ID
            **updates: Fields to update
        """
        ...


@runtime_checkable
class ShoppingListManager(Protocol):
    """
    Protocol for systems that can manage shopping lists.

    Implemented by: Grocy
    """

    @abstractmethod
    async def get_shopping_list(self) -> list[tuple[NormalisedIngredient, float]]:
        """
        Get current shopping list.

        Returns:
            List of (ingredient, amount_g) tuples
        """
        ...

    @abstractmethod
    async def add_to_shopping_list(
        self,
        ingredient: NormalisedIngredient,
        amount_g: float,
    ) -> None:
        """
        Add ingredient to shopping list.

        Args:
            ingredient: The ingredient to add
            amount_g: Amount needed in grams
        """
        ...

    @abstractmethod
    async def add_recipe_shortages(
        self,
        recipe: Recipe,
    ) -> list[tuple[NormalisedIngredient, float]]:
        """
        Add all missing ingredients for a recipe to the shopping list.

        Args:
            recipe: The recipe to check

        Returns:
            List of (ingredient, shortage_g) tuples that were added
        """
        ...

    @abstractmethod
    async def clear_shopping_list(self) -> None:
        """Clear all items from the shopping list."""
        ...
