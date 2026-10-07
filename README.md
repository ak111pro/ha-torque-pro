# Torque Pro for Home Assistant

[![Validate](https://github.com/ak111pro/ha-torque-pro/actions/workflows/validate.yml/badge.svg)](https://github.com/ak111pro/ha-torque-pro/actions/workflows/validate.yml)
[![Tests](https://github.com/ak111pro/ha-torque-pro/actions/workflows/tests.yml/badge.svg)](https://github.com/ak111pro/ha-torque-pro/actions/workflows/tests.yml)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)

> [!WARNING]
> **Experimental and AI-generated. Not yet in daily use.**
>
> This integration was written by an AI assistant (Claude, by Anthropic) for its owner
> [@ak111pro](https://github.com/ak111pro). It has been tested only in a throwaway Home
> Assistant instance with replayed real uploads from the Torque Pro app. It is **not yet in
> daily use**, so expect bugs, do not rely on it for anything important, and please report
> problems as issues. This notice will be updated once it has proven itself.

A Home Assistant integration that receives the live data the **Torque Pro** OBD-II app
(Android) uploads to a web server: engine, speed, fuel and battery values, GPS position
and trip notices of your car, as proper Home Assistant entities.

## Why

It replaces the legacy core `torque` integration, which has some long-standing limits:

- its sensors have **no unique ids**, so they cannot be renamed or assigned to areas in the UI
- it is **YAML only**
- its entities **vanish after every restart** until the next trip sends data again

This integration is set up in the UI, gives every vehicle a real device, and keeps the
sensors (and their last values) across restarts.

## Features

- Set up in the UI, no YAML
- One **device per vehicle**, named after the vehicle profile in the Torque app
- **Persistent sensors**: one per value the app sends, created automatically, restored with
  their last value after a restart
- **GPS device tracker** with the phone's position and accuracy
- **Active** binary sensor: on while uploads arrive, off after a configurable timeout
- **Trip event** entity for the app's trip notices (started, resumed, other)
- **Odometer** and **tank capacity** sensors taken from the vehicle profile
- Optional **e-mail filter** (the "User Email Address" set in the app) to ignore foreign uploads
- **Legacy URL alias** `/api/torque` is served when the core `torque` platform is not
  configured, so an existing app setup keeps working unchanged
- **Migration keeps entity ids** `sensor.<vehicle>_<sensor name>` the same as the core
  integration used
- English and German translations, diagnostics download

## Installation

### HACS (custom repository)

1. In HACS open the three-dot menu, choose **Custom repositories**.
2. Add `https://github.com/ak111pro/ha-torque-pro` with category **Integration**.
3. Search for **Torque Pro** in HACS, download it and restart Home Assistant.

### Manual

Copy the folder `custom_components/torque_pro` of this repository into the
`custom_components` folder of your Home Assistant configuration and restart Home Assistant.

Requires Home Assistant 2025.8.0 or newer.

## Setup

1. In Home Assistant go to **Settings > Devices & services > Add integration** and search
   for **Torque Pro**. Optionally enter an e-mail filter. The dialog shows the URL to use.
2. Create a **long-lived access token** in your Home Assistant profile
   (profile > Security > Long-lived access tokens).
3. In the Torque Pro app open **Settings > Data Logging & Upload**:
   - **Webserver URL**: `https://<your-home-assistant>/api/torque_pro`
   - Enable **Send https: Bearer Token** and enter the long-lived token.
   - **HTTPS is required** for the bearer token; use a URL that is reachable from your phone
     (your external URL, a VPN or a reverse proxy).
   - Set the upload interval you like (for example a few seconds while driving).
   - Under **Select what to log** pick the values that should be uploaded.
   - Optionally set **User Email Address** to match the integration's e-mail filter.
4. Drive (or just start a trip). The vehicle and its entities appear with the first uploads.

The endpoint requires Home Assistant authentication, uploads without a valid token are
rejected before reaching the integration.

**Options** (integration card > Configure):

| Option | Default | Allowed | Description |
| --- | --- | --- | --- |
| E-mail filter | empty | any address | Only accept uploads whose app e-mail address matches; empty accepts all |
| Active timeout | 60 s | 15 to 3600 s | The Active sensor turns off after this long without an upload |

## Migrating from the core `torque` integration

1. Comment out (or remove) the YAML `platform: torque` entry of the old integration
   under `sensor:`.
2. Restart Home Assistant.
3. Add the **Torque Pro** integration as described above. You do not have to change the
   URL in the app: while the core platform is not configured, the old `/api/torque`
   address is served by this integration too. The bearer token stays the same.
4. Start a trip. The vehicle device and its sensors are created. Entity ids follow the
   pattern `sensor.<vehicle>_<sensor name>`, the same as with the core integration, so
   dashboards and automations keep working. Old orphaned entities of the core integration
   can be removed in the entity list.

If the core platform is still configured, it owns `/api/torque`. In that case point the app
to `/api/torque_pro` instead.

## Entities

Everything belongs to one device per vehicle.

| Entity | Type | Description |
| --- | --- | --- |
| One sensor per reported value (for example *Engine RPM*, *Speed (GPS)*, *Voltage (Control Module)*) | sensor | Named and unit-converted as the app sends it; keeps the last value across restarts. Attributes `pid` and `short_name` |
| Location | device tracker | GPS position and accuracy; ignores the 0/0 the app sends before it has a fix |
| Active | binary sensor (running) | On while uploads arrive |
| Trip | event | Event types `trip_started`, `trip_resumed`, `trip_notice`; attribute `message` |
| Last upload | sensor (diagnostic) | Time of the last upload |
| Odometer | sensor (diagnostic) | From the vehicle profile in the app, km |
| Tank capacity | sensor (diagnostic) | From the vehicle profile in the app, L |

Some sensors get a device class from their unit (temperature, speed, pressure, voltage,
distance, duration, power, battery). Counters that restart with every trip, such as
*Fuel used (trip)*, are `total_increasing` volume sensors. GPS longitude and latitude are
not recorded for long-term statistics.

## Events

The app reports a notice at the start of a trip. The **Trip** event entity fires:

| Event type | When |
| --- | --- |
| `trip_started` | The notice starts with "Trip started" |
| `trip_resumed` | The notice starts with "Trip resumed" |
| `trip_notice` | Any other notice |

Each event carries the original text as `message`.

Example automation:

```yaml
automation:
  - alias: Car trip started
    triggers:
      - trigger: state
        entity_id: event.my_car_trip
        attribute: event_type
        to: trip_started
    actions:
      - action: notify.notify
        data:
          message: "{{ trigger.to_state.attributes.message }}"
```

(Replace `event.my_car_trip` with the entity id of your vehicle's Trip entity.)

## Limitations

- **Only what Torque uploads.** Fault codes (DTCs) and readiness monitors are not part of
  the web upload, so they are not available.
- Sensor **names and units come from the app**. Values are in the **app's units**: if you
  change a unit in the app, the values change, too. No conversion is done.
- The app sends sensor **names only at the start of a trip**. Right after installing, before
  the first trip, sensors appear as soon as values with names this integration already knows
  arrive; other values wait for their name and show up after the next trip start.
- A new device is created per phone and vehicle profile name. Renaming a profile in the
  app creates a new vehicle.
- The upload interval, and therefore the freshness of the data, is whatever you set in the app.

## Privacy

Everything stays in your Home Assistant. The integration contacts no external service and
has no telemetry or analytics. The endpoint requires Home Assistant authentication, and the
diagnostics download redacts the e-mail address, phone id and odometer.

## Development

Parser and PID tests run without Home Assistant:

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements_test.txt
pytest
```

The tests use synthetic values only and contain no real vehicle or account data.

## Credits

Thank you to everyone whose work made this possible:

- the authors of the **core Home Assistant `torque` integration**, which this one replaces
  and stays entity-id compatible with
- **[JOHLC/Home-Assistant-Torque-OBDII](https://github.com/JOHLC/Home-Assistant-Torque-OBDII)**
- **[econpy/torque](https://github.com/econpy/torque)**
- the **community payload documentation** of the Torque upload protocol, which was used to
  understand the protocol
- the engine icon shape comes from [Material Design Icons](https://pictogrammers.com/library/mdi/)
  (`mdi:engine`, Apache-2.0)

No code was copied from any of these projects.

## Disclaimer

This project is AI-generated and experimental (see the notice at the top). It is not
affiliated with, endorsed by or connected to Torque Pro, Ian Hawkins or the Torque
developers, nor to any vehicle manufacturer. Torque Pro and all vehicle brand names are
trademarks of their respective owners. Use at your own risk.

## License

[MIT](LICENSE)
