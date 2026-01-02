"""Pydantic models for BeerSmith data structures."""

from datetime import date
from enum import IntEnum
from typing import Annotated, Optional, Union

from pydantic import BaseModel, BeforeValidator, Field, field_validator


# Helper to coerce int to str
def coerce_to_str(v: Union[int, str, None]) -> str:
    if v is None:
        return ""
    return str(v)


StrOrInt = Annotated[str, BeforeValidator(coerce_to_str)]


# === Enums ===


class HopType(IntEnum):
    """Hop type classification."""

    BITTERING = 0
    AROMA = 1
    BOTH = 2
    WHIRLPOOL = 3  # Some recipes use this


class HopForm(IntEnum):
    """Hop form/packaging."""

    PELLET = 0
    PLUG = 1
    LEAF = 2
    EXTRACT = 3
    CRYO = 4  # Cryogenic hops


class HopUse(IntEnum):
    """When hops are used in the brewing process."""

    BOIL = 0
    DRY_HOP = 1
    MASH = 2
    FIRST_WORT = 3
    AROMA = 4  # Whirlpool/steep


class GrainType(IntEnum):
    """Grain/fermentable type classification."""

    GRAIN = 0
    EXTRACT_LIQUID = 1
    EXTRACT_DRY = 4
    ADJUNCT = 3
    SUGAR = 2
    FRUIT = 5
    JUICE = 6
    HONEY = 7


class GrainUse(IntEnum):
    """When grain is used."""

    MASH = 0
    STEEP = 1
    BOIL = 2
    LATE_BOIL = 3
    PRIMARY = 4
    SECONDARY = 5


class YeastType(IntEnum):
    """Yeast type classification."""

    ALE = 0
    LAGER = 1
    WINE = 2
    CHAMPAGNE = 3
    WHEAT = 4


class YeastForm(IntEnum):
    """Yeast packaging form."""

    LIQUID = 0
    DRY = 1
    SLANT = 2
    CULTURE = 3


class Flocculation(IntEnum):
    """Yeast flocculation level."""

    LOW = 0
    MEDIUM = 1
    HIGH = 2
    VERY_HIGH = 3


class StyleType(IntEnum):
    """Beer style type."""

    ALE = 0
    LAGER = 1
    MIXED = 2
    MEAD = 3
    CIDER = 4
    WHEAT = 5  # Some BeerSmith styles use these
    OTHER = 6


class EquipmentType(IntEnum):
    """Equipment profile type."""

    UNKNOWN = 0
    EXTRACT = 1
    PARTIAL_MASH = 2
    ALL_GRAIN = 3
    BIAB = 4
    WINE_MEAD = 5
    OTHER = 6


class MiscType(IntEnum):
    """Miscellaneous ingredient type."""

    SPICE = 0
    FINING = 1
    WATER_AGENT = 2
    HERB = 3
    FLAVOR = 4
    OTHER = 5


class MiscUse(IntEnum):
    """When misc ingredient is used."""

    BOIL = 0
    MASH = 1
    PRIMARY = 2
    SECONDARY = 3
    BOTTLING = 4
    AGING = 5  # Used during aging/conditioning


# === Unit Conversion Helpers ===


def oz_to_ml(oz: float) -> float:
    """Convert fluid ounces to milliliters."""
    return oz * 29.5735


def oz_to_liters(oz: float) -> float:
    """Convert fluid ounces to liters."""
    return oz * 0.0295735


def oz_to_grams(oz: float) -> float:
    """Convert weight ounces to grams."""
    return oz * 28.3495


def oz_to_kg(oz: float) -> float:
    """Convert weight ounces to kilograms."""
    return oz * 0.0283495


def f_to_c(f: float) -> float:
    """Convert Fahrenheit to Celsius."""
    return (f - 32) * 5 / 9


def grams_to_oz(g: float) -> float:
    """Convert grams to ounces."""
    return g / 28.3495


def liters_to_oz(l: float) -> float:
    """Convert liters to fluid ounces."""
    return l / 0.0295735


def c_to_f(c: float) -> float:
    """Convert Celsius to Fahrenheit."""
    return c * 9 / 5 + 32


