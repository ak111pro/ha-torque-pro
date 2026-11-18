"""Odometer numbers: the dashboard reading, and the correction added to Torque's odometer."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import EntityCategory, UnitOfLength
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import TorqueConfigEntry
from .const import DOMAIN
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
        lambda vehicle: [
            TorqueOdometerReading(hub, vehicle),
            TorqueOdometerCorrection(hub, vehicle),
        ],
        async_add_entities,
    )


class TorqueOdometerReading(TorqueEntity, NumberEntity):
    """The odometer as the dashboard shows it; entering a reading makes Torque count on from it.

    The difference to Torque's own odometer is kept as the correction, so no arithmetic is
    needed: read the dashboard, type the number in.
    """

    _attr_translation_key = "odometer_reading"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX
    _attr_native_unit_of_measurement = UnitOfLength.KILOMETERS
    _attr_native_min_value = 0
    _attr_native_max_value = 10_000_000
    _attr_native_step = 1

    def __init__(self, hub: TorqueHub, vehicle: Vehicle) -> None:
        super().__init__(hub, vehicle, "odometer_reading")

    @property
    def native_value(self) -> float | None:
        return self.vehicle.odometer

    async def async_set_native_value(self, value: float) -> None:
        try:
            self.hub.async_set_odometer_reading(self.vehicle, value)
        except ValueError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="odometer_unknown"
            ) from err


class TorqueOdometerCorrection(TorqueEntity, NumberEntity):
    """Kilometres added to Torque's own odometer; 0 leaves the odometer as Torque counts it.

    Torque only counts the distance it logged, so the difference to the car's dashboard is
    entered once (dashboard reading minus Torque's value). It is kept with the vehicle.
    """

    _attr_translation_key = "odometer_correction"
    _attr_entity_category = EntityCategory.CONFIG
    # "Odometer reading" sets it for you; kept for anyone who prefers entering the difference.
    _attr_entity_registry_enabled_default = False
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
