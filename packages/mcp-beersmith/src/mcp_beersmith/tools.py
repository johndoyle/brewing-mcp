"""MCP tool definitions for BeerSmith."""

import json
from pathlib import Path

from fastmcp import FastMCP

from mcp_beersmith.config import get_config
from mcp_beersmith.matching import IngredientMatcher
from mcp_beersmith.models import Recipe
from mcp_beersmith.parser import BeerSmithParser


def _get_parser() -> BeerSmithParser:
    """Get a configured BeerSmith parser."""
    config = get_config()
    return BeerSmithParser(str(config.library_path))


def _get_matcher() -> IngredientMatcher:
    """Get a configured ingredient matcher."""
    parser = _get_parser()
    return IngredientMatcher(
        hops=parser.get_hops(),
        grains=parser.get_grains(),
        yeasts=parser.get_yeasts(),
    )


def _load_currency_config() -> dict:
    """Load currency configuration."""
    config_path = Path(__file__).parent / "currency_config.json"
    if config_path.exists():
        return json.loads(config_path.read_text())
    return {
        "default_currency": "GBP",
        "default_weight_unit": "kg",
        "exchange_rates": {"USD": 0.79, "EUR": 0.86},
    }


def register_tools(mcp: FastMCP) -> None:
    """Register all BeerSmith MCP tools."""

    @mcp.tool()
    def list_recipes(folder: str | None = None, search: str | None = None) -> list[dict]:
        """
        List all available BeerSmith recipes.

        Args:
            folder: Filter by folder path (optional)
            search: Search term to filter recipes by name (optional)

        Returns a list of recipe summaries including name, style, OG, IBU, and ABV.
        """
        parser = _get_parser()
        recipes = parser.get_recipes(folder=folder, search=search)
        return [r.model_dump() for r in recipes]

    @mcp.tool()
    def get_recipe(name_or_id: str) -> dict | None:
        """
        Get a specific recipe by name or ID.

        Args:
            name_or_id: Recipe name or unique ID

        Returns full recipe details including all ingredients, or None if not found.
        """
        parser = _get_parser()
        recipe = parser.get_recipe(name_or_id)
        if recipe:
            return recipe.model_dump()
        return None

    @mcp.tool()
    def search_recipes_by_ingredient(ingredient_name: str, limit: int = 10) -> list[dict]:
        """
        Search for recipes containing a specific ingredient.

        Args:
            ingredient_name: Name of ingredient to search for
            limit: Maximum number of results (default 10)

        Returns list of recipes that use the specified ingredient.
        """
        parser = _get_parser()
        matcher = _get_matcher()
        recipes = parser.get_recipes()
        results = []

        for summary in recipes:
            recipe = parser.get_recipe(summary.id)
            if not recipe:
                continue

            # Check hops
            for hop in recipe.hops:
                match = matcher.match_hop(ingredient_name)
                if match and match.matched_name.lower() == hop.name.lower():
                    results.append({
                        "recipe": summary.name,
                        "ingredient": hop.name,
                        "type": "hop",
                        "amount_oz": hop.amount_oz,
                    })
                    break

            # Check grains
            for grain in recipe.grains:
                match = matcher.match_grain(ingredient_name)
                if match and match.matched_name.lower() == grain.name.lower():
                    results.append({
                        "recipe": summary.name,
                        "ingredient": grain.name,
                        "type": "grain",
                        "amount_oz": grain.amount_oz,
                    })
                    break

            if len(results) >= limit:
                break

        return results

    @mcp.tool()
    def list_hops(search: str | None = None, hop_type: int | None = None) -> list[dict]:
        """
        List hops from the BeerSmith database.

        Args:
            search: Search term to filter hops by name or origin (optional)
            hop_type: Filter by hop type (0=Bittering, 1=Aroma, 2=Both) (optional)

        Returns list of hops with their properties.
        """
        parser = _get_parser()
        hops = parser.get_hops(search=search, hop_type=hop_type)
        return [h.model_dump() for h in hops]

    @mcp.tool()
    def get_hop(name: str) -> dict | None:
        """
        Get a specific hop by name.

        Args:
            name: Hop name to search for

        Returns hop details or None if not found.
        """
        parser = _get_parser()
        hop = parser.get_hop(name)
        if hop:
            return hop.model_dump()
        return None

    @mcp.tool()
    def list_grains(search: str | None = None, grain_type: int | None = None) -> list[dict]:
        """
        List grains/fermentables from the BeerSmith database.

        Args:
            search: Search term to filter by name or origin (optional)
            grain_type: Filter by grain type (0=Base, 1=Specialty, etc.) (optional)

        Returns list of grains with their properties.
        """
        parser = _get_parser()
        grains = parser.get_grains(search=search, grain_type=grain_type)
        return [g.model_dump() for g in grains]

    @mcp.tool()
    def get_grain(name: str) -> dict | None:
        """
        Get a specific grain by name.

        Args:
            name: Grain name to search for

        Returns grain details or None if not found.
        """
        parser = _get_parser()
        grain = parser.get_grain(name)
        if grain:
            return grain.model_dump()
        return None

    @mcp.tool()
    def list_yeasts(search: str | None = None, lab: str | None = None) -> list[dict]:
        """
        List yeasts from the BeerSmith database.

        Args:
            search: Search term to filter by name, lab, or product ID (optional)
            lab: Filter by lab/manufacturer (optional)

        Returns list of yeasts with their properties.
        """
        parser = _get_parser()
        yeasts = parser.get_yeasts(search=search, lab=lab)
        return [y.model_dump() for y in yeasts]

    @mcp.tool()
    def get_yeast(name: str) -> dict | None:
        """
        Get a specific yeast by name or product ID.

        Args:
            name: Yeast name or product ID to search for

        Returns yeast details or None if not found.
        """
        parser = _get_parser()
        yeast = parser.get_yeast(name)
        if yeast:
            return yeast.model_dump()
        return None

    @mcp.tool()
    def list_water_profiles(search: str | None = None) -> list[dict]:
        """
        List water profiles from the BeerSmith database.

        Args:
            search: Search term to filter by name (optional)

        Returns list of water profiles with mineral content.
        """
        parser = _get_parser()
        waters = parser.get_water_profiles(search=search)
        return [w.model_dump() for w in waters]

    @mcp.tool()
    def get_water_profile(name: str) -> dict | None:
        """
        Get a specific water profile by name.

        Args:
            name: Water profile name to search for

        Returns water profile details or None if not found.
        """
        parser = _get_parser()
        water = parser.get_water_profile(name)
        if water:
            return water.model_dump()
        return None

    @mcp.tool()
    def list_styles(search: str | None = None, category: str | None = None) -> list[dict]:
        """
        List beer styles from the BeerSmith database.

        Args:
            search: Search term to filter by name or category (optional)
            category: Filter by style category (optional)

        Returns list of beer styles with parameters.
        """
        parser = _get_parser()
        styles = parser.get_styles(search=search, category=category)
        return [s.model_dump() for s in styles]

    @mcp.tool()
    def get_style(name: str) -> dict | None:
        """
        Get a specific beer style by name.

        Args:
            name: Style name to search for

        Returns style details or None if not found.
        """
        parser = _get_parser()
        style = parser.get_style(name)
        if style:
            return style.model_dump()
        return None

    @mcp.tool()
    def list_equipment() -> list[dict]:
        """
        List equipment profiles from BeerSmith.

        Returns list of equipment profiles with brewing parameters.
        """
        parser = _get_parser()
        equipment = parser.get_equipment_profiles()
        return [e.model_dump() for e in equipment]

    @mcp.tool()
    def get_equipment(name: str) -> dict | None:
        """
        Get a specific equipment profile by name.

        Args:
            name: Equipment profile name to search for

        Returns equipment details or None if not found.
        """
        parser = _get_parser()
        equipment = parser.get_equipment(name)
        if equipment:
            return equipment.model_dump()
        return None

    @mcp.tool()
    def list_mash_profiles() -> list[dict]:
        """
        List mash profiles from BeerSmith.

        Returns list of mash profiles with steps.
        """
        parser = _get_parser()
        profiles = parser.get_mash_profiles()
        return [p.model_dump() for p in profiles]

    @mcp.tool()
    def get_mash_profile(name: str) -> dict | None:
        """
        Get a specific mash profile by name.

        Args:
            name: Mash profile name to search for

        Returns mash profile with steps or None if not found.
        """
        parser = _get_parser()
        profile = parser.get_mash_profile(name)
        if profile:
            return profile.model_dump()
        return None

    @mcp.tool()
    def match_ingredients(
        names: list[str],
        ingredient_type: str | None = None,
        threshold: float = 70.0,
    ) -> dict[str, dict | None]:
        """
        Match ingredient names to BeerSmith database with fuzzy matching.

        Args:
            names: List of ingredient names to match
            ingredient_type: Filter by type (hop, grain, yeast) (optional)
            threshold: Minimum match confidence 0-100 (default 70)

        Returns dictionary mapping input names to matched ingredients.
        """
        matcher = _get_matcher()
        results = matcher.match_batch(names, ingredient_type, threshold)
        return {
            name: match.model_dump() if match else None
            for name, match in results.items()
        }

    @mcp.tool()
    def get_hop_substitutes(hop_name: str) -> list[str]:
        """
        Get substitute hops for a given hop variety.

        Args:
            hop_name: Name of hop to find substitutes for

        Returns list of substitute hop names.
        """
        matcher = _get_matcher()
        return matcher.get_hop_substitutes(hop_name)

    @mcp.tool()
    def suggest_recipes(
        style: str | None = None,
        ingredients: list[str] | None = None,
        og_min: float | None = None,
        og_max: float | None = None,
        ibu_min: float | None = None,
        ibu_max: float | None = None,
        limit: int = 5,
    ) -> list[dict]:
        """
        Suggest recipes based on criteria.

        Args:
            style: Desired beer style (optional)
            ingredients: Required ingredients (optional)
            og_min: Minimum original gravity (optional)
            og_max: Maximum original gravity (optional)
            ibu_min: Minimum IBU (optional)
            ibu_max: Maximum IBU (optional)
            limit: Maximum results (default 5)

        Returns list of matching recipes sorted by relevance.
        """
        parser = _get_parser()
        recipes = parser.get_recipes()
        results = []

        for summary in recipes:
            recipe = parser.get_recipe(summary.id)
            if not recipe:
                continue

            score = 0

            # Check style match
            if style and recipe.style:
                if style.lower() in recipe.style.name.lower():
                    score += 30

            # Check OG range
            if og_min and recipe.og < og_min:
                continue
            if og_max and recipe.og > og_max:
                continue
            if og_min or og_max:
                score += 10

            # Check IBU range
            if ibu_min and recipe.ibu < ibu_min:
                continue
            if ibu_max and recipe.ibu > ibu_max:
                continue
            if ibu_min or ibu_max:
                score += 10

            # Check ingredients
            if ingredients:
                recipe_ingredients = (
                    [h.name.lower() for h in recipe.hops] +
                    [g.name.lower() for g in recipe.grains] +
                    [y.name.lower() for y in recipe.yeasts]
                )
                matches = sum(
                    1 for ing in ingredients
                    if any(ing.lower() in ri for ri in recipe_ingredients)
                )
                score += matches * 20

            if score > 0:
                results.append({
                    "recipe": summary.model_dump(),
                    "score": score,
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    @mcp.tool()
    def validate_recipe(name_or_id: str) -> dict:
        """
        Validate a recipe for completeness and style compliance.

        Args:
            name_or_id: Recipe name or ID to validate

        Returns validation results with warnings and errors.
        """
        parser = _get_parser()
        recipe = parser.get_recipe(name_or_id)

        if not recipe:
            return {"valid": False, "errors": ["Recipe not found"], "warnings": []}

        errors = []
        warnings = []

        # Check for required components
        if not recipe.grains:
            errors.append("Recipe has no grains/fermentables")
        if not recipe.yeasts:
            errors.append("Recipe has no yeast")

        # Check for common issues
        if not recipe.hops:
            warnings.append("Recipe has no hops - is this intentional?")
        if recipe.og < 1.010:
            warnings.append(f"Very low OG ({recipe.og}) - check grain amounts")
        if recipe.ibu > 120:
            warnings.append(f"Very high IBU ({recipe.ibu}) - check hop amounts")

        # Style compliance
        if recipe.style:
            style = recipe.style
            if recipe.og < style.og_min or recipe.og > style.og_max:
                warnings.append(
                    f"OG {recipe.og} outside style range ({style.og_min}-{style.og_max})"
                )
            if recipe.ibu < style.ibu_min or recipe.ibu > style.ibu_max:
                warnings.append(
                    f"IBU {recipe.ibu} outside style range ({style.ibu_min}-{style.ibu_max})"
                )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "recipe_name": recipe.name,
        }

    @mcp.tool()
    def export_recipe_beerxml(name_or_id: str) -> str:
        """
        Export a recipe in BeerXML format.

        Args:
            name_or_id: Recipe name or ID to export

        Returns BeerXML string.
        """
        parser = _get_parser()
        recipe = parser.get_recipe(name_or_id)

        if not recipe:
            return "<error>Recipe not found</error>"

        return parser.export_recipe_beerxml(recipe)

    @mcp.tool()
    def update_ingredient(
        ingredient_type: str,
        ingredient_name: str,
        updates: dict,
    ) -> dict:
        """
        Update an ingredient in the BeerSmith database.

        Args:
            ingredient_type: Type of ingredient (hop, grain, yeast, misc)
            ingredient_name: Name of ingredient to update
            updates: Dictionary of field updates

        Returns success status and backup location.
        """
        parser = _get_parser()
        try:
            parser.update_ingredient(ingredient_type, ingredient_name, updates)
            return {
                "success": True,
                "ingredient": ingredient_name,
                "updates": updates,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    @mcp.tool()
    def convert_ingredient_price(
        price: float,
        from_currency: str = "USD",
        from_weight_unit: str = "lb",
    ) -> dict:
        """
        Convert ingredient price to default currency and weight unit.

        Args:
            price: Price in source currency/weight
            from_currency: Source currency code (default USD)
            from_weight_unit: Source weight unit (default lb)

        Returns converted price with exchange rate used.
        """
        config = _load_currency_config()
        target_currency = config["default_currency"]
        target_weight = config["default_weight_unit"]

        # Get exchange rate
        rate = 1.0
        if from_currency != target_currency:
            if from_currency == "USD":
                rate = config["exchange_rates"].get(target_currency, 1.0)
            elif from_currency in config["exchange_rates"]:
                usd_rate = 1.0 / config["exchange_rates"][from_currency]
                rate = usd_rate * config["exchange_rates"].get(target_currency, 1.0)

        # Weight conversion
        weight_factor = 1.0
        if from_weight_unit == "lb" and target_weight == "kg":
            weight_factor = 2.20462  # 1 kg = 2.20462 lb
        elif from_weight_unit == "oz" and target_weight == "kg":
            weight_factor = 35.274  # 1 kg = 35.274 oz
        elif from_weight_unit == "kg" and target_weight == "lb":
            weight_factor = 1 / 2.20462

        converted_price = price * rate * weight_factor

        return {
            "original_price": price,
            "original_currency": from_currency,
            "original_weight_unit": from_weight_unit,
            "converted_price": round(converted_price, 2),
            "target_currency": target_currency,
            "target_weight_unit": target_weight,
            "exchange_rate": rate,
        }