# === Base Models ===


class BeerSmithBase(BaseModel):
    """Base model for all BeerSmith entities."""

    id: str = Field(alias="_permid", default="0")
    modified: Optional[str] = Field(alias="_mod", default=None)

    class Config:
        populate_by_name = True
        extra = "ignore"


# === Hop Models ===


class Hop(BeerSmithBase):
    """Hop variety from the database."""

    name: str = Field(alias="f_h_name")
    origin: str = Field(alias="f_h_origin", default="")
    alpha: float = Field(alias="f_h_alpha", default=0.0)  # Alpha acid %
    beta: float = Field(alias="f_h_beta", default=0.0)  # Beta acid %
    type: HopType = Field(alias="f_h_type", default=HopType.BOTH)
    form: HopForm = Field(alias="f_h_form", default=HopForm.PELLET)
    hsi: float = Field(alias="f_h_hsi", default=25.0)  # Hop Storage Index
    inventory: float = Field(alias="f_h_inventory", default=0.0)  # Amount in stock (oz)
    price: float = Field(alias="f_h_price", default=0.0)  # Price per oz
    notes: str = Field(alias="f_h_notes", default="")

    @property
    def type_name(self) -> str:
        return ["Bittering", "Aroma", "Both"][self.type]

    @property
    def form_name(self) -> str:
        names = ["Pellet", "Plug", "Leaf", "Extract", "Cryo"]
        return names[self.form] if self.form < len(names) else "Other"


class RecipeHop(Hop):
    """Hop addition in a recipe."""

    amount_oz: float = Field(alias="f_h_amount", default=0.0)
    boil_time: float = Field(alias="f_h_boil_time", default=60.0)  # minutes
    use: HopUse = Field(alias="f_h_use", default=HopUse.BOIL)
    ibu_contribution: float = Field(alias="f_h_ibu_contrib", default=0.0)
    dry_hop_time: float = Field(alias="f_h_dry_hop_time", default=3.0)  # days

    @property
    def amount_grams(self) -> float:
        return oz_to_grams(self.amount_oz)

    @property
    def use_name(self) -> str:
        return ["Boil", "Dry Hop", "Mash", "First Wort", "Whirlpool"][self.use]


# === Grain Models ===


class Grain(BeerSmithBase):
    """Grain/fermentable from the database."""

    name: str = Field(alias="f_g_name")
    origin: str = Field(alias="f_g_origin", default="")
    supplier: str = Field(alias="f_g_supplier", default="")
    type: GrainType = Field(alias="f_g_type", default=GrainType.GRAIN)
    color: float = Field(alias="f_g_color", default=0.0)  # Lovibond
    yield_pct: float = Field(alias="f_g_yield", default=75.0)  # Extract yield %
    moisture: float = Field(alias="f_g_moisture", default=4.0)
    diastatic_power: float = Field(alias="f_g_diastatic_power", default=0.0)
    protein: float = Field(alias="f_g_protein", default=0.0)
    max_in_batch: float = Field(alias="f_g_max_in_batch", default=100.0)
    recommend_mash: bool = Field(alias="f_g_recommend_mash", default=False)
    inventory: float = Field(alias="f_g_inventory", default=0.0)  # Amount in stock (oz)
    price: float = Field(alias="f_g_price", default=0.0)  # Price per oz
    notes: str = Field(alias="f_g_notes", default="")

    @property
    def type_name(self) -> str:
        type_names = {
            0: "Grain",
            1: "Extract (Liquid)",
            2: "Sugar",
            3: "Adjunct",
            4: "Extract (Dry)",
            5: "Fruit",
            6: "Juice",
            7: "Honey",
        }
        return type_names.get(self.type, "Unknown")


