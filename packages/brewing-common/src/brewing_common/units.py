"""
Unit conversion utilities for brewing measurements.

Supports mass, volume, temperature, and colour unit conversions.
All internal representations use metric base units:
- Mass: grams
- Volume: litres
- Temperature: Celsius
- Colour: EBC
"""

from enum import Enum

from brewing_common.exceptions import UnitConversionError


class MassUnit(str, Enum):
    """Mass/weight units."""

    KG = "kg"
    G = "g"
    MG = "mg"
    LB = "lb"
    OZ = "oz"


class VolumeUnit(str, Enum):
    """Volume units."""

    L = "l"
    ML = "ml"
    GAL_US = "gal_us"
    GAL_UK = "gal_uk"
    QT = "qt"
    PT_US = "pt_us"
    PT_UK = "pt_uk"
    FL_OZ_US = "fl_oz_us"
    FL_OZ_UK = "fl_oz_uk"
    BBL = "bbl"  # US barrel (31 gallons)


class TemperatureUnit(str, Enum):
    """Temperature units."""

    C = "c"
    F = "f"
    K = "k"


class ColourUnit(str, Enum):
    """Beer colour units."""

    EBC = "ebc"
    SRM = "srm"
    LOVIBOND = "lovibond"


# Conversion constants to base units
MASS_TO_GRAMS: dict[MassUnit, float] = {
    MassUnit.KG: 1000.0,
    MassUnit.G: 1.0,
    MassUnit.MG: 0.001,
    MassUnit.LB: 453.59237,
    MassUnit.OZ: 28.349523125,
}

VOLUME_TO_LITRES: dict[VolumeUnit, float] = {
    VolumeUnit.L: 1.0,
    VolumeUnit.ML: 0.001,
    VolumeUnit.GAL_US: 3.785411784,
    VolumeUnit.GAL_UK: 4.54609,
    VolumeUnit.QT: 0.946352946,
    VolumeUnit.PT_US: 0.473176473,
    VolumeUnit.PT_UK: 0.56826125,
    VolumeUnit.FL_OZ_US: 0.0295735295625,
    VolumeUnit.FL_OZ_UK: 0.0284130625,
    VolumeUnit.BBL: 117.347765,  # US barrel = 31 US gallons
}


def convert_mass(
    value: float,
    from_unit: MassUnit | str,
    to_unit: MassUnit | str,
) -> float:
    """
    Convert between mass units.

    Args:
        value: The value to convert
        from_unit: Source unit
        to_unit: Target unit

    Returns:
        Converted value

    Raises:
        UnitConversionError: If units are invalid
    """
    # Handle string inputs
    if isinstance(from_unit, str):
        try:
            from_unit = MassUnit(from_unit.lower())
        except ValueError as e:
            raise UnitConversionError(f"Unknown mass unit: {from_unit}") from e

    if isinstance(to_unit, str):
        try:
            to_unit = MassUnit(to_unit.lower())
        except ValueError as e:
            raise UnitConversionError(f"Unknown mass unit: {to_unit}") from e

    # Convert via grams as intermediate
    grams = value * MASS_TO_GRAMS[from_unit]
    return grams / MASS_TO_GRAMS[to_unit]


def convert_volume(
    value: float,
    from_unit: VolumeUnit | str,
    to_unit: VolumeUnit | str,
) -> float:
    """
    Convert between volume units.

    Args:
        value: The value to convert
        from_unit: Source unit
        to_unit: Target unit

    Returns:
        Converted value

    Raises:
        UnitConversionError: If units are invalid
    """
    if isinstance(from_unit, str):
        try:
            from_unit = VolumeUnit(from_unit.lower())
        except ValueError as e:
            raise UnitConversionError(f"Unknown volume unit: {from_unit}") from e

    if isinstance(to_unit, str):
        try:
            to_unit = VolumeUnit(to_unit.lower())
        except ValueError as e:
            raise UnitConversionError(f"Unknown volume unit: {to_unit}") from e

    # Convert via litres as intermediate
    litres = value * VOLUME_TO_LITRES[from_unit]
    return litres / VOLUME_TO_LITRES[to_unit]


def convert_temperature(
    value: float,
    from_unit: TemperatureUnit | str,
    to_unit: TemperatureUnit | str,
) -> float:
    """
    Convert between temperature units.

    Args:
        value: The value to convert
        from_unit: Source unit
        to_unit: Target unit

    Returns:
        Converted value

    Raises:
        UnitConversionError: If units are invalid
    """
    if isinstance(from_unit, str):
        try:
            from_unit = TemperatureUnit(from_unit.lower())
        except ValueError as e:
            raise UnitConversionError(f"Unknown temperature unit: {from_unit}") from e

    if isinstance(to_unit, str):
        try:
            to_unit = TemperatureUnit(to_unit.lower())
        except ValueError as e:
            raise UnitConversionError(f"Unknown temperature unit: {to_unit}") from e

    # First convert to Celsius
    if from_unit == TemperatureUnit.F:
        celsius = (value - 32) * 5 / 9
    elif from_unit == TemperatureUnit.K:
        celsius = value - 273.15
    else:
        celsius = value

    # Then convert to target
    if to_unit == TemperatureUnit.F:
        return celsius * 9 / 5 + 32
    elif to_unit == TemperatureUnit.K:
        return celsius + 273.15
    return celsius


