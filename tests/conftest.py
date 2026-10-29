"""Load the integration's HA-free modules (protocol, pids, hub) without Home Assistant.

``custom_components/torque_pro/__init__.py`` imports Home Assistant, so the real package
is never imported. Placeholder packages are registered in ``sys.modules`` instead and only
the pure-Python submodules are loaded from their files. ``ha_stubs`` stands in for the
Home Assistant names ``hub`` imports when Home Assistant is not installed.
"""

from __future__ import annotations

import importlib
from pathlib import Path
import sys
import types

import pytest

ROOT = Path(__file__).resolve().parent.parent
PACKAGE_DIR = ROOT / "custom_components" / "torque_pro"


def _placeholder(name: str, path: Path) -> types.ModuleType:
    module = types.ModuleType(name)
    module.__path__ = [str(path)]
    sys.modules[name] = module
    return module


_placeholder("custom_components", ROOT / "custom_components")
_placeholder("custom_components.torque_pro", PACKAGE_DIR)

import ha_stubs  # noqa: E402  (registers the stubs before hub is imported)

importlib.import_module("custom_components.torque_pro.hub")


@pytest.fixture(scope="session")
def protocol():
    return importlib.import_module("custom_components.torque_pro.protocol")


@pytest.fixture(scope="session")
def pids():
    return importlib.import_module("custom_components.torque_pro.pids")


@pytest.fixture
def hub():
    """Fresh hub on fresh in-memory storage, dispatcher and clock."""
    ha_stubs.clear_storage()
    ha_stubs.reset_dispatcher()
    ha_stubs.reset_clock()
    hub_module = importlib.import_module("custom_components.torque_pro.hub")
    return hub_module.TorqueHub(ha_stubs.FakeHomeAssistant(), ha_stubs.FakeConfigEntry())