class RecipeGrain(Grain):
    """Grain/fermentable in a recipe."""

    amount_oz: float = Field(alias="f_g_amount", default=0.0)
    use: GrainUse = Field(alias="f_g_use", default=GrainUse.MASH)
    percent: float = Field(alias="f_g_percent", default=0.0)
    late_extract: float = Field(alias="f_g_late_extract", default=0.0)
    add_after_boil: bool = Field(alias="f_g_add_after_boil", default=False)

    @property
    def amount_kg(self) -> float:
        return oz_to_kg(self.amount_oz)

    @property
    def amount_grams(self) -> float:
        return oz_to_grams(self.amount_oz)

    @property
    def use_name(self) -> str:
        return ["Mash", "Steep", "Boil", "Late Boil", "Primary", "Secondary"][self.use]


# === Yeast Models ===


class Yeast(BeerSmithBase):
    """Yeast strain from the database."""

    name: str = Field(alias="f_y_name")
    lab: str = Field(alias="f_y_lab", default="")
    product_id: StrOrInt = Field(alias="f_y_product_id", default="")
    type: YeastType = Field(alias="f_y_type", default=YeastType.ALE)
    form: YeastForm = Field(alias="f_y_form", default=YeastForm.LIQUID)
    flocculation: Flocculation = Field(alias="f_y_flocculation", default=Flocculation.MEDIUM)
    min_attenuation: float = Field(alias="f_y_min_attenuation", default=70.0)
    max_attenuation: float = Field(alias="f_y_max_attenuation", default=80.0)
    min_temp_f: float = Field(alias="f_y_min_temp", default=60.0)
    max_temp_f: float = Field(alias="f_y_max_temp", default=72.0)
    tolerance: float = Field(alias="f_y_tolerance", default=10.0)  # ABV %
    best_for: str = Field(alias="f_y_best_for", default="")
    notes: str = Field(alias="f_y_notes", default="")
    inventory: float = Field(alias="f_y_inventory", default=0.0)
    price: float = Field(alias="f_y_price", default=0.0)

    @property
    def type_name(self) -> str:
        return ["Ale", "Lager", "Wine", "Champagne", "Wheat"][self.type]

    @property
    def form_name(self) -> str:
        return ["Liquid", "Dry", "Slant", "Culture"][self.form]

    @property
    def flocculation_name(self) -> str:
        return ["Low", "Medium", "High", "Very High"][self.flocculation]

    @property
    def min_temp_c(self) -> float:
        return f_to_c(self.min_temp_f)

    @property
    def max_temp_c(self) -> float:
        return f_to_c(self.max_temp_f)

    @property
    def avg_attenuation(self) -> float:
        return (self.min_attenuation + self.max_attenuation) / 2


class RecipeYeast(Yeast):
    """Yeast in a recipe."""

    amount: float = Field(alias="f_y_amount", default=1.0)  # Number of packages/units
    use_starter: bool = Field(alias="f_y_use_starter", default=False)
    starter_size: float = Field(alias="f_y_starter_size", default=0.0)  # Liters
    add_to_secondary: bool = Field(alias="f_y_add_to_secondary", default=False)


# === Water Models ===


class Water(BeerSmithBase):
    """Water profile."""

    name: str = Field(alias="f_w_name")
    calcium: float = Field(alias="f_w_calcium", default=0.0)  # ppm
    magnesium: float = Field(alias="f_w_magnesium", default=0.0)  # ppm
    sodium: float = Field(alias="f_w_sodium", default=0.0)  # ppm
    sulfate: float = Field(alias="f_w_sulfate", default=0.0)  # ppm
    chloride: float = Field(alias="f_w_chloride", default=0.0)  # ppm
    bicarbonate: float = Field(alias="f_w_bicarb", default=0.0)  # ppm
    ph: float = Field(alias="f_w_ph", default=7.0)
    notes: str = Field(alias="f_w_notes", default="")

    @property
    def sulfate_chloride_ratio(self) -> float:
        """Sulfate to chloride ratio - indicates hoppy (>1) vs malty (<1) profile."""
        if self.chloride == 0:
            return 0.0
        return self.sulfate / self.chloride


class RecipeWater(Water):
    """Water in a recipe."""

    amount_oz: float = Field(alias="f_w_amount", default=0.0)

    @property
    def amount_liters(self) -> float:
        return oz_to_liters(self.amount_oz)


# === Style Models ===


