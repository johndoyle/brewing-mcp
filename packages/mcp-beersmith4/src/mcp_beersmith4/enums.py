"""BeerSmith 4 enumeration types derived from schema analysis."""

from enum import IntEnum


class RecipeType(IntEnum):
    """Recipe type (F_R_TYPE)."""

    EXTRACT = 0
    PARTIAL_MASH = 1
    ALL_GRAIN = 2
    CIDER = 3
    MEAD = 4
    WINE = 5


class HopUse(IntEnum):
    """How a hop is used in a recipe (F_H_USE)."""

    BOIL = 0
    DRY_HOP = 1
    MASH = 2
    FIRST_WORT = 3
    AROMA = 4


class HopType(IntEnum):
    """Hop variety type (F_H_TYPE)."""

    BITTERING = 0
    AROMA = 1
    BOTH = 2


class HopForm(IntEnum):
    """Physical form of hops (F_H_FORM)."""

    PELLET = 0
    PLUG = 1
    WHOLE = 2
    EXTRACT = 3


class GrainType(IntEnum):
    """Grain/fermentable type (F_G_TYPE)."""

    GRAIN = 0
    SUGAR = 1
    EXTRACT = 2
    DRY_EXTRACT = 3
    ADJUNCT = 4
    CANDI_SUGAR = 5
    FRUIT = 6
    JUICE = 7


class GrainUse(IntEnum):
    """How grain is used in a recipe (F_G_USE)."""

    MASH = 0
    STEEP = 1
    BOIL = 2
    LATE_ADDITION = 3


class YeastType(IntEnum):
    """Yeast type (F_Y_TYPE)."""

    ALE = 0
    LAGER = 1
    WINE = 2
    CHAMPAGNE = 3
    WHEAT = 4


class YeastForm(IntEnum):
    """Physical form of yeast (F_Y_FORM)."""

    LIQUID = 0
    DRY = 1


class YeastFlocculation(IntEnum):
    """Yeast flocculation (F_Y_FLOCCULATION)."""

    LOW = 0
    MEDIUM = 1
    HIGH = 2
    VERY_HIGH = 3


class MiscType(IntEnum):
    """Miscellaneous ingredient type (F_M_TYPE)."""

    SPICE = 0
    FINING = 1
    WATER_AGENT = 2
    HERB = 3
    FLAVOR = 4
    OTHER = 5


class MiscUse(IntEnum):
    """How a misc ingredient is used (F_M_USE)."""

    BOIL = 0
    MASH = 1
    PRIMARY = 2
    SECONDARY = 3
    BOTTLING = 4


class MashStepType(IntEnum):
    """Mash step type (F_MS_TYPE)."""

    INFUSION = 0
    TEMPERATURE = 1
    DECOCTION = 2


class StyleType(IntEnum):
    """Beer style type (F_S_TYPE)."""

    ALE = 0
    LAGER = 1
    MEAD = 2
    WHEAT = 3
    MIXED = 4
    CIDER = 5


class EquipmentType(IntEnum):
    """Equipment profile type (F_E_TYPE)."""

    EXTRACT = 0
    PARTIAL_MASH = 1
    ALL_GRAIN = 2
    BIAB = 3


class CarbType(IntEnum):
    """Carbonation method type (F_C_TYPE)."""

    FORCE_CARBONATION = 0
    CORN_SUGAR = 1
    DME = 2
    HONEY = 3
    TABLE_SUGAR = 4


# Schema IDs used to discriminate ingredient types in the embedded Ingredients JSON
SCHEMA_GRAIN = "7406"
SCHEMA_HOP = "7403"
SCHEMA_YEAST = "7426"
SCHEMA_MISC = "7421"
SCHEMA_WATER = "7423"
SCHEMA_EQUIPMENT = "7430"
SCHEMA_STYLE = "7428"
SCHEMA_MASH = "7434"
SCHEMA_MASH_STEP = "7432"
