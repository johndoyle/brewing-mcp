"""BeerSmith 4 domain models mapped directly from SQLite schema and embedded JSON."""

from __future__ import annotations

import json
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from mcp_beersmith4.enums import (
    SCHEMA_GRAIN,
    SCHEMA_HOP,
    SCHEMA_MISC,
    SCHEMA_WATER,
    SCHEMA_YEAST,
    CarbType,
    EquipmentType,
    GrainType,
    GrainUse,
    HopForm,
    HopType,
    HopUse,
    MashStepType,
    MiscType,
    MiscUse,
    RecipeType,
    StyleType,
    YeastFlocculation,
    YeastForm,
    YeastType,
)


class BS4Base(BaseModel):
    """Common fields for all BeerSmith 4 records."""

    model_config = ConfigDict(populate_by_name=True)

    permid: int = Field(alias="_PERMID_", default=0)
    mod: str = Field(alias="_MOD_", default="")
    cloud_id: int = Field(alias="_CLOUDID_", default=0)
    cloud_state: int = Field(alias="_CLOUD_STATE_", default=0)


# ── Grain / Fermentable ──────────────────────────────────────────────


class BS4Grain(BS4Base):
    """Grain/fermentable from library (M_GRAIN) or recipe JSON."""

    name: str = Field(alias="F_G_NAME", default="")
    origin: str = Field(alias="F_G_ORIGIN", default="")
    supplier: str = Field(alias="F_G_SUPPLIER", default="")
    type: int = Field(alias="F_G_TYPE", default=0)
    use: int = Field(alias="F_G_USE", default=0)
    amount: float = Field(alias="F_G_AMOUNT", default=0.0)
    color: float = Field(alias="F_G_COLOR", default=0.0)
    yield_pct: float = Field(alias="F_G_YIELD", default=0.0)
    percent: float = Field(alias="F_G_PERCENT", default=0.0)
    not_fermentable: int = Field(alias="F_G_NOT_FERMENTABLE", default=0)
    inventory: float = Field(alias="F_G_INVENTORY", default=0.0)
    coarse_fine_diff: float = Field(alias="F_G_COARSE_FINE_DIFF", default=0.0)
    moisture: float = Field(alias="F_G_MOISTURE", default=0.0)
    diastatic_power: float = Field(alias="F_G_DIASTATIC_POWER", default=0.0)
    protein: float = Field(alias="F_G_PROTEIN", default=0.0)
    ibu_gal_per_lb: float = Field(alias="F_G_IBU_GAL_PER_LB", default=0.0)
    add_after_boil: int = Field(alias="F_G_ADD_AFTER_BOIL", default=0)
    recommend_mash: int = Field(alias="F_G_RECOMMEND_MASH", default=0)
    max_in_batch: float = Field(alias="F_G_MAX_IN_BATCH", default=0.0)
    boil_time: float = Field(alias="F_G_BOIL_TIME", default=0.0)
    price: float = Field(alias="F_G_PRICE", default=0.0)
    notes: str = Field(alias="F_G_NOTES", default="")
    in_recipe: int = Field(alias="F_G_IN_RECIPE", default=0)
    order: int = Field(alias="F_ORDER", default=0)

    @property
    def grain_type(self) -> GrainType:
        try:
            return GrainType(self.type)
        except ValueError:
            return GrainType.GRAIN

    @property
    def grain_use(self) -> GrainUse:
        try:
            return GrainUse(self.use)
        except ValueError:
            return GrainUse.MASH

    @property
    def amount_oz(self) -> float:
        """Amount in ounces (BeerSmith internal unit)."""
        return self.amount

    @property
    def amount_g(self) -> float:
        """Amount converted to grams."""
        return self.amount * 28.3495231


# ── Hops ──────────────────────────────────────────────────────────────