class Style(BeerSmithBase):
    """Beer style (BJCP guidelines)."""

    name: str = Field(alias="f_s_name")
    category: str = Field(alias="f_s_category", default="")
    guide: str = Field(alias="f_s_guide", default="BJCP 2015")
    number: StrOrInt = Field(alias="f_s_number", default="")
    letter: StrOrInt = Field(alias="f_s_letter", default="")
    type: StyleType = Field(alias="f_s_type", default=StyleType.ALE)
    min_og: float = Field(alias="f_s_min_og", default=1.040)
    max_og: float = Field(alias="f_s_max_og", default=1.060)
    min_fg: float = Field(alias="f_s_min_fg", default=1.008)
    max_fg: float = Field(alias="f_s_max_fg", default=1.016)
    min_ibu: float = Field(alias="f_s_min_ibu", default=20.0)
    max_ibu: float = Field(alias="f_s_max_ibu", default=40.0)
    min_color: float = Field(alias="f_s_min_color", default=4.0)  # SRM
    max_color: float = Field(alias="f_s_max_color", default=14.0)  # SRM
    min_abv: float = Field(alias="f_s_min_abv", default=4.0)
    max_abv: float = Field(alias="f_s_max_abv", default=6.0)
    min_carb: float = Field(alias="f_s_min_carb", default=2.0)
    max_carb: float = Field(alias="f_s_max_carb", default=3.0)
    description: str = Field(alias="f_s_description", default="")
    profile: str = Field(alias="f_s_profile", default="")
    ingredients: str = Field(alias="f_s_ingredients", default="")
    examples: str = Field(alias="f_s_examples", default="")

    @property
    def style_code(self) -> str:
        """Full BJCP style code like '5B' or '21A'."""
        return f"{self.number}{self.letter}"

    @property
    def type_name(self) -> str:
        names = ["Ale", "Lager", "Mixed", "Mead", "Cider", "Wheat", "Other"]
        return names[self.type] if self.type < len(names) else "Other"


# === Misc Models ===


class Misc(BeerSmithBase):
    """Miscellaneous ingredient from the database."""

    name: str = Field(alias="f_m_name")
    type: MiscType = Field(alias="f_m_type", default=MiscType.OTHER)
    use_for: str = Field(alias="f_m_use_for", default="")
    notes: str = Field(alias="f_m_notes", default="")
    inventory: float = Field(alias="f_m_inventory", default=0.0)
    price: float = Field(alias="f_m_price", default=0.0)

    @property
    def type_name(self) -> str:
        return ["Spice", "Fining", "Water Agent", "Herb", "Flavor", "Other"][self.type]


class RecipeMisc(Misc):
    """Misc ingredient in a recipe."""

    amount: float = Field(alias="f_m_amount", default=0.0)
    units: int = Field(alias="f_m_units", default=1)  # Unit type
    use: MiscUse = Field(alias="f_m_use", default=MiscUse.BOIL)
    time: float = Field(alias="f_m_time", default=0.0)
    time_units: int = Field(alias="f_m_time_units", default=0)

    @property
    def use_name(self) -> str:
        return ["Boil", "Mash", "Primary", "Secondary", "Bottling", "Aging"][self.use]


# === Equipment Models ===


