"""MCP tool definitions for BeerSmith."""

import json
from pathlib import Path

from fastmcp import FastMCP

from mcp_beersmith.config import get_config
from mcp_beersmith.matching import IngredientMatcher
from mcp_beersmith.models import Recipe, RecipeGrain, RecipeHop, RecipeYeast, grams_to_oz
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
    """Load currency configuration from root config.json."""
    # Try root config first
    root_config_path = Path(__file__).parent.parent.parent.parent.parent.parent / "config.json"
    if root_config_path.exists():
        config = json.loads(root_config_path.read_text())
        return {
            "default_currency": config["currency"]["default"],
            "default_weight_unit": config["units"]["default_weight"],
            "beersmith_currency": config["currency"]["beersmith"],
            "grocy_currency": config["currency"]["grocy"],
            "exchange_rates": config["currency"]["exchange_rates"],
        }
    
    # Fallback to legacy config
    legacy_config_path = Path(__file__).parent / "currency_config.json"
    if legacy_config_path.exists():
        return json.loads(legacy_config_path.read_text())
    
    # Default values
    return {
        "default_currency": "GBP",
        "default_weight_unit": "kg",
        "beersmith_currency": "GBP",
        "grocy_currency": "GBP",
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
    def create_recipe(
        name: str,
        style_name: str,
        equipment_name: str,
        grains_json: str,
        hops_json: str,
        yeast_name: str,
        boil_time: float = 60.0,
        mash_profile_name: str = "",
        carbonation_profile_name: str = "",
        age_profile_name: str = "",
        brewer: str = "",
        notes: str = "",
    ) -> str:
        """
        Create a new recipe in BeerSmith.

        The recipe will be saved directly to BeerSmith and appear in the "MCP Created" folder.

        Args:
            name: Recipe name
            style_name: Target beer style (e.g., "American IPA")
            equipment_name: Equipment profile to use
            grains_json: JSON array of grains: [{"name": "Pale Malt", "amount_kg": 5.0}, ...]
            hops_json: JSON array of hops: [{"name": "Cascade", "amount_g": 50, "time": 60, "use": "boil"}, ...]
            yeast_name: Yeast strain name or product ID
            boil_time: Boil time in minutes (default 60)
            mash_profile_name: Mash profile name (optional, defaults to "Single Infusion")
            carbonation_profile_name: Carbonation profile (optional, defaults to "Keg")
            age_profile_name: Age/fermentation profile (optional, defaults to "Ale, Two Stage")
            brewer: Brewer name (optional)
            notes: Recipe notes (optional)

        Returns:
            Confirmation message with details
        """
        parser = _get_parser()

        # Parse JSON inputs
        try:
            grains_data = json.loads(grains_json)
            hops_data = json.loads(hops_json)
        except json.JSONDecodeError as e:
            return f"Error parsing JSON: {e}"

        # Get style
        style = parser.get_style(style_name)
        if not style:
            return f"Style '{style_name}' not found. Use list_styles to see available styles."

        # Get equipment
        equipment = parser.get_equipment(equipment_name)
        if not equipment:
            return f"Equipment '{equipment_name}' not found. Use list_equipment to see available profiles."

        # Check for unrealistic equipment settings
        warnings = []
        if equipment.hop_utilization > 50.0:
            warnings.append(
                f"⚠️  WARNING: Equipment hop utilization is {equipment.hop_utilization}% which is unrealistically high!\n"
                f"   Typical values: 20-30% for pellets, 15-20% for whole hops.\n"
                f"   This will cause IBU calculations to be much higher than expected.\n"
                f"   Consider updating your equipment profile's hop utilization setting."
            )

        # Get yeast
        yeast = parser.get_yeast(yeast_name)
        if not yeast:
            return f"Yeast '{yeast_name}' not found. Use list_yeasts to see available strains."

        # Get default settings from BeerSmith's DefRecipe.bsopt
        beersmith_defaults = parser.get_default_recipe_settings()

        # Get default profiles from most recent MCP-created recipe as secondary fallback
        mcp_default_profiles = None
        if not (mash_profile_name and carbonation_profile_name and age_profile_name):
            # Try to get the most recent MCP-created recipe to use its profiles as defaults
            try:
                mcp_recipes = parser.get_recipes(folder="/MCP Created/")
                if mcp_recipes:
                    # Get the most recent recipe (last in list)
                    recent_recipe = parser.get_recipe(mcp_recipes[-1].id)
                    if recent_recipe:
                        mcp_default_profiles = {
                            'mash': recent_recipe.mash,
                            'carbonation': recent_recipe.carbonation,
                            'age': recent_recipe.age,
                        }
            except Exception:
                pass  # Fall back to hardcoded defaults if this fails

        # Get mash profile
        # Priority: explicit param > BeerSmith default > MCP recipe default > hardcoded fallback
        if mash_profile_name:
            mash_profile = parser.get_mash_profile(mash_profile_name)
        elif beersmith_defaults.get('mash'):
            mash_profile = parser.get_mash_profile(beersmith_defaults['mash'])
        elif mcp_default_profiles and mcp_default_profiles['mash']:
            mash_profile = mcp_default_profiles['mash']
        else:
            mash_profile = parser.get_mash_profile("Single Infusion, Light Body, Batch Sparge")
            if not mash_profile:
                mash_profile = parser.get_mash_profile("Single Infusion")

        if not mash_profile:
            return "No suitable mash profile found. Please specify a mash_profile_name."

        # Get carbonation profile
        # Priority: explicit param > BeerSmith default > MCP recipe default > hardcoded fallback
        if carbonation_profile_name:
            carbonation_profile = parser.get_carbonation_profile(carbonation_profile_name)
        elif beersmith_defaults.get('carbonation'):
            carbonation_profile = parser.get_carbonation_profile(beersmith_defaults['carbonation'])
        elif mcp_default_profiles and mcp_default_profiles['carbonation']:
            carbonation_profile = mcp_default_profiles['carbonation']
        else:
            carbonation_profile = parser.get_carbonation_profile("Keg")
            if not carbonation_profile:
                carb_profiles = parser.get_carbonation_profiles()
                carbonation_profile = carb_profiles[0] if carb_profiles else None

        # Get age/fermentation profile
        # Priority: explicit param > BeerSmith default > MCP recipe default > hardcoded fallback
        if age_profile_name:
            age_profile = parser.get_age_profile(age_profile_name)
        elif beersmith_defaults.get('age'):
            age_profile = parser.get_age_profile(beersmith_defaults['age'])
        elif mcp_default_profiles and mcp_default_profiles['age']:
            age_profile = mcp_default_profiles['age']
        else:
            age_profile = parser.get_age_profile("Ale, Two Stage")
            if not age_profile:
                age_profile = parser.get_age_profile("Ale, Single Stage")

        # Use BeerSmith default brewer if not specified
        if not brewer and beersmith_defaults.get('brewer'):
            brewer = beersmith_defaults['brewer']

        # Build recipe
        recipe = Recipe(
            id="0",
            name=name,
            brewer=brewer,
            notes=notes,
            boil_time=boil_time,
            style=style,
            equipment=equipment,
            mash=mash_profile,
            carbonation=carbonation_profile,
            age=age_profile,
            folder="/MCP Created/",
        )

        # Add grains
        for grain_data in grains_data:
            grain = parser.get_grain(grain_data["name"])
            if not grain:
                return f"Grain '{grain_data['name']}' not found. Use list_grains to see available grains."

            amount_kg = grain_data.get("amount_kg", 0)
            recipe_grain = RecipeGrain(
                id=grain.id,
                name=grain.name,
                amount_oz=grams_to_oz(amount_kg * 1000),
                color=grain.color,
                yield_pct=grain.yield_pct,
                type=grain.type,
                origin=grain.origin,
                supplier=grain.supplier,
                notes=grain.notes,
                moisture=grain.moisture,
                diastatic_power=grain.diastatic_power,
                protein=grain.protein,
                max_in_batch=grain.max_in_batch,
                recommend_mash=grain.recommend_mash,
                inventory=grain.inventory,
                price=grain.price,
                use=0,  # Default to mash
                percent=0.0,  # Will be calculated by BeerSmith
                late_extract=0.0,
                add_after_boil=False,
            )
            recipe.grains.append(recipe_grain)

        # Add hops
        use_map = {"boil": 0, "dry hop": 1, "mash": 2, "first wort": 3, "whirlpool": 4}
        for hop_data in hops_data:
            hop = parser.get_hop(hop_data["name"])
            if not hop:
                return f"Hop '{hop_data['name']}' not found. Use list_hops to see available hops."

            recipe_hop = RecipeHop(
                id=hop.id,
                name=hop.name,
                amount_oz=grams_to_oz(hop_data.get("amount_g", 0)),
                alpha=hop.alpha,
                beta=hop.beta,
                boil_time=hop_data.get("time", 60),
                use=use_map.get(hop_data.get("use", "boil").lower(), 0),
                type=hop.type,
                form=hop.form,
                origin=hop.origin,
                notes=hop.notes,
                hsi=hop.hsi,
                inventory=hop.inventory,
                price=hop.price,
                dry_hop_time=3.0,  # Default 3 days
                ibu_contribution=0.0,  # Will be calculated by BeerSmith
            )
            recipe.hops.append(recipe_hop)

        # Add yeast
        recipe_yeast = RecipeYeast(
            id=yeast.id,
            name=yeast.name,
            lab=yeast.lab,
            product_id=yeast.product_id,
            type=yeast.type,
            form=yeast.form,
            flocculation=yeast.flocculation,
            min_attenuation=yeast.min_attenuation,
            max_attenuation=yeast.max_attenuation,
            min_temp_f=yeast.min_temp_f,
            max_temp_f=yeast.max_temp_f,
            tolerance=yeast.tolerance,
            best_for=yeast.best_for,
            notes=yeast.notes,
            inventory=yeast.inventory,
            price=yeast.price,
            amount=1,
            use_starter=False,
            add_to_secondary=False,
            starter_size=0.0,
        )
        recipe.yeasts.append(recipe_yeast)

        # Save recipe
        try:
            # Also save as exportable file for backup FIRST
            parser.save_recipe(recipe)
            export_path = parser.beersmith_path / "MCP_Exports"

            # Add recipe directly to BeerSmith's Recipe.bsmx
            try:
                parser.add_recipe_to_beersmith(recipe)
                database_status = "✅ Added to BeerSmith database"
            except Exception as db_error:
                database_status = f"⚠️  Database write failed: {str(db_error)}\n   Recipe exported to {export_path} but not added to database"

            warning_text = "\n\n".join(warnings) if warnings else ""
            warning_section = f"\n\n{warning_text}" if warnings else ""

            return (
                f"✅ Recipe '{name}' created successfully!\n\n"
                f"{database_status}\n\n"
                f"Look for it in the '/MCP Created/' folder.\n"
                f"A backup copy was saved to: {export_path}\n\n"
                f"**Recipe Parameters:**\n"
                f"- Boil Time: {boil_time} minutes\n"
                f"- Grains: {len(recipe.grains)} ({sum(g.amount_oz for g in recipe.grains) * 0.0283495:.2f} kg)\n"
                f"- Hops: {len(recipe.hops)} additions\n"
                f"- Equipment: {equipment.name} ({equipment.batch_vol_oz * 0.0295735:.1f}L batch, {equipment.efficiency}% efficiency)\n"
                f"{warning_section}\n\n"
                f"**Note:** You may need to restart BeerSmith to see the new recipe.\n"
                f"BeerSmith will calculate OG, FG, ABV, and IBU based on your grain bill and equipment settings."
            )
        except Exception as e:
            import traceback
            return f"Error saving recipe: {e}\n\nTraceback:\n{traceback.format_exc()}"

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
    def list_carbonation_profiles() -> list[dict]:
        """
        List carbonation profiles from BeerSmith.

        Returns list of carbonation profiles with carbonation methods and settings.
        """
        parser = _get_parser()
        profiles = parser.get_carbonation_profiles()
        return [p.model_dump() for p in profiles]

    @mcp.tool()
    def get_carbonation_profile(name: str) -> dict | None:
        """
        Get a specific carbonation profile by name.

        Args:
            name: Carbonation profile name to search for

        Returns carbonation profile details or None if not found.
        """
        parser = _get_parser()
        profile = parser.get_carbonation_profile(name)
        if profile:
            return profile.model_dump()
        return None

    @mcp.tool()
    def list_age_profiles() -> list[dict]:
        """
        List fermentation/aging profiles from BeerSmith.

        Returns list of fermentation and aging profiles with temperature schedules.
        """
        parser = _get_parser()
        profiles = parser.get_age_profiles()
        return [p.model_dump() for p in profiles]

    @mcp.tool()
    def get_age_profile(name: str) -> dict | None:
        """
        Get a specific fermentation/aging profile by name.

        Args:
            name: Fermentation/aging profile name to search for

        Returns fermentation profile with temperature schedule or None if not found.
        """
        parser = _get_parser()
        profile = parser.get_age_profile(name)
        if profile:
            return profile.model_dump()
        return None

    @mcp.tool()
    def get_default_recipe_settings() -> dict:
        """
        Get default recipe settings from BeerSmith's DefRecipe.bsopt file.

        Returns BeerSmith's default profile selections that will be used when creating new recipes.
        This includes equipment, mash, carbonation, age, style, and brewer name defaults.

        Returns dict with keys: equipment, mash, carbonation, age, style, brewer
        """
        parser = _get_parser()
        return parser.get_default_recipe_settings()

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
        ingredient_type: str,
        from_unit: str | None = None,
        from_currency: str | None = None,
        to_currency: str | None = None,
    ) -> str:
        """
        Convert ingredient prices from your local units/currency to BeerSmith's storage format.

        CRITICAL: BeerSmith stores ALL ingredient prices as price per OUNCE ($/oz or £/oz),
        including grains! When displaying in metric, BeerSmith multiplies by 35.274 to show price/kg.

        Args:
            price: The price value to convert
            ingredient_type: Type of ingredient - "grain", "hop", "yeast", or "misc"
            from_unit: Source unit (optional, defaults to kg) - "lb", "kg", "oz", "g", "pkg"
            from_currency: Source currency (optional, defaults to config) - "USD", "GBP", "EUR"
            to_currency: Target currency (optional, defaults to config)

        Returns:
            Markdown formatted conversion breakdown with ready-to-use JSON

        Example:
            # Convert £3.75/kg grain price
            convert_ingredient_price(3.75, "grain", "kg", "GBP", "GBP")
            # Result: £0.1063/oz (ready for BeerSmith)

            # Convert €25/kg hops from EUR to GBP
            convert_ingredient_price(25.0, "hop", "kg", "EUR", "GBP")
            # Result: £0.6095/oz

            # Grocy price: €0.003/g
            convert_ingredient_price(0.003, "grain", "g", "EUR", "GBP")
        """
        config = _load_currency_config()

        # Use config defaults if not specified
        from_unit = from_unit or config.get("default_weight_unit", "kg")
        from_currency = from_currency or config.get("default_currency", "GBP")
        to_currency = to_currency or config.get("beersmith_currency", "GBP")

        # CRITICAL: BeerSmith stores ALL prices as price per OUNCE
        beersmith_unit = "oz" if ingredient_type in ["grain", "hop", "misc"] else "pkg"

        # Unit conversion factors (FROM source TO ounces)
        unit_conversions = {
            ("kg", "oz"): 35.274,  # 1 kg = 35.274 oz
            ("lb", "oz"): 16.0,  # 1 lb = 16 oz
            ("g", "oz"): 0.035274,  # 1 g = 0.035274 oz
            ("oz", "oz"): 1.0,  # No conversion
            ("pkg", "pkg"): 1.0,  # No conversion
        }

        # Step 1: Currency conversion
        currency_rate = 1.0
        if from_currency != to_currency:
            # Try direct conversion
            rates = config.get("exchange_rates", {})
            if from_currency in rates:
                currency_rate = rates[from_currency]
            else:
                return f"Error: Exchange rate not found for {from_currency} in currency_config.json"

        price_in_target_currency = price * currency_rate

        # Step 2: Unit conversion
        unit_key = (from_unit, beersmith_unit)
        if unit_key not in unit_conversions:
            return f"Error: Unsupported unit conversion {from_unit}→{beersmith_unit}. Supported: kg, lb, g, oz, pkg"

        unit_factor = unit_conversions[unit_key]
        # Price per FROM_UNIT → Price per TO_UNIT: divide by conversion factor
        final_price = price_in_target_currency / unit_factor

        # Build detailed response
        lines = [
            f"# Price Conversion for {ingredient_type.title()}",
            "",
            f"**Input:** {from_currency}{price:.4f}/{from_unit}",
            "",
        ]

        # Show currency conversion if needed
        if from_currency != to_currency:
            lines.extend(
                [
                    "## Step 1: Currency Conversion",
                    f"- {from_currency}{price:.4f} × {currency_rate:.4f} = {to_currency}{price_in_target_currency:.4f}",
                    f"- Exchange rate: 1 {from_currency} = {currency_rate:.4f} {to_currency}",
                    "",
                ]
            )
        else:
            lines.append(f"✓ No currency conversion needed ({from_currency}={to_currency})\n")

        # Show unit conversion
        if from_unit != beersmith_unit:
            lines.extend(
                [
                    "## Step 2: Unit Conversion",
                    f"- {to_currency}{price_in_target_currency:.4f}/{from_unit} ÷ {unit_factor:.4f} = {to_currency}{final_price:.4f}/{beersmith_unit}",
                    f"- Conversion: 1 {from_unit} = {unit_factor:.4f} {beersmith_unit}",
                    f"- **IMPORTANT:** BeerSmith stores ALL prices as $/oz (or £/oz, €/oz)",
                    "",
                ]
            )
        else:
            lines.append(f"✓ No unit conversion needed ({from_unit}={beersmith_unit})\n")

        # Final result
        lines.extend(
            [
                "## Result",
                f"**BeerSmith Price:** {to_currency}{final_price:.4f}/{beersmith_unit}",
                "",
                "✅ Ready to use:",
                "```json",
                f'{{"price": {final_price:.4f}}}',
                "```",
                "",
                "Update command:",
                "```",
                f'update_ingredient("{ingredient_type}", "INGREDIENT_NAME", \'{{"price": {final_price:.4f}}}\')' "",
            ]
        )

        return "\n".join(lines)
