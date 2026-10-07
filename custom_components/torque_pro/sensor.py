"""Sensors: one per Torque PID, plus last upload and vehicle profile values."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfLength, UnitOfVolume
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import TorqueConfigEntry
from .const import SIGNAL_NEW_SENSORS
from .entity import TorqueEntity, async_setup_vehicle_entities
from .hub import TorqueHub, Vehicle
from .pids import describe

PROFILE_SENSORS: tuple[tuple[str, str, str | None, SensorDeviceClass | None], ...] = (
    ("Odometer", "odometer", UnitOfLength.KILOMETERS, SensorDeviceClass.DISTANCE),
    ("TankCapacity", "tank_capacity", UnitOfVolume.LITERS, SensorDeviceClass.VOLUME),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TorqueConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    hub = entry.runtime_data

    def create(vehicle: Vehicle) -> list[SensorEntity]:
        entities: list[SensorEntity] = [TorqueLastUploadSensor(hub, vehicle)]
        entities += [
            TorqueProfileSensor(hub, vehicle, *description) for description in PROFILE_SENSORS
        ]
        entities += [
            TorquePidSensor(hub, vehicle, pid)
            for pid, meta in vehicle.sensors.items()
            if meta.get("created")
        ]

        @callback
        def _new_pids(pids: list[str]) -> None:
            async_add_entities(TorquePidSensor(hub, vehicle, pid) for pid in pids)

        entry.async_on_unload(
            async_dispatcher_connect(hass, SIGNAL_NEW_SENSORS.format(vehicle.vehicle_id), _new_pids)
        )
        return entities

    async_setup_vehicle_entities(hass, entry, hub, create, async_add_entities)


class TorquePidSensor(TorqueEntity, RestoreSensor):
    """A value reported by the app. Keeps its last value across restarts."""

    def __init__(self, hub: TorqueHub, vehicle: Vehicle, pid: str) -> None:
        super().__init__(hub, vehicle, f"pid_{pid}")
        self.pid = pid
        meta = vehicle.sensors.get(pid, {})
        info = describe(pid, meta.get("full_name"), meta.get("user_unit"))
        self._attr_name = info.name
        self._attr_native_unit_of_measurement = info.unit
        self._attr_device_class = SensorDeviceClass(info.device_class) if info.device_class else None
        self._attr_state_class = SensorStateClass.MEASUREMENT if info.statistics else None
        self._attr_suggested_display_precision = info.precision
        self._value: float | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if self.pid in self.vehicle.values:
            self._value = self.vehicle.values[self.pid]
        elif (last := await self.async_get_last_sensor_data()) is not None:
            if isinstance(last.native_value, (int, float)):
                self._value = float(last.native_value)
            elif last.native_value is not None:
                try:
                    self._value = float(last.native_value)
                except (TypeError, ValueError):
                    self._value = None

    @callback
    def _handle_upload(self) -> None:
        if self.pid in self.vehicle.values:
            value = self.vehicle.values[self.pid]
            if value != self._value:
                self._value = value
                self.async_write_ha_state()

    @property
    def native_value(self) -> float | None:
        return self._value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        meta = self.vehicle.sensors.get(self.pid, {})
        return {"pid": self.pid, "short_name": meta.get("short_name")}


class TorqueLastUploadSensor(TorqueEntity, RestoreSensor):
    """When the app last sent data for this vehicle."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "last_upload"

    def __init__(self, hub: TorqueHub, vehicle: Vehicle) -> None:
        super().__init__(hub, vehicle, "last_upload")
        self._restored: datetime | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_sensor_data()) is not None and isinstance(
            last.native_value, datetime
        ):
            self._restored = last.native_value

    @property
    def native_value(self) -> datetime | None:
        return self.vehicle.last_upload or self._restored


class TorqueProfileSensor(TorqueEntity, SensorEntity):
    """A value from the vehicle profile in the app (odometer, tank size)."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        hub: TorqueHub,
        vehicle: Vehicle,
        profile_key: str,
        key: str,
        unit: str | None,
        device_class: SensorDeviceClass | None,
    ) -> None:
        super().__init__(hub, vehicle, key)
        self._profile_key = profile_key
        self._attr_translation_key = key
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_suggested_display_precision = 0

    @property
    def native_value(self) -> float | None:
        raw = self.vehicle.profile.get(self._profile_key)
        try:
            return float(raw) if raw not in (None, "") else None
        except ValueError:
            return None
