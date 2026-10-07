"""Base entity for Torque Pro."""

from __future__ import annotations

from collections.abc import Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, SIGNAL_NEW_VEHICLE, SIGNAL_UPDATE
from .hub import TorqueHub, Vehicle


def vehicle_device_info(vehicle: Vehicle) -> DeviceInfo:
    profile = vehicle.profile
    details = []
    if profile.get("Displacement"):
        details.append(f"{profile['Displacement']} l")
    return DeviceInfo(
        identifiers={(DOMAIN, vehicle.vehicle_id)},
        name=vehicle.name,
        manufacturer="Torque Pro",
        model="Vehicle profile" + (f" ({', '.join(details)})" if details else ""),
    )


class TorqueEntity(Entity):
    """An entity that belongs to one vehicle and refreshes on each upload."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, hub: TorqueHub, vehicle: Vehicle, key: str) -> None:
        self.hub = hub
        self.vehicle = vehicle
        self._attr_unique_id = f"{vehicle.vehicle_id}_{key}"
        self._attr_device_info = vehicle_device_info(vehicle)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_UPDATE.format(self.vehicle.vehicle_id), self._handle_upload
            )
        )

    @callback
    def _handle_upload(self) -> None:
        self.async_write_ha_state()


@callback
def async_setup_vehicle_entities(
    hass: HomeAssistant,
    entry: ConfigEntry,
    hub: TorqueHub,
    create: Callable[[Vehicle], list[Entity]],
    add: Callable[[list[Entity]], None],
) -> None:
    """Add entities for known vehicles now and for new vehicles when they appear."""
    entities: list[Entity] = []
    for vehicle in hub.vehicles.values():
        entities.extend(create(vehicle))
    if entities:
        add(entities)

    @callback
    def _new_vehicle(entry_id: str, vehicle_id: str) -> None:
        if entry_id == entry.entry_id:
            add(create(hub.vehicles[vehicle_id]))

    entry.async_on_unload(async_dispatcher_connect(hass, SIGNAL_NEW_VEHICLE, _new_vehicle))
