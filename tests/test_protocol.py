"""Tests for the upload parser (no Home Assistant needed)."""

from __future__ import annotations

import math

import pytest


@pytest.fixture
def parse(protocol):
    return protocol.parse_upload


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("05", "5"),
        ("5", "5"),
        ("0c", "c"),
        ("0C", "c"),
        ("ff1005", "ff1005"),
        ("FF1005", "ff1005"),
        ("0", "0"),
    ],
)
def test_normalise_pid(protocol, raw, expected):
    assert protocol.normalise_pid(raw) == expected


@pytest.mark.parametrize("raw", ["", "xyz", "0x5", "5 ", "-5"])
def test_normalise_pid_invalid(protocol, raw):
    assert protocol.normalise_pid(raw) is None


def test_padded_and_unpadded_keys_give_same_pid(parse):
    assert parse([("k05", "90")]).values == {"5": 90.0}
    assert parse([("k5", "90")]).values == {"5": 90.0}


def test_extended_pid_key(parse):
    assert parse([("kff1005", "11.5")]).values == {"ff1005": 11.5}


def test_repeated_keys_keep_first_value(parse):
    upload = parse([("kff1006", "1.5"), ("kff1006", "9.9"), ("k5", "80"), ("k05", "99")])
    assert upload.values["ff1006"] == 1.5
    # "k5" and "k05" are different query keys but the same PID: the later one overwrites.
    assert upload.values["5"] == 99.0


def test_non_numeric_values_ignored(parse):
    upload = parse([("k5", "abc"), ("kc", ""), ("kd", "-"), ("k4", "12")])
    assert upload.values == {"4": 12.0}


@pytest.mark.parametrize("bad", ["nan", "NaN", "inf", "-inf", "Infinity"])
def test_nan_and_inf_ignored(parse, bad):
    assert parse([("k5", bad)]).values == {}


def test_negative_and_float_values(parse):
    assert parse([("k5", "-12.5"), ("kc", "1e3")]).values == {"5": -12.5, "c": 1000.0}


def test_invalid_hex_pid_ignored(parse):
    upload = parse([("kzz", "1"), ("k", "1"), ("k0x5", "1"), ("userFullNamezz", "X")])
    assert upload.values == {}
    assert upload.meta == {}


def test_metadata(parse):
    upload = parse(
        [
            ("userFullName05", " Engine Coolant Temperature "),
            ("userShortName05", " Coolant "),
            ("userUnit05", " °C "),
            ("defaultUnit05", "°C"),
            ("userFullNameff1001", "Speed (GPS)"),
            ("userUnitff1001", "km/h"),
        ]
    )
    assert upload.meta == {
        "5": {
            "full_name": "Engine Coolant Temperature",
            "short_name": "Coolant",
            "user_unit": "°C",
            "default_unit": "°C",
        },
        "ff1001": {"full_name": "Speed (GPS)", "user_unit": "km/h"},
    }
    assert upload.values == {}


def test_metadata_padded_and_unpadded_merge(parse):
    upload = parse([("userFullName05", "A"), ("userUnit5", "V")])
    assert upload.meta == {"5": {"full_name": "A", "user_unit": "V"}}


def test_profile(parse):
    upload = parse(
        [
            ("profileName", "Test Car"),
            ("profileFuelType", "0"),
            ("profileOdometer", "12345.0"),
            ("profileTankCapacity", "50"),
        ]
    )
    assert upload.profile["Name"] == "Test Car"
    assert upload.profile == {
        "Name": "Test Car",
        "FuelType": "0",
        "Odometer": "12345.0",
        "TankCapacity": "50",
    }
    assert upload.profile_name == "Test Car"


def test_profile_name_empty_is_none(parse):
    assert parse([("profileName", "")]).profile_name is None
    assert parse([("k5", "1")]).profile_name is None


def test_bare_profile_key_ignored(parse):
    assert parse([("profile", "x")]).profile == {}


def test_identity_fields(parse):
    upload = parse(
        [
            ("id", "0123456789abcdef"),
            ("session", "11111111-2222-3333-4444-555555555555"),
            ("eml", "driver@example.com"),
            ("time", "1700000000000"),
            ("v", "9"),
        ]
    )
    assert upload.phone_id == "0123456789abcdef"
    assert upload.session == "11111111-2222-3333-4444-555555555555"
    assert upload.email == "driver@example.com"
    assert upload.time_ms == 1700000000000


def test_empty_identity_fields_become_none(parse):
    upload = parse([("id", ""), ("session", ""), ("eml", ""), ("notice", ""), ("noticeClass", "")])
    assert upload.phone_id is None
    assert upload.session is None
    assert upload.email is None
    assert upload.notice is None
    assert upload.notice_class is None


@pytest.mark.parametrize("value", ["abc", "", "-5", "1.5"])
def test_invalid_time_is_none(parse, value):
    assert parse([("time", value)]).time_ms is None


def test_notice(parse):
    upload = parse([("notice", "Trip started"), ("noticeClass", "1")])
    assert upload.notice == "Trip started"
    assert upload.notice_class == "1"


def test_unknown_keys_ignored(parse):
    upload = parse([("foo", "bar"), ("abc", "1"), ("userFoo5", "x"), ("kk", "1")])
    assert upload.values == {}
    assert upload.meta == {}
    assert upload.profile == {}
    assert upload.phone_id is None


def test_empty_upload(parse):
    upload = parse([])
    assert upload.values == {} and upload.meta == {} and upload.profile == {}


def test_gps_pid_constants(protocol, parse):
    upload = parse([("kff1005", "10.5"), ("kff1006", "20.25"), ("kff1239", "4")])
    assert upload.values[protocol.PID_LONGITUDE] == 10.5
    assert upload.values[protocol.PID_LATITUDE] == 20.25
    assert upload.values[protocol.PID_GPS_ACCURACY] == 4.0


def test_no_nan_in_values(parse):
    upload = parse([("k5", "nan"), ("kc", "1")])
    assert all(not math.isnan(v) for v in upload.values.values())
