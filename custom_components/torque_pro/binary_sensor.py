"""Whether the app is currently sending data (car in use)."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_call_later
from homeassistant.util import dt as dt_util

from . import TorqueConfigEntry
from .const import CONF_DRIVING_TIMEOUT, DEFAULT_DRIVING_TIMEOUT
from .entity import TorqueEntity, async_setup_vehicle_entities
from .hub import TorqueHub, Vehicle


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TorqueConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    hub = entry.runtime_data
    async_setup_vehicle_entities(
        hass, entry, hub, lambda vehicle: [TorqueActiveSensor(hub, vehicle)], async_add_entities
    )


class TorqueActiveSensor(TorqueEntity, BinarySensorEntity):
    """On while OBD values change; off after the configured timeout without a change.

    Uploads alone are not enough: after the ignition is off Torque keeps sending the last OBD
    values (unchanged, e.g. the engine run time stays frozen) together with GPS data.
    """

    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_translation_key = "active"

    def __init__(self, hub: TorqueHub, vehicle: Vehicle) -> None:
        super().__init__(hub, vehicle, "active")
        self._unsub_timer = None

    @property
    def _timeout(self) -> timedelta:
        seconds = self.hub.entry.options.get(CONF_DRIVING_TIMEOUT, DEFAULT_DRIVING_TIMEOUT)
        return timedelta(seconds=seconds)

    @property
    def is_on(self) -> bool:
        last = self.vehicle.last_obd_change
        return last is not None and dt_util.utcnow() - last < self._timeout

    @callback
    def _handle_upload(self) -> None:
        if self._unsub_timer:
            self._unsub_timer()
        self._unsub_timer = async_call_later(
            self.hass, self._timeout.total_seconds() + 1, self._expired
        )
        self.async_write_ha_state()

    @callback
    def _expired(self, _now) -> None:
        self._unsub_timer = None
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub_timer:
            self._unsub_timer()
            self._unsub_timer = None
