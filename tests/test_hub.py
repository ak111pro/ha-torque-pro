"""Tests for TorqueHub (routing, merging, announcements) without Home Assistant.

All phone ids, emails, vehicle names and sensor names below are synthetic examples,
not data from a real home.
"""

import asyncio

import ha_stubs

from custom_components.torque_pro.const import (
    CONF_EMAIL,
    SIGNAL_NEW_SENSORS,
    SIGNAL_NEW_VEHICLE,
    SIGNAL_UPDATE,
    TRIP_NOTICE,
    TRIP_RESUMED,
    TRIP_STARTED,
)
from custom_components.torque_pro.hub import MAX_SESSIONS, TorqueHub
from custom_components.torque_pro.protocol import Upload

PHONE1 = "a1b2c3d4e5f6g7h8"
PHONE2 = "ffffffffffff1111"
TRUCK = "Family Truck"
TRUCK_VID = "a1b2c3d4e5f6_family_truck"
VAN = "Work Van"
VAN_VID = "a1b2c3d4e5f6_work_van"


def handle(hub, phone_id=PHONE1, session="s1", **kwargs):
    """Feed one upload to the hub and return its answer."""
    kwargs.setdefault("email", None)
    upload = Upload(phone_id=phone_id, session=session, time_ms=None, **kwargs)
    return hub.async_handle_upload(upload)


def restart(hub):
    """What Home Assistant does on a reload: flush the hub, then load it into a new one."""
    asyncio.run(hub.async_flush())
    fresh = TorqueHub(ha_stubs.FakeHomeAssistant(), ha_stubs.FakeConfigEntry())
    asyncio.run(fresh.async_load())
    return fresh


# --- 1. e-mail filter ---------------------------------------------------------


def test_email_filter_accepts_everything_when_unset(hub):
    assert handle(hub, phone_id=PHONE1, profile={"Name": TRUCK})
    assert handle(hub, phone_id=PHONE2, profile={"Name": TRUCK})
    assert len(hub.vehicles) == 2


def test_email_filter_from_entry_data(hub):
    hub.entry.data[CONF_EMAIL] = "fleet@example.com"
    assert handle(hub, profile={"Name": TRUCK}, email="fleet@example.com")
    assert not handle(hub, profile={"Name": VAN}, email="other@example.com")
    assert set(hub.vehicles) == {TRUCK_VID}


def test_email_filter_options_win_over_data(hub):
    hub.entry.data[CONF_EMAIL] = "old@example.com"
    hub.entry.options[CONF_EMAIL] = "new@example.com"
    assert not handle(hub, profile={"Name": TRUCK}, email="old@example.com")
    assert handle(hub, profile={"Name": TRUCK}, email="new@example.com")


def test_email_filter_ignores_case_and_surrounding_spaces(hub):
    hub.entry.options[CONF_EMAIL] = "  Fleet@Example.COM  "
    assert handle(hub, values={"5": 90.0}, email="fleet@example.com")
    assert handle(hub, values={"5": 91.0}, email="  FLEET@EXAMPLE.com ")


def test_filtered_upload_changes_nothing(hub):
    hub.entry.options[CONF_EMAIL] = "fleet@example.com"
    handle(hub, profile={"Name": TRUCK}, email="fleet@example.com")
    vehicle = hub.vehicles[TRUCK_VID]

    assert not handle(hub, values={"5": 99.0}, email="other@example.com")
    assert vehicle.values == {}
    assert not handle(hub, profile={"Name": VAN}, email="x@example.com")
    assert set(hub.vehicles) == {TRUCK_VID}
    assert ha_stubs.sent(SIGNAL_NEW_VEHICLE) == [(hub.entry.entry_id, TRUCK_VID)]


# --- 2. profile uploads create vehicles ---------------------------------------


