"""Parser for BeerSmith .bsmx XML files."""

import html
import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, TypeVar

from lxml import etree
from pydantic import BaseModel

from mcp_beersmith.models import (
    AgeProfile,
    Carbonation,
    Equipment,
    Grain,
    Hop,
    MashProfile,
    MashStep,
    Misc,
    Recipe,
    RecipeGrain,
    RecipeHop,
    RecipeMisc,
    RecipeSummary,
    RecipeWater,
    RecipeYeast,
    Style,
    Water,
    Yeast,
)

T = TypeVar("T", bound=BaseModel)

# Default BeerSmith data path on macOS
DEFAULT_BEERSMITH_PATH = os.path.expanduser("~/Library/Application Support/BeerSmith3")

# HTML entities that need to be converted for XML parsing
HTML_ENTITIES = {
    '&ldquo;': '"',
    '&rdquo;': '"',
    '&lsquo;': "'",
    '&rsquo;': "'",
    '&ndash;': '-',
    '&mdash;': '--',
    '&nbsp;': ' ',
    '&auml;': 'ä',
    '&ouml;': 'ö',
    '&uuml;': 'ü',
    '&Auml;': 'Ä',
    '&Ouml;': 'Ö',
    '&Uuml;': 'Ü',
    '&szlig;': 'ß',
    '&eacute;': 'é',
    '&egrave;': 'è',
    '&aacute;': 'á',
    '&iacute;': 'í',
    '&oacute;': 'ó',
    '&uacute;': 'ú',
    '&ntilde;': 'ñ',
    '&copy;': '©',
    '&reg;': '®',
    '&trade;': '™',
    '&deg;': '°',
    '&plusmn;': '±',
    '&frac12;': '½',
    '&frac14;': '¼',
    '&frac34;': '¾',
    '&times;': '×',
    '&divide;': '÷',
    '&aring;': 'å',
    '&Aring;': 'Å',
    '&ordm;': 'º',
    '&shy;': '',
    '&hellip;': '...',
    '&bull;': '•',
    '&middot;': '·',
    '&cedil;': '¸',
    '&ccedil;': 'ç',
    '&Ccedil;': 'Ç',
}


