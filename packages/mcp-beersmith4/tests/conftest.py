"""Shared test fixtures for mcp-beersmith4."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

import pytest

from mcp_beersmith4.config import BeerSmith4Config
from mcp_beersmith4.database import DatabaseManager


@pytest.fixture()
def tmp_bs4_dir(tmp_path: Path) -> Path:
    """Create a temporary BeerSmith 4 data directory with SQLite databases."""
    data_dir = tmp_path / "BeerSmith4"
    data_dir.mkdir()
    _create_main_db(data_dir / "BeerSmith.sqlite")
    _create_opts_db(data_dir / "Opts.sqlite")
    return data_dir


@pytest.fixture()
def config(tmp_bs4_dir: Path) -> BeerSmith4Config:
    return BeerSmith4Config(data_path=tmp_bs4_dir, read_only=False)


@pytest.fixture()
def ro_config(tmp_bs4_dir: Path) -> BeerSmith4Config:
    return BeerSmith4Config(data_path=tmp_bs4_dir, read_only=True)


@pytest.fixture()
def db(config: BeerSmith4Config) -> DatabaseManager:
    return DatabaseManager(config)


def _create_main_db(path: Path) -> None:
    """Create a minimal BeerSmith.sqlite with schema and seed data."""
    conn = sqlite3.connect(str(path))

    conn.executescript("""
        CREATE TABLE M_RECIPE (
            _PERMID_ INTEGER PRIMARY KEY,
            _MOD_ TEXT DEFAULT '',
            _CLOUDID_ INTEGER DEFAULT 0,
            _CLOUD_STATE_ INTEGER DEFAULT 0,
            F_R_NAME TEXT DEFAULT '',
            F_R_BREWER TEXT DEFAULT '',
            F_R_DATE INTEGER DEFAULT 0,
            F_R_FOLDER_NAME TEXT DEFAULT '',
            F_R_PARENT INTEGER DEFAULT 0,
            F_R_TYPE INTEGER DEFAULT 0,
            F_R_NOTES TEXT DEFAULT '',
            F_R_DESCRIPTION TEXT DEFAULT '',
            F_R_RATING REAL DEFAULT 0,
            F_R_LOCKED INTEGER DEFAULT 0,
            F_R_VERSION REAL DEFAULT 0,
            F_R_OG_MEASURED REAL DEFAULT 0,
            F_R_FG_MEASURED REAL DEFAULT 0,
            F_R_OG_MEASURED_SET INTEGER DEFAULT 0,
            F_R_FG_MEASURED_SET INTEGER DEFAULT 0,
            F_R_CARB_VOLS REAL DEFAULT 0,
            F_R_MASH_PH REAL DEFAULT 0,
            F_R_EQUIPMENT TEXT DEFAULT '',
            F_R_STYLE TEXT DEFAULT '',
            F_R_MASH TEXT DEFAULT '',
            F_R_CARB TEXT DEFAULT '',
            F_R_AGE TEXT DEFAULT '',
            Ingredients TEXT DEFAULT '',
            AgeData TEXT DEFAULT ''
        );

        CREATE TABLE M_GRAIN (
            _PERMID_ INTEGER PRIMARY KEY,
            _MOD_ TEXT DEFAULT '',
            _CLOUDID_ INTEGER DEFAULT 0,
            _CLOUD_STATE_ INTEGER DEFAULT 0,
            F_G_NAME TEXT DEFAULT '',
            F_G_ORIGIN TEXT DEFAULT '',
            F_G_SUPPLIER TEXT DEFAULT '',
            F_G_TYPE INTEGER DEFAULT 0,
            F_G_USE INTEGER DEFAULT 0,
            F_G_AMOUNT REAL DEFAULT 0,
            F_G_COLOR REAL DEFAULT 0,
            F_G_YIELD REAL DEFAULT 0,
            F_G_PERCENT REAL DEFAULT 0,
            F_G_NOT_FERMENTABLE INTEGER DEFAULT 0,
            F_G_INVENTORY REAL DEFAULT 0,
            F_G_COARSE_FINE_DIFF REAL DEFAULT 0,
            F_G_MOISTURE REAL DEFAULT 0,
            F_G_DIASTATIC_POWER REAL DEFAULT 0,
            F_G_PROTEIN REAL DEFAULT 0,
            F_G_IBU_GAL_PER_LB REAL DEFAULT 0,
            F_G_ADD_AFTER_BOIL INTEGER DEFAULT 0,
            F_G_RECOMMEND_MASH INTEGER DEFAULT 0,
            F_G_MAX_IN_BATCH REAL DEFAULT 0,
            F_G_BOIL_TIME REAL DEFAULT 0,
            F_G_PRICE REAL DEFAULT 0,
            F_G_NOTES TEXT DEFAULT '',
            F_G_IN_RECIPE INTEGER DEFAULT 0,
            F_ORDER INTEGER DEFAULT 0
        );

        CREATE TABLE M_HOPS (
            _PERMID_ INTEGER PRIMARY KEY,
            _MOD_ TEXT DEFAULT '',
            _CLOUDID_ INTEGER DEFAULT 0,
            _CLOUD_STATE_ INTEGER DEFAULT 0,
            F_H_NAME TEXT DEFAULT '',
            F_H_ORIGIN TEXT DEFAULT '',
            F_H_TYPE INTEGER DEFAULT 0,
            F_H_FORM INTEGER DEFAULT 0,
            F_H_ALPHA REAL DEFAULT 0,
            F_H_BETA REAL DEFAULT 0,
            F_H_PERCENT REAL DEFAULT 0,
            F_H_AMOUNT REAL DEFAULT 0,
            F_H_INVENTORY REAL DEFAULT 0,
            F_H_HSI REAL DEFAULT 0,
            F_H_BOIL_TIME REAL DEFAULT 0,
            F_H_DRY_HOP_TIME REAL DEFAULT 0,
            F_H_WHIRLPOOL_TEMP REAL DEFAULT 0,
            F_H_IBU_CONTRIB REAL DEFAULT 0,
            F_H_PRICE REAL DEFAULT 0,
            F_H_NOTES TEXT DEFAULT '',
            F_H_USE INTEGER DEFAULT 0,
            F_H_IN_RECIPE INTEGER DEFAULT 0,
            F_ORDER INTEGER DEFAULT 0
        );

        CREATE TABLE M_YEAST (
            _PERMID_ INTEGER PRIMARY KEY,
            _MOD_ TEXT DEFAULT '',
            _CLOUDID_ INTEGER DEFAULT 0,
            _CLOUD_STATE_ INTEGER DEFAULT 0,
            F_Y_NAME TEXT DEFAULT '',
            F_Y_LAB TEXT DEFAULT '',
            F_Y_PRODUCT_ID TEXT DEFAULT '',
            F_Y_TYPE INTEGER DEFAULT 0,
            F_Y_FORM INTEGER DEFAULT 0,
            F_Y_FLOCCULATION INTEGER DEFAULT 0,
            F_Y_AMOUNT REAL DEFAULT 0,
            F_Y_INVENTORY REAL DEFAULT 0,
            F_Y_TOLERANCE REAL DEFAULT 0,
            F_Y_PRICE REAL DEFAULT 0,
            F_Y_MIN_ATTENUATION REAL DEFAULT 0,
            F_Y_MAX_ATTENUATION REAL DEFAULT 0,
            F_Y_MIN_TEMP REAL DEFAULT 0,
            F_Y_MAX_TEMP REAL DEFAULT 0,
            F_Y_BEST_FOR TEXT DEFAULT '',
            F_Y_NOTES TEXT DEFAULT '',
            F_Y_IN_RECIPE INTEGER DEFAULT 0,
            F_ORDER INTEGER DEFAULT 0
        );

        CREATE TABLE M_MISC (
            _PERMID_ INTEGER PRIMARY KEY,
            _MOD_ TEXT DEFAULT '',
            _CLOUDID_ INTEGER DEFAULT 0,
            _CLOUD_STATE_ INTEGER DEFAULT 0,
            F_M_NAME TEXT DEFAULT '',
            F_M_TYPE INTEGER DEFAULT 0,
            F_M_USE_FOR TEXT DEFAULT '',
            F_M_AMOUNT REAL DEFAULT 0,
            F_M_VOLUME REAL DEFAULT 0,
            F_M_INVENTORY REAL DEFAULT 0,
            F_M_PRICE REAL DEFAULT 0,
            F_M_USE INTEGER DEFAULT 0,
            F_M_TIME REAL DEFAULT 0,
            F_M_NOTES TEXT DEFAULT '',
            F_ORDER INTEGER DEFAULT 0
        );

        CREATE TABLE M_WATER (
            _PERMID_ INTEGER PRIMARY KEY,
            _MOD_ TEXT DEFAULT '',
            _CLOUDID_ INTEGER DEFAULT 0,
            _CLOUD_STATE_ INTEGER DEFAULT 0,
            F_W_NAME TEXT DEFAULT '',
            F_W_AMOUNT REAL DEFAULT 0,
            F_W_PH REAL DEFAULT 0,
            F_W_CALCIUM REAL DEFAULT 0,
            F_W_MAGNESIUM REAL DEFAULT 0,
            F_W_SODIUM REAL DEFAULT 0,
            F_W_SULFATE REAL DEFAULT 0,
            F_W_CHLORIDE REAL DEFAULT 0,
            F_W_BICARB REAL DEFAULT 0,
            F_W_NOTES TEXT DEFAULT '',
            F_W_IN_RECIPE INTEGER DEFAULT 0
        );

        CREATE TABLE M_EQUIPMENT (
            _PERMID_ INTEGER PRIMARY KEY,
            _MOD_ TEXT DEFAULT '',
            _CLOUDID_ INTEGER DEFAULT 0,
            _CLOUD_STATE_ INTEGER DEFAULT 0,
            F_E_NAME TEXT DEFAULT '',
            F_E_TYPE INTEGER DEFAULT 0,
            F_E_BOIL_VOL REAL DEFAULT 0,
            F_E_BOIL_TIME REAL DEFAULT 0,
            F_E_BOIL_OFF REAL DEFAULT 0,
            F_E_TRUB_LOSS REAL DEFAULT 0,
            F_E_COOL_PCT REAL DEFAULT 0,
            F_E_BATCH_VOL REAL DEFAULT 0,
            F_E_FERMENTER_LOSS REAL DEFAULT 0,
            F_E_TOP_UP REAL DEFAULT 0,
            F_E_EFFICIENCY REAL DEFAULT 0,
            F_E_HOP_UTIL REAL DEFAULT 0,
            F_E_TUN_DEADSPACE REAL DEFAULT 0,
            F_E_NOTES TEXT DEFAULT ''
        );

        CREATE TABLE M_STYLE (
            _PERMID_ INTEGER PRIMARY KEY,
            _MOD_ TEXT DEFAULT '',
            _CLOUDID_ INTEGER DEFAULT 0,
            _CLOUD_STATE_ INTEGER DEFAULT 0,
            F_S_NAME TEXT DEFAULT '',
            F_S_CATEGORY TEXT DEFAULT '',
            F_S_GUIDE TEXT DEFAULT '',
            F_S_NUMBER TEXT DEFAULT '',
            F_S_TYPE INTEGER DEFAULT 0,
            F_S_MIN_OG REAL DEFAULT 0,
            F_S_MAX_OG REAL DEFAULT 0,
            F_S_MIN_FG REAL DEFAULT 0,
            F_S_MAX_FG REAL DEFAULT 0,
            F_S_MIN_IBU REAL DEFAULT 0,
            F_S_MAX_IBU REAL DEFAULT 0,
            F_S_MIN_COLOR REAL DEFAULT 0,
            F_S_MAX_COLOR REAL DEFAULT 0,
            F_S_MIN_ABV REAL DEFAULT 0,
            F_S_MAX_ABV REAL DEFAULT 0,
            F_S_DESCRIPTION TEXT DEFAULT '',
            F_S_PROFILE TEXT DEFAULT '',
            F_S_INGREDIENTS TEXT DEFAULT '',
            F_S_EXAMPLES TEXT DEFAULT ''
        );

        CREATE TABLE M_MASH (
            _PERMID_ INTEGER PRIMARY KEY,
            _MOD_ TEXT DEFAULT '',
            _CLOUDID_ INTEGER DEFAULT 0,
            _CLOUD_STATE_ INTEGER DEFAULT 0,
            F_MH_NAME TEXT DEFAULT '',
            F_MH_GRAIN_WEIGHT REAL DEFAULT 0,
            F_MH_GRAIN_TEMP REAL DEFAULT 0,
            F_MH_BOIL_TEMP REAL DEFAULT 0,
            F_MH_TUN_TEMP REAL DEFAULT 0,
            F_MH_PH REAL DEFAULT 0,
            F_MH_SPARGE_TEMP REAL DEFAULT 0,
            F_MH_BIAB INTEGER DEFAULT 0,
            F_MH_NOTES TEXT DEFAULT '',
            steps TEXT DEFAULT '',
            F_MH_EQUIP_ADJUST INTEGER DEFAULT 0
        );

        CREATE TABLE M_CARB (
            _PERMID_ INTEGER PRIMARY KEY,
            _MOD_ TEXT DEFAULT '',
            F_C_NAME TEXT DEFAULT '',
            F_C_TEMPERATURE REAL DEFAULT 0,
            F_C_TYPE INTEGER DEFAULT 0,
            F_C_PRIMER_NAME TEXT DEFAULT '',
            F_C_CARB_RATE REAL DEFAULT 0,
            F_C_NOTES TEXT DEFAULT ''
        );

        CREATE TABLE M_AGE (
            _PERMID_ INTEGER PRIMARY KEY,
            _MOD_ TEXT DEFAULT '',
            F_A_NAME TEXT DEFAULT '',
            F_A_PRIM_TEMP REAL DEFAULT 0,
            F_A_SEC_TEMP REAL DEFAULT 0,
            F_A_TERT_TEMP REAL DEFAULT 0,
            F_A_AGE_TEMP REAL DEFAULT 0,
            F_A_PRIM_DAYS REAL DEFAULT 0,
            F_A_SEC_DAYS REAL DEFAULT 0,
            F_A_TERT_DAYS REAL DEFAULT 0,
            F_A_AGE REAL DEFAULT 0,
            F_A_TYPE INTEGER DEFAULT 0,
            F_A_NOTES TEXT DEFAULT ''
        );

        CREATE TABLE M_FOLDER (
            _PERMID_ INTEGER PRIMARY KEY,
            F_F_NAME TEXT DEFAULT '',
            F_F_PARENT INTEGER DEFAULT 0
        );

        CREATE TABLE M_CLOUD_FOLDER (
            _PERMID_ INTEGER PRIMARY KEY,
            F_F_NAME TEXT DEFAULT '',
            F_F_PARENT INTEGER DEFAULT 0
        );

        CREATE TABLE M_CLOUD (
            _PERMID_ INTEGER PRIMARY KEY,
            _MOD_ TEXT DEFAULT '',
            _CLOUDID_ INTEGER DEFAULT 0,
            _CLOUD_STATE_ INTEGER DEFAULT 0,
            F_R_NAME TEXT DEFAULT '',
            F_R_BREWER TEXT DEFAULT '',
            F_R_DATE INTEGER DEFAULT 0,
            F_R_FOLDER_NAME TEXT DEFAULT '',
            F_R_PARENT INTEGER DEFAULT 0,
            F_R_TYPE INTEGER DEFAULT 0,
            F_R_NOTES TEXT DEFAULT '',
            F_R_DESCRIPTION TEXT DEFAULT '',
            F_R_RATING REAL DEFAULT 0,
            F_R_LOCKED INTEGER DEFAULT 0,
            F_R_VERSION REAL DEFAULT 0,
            F_R_OG_MEASURED REAL DEFAULT 0,
            F_R_FG_MEASURED REAL DEFAULT 0,
            F_R_OG_MEASURED_SET INTEGER DEFAULT 0,
            F_R_FG_MEASURED_SET INTEGER DEFAULT 0,
            F_R_CARB_VOLS REAL DEFAULT 0,
            F_R_MASH_PH REAL DEFAULT 0,
            F_R_EQUIPMENT TEXT DEFAULT '',
            F_R_STYLE TEXT DEFAULT '',
            F_R_MASH TEXT DEFAULT '',
            F_R_CARB TEXT DEFAULT '',
            F_R_AGE TEXT DEFAULT '',
            Ingredients TEXT DEFAULT '',
            AgeData TEXT DEFAULT ''
        );
    """)

    # Seed data
    _seed_grains(conn)
    _seed_hops(conn)
    _seed_yeasts(conn)
    _seed_equipment(conn)
    _seed_styles(conn)
    _seed_mash(conn)
    _seed_recipes(conn)
    _seed_folders(conn)

    conn.commit()
    conn.close()


def _create_opts_db(path: Path) -> None:
    conn = sqlite3.connect(str(path))
    conn.execute(
        "CREATE TABLE sysopts (R_OPTNAME TEXT PRIMARY KEY, R_VALUE TEXT DEFAULT '')"
    )
    conn.execute(
        "INSERT INTO sysopts VALUES ('Units.Gravity', '0')"
    )
    conn.execute(
        "INSERT INTO sysopts VALUES ('Units.Temperature', '0')"
    )
    conn.commit()
    conn.close()


def _seed_grains(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT INTO M_GRAIN (_PERMID_, F_G_NAME, F_G_ORIGIN, F_G_TYPE, F_G_COLOR, F_G_YIELD) "
        "VALUES (1, 'Pale Malt (2 Row) US', 'US', 0, 2.0, 79.0)"
    )
    conn.execute(
        "INSERT INTO M_GRAIN (_PERMID_, F_G_NAME, F_G_ORIGIN, F_G_TYPE, F_G_COLOR, F_G_YIELD) "
        "VALUES (2, 'Crystal 60L', 'US', 0, 60.0, 74.0)"
    )
    conn.execute(
        "INSERT INTO M_GRAIN (_PERMID_, F_G_NAME, F_G_ORIGIN, F_G_TYPE, F_G_COLOR, F_G_YIELD) "
        "VALUES (3, 'Munich Malt', 'Germany', 0, 9.0, 80.0)"
    )


def _seed_hops(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT INTO M_HOPS (_PERMID_, F_H_NAME, F_H_ORIGIN, F_H_ALPHA, F_H_TYPE, F_H_FORM) "
        "VALUES (1, 'Cascade', 'US', 5.5, 2, 0)"
    )
    conn.execute(
        "INSERT INTO M_HOPS (_PERMID_, F_H_NAME, F_H_ORIGIN, F_H_ALPHA, F_H_TYPE, F_H_FORM) "
        "VALUES (2, 'Centennial', 'US', 10.0, 0, 0)"
    )
    conn.execute(
        "INSERT INTO M_HOPS (_PERMID_, F_H_NAME, F_H_ORIGIN, F_H_ALPHA, F_H_TYPE, F_H_FORM) "
        "VALUES (3, 'Citra', 'US', 12.0, 2, 0)"
    )


def _seed_yeasts(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT INTO M_YEAST (_PERMID_, F_Y_NAME, F_Y_LAB, F_Y_PRODUCT_ID, F_Y_TYPE, F_Y_FORM, "
        "F_Y_MIN_ATTENUATION, F_Y_MAX_ATTENUATION) "
        "VALUES (1, 'Safale US-05', 'Fermentis', 'US-05', 0, 1, 73.0, 77.0)"
    )
    conn.execute(
        "INSERT INTO M_YEAST (_PERMID_, F_Y_NAME, F_Y_LAB, F_Y_PRODUCT_ID, F_Y_TYPE, F_Y_FORM, "
        "F_Y_MIN_ATTENUATION, F_Y_MAX_ATTENUATION) "
        "VALUES (2, 'WLP001', 'White Labs', 'WLP001', 0, 0, 73.0, 80.0)"
    )


def _seed_equipment(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT INTO M_EQUIPMENT (_PERMID_, F_E_NAME, F_E_TYPE, F_E_BATCH_VOL, F_E_BOIL_VOL, "
        "F_E_BOIL_TIME, F_E_EFFICIENCY) "
        "VALUES (1, 'My Brew Kettle (5 Gal)', 2, 640.0, 896.0, 60.0, 72.0)"
    )


def _seed_styles(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT INTO M_STYLE (_PERMID_, F_S_NAME, F_S_CATEGORY, F_S_GUIDE, F_S_TYPE, "
        "F_S_MIN_OG, F_S_MAX_OG, F_S_MIN_IBU, F_S_MAX_IBU, F_S_MIN_COLOR, F_S_MAX_COLOR) "
        "VALUES (1, 'American IPA', 'IPA', 'BJCP 2021', 0, 1.056, 1.070, 40.0, 70.0, 6.0, 14.0)"
    )


def _seed_mash(conn: sqlite3.Connection) -> None:
    steps_json = json.dumps([
        {
            "_Schema_": "7432",
            "F_MS_NAME": "Mash In",
            "F_MS_TYPE": "0",
            "F_MS_STEP_TEMP": "152.0",
            "F_MS_STEP_TIME": "60.0",
            "F_MS_RISE_TIME": "0.0",
            "F_MS_INFUSION_TEMP": "168.0",
        },
        {
            "_Schema_": "7432",
            "F_MS_NAME": "Mash Out",
            "F_MS_TYPE": "1",
            "F_MS_STEP_TEMP": "168.0",
            "F_MS_STEP_TIME": "10.0",
            "F_MS_RISE_TIME": "10.0",
        },
    ])
    conn.execute(
        "INSERT INTO M_MASH (_PERMID_, F_MH_NAME, F_MH_PH, F_MH_SPARGE_TEMP, steps) "
        "VALUES (1, 'Single Infusion, Medium Body', 5.4, 168.0, ?)",
        (steps_json,),
    )


def _seed_recipes(conn: sqlite3.Connection) -> None:
    equipment_json = json.dumps({
        "F_E_NAME": "My Brew Kettle (5 Gal)",
        "F_E_BATCH_VOL": "640.0",
        "F_E_BOIL_VOL": "896.0",
        "F_E_BOIL_TIME": "60.0",
        "F_E_EFFICIENCY": "72.0",
        "F_E_TYPE": "2",
    })
    style_json = json.dumps({
        "F_S_NAME": "American IPA",
        "F_S_CATEGORY": "IPA",
        "F_S_GUIDE": "BJCP 2021",
        "F_S_MIN_OG": "1.056",
        "F_S_MAX_OG": "1.070",
        "F_S_MIN_IBU": "40.0",
        "F_S_MAX_IBU": "70.0",
        "F_S_MIN_COLOR": "6.0",
        "F_S_MAX_COLOR": "14.0",
    })
    mash_json = json.dumps({
        "F_MH_NAME": "Single Infusion, Medium Body",
        "F_MH_PH": "5.4",
        "F_MH_SPARGE_TEMP": "168.0",
        "steps": json.dumps([
            {"_Schema_": "7432", "F_MS_NAME": "Mash In", "F_MS_TYPE": "0",
             "F_MS_STEP_TEMP": "152.0", "F_MS_STEP_TIME": "60.0"},
        ]),
    })
    age_json = json.dumps({
        "F_A_NAME": "Ale, Two Stage",
        "F_A_PRIM_TEMP": "67.0",
        "F_A_PRIM_DAYS": "14.0",
        "F_A_SEC_TEMP": "67.0",
        "F_A_SEC_DAYS": "14.0",
    })
    ingredients_json = json.dumps([
        {
            "_Schema_": "7406",
            "F_G_NAME": "Pale Malt (2 Row) US",
            "F_G_AMOUNT": "176.0",
            "F_G_COLOR": "2.0",
            "F_G_YIELD": "79.0",
            "F_G_TYPE": "0",
            "F_G_PERCENT": "85.0",
        },
        {
            "_Schema_": "7406",
            "F_G_NAME": "Crystal 60L",
            "F_G_AMOUNT": "16.0",
            "F_G_COLOR": "60.0",
            "F_G_YIELD": "74.0",
            "F_G_TYPE": "0",
            "F_G_PERCENT": "15.0",
        },
        {
            "_Schema_": "7403",
            "F_H_NAME": "Cascade",
            "F_H_AMOUNT": "2.0",
            "F_H_ALPHA": "5.5",
            "F_H_BOIL_TIME": "60.0",
            "F_H_USE": "0",
            "F_H_FORM": "0",
        },
        {
            "_Schema_": "7403",
            "F_H_NAME": "Citra",
            "F_H_AMOUNT": "1.5",
            "F_H_ALPHA": "12.0",
            "F_H_BOIL_TIME": "0.0",
            "F_H_USE": "4",
            "F_H_FORM": "0",
        },
        {
            "_Schema_": "7426",
            "F_Y_NAME": "Safale US-05",
            "F_Y_LAB": "Fermentis",
            "F_Y_PRODUCT_ID": "US-05",
            "F_Y_TYPE": "0",
            "F_Y_FORM": "1",
            "F_Y_MIN_ATTENUATION": "73.0",
            "F_Y_MAX_ATTENUATION": "77.0",
        },
    ])

    conn.execute(
        "INSERT INTO M_RECIPE (_PERMID_, F_R_NAME, F_R_BREWER, F_R_TYPE, "
        "F_R_OG_MEASURED, F_R_FG_MEASURED, F_R_OG_MEASURED_SET, F_R_FG_MEASURED_SET, "
        "F_R_EQUIPMENT, F_R_STYLE, F_R_MASH, F_R_AGE, Ingredients) "
        "VALUES (100, 'Test IPA', 'TestBrewer', 2, "
        "1.065, 1.012, 1, 1, ?, ?, ?, ?, ?)",
        (equipment_json, style_json, mash_json, age_json, ingredients_json),
    )


def _seed_folders(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT INTO M_CLOUD_FOLDER (_PERMID_, F_F_NAME, F_F_PARENT) "
        "VALUES (1, 'My Recipes', 0)"
    )
    conn.execute(
        "INSERT INTO M_CLOUD_FOLDER (_PERMID_, F_F_NAME, F_F_PARENT) "
        "VALUES (2, 'IPAs', 1)"
    )
    conn.execute(
        "INSERT INTO M_CLOUD_FOLDER (_PERMID_, F_F_NAME, F_F_PARENT) "
        "VALUES (3, 'Stouts', 1)"
    )
