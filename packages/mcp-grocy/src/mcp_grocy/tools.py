"""MCP tool definitions for Grocy."""

import re

import httpx
from fastmcp import FastMCP

from mcp_grocy.adapter import GrocyAdapter
from mcp_grocy.client import GrocyClient
from mcp_grocy.config import get_config


async def _fetch_product_description_from_url(url: str) -> dict:
    """
    Fetch product description and metadata from a URL.

    Args:
        url: Product page URL

    Returns:
        Dictionary with extracted description and metadata, or error info.
    """
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Accept-Encoding": "gzip, deflate, br",
                    "DNT": "1",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                },
            )
            response.raise_for_status()
            html = response.text

            result = {}

            # Extract meta description
            meta_desc_match = re.search(
                r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']',
                html,
                re.IGNORECASE,
            )
            if not meta_desc_match:
                meta_desc_match = re.search(
                    r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*name=["\']description["\']',
                    html,
                    re.IGNORECASE,
                )
            if meta_desc_match:
                result["meta_description"] = meta_desc_match.group(1).strip()

            # Extract Open Graph description (often more detailed)
            og_desc_match = re.search(
                r'<meta[^>]*property=["\']og:description["\'][^>]*content=["\']([^"\']+)["\']',
                html,
                re.IGNORECASE,
            )
            if not og_desc_match:
                og_desc_match = re.search(
                    r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*property=["\']og:description["\']',
                    html,
                    re.IGNORECASE,
                )
            if og_desc_match:
                result["og_description"] = og_desc_match.group(1).strip()

            # Try to extract product description from common e-commerce patterns
            # Look for product description divs/sections
            desc_patterns = [
                r'<div[^>]*class="[^"]*product[_-]?description[^"]*"[^>]*>(.*?)</div>',
                r'<div[^>]*class="[^"]*description[^"]*"[^>]*>(.*?)</div>',
                r'<div[^>]*id="[^"]*description[^"]*"[^>]*>(.*?)</div>',
                r'<section[^>]*class="[^"]*description[^"]*"[^>]*>(.*?)</section>',
                # WooCommerce
                r'<div[^>]*class="[^"]*woocommerce-product-details__short-description[^"]*"[^>]*>(.*?)</div>',
            ]

            for pattern in desc_patterns:
                match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
                if match:
                    # Clean up HTML tags from the extracted text
                    desc_html = match.group(1)
                    # Remove HTML tags
                    desc_text = re.sub(r'<[^>]+>', ' ', desc_html)
                    # Clean up whitespace
                    desc_text = re.sub(r'\s+', ' ', desc_text).strip()
                    if len(desc_text) > 20:  # Only use if substantial
                        result["product_description"] = desc_text[:1000]  # Limit length
                        break

            # Prefer product description, then OG, then meta
            if "product_description" in result:
                result["description"] = result["product_description"]
            elif "og_description" in result:
                result["description"] = result["og_description"]
            elif "meta_description" in result:
                result["description"] = result["meta_description"]

            result["source_url"] = url
            result["success"] = "description" in result

            return result

    except httpx.HTTPError as e:
        return {"success": False, "error": f"HTTP error: {e}", "source_url": url}
    except Exception as e:
        return {"success": False, "error": f"Failed to fetch: {e}", "source_url": url}


def _get_unit_for_category(category_name: str, units: list[dict]) -> int | None:
    """
    Get the appropriate quantity unit ID based on product category.

    Args:
        category_name: Name of the product category/group
        units: List of available quantity units

    Returns:
        Unit ID for the category, or None if no match found.
    """
    if not category_name or not units:
        return None

    category_lower = category_name.lower()

    # Build unit lookup by name (case-insensitive)
    unit_by_name = {}
    for u in units:
        name = u.get("name", "").lower()
        unit_by_name[name] = u["id"]
        # Also check name_plural
        name_plural = u.get("name_plural", "").lower()
        if name_plural:
            unit_by_name[name_plural] = u["id"]

    # Category to unit mapping
    # Grains/Malts and Hops should use grams
    if any(kw in category_lower for kw in ["grain", "malt", "hop", "adjunct"]):
        # Look for gram unit
        for name in ["g", "gram", "grams", "gr"]:
            if name in unit_by_name:
                return unit_by_name[name]

    # Yeast should use pieces
    if "yeast" in category_lower:
        for name in ["piece", "pieces", "pcs", "pack", "packs", "packet", "packets"]:
            if name in unit_by_name:
                return unit_by_name[name]

    # Misc/Other - try to use piece as default for countable items
    if any(kw in category_lower for kw in ["misc", "other", "equipment", "fining", "additive"]):
        for name in ["piece", "pieces", "pcs"]:
            if name in unit_by_name:
                return unit_by_name[name]

    # Liquids - try ml or L
    if any(kw in category_lower for kw in ["liquid", "extract", "syrup"]):
        for name in ["ml", "l", "liter", "litre", "milliliter", "millilitre"]:
            if name in unit_by_name:
                return unit_by_name[name]

    return None


# ==================== Malt Color Matching Utilities ====================

def _lovibond_to_ebc(lovibond: float) -> float:
    """Convert Lovibond to EBC color units."""
    return lovibond * 2.63


def _ebc_to_lovibond(ebc: float) -> float:
    """Convert EBC to Lovibond color units."""
    return ebc / 2.63


def _parse_malt_color(text: str) -> dict | None:
    """
    Parse malt color specifications from a name or description.

    Supports formats:
    - "60L" or "60°L" or "60 L" (Lovibond)
    - "Crystal 60" or "Crystal 60L" (Lovibond)
    - "EBC 150" or "150 EBC" or "EBC 150-180" (EBC)
    - "150-180 EBC" (EBC range)

    Returns:
        Dictionary with ebc_min, ebc_max, ebc_mid, lovibond, or None if not found.
    """
    if not text:
        return None

    text = text.upper()

    # Pattern 1: Lovibond - "60L", "60°L", "60 L", "Crystal 60L"
    lovibond_patterns = [
        r'(\d+)\s*°?\s*L\b',  # 60L, 60°L, 60 L
        r'CRYSTAL\s*(\d+)\b(?!\s*EBC)',  # Crystal 60 (but not Crystal 60 EBC)
        r'CARAMEL\s*(\d+)\b(?!\s*EBC)',  # Caramel 60
    ]

    for pattern in lovibond_patterns:
        match = re.search(pattern, text)
        if match:
            lovibond = float(match.group(1))
            ebc = _lovibond_to_ebc(lovibond)
            return {
                "lovibond": lovibond,
                "ebc_min": ebc,
                "ebc_max": ebc,
                "ebc_mid": ebc,
                "source": "lovibond",
            }

    # Pattern 2: EBC range - "150-180 EBC", "EBC 150-180", "EBC: 150-180"
    ebc_range_patterns = [
        r'EBC[:\s]*(\d+)\s*[-–]\s*(\d+)',  # EBC 150-180, EBC: 150-180
        r'(\d+)\s*[-–]\s*(\d+)\s*EBC',  # 150-180 EBC
    ]

    for pattern in ebc_range_patterns:
        match = re.search(pattern, text)
        if match:
            ebc_min = float(match.group(1))
            ebc_max = float(match.group(2))
            ebc_mid = (ebc_min + ebc_max) / 2
            return {
                "lovibond": _ebc_to_lovibond(ebc_mid),
                "ebc_min": ebc_min,
                "ebc_max": ebc_max,
                "ebc_mid": ebc_mid,
                "source": "ebc_range",
            }

    # Pattern 3: Single EBC - "EBC 150", "150 EBC"
    ebc_single_patterns = [
        r'EBC[:\s]*(\d+)(?!\s*[-–])',  # EBC 150 (not followed by range)
        r'(\d+)\s*EBC\b',  # 150 EBC
    ]

    for pattern in ebc_single_patterns:
        match = re.search(pattern, text)
        if match:
            ebc = float(match.group(1))
            return {
                "lovibond": _ebc_to_lovibond(ebc),
                "ebc_min": ebc,
                "ebc_max": ebc,
                "ebc_mid": ebc,
                "source": "ebc_single",
            }

    return None


def _is_crystal_malt(name: str) -> bool:
    """Check if a product name indicates a crystal/caramel malt."""
    name_lower = name.lower()
    crystal_keywords = ["crystal", "caramel", "cara", "caramalt", "carapils", "caramunich", "carared", "carahell"]
    return any(kw in name_lower for kw in crystal_keywords)


def _calculate_color_match_score(
    target_ebc: float,
    product_ebc_min: float,
    product_ebc_max: float,
    tolerance: float = 30.0,
) -> float:
    """
    Calculate a match score for color compatibility.

    Returns:
        Score from 0-100, where 100 is perfect match, 0 is outside tolerance.
    """
    product_ebc_mid = (product_ebc_min + product_ebc_max) / 2

    # If target is within the product's range, it's a perfect match
    if product_ebc_min <= target_ebc <= product_ebc_max:
        return 100.0

    # Calculate distance to nearest edge of range
    if target_ebc < product_ebc_min:
        distance = product_ebc_min - target_ebc
    else:
        distance = target_ebc - product_ebc_max

    # Score based on distance within tolerance
    if distance > tolerance:
        return 0.0

    # Linear score: 100 at distance 0, 50 at edge of tolerance
    return max(0, 100 - (distance / tolerance * 50))


# ==================== Maltster Brand Matching ====================

# Known maltster/supplier brands - these should NOT be fuzzy matched across
MALTSTER_BRANDS = [
    # German
    "bestmalz", "best",  # BESTMALZ (German)
    "weyermann",
    # UK
    "simpsons", "simpson",
    "crisp",
    "thomas fawcett", "fawcett",
    "warminster",
    "muntons",
    "pauls malt", "pauls",
    # Belgian
    "castle malting", "château", "chateau",
    # US
    "briess",
    "great western",
    "rahr",
    # Other
    "dingemans",
    "franco-belges",
    "malt craft",  # Australia
    "gladfield",  # New Zealand
]


def _extract_maltster(name: str) -> str | None:
    """
    Extract maltster/supplier brand from an ingredient name.

    Args:
        name: Ingredient name (e.g., "BEST Pale Ale", "Simpsons Golden Promise")

    Returns:
        Maltster brand name (lowercase) if found, None otherwise.
    """
    if not name:
        return None

    name_lower = name.lower()

    for brand in MALTSTER_BRANDS:
        if brand in name_lower:
            # Return the canonical brand name
            # Map aliases to canonical names
            if brand in ["best", "bestmalz"]:
                return "bestmalz"
            if brand in ["simpson", "simpsons"]:
                return "simpsons"
            if brand in ["fawcett", "thomas fawcett"]:
                return "thomas fawcett"
            if brand in ["château", "chateau", "castle malting"]:
                return "castle malting"
            if brand in ["pauls", "pauls malt"]:
                return "pauls malt"
            return brand

    return None


def _is_same_maltster(name1: str, name2: str) -> bool:
    """
    Check if two ingredient names are from the same maltster.

    Returns True if:
    - Both have the same maltster brand
    - Neither has a maltster brand (generic products)
    - Only one has a maltster brand (can't determine)

    Returns False if:
    - Both have different maltster brands
    """
    maltster1 = _extract_maltster(name1)
    maltster2 = _extract_maltster(name2)

    # If both have maltsters, they must match
    if maltster1 and maltster2:
        return maltster1 == maltster2

    # Otherwise, allow matching (at least one is generic)
    return True


# ==================== Yeast Matching Utilities ====================

# Regex patterns for extracting yeast product IDs
YEAST_ID_PATTERNS = {
    "fermentis": [
        r"\b(US-?\d{2})\b",  # US-05, US05
        r"\b(S-?\d{2,3})\b",  # S-04, S-33, S-189
        r"\b(K-?\d{2})\b",  # K-97
        r"\b(W-?\d{2})\b",  # W-34/70
        r"\bSafale\s+(US-?\d{2})\b",
        r"\bSaflager\s+(S-?\d{2,3}|W-?\d{2})\b",
    ],
    "white_labs": [
        r"\b(WLP\d{3})\b",  # WLP001
    ],
    "wyeast": [
        r"\b(\d{4})\b(?=.*(?:wyeast|activator))",  # 1056 (with context)
        r"\bWyeast\s+(\d{4})\b",  # Wyeast 1056
    ],
    "mangrove_jacks": [
        r"\b(M\d{2})\b",  # M47
        r"\bMangrove\s+Jack(?:'?s)?\s+(M\d{2})\b",
    ],
    "lallemand": [
        r"\b(BRY-?\d+)\b",  # BRY-97
        r"\b(CBC-?\d+)\b",  # CBC-1
        r"\bLalBrew\s+(\w+)\b",
    ],
    "omega": [
        r"\b(OYL-?\d{3})\b",  # OYL-057
    ],
    "imperial": [
        r"\bImperial\s+(A\d{2})\b",  # Imperial A01
        r"\b(A\d{2})\b(?=.*imperial)",
    ],
}

# Known yeast functional equivalents (same or very similar strains)
YEAST_EQUIVALENTS = {
    # American Ale / Chico strain
    "us-05": ["wlp001", "wyeast 1056", "1056", "safale us-05", "bry-97"],
    "wlp001": ["us-05", "wyeast 1056", "1056", "safale us-05"],
    "1056": ["us-05", "wlp001", "safale us-05"],
    # English Ale
    "s-04": ["wlp007", "wyeast 1098", "1098"],
    "wlp007": ["s-04", "wyeast 1098", "1098"],
    "1098": ["s-04", "wlp007"],
    # Belgian Abbey
    "m47": ["wlp550", "wyeast 3522", "3522"],
    "wlp550": ["m47", "wyeast 3522", "3522"],
    "3522": ["m47", "wlp550"],
    # German Lager
    "w-34/70": ["wlp830", "wyeast 2124", "2124", "s-189"],
    "s-189": ["w-34/70", "wlp830", "wyeast 2124"],
    "wlp830": ["w-34/70", "s-189", "wyeast 2124"],
    "2124": ["w-34/70", "s-189", "wlp830"],
    # Hefeweizen
    "wlp300": ["wyeast 3068", "3068"],
    "3068": ["wlp300"],
    # Kveik
    "oyl-061": ["voss kveik"],
}


def _normalize_yeast_id(yeast_id: str) -> str:
    """Normalize a yeast ID for comparison."""
    if not yeast_id:
        return ""
    # Remove spaces and hyphens, lowercase
    return yeast_id.lower().replace("-", "").replace(" ", "")


def _extract_yeast_id(name: str) -> dict | None:
    """
    Extract yeast product ID from a name.

    Args:
        name: Product name (e.g., "US-05", "Safale American Ale US-05", "Wyeast 1272")

    Returns:
        Dictionary with id, lab, normalized_id, or None if not found.
    """
    if not name:
        return None

    name_upper = name.upper()

    for lab, patterns in YEAST_ID_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, name_upper, re.IGNORECASE)
            if match:
                yeast_id = match.group(1)
                return {
                    "id": yeast_id.upper(),
                    "lab": lab,
                    "normalized": _normalize_yeast_id(yeast_id),
                }

    return None


def _get_yeast_equivalents(yeast_id: str) -> list[str]:
    """Get list of equivalent yeast strains for a given ID."""
    normalized = _normalize_yeast_id(yeast_id)

    for key, equivalents in YEAST_EQUIVALENTS.items():
        if _normalize_yeast_id(key) == normalized:
            return equivalents
        if normalized in [_normalize_yeast_id(e) for e in equivalents]:
            # Return the key plus other equivalents
            return [key] + [e for e in equivalents if _normalize_yeast_id(e) != normalized]

    return []


def _is_yeast_product(name: str) -> bool:
    """Check if a product name indicates it's a yeast product."""
    name_lower = name.lower()
    yeast_keywords = [
        "yeast", "ale yeast", "lager yeast", "safale", "saflager",
        "wyeast", "white labs", "wlp", "mangrove jack", "lallemand",
        "lalbrew", "fermentis", "omega", "imperial yeast", "kveik",
        "starter", "activator", "dry yeast", "liquid yeast",
    ]
    return any(kw in name_lower for kw in yeast_keywords) or _extract_yeast_id(name) is not None


def _map_lab_name(lab_name: str) -> str:
    """
    Map BeerSmith lab names to canonical lab identifiers used in YEAST_ID_PATTERNS.

    BeerSmith uses various lab name formats that need to be normalized.
    """
    if not lab_name:
        return "unknown"

    lab_lower = lab_name.lower()

    # Map common variations to canonical names
    lab_mappings = {
        # Fermentis / Safale / Saflager
        "fermentis": "fermentis",
        "safale": "fermentis",
        "saflager": "fermentis",
        "lesaffre": "fermentis",
        # White Labs
        "white labs": "white_labs",
        "whitelabs": "white_labs",
        "wlp": "white_labs",
        # Wyeast
        "wyeast": "wyeast",
        "wyeast laboratories": "wyeast",
        # Mangrove Jack's
        "mangrove jack": "mangrove_jacks",
        "mangrove jacks": "mangrove_jacks",
        "mangrove jack's": "mangrove_jacks",
        # Lallemand
        "lallemand": "lallemand",
        "lalbrew": "lallemand",
        "lalvin": "lallemand",
        # Omega
        "omega": "omega",
        "omega yeast": "omega",
        "omega yeast labs": "omega",
        # Imperial
        "imperial": "imperial",
        "imperial yeast": "imperial",
        "imperial organic yeast": "imperial",
    }

    for pattern, canonical in lab_mappings.items():
        if pattern in lab_lower:
            return canonical

    return lab_lower


def _match_yeast(
    ingredient_name: str,
    products: list[dict],
    stock: list[dict] | None = None,
    # BeerSmith metadata (optional)
    lab: str | None = None,  # Yeast lab (e.g., "Fermentis", "White Labs")
    yeast_product_id: str | None = None,  # Yeast product ID (e.g., "US-05", "WLP001")
) -> list[dict]:
    """
    Match yeast ingredient using multi-level strategy.

    When BeerSmith metadata (lab, yeast_product_id) is provided, it takes precedence
    over text parsing for more accurate matching.

    Matching levels:
    1. Product ID exact match (e.g., "US-05" in name)
    2. Lab + name fuzzy match
    3. High-threshold fuzzy name match
    4. Functional equivalents (suggest but don't auto-match)

    Args:
        ingredient_name: Yeast name to match
        products: List of Grocy products
        stock: Optional stock info
        lab: BeerSmith yeast lab (optional)
        yeast_product_id: BeerSmith yeast product ID, e.g. "US-05" (optional)

    Returns:
        List of matches with scores and match types.
    """
    matches = []
    stock_map = {s.get("product_id"): s for s in (stock or [])}

    # Use BeerSmith yeast_product_id if provided, otherwise extract from name
    if yeast_product_id:
        # BeerSmith provides the product ID directly
        ingredient_normalized = _normalize_yeast_id(yeast_product_id)
        ingredient_yeast = {
            "id": yeast_product_id.upper(),
            "lab": _map_lab_name(lab) if lab else "unknown",
            "normalized": ingredient_normalized,
            "source": "beersmith",
        }
    else:
        # Fall back to text parsing
        ingredient_yeast = _extract_yeast_id(ingredient_name)
        ingredient_normalized = ingredient_yeast["normalized"] if ingredient_yeast else None

    # If lab provided but no yeast_product_id, use it for lab matching
    beersmith_lab = _map_lab_name(lab) if lab else None

    for product in products:
        product_name = product.get("name", "")
        product_id = product.get("id")

        # Only consider yeast products
        if not _is_yeast_product(product_name):
            continue

        match_info = {
            "product_id": product_id,
            "product_name": product_name,
            "score": 0,
            "match_type": None,
            "details": {},
        }

        # Add stock info
        if stock_map and product_id in stock_map:
            match_info["stock_amount"] = stock_map[product_id].get("amount", 0)

        # Level 1: Product ID exact match
        product_yeast = _extract_yeast_id(product_name)
        if ingredient_normalized and product_yeast:
            if ingredient_normalized == product_yeast["normalized"]:
                match_info["score"] = 100
                match_info["match_type"] = "yeast_id"
                match_info["details"] = {
                    "matched_id": product_yeast["id"],
                    "lab": product_yeast["lab"],
                }
                matches.append(match_info)
                continue

        # Level 2: Lab match + name similarity
        if ingredient_yeast and product_yeast:
            if ingredient_yeast["lab"] == product_yeast["lab"]:
                # Same lab, check name similarity
                ing_lower = ingredient_name.lower()
                prod_lower = product_name.lower()

                # Check for common words
                ing_words = set(ing_lower.replace("-", " ").split())
                prod_words = set(prod_lower.replace("-", " ").split())
                filler = {"yeast", "ale", "lager", "dry", "liquid", "the", "a"}
                ing_words -= filler
                prod_words -= filler

                if ing_words and prod_words:
                    overlap = len(ing_words & prod_words)
                    if overlap >= 2:
                        match_info["score"] = 80
                        match_info["match_type"] = "lab_name"
                        match_info["details"]["lab"] = ingredient_yeast["lab"]
                        matches.append(match_info)
                        continue

        # Level 3: High-threshold fuzzy name matching
        ing_lower = ingredient_name.lower()
        prod_lower = product_name.lower()

        # Check for significant word overlap
        ing_words = set(ing_lower.replace("-", " ").replace("/", " ").split())
        prod_words = set(prod_lower.replace("-", " ").replace("/", " ").split())
        filler = {"yeast", "the", "a", "an", "-", "/"}
        ing_words -= filler
        prod_words -= filler

        if ing_words and prod_words:
            overlap = len(ing_words & prod_words)
            total = len(ing_words | prod_words)
            if overlap > 0:
                word_score = (overlap / total) * 100
                # Only accept high confidence matches for yeast
                if word_score >= 60:
                    match_info["score"] = word_score * 0.7  # Cap at 70 for fuzzy
                    match_info["match_type"] = "fuzzy_name"
                    match_info["details"]["matching_words"] = list(ing_words & prod_words)
                    matches.append(match_info)

    # Level 4: Check for functional equivalents in unmatched products
    if ingredient_normalized:
        equivalents = _get_yeast_equivalents(ingredient_normalized)
        if equivalents:
            for product in products:
                product_name = product.get("name", "")
                product_id = product.get("id")

                # Skip if already matched
                if any(m["product_id"] == product_id for m in matches):
                    continue

                product_yeast = _extract_yeast_id(product_name)
                if product_yeast:
                    for equiv in equivalents:
                        if _normalize_yeast_id(equiv) == product_yeast["normalized"]:
                            match_info = {
                                "product_id": product_id,
                                "product_name": product_name,
                                "score": 40,  # Lower score for equivalents
                                "match_type": "equivalent",
                                "details": {
                                    "equivalent_to": ingredient_yeast["id"] if ingredient_yeast else ingredient_name,
                                    "matched_id": product_yeast["id"],
                                },
                            }
                            if stock_map and product_id in stock_map:
                                match_info["stock_amount"] = stock_map[product_id].get("amount", 0)
                            matches.append(match_info)
                            break

    # Sort by score
    matches.sort(key=lambda x: x["score"], reverse=True)
    return matches


def _find_ingredient_substitutes(
    ingredient_name: str,
    products: list[dict],
    stock: list[dict] | None = None,
    tolerance_ebc: float = 30.0,
    # BeerSmith metadata (optional) - takes precedence over text parsing
    supplier: str | None = None,  # Grain supplier/maltster
    lab: str | None = None,  # Yeast lab
    product_id: str | None = None,  # Yeast product ID
    color_lovibond: float | None = None,  # Grain color
) -> list[dict]:
    """
    Find suitable substitute products for an ingredient.

    Matching strategy:
    - Yeast: Uses specialized yeast ID matching with equivalents
    - Crystal/caramel malts: Matches based on color specifications
    - Malts with maltster brands: Only matches within same maltster
    - Other ingredients: Uses fuzzy name matching

    When BeerSmith metadata is provided (supplier, lab, product_id), it takes
    precedence over text parsing for more accurate matching.

    Args:
        ingredient_name: The ingredient name to find substitutes for
        products: List of Grocy products
        stock: Optional list of stock entries for availability info
        tolerance_ebc: EBC tolerance for color matching (default 30)
        supplier: BeerSmith grain supplier/maltster (optional)
        lab: BeerSmith yeast lab (optional)
        product_id: BeerSmith yeast product ID (optional)
        color_lovibond: BeerSmith grain color in Lovibond (optional)

    Returns:
        List of substitute matches with scores and details.
    """
    # Check if this is a yeast ingredient - use specialized matching
    if lab or product_id or _is_yeast_product(ingredient_name):
        return _match_yeast(ingredient_name, products, stock, lab=lab, yeast_product_id=product_id)

    substitutes = []
    stock_map = {s.get("product_id"): s for s in (stock or [])}

    # Use BeerSmith color if provided, otherwise parse from name
    if color_lovibond is not None:
        ebc = _lovibond_to_ebc(color_lovibond)
        ingredient_color = {
            "lovibond": color_lovibond,
            "ebc_min": ebc,
            "ebc_max": ebc,
            "ebc_mid": ebc,
            "source": "beersmith",
        }
    else:
        ingredient_color = _parse_malt_color(ingredient_name)

    is_crystal = _is_crystal_malt(ingredient_name)

    # Use BeerSmith supplier if provided, otherwise extract from name
    # Normalize supplier names for comparison
    if supplier:
        # Map BeerSmith supplier names to our canonical names
        supplier_lower = supplier.lower()
        ingredient_maltster = _extract_maltster(supplier) or supplier_lower
    else:
        ingredient_maltster = _extract_maltster(ingredient_name)

    for product in products:
        product_name = product.get("name", "")
        product_desc = product.get("description", "")
        product_id = product.get("id")

        match_info = {
            "product_id": product_id,
            "product_name": product_name,
            "score": 0,
            "match_type": None,
            "details": {},
        }

        # Add stock info if available
        if stock_map and product_id in stock_map:
            match_info["stock_amount"] = stock_map[product_id].get("amount", 0)

        # Check maltster brand compatibility
        # If ingredient has a maltster brand, only match products from same maltster
        product_maltster = _extract_maltster(product_name)
        if ingredient_maltster and product_maltster:
            if ingredient_maltster != product_maltster:
                # Different maltsters - skip this product for fuzzy matching
                # But still allow exact matches
                name_lower = ingredient_name.lower()
                product_name_lower = product_name.lower()
                if name_lower == product_name_lower:
                    match_info["score"] = 100
                    match_info["match_type"] = "exact"
                    substitutes.append(match_info)
                # Otherwise, add as a "different_maltster" suggestion with low score
                elif ingredient_maltster and product_maltster:
                    # Only suggest if there's some name similarity
                    name_words = set(name_lower.replace("-", " ").replace("/", " ").split())
                    product_words = set(product_name_lower.replace("-", " ").replace("/", " ").split())
                    filler = {"malt", "malts", "the", "a", "an", "-", "/"}
                    name_words -= filler
                    product_words -= filler
                    # Remove maltster words
                    maltster_words = set(ingredient_maltster.split()) | set(product_maltster.split())
                    name_words -= maltster_words
                    product_words -= maltster_words

                    if name_words and product_words:
                        overlap = len(name_words & product_words)
                        if overlap >= 2:  # At least 2 words must match
                            match_info["score"] = 30  # Low score - different maltster
                            match_info["match_type"] = "different_maltster"
                            match_info["details"] = {
                                "requested_maltster": ingredient_maltster,
                                "product_maltster": product_maltster,
                                "warning": "Different maltster - manual verification recommended",
                            }
                            substitutes.append(match_info)
                continue

        # For crystal malts with color info, try color matching
        if is_crystal and ingredient_color and _is_crystal_malt(product_name):
            # Try to parse color from product name and description
            product_color = _parse_malt_color(product_name)
            if not product_color:
                product_color = _parse_malt_color(product_desc)

            if product_color:
                color_score = _calculate_color_match_score(
                    ingredient_color["ebc_mid"],
                    product_color["ebc_min"],
                    product_color["ebc_max"],
                    tolerance_ebc,
                )

                if color_score > 0:
                    match_info["score"] = color_score
                    match_info["match_type"] = "color"
                    match_info["details"] = {
                        "target_ebc": round(ingredient_color["ebc_mid"], 1),
                        "target_lovibond": round(ingredient_color["lovibond"], 1),
                        "product_ebc_range": f"{product_color['ebc_min']:.0f}-{product_color['ebc_max']:.0f}",
                        "ebc_difference": round(abs(ingredient_color["ebc_mid"] - product_color["ebc_mid"]), 1),
                    }
                    substitutes.append(match_info)
                    continue

        # Fuzzy name matching for non-crystal or if color matching failed
        name_lower = ingredient_name.lower()
        product_name_lower = product_name.lower()

        # Exact match
        if name_lower == product_name_lower:
            match_info["score"] = 100
            match_info["match_type"] = "exact"
            substitutes.append(match_info)
            continue

        # Contains match - but be careful with maltster brands
        if name_lower in product_name_lower:
            # If ingredient has a maltster, require it to be present in product too
            if ingredient_maltster:
                if ingredient_maltster in product_name_lower:
                    match_info["score"] = 85
                    match_info["match_type"] = "contains"
                    substitutes.append(match_info)
                # Otherwise skip - don't match "BEST Pale Ale" to "Simpsons Best Pale Ale"
            else:
                match_info["score"] = 85
                match_info["match_type"] = "contains"
                substitutes.append(match_info)
            continue

        if product_name_lower in name_lower:
            match_info["score"] = 75
            match_info["match_type"] = "partial"
            substitutes.append(match_info)
            continue

        # Word overlap matching
        name_words = set(name_lower.replace("-", " ").replace("/", " ").split())
        product_words = set(product_name_lower.replace("-", " ").replace("/", " ").split())

        # Remove common filler words
        filler_words = {"malt", "malts", "the", "a", "an", "-", "/"}
        name_words -= filler_words
        product_words -= filler_words

        # Remove maltster brand words to prevent "BEST Pale Ale" matching "Simpsons Best Pale Ale"
        # because "best" appears in both but means different things
        if ingredient_maltster:
            maltster_words = set(ingredient_maltster.split())
            name_words -= maltster_words
        if product_maltster:
            maltster_words = set(product_maltster.split())
            product_words -= maltster_words

        if name_words and product_words:
            overlap = len(name_words & product_words)
            total = len(name_words | product_words)
            if overlap > 0:
                word_score = (overlap / total) * 70  # Max 70 for word matching
                if word_score >= 30:  # Minimum threshold
                    match_info["score"] = word_score
                    match_info["match_type"] = "word_overlap"
                    match_info["details"]["matching_words"] = list(name_words & product_words)
                    substitutes.append(match_info)

    # Sort by score descending
    substitutes.sort(key=lambda x: x["score"], reverse=True)

    return substitutes


async def _smart_match_ingredient(
    ingredient_name: str,
    products: list[dict],
    stock: list[dict] | None = None,
    min_score: float = 50.0,
    # BeerSmith metadata (optional)
    supplier: str | None = None,  # Grain supplier/maltster (e.g., "BESTMALZ", "Simpsons")
    origin: str | None = None,  # Ingredient origin country
    lab: str | None = None,  # Yeast lab (e.g., "Fermentis", "White Labs")
    product_id: str | None = None,  # Yeast product ID (e.g., "US-05", "WLP001")
    color_lovibond: float | None = None,  # Grain color in Lovibond
) -> dict:
    """
    Smart ingredient matching with color awareness for brewing ingredients.

    When BeerSmith metadata is provided (supplier, lab, product_id, color_lovibond),
    matching uses this structured data for more accurate results.

    Match types returned:
    - exact: Exact name match (score 100)
    - yeast_id: Yeast product ID match (score 100)
    - color: Crystal malt color match (score varies)
    - contains/partial: Name substring match (score 75-85)
    - lab_name: Same yeast lab + name similarity (score 80)
    - fuzzy_name: Word overlap match (score varies)
    - equivalent: Functionally equivalent yeast (score 40, requires confirmation)
    - different_maltster: Similar malt from different supplier (score 30, requires confirmation)

    Args:
        ingredient_name: The ingredient name to match
        products: List of Grocy products
        stock: Optional stock data for availability info
        min_score: Minimum match score to consider (default 50)
        supplier: BeerSmith grain supplier/maltster (optional)
        origin: BeerSmith origin country (optional)
        lab: BeerSmith yeast lab (optional)
        product_id: BeerSmith yeast product ID (optional)
        color_lovibond: BeerSmith grain color in Lovibond (optional)

    Returns:
        Dictionary with match result, including best_match and alternatives.
    """
    substitutes = _find_ingredient_substitutes(
        ingredient_name,
        products,
        stock,
        supplier=supplier,
        lab=lab,
        product_id=product_id,
        color_lovibond=color_lovibond,
    )

    # Filter by minimum score
    valid_matches = [s for s in substitutes if s["score"] >= min_score]

    if not valid_matches:
        # Check if there are any lower-score suggestions (equivalents, different maltsters)
        suggestions = [s for s in substitutes if s["score"] > 0]
        return {
            "found": False,
            "ingredient": ingredient_name,
            "best_match": None,
            "alternatives": [],
            "suggestions": suggestions[:3] if suggestions else [],  # Low-score suggestions
        }

    best_match = valid_matches[0]
    alternatives = valid_matches[1:5]  # Top 4 alternatives

    # Determine match quality
    is_exact = best_match["match_type"] == "exact" and best_match["score"] == 100
    is_yeast_id = best_match["match_type"] == "yeast_id" and best_match["score"] == 100
    requires_confirmation = best_match["match_type"] in ["equivalent", "different_maltster"]

    return {
        "found": True,
        "ingredient": ingredient_name,
        "best_match": best_match,
        "alternatives": alternatives,
        "is_exact": is_exact or is_yeast_id,
        "requires_confirmation": requires_confirmation,
    }


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
    async def get_products_with_stock_entries(
        category: str | None = None,
        only_in_stock: bool = True,
    ) -> list[dict]:
        """
        Get stock entries for multiple products efficiently.

        This is much faster than calling get_product_entries repeatedly for each product
        as it fetches all data in one pass.

        Args:
            category: Optional product group/category filter (e.g., "Hops", "Grains")
            only_in_stock: Only return products that currently have stock (default True)

        Returns list of products with their stock entries, purchase dates, prices, etc.
        """
        client = _get_client()

        # Fetch all data once
        products = await client.get_products()
        stock = await client.get_stock()
        groups = await client.get_product_groups()
        locations = await client.get_locations()

        # Build maps
        stock_map = {s.get("product_id"): s for s in stock}
        group_map = {g["id"]: g.get("name") for g in groups}
        loc_map = {loc["id"]: loc.get("name") for loc in locations}

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

        # Filter by stock if requested
        if only_in_stock:
            products = [
                p for p in products
                if stock_map.get(p["id"], {}).get("amount", 0) > 0
            ]

        # Get entries for each product
        results = []
        for product in products:
            product_id = product.get("id")
            stock_item = stock_map.get(product_id, {})

            # Get stock entries for this product
            try:
                entries = await client.get_product_stock_entries(product_id)
            except Exception:
                entries = []

            # Format entries
            formatted_entries = [
                {
                    "entry_id": e.get("id"),
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

            results.append({
                "product_id": product_id,
                "product_name": product.get("name"),
                "category": group_map.get(product.get("product_group_id"), "Uncategorized"),
                "total_stock": stock_item.get("amount", 0),
                "total_stock_opened": stock_item.get("amount_opened", 0),
                "entries": formatted_entries,
                "entry_count": len(formatted_entries),
            })

        return results

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
        use_substitutes: bool = True,
        min_match_score: float = 50.0,
    ) -> dict:
        """
        Create a new recipe with smart ingredient matching.

        Uses intelligent matching for brewing ingredients:
        - Yeast: Matches by product ID (US-05, M47, WLP001) and lab
        - Crystal/Caramel malts: Matches based on color (Lovibond/EBC)
        - Branded malts: Only matches within same maltster (BESTMALZ, Simpsons, etc.)
        - Other ingredients: Uses fuzzy name matching
        - Reports substitutes when exact match not found

        Args:
            name: Recipe name
            ingredients: List of ingredients, each with:
                - name: Product name (required)
                - amount: Amount required (default 1)
                - note: Optional note

                BeerSmith metadata (optional, improves matching accuracy):
                - supplier: Grain supplier/maltster (e.g., "BESTMALZ", "Simpsons")
                - origin: Ingredient origin country
                - lab: Yeast lab (e.g., "Fermentis", "White Labs")
                - product_id: Yeast product ID (e.g., "US-05", "WLP001")
                - color: Grain color in Lovibond

            description: Recipe description
            servings: Number of servings (default 1)
            use_substitutes: If True, use substitute matches when exact not found (default True)
            min_match_score: Minimum score (0-100) for substitute matching (default 50)

        Returns created recipe with ingredient matching details.
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

        # Get products and stock for smart matching
        products = await client.get_products()
        stock = await client.get_stock()

        added_ingredients = []
        substituted_ingredients = []
        not_found_ingredients = []

        for ing in ingredients:
            ing_name = ing.get("name", "")
            amount = ing.get("amount", 1)
            note = ing.get("note")

            # Extract BeerSmith metadata for improved matching
            supplier = ing.get("supplier")  # Grain maltster
            origin = ing.get("origin")  # Ingredient origin
            lab = ing.get("lab")  # Yeast lab
            yeast_product_id = ing.get("product_id")  # Yeast product ID
            color_lovibond = ing.get("color")  # Grain color in Lovibond

            # Use smart matching with BeerSmith metadata
            match_result = await _smart_match_ingredient(
                ing_name,
                products,
                stock,
                min_score=min_match_score,
                supplier=supplier,
                origin=origin,
                lab=lab,
                product_id=yeast_product_id,
                color_lovibond=color_lovibond,
            )

            if match_result["found"]:
                best_match = match_result["best_match"]
                matched_product_id = best_match["product_id"]
                matched_product_name = best_match["product_name"]

                # Decide whether to use this match
                is_exact = match_result["is_exact"]
                should_use = is_exact or use_substitutes

                if should_use:
                    await client.add_recipe_ingredient(
                        recipe_id=recipe_id,
                        product_id=matched_product_id,
                        amount=amount,
                        note=note,
                    )

                    ingredient_info = {
                        "requested": ing_name,
                        "matched": matched_product_name,
                        "amount": amount,
                        "match_type": best_match["match_type"],
                        "match_score": best_match["score"],
                    }

                    # Add color details for crystal malt matches
                    if best_match["match_type"] == "color" and best_match.get("details"):
                        ingredient_info["color_match"] = best_match["details"]

                    # Add stock info if available
                    if "stock_amount" in best_match:
                        ingredient_info["stock_available"] = best_match["stock_amount"]

                    if is_exact:
                        added_ingredients.append(ingredient_info)
                    else:
                        # Include alternatives for substituted ingredients
                        ingredient_info["alternatives"] = [
                            {
                                "name": alt["product_name"],
                                "score": alt["score"],
                                "match_type": alt["match_type"],
                            }
                            for alt in match_result["alternatives"][:3]
                        ]
                        substituted_ingredients.append(ingredient_info)
                else:
                    # Match found but substitutes disabled
                    not_found_ingredients.append({
                        "name": ing_name,
                        "suggested_substitute": matched_product_name,
                        "match_score": best_match["score"],
                        "match_type": best_match["match_type"],
                    })
            else:
                not_found_ingredients.append({
                    "name": ing_name,
                    "suggested_substitute": None,
                })

        return {
            "success": True,
            "recipe_id": recipe_id,
            "recipe_name": name,
            "ingredients_added": added_ingredients,
            "ingredients_substituted": substituted_ingredients,
            "ingredients_not_found": not_found_ingredients,
            "summary": {
                "exact_matches": len(added_ingredients),
                "substitutes_used": len(substituted_ingredients),
                "not_found": len(not_found_ingredients),
            },
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

    # ==================== Ingredient Matching ====================

    @mcp.tool()
    async def find_ingredient_substitutes(
        ingredient_name: str,
        tolerance_ebc: float = 30.0,
        min_score: float = 30.0,
        include_stock: bool = True,
    ) -> dict:
        """
        Find substitute products for a brewing ingredient.

        Matching strategies by ingredient type:
        - Yeast: Matches by product ID (US-05, M47, WLP001), lab, or functional equivalents
        - Crystal/caramel malts: Uses color matching (Lovibond/EBC)
        - Branded malts: Only matches within same maltster (BESTMALZ, Simpsons, etc.)
        - Other ingredients: Uses fuzzy name matching

        This is useful for:
        - Finding equivalent yeasts (e.g., "US-05" matches "Safale US-05" or suggests "WLP001")
        - Finding equivalent malts based on color (e.g., "Crystal 60L" → "Crystal 150 EBC")
        - Identifying products you already have that could substitute
        - Recipe planning with available inventory

        Args:
            ingredient_name: The ingredient to find substitutes for
            tolerance_ebc: EBC color tolerance for malt matching (default 30)
            min_score: Minimum match score (0-100) to include (default 30)
            include_stock: Include stock availability in results (default True)

        Returns list of substitute matches sorted by score.
        """
        client = _get_client()

        products = await client.get_products()
        stock = await client.get_stock() if include_stock else None

        # Detect ingredient type
        is_yeast = _is_yeast_product(ingredient_name)
        is_crystal = _is_crystal_malt(ingredient_name)
        color_info = _parse_malt_color(ingredient_name) if not is_yeast else None
        maltster = _extract_maltster(ingredient_name) if not is_yeast else None
        yeast_info = _extract_yeast_id(ingredient_name) if is_yeast else None

        substitutes = _find_ingredient_substitutes(
            ingredient_name,
            products,
            stock,
            tolerance_ebc=tolerance_ebc,
        )

        # Filter by minimum score
        valid_substitutes = [s for s in substitutes if s["score"] >= min_score]

        result = {
            "ingredient": ingredient_name,
            "ingredient_type": "yeast" if is_yeast else ("crystal_malt" if is_crystal else "malt" if maltster else "other"),
            "substitutes_found": len(valid_substitutes),
            "substitutes": valid_substitutes[:10],  # Top 10
        }

        # Add yeast info if parsed
        if yeast_info:
            result["parsed_yeast"] = {
                "id": yeast_info["id"],
                "lab": yeast_info["lab"],
            }
            equivalents = _get_yeast_equivalents(yeast_info["normalized"])
            if equivalents:
                result["known_equivalents"] = equivalents

        # Add color info if parsed
        if color_info:
            result["parsed_color"] = {
                "lovibond": round(color_info["lovibond"], 1),
                "ebc": round(color_info["ebc_mid"], 1),
                "source": color_info["source"],
            }

        # Add maltster info if detected
        if maltster:
            result["detected_maltster"] = maltster

        # Add recommendation based on match type
        if valid_substitutes:
            best = valid_substitutes[0]
            match_type = best["match_type"]

            if match_type == "exact":
                result["recommendation"] = f"Exact match found: {best['product_name']}"
            elif match_type == "yeast_id":
                result["recommendation"] = f"Yeast ID match: {best['product_name']} ({best['details'].get('matched_id', '?')})"
            elif match_type == "equivalent":
                result["recommendation"] = (
                    f"Functional equivalent: {best['product_name']} - "
                    f"equivalent to {best['details'].get('equivalent_to', '?')} (requires confirmation)"
                )
            elif match_type == "color":
                result["recommendation"] = (
                    f"Color match: {best['product_name']} "
                    f"({best['details'].get('product_ebc_range', '?')} EBC, "
                    f"{best['details'].get('ebc_difference', '?')} EBC difference)"
                )
            elif match_type == "different_maltster":
                result["recommendation"] = (
                    f"Different maltster: {best['product_name']} "
                    f"(from {best['details'].get('product_maltster', '?')}, "
                    f"requested {best['details'].get('requested_maltster', '?')}) - requires confirmation"
                )
            else:
                result["recommendation"] = f"Best fuzzy match: {best['product_name']} (score: {best['score']:.0f})"
        else:
            # Check for low-score suggestions
            suggestions = [s for s in substitutes if s["score"] > 0]
            if suggestions:
                sugg = suggestions[0]
                if sugg["match_type"] == "equivalent":
                    result["recommendation"] = (
                        f"No direct match, but equivalent yeast available: {sugg['product_name']}"
                    )
                elif sugg["match_type"] == "different_maltster":
                    result["recommendation"] = (
                        f"No match from same maltster. Alternative from {sugg['details'].get('product_maltster', '?')}: "
                        f"{sugg['product_name']}"
                    )
                else:
                    result["recommendation"] = "No suitable substitutes found"
                result["low_score_suggestions"] = suggestions[:3]
            else:
                result["recommendation"] = "No suitable substitutes found"

        return result

    @mcp.tool()
    async def convert_malt_color(
        value: float,
        from_unit: str = "lovibond",
    ) -> dict:
        """
        Convert malt color between Lovibond and EBC units.

        Common crystal malt reference points:
        - Crystal 10L = 26 EBC (Very light)
        - Crystal 40L = 105 EBC (Light)
        - Crystal 60L = 158 EBC (Medium)
        - Crystal 80L = 211 EBC (Medium-dark)
        - Crystal 120L = 316 EBC (Dark)

        Args:
            value: The color value to convert
            from_unit: Source unit - "lovibond" or "ebc" (default "lovibond")

        Returns converted value in both units.
        """
        from_unit_lower = from_unit.lower()

        if from_unit_lower in ["lovibond", "l", "°l"]:
            lovibond = value
            ebc = _lovibond_to_ebc(value)
        elif from_unit_lower in ["ebc"]:
            ebc = value
            lovibond = _ebc_to_lovibond(value)
        else:
            return {"error": f"Unknown unit: {from_unit}. Use 'lovibond' or 'ebc'."}

        # Get color description
        if lovibond <= 10:
            desc = "Very pale (Pilsner range)"
        elif lovibond <= 20:
            desc = "Pale/Light (Pale Ale range)"
        elif lovibond <= 40:
            desc = "Light amber"
        elif lovibond <= 60:
            desc = "Amber/Medium"
        elif lovibond <= 80:
            desc = "Medium-dark amber"
        elif lovibond <= 120:
            desc = "Dark amber/Brown"
        elif lovibond <= 200:
            desc = "Dark brown"
        else:
            desc = "Very dark (Stout range)"

        return {
            "lovibond": round(lovibond, 1),
            "ebc": round(ebc, 1),
            "description": desc,
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
        location_id: int | None = None,
        source_url: str | None = None,
    ) -> dict:
        """
        Create a new product with smart defaults for brewing ingredients.

        The quantity unit is automatically selected based on the product category:
        - Grains/Malts/Hops/Adjuncts → grams (g)
        - Yeast → pieces
        - Liquids/Extracts → ml or L
        - Other categories → pieces

        If a source_url is provided and no description is given, the tool will
        attempt to fetch the product description from the URL.

        Args:
            name: Product name
            description: Product description (if not provided, will try to fetch from source_url)
            product_group_id: Product group ID (optional, can be found using get_product_groups)
            min_stock_amount: Minimum stock level
            location_id: Default location ID (optional, can be found using get_locations)
            source_url: URL to product page (used to fetch description if not provided)

        Returns created product or error details.
        """
        client = _get_client()

        # Fetch product groups for validation and unit selection
        groups = await client.get_product_groups()
        group_map = {g["id"]: g for g in groups}

        # Validate product_group_id if provided
        if product_group_id is not None:
            group_ids = [g["id"] for g in groups]
            if product_group_id not in group_ids:
                return {
                    "error": f"Invalid product_group_id {product_group_id}. Valid IDs: {group_ids}",
                    "available_groups": [
                        {"id": g["id"], "name": g["name"]}
                        for g in groups
                    ],
                }

        # Get locations and validate/set default location_id
        locations = await client.get_locations()
        if not locations:
            return {"error": "No locations found in Grocy. Please create a location first."}

        if location_id is not None:
            location_ids = [loc["id"] for loc in locations]
            if location_id not in location_ids:
                return {
                    "error": f"Invalid location_id {location_id}. Valid IDs: {location_ids}",
                    "available_locations": [
                        {"id": loc["id"], "name": loc["name"]}
                        for loc in locations
                    ],
                }
        else:
            # Use first location as default if none specified
            location_id = locations[0]["id"]

        # Get quantity units
        units = await client.get_quantity_units()
        default_unit = units[0]["id"] if units else 1

        # Select appropriate unit based on product category
        selected_unit = default_unit
        category_name = None
        if product_group_id is not None and product_group_id in group_map:
            category_name = group_map[product_group_id].get("name", "")
            category_unit = _get_unit_for_category(category_name, units)
            if category_unit is not None:
                selected_unit = category_unit

        # If no description provided but source_url is, try to fetch it
        url_fetch_result = None
        final_description = description
        if source_url and not description:
            url_fetch_result = await _fetch_product_description_from_url(source_url)
            if url_fetch_result.get("success") and url_fetch_result.get("description"):
                final_description = url_fetch_result["description"]
                # Append source URL to description
                final_description = f"{final_description}\n\nSource: {source_url}"

        product_data = {
            "name": name,
            "qu_id_purchase": selected_unit,
            "qu_id_stock": selected_unit,
            "min_stock_amount": min_stock_amount,
            "location_id": location_id,
        }
        if final_description:
            product_data["description"] = final_description
        if product_group_id is not None:
            product_data["product_group_id"] = product_group_id

        # Find unit name for response
        unit_name = "unknown"
        for u in units:
            if u["id"] == selected_unit:
                unit_name = u.get("name", "unknown")
                break

        try:
            result = await client.create_product(product_data)
            response = {
                "success": True,
                "product": result,
                "unit_selected": unit_name,
            }
            if category_name:
                response["category"] = category_name
            if url_fetch_result:
                response["url_fetch"] = {
                    "attempted": True,
                    "success": url_fetch_result.get("success", False),
                    "source_url": source_url,
                }
                if not url_fetch_result.get("success"):
                    response["url_fetch"]["error"] = url_fetch_result.get("error")
            return response
        except Exception as e:
            # Return detailed error information
            return {
                "success": False,
                "error": str(e),
                "product_data_sent": product_data,
            }

    @mcp.tool()
    async def update_product(
        product_id: int,
        name: str | None = None,
        description: str | None = None,
        product_group_id: int | None = None,
        min_stock_amount: float | None = None,
        location_id: int | None = None,
        source_url: str | None = None,
        fix_unit_from_category: bool = False,
    ) -> dict:
        """
        Update an existing product's details.

        Use fix_unit_from_category=True to automatically set the quantity unit
        based on the product's category (grains/hops → grams, yeast → pieces).

        Args:
            product_id: Product ID to update
            name: New product name (optional)
            description: New description (optional, or fetch from source_url)
            product_group_id: New product group ID (optional)
            min_stock_amount: New minimum stock level (optional)
            location_id: New default location ID (optional)
            source_url: URL to fetch description from (if description not provided)
            fix_unit_from_category: If True, automatically set quantity unit based on category

        Returns updated product details.
        """
        client = _get_client()

        # Get current product
        try:
            current = await client.get_entity("products", product_id)
        except Exception as e:
            return {"error": f"Product {product_id} not found: {e}"}

        # Build update data
        update_data = {}

        if name is not None:
            update_data["name"] = name

        # Handle description - fetch from URL if needed
        if description is not None:
            update_data["description"] = description
        elif source_url:
            url_result = await _fetch_product_description_from_url(source_url)
            if url_result.get("success") and url_result.get("description"):
                update_data["description"] = f"{url_result['description']}\n\nSource: {source_url}"

        if product_group_id is not None:
            update_data["product_group_id"] = product_group_id

        if min_stock_amount is not None:
            update_data["min_stock_amount"] = min_stock_amount

        if location_id is not None:
            update_data["location_id"] = location_id

        # Fix quantity unit based on category
        if fix_unit_from_category:
            groups = await client.get_product_groups()
            group_map = {g["id"]: g for g in groups}
            units = await client.get_quantity_units()

            # Use new product_group_id if provided, else current
            group_id = product_group_id if product_group_id is not None else current.get("product_group_id")
            if group_id and group_id in group_map:
                category_name = group_map[group_id].get("name", "")
                category_unit = _get_unit_for_category(category_name, units)
                if category_unit is not None:
                    update_data["qu_id_purchase"] = category_unit
                    update_data["qu_id_stock"] = category_unit

        if not update_data:
            return {"success": True, "message": "No changes to apply", "product_id": product_id}

        try:
            await client.update_entity("products", product_id, update_data)

            # Get unit name for response
            unit_name = None
            if "qu_id_stock" in update_data:
                units = await client.get_quantity_units()
                for u in units:
                    if u["id"] == update_data["qu_id_stock"]:
                        unit_name = u.get("name")
                        break

            response = {
                "success": True,
                "product_id": product_id,
                "updated_fields": list(update_data.keys()),
            }
            if unit_name:
                response["new_unit"] = unit_name
            return response
        except Exception as e:
            return {"success": False, "error": str(e), "product_id": product_id}

    @mcp.tool()
    async def fix_product_units_by_category(
        category: str | None = None,
        dry_run: bool = True,
    ) -> dict:
        """
        Fix quantity units for products based on their category.

        This updates products in the specified category to use the appropriate unit:
        - Grains/Malts/Hops/Adjuncts → grams (g)
        - Yeast → pieces
        - Liquids/Extracts → ml or L

        Args:
            category: Category to fix (e.g., "Grains", "Hops"). If not specified, fixes all.
            dry_run: If True (default), only report what would change without making changes.

        Returns summary of changes made or planned.
        """
        client = _get_client()

        products = await client.get_products()
        groups = await client.get_product_groups()
        units = await client.get_quantity_units()

        group_map = {g["id"]: g for g in groups}
        unit_map = {u["id"]: u.get("name") for u in units}

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

        changes = []
        errors = []

        for product in products:
            product_id = product["id"]
            product_name = product.get("name", "Unknown")
            group_id = product.get("product_group_id")
            current_unit_id = product.get("qu_id_stock")
            current_unit_name = unit_map.get(current_unit_id, "unknown")

            if not group_id or group_id not in group_map:
                continue

            category_name = group_map[group_id].get("name", "")
            expected_unit_id = _get_unit_for_category(category_name, units)

            if expected_unit_id is None:
                continue

            if current_unit_id != expected_unit_id:
                expected_unit_name = unit_map.get(expected_unit_id, "unknown")
                change = {
                    "product_id": product_id,
                    "product_name": product_name,
                    "category": category_name,
                    "current_unit": current_unit_name,
                    "expected_unit": expected_unit_name,
                }

                if not dry_run:
                    try:
                        await client.update_entity("products", product_id, {
                            "qu_id_purchase": expected_unit_id,
                            "qu_id_stock": expected_unit_id,
                        })
                        change["status"] = "fixed"
                    except Exception as e:
                        change["status"] = "error"
                        change["error"] = str(e)
                        errors.append(change)
                        continue
                else:
                    change["status"] = "would_fix"

                changes.append(change)

        return {
            "dry_run": dry_run,
            "products_checked": len(products),
            "changes_needed": len(changes),
            "errors": len(errors),
            "changes": changes,
        }

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