class BeerSmithParser:
    """Parser for BeerSmith .bsmx files."""

    def __init__(self, beersmith_path: str | None = None):
        """Initialize parser with BeerSmith data path."""
        self.beersmith_path = Path(beersmith_path or DEFAULT_BEERSMITH_PATH)
        self.backup_path = self.beersmith_path / "mcp_backups"
        self._cache: dict[str, tuple[float, Any]] = {}

    def _xml_escape(self, text: str) -> str:
        """Escape text for XML."""
        text = html.escape(text)
        result = []
        for char in text:
            if ord(char) > 127:
                result.append(f'&#{ord(char)};')
            else:
                result.append(char)
        return ''.join(result)

    def _get_file_path(self, filename: str) -> Path:
        """Get full path to a BeerSmith file."""
        return self.beersmith_path / filename

    def _parse_xml_file(self, filename: str) -> etree._Element | None:
        """Parse a .bsmx XML file and return the root element."""
        filepath = self._get_file_path(filename)
        if not filepath.exists():
            return None

        mtime = filepath.stat().st_mtime
        if filename in self._cache:
            cached_mtime, cached_data = self._cache[filename]
            if cached_mtime == mtime:
                return cached_data

        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        for entity, replacement in HTML_ENTITIES.items():
            content = content.replace(entity, replacement)
        
        content = re.sub(r'&#(\d+);', lambda m: chr(int(m.group(1))), content)
        content = re.sub(r'&#x([0-9a-fA-F]+);', lambda m: chr(int(m.group(1), 16)), content)

        try:
            parser = etree.XMLParser(recover=True, encoding='utf-8')
            root = etree.fromstring(content.encode('utf-8'), parser=parser)
            self._cache[filename] = (mtime, root)
            return root
        except etree.XMLSyntaxError:
            return None

    def _element_to_dict(self, element: etree._Element) -> dict[str, Any]:
        """Convert an XML element to a dictionary with lowercase keys."""
        result = {}
        for child in element:
            tag = child.tag.lower()
            if len(child) > 0:
                result[tag] = self._element_to_dict(child)
            else:
                text = child.text or ""
                text = html.unescape(text)
                result[tag] = self._convert_value(text)
        return result

    def _convert_value(self, text: str) -> Any:
        """Convert string value to appropriate Python type."""
        if not text:
            return ""
        try:
            if "." not in text:
                return int(text)
        except ValueError:
            pass
        try:
            return float(text)
        except ValueError:
            pass
        return text

    def _parse_items(self, root: etree._Element, item_tag: str, model_class: type[T]) -> list[T]:
        """Parse all items of a given type from an XML root."""
        items = []
        for data in root.iter("Data"):
            for item_elem in data.findall(item_tag):
                try:
                    item_dict = self._element_to_dict(item_elem)
                    item = model_class.model_validate(item_dict)
                    items.append(item)
                except Exception:
                    continue
        return items

    def get_hops(self, search: str | None = None, hop_type: int | None = None) -> list[Hop]:
        """Get all hops, optionally filtered."""
        root = self._parse_xml_file("Hops.bsmx")
        if root is None:
            return []
        hops = self._parse_items(root, "Hops", Hop)
        if search:
            search_lower = search.lower()
            hops = [h for h in hops if search_lower in h.name.lower() or search_lower in h.origin.lower()]
        if hop_type is not None:
            hops = [h for h in hops if h.type == hop_type]
        return sorted(hops, key=lambda h: h.name)

    def get_hop(self, name: str) -> Hop | None:
        """Get a specific hop by name."""
        hops = self.get_hops(search=name)
        for hop in hops:
            if hop.name.lower() == name.lower():
                return hop
        return hops[0] if hops else None

    def get_grains(self, search: str | None = None, grain_type: int | None = None) -> list[Grain]:
        """Get all grains/fermentables, optionally filtered."""
        root = self._parse_xml_file("Grain.bsmx")
        if root is None:
            return []
        grains = self._parse_items(root, "Grain", Grain)
        if search:
            search_lower = search.lower()
            grains = [g for g in grains if search_lower in g.name.lower() or search_lower in g.origin.lower()]
        if grain_type is not None:
            grains = [g for g in grains if g.type == grain_type]
        return sorted(grains, key=lambda g: g.name)

    def get_grain(self, name: str) -> Grain | None:
        """Get a specific grain by name."""
        grains = self.get_grains(search=name)
        for grain in grains:
            if grain.name.lower() == name.lower():
                return grain
        return grains[0] if grains else None

    def get_yeasts(self, search: str | None = None, lab: str | None = None) -> list[Yeast]:
        """Get all yeasts, optionally filtered."""
        root = self._parse_xml_file("Yeast.bsmx")
        if root is None:
            return []
        yeasts = self._parse_items(root, "Yeast", Yeast)
        if search:
            search_lower = search.lower()
            yeasts = [y for y in yeasts if search_lower in y.name.lower() or 
                      search_lower in y.lab.lower() or search_lower in y.product_id.lower()]
        if lab:
            lab_lower = lab.lower()
            yeasts = [y for y in yeasts if lab_lower in y.lab.lower()]
        return sorted(yeasts, key=lambda y: (y.lab, y.name))

    def get_yeast(self, name: str) -> Yeast | None:
        """Get a specific yeast by name or product ID."""
        yeasts = self.get_yeasts(search=name)
        for yeast in yeasts:
            if yeast.name.lower() == name.lower() or yeast.product_id.lower() == name.lower():
                return yeast
        return yeasts[0] if yeasts else None

    def get_water_profiles(self, search: str | None = None) -> list[Water]:
        """Get all water profiles, optionally filtered."""
        root = self._parse_xml_file("Water.bsmx")
        if root is None:
            return []
        waters = self._parse_items(root, "Water", Water)
        if search:
            search_lower = search.lower()
            waters = [w for w in waters if search_lower in w.name.lower()]
        return sorted(waters, key=lambda w: w.name)

    def get_water_profile(self, name: str) -> Water | None:
        """Get a specific water profile by name."""
        waters = self.get_water_profiles(search=name)
        for water in waters:
            if water.name.lower() == name.lower():
                return water
        return waters[0] if waters else None

    def get_styles(self, search: str | None = None, category: str | None = None) -> list[Style]:
        """Get all beer styles, optionally filtered."""
        root = self._parse_xml_file("Style.bsmx")
        if root is None:
            return []
        styles = self._parse_items(root, "Style", Style)
        if search:
            search_lower = search.lower()
            styles = [s for s in styles if search_lower in s.name.lower() or search_lower in s.category.lower()]
        if category:
            cat_lower = category.lower()
            styles = [s for s in styles if cat_lower in s.category.lower()]
        return sorted(styles, key=lambda s: (s.category, s.name))

    def get_style(self, name: str) -> Style | None:
        """Get a specific style by name."""
        styles = self.get_styles(search=name)
        for style in styles:
            if style.name.lower() == name.lower():
                return style
        return styles[0] if styles else None

    def get_equipment_profiles(self) -> list[Equipment]:
        """Get all equipment profiles.

        Note: Equipment.bsmx has a non-standard XML structure with multiple root elements.
        Standard profiles are in <Equipment><Data>, user-defined profiles are sibling roots.
        """
        if "Equipment.bsmx" in self._cache:
            del self._cache["Equipment.bsmx"]

        # Special handling for Equipment.bsmx with multiple root elements
        filepath = self.beersmith_path / "Equipment.bsmx"
        if not filepath.exists():
            return []

        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        # Replace HTML entities
        for entity, replacement in HTML_ENTITIES.items():
            content = content.replace(entity, replacement)
        content = re.sub(r'&#(\d+);', lambda m: chr(int(m.group(1))), content)
        content = re.sub(r'&#x([0-9a-fA-F]+);', lambda m: chr(int(m.group(1), 16)), content)

        # Wrap in fake root to handle multiple root elements
        wrapped_content = f"<root>{content}</root>"

        try:
            parser = etree.XMLParser(recover=True, encoding='utf-8')
            root = etree.fromstring(wrapped_content.encode('utf-8'), parser=parser)
        except etree.XMLSyntaxError:
            return []

        equipment = []

        # Parse standard equipment profiles from within <Data> elements
        for data in root.iter("Data"):
            for equip_elem in data.findall("Equipment"):
                try:
                    equip_dict = self._element_to_dict(equip_elem)
                    equip = Equipment.model_validate(equip_dict)
                    equipment.append(equip)
                except Exception:
                    continue

        # Parse user-defined equipment profiles at root level
        # These are <Equipment> elements that are direct children of our fake root
        # BeerSmith stores version history, so we may see duplicates - keep the last one
        user_equipment = {}
        for equip_elem in root.findall("Equipment"):
            # Skip the container element (has <Data> child)
            if equip_elem.find("Data") is not None:
                continue
            try:
                equip_dict = self._element_to_dict(equip_elem)
                equip = Equipment.model_validate(equip_dict)
                # Use name as key - last occurrence wins
                user_equipment[equip.name] = equip
            except Exception:
                continue

        equipment.extend(user_equipment.values())

        return sorted(equipment, key=lambda e: e.name)

    def get_equipment(self, name: str) -> Equipment | None:
        """Get a specific equipment profile by name."""
        equipment_list = self.get_equipment_profiles()
        for equipment in equipment_list:
            if equipment.name.lower() == name.lower():
                return equipment
        for equipment in equipment_list:
            if name.lower() in equipment.name.lower():
                return equipment
        return None

    def get_mash_profiles(self) -> list[MashProfile]:
        """Get all mash profiles.

        Note: Mash.bsmx has a non-standard XML structure with multiple root elements.
        Standard profiles are in <Mash><Data>, user-defined profiles are sibling roots.
        """
        # Special handling for Mash.bsmx with multiple root elements
        filepath = self.beersmith_path / "Mash.bsmx"
        if not filepath.exists():
            return []

        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        # Replace HTML entities
        for entity, replacement in HTML_ENTITIES.items():
            content = content.replace(entity, replacement)
        content = re.sub(r'&#(\d+);', lambda m: chr(int(m.group(1))), content)
        content = re.sub(r'&#x([0-9a-fA-F]+);', lambda m: chr(int(m.group(1), 16)), content)

        # Wrap in fake root to handle multiple root elements
        wrapped_content = f"<root>{content}</root>"

        try:
            parser = etree.XMLParser(recover=True, encoding='utf-8')
            root = etree.fromstring(wrapped_content.encode('utf-8'), parser=parser)
        except etree.XMLSyntaxError:
            return []

        profiles = []

        # Parse standard mash profiles from within <Data> elements
        for data in root.iter("Data"):
            for mash_elem in data.findall("Mash"):
                try:
                    mash_dict = self._element_to_dict(mash_elem)
                    mash = MashProfile.model_validate(mash_dict)
                    steps_elem = mash_elem.find("steps")
                    if steps_elem is not None:
                        steps_data = steps_elem.find("Data")
                        if steps_data is not None:
                            for step_elem in steps_data.findall("MashStep"):
                                step_dict = self._element_to_dict(step_elem)
                                step = MashStep.model_validate(step_dict)
                                mash.steps.append(step)
                    profiles.append(mash)
                except Exception:
                    pass

        # Parse user-defined mash profiles at root level
        # BeerSmith stores version history, so we may see duplicates - keep the last one
        user_profiles = {}
        for mash_elem in root.findall("Mash"):
            # Skip the container element (has <Data> child)
            if mash_elem.find("Data") is not None:
                continue
            try:
                mash_dict = self._element_to_dict(mash_elem)
                mash = MashProfile.model_validate(mash_dict)
                steps_elem = mash_elem.find("steps")
                if steps_elem is not None:
                    steps_data = steps_elem.find("Data")
                    if steps_data is not None:
                        for step_elem in steps_data.findall("MashStep"):
                            step_dict = self._element_to_dict(step_elem)
                            step = MashStep.model_validate(step_dict)
                            mash.steps.append(step)
                # Use name as key - last occurrence wins
                user_profiles[mash.name] = mash
            except Exception:
                pass

        profiles.extend(user_profiles.values())

        return sorted(profiles, key=lambda m: m.name)

    def get_mash_profile(self, name: str) -> MashProfile | None:
        """Get a specific mash profile by name."""
        profiles = self.get_mash_profiles()
        for profile in profiles:
            if profile.name.lower() == name.lower():
                return profile
        for profile in profiles:
            if name.lower() in profile.name.lower():
                return profile
        return None

    def get_carbonation_profiles(self) -> list[Carbonation]:
        """Get all carbonation profiles.

        Note: Carbonation.bsmx has a non-standard XML structure with multiple root elements.
        Standard profiles are in <Carbonation><Data>, user-defined profiles are sibling roots.
        """
        # Special handling for Carbonation.bsmx with multiple root elements
        filepath = self.beersmith_path / "Carbonation.bsmx"
        if not filepath.exists():
            return []

        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        # Replace HTML entities
        for entity, replacement in HTML_ENTITIES.items():
            content = content.replace(entity, replacement)
        content = re.sub(r'&#(\d+);', lambda m: chr(int(m.group(1))), content)
        content = re.sub(r'&#x([0-9a-fA-F]+);', lambda m: chr(int(m.group(1), 16)), content)

        # Wrap in fake root to handle multiple root elements
        wrapped_content = f"<root>{content}</root>"

        try:
            parser = etree.XMLParser(recover=True, encoding='utf-8')
            root = etree.fromstring(wrapped_content.encode('utf-8'), parser=parser)
        except etree.XMLSyntaxError:
            return []

        profiles = []

        # Parse standard carbonation profiles from within <Data> elements
        for data in root.iter("Data"):
            for carb_elem in data.findall("Carbonation"):
                try:
                    carb_dict = self._element_to_dict(carb_elem)
                    carb = Carbonation.model_validate(carb_dict)
                    profiles.append(carb)
                except Exception:
                    pass

        # Parse user-defined carbonation profiles at root level
        # BeerSmith stores version history, so we may see duplicates - keep the last one
        user_profiles = {}
        for carb_elem in root.findall("Carbonation"):
            # Skip the container element (has <Data> child)
            if carb_elem.find("Data") is not None:
                continue
            try:
                carb_dict = self._element_to_dict(carb_elem)
                carb = Carbonation.model_validate(carb_dict)
                # Use name as key - last occurrence wins
                user_profiles[carb.name] = carb
            except Exception:
                pass

        profiles.extend(user_profiles.values())

        return sorted(profiles, key=lambda c: c.name)

    def get_carbonation_profile(self, name: str) -> Carbonation | None:
        """Get a specific carbonation profile by name."""
        profiles = self.get_carbonation_profiles()
        for profile in profiles:
            if profile.name.lower() == name.lower():
                return profile
        for profile in profiles:
            if name.lower() in profile.name.lower():
                return profile
        return None

    def get_age_profiles(self) -> list[AgeProfile]:
        """Get all fermentation/aging profiles.

        Note: Age.bsmx has a non-standard XML structure with multiple root elements.
        Standard profiles are in <Selections><Data>, user-defined profiles are sibling roots.
        """
        # Special handling for Age.bsmx with multiple root elements
        filepath = self.beersmith_path / "Age.bsmx"
        if not filepath.exists():
            return []

        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        # Replace HTML entities
        for entity, replacement in HTML_ENTITIES.items():
            content = content.replace(entity, replacement)
        content = re.sub(r'&#(\d+);', lambda m: chr(int(m.group(1))), content)
        content = re.sub(r'&#x([0-9a-fA-F]+);', lambda m: chr(int(m.group(1), 16)), content)

        # Wrap in fake root to handle multiple root elements
        wrapped_content = f"<root>{content}</root>"

        try:
            parser = etree.XMLParser(recover=True, encoding='utf-8')
            root = etree.fromstring(wrapped_content.encode('utf-8'), parser=parser)
        except etree.XMLSyntaxError:
            return []

        profiles = []

        # Parse standard age profiles from within <Data> elements
        for data in root.iter("Data"):
            for age_elem in data.findall("Age"):
                try:
                    age_dict = self._element_to_dict(age_elem)
                    age = AgeProfile.model_validate(age_dict)
                    profiles.append(age)
                except Exception:
                    pass

        # Parse user-defined age profiles at root level
        # BeerSmith stores version history, so we may see duplicates - keep the last one
        user_profiles = {}
        for age_elem in root.findall("Age"):
            # Skip age elements that are inside <Data> (already processed above)
            # We only want direct children of our fake root
            parent = age_elem.getparent()
            if parent is not None and parent.tag == "Data":
                continue
            try:
                age_dict = self._element_to_dict(age_elem)
                age = AgeProfile.model_validate(age_dict)
                # Use name as key - last occurrence wins
                user_profiles[age.name] = age
            except Exception:
                pass

        profiles.extend(user_profiles.values())

        return sorted(profiles, key=lambda a: a.name)

    def get_age_profile(self, name: str) -> AgeProfile | None:
        """Get a specific age profile by name."""
        profiles = self.get_age_profiles()
        for profile in profiles:
            if profile.name.lower() == name.lower():
                return profile
        for profile in profiles:
            if name.lower() in profile.name.lower():
                return profile
        return None

    def get_misc_ingredients(self, search: str | None = None) -> list[Misc]:
        """Get all miscellaneous ingredients."""
        root = self._parse_xml_file("Misc.bsmx")
        if root is None:
            return []
        miscs = self._parse_items(root, "Misc", Misc)
        if search:
            search_lower = search.lower()
            miscs = [m for m in miscs if search_lower in m.name.lower()]
        return sorted(miscs, key=lambda m: m.name)

    def _parse_recipe_element(self, recipe_elem: etree._Element) -> Recipe | None:
        """Parse a single recipe element into a Recipe object."""
        try:
            recipe_dict = self._element_to_dict(recipe_elem)
            recipe = Recipe.model_validate(recipe_dict)

            style_elem = recipe_elem.find("F_R_STYLE")
            if style_elem is not None:
                style_dict = self._element_to_dict(style_elem)
                recipe.style = Style.model_validate(style_dict)

            equip_elem = recipe_elem.find("F_R_EQUIPMENT")
            if equip_elem is not None:
                equip_dict = self._element_to_dict(equip_elem)
                recipe.equipment = Equipment.model_validate(equip_dict)

            mash_elem = recipe_elem.find("F_R_MASH")
            if mash_elem is not None:
                mash_dict = self._element_to_dict(mash_elem)
                recipe.mash = MashProfile.model_validate(mash_dict)
                steps_elem = mash_elem.find("steps")
                if steps_elem is not None:
                    steps_data = steps_elem.find("Data")
                    if steps_data is not None:
                        for step_elem in steps_data.findall("MashStep"):
                            step_dict = self._element_to_dict(step_elem)
                            step = MashStep.model_validate(step_dict)
                            recipe.mash.steps.append(step)

            carb_elem = recipe_elem.find("F_R_CARB")
            if carb_elem is not None:
                carb_dict = self._element_to_dict(carb_elem)
                recipe.carbonation = Carbonation.model_validate(carb_dict)

            age_elem = recipe_elem.find("F_R_AGE")
            if age_elem is not None:
                age_dict = self._element_to_dict(age_elem)
                recipe.age = AgeProfile.model_validate(age_dict)

            ingredients_elem = recipe_elem.find("Ingredients")
            if ingredients_elem is not None:
                ingredients_data = ingredients_elem.find("Data")
                if ingredients_data is not None:
                    for grain_elem in ingredients_data.findall("Grain"):
                        grain_dict = self._element_to_dict(grain_elem)
                        grain = RecipeGrain.model_validate(grain_dict)
                        recipe.grains.append(grain)
                    for hop_elem in ingredients_data.findall("Hops"):
                        hop_dict = self._element_to_dict(hop_elem)
                        hop = RecipeHop.model_validate(hop_dict)
                        recipe.hops.append(hop)
                    for yeast_elem in ingredients_data.findall("Yeast"):
                        yeast_dict = self._element_to_dict(yeast_elem)
                        yeast = RecipeYeast.model_validate(yeast_dict)
                        recipe.yeasts.append(yeast)
                    for misc_elem in ingredients_data.findall("Misc"):
                        misc_dict = self._element_to_dict(misc_elem)
                        misc = RecipeMisc.model_validate(misc_dict)
                        recipe.miscs.append(misc)
                    for water_elem in ingredients_data.findall("Water"):
                        water_dict = self._element_to_dict(water_elem)
                        water = RecipeWater.model_validate(water_dict)
                        recipe.waters.append(water)
            return recipe
        except Exception:
            return None

    def _find_recipes_recursive(self, element: etree._Element, folder_path: str = "/") -> list[Recipe]:
        """Recursively find all recipes in folders."""
        recipes = []
        for table in element.findall("Table"):
            table_name = table.findtext("Name", "")
            folder_data = table.find("Data")
            if folder_data is not None:
                new_folder = f"{folder_path}{table_name}/"
                recipes.extend(self._find_recipes_recursive(folder_data, new_folder))
        for recipe_elem in element.findall("Recipe"):
            recipe = self._parse_recipe_element(recipe_elem)
            if recipe:
                if not recipe.folder or recipe.folder == "/":
                    recipe.folder = folder_path
                recipes.append(recipe)
        for cloud_elem in element.findall("Cloud"):
            recipe_data = cloud_elem.find("F_C_RECIPE")
            if recipe_data is not None:
                recipe = self._parse_recipe_element(recipe_data)
                if recipe:
                    if not recipe.folder or recipe.folder == "/":
                        recipe.folder = folder_path
                    recipes.append(recipe)
        for data in element.findall("Data"):
            recipes.extend(self._find_recipes_recursive(data, folder_path))
        return recipes

    def get_recipes(self, folder: str | None = None, search: str | None = None) -> list[RecipeSummary]:
        """Get all recipes as summaries."""
        recipes = []
        root = self._parse_xml_file("Recipe.bsmx")
        if root is not None:
            recipes.extend(self._find_recipes_recursive(root))
        cloud_root = self._parse_xml_file("Cloud.bsmx")
        if cloud_root is not None:
            recipes.extend(self._find_recipes_recursive(cloud_root, folder_path="/Cloud/"))
        if folder:
            folder_lower = folder.lower()
            recipes = [r for r in recipes if folder_lower in r.folder.lower()]
        if search:
            search_lower = search.lower()
            recipes = [r for r in recipes if search_lower in r.name.lower()]
        summaries = []
        for r in recipes:
            summaries.append(RecipeSummary(
                id=r.id, name=r.name, style=r.style.name if r.style else "",
                og=r.og, fg=r.fg, ibu=r.ibu, abv=r.abv, color_srm=r.color_srm, folder=r.folder,
            ))
        return sorted(summaries, key=lambda r: (r.folder, r.name))

    def get_recipe(self, name_or_id: str) -> Recipe | None:
        """Get a specific recipe by name or ID."""
        recipes = []
        root = self._parse_xml_file("Recipe.bsmx")
        if root is not None:
            recipes.extend(self._find_recipes_recursive(root))
        cloud_root = self._parse_xml_file("Cloud.bsmx")
        if cloud_root is not None:
            recipes.extend(self._find_recipes_recursive(cloud_root, folder_path="/Cloud/"))
        for recipe in recipes:
            if recipe.id == name_or_id:
                return recipe
        name_lower = name_or_id.lower()
        for recipe in recipes:
            if recipe.name.lower() == name_lower:
                return recipe
        for recipe in recipes:
            if name_lower in recipe.name.lower():
                return recipe
        return None

    def create_backup(self, filename: str) -> Path:
        """Create a backup of a file before modifying it."""
        source = self._get_file_path(filename)
        if not source.exists():
            raise FileNotFoundError(f"Cannot backup {filename}: file does not exist")
        timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        backup_dir = self.backup_path / timestamp
        backup_dir.mkdir(parents=True, exist_ok=True)
        dest = backup_dir / filename
        shutil.copy2(source, dest)
        manifest = backup_dir / "manifest.json"
        manifest.write_text(json.dumps({
            "timestamp": timestamp, "files": [filename], "reason": "MCP server modification"
        }, indent=2))
        return dest

    def _generate_recipe_xml(self, recipe: Recipe) -> str:
        """Generate XML string for a recipe."""
        lines = [
            f"<Recipe><_PERMID_>{recipe.id}</_PERMID_>",
            f"<_MOD_>{datetime.now().strftime('%Y-%m-%d')}</_MOD_>",
            f"<F_R_NAME>{self._xml_escape(recipe.name)}</F_R_NAME>",
            f"<F_R_BREWER>{self._xml_escape(recipe.brewer)}</F_R_BREWER>",
            f"<F_R_FOLDER_NAME>{self._xml_escape(recipe.folder)}</F_R_FOLDER_NAME>",
            f"<F_R_OG>{recipe.og:.7f}</F_R_OG>",
            f"<F_R_FG>{recipe.fg:.7f}</F_R_FG>",
            f"<F_R_IBU>{recipe.ibu:.7f}</F_R_IBU>",
            f"<F_R_COLOR>{recipe.color_srm:.7f}</F_R_COLOR>",
            f"<F_R_ABV>{recipe.abv:.7f}</F_R_ABV>",
            f"<F_R_BOIL_TIME>{recipe.boil_time:.7f}</F_R_BOIL_TIME>",
            f"<F_R_NOTES>{self._xml_escape(recipe.notes)}</F_R_NOTES>",
        ]
        if recipe.style:
            lines.extend([
                "<F_R_STYLE>",
                f"<F_S_NAME>{self._xml_escape(recipe.style.name)}</F_S_NAME>",
                f"<F_S_CATEGORY>{self._xml_escape(recipe.style.category)}</F_S_CATEGORY>",
                "</F_R_STYLE>",
            ])
        if recipe.equipment:
            lines.extend([
                "<F_R_EQUIPMENT>",
                f"<F_E_NAME>{self._xml_escape(recipe.equipment.name)}</F_E_NAME>",
                f"<F_E_EFFICIENCY>{recipe.equipment.efficiency:.7f}</F_E_EFFICIENCY>",
                "</F_R_EQUIPMENT>",
            ])
        lines.append("<Ingredients><Data>")
        for grain in recipe.grains:
            lines.extend([
                "<Grain>",
                f"<F_G_NAME>{self._xml_escape(grain.name)}</F_G_NAME>",
                f"<F_G_AMOUNT>{grain.amount_oz:.7f}</F_G_AMOUNT>",
                f"<F_G_COLOR>{grain.color:.7f}</F_G_COLOR>",
                "</Grain>",
            ])
        for hop in recipe.hops:
            lines.extend([
                "<Hops>",
                f"<F_H_NAME>{self._xml_escape(hop.name)}</F_H_NAME>",
                f"<F_H_AMOUNT>{hop.amount_oz:.7f}</F_H_AMOUNT>",
                f"<F_H_ALPHA>{hop.alpha:.7f}</F_H_ALPHA>",
                f"<F_H_BOIL_TIME>{hop.boil_time:.7f}</F_H_BOIL_TIME>",
                "</Hops>",
            ])
        for yeast in recipe.yeasts:
            lines.extend([
                "<Yeast>",
                f"<F_Y_NAME>{self._xml_escape(yeast.name)}</F_Y_NAME>",
                f"<F_Y_LAB>{self._xml_escape(yeast.lab)}</F_Y_LAB>",
                f"<F_Y_PRODUCT_ID>{self._xml_escape(yeast.product_id)}</F_Y_PRODUCT_ID>",
                "</Yeast>",
            ])
        lines.append("</Data></Ingredients></Recipe>")
        return "\n".join(lines)

    def save_recipe(self, recipe: Recipe) -> bool:
        """Save a recipe to an importable .bsmx file."""
        export_dir = self.beersmith_path / "MCP_Exports"
        export_dir.mkdir(exist_ok=True)
        filename = re.sub(r'[^\w\-_]', '_', recipe.name) + ".bsmx"
        filepath = export_dir / filename
        xml_content = self._generate_recipe_xml(recipe)
        full_xml = f"""<Recipe><_PERMID_>0</_PERMID_>
<Name>MCP Export</Name><Type>7372</Type><Dirty>1</Dirty>
<Data>{xml_content}</Data></Recipe>"""
        filepath.write_text(full_xml, encoding="utf-8")
        return True

    def update_ingredient(self, ingredient_type: str, ingredient_name: str, updates: dict) -> bool:
        """Update an ingredient in BeerSmith's database."""
        type_map = {
            'grain': ('Grain.bsmx', 'Grain', Grain),
            'hop': ('Hops.bsmx', 'Hops', Hop),
            'yeast': ('Yeast.bsmx', 'Yeast', Yeast),
            'misc': ('Misc.bsmx', 'Misc', Misc),
        }
        if ingredient_type.lower() not in type_map:
            raise ValueError(f"Invalid ingredient type: {ingredient_type}")
        filename, tag_name, model_class = type_map[ingredient_type.lower()]
        file_path = self._get_file_path(filename)
        if not file_path.exists():
            raise FileNotFoundError(f"{filename} not found")
        self.backup_path.mkdir(exist_ok=True)
        backup_file = self.backup_path / f"{filename.replace('.bsmx', '')}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bsmx"
        shutil.copy2(file_path, backup_file)
        content = file_path.read_text(encoding="utf-8")
        parser = etree.XMLParser(recover=True, encoding='utf-8')
        pattern = f'<{tag_name}>.*?</{tag_name}>'
        matches = list(re.finditer(pattern, content, re.DOTALL))
        if not matches:
            raise ValueError(f"No {tag_name} elements found")
        ingredient_found = False
        updated_content = content
        for match in matches:
            xml_chunk = match.group(0)
            try:
                root = etree.fromstring(xml_chunk.encode('utf-8'), parser=parser)
                item_dict = self._element_to_dict(root)
                item = model_class.model_validate(item_dict)
                if item.name.lower() == ingredient_name.lower():
                    ingredient_found = True
                    updated_xml = self._update_xml_fields(xml_chunk, updates, model_class)
                    updated_content = updated_content.replace(xml_chunk, updated_xml)
                    break
            except Exception:
                continue
        if not ingredient_found:
            raise ValueError(f"Ingredient '{ingredient_name}' not found")
        file_path.write_text(updated_content, encoding="utf-8")
        if filename in self._cache:
            del self._cache[filename]
        return True

    def _update_xml_fields(self, xml_str: str, updates: dict, model_class) -> str:
        """Update XML fields based on updates dictionary."""
        field_aliases = {}
        for field_name, field_info in model_class.model_fields.items():
            if hasattr(field_info, 'alias') and field_info.alias:
                field_aliases[field_name] = field_info.alias.upper()
        updated_xml = xml_str
        for field_name, new_value in updates.items():
            xml_tag = field_aliases.get(field_name, f"F_{field_name.upper()}")
            if isinstance(new_value, str):
                new_value = self._xml_escape(new_value)
            elif isinstance(new_value, bool):
                new_value = 1 if new_value else 0
            elif isinstance(new_value, float):
                new_value = f"{new_value:.7f}"
            pattern = f'<{xml_tag}>.*?</{xml_tag}>'
            replacement = f'<{xml_tag}>{new_value}</{xml_tag}>'
            updated_xml = re.sub(pattern, replacement, updated_xml, count=1)
        return updated_xml

    def export_recipe_beerxml(self, recipe: Recipe) -> str:
        """Export a recipe in BeerXML format."""
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<RECIPES><RECIPE>',
            f'<NAME>{self._xml_escape(recipe.name)}</NAME>',
            '<VERSION>1</VERSION><TYPE>All Grain</TYPE>',
            f'<BATCH_SIZE>{recipe.batch_size_liters:.2f}</BATCH_SIZE>',
            f'<BOIL_TIME>{recipe.boil_time:.0f}</BOIL_TIME>',
            f'<EFFICIENCY>{recipe.efficiency:.1f}</EFFICIENCY>',
            '<HOPS>',
        ]
        for hop in recipe.hops:
            lines.extend([
                '<HOP>',
                f'<NAME>{self._xml_escape(hop.name)}</NAME>',
                f'<ALPHA>{hop.alpha:.2f}</ALPHA>',
                f'<AMOUNT>{hop.amount_grams / 1000:.4f}</AMOUNT>',
                f'<TIME>{hop.boil_time:.0f}</TIME>',
                '</HOP>',
            ])
        lines.append('</HOPS><FERMENTABLES>')
        for grain in recipe.grains:
            lines.extend([
                '<FERMENTABLE>',
                f'<NAME>{self._xml_escape(grain.name)}</NAME>',
                f'<AMOUNT>{grain.amount_kg:.4f}</AMOUNT>',
                f'<COLOR>{grain.color:.1f}</COLOR>',
                '</FERMENTABLE>',
            ])
        lines.append('</FERMENTABLES><YEASTS>')
        for yeast in recipe.yeasts:
            lines.extend([
                '<YEAST>',
                f'<NAME>{self._xml_escape(yeast.name)}</NAME>',
                f'<LABORATORY>{self._xml_escape(yeast.lab)}</LABORATORY>',
                '</YEAST>',
            ])
        lines.append('</YEASTS></RECIPE></RECIPES>')
        return '\n'.join(lines)