class BS4Hop(BS4Base):
    """Hop from library (M_HOPS) or recipe JSON."""

    name: str = Field(alias="F_H_NAME", default="")
    origin: str = Field(alias="F_H_ORIGIN", default="")
    type: int = Field(alias="F_H_TYPE", default=0)
    form: int = Field(alias="F_H_FORM", default=0)
    alpha: float = Field(alias="F_H_ALPHA", default=0.0)
    beta: float = Field(alias="F_H_BETA", default=0.0)
    percent: float = Field(alias="F_H_PERCENT", default=0.0)
    amount: float = Field(alias="F_H_AMOUNT", default=0.0)
    inventory: float = Field(alias="F_H_INVENTORY", default=0.0)
    hsi: float = Field(alias="F_H_HSI", default=0.0)
    boil_time: float = Field(alias="F_H_BOIL_TIME", default=0.0)
    dry_hop_time: float = Field(alias="F_H_DRY_HOP_TIME", default=0.0)
    whirlpool_temp: float = Field(alias="F_H_WHIRLPOOL_TEMP", default=0.0)
    ibu_contrib: float = Field(alias="F_H_IBU_CONTRIB", default=0.0)
    price: float = Field(alias="F_H_PRICE", default=0.0)
    notes: str = Field(alias="F_H_NOTES", default="")
    use: int = Field(alias="F_H_USE", default=0)
    in_recipe: int = Field(alias="F_H_IN_RECIPE", default=0)
    order: int = Field(alias="F_ORDER", default=0)

    @property
    def hop_use(self) -> HopUse:
        try:
            return HopUse(self.use)
        except ValueError:
            return HopUse.BOIL

    @property
    def hop_type(self) -> HopType:
        try:
            return HopType(self.type)
        except ValueError:
            return HopType.BOTH

    @property
    def hop_form(self) -> HopForm:
        try:
            return HopForm(self.form)
        except ValueError:
            return HopForm.PELLET

    @property
    def amount_oz(self) -> float:
        return self.amount

    @property
    def amount_g(self) -> float:
        return self.amount * 28.3495231


# ── Yeast ─────────────────────────────────────────────────────────────


class BS4Yeast(BS4Base):
    """Yeast from library (M_YEAST) or recipe JSON."""

    name: str = Field(alias="F_Y_NAME", default="")
    lab: str = Field(alias="F_Y_LAB", default="")
    product_id: str = Field(alias="F_Y_PRODUCT_ID", default="")
    type: int = Field(alias="F_Y_TYPE", default=0)
    form: int = Field(alias="F_Y_FORM", default=0)
    flocculation: int = Field(alias="F_Y_FLOCCULATION", default=0)
    amount: float = Field(alias="F_Y_AMOUNT", default=0.0)
    inventory: float = Field(alias="F_Y_INVENTORY", default=0.0)
    tolerance: float = Field(alias="F_Y_TOLERANCE", default=0.0)
    price: float = Field(alias="F_Y_PRICE", default=0.0)
    min_attenuation: float = Field(alias="F_Y_MIN_ATTENUATION", default=0.0)
    max_attenuation: float = Field(alias="F_Y_MAX_ATTENUATION", default=0.0)
    min_temp: float = Field(alias="F_Y_MIN_TEMP", default=0.0)
    max_temp: float = Field(alias="F_Y_MAX_TEMP", default=0.0)
    best_for: str = Field(alias="F_Y_BEST_FOR", default="")
    notes: str = Field(alias="F_Y_NOTES", default="")
    in_recipe: int = Field(alias="F_Y_IN_RECIPE", default=0)
    order: int = Field(alias="F_ORDER", default=0)

    @property
    def yeast_type(self) -> YeastType:
        try:
            return YeastType(self.type)
        except ValueError:
            return YeastType.ALE

    @property
    def yeast_form(self) -> YeastForm:
        try:
            return YeastForm(self.form)
        except ValueError:
            return YeastForm.DRY

    @property
    def avg_attenuation(self) -> float:
        if self.min_attenuation and self.max_attenuation:
            return (self.min_attenuation + self.max_attenuation) / 2.0
        return self.max_attenuation or self.min_attenuation


# ── Misc ──────────────────────────────────────────────────────────────