class Equipment(BeerSmithBase):
    """Equipment profile."""

    name: str = Field(alias="f_e_name")
    type: EquipmentType = Field(alias="f_e_type", default=EquipmentType.ALL_GRAIN)
    batch_vol_oz: float = Field(alias="f_e_batch_vol", default=640.0)  # ~5 gal
    boil_vol_oz: float = Field(alias="f_e_boil_vol", default=768.0)
    boil_time: float = Field(alias="f_e_boil_time", default=60.0)  # minutes
    boil_off_oz: float = Field(alias="f_e_boil_off", default=64.0)  # per hour
    efficiency: float = Field(alias="f_e_efficiency", default=72.0)  # %
    hop_utilization: float = Field(alias="f_e_hop_util", default=100.0)  # %
    trub_loss_oz: float = Field(alias="f_e_trub_loss", default=96.0)
    fermenter_loss_oz: float = Field(alias="f_e_fermenter_loss", default=51.2)
    mash_vol_oz: float = Field(alias="f_e_mash_vol", default=640.0)
    tun_mass: float = Field(alias="f_e_tun_mass", default=64.0)  # Tun weight in oz
    tun_specific_heat: float = Field(alias="f_e_tun_specific_heat", default=0.12)
    tun_deadspace: float = Field(alias="f_e_tun_deadspace", default=0.0)  # Lauter deadspace
    notes: str = Field(alias="f_e_notes", default="")

    @property
    def type_name(self) -> str:
        type_names = {
            1: "Extract",
            2: "Partial Mash",
            3: "All Grain",
            4: "BIAB",
            5: "Wine/Mead",
            6: "Other",
        }
        return type_names.get(self.type, "Unknown")

    @property
    def batch_size_liters(self) -> float:
        return oz_to_liters(self.batch_vol_oz)

    @property
    def batch_size_gallons(self) -> float:
        return self.batch_vol_oz / 128.0

    @property
    def boil_size_liters(self) -> float:
        return oz_to_liters(self.boil_vol_oz)


# === Mash Models ===


class MashStep(BeerSmithBase):
    """Single step in a mash profile."""

    name: str = Field(alias="f_ms_name")
    type: int = Field(alias="f_ms_type", default=0)  # 0=Infusion, 1=Decoction, 2=Temperature
    step_temp_f: float = Field(alias="f_ms_step_temp", default=152.0)
    step_time: float = Field(alias="f_ms_step_time", default=60.0)  # minutes
    rise_time: float = Field(alias="f_ms_rise_time", default=2.0)  # minutes
    infusion_amount_oz: float = Field(alias="f_ms_infusion", default=0.0)
    infusion_temp_f: float = Field(alias="f_ms_infusion_temp", default=168.0)

    @property
    def step_temp_c(self) -> float:
        return f_to_c(self.step_temp_f)

    @property
    def infusion_temp_c(self) -> float:
        return f_to_c(self.infusion_temp_f)

    @property
    def type_name(self) -> str:
        names = ["Infusion", "Decoction", "Temperature", "FlySparge", "BatchSparge"]
        return names[self.type] if self.type < len(names) else "Other"


class MashProfile(BeerSmithBase):
    """Mash profile with steps."""

    name: str = Field(alias="f_mh_name")
    grain_temp_f: float = Field(alias="f_mh_grain_temp", default=72.0)
    sparge_temp_f: float = Field(alias="f_mh_sparge_temp", default=168.0)
    ph: float = Field(alias="f_mh_ph", default=5.4)
    notes: str = Field(alias="f_mh_notes", default="")
    steps: list[MashStep] = Field(default_factory=list)

    @field_validator("steps", mode="before")
    @classmethod
    def wrap_single_step(cls, v):
        """Wrap a single step dict in a list."""
        if isinstance(v, dict):
            return [v]
        return v if v else []

    @property
    def grain_temp_c(self) -> float:
        return f_to_c(self.grain_temp_f)

    @property
    def sparge_temp_c(self) -> float:
        return f_to_c(self.sparge_temp_f)


# === Carbonation and Age Profiles ===


class Carbonation(BaseModel):
    """Carbonation profile."""

    id: str | int = Field(alias="_permid_", default="0")
    name: str = Field(alias="f_c_name", default="Carbonation")
    type: int = Field(alias="f_c_type", default=1)  # 0=bottle, 1=keg, 2=both
    temperature: float = Field(alias="f_c_temperature", default=45.0)
    primer_name: str = Field(alias="f_c_primer_name", default="Forced Carbonation")
    carb_rate: float = Field(alias="f_c_carb_rate", default=100.0)
    notes: str = Field(alias="f_c_notes", default="")

    class Config:
        populate_by_name = True
        extra = "ignore"


