"""Ingredient matching utilities for BeerSmith MCP."""

from dataclasses import dataclass
from typing import Any

from rapidfuzz import fuzz, process

from mcp_beersmith.models import Grain, Hop, IngredientMatch, Yeast


# Common hop substitutes mapping
HOP_SUBSTITUTES: dict[str, list[str]] = {
    # American Hops
    "Cascade": ["Centennial", "Amarillo", "Citra", "Ahtanum"],
    "Centennial": ["Cascade", "Chinook", "Columbus", "Simcoe"],
    "Chinook": ["Columbus", "Centennial", "Simcoe", "Nugget"],
    "Columbus": ["Chinook", "Centennial", "CTZ", "Tomahawk", "Zeus"],
    "Simcoe": ["Chinook", "Columbus", "Amarillo"],
    "Amarillo": ["Cascade", "Centennial", "Citra", "Simcoe"],
    "Citra": ["Amarillo", "Mosaic", "Simcoe", "Galaxy"],
    "Mosaic": ["Citra", "Simcoe", "Amarillo", "El Dorado"],
    "Ahtanum": ["Cascade", "Amarillo", "Centennial"],
    "Nugget": ["Chinook", "Columbus", "Magnum", "Galena"],
    "Galena": ["Nugget", "Columbus", "Cluster"],
    "Cluster": ["Galena", "Northern Brewer"],
    "Warrior": ["Columbus", "Simcoe", "Magnum"],
    "El Dorado": ["Citra", "Mosaic", "Simcoe"],
    "Azacca": ["Simcoe", "Citra", "Mosaic"],
    
    # English Hops
    "East Kent Goldings": ["Fuggle", "UK Goldings", "Styrian Goldings", "First Gold"],
    "Fuggle": ["East Kent Goldings", "Willamette", "Styrian Goldings"],
    "UK Goldings": ["East Kent Goldings", "Fuggle", "Styrian Goldings"],
    "First Gold": ["East Kent Goldings", "Fuggle", "Crystal"],
    "Challenger": ["Target", "Admiral", "Northern Brewer"],
    "Target": ["Challenger", "Admiral", "Fuggle"],
    "Admiral": ["Target", "Challenger", "Northdown"],
    
    # German Hops
    "Hallertau": ["Hallertauer Mittelfruh", "Liberty", "Mt. Hood", "Tettnang"],
    "Hallertauer Mittelfruh": ["Hallertau", "Liberty", "Crystal", "Hersbrucker"],
    "Hersbrucker": ["Hallertau", "Tettnang", "Spalt"],
    "Tettnang": ["Saaz", "Spalt", "Hallertau", "Santiam"],
    "Spalt": ["Tettnang", "Saaz", "Hallertau"],
    "Magnum": ["Nugget", "Horizon", "Columbus"],
    "Perle": ["Northern Brewer", "Hallertau", "Mt. Hood"],
    "Northern Brewer": ["Perle", "Chinook", "Cluster"],
    "Tradition": ["Hallertau", "Liberty", "Mt. Hood"],
    "Hallertau Blanc": ["Nelson Sauvin", "Sauvignon Blanc"],
    "Hüll Melon": ["Cascade", "Mandarina Bavaria"],
    "Mandarina Bavaria": ["Citra", "Cascade", "Hüll Melon"],
    
    # Czech Hops
    "Saaz": ["Tettnang", "Spalt", "Sterling", "Styrian Goldings"],
    
    # American Noble-style
    "Liberty": ["Hallertau", "Mt. Hood", "Crystal"],
    "Mt. Hood": ["Hallertau", "Liberty", "Crystal"],
    "Crystal": ["Hallertau", "Liberty", "Mt. Hood", "Hersbrucker"],
    "Sterling": ["Saaz", "Tettnang"],
    "Santiam": ["Tettnang", "Spalt"],
    "Willamette": ["Fuggle", "Tettnang", "Styrian Goldings"],
    
    # Slovenian
    "Styrian Goldings": ["Fuggle", "Willamette", "UK Goldings"],
    
    # Australian/NZ
    "Galaxy": ["Citra", "Simcoe", "Amarillo"],
    "Nelson Sauvin": ["Galaxy", "Motueka", "Hallertau Blanc"],
    "Motueka": ["Saaz", "Nelson Sauvin", "Sterling"],
    "Pacifica": ["Hallertau", "Motueka"],
    "Vic Secret": ["Galaxy", "Citra"],
}