class BS4Misc(BS4Base):
    """Miscellaneous ingredient from library (M_MISC) or recipe JSON."""

    name: str = Field(alias="F_M_NAME", default="")
    type: int = Field(alias="F_M_TYPE", default=0)
    use_for: str = Field(alias="F_M_USE_FOR", default="")
    amount: float = Field(alias="F_M_AMOUNT", default=0.0)
    volume: float = Field(alias="F_M_VOLUME", default=0.0)
    inventory: float = Field(alias="F_M_INVENTORY", default=0.0)
    price: float = Field(alias="F_M_PRICE", default=0.0)
    use: int = Field(alias="F_M_USE", default=0)
    time: float = Field(alias="F_M_TIME", default=0.0)
    notes: str = Field(alias="F_M_NOTES", default="")
    order: int = Field(alias="F_ORDER", default=0)

    @property
    def misc_type(self) -> MiscType:
        try:
            return MiscType(self.type)
        except ValueError:
            return MiscType.OTHER

    @property
    def misc_use(self) -> MiscUse:
        try:
            return MiscUse(self.use)
        except ValueError:
            return MiscUse.BOIL


# ── Water ─────────────────────────────────────────────────────────────


class BS4Water(BS4Base):
    """Water profile from library (M_WATER) or recipe JSON."""

    name: str = Field(alias="F_W_NAME", default="")
    amount: float = Field(alias="F_W_AMOUNT", default=0.0)
    ph: float = Field(alias="F_W_PH", default=0.0)
    calcium: float = Field(alias="F_W_CALCIUM", default=0.0)
    magnesium: float = Field(alias="F_W_MAGNESIUM", default=0.0)
    sodium: float = Field(alias="F_W_SODIUM", default=0.0)
    sulfate: float = Field(alias="F_W_SULFATE", default=0.0)
    chloride: float = Field(alias="F_W_CHLORIDE", default=0.0)
    bicarb: float = Field(alias="F_W_BICARB", default=0.0)
    notes: str = Field(alias="F_W_NOTES", default="")
    in_recipe: int = Field(alias="F_W_IN_RECIPE", default=0)


# ── Mash ──────────────────────────────────────────────────────────────


class BS4MashStep(BaseModel):
    """A single mash step within a mash profile."""

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(alias="F_MS_NAME", default="")
    type: int = Field(alias="F_MS_TYPE", default=0)
    infusion: float = Field(alias="F_MS_INFUSION", default=0.0)
    step_temp: float = Field(alias="F_MS_STEP_TEMP", default=0.0)
    step_time: float = Field(alias="F_MS_STEP_TIME", default=0.0)
    rise_time: float = Field(alias="F_MS_RISE_TIME", default=0.0)
    infusion_temp: float = Field(alias="F_MS_INFUSION_TEMP", default=0.0)
    decoction_amt: float = Field(alias="F_MS_DECOCTION_AMT", default=0.0)
    grain_temp: float = Field(alias="F_MS_GRAIN_TEMP", default=0.0)

    @property
    def step_type(self) -> MashStepType:
        try:
            return MashStepType(self.type)
        except ValueError:
            return MashStepType.INFUSION


class BS4Mash(BS4Base):
    """Mash profile from library (M_MASH) or recipe JSON."""

    name: str = Field(alias="F_MH_NAME", default="")
    grain_weight: float = Field(alias="F_MH_GRAIN_WEIGHT", default=0.0)
    grain_temp: float = Field(alias="F_MH_GRAIN_TEMP", default=0.0)
    boil_temp: float = Field(alias="F_MH_BOIL_TEMP", default=0.0)
    tun_temp: float = Field(alias="F_MH_TUN_TEMP", default=0.0)
    ph: float = Field(alias="F_MH_PH", default=0.0)
    sparge_temp: float = Field(alias="F_MH_SPARGE_TEMP", default=0.0)
    biab: int = Field(alias="F_MH_BIAB", default=0)
    notes: str = Field(alias="F_MH_NOTES", default="")
    steps_raw: str = Field(alias="steps", default="")
    equip_adjust: int = Field(alias="F_MH_EQUIP_ADJUST", default=0)

    @field_validator("steps_raw", mode="before")
    @classmethod
    def coerce_steps_raw(cls, v: object) -> str:
        if isinstance(v, list):
            return json.dumps(v)
        if v is None:
            return ""
        return str(v)

    @property
    def steps(self) -> list[BS4MashStep]:
        if not self.steps_raw:
            return []
        try:
            raw = json.loads(self.steps_raw)
            return [BS4MashStep.model_validate(s) for s in raw]
        except (json.JSONDecodeError, TypeError):
            return []


# ── Equipment ─────────────────────────────────────────────────────────