class AgeProfile(BaseModel):
    """Fermentation/aging profile."""

    id: str | int = Field(alias="_permid_", default="0")
    name: str = Field(alias="f_a_name", default="Fermentation")
    type: int = Field(alias="f_a_type", default=0)  # 0=ale, 1=lager, 2=mead/wine, 3=cider
    prim_temp: float = Field(alias="f_a_prim_temp", default=68.0)
    prim_end_temp: float = Field(alias="f_a_prim_end_temp", default=68.0)
    sec_temp: float = Field(alias="f_a_sec_temp", default=68.0)
    sec_end_temp: float = Field(alias="f_a_sec_end_temp", default=68.0)
    tert_temp: float = Field(alias="f_a_tert_temp", default=68.0)
    tert_end_temp: float = Field(alias="f_a_tert_end_temp", default=68.0)
    age_temp: float = Field(alias="f_a_age_temp", default=68.0)
    end_age_temp: float = Field(alias="f_a_end_age_temp", default=68.0)
    bulk_temp: float = Field(alias="f_a_bulk_temp", default=68.0)
    bulk_end_temp: float = Field(alias="f_a_bulk_end_temp", default=68.0)
    prim_days: float = Field(alias="f_a_prim_days", default=7.0)
    sec_days: float = Field(alias="f_a_sec_days", default=7.0)
    tert_days: float = Field(alias="f_a_tert_days", default=7.0)
    bulk_days: float = Field(alias="f_a_bulk_days", default=14.0)
    age_days: float = Field(alias="f_a_age", default=30.0)

    class Config:
        populate_by_name = True
        extra = "ignore"


# === Recipe Models ===


class Recipe(BeerSmithBase):
    """Complete recipe with all details."""

    name: str = Field(alias="f_r_name")
    brewer: str = Field(alias="f_r_brewer", default="")
    asst_brewer: str = Field(alias="f_r_asst_brewer", default="")
    recipe_date: Optional[str] = Field(alias="f_r_date", default=None)
    folder: str = Field(alias="f_r_folder_name", default="/")

    # Calculated values (stored by BeerSmith)
    og: float = Field(alias="f_r_og", default=1.050)
    fg: float = Field(alias="f_r_fg", default=1.010)
    ibu: float = Field(alias="f_r_ibu", default=30.0)
    color_srm: float = Field(alias="f_r_color", default=8.0)
    abv: float = Field(alias="f_r_abv", default=5.0)

    # Process
    boil_time: float = Field(alias="f_r_boil_time", default=60.0)
    notes: str = Field(alias="f_r_notes", default="")

    # Embedded objects
    style: Optional[Style] = None
    equipment: Optional[Equipment] = None
    mash: Optional[MashProfile] = None
    carbonation: Optional[Carbonation] = None
    age: Optional[AgeProfile] = None

    # Ingredients (populated from Ingredients section)
    grains: list[RecipeGrain] = Field(default_factory=list)
    hops: list[RecipeHop] = Field(default_factory=list)
    yeasts: list[RecipeYeast] = Field(default_factory=list)
    miscs: list[RecipeMisc] = Field(default_factory=list)
    waters: list[RecipeWater] = Field(default_factory=list)

    @property
    def batch_size_liters(self) -> float:
        if self.equipment:
            return self.equipment.batch_size_liters
        return 19.0  # Default 5 gal

    @property
    def efficiency(self) -> float:
        if self.equipment:
            return self.equipment.efficiency
        return 72.0


# === Summary Models for listing ===


class RecipeSummary(BaseModel):
    """Lightweight recipe info for listings."""

    id: str
    name: str
    style: str = ""
    og: float = 1.050
    fg: float = 1.010
    ibu: float = 30.0
    abv: float = 5.0
    color_srm: float = 8.0
    folder: str = "/"

    class Config:
        extra = "ignore"


class IngredientMatch(BaseModel):
    """Result of fuzzy ingredient matching."""

    query: str
    matched_name: str
    matched_type: str  # 'hop', 'grain', 'yeast', 'misc'
    confidence: float  # 0.0 to 1.0
    beersmith_id: str

    class Config:
        extra = "ignore"


class RecipeSuggestion(BaseModel):
    """Recipe suggestion based on available ingredients."""

    recipe_id: str
    recipe_name: str
    style: str
    match_percentage: float
    available_ingredients: list[str]
    missing_ingredients: list[str]
    substitution_suggestions: dict[str, list[str]] = Field(default_factory=dict)

    class Config:
        extra = "ignore"
