"""Trip events: start/resume as the app reports them, and a trip end with a summary."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_call_later
from homeassistant.util import dt as dt_util

from . import TorqueConfigEntry
from .const import (
    CONF_DRIVING_TIMEOUT,
    DEFAULT_DRIVING_TIMEOUT,
    TRIP_ENDED,
    TRIP_NOTICE,
    TRIP_RESUMED,
    TRIP_STARTED,
)
from .entity import TorqueEntity, async_setup_vehicle_entities
from .hub import TorqueHub, Vehicle


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TorqueConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    hub = entry.runtime_data
    async_setup_vehicle_entities(
        hass, entry, hub, lambda vehicle: [TorqueTripEvent(hub, vehicle)], async_add_entities
    )


class TorqueTripEvent(TorqueEntity, EventEntity):
    """Fires when the app reports a trip start or resume, and when the car stops being active.

    "Trip ended" uses the same rule as the Driving sensor: no OBD value changed for the
    configured timeout. Its attributes are the trip summary (distance, duration, fuel, ...).
    """

    _attr_translation_key = "trip"
    _attr_event_types = [TRIP_STARTED, TRIP_RESUMED, TRIP_NOTICE, TRIP_ENDED]

    def __init__(self, hub: TorqueHub, vehicle: Vehicle) -> None:
        super().__init__(hub, vehicle, "trip")
        self._unsub_timer = None

    @property
    def _timeout(self) -> timedelta:
        seconds = self.hub.entry.options.get(CONF_DRIVING_TIMEOUT, DEFAULT_DRIVING_TIMEOUT)
        return timedelta(seconds=seconds)

    @callback
    def _handle_upload(self) -> None:
        if self.vehicle.last_notice is not None:
            event_type, message = self.vehicle.last_notice
            self._trigger_event(event_type, {"message": message})
            self.async_write_ha_state()
        if self.vehicle.trip is not None:
            self._schedule_end_check()

    @callback
    def _schedule_end_check(self) -> None:
        if self._unsub_timer:
            self._unsub_timer()
        self._unsub_timer = async_call_later(
            self.hass, self._timeout.total_seconds() + 1, self._check_end
        )

    @callback
    def _check_end(self, _now) -> None:
        self._unsub_timer = None
        last = self.vehicle.last_obd_change
        if last is not None and dt_util.utcnow() - last < self._timeout:
            self._schedule_end_check()  # still active (an upload re-armed it meanwhile)
            return
        summary = self.hub.async_end_trip(self.vehicle)
        if summary is None:
            return
        self._trigger_event(TRIP_ENDED, summary)
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub_timer:
            self._unsub_timer()
            self._unsub_timer = None
