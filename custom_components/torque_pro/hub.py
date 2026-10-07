"""Keeps vehicles, their sensor metadata and the latest values for one config entry."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import logging
import re
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    CONF_EMAIL,
    DOMAIN,
    SAVE_DELAY,
    SIGNAL_NEW_SENSORS,
    SIGNAL_NEW_VEHICLE,
    SIGNAL_UPDATE,
    STORAGE_VERSION,
    TRIP_NOTICE,
    TRIP_RESUMED,
    TRIP_STARTED,
)
from .pids import KNOWN_PIDS
from .protocol import Upload

_LOGGER = logging.getLogger(__name__)
MAX_SESSIONS = 50


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_") or "vehicle"


@dataclass(slots=True)
class Vehicle:
    """One vehicle profile on one phone."""

    vehicle_id: str
    name: str
    phone_id: str
    profile: dict[str, str] = field(default_factory=dict)
    # pid -> {"full_name", "short_name", "user_unit", "default_unit"}
    sensors: dict[str, dict[str, str]] = field(default_factory=dict)
    values: dict[str, float] = field(default_factory=dict)
    last_upload: datetime | None = None
    last_notice: tuple[str, str] | None = None  # (event type, message)

    def as_store(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "phone_id": self.phone_id,
            "profile": self.profile,
            "sensors": self.sensors,
        }


class TorqueHub:
    """Routes uploads to vehicles and tells the platforms what changed."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.vehicles: dict[str, Vehicle] = {}
        self._sessions: dict[str, str] = {}  # session -> vehicle id
        self._last_vehicle_of_phone: dict[str, str] = {}
        # Metadata that arrived before the profile request of its session (order varies).
        self._pending_meta: dict[str, dict[str, dict[str, str]]] = {}
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}"
        )

    @property
    def email_filter(self) -> str | None:
        if CONF_EMAIL in self.entry.options:
            return self.entry.options[CONF_EMAIL].strip() or None
        return (self.entry.data.get(CONF_EMAIL) or "").strip() or None

    async def async_load(self) -> None:
        stored = await self._store.async_load() or {}
        for vehicle_id, data in stored.get("vehicles", {}).items():
            self.vehicles[vehicle_id] = Vehicle(
                vehicle_id=vehicle_id,
                name=data["name"],
                phone_id=data["phone_id"],
                profile=data.get("profile", {}),
                sensors=data.get("sensors", {}),
            )
        self._sessions = stored.get("sessions", {})
        self._last_vehicle_of_phone = stored.get("last_vehicle_of_phone", {})

    def _data(self) -> dict[str, Any]:
        return {
            "vehicles": {vid: v.as_store() for vid, v in self.vehicles.items()},
            "sessions": self._sessions,
            "last_vehicle_of_phone": self._last_vehicle_of_phone,
        }

    @callback
    def _schedule_save(self) -> None:
        self._store.async_delay_save(self._data, SAVE_DELAY)

    async def async_flush(self) -> None:
        """Write pending changes now (on unload/reload, so a reload never loads stale data)."""
        await self._store.async_save(self._data())

    # ------------------------------------------------------------------ routing

    @callback
    def _vehicle_for(self, upload: Upload) -> Vehicle | None:
        phone = upload.phone_id or "unknown"
        if upload.profile_name:
            vehicle_id = f"{phone[:12]}_{_slug(upload.profile_name)}"
            vehicle = self.vehicles.get(vehicle_id)
            if vehicle is None:
                vehicle = Vehicle(vehicle_id=vehicle_id, name=upload.profile_name, phone_id=phone)
                self.vehicles[vehicle_id] = vehicle
                async_dispatcher_send(self.hass, SIGNAL_NEW_VEHICLE, self.entry.entry_id, vehicle_id)
            vehicle.profile = dict(upload.profile)
            if upload.session:
                self._sessions[upload.session] = vehicle_id
                while len(self._sessions) > MAX_SESSIONS:
                    self._sessions.pop(next(iter(self._sessions)))
            self._last_vehicle_of_phone[phone] = vehicle_id
            self._schedule_save()
            return vehicle
        # Value and metadata requests carry no profile name: use the session, else the
        # vehicle this phone used last (e.g. Home Assistant restarted during a trip).
        vehicle_id = self._sessions.get(upload.session or "") or self._last_vehicle_of_phone.get(phone)
        return self.vehicles.get(vehicle_id) if vehicle_id else None

    @callback
    def _merge_meta(self, vehicle: Vehicle, meta: dict[str, dict[str, str]]) -> None:
        for pid, values in meta.items():
            current = vehicle.sensors.setdefault(pid, {})
            current.update({key: value for key, value in values.items() if value or key not in current})
        self._schedule_save()

    @callback
    def async_handle_upload(self, upload: Upload) -> bool:
        """Apply one upload. Returns False if it was filtered out."""
        if self.email_filter and (upload.email or "").strip().lower() != self.email_filter.lower():
            _LOGGER.debug("Ignoring upload with a different e-mail address")
            return False

        session_known = bool(upload.session and upload.session in self._sessions)
        vehicle = self._vehicle_for(upload)
        if upload.meta and not upload.profile_name and not session_known and upload.session:
            # Names/units came before this session's profile request: keep them until the
            # profile tells us which vehicle they belong to.
            pending = self._pending_meta.setdefault(upload.session, {})
            for pid, meta in upload.meta.items():
                pending.setdefault(pid, {}).update(meta)
            while len(self._pending_meta) > 5:
                self._pending_meta.pop(next(iter(self._pending_meta)))
            upload.meta = {}
        if vehicle is None:
            _LOGGER.debug("Upload before any vehicle profile was received, values dropped")
            return True

        new_pids: list[str] = []
        if upload.session and upload.session in self._pending_meta and upload.profile_name:
            self._merge_meta(vehicle, self._pending_meta.pop(upload.session))
        if upload.meta:
            self._merge_meta(vehicle, upload.meta)

        vehicle.values.update(upload.values)
        # Create an entity once a PID has a value and a name (from the app or the built-in
        # table). Waiting for the name keeps entity ids stable when values come first.
        for pid in vehicle.values:
            sensor = vehicle.sensors.setdefault(pid, {})
            if not sensor.get("created") and (sensor.get("full_name") or pid in KNOWN_PIDS):
                sensor["created"] = True
                new_pids.append(pid)
        if new_pids:
            self._schedule_save()
            async_dispatcher_send(
                self.hass, SIGNAL_NEW_SENSORS.format(vehicle.vehicle_id), new_pids
            )

        vehicle.last_upload = dt_util.utcnow()
        vehicle.last_notice = None
        if upload.notice:
            message = upload.notice
            if message.lower().startswith("trip started"):
                vehicle.last_notice = (TRIP_STARTED, message)
            elif message.lower().startswith("trip resumed"):
                vehicle.last_notice = (TRIP_RESUMED, message)
            else:
                vehicle.last_notice = (TRIP_NOTICE, message)
        async_dispatcher_send(self.hass, SIGNAL_UPDATE.format(vehicle.vehicle_id))
        return True