class BS4Equipment(BS4Base):
    """Equipment profile from library (M_EQUIPMENT) or recipe JSON."""

    name: str = Field(alias="F_E_NAME", default="")
    type: int = Field(alias="F_E_TYPE", default=0)
    boil_vol: float = Field(alias="F_E_BOIL_VOL", default=0.0)
    boil_time: float = Field(alias="F_E_BOIL_TIME", default=0.0)
    boil_off: float = Field(alias="F_E_BOIL_OFF", default=0.0)
    trub_loss: float = Field(alias="F_E_TRUB_LOSS", default=0.0)
    cool_pct: float = Field(alias="F_E_COOL_PCT", default=0.0)
    batch_vol: float = Field(alias="F_E_BATCH_VOL", default=0.0)
    fermenter_loss: float = Field(alias="F_E_FERMENTER_LOSS", default=0.0)
    top_up: float = Field(alias="F_E_TOP_UP", default=0.0)
    efficiency: float = Field(alias="F_E_EFFICIENCY", default=0.0)
    hop_util: float = Field(alias="F_E_HOP_UTIL", default=0.0)
    tun_deadspace: float = Field(alias="F_E_TUN_DEADSPACE", default=0.0)
    notes: str = Field(alias="F_E_NOTES", default="")

    @property
    def equip_type(self) -> EquipmentType:
        try:
            return EquipmentType(self.type)
        except ValueError:
            return EquipmentType.ALL_GRAIN

    @property
    def batch_vol_l(self) -> float:
        """Batch volume in litres (stored as fl oz)."""
        return self.batch_vol * 0.0295735296


# ── Style ─────────────────────────────────────────────────────────────


class BS4Style(BS4Base):
    """Beer style from library (M_STYLE) or recipe JSON."""

    name: str = Field(alias="F_S_NAME", default="")
    category: str = Field(alias="F_S_CATEGORY", default="")
    guide: str = Field(alias="F_S_GUIDE", default="")
    number: str = Field(alias="F_S_NUMBER", default="")
    type: int = Field(alias="F_S_TYPE", default=0)
    min_og: float = Field(alias="F_S_MIN_OG", default=0.0)
    max_og: float = Field(alias="F_S_MAX_OG", default=0.0)
    min_fg: float = Field(alias="F_S_MIN_FG", default=0.0)
    max_fg: float = Field(alias="F_S_MAX_FG", default=0.0)
    min_ibu: float = Field(alias="F_S_MIN_IBU", default=0.0)
    max_ibu: float = Field(alias="F_S_MAX_IBU", default=0.0)
    min_color: float = Field(alias="F_S_MIN_COLOR", default=0.0)
    max_color: float = Field(alias="F_S_MAX_COLOR", default=0.0)
    min_abv: float = Field(alias="F_S_MIN_ABV", default=0.0)
    max_abv: float = Field(alias="F_S_MAX_ABV", default=0.0)
    description: str = Field(alias="F_S_DESCRIPTION", default="")
    profile: str = Field(alias="F_S_PROFILE", default="")
    ingredients: str = Field(alias="F_S_INGREDIENTS", default="")
    examples: str = Field(alias="F_S_EXAMPLES", default="")

    @property
    def style_type(self) -> StyleType:
        try:
            return StyleType(self.type)
        except ValueError:
            return StyleType.ALE


# ── Carbonation ───────────────────────────────────────────────────────


class BS4Carb(BS4Base):
    """Carbonation profile from library (M_CARB) or recipe JSON."""

    name: str = Field(alias="F_C_NAME", default="")
    temperature: float = Field(alias="F_C_TEMPERATURE", default=0.0)
    type: int = Field(alias="F_C_TYPE", default=0)
    primer_name: str = Field(alias="F_C_PRIMER_NAME", default="")
    carb_rate: float = Field(alias="F_C_CARB_RATE", default=0.0)
    notes: str = Field(alias="F_C_NOTES", default="")


# ── Age / Fermentation ───────────────────────────────────────────────


