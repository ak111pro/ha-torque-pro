# Changelog

## 0.3.1 – 2026-11-02

### Changed

- Torque Pro is now in the HACS default list. The README's install section leads with searching
  for **Torque Pro** in HACS; adding the custom repository stays as a fallback. No code changes.

## 0.3.0 – 2026-11-01

### Added

- *Trip ended* event: the *Trip* event entity now also fires `trip_ended` when the car stops
  being active (no OBD value changed for the *Driving* timeout, the same rule as the *Driving*
  sensor). Its attributes summarise the trip: start and end, duration, distance, fuel used,
  L/100 km, fuel cost, average and top speed, and the odometer at start and end (with your
  correction). Handy for a trip log or a "how was the drive" notification.

### Notes

- The app keeps its trip counters running across a short stop ("Trip resumed"), so each
  summary only counts its own part: a refuelling stop does not add the first leg twice.
- The open trip is kept in memory only. After a Home Assistant restart during a drive, the
  next summary covers the part after the restart.

## 0.2.0 – 2026-10-20

### Added

- *Odometer correction*: a number per vehicle with the kilometres between the app's own
  odometer and the car's dashboard. The *Odometer* sensor adds it (0 leaves it unchanged) and
  shows both parts as attributes. The correction is kept with the vehicle.
- Icons for every known value without a device class, such as `mdi:latitude` and
  `mdi:longitude` for the GPS position, `mdi:gauge` for RPM and `mdi:highway` for the share of
  highway driving.

### Changed

- *Odometer* is no longer a diagnostic entity and has state class `total_increasing`, so it
  has long-term statistics.

### Notes

- The *Trip* event entity only keeps a history if the `event` domain is recorded: a
  `recorder:` configuration with an `include:` list must name `event`.

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
