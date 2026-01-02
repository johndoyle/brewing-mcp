"""
Tests for brewing-common unit conversion.
"""

import pytest
from brewing_common.units import (
    convert_mass,
    convert_volume,
    convert_temperature,
    srm_to_ebc,
    ebc_to_srm,
    lovibond_to_ebc,
    lb_to_kg,
    kg_to_lb,
    oz_to_g,
    gal_to_l,
    f_to_c,
    c_to_f,
    sg_to_plato,
    plato_to_sg,
    MassUnit,
    VolumeUnit,
    TemperatureUnit,
)
from brewing_common.exceptions import UnitConversionError


class TestMassConversion:
    """Tests for mass unit conversion."""

    def test_kg_to_g(self):
        assert convert_mass(1.0, MassUnit.KG, MassUnit.G) == 1000.0

    def test_g_to_kg(self):
        assert convert_mass(1000.0, MassUnit.G, MassUnit.KG) == 1.0

    def test_lb_to_kg(self):
        result = convert_mass(1.0, MassUnit.LB, MassUnit.KG)
        assert abs(result - 0.45359237) < 0.0001

    def test_oz_to_g(self):
        result = convert_mass(1.0, MassUnit.OZ, MassUnit.G)
        assert abs(result - 28.3495) < 0.001

    def test_convenience_lb_to_kg(self):
        result = lb_to_kg(1.0)
        assert abs(result - 0.45359237) < 0.0001

    def test_convenience_kg_to_lb(self):
        result = kg_to_lb(1.0)
        assert abs(result - 2.20462) < 0.001

    def test_convenience_oz_to_g(self):
        result = oz_to_g(1.0)
        assert abs(result - 28.3495) < 0.001

    def test_string_units(self):
        result = convert_mass(1.0, "kg", "g")
        assert result == 1000.0

    def test_invalid_unit(self):
        with pytest.raises(UnitConversionError):
            convert_mass(1.0, "invalid", MassUnit.G)


class TestVolumeConversion:
    """Tests for volume unit conversion."""

    def test_l_to_ml(self):
        assert convert_volume(1.0, VolumeUnit.L, VolumeUnit.ML) == 1000.0

    def test_gal_us_to_l(self):
        result = convert_volume(1.0, VolumeUnit.GAL_US, VolumeUnit.L)
        assert abs(result - 3.78541) < 0.001

    def test_gal_uk_to_l(self):
        result = convert_volume(1.0, VolumeUnit.GAL_UK, VolumeUnit.L)
        assert abs(result - 4.54609) < 0.001

    def test_convenience_gal_to_l(self):
        result = gal_to_l(5.0, us=True)
        assert abs(result - 18.927) < 0.01


class TestTemperatureConversion:
    """Tests for temperature unit conversion."""

    def test_f_to_c(self):
        result = convert_temperature(32.0, TemperatureUnit.F, TemperatureUnit.C)
        assert abs(result - 0.0) < 0.01

    def test_c_to_f(self):
        result = convert_temperature(100.0, TemperatureUnit.C, TemperatureUnit.F)
        assert abs(result - 212.0) < 0.01

    def test_c_to_k(self):
        result = convert_temperature(0.0, TemperatureUnit.C, TemperatureUnit.K)
        assert abs(result - 273.15) < 0.01

    def test_convenience_f_to_c(self):
        result = f_to_c(68.0)
        assert abs(result - 20.0) < 0.01

    def test_convenience_c_to_f(self):
        result = c_to_f(20.0)
        assert abs(result - 68.0) < 0.01


class TestColourConversion:
    """Tests for beer colour unit conversion."""

    def test_srm_to_ebc(self):
        result = srm_to_ebc(10.0)
        assert abs(result - 19.7) < 0.01

    def test_ebc_to_srm(self):
        result = ebc_to_srm(19.7)
        assert abs(result - 10.0) < 0.01

    def test_lovibond_to_ebc(self):
        # 3°L is approximately 6.5 EBC
        result = lovibond_to_ebc(3.0)
        assert result > 5.0 and result < 8.0


class TestGravityConversion:
    """Tests for gravity unit conversion."""

    def test_sg_to_plato(self):
        # 1.040 SG ≈ 10°P
        result = sg_to_plato(1.040)
        assert abs(result - 10.0) < 0.5

    def test_plato_to_sg(self):
        # 10°P ≈ 1.040 SG
        result = plato_to_sg(10.0)
        assert abs(result - 1.040) < 0.002

    def test_roundtrip(self):
        sg = 1.055
        plato = sg_to_plato(sg)
        sg_back = plato_to_sg(plato)
        assert abs(sg - sg_back) < 0.001
