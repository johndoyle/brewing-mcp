"""
Fuzzy string matching utilities for ingredient names.

Uses RapidFuzz for fast, accurate fuzzy matching with support for
ingredient name normalisation and alias resolution.
"""

from typing import TypeVar, Callable
from rapidfuzz import fuzz, process

from brewing_common.exceptions import MatchingError


T = TypeVar("T")


def match_string(
    query: str,
    candidates: list[str],
    threshold: float = 0.7,
    limit: int = 5,
) -> list[tuple[str, float]]:
    """
    Match a query string against candidates using fuzzy matching.

    Uses token_sort_ratio which handles word order variations well,
    making it suitable for ingredient names like "Maris Otter" vs "Otter, Maris".

    Args:
        query: The string to search for
        candidates: List of strings to match against
        threshold: Minimum match score (0.0 to 1.0), default 0.7
        limit: Maximum number of results to return

    Returns:
        List of (match, confidence) tuples above threshold, sorted by confidence

    Example:
        >>> matches = match_string("casade", ["Cascade", "Centennial", "Citra"])
        >>> matches
        [("Cascade", 0.92)]
    """
    if not candidates:
        return []

    if not query or not query.strip():
        return []

    # Use token_sort_ratio for better handling of word order
    results = process.extract(
        query,
        candidates,
        scorer=fuzz.token_sort_ratio,
        limit=limit,
    )

    # Convert scores from 0-100 to 0-1 and filter by threshold
    return [
        (match, score / 100)
        for match, score, _ in results
        if score / 100 >= threshold
    ]


def match_objects(
    query: str,
    candidates: list[T],
    key: Callable[[T], str],
    threshold: float = 0.7,
    limit: int = 5,
) -> list[tuple[T, float]]:
    """
    Match a query string against objects using a key function.

    Useful when matching against objects where you want to extract
    a specific field for matching (e.g., ingredient.name).

    Args:
        query: The string to search for
        candidates: List of objects to match against
        key: Function to extract the string to match from each object
        threshold: Minimum match score (0.0 to 1.0)
        limit: Maximum number of results to return

    Returns:
        List of (object, confidence) tuples above threshold

    Example:
        >>> ingredients = [Ingredient(name="Cascade"), Ingredient(name="Centennial")]
        >>> matches = match_objects("casade", ingredients, lambda i: i.name)
        >>> matches[0][0].name
        "Cascade"
    """
    if not candidates:
        return []

    if not query or not query.strip():
        return []

    # Build lookup from string to object(s)
    # Handle potential duplicates by keeping all objects with same key
    string_to_objs: dict[str, list[T]] = {}
    for obj in candidates:
        k = key(obj)
        if k not in string_to_objs:
            string_to_objs[k] = []
        string_to_objs[k].append(obj)

    # Match against unique strings
    string_matches = match_string(
        query,
        list(string_to_objs.keys()),
        threshold,
        limit,
    )

    # Map back to objects, preserving order
    results: list[tuple[T, float]] = []
    for match_str, confidence in string_matches:
        for obj in string_to_objs[match_str]:
            results.append((obj, confidence))
            if len(results) >= limit:
                break
        if len(results) >= limit:
            break

    return results


def best_match(
    query: str,
    candidates: list[str],
    threshold: float = 0.7,
) -> tuple[str, float] | None:
    """
    Get the single best match above threshold.

    Args:
        query: The string to search for
        candidates: List of strings to match against
        threshold: Minimum match score (0.0 to 1.0)

    Returns:
        (match, confidence) tuple or None if no match above threshold
    """
    matches = match_string(query, candidates, threshold, limit=1)
    return matches[0] if matches else None


def best_match_object(
    query: str,
    candidates: list[T],
    key: Callable[[T], str],
    threshold: float = 0.7,
) -> tuple[T, float] | None:
    """
    Get the single best matching object above threshold.

    Args:
        query: The string to search for
        candidates: List of objects to match against
        key: Function to extract the string to match from each object
        threshold: Minimum match score (0.0 to 1.0)

    Returns:
        (object, confidence) tuple or None if no match above threshold
    """
    matches = match_objects(query, candidates, key, threshold, limit=1)
    return matches[0] if matches else None