def test_profile_creates_vehicle_and_signals_new_vehicle_once(hub):
    assert handle(hub, session="s1", profile={"Name": TRUCK, "FuelType": "Petrol"})
    vehicle = hub.vehicles[TRUCK_VID]
    assert vehicle.vehicle_id == TRUCK_VID
    assert vehicle.name == TRUCK
    assert vehicle.phone_id == PHONE1
    assert vehicle.profile["FuelType"] == "Petrol"
    assert ha_stubs.sent(SIGNAL_NEW_VEHICLE) == [(hub.entry.entry_id, TRUCK_VID)]

    # the app sends its profile with every request: no re-signal, name stays as it was
    assert handle(hub, session="s2", profile={"Name": TRUCK})
    assert set(hub.vehicles) == {TRUCK_VID}
    assert vehicle.name == TRUCK
    assert len(ha_stubs.sent(SIGNAL_NEW_VEHICLE)) == 1


def test_renamed_profile_creates_a_second_vehicle(hub):
    handle(hub, profile={"Name": TRUCK})
    handle(hub, session="s2", profile={"Name": VAN})
    assert set(hub.vehicles) == {TRUCK_VID, VAN_VID}
    assert len(ha_stubs.sent(SIGNAL_NEW_VEHICLE)) == 2


def test_same_profile_name_on_two_phones_gives_two_vehicles(hub):
    handle(hub, phone_id=PHONE1, profile={"Name": TRUCK})
    handle(hub, phone_id=PHONE2, profile={"Name": TRUCK})
    assert set(hub.vehicles) == {TRUCK_VID, "ffffffffffff_family_truck"}


# --- 3. value uploads are routed by session, else by last vehicle -------------


def test_value_uploads_follow_their_session(hub):
    handle(hub, session="s1", profile={"Name": TRUCK})
    handle(hub, session="s2", profile={"Name": VAN})
    handle(hub, session="s1", values={"5": 91.0})
    handle(hub, session="s2", values={"5": 92.0})
    assert hub.vehicles[TRUCK_VID].values == {"5": 91.0}
    assert hub.vehicles[VAN_VID].values == {"5": 92.0}


def test_value_upload_without_session_goes_to_the_last_vehicle(hub):
    handle(hub, session="s1", profile={"Name": TRUCK})
    handle(hub, session="s2", profile={"Name": VAN})
    assert handle(hub, session=None, values={"5": 93.0})
    assert hub.vehicles[VAN_VID].values["5"] == 93.0  # the van profile was the last one seen
    assert hub.vehicles[TRUCK_VID].values == {}


def test_upload_before_any_vehicle_is_accepted_but_not_routed(hub):
    # nothing to route to yet: the values are dropped, but the upload was not filtered out
    assert handle(hub, values={"5": 1.0}) is True
    assert hub.vehicles == {}


def test_restart_during_a_trip_keeps_both_uploads_routed(hub):
    handle(hub, session="s1", profile={"Name": TRUCK})
    handle(hub, session="s1", values={"5": 90.0})
    hub2 = restart(hub)
    assert set(hub2.vehicles) == {TRUCK_VID}
    assert hub2._last_vehicle_of_phone == {PHONE1: TRUCK_VID}

    # the known session keeps routing, and a brand-new session (Torque restarted too)
    # or a session-less upload still lands on the phone's last vehicle
    assert handle(hub2, session="s1", values={"5": 91.0})
    assert handle(hub2, session="s3", values={"d": 60.0})
    assert handle(hub2, session=None, values={"d": 61.0})
    assert hub2.vehicles[TRUCK_VID].values == {"5": 91.0, "d": 61.0}


def test_last_vehicle_of_phone_follows_profiles_only(hub):
    handle(hub, session="s1", profile={"Name": TRUCK})
    handle(hub, session="s2", profile={"Name": VAN})
    handle(hub, session="s1", values={"5": 91.0})
    assert hub._last_vehicle_of_phone[PHONE1] == VAN_VID  # value uploads do not move it
    handle(hub, session="s1", profile={"Name": TRUCK})
    assert hub._last_vehicle_of_phone[PHONE1] == TRUCK_VID


