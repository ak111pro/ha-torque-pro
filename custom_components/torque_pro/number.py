"""Odometer correction: what to add to Torque's odometer to match the car's dashboard."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import EntityCategory, UnitOfLength
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import TorqueConfigEntry
from .entity import TorqueEntity, async_setup_vehicle_entities
from .hub import TorqueHub, Vehicle


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TorqueConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    hub = entry.runtime_data
    async_setup_vehicle_entities(
        hass,
        entry,
        hub,
        lambda vehicle: [TorqueOdometerCorrection(hub, vehicle)],
        async_add_entities,
    )


class TorqueOdometerCorrection(TorqueEntity, NumberEntity):
    """Kilometres added to Torque's own odometer; 0 leaves the odometer as Torque counts it.

    Torque only counts the distance it logged, so the difference to the car's dashboard is
    entered once (dashboard reading minus Torque's value). It is kept with the vehicle.
    """

    _attr_translation_key = "odometer_correction"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX
    _attr_native_unit_of_measurement = UnitOfLength.KILOMETERS
    _attr_native_min_value = -10_000_000
    _attr_native_max_value = 10_000_000
    _attr_native_step = 1

    def __init__(self, hub: TorqueHub, vehicle: Vehicle) -> None:
        super().__init__(hub, vehicle, "odometer_correction")

    @property
    def native_value(self) -> float:
        return self.vehicle.odometer_correction

    async def async_set_native_value(self, value: float) -> None:
        self.hub.async_set_odometer_correction(self.vehicle, value)
