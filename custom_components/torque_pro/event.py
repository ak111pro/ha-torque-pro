"""Trip events reported by the app ("Trip started", "Trip resumed after ...")."""

from __future__ import annotations

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import TorqueConfigEntry
from .const import TRIP_NOTICE, TRIP_RESUMED, TRIP_STARTED
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
    """Fires when the app reports a trip start or resume."""

    _attr_translation_key = "trip"
    _attr_event_types = [TRIP_STARTED, TRIP_RESUMED, TRIP_NOTICE]

    def __init__(self, hub: TorqueHub, vehicle: Vehicle) -> None:
        super().__init__(hub, vehicle, "trip")

    @callback
    def _handle_upload(self) -> None:
        if self.vehicle.last_notice is None:
            return
        event_type, message = self.vehicle.last_notice
        self._trigger_event(event_type, {"message": message})
        self.async_write_ha_state()