# --- 4. metadata that arrives before the profile ------------------------------


def test_meta_before_the_profile_is_kept_and_merged(hub):
    meta = {"abc": {"full_name": "Custom sensor", "user_unit": "kPa"}}
    assert handle(hub, values={"abc": 111.0}, meta=meta)  # no vehicle yet, values dropped
    assert hub.vehicles == {}
    assert hub._pending_meta["s1"]["abc"]["full_name"] == "Custom sensor"

    assert handle(hub, profile={"Name": TRUCK})  # the profile names the session's vehicle
    vehicle = hub.vehicles[TRUCK_VID]
    assert vehicle.sensors["abc"]["full_name"] == "Custom sensor"
    assert vehicle.sensors["abc"]["user_unit"] == "kPa"
    assert "s1" not in hub._pending_meta

    assert handle(hub, values={"abc": 112.0})
    assert vehicle.values["abc"] == 112.0


def test_only_five_pending_sessions_are_kept(hub):
    for i in range(1, 7):
        handle(
            hub, session=f"s{i}", values={"abc": float(i)}, meta={"abc": {"full_name": f"Name {i}"}}
        )
    assert list(hub._pending_meta) == ["s2", "s3", "s4", "s5", "s6"]  # the oldest was dropped

    handle(hub, session="s1", profile={"Name": TRUCK})
    assert hub.vehicles[TRUCK_VID].sensors == {}
    handle(hub, session="s6", profile={"Name": VAN})
    assert hub.vehicles[VAN_VID].sensors["abc"]["full_name"] == "Name 6"


# --- 5. merging sensor metadata ------------------------------------------------


def test_merge_never_overwrites_with_empty_values_and_adds_new_keys(hub):
    handle(hub, profile={"Name": TRUCK})
    vehicle = hub.vehicles[TRUCK_VID]
    hub._merge_meta(vehicle, {"5": {"full_name": "Coolant", "user_unit": "C"}})
    hub._merge_meta(
        vehicle, {"5": {"full_name": "", "short_name": "ECT"}, "d": {"full_name": "Speed"}}
    )
    assert vehicle.sensors["5"]["full_name"] == "Coolant"  # empty value did not overwrite
    assert vehicle.sensors["5"]["user_unit"] == "C"
    assert vehicle.sensors["5"]["short_name"] == "ECT"  # new key added
    assert vehicle.sensors["d"]["full_name"] == "Speed"


def test_merge_replaces_outdated_names_with_real_values(hub):
    handle(hub, profile={"Name": TRUCK})
    vehicle = hub.vehicles[TRUCK_VID]
    hub._merge_meta(vehicle, {"5": {"full_name": "old name"}})
    hub._merge_meta(vehicle, {"5": {"full_name": "Engine Coolant Temperature"}})
    assert vehicle.sensors["5"]["full_name"] == "Engine Coolant Temperature"


# --- 6. a sensor is announced once it has a value and a name -------------------


def test_known_pid_is_announced_once_when_it_gets_a_value(hub):
    handle(hub, profile={"Name": TRUCK})
    signal = SIGNAL_NEW_SENSORS.format(TRUCK_VID)

    handle(hub, values={"5": 90.0})  # "5" is in KNOWN_PIDS: value alone is enough
    assert ha_stubs.sent(signal) == [(["5"],)]

    handle(hub, values={"5": 91.0})  # value change: still announced only once
    assert ha_stubs.sent(signal) == [(["5"],)]


def test_unknown_pid_is_announced_when_its_name_arrives(hub):
    handle(hub, profile={"Name": TRUCK})
    signal = SIGNAL_NEW_SENSORS.format(TRUCK_VID)

    handle(hub, values={"abc": 1.0})  # value without name: no entity yet
    assert ha_stubs.sent(signal) == []

    handle(hub, meta={"abc": {"full_name": "Custom sensor"}})  # now it has both
    assert ha_stubs.sent(signal) == [(["abc"],)]

    handle(hub, values={"abc": 2.0}, meta={"abc": {"full_name": "Custom sensor renamed"}})
    assert len(ha_stubs.sent(signal)) == 1  # never announced twice


