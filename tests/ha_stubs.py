"""Minimal stand-ins for the Home Assistant names ``hub.py`` imports.

Registered in ``sys.modules`` only when Home Assistant is not installed, so the same
tests run here and in an environment with real Home Assistant. Just enough for the hub
to work: a config entry, a hass object, a callback decorator, a dispatcher that records
the signals it receives, a storage helper that keeps the data in memory, and a clock.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import importlib.util
import sys
import types
from unittest.mock import Mock

BASE_TIME = datetime(2026, 1, 1)


class FakeClock:
    """Stand-in for ``dt_util.utcnow``, handing out one new timestamp per call."""

    def __init__(self) -> None:
        self._i = 0
        self.last = BASE_TIME

    def __call__(self) -> datetime:
        self._i += 1
        self.last = BASE_TIME + timedelta(minutes=self._i)
        return self.last


clock = FakeClock()


class FakeHomeAssistant:
    def __init__(self) -> None:
        self.data: dict[str, object] = {}


class FakeConfigEntry:
    def __init__(
        self,
        data: dict[str, object] | None = None,
        options: dict[str, object] | None = None,
        entry_id: str = "test",
    ) -> None:
        self.data = data or {}
        self.options = options or {}
        self.entry_id = entry_id


class FakeStore:
    """In-memory stand-in for ``homeassistant.helpers.storage.Store``.

    The payload dict is shared between stores so a second hub can read what a first
    one saved, the way a reload reads the file on disk.
    """

    def __init__(self, hass: object, version: int, key: str) -> None:
        self.hass = hass
        self.version = version
        self.key = key

    # Pending async_delay_save calls, shared so flush_delayed() writes them all out.
    delayed: list[tuple[FakeStore, object]] = []

    async def async_load(self) -> dict | None:
        return _storage.get(self.key)

    async def async_save(self, data: dict) -> None:
        _storage[self.key] = data

    @classmethod
    def flush_delayed(cls) -> None:
        """Write every pending ``async_delay_save`` payload into the storage."""
        for store, data in cls.delayed:
            _storage[store.key] = data()
        cls.delayed.clear()

    def async_delay_save(self, data_func: object, delay: float) -> None:
        self.delayed.append((self, data_func))


_storage: dict[str, dict] = {}


def clear_storage() -> None:
    _storage.clear()
    FakeStore.delayed.clear()


def reset_clock() -> None:
    clock._i = 0
    clock.last = BASE_TIME


dispatcher_send = Mock(name="async_dispatcher_send")


def reset_dispatcher() -> None:
    """Fresh recorder, rebound in both the stub module and ``hub``."""
    global dispatcher_send
    dispatcher_send = Mock(name="async_dispatcher_send")
    sys.modules["homeassistant.helpers.dispatcher"].async_dispatcher_send = dispatcher_send
    hub = sys.modules.get("custom_components.torque_pro.hub")
    if hub is not None:
        hub.async_dispatcher_send = dispatcher_send


def dispatches() -> list[tuple]:
    """Argument tuple ``(hass, signal, *payload)`` of every dispatch, in the order sent."""
    return [args for args, _kwargs in dispatcher_send.call_args_list]


def sent(signal: str) -> list[tuple]:
    """Payload arguments of every dispatch of one signal (empty list when never sent)."""
    return [args[2:] for args in dispatches() if len(args) > 1 and args[1] == signal]


def _install() -> None:
    ha = types.ModuleType("homeassistant")
    core = types.ModuleType("homeassistant.core")
    core.HomeAssistant = FakeHomeAssistant
    core.callback = lambda func: func

    config_entries = types.ModuleType("homeassistant.config_entries")
    config_entries.ConfigEntry = FakeConfigEntry

    helpers = types.ModuleType("homeassistant.helpers")
    dispatcher = types.ModuleType("homeassistant.helpers.dispatcher")
    dispatcher.async_dispatcher_send = dispatcher_send
    helpers.dispatcher = dispatcher

    storage = types.ModuleType("homeassistant.helpers.storage")
    storage.Store = FakeStore
    helpers.storage = storage

    util = types.ModuleType("homeassistant.util")
    util_dt = types.ModuleType("homeassistant.util.dt")
    util_dt.utcnow = clock
    util.dt = util_dt

    ha.core = core
    ha.config_entries = config_entries
    ha.helpers = helpers
    ha.util = util

    for name, module in (
        ("homeassistant", ha),
        ("homeassistant.core", core),
        ("homeassistant.config_entries", config_entries),
        ("homeassistant.helpers", helpers),
        ("homeassistant.helpers.dispatcher", dispatcher),
        ("homeassistant.helpers.storage", storage),
        ("homeassistant.util", util),
        ("homeassistant.util.dt", util_dt),
    ):
        sys.modules.setdefault(name, module)


if importlib.util.find_spec("homeassistant") is None:
    _install()