# Colour conversions
def srm_to_ebc(srm: float) -> float:
    """
    Convert SRM (Standard Reference Method) to EBC.

    EBC = SRM × 1.97

    Args:
        srm: Colour in SRM

    Returns:
        Colour in EBC
    """
    return srm * 1.97


def ebc_to_srm(ebc: float) -> float:
    """
    Convert EBC to SRM (Standard Reference Method).

    SRM = EBC / 1.97

    Args:
        ebc: Colour in EBC

    Returns:
        Colour in SRM
    """
    return ebc / 1.97


def lovibond_to_ebc(lovibond: float) -> float:
    """
    Convert Lovibond (grain colour rating) to EBC.

    Uses the formula: SRM = (1.3546 × Lovibond) - 0.76
    Then: EBC = SRM × 1.97

    Args:
        lovibond: Colour in degrees Lovibond

    Returns:
        Colour in EBC
    """
    srm = (1.3546 * lovibond) - 0.76
    return srm_to_ebc(max(0, srm))


def ebc_to_lovibond(ebc: float) -> float:
    """
    Convert EBC to Lovibond (grain colour rating).

    Args:
        ebc: Colour in EBC

    Returns:
        Colour in degrees Lovibond
    """
    srm = ebc_to_srm(ebc)
    return (srm + 0.76) / 1.3546


def lovibond_to_srm(lovibond: float) -> float:
    """
    Convert Lovibond to SRM.

    Args:
        lovibond: Colour in degrees Lovibond

    Returns:
        Colour in SRM
    """
    return (1.3546 * lovibond) - 0.76


def srm_to_lovibond(srm: float) -> float:
    """
    Convert SRM to Lovibond.

    Args:
        srm: Colour in SRM

    Returns:
        Colour in degrees Lovibond
    """
    return (srm + 0.76) / 1.3546


# Gravity conversions
def sg_to_plato(sg: float) -> float:
    """
    Convert specific gravity to degrees Plato.

    Uses the approximation: Plato = 259 - (259 / SG)

    Args:
        sg: Specific gravity (e.g., 1.050)

    Returns:
        Degrees Plato
    """
    return 259 - (259 / sg)


def plato_to_sg(plato: float) -> float:
    """
    Convert degrees Plato to specific gravity.

    Args:
        plato: Degrees Plato

    Returns:
        Specific gravity
    """
    return 259 / (259 - plato)


def sg_to_brix(sg: float) -> float:
    """
    Convert specific gravity to Brix.

    Note: Only accurate for unfermented wort.

    Args:
        sg: Specific gravity

    Returns:
        Degrees Brix
    """
    # More accurate polynomial approximation
    return (
        ((182.4601 * sg - 775.6821) * sg + 1262.7794) * sg - 669.5622
    )


def brix_to_sg(brix: float) -> float:
    """
    Convert Brix to specific gravity.

    Note: Only accurate for unfermented wort.

    Args:
        brix: Degrees Brix

    Returns:
        Specific gravity
    """
    return (brix / (258.6 - ((brix / 258.2) * 227.1))) + 1


# Convenience functions for common conversions
def lb_to_kg(lb: float) -> float:
    """Convert pounds to kilograms."""
    return convert_mass(lb, MassUnit.LB, MassUnit.KG)


def kg_to_lb(kg: float) -> float:
    """Convert kilograms to pounds."""
    return convert_mass(kg, MassUnit.KG, MassUnit.LB)


def oz_to_g(oz: float) -> float:
    """Convert ounces to grams."""
    return convert_mass(oz, MassUnit.OZ, MassUnit.G)


def g_to_oz(g: float) -> float:
    """Convert grams to ounces."""
    return convert_mass(g, MassUnit.G, MassUnit.OZ)


def gal_to_l(gal: float, us: bool = True) -> float:
    """Convert gallons to litres."""
    unit = VolumeUnit.GAL_US if us else VolumeUnit.GAL_UK
    return convert_volume(gal, unit, VolumeUnit.L)


def l_to_gal(litres: float, us: bool = True) -> float:
    """Convert litres to gallons."""
    unit = VolumeUnit.GAL_US if us else VolumeUnit.GAL_UK
    return convert_volume(litres, VolumeUnit.L, unit)


def f_to_c(f: float) -> float:
    """Convert Fahrenheit to Celsius."""
    return convert_temperature(f, TemperatureUnit.F, TemperatureUnit.C)


def c_to_f(c: float) -> float:
    """Convert Celsius to Fahrenheit."""
    return convert_temperature(c, TemperatureUnit.C, TemperatureUnit.F)
