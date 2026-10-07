"""Constants for Torque Pro."""

from __future__ import annotations

DOMAIN = "torque_pro"

API_PATH = "/api/torque_pro"
# Path of the legacy core integration. Served as an alias when the legacy platform is not
# configured, so the app keeps working without changing its URL.
LEGACY_API_PATH = "/api/torque"

CONF_EMAIL = "email"
CONF_DRIVING_TIMEOUT = "driving_timeout"
DEFAULT_DRIVING_TIMEOUT = 60  # seconds without an upload before "driving" turns off

DATA_LEGACY_ALIAS = f"{DOMAIN}_legacy_alias"

STORAGE_VERSION = 1
SAVE_DELAY = 30

SIGNAL_NEW_VEHICLE = f"{DOMAIN}_new_vehicle"
SIGNAL_NEW_SENSORS = f"{DOMAIN}_new_sensors_{{}}"  # vehicle id
SIGNAL_UPDATE = f"{DOMAIN}_update_{{}}"  # vehicle id

EVENT_TRIP = "trip"
TRIP_STARTED = "trip_started"
TRIP_RESUMED = "trip_resumed"
TRIP_NOTICE = "trip_notice"
