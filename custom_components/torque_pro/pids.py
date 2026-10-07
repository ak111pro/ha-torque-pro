"""Known Torque PIDs and unit mapping (no Home Assistant imports, plain strings).

Names are what Torque itself sends in `userFullName`, so entity ids match the legacy core
integration. They are only used when the app has not (yet) sent a name for a PID.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PidInfo:
    name: str
    unit: str | None = None
    device_class: str | None = None  # SensorDeviceClass value
    statistics: bool = True  # state_class measurement
    precision: int | None = None


KNOWN_PIDS: dict[str, PidInfo] = {
    "4": PidInfo("Engine Load", "%", None, True, 1),
    "5": PidInfo("Engine Coolant Temperature", "°C", "temperature", True, 0),
    "b": PidInfo("Intake Manifold Pressure", "kPa", "pressure", True, 0),
    "c": PidInfo("Engine RPM", "rpm", None, True, 0),
    "d": PidInfo("Speed (OBD)", "km/h", "speed", True, 0),
    "f": PidInfo("Intake Air Temperature", "°C", "temperature", True, 0),
    "10": PidInfo("Mass Air Flow Rate", "g/s", None, True, 1),
    "11": PidInfo("Throttle Position(Manifold)", "%", None, True, 0),
    "1f": PidInfo("Run time since engine start", "s", "duration", True, 0),
    "2f": PidInfo("Fuel Level (From Engine ECU)", "%", None, True, 0),
    "33": PidInfo("Barometric pressure (from vehicle)", "kPa", "atmospheric_pressure", True, 0),
    "3c": PidInfo("Catalyst Temperature (Bank 1,Sensor 1)", "°C", "temperature", True, 0),
    "3d": PidInfo("Catalyst Temperature (Bank 2,Sensor 1)", "°C", "temperature", True, 0),
    "3e": PidInfo("Catalyst Temperature (Bank 1,Sensor 2)", "°C", "temperature", True, 0),
    "3f": PidInfo("Catalyst Temperature (Bank 2,Sensor 2)", "°C", "temperature", True, 0),
    "42": PidInfo("Voltage (Control Module)", "V", "voltage", True, 2),
    "46": PidInfo("Ambient air temp", "°C", "temperature", True, 0),
    "5c": PidInfo("Engine Oil Temperature", "°C", "temperature", True, 0),
    "ff1001": PidInfo("Speed (GPS)", "km/h", "speed", True, 0),
    "ff1005": PidInfo("GPS Longitude", "°", None, False, 6),
    "ff1006": PidInfo("GPS Latitude", "°", None, False, 6),
    "ff1007": PidInfo("GPS Bearing", "°", None, False, 0),
    "ff1010": PidInfo("GPS Altitude", "m", "distance", True, 0),
    "ff1204": PidInfo("Trip Distance", "km", "distance", True, 2),
    "ff1208": PidInfo("Trip average Litres/100 KM", "L/100km", None, True, 1),
    "ff1223": PidInfo("Acceleration Sensor(Total)", "g", None, True, 2),
    "ff1225": PidInfo("Torque", "Nm", None, True, 0),
    "ff1238": PidInfo("Voltage (OBD Adapter)", "V", "voltage", True, 2),
    "ff1239": PidInfo("GPS Accuracy", "m", "distance", True, 0),
    "ff123a": PidInfo("GPS Satellites", None, None, True, 0),
    "ff123b": PidInfo("GPS Bearing", "°", None, False, 0),
    "ff1249": PidInfo("Air Fuel Ratio(Measured)", ":1", None, True, 2),
    "ff124d": PidInfo("Air Fuel Ratio(Commanded)", ":1", None, True, 2),
    "ff125c": PidInfo("Fuel cost (trip)", None, None, True, 2),
    "ff125d": PidInfo("Fuel flow rate/hour", "L/h", None, True, 2),
    "ff1263": PidInfo("Average trip speed(whilst moving only)", "km/h", "speed", True, 0),
    "ff1269": PidInfo("Volumetric Efficiency (Calculated)", "%", None, True, 0),
    "ff126a": PidInfo("Distance to empty (Estimated)", "km", "distance", True, 0),
    "ff126b": PidInfo("Fuel Remaining (Calculated from vehicle profile)", "%", None, True, 0),
    "ff126e": PidInfo("Cost per mile/km (Trip)", None, None, True, 3),
    "ff1271": PidInfo("Fuel used (trip)", "L", "volume", True, 2),
    "ff1273": PidInfo("Engine kW (At the wheels)", "kW", "power", True, 1),
    "ff1296": PidInfo("Percentage of City driving", "%", None, True, 0),
    "ff1297": PidInfo("Percentage of Highway driving", "%", None, True, 0),
    "ff1298": PidInfo("Percentage of Idle driving", "%", None, True, 0),
    "ff129a": PidInfo("Android device Battery Level", "%", "battery", True, 0),
    "ff5202": PidInfo("Kilometers Per Litre(Long Term Average)", "km/L", None, True, 2),
    "ff5203": PidInfo("Litres Per 100 Kilometer(Long Term Average)", "L/100km", None, True, 2),
}

# Torque unit strings -> Home Assistant unit strings (and the device class they allow).
UNITS: dict[str, tuple[str, str | None]] = {
    "°C": ("°C", "temperature"),
    "°F": ("°F", "temperature"),
    "km/h": ("km/h", "speed"),
    "mph": ("mph", "speed"),
    "kpa": ("kPa", "pressure"),
    "kPa": ("kPa", "pressure"),
    "psi": ("psi", "pressure"),
    "bar": ("bar", "pressure"),
    "V": ("V", "voltage"),
    "km": ("km", "distance"),
    "m": ("m", "distance"),
    "miles": ("mi", "distance"),
    "ft": ("ft", "distance"),
    "s": ("s", "duration"),
    "l": ("L", "volume"),
    "L": ("L", "volume"),
    "gal": ("gal", "volume"),
    "kW": ("kW", "power"),
    "hp": ("hp", None),
    "%": ("%", None),
    "l/hr": ("L/h", None),
    "l/100km": ("L/100km", None),
    "kpl": ("km/L", None),
    "mpg": ("mpg", None),
    "g/s": ("g/s", None),
    "rpm": ("rpm", None),
    "°": ("°", None),
    "g": ("g", None),
    "Nm": ("Nm", None),
    "ft-lb": ("ft-lb", None),
    ":1": (":1", None),
}


def describe(pid: str, full_name: str | None, unit: str | None) -> PidInfo:
    """Combine what the app sent with the built-in table into one description."""
    known = KNOWN_PIDS.get(pid)
    name = (full_name or "").strip() or (known.name if known else f"PID {pid}")
    if unit is not None and unit.strip():
        ha_unit, unit_class = UNITS.get(unit.strip(), (unit.strip(), None))
    elif known is not None:
        ha_unit, unit_class = known.unit, known.device_class
    else:
        ha_unit, unit_class = None, None
    if known is not None and known.device_class and known.unit == ha_unit:
        device_class = known.device_class  # e.g. "battery" for %, "atmospheric_pressure"
    else:
        device_class = unit_class
    return PidInfo(
        name=name,
        unit=ha_unit or None,
        device_class=device_class,
        statistics=known.statistics if known else True,
        precision=known.precision if known else None,
    )
