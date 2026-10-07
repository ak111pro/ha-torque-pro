"""Tests for the PID table and unit mapping (no Home Assistant needed)."""

from __future__ import annotations

import pytest


def test_known_pid_with_app_name_and_unit(pids):
    info = pids.describe("5", "Engine Coolant Temperature", "°C")
    assert info.name == "Engine Coolant Temperature"
    assert info.unit == "°C"
    assert info.device_class == "temperature"
    assert info.total is False


def test_app_name_wins_over_table(pids):
    assert pids.describe("5", "  My Coolant  ", "°C").name == "My Coolant"


def test_known_pid_without_app_data_uses_table(pids):
    info = pids.describe("5", None, None)
    assert info.name == "Engine Coolant Temperature"
    assert info.unit == "°C"
    assert info.device_class == "temperature"
    assert info.precision == 0


def test_blank_name_and_unit_fall_back(pids):
    info = pids.describe("c", "  ", "  ")
    assert info.name == "Engine RPM"
    assert info.unit == "rpm"


def test_lowercase_kpa_maps_to_kpa_pressure(pids):
    info = pids.describe("b", "Intake Manifold Pressure", "kpa")
    assert info.unit == "kPa"
    assert info.device_class == "pressure"


def test_barometric_keeps_atmospheric_pressure_for_kpa(pids):
    info = pids.describe("33", None, "kPa")
    assert info.device_class == "atmospheric_pressure"
    # a different unit falls back to the generic class from the unit table
    assert pids.describe("33", None, "psi").device_class == "pressure"


def test_battery_percent_is_battery_class(pids):
    info = pids.describe("ff129a", "Android device Battery Level", "%")
    assert info.unit == "%"
    assert info.device_class == "battery"


def test_percent_without_known_class_has_none(pids):
    info = pids.describe("4", "Engine Load", "%")
    assert info.unit == "%"
    assert info.device_class is None


def test_unknown_pid_gets_generic_name(pids):
    info = pids.describe("abc", None, None)
    assert info.name == "PID abc"
    assert info.unit is None
    assert info.device_class is None
    assert info.statistics is True
    assert info.total is False
    assert info.precision is None


def test_unknown_unit_passes_through_without_device_class(pids):
    info = pids.describe("abc", "Weird", "furlongs")
    assert info.unit == "furlongs"
    assert info.device_class is None


def test_unit_with_no_device_class(pids):
    info = pids.describe("c", "Engine RPM", "rpm")
    assert info.unit == "rpm"
    assert info.device_class is None


@pytest.mark.parametrize("unit", ["l", "L", "gal"])
def test_volume_device_class_is_total(pids, unit):
    info = pids.describe("abc", "Some volume", unit)
    assert info.device_class == "volume"
    assert info.total is True


def test_unit_l_is_normalised_to_litres(pids):
    assert pids.describe("abc", "x", "l").unit == "L"


def test_fuel_used_trip_is_total(pids):
    info = pids.describe("ff1271", "Fuel used (trip)", "l")
    assert info.total is True
    assert info.device_class == "volume"
    assert info.unit == "L"


def test_fuel_used_trip_without_unit_is_total(pids):
    assert pids.describe("ff1271", None, None).total is True


def test_known_names_table(pids):
    names = {info.name for info in pids.KNOWN_PIDS.values()}
    assert len(pids.KNOWN_PIDS) >= 40
    for expected in (
        "Voltage (Control Module)",
        "Engine RPM",
        "Fuel used (trip)",
        "Speed (GPS)",
        "Engine Coolant Temperature",
        "GPS Latitude",
        "GPS Longitude",
    ):
        assert expected in names


def test_known_pid_keys_are_canonical(pids, protocol):
    for pid in pids.KNOWN_PIDS:
        assert protocol.normalise_pid(pid) == pid


def test_gps_coordinates_not_in_statistics(pids):
    assert pids.describe("ff1005", None, None).statistics is False
    assert pids.describe("ff1006", None, None).statistics is False


def test_device_classes_are_known_ha_values(pids):
    allowed = {
        "temperature", "pressure", "atmospheric_pressure", "speed", "voltage",
        "distance", "duration", "volume", "power", "battery", None,
    }
    for info in pids.KNOWN_PIDS.values():
        assert info.device_class in allowed
    for _unit, device_class in pids.UNITS.values():
        assert device_class in allowed
