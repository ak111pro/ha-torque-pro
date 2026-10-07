"""GPS position of the vehicle."""

from __future__ import annotations

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import TorqueConfigEntry
from .entity import TorqueEntity, async_setup_vehicle_entities
from .hub import TorqueHub, Vehicle
from .protocol import PID_GPS_ACCURACY, PID_LATITUDE, PID_LONGITUDE


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TorqueConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    hub = entry.runtime_data
    async_setup_vehicle_entities(
        hass, entry, hub, lambda vehicle: [TorqueTracker(hub, vehicle)], async_add_entities
    )


class TorqueTracker(TorqueEntity, TrackerEntity, RestoreEntity):
    """Position reported by the phone's GPS. Keeps the last position across restarts."""

    _attr_translation_key = "location"
    _attr_source_type = SourceType.GPS

    def __init__(self, hub: TorqueHub, vehicle: Vehicle) -> None:
        super().__init__(hub, vehicle, "location")
        self._lat: float | None = None
        self._lon: float | None = None
        self._accuracy: float = 0

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._read()
        if self._lat is None and (last := await self.async_get_last_state()) is not None:
            self._lat = last.attributes.get("latitude")
            self._lon = last.attributes.get("longitude")
            self._accuracy = last.attributes.get("gps_accuracy") or 0

    def _read(self) -> None:
        values = self.vehicle.values
        lat, lon = values.get(PID_LATITUDE), values.get(PID_LONGITUDE)
        # Torque sends 0/0 before it has a fix.
        if lat is not None and lon is not None and (lat, lon) != (0, 0):
            self._lat, self._lon = lat, lon
            self._accuracy = values.get(PID_GPS_ACCURACY, 0)

    @callback
    def _handle_upload(self) -> None:
        self._read()
        super()._handle_upload()

    @property
    def latitude(self) -> float | None:
        return self._lat

    @property
    def longitude(self) -> float | None:
        return self._lon

    @property
    def location_accuracy(self) -> float:
        return float(self._accuracy or 0)
