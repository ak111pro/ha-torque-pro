"""Diagnostics for Torque Pro."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import TorqueConfigEntry
from .const import CONF_EMAIL

TO_REDACT = {CONF_EMAIL, "phone_id", "Odometer", "values"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: TorqueConfigEntry
) -> dict[str, Any]:
    hub = entry.runtime_data
    return {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "vehicles": [
            {
                "name": vehicle.name,
                "profile": async_redact_data(vehicle.profile, TO_REDACT),
                "sensors": vehicle.sensors,
                "last_upload": vehicle.last_upload.isoformat() if vehicle.last_upload else None,
            }
            for vehicle in hub.vehicles.values()
        ],
    }