class BS4Age(BS4Base):
    """Age/fermentation profile from library (M_AGE) or recipe JSON."""

    name: str = Field(alias="F_A_NAME", default="")
    prim_temp: float = Field(alias="F_A_PRIM_TEMP", default=0.0)
    sec_temp: float = Field(alias="F_A_SEC_TEMP", default=0.0)
    tert_temp: float = Field(alias="F_A_TERT_TEMP", default=0.0)
    age_temp: float = Field(alias="F_A_AGE_TEMP", default=0.0)
    prim_days: float = Field(alias="F_A_PRIM_DAYS", default=0.0)
    sec_days: float = Field(alias="F_A_SEC_DAYS", default=0.0)
    tert_days: float = Field(alias="F_A_TERT_DAYS", default=0.0)
    age: float = Field(alias="F_A_AGE", default=0.0)
    type: int = Field(alias="F_A_TYPE", default=0)
    notes: str = Field(alias="F_A_NOTES", default="")


# ── Folder ────────────────────────────────────────────────────────────


class BS4Folder(BaseModel):
    """Folder from M_FOLDER or M_CLOUD_FOLDER."""

    model_config = ConfigDict(populate_by_name=True)

    permid: int = Field(alias="_PERMID_", default=0)
    name: str = Field(alias="F_F_NAME", default="")
    parent: int = Field(alias="F_F_PARENT", default=0)


# ── Recipe ────────────────────────────────────────────────────────────


class BS4Recipe(BS4Base):
    """Full recipe from M_RECIPE — top-level fields only (no embedded parsing)."""

    name: str = Field(alias="F_R_NAME", default="")
    brewer: str = Field(alias="F_R_BREWER", default="")
    date: int = Field(alias="F_R_DATE", default=0)
    folder_name: str = Field(alias="F_R_FOLDER_NAME", default="")
    parent: int = Field(alias="F_R_PARENT", default=0)
    type: int = Field(alias="F_R_TYPE", default=0)
    notes: str = Field(alias="F_R_NOTES", default="")
    description: str = Field(alias="F_R_DESCRIPTION", default="")
    rating: float = Field(alias="F_R_RATING", default=0.0)
    boil_time: float | None = Field(default=None)
    locked: int = Field(alias="F_R_LOCKED", default=0)
    version: float = Field(alias="F_R_VERSION", default=0.0)

    # Measured values
    og_measured: float = Field(alias="F_R_OG_MEASURED", default=0.0)
    fg_measured: float = Field(alias="F_R_FG_MEASURED", default=0.0)
    og_measured_set: int = Field(alias="F_R_OG_MEASURED_SET", default=0)
    fg_measured_set: int = Field(alias="F_R_FG_MEASURED_SET", default=0)

    # Carbonation target
    carb_vols: float = Field(alias="F_R_CARB_VOLS", default=0.0)
    mash_ph: float = Field(alias="F_R_MASH_PH", default=0.0)

    # Raw embedded JSON strings (parsed by repository)
    equipment_raw: str = Field(alias="F_R_EQUIPMENT", default="")
    style_raw: str = Field(alias="F_R_STYLE", default="")
    mash_raw: str = Field(alias="F_R_MASH", default="")
    carb_raw: str = Field(alias="F_R_CARB", default="")
    age_raw: str = Field(alias="F_R_AGE", default="")
    ingredients_raw: str = Field(alias="Ingredients", default="")
    age_data_raw: str = Field(alias="AgeData", default="")

    @property
    def recipe_type(self) -> RecipeType:
        try:
            return RecipeType(self.type)
        except ValueError:
            return RecipeType.ALL_GRAIN

    @property
    def brew_date(self) -> datetime | None:
        if self.date and self.date > 0:
            return datetime.fromtimestamp(self.date)
        return None


# ── Parsed Recipe (with all embedded objects resolved) ────────────────


class BS4RecipeFull(BaseModel):
    """Recipe with all embedded JSON parsed into typed models."""

    model_config = ConfigDict(populate_by_name=True)

    recipe: BS4Recipe
    equipment: BS4Equipment | None = None
    style: BS4Style | None = None
    mash: BS4Mash | None = None
    carb: BS4Carb | None = None
    age: BS4Age | None = None
    grains: list[BS4Grain] = Field(default_factory=list)
    hops: list[BS4Hop] = Field(default_factory=list)
    yeasts: list[BS4Yeast] = Field(default_factory=list)
    miscs: list[BS4Misc] = Field(default_factory=list)
    waters: list[BS4Water] = Field(default_factory=list)
