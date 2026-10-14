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


# Fuel type numbers of the app's vehicle profile. Only "0" is confirmed (a petrol car sends it);
# other numbers are left out rather than guessed.
FUEL_TYPES = {"0": "petrol"}


def _number(text: str | None) -> float | None:
    try:
        return float(text) if text else None
    except ValueError:
        return None


def vehicle_model(profile: dict[str, str]) -> str:
    """What the app's vehicle profile tells about the car, e.g. "3.0 l petrol, 2120 kg"."""
    engine = []
    if (litres := _number(profile.get("Displacement"))) is not None and litres > 0:
        engine.append(f"{litres:.1f} l")
    if (fuel := FUEL_TYPES.get(profile.get("FuelType", ""))) is not None:
        engine.append(fuel)
    details = [" ".join(engine)] if engine else []
    if (weight := _number(profile.get("Weight"))) is not None and weight > 0:
        details.append(f"{weight:g} kg")
    return ", ".join(details) or "Vehicle profile"


def vehicle_device_info(vehicle: Vehicle) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, vehicle.vehicle_id)},
        name=vehicle.name,
        manufacturer="Torque Pro",
        model=vehicle_model(vehicle.profile),
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