def test_name_without_value_is_not_announced(hub):
    handle(hub, profile={"Name": TRUCK})
    handle(hub, meta={"abc": {"full_name": "Custom sensor"}})
    assert ha_stubs.sent(SIGNAL_NEW_SENSORS.format(TRUCK_VID)) == []


def test_gps_pid_announced_like_any_other(hub):
    handle(hub, profile={"Name": TRUCK})
    handle(hub, values={"ff1001": 55.0})  # "ff1001" is in KNOWN_PIDS
    assert ha_stubs.sent(SIGNAL_NEW_SENSORS.format(TRUCK_VID)) == [(["ff1001"],)]


# --- 7. last_obd_change only moves on changed OBD values -----------------------


def test_last_obd_change_ignores_gps_and_unchanged_values(hub):
    handle(hub, profile={"Name": TRUCK}, values={"5": 90.0})
    vehicle = hub.vehicles[TRUCK_VID]
    obd_time = vehicle.last_obd_change
    assert obd_time is not None

    handle(hub, values={"ff1001": 50.0, "ff1005": 9.99999})  # GPS/phone values: ignored
    assert vehicle.last_obd_change == obd_time
    handle(hub, values={"5": 90.0})  # Torque keeps resending the last OBD values: ignored
    assert vehicle.last_obd_change == obd_time

    handle(hub, values={"5": 91.0})  # a real OBD change: the trip clock moves
    assert vehicle.last_obd_change > obd_time
    assert vehicle.last_upload == ha_stubs.clock.last


# --- 8. trip notices ------------------------------------------------------------


def test_trip_notices_are_classified_and_cleared_by_the_next_upload(hub):
    handle(hub, profile={"Name": TRUCK})
    vehicle = hub.vehicles[TRUCK_VID]

    handle(hub, notice="Trip started at 8:15 AM")
    assert vehicle.last_notice == (TRIP_STARTED, "Trip started at 8:15 AM")
    handle(hub, notice="trip resumed after refueling")
    assert vehicle.last_notice == (TRIP_RESUMED, "trip resumed after refueling")
    handle(hub, notice="Check engine light on")
    assert vehicle.last_notice == (TRIP_NOTICE, "Check engine light on")

    handle(hub, values={"5": 92.0})
    assert vehicle.last_notice is None


# --- 9. session bookkeeping is capped -------------------------------------------


def test_sessions_are_capped_at_max_sessions(hub):
    for i in range(MAX_SESSIONS + 1):
        handle(hub, session=f"s{i}", profile={"Name": TRUCK})
    assert len(hub._sessions) == MAX_SESSIONS
    assert "s0" not in hub._sessions  # the oldest was dropped
    assert hub._sessions[f"s{MAX_SESSIONS}"] == TRUCK_VID


# --- every routed upload ends with an update signal for its vehicle -------------


def test_routed_upload_dispatches_one_update_signal(hub):
    handle(hub, profile={"Name": TRUCK})
    handle(hub, values={"5": 90.0})
    signal = SIGNAL_UPDATE.format(TRUCK_VID)
    assert ha_stubs.sent(signal) == [(), ()]  # one dispatch per routed upload, no payload


def test_uploads_schedule_a_debounced_save(hub):
    handle(hub, profile={"Name": TRUCK})
    assert any(store is hub._store for store, _data in hub._store.delayed)

    ha_stubs.FakeStore.flush_delayed()  # the debounced timer fires
    hub2 = TorqueHub(ha_stubs.FakeHomeAssistant(), ha_stubs.FakeConfigEntry())
    asyncio.run(hub2.async_load())
    assert set(hub2.vehicles) == {TRUCK_VID}
