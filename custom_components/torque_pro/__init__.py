"""Torque Pro: receive data from the Torque Pro OBD-II app."""

from __future__ import annotations

import logging

from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.http import KEY_HASS
from homeassistant.helpers.typing import ConfigType

from .const import API_PATH, DATA_LEGACY_ALIAS, DOMAIN, LEGACY_API_PATH
from .hub import TorqueHub
from .protocol import parse_upload

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.DEVICE_TRACKER,
    Platform.EVENT,
    Platform.SENSOR,
]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type TorqueConfigEntry = ConfigEntry[TorqueHub]

def _legacy_platform_configured(config: ConfigType) -> bool:
    """True if the core `torque` platform is set up in YAML (it owns /api/torque)."""
    for key, value in config.items():
        if not isinstance(key, str) or not key.startswith("sensor"):
            continue
        for platform_config in value if isinstance(value, list) else [value]:
            if isinstance(platform_config, dict) and platform_config.get("platform") == "torque":
                return True
    return False


class TorqueUploadView(HomeAssistantView):
    """Receives uploads. Torque needs the answer "OK!" or it retries the upload."""

    requires_auth = True

    def __init__(self, url: str, name: str) -> None:
        self.url = url
        self.name = name

    async def _handle(self, request: web.Request, items) -> web.Response:
        hass = request.app[KEY_HASS]
        entries = [
            entry
            for entry in hass.config_entries.async_loaded_entries(DOMAIN)
            if isinstance(getattr(entry, "runtime_data", None), TorqueHub)
        ]
        if entries:
            try:
                upload = parse_upload(items)
                for entry in entries:
                    if entry.runtime_data.async_handle_upload(upload):
                        break
            except Exception:  # noqa: BLE001 - never make the app retry because of us
                _LOGGER.exception("Could not process a Torque upload")
        return web.Response(text="OK!")

    async def get(self, request: web.Request) -> web.Response:
        return await self._handle(request, request.query.items())

    async def post(self, request: web.Request) -> web.Response:
        form = await request.post()
        return await self._handle(request, [*request.query.items(), *form.items()])



async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the upload endpoint(s) once."""
    hass.http.register_view(TorqueUploadView(API_PATH, f"api:{DOMAIN}"))
    if _legacy_platform_configured(config):
        _LOGGER.info(
            "The core torque platform is configured, so %s is left to it. "
            "Point the Torque app at %s, or remove the old platform",
            LEGACY_API_PATH,
            API_PATH,
        )
        hass.data[DATA_LEGACY_ALIAS] = False
    else:
        hass.http.register_view(TorqueUploadView(LEGACY_API_PATH, f"api:{DOMAIN}_legacy"))
        hass.data[DATA_LEGACY_ALIAS] = True
    return True


async def async_setup_entry(hass: HomeAssistant, entry: TorqueConfigEntry) -> bool:
    hub = TorqueHub(hass, entry)
    await hub.async_load()
    entry.runtime_data = hub
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: TorqueConfigEntry) -> bool:
    await entry.runtime_data.async_flush()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
