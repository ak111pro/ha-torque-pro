# Changelog

## 0.1.0 – 2026-10-14

First release. In daily use on a Home Assistant 2026.9.4 installation since 2026-10-14,
replacing the core `torque` integration.

### Added

- UI setup (no YAML), one device per vehicle profile of the app.
- A sensor for every value the app sends, created automatically with the app's name and
  unit, kept with its last value across restarts.
- GPS device tracker, *Last upload* sensor, odometer and tank capacity from the vehicle
  profile.
- *Active* binary sensor with a configurable timeout (option *Active timeout*, 60 s by
  default).
- *Trip* event entity for the app's trip notices (started, resumed, other).
- Optional e-mail filter for the app's "User Email Address".
- The legacy address `/api/torque` is served while the core `torque` platform is not
  configured, so an existing app setup keeps working; entity ids stay those of the core
  integration.
- English and German translations, diagnostics download, brand icon.

### Fixed during the first live run

- *Active* follows changing OBD values instead of arriving uploads: after the ignition is off
  the app keeps uploading the last values unchanged together with GPS data, which kept the
  sensor on.
- *Fuel cost (trip)* is a monetary sensor in Home Assistant's currency (the app only sends
  "cost"), state class `total` with `last_reset` at the start of each trip.
- The device model shows engine size, fuel type and weight from the vehicle profile
  ("3.0 l petrol, 2120 kg") instead of "Vehicle profile (3.0 l)".