@dataclass
class MatchResult:
    """Result of a fuzzy match operation."""
    
    name: str
    score: float
    item: Any


class IngredientMatcher:
    """Fuzzy matching for brewing ingredients."""

    def __init__(self, hops: list[Hop], grains: list[Grain], yeasts: list[Yeast]):
        """Initialize matcher with ingredient lists."""
        self.hops = {h.name: h for h in hops}
        self.grains = {g.name: g for g in grains}
        self.yeasts = {y.name: y for y in yeasts}
        
        # Build search indices
        self._hop_names = list(self.hops.keys())
        self._grain_names = list(self.grains.keys())
        self._yeast_names = list(self.yeasts.keys())
        
        # Also index by product_id for yeasts
        self._yeast_by_product_id = {y.product_id: y for y in yeasts if y.product_id}

    def match_hop(self, name: str, threshold: float = 70) -> IngredientMatch | None:
        """Find the best matching hop."""
        if not self._hop_names:
            return None
        
        # Try exact match first
        if name in self.hops:
            return IngredientMatch(
                query=name,
                matched_name=name,
                ingredient_type="hop",
                confidence=100.0,
                substitutes=HOP_SUBSTITUTES.get(name, []),
            )
        
        # Fuzzy match
        result = process.extractOne(name, self._hop_names, scorer=fuzz.WRatio)
        if result and result[1] >= threshold:
            matched_name = result[0]
            return IngredientMatch(
                query=name,
                matched_name=matched_name,
                ingredient_type="hop",
                confidence=result[1],
                substitutes=HOP_SUBSTITUTES.get(matched_name, []),
            )
        return None

    def match_grain(self, name: str, threshold: float = 70) -> IngredientMatch | None:
        """Find the best matching grain."""
        if not self._grain_names:
            return None
        
        # Try exact match first
        if name in self.grains:
            return IngredientMatch(
                query=name,
                matched_name=name,
                ingredient_type="grain",
                confidence=100.0,
            )
        
        # Fuzzy match
        result = process.extractOne(name, self._grain_names, scorer=fuzz.WRatio)
        if result and result[1] >= threshold:
            return IngredientMatch(
                query=name,
                matched_name=result[0],
                ingredient_type="grain",
                confidence=result[1],
            )
        return None

    def match_yeast(self, name: str, threshold: float = 70) -> IngredientMatch | None:
        """Find the best matching yeast."""
        if not self._yeast_names:
            return None
        
        # Try exact match first
        if name in self.yeasts:
            return IngredientMatch(
                query=name,
                matched_name=name,
                ingredient_type="yeast",
                confidence=100.0,
            )
        
        # Try by product ID
        if name in self._yeast_by_product_id:
            yeast = self._yeast_by_product_id[name]
            return IngredientMatch(
                query=name,
                matched_name=yeast.name,
                ingredient_type="yeast",
                confidence=100.0,
            )
        
        # Fuzzy match on name
        result = process.extractOne(name, self._yeast_names, scorer=fuzz.WRatio)
        if result and result[1] >= threshold:
            return IngredientMatch(
                query=name,
                matched_name=result[0],
                ingredient_type="yeast",
                confidence=result[1],
            )
        return None

    def match_ingredient(
        self, name: str, ingredient_type: str | None = None, threshold: float = 70
    ) -> IngredientMatch | None:
        """Match an ingredient, optionally filtering by type."""
        if ingredient_type:
            type_lower = ingredient_type.lower()
            if type_lower == "hop":
                return self.match_hop(name, threshold)
            elif type_lower == "grain" or type_lower == "fermentable":
                return self.match_grain(name, threshold)
            elif type_lower == "yeast":
                return self.match_yeast(name, threshold)
        
        # Try all types and return best match
        matches = []
        
        hop_match = self.match_hop(name, threshold)
        if hop_match:
            matches.append(hop_match)
        
        grain_match = self.match_grain(name, threshold)
        if grain_match:
            matches.append(grain_match)
        
        yeast_match = self.match_yeast(name, threshold)
        if yeast_match:
            matches.append(yeast_match)
        
        if not matches:
            return None
        
        # Return the highest confidence match
        return max(matches, key=lambda m: m.confidence)

    def match_batch(
        self, names: list[str], ingredient_type: str | None = None, threshold: float = 70
    ) -> dict[str, IngredientMatch | None]:
        """Match multiple ingredients at once."""
        return {name: self.match_ingredient(name, ingredient_type, threshold) for name in names}

    def get_hop_substitutes(self, hop_name: str) -> list[str]:
        """Get a list of substitute hops."""
        # Try exact match in substitutes dict
        if hop_name in HOP_SUBSTITUTES:
            return HOP_SUBSTITUTES[hop_name]
        
        # Try fuzzy match
        match = self.match_hop(hop_name)
        if match and match.confidence >= 80:
            return HOP_SUBSTITUTES.get(match.matched_name, [])
        
        return []

    def find_similar_hops(
        self, hop_name: str, limit: int = 5, include_substitutes: bool = True
    ) -> list[IngredientMatch]:
        """Find hops similar to the given one by name and substitutes."""
        results = []
        
        # Get substitutes first if requested
        if include_substitutes:
            subs = self.get_hop_substitutes(hop_name)
            for sub in subs[:limit]:
                if sub in self.hops:
                    results.append(IngredientMatch(
                        query=hop_name,
                        matched_name=sub,
                        ingredient_type="hop",
                        confidence=95.0,  # High confidence for known substitutes
                        substitutes=[],
                    ))
        
        # Add fuzzy matches
        fuzzy_results = process.extract(hop_name, self._hop_names, scorer=fuzz.WRatio, limit=limit)
        for name, score, _ in fuzzy_results:
            if name != hop_name and name not in [r.matched_name for r in results]:
                results.append(IngredientMatch(
                    query=hop_name,
                    matched_name=name,
                    ingredient_type="hop",
                    confidence=score,
                    substitutes=HOP_SUBSTITUTES.get(name, []),
                ))
        
        # Sort by confidence and return top results
        return sorted(results, key=lambda m: m.confidence, reverse=True)[:limit]

    def find_similar_grains(self, grain_name: str, limit: int = 5) -> list[IngredientMatch]:
        """Find grains similar to the given one by name."""
        results = []
        fuzzy_results = process.extract(grain_name, self._grain_names, scorer=fuzz.WRatio, limit=limit)
        for name, score, _ in fuzzy_results:
            if name != grain_name:
                results.append(IngredientMatch(
                    query=grain_name,
                    matched_name=name,
                    ingredient_type="grain",
                    confidence=score,
                ))
        return results

    def find_similar_yeasts(self, yeast_name: str, limit: int = 5) -> list[IngredientMatch]:
        """Find yeasts similar to the given one by name."""
        results = []
        fuzzy_results = process.extract(yeast_name, self._yeast_names, scorer=fuzz.WRatio, limit=limit)
        for name, score, _ in fuzzy_results:
            if name != yeast_name:
                results.append(IngredientMatch(
                    query=yeast_name,
                    matched_name=name,
                    ingredient_type="yeast",
                    confidence=score,
                ))
        return results