# Common ingredient name normalisations and aliases
INGREDIENT_ALIASES: dict[str, list[str]] = {
    # Grains
    "2-row": [
        "two-row",
        "2 row",
        "pale malt 2-row",
        "2-row pale",
        "2-row pale malt",
        "american 2-row",
        "us 2-row",
    ],
    "pilsner": [
        "pils",
        "pilsner malt",
        "pilsen",
        "pils malt",
        "german pilsner",
        "bohemian pilsner",
    ],
    "munich": [
        "munich malt",
        "münchner",
        "munchner",
        "munich i",
        "munich ii",
    ],
    "vienna": ["vienna malt", "wiener"],
    "maris otter": ["maris otter pale", "mo", "marris otter"],
    "crystal 60": ["caramel 60", "c60", "crystal 60l", "caramel 60l"],
    "crystal 40": ["caramel 40", "c40", "crystal 40l", "caramel 40l"],
    "crystal 20": ["caramel 20", "c20", "crystal 20l", "caramel 20l"],
    "chocolate malt": ["chocolate", "choc malt"],
    "black malt": ["black patent", "black patent malt"],
    "roasted barley": ["roast barley"],
    "wheat malt": ["wheat", "malted wheat"],
    "flaked oats": ["oats", "oat flakes"],
    "flaked wheat": ["wheat flakes"],

    # Hops
    "cascade": ["cascade hops", "cascade (us)", "us cascade"],
    "centennial": ["centennial hops", "centennial (us)"],
    "citra": ["citra hops", "citra (us)"],
    "mosaic": ["mosaic hops", "mosaic (us)"],
    "simcoe": ["simcoe hops", "simcoe (us)"],
    "amarillo": ["amarillo hops", "amarillo (us)"],
    "galaxy": ["galaxy hops", "galaxy (au)", "australian galaxy"],
    "nelson sauvin": ["nelson", "nelson sauvin (nz)"],
    "saaz": ["saaz hops", "czech saaz"],
    "hallertau": ["hallertauer", "hallertau mittelfrüh", "hallertauer mittelfruh"],
    "east kent goldings": ["ekg", "kent goldings", "goldings"],
    "fuggle": ["fuggles", "fuggle hops"],

    # Yeasts
    "us-05": [
        "safale us-05",
        "us05",
        "american ale yeast",
        "us-05 american ale",
        "fermentis us-05",
    ],
    "s-04": [
        "safale s-04",
        "s04",
        "english ale yeast",
        "s-04 english ale",
        "fermentis s-04",
    ],
    "s-33": ["safale s-33", "s33"],
    "w-34/70": ["saflager w-34/70", "w34/70", "34/70", "german lager yeast"],
    "nottingham": ["danstar nottingham", "lallemand nottingham"],
    "london ale iii": ["wyeast 1318", "1318"],
    "california ale": ["wlp001", "wyeast 1056", "1056", "american ale"],

    # Misc
    "irish moss": ["carrageenan", "whirlfloc"],
    "gypsum": ["calcium sulfate", "caso4"],
    "calcium chloride": ["cacl2"],
}


def normalise_ingredient_name(name: str) -> str:
    """
    Normalise an ingredient name to a canonical form.

    Handles common variations and aliases, converting them to a
    standard name for consistent matching across systems.

    Args:
        name: The ingredient name to normalise

    Returns:
        Normalised canonical name

    Example:
        >>> normalise_ingredient_name("Safale US-05")
        "us-05"
        >>> normalise_ingredient_name("Cascade (US)")
        "cascade"
    """
    name_lower = name.lower().strip()

    # Check if this is a known canonical name
    if name_lower in INGREDIENT_ALIASES:
        return name_lower

    # Check if this matches any known alias
    for canonical, aliases in INGREDIENT_ALIASES.items():
        aliases_lower = [a.lower() for a in aliases]
        if name_lower in aliases_lower:
            return canonical

    # No known alias, return cleaned version
    return name_lower


def find_canonical_name(
    name: str,
    threshold: float = 0.85,
) -> str | None:
    """
    Try to find a canonical name for an ingredient using fuzzy matching.

    Searches both canonical names and their aliases for the best match.

    Args:
        name: The ingredient name to look up
        threshold: Minimum match score (higher for stricter matching)

    Returns:
        Canonical name if a good match is found, None otherwise
    """
    name_lower = name.lower().strip()

    # First try exact matching
    if name_lower in INGREDIENT_ALIASES:
        return name_lower

    for canonical, aliases in INGREDIENT_ALIASES.items():
        aliases_lower = [a.lower() for a in aliases]
        if name_lower in aliases_lower:
            return canonical

    # Build list of all possible names for fuzzy matching
    all_names: list[tuple[str, str]] = []  # (searchable_name, canonical)
    for canonical, aliases in INGREDIENT_ALIASES.items():
        all_names.append((canonical, canonical))
        for alias in aliases:
            all_names.append((alias.lower(), canonical))

    # Fuzzy match against all names
    searchable_names = [n[0] for n in all_names]
    matches = match_string(name_lower, searchable_names, threshold, limit=1)

    if matches:
        matched_name, _ = matches[0]
        # Find the canonical name for this match
        for searchable, canonical in all_names:
            if searchable == matched_name:
                return canonical

    return None


def suggest_ingredient_names(
    query: str,
    limit: int = 5,
) -> list[str]:
    """
    Suggest canonical ingredient names based on a query.

    Useful for autocomplete functionality.

    Args:
        query: Partial ingredient name
        limit: Maximum number of suggestions

    Returns:
        List of canonical ingredient names
    """
    if not query or not query.strip():
        return []

    # Get all canonical names
    canonical_names = list(INGREDIENT_ALIASES.keys())

    # Fuzzy match with lower threshold for suggestions
    matches = match_string(query, canonical_names, threshold=0.4, limit=limit)

    return [name for name, _ in matches]
