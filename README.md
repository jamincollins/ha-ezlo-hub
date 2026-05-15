# Ezlo Hub — Home Assistant Integration

[![CI](https://github.com/jamincollins/ha-ezlo-hub/actions/workflows/ci.yml/badge.svg)](https://github.com/jamincollins/ha-ezlo-hub/actions/workflows/ci.yml)
[![HACS Validation](https://github.com/jamincollins/ha-ezlo-hub/actions/workflows/hacs-validate.yml/badge.svg)](https://github.com/jamincollins/ha-ezlo-hub/actions/workflows/hacs-validate.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

A custom Home Assistant integration for **Ezlo Plus** (and compatible) Z-Wave hubs.
Connects over the local network using the hub's WebSocket API — no cloud relay required
after initial setup.

---

## Features

- **Local push** — real-time state updates via WebSocket; no polling
- **Auto-discovery** — connects, authenticates, and discovers all devices on first run
- **Proper entity types** — switch, lock, cover, sensor — not generic MQTT sensors
- **Automatic reconnect** — transparently recovers from hub reboots or network drops
- **Unsupported-device logging** — any device type not yet handled is logged at INFO
  with enough detail to make adding support straightforward

## Supported Device Types

| Ezlo Device Type  | HA Platform | Entities created                              |
|-------------------|-------------|-----------------------------------------------|
| `switch.inwall`   | `switch`    | On/off switch                                 |
| `doorlock`        | `lock`      | Lock/unlock + battery % + battery status      |
| `shutter.garage`  | `cover`     | Open/close garage door (unavailable when hub  |
|                   |             | reports device as unreachable)                |

Devices with types **not in the table above** are logged at `INFO` level with their full
item list at `DEBUG` so you can add support yourself (see below).

---

## Requirements

- Home Assistant 2023.6 or newer
- Ezlo Plus hub (serial beginning with `9`) on the same LAN as your HA instance
- A [Vera/Ezlo cloud account](https://home.getvera.com/) — used once to fetch a local
  access token; the integration talks to your hub directly after that

---

## Installation

### HACS (recommended)

1. Open HACS → **Integrations** → the three-dot menu → **Custom repositories**.
2. Add the URL of this repository and select category **Integration**.
3. Search for *Ezlo Hub*, install, and restart Home Assistant.

### Manual

1. Copy the `custom_components/ezlo/` directory from this repository to
   `<your HA config>/custom_components/ezlo/`.
2. Restart Home Assistant.

---

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for **Ezlo Hub**.
3. Fill in the form:

   | Field | Value |
   |-------|-------|
   | Hub IP Address | Local IP of your Ezlo hub (e.g. `192.168.1.171`) |
   | Vera/Ezlo Cloud Username | Your login for the Vera mobile app |
   | Vera/Ezlo Cloud Password | Same password |

4. The integration will:
   - Connect to the hub and read its serial number and UUID (no credentials needed at this stage)
   - Authenticate with the Vera/Ezlo cloud to fetch a local access token for that hub
   - Store the token — all subsequent communication is local only

> **Tip:** If the hub IP changes, remove the integration and add it again with the new IP.

---

## How It Works

```
HA ──wss://hub-ip:17000──► Ezlo hub     (local, AES256-SHA256 TLS)
                                │
HA ──HTTPS──► vera-us-oem-autha11.mios.com   (one-time auth only)
           ──HTTPS──► cloud.ezlo.com         (JWT token exchange)
           ──HTTPS──► api-cloud.ezlo.com     (access_keys_sync)
```

The hub's local API requires a specific TLS cipher (`AES256-SHA256`) due to the ARM
hardware it runs on.  Standard TLS clients reject this connection; the integration
configures the cipher explicitly.

---

## Adding Support for New Device Types

When an unsupported device is found, the log will contain a line like:

```
INFO  custom_components.ezlo  Unsupported Ezlo device type 'binary_sensor.motion'
      (name='Motion Sensor', id=abc123). See README → 'Adding Support…'
```

Enable `DEBUG` logging for `custom_components.ezlo` to also see every item the device
exposes:

```yaml
# configuration.yaml
logger:
  logs:
    custom_components.ezlo: debug
```

### Step-by-step

1. **Identify the device type string** from the log (e.g. `binary_sensor.motion`).

2. **Note the items** — each item has a `name` and `valueType`. At DEBUG level you'll
   see something like:
   ```
   DEBUG  → item 'motion': valueType=bool, value=False
   DEBUG  → item 'battery': valueType=int, value=92
   ```

3. **Add the type to `const.py`**:
   ```python
   DEV_TYPE_MOTION = "binary_sensor.motion"
   ITEM_MOTION = "motion"
   SUPPORTED_DEVICE_TYPES.add(DEV_TYPE_MOTION)
   ```

4. **Create a new platform file** (e.g. `binary_sensor.py`) following the same pattern
   as `switch.py`:
   - `async_setup_entry` filters `hub.devices` by the new type
   - The entity class extends the appropriate HA base (`BinarySensorEntity`, etc.)
   - `is_<state>` reads from `self._item["value"]`
   - `_on_hub_update` calls `self.async_write_ha_state()` when the item changes
   - `async_turn_on / async_turn_off / async_lock / …` calls
     `hub.async_set_item_value(item_id, value)` with whatever value the hub expects

5. **Add the platform to `PLATFORMS` in `const.py`**:
   ```python
   from homeassistant.const import Platform
   PLATFORMS = [..., Platform.BINARY_SENSOR]
   ```

6. **Write tests first** (see [Development](#development)) — `tests/test_binary_sensor.py`
   following the same pattern as `tests/test_switch.py`.

7. **Open a pull request** — include the DEBUG log output showing the device's items so
   reviewers can verify the mapping is correct.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| "Cannot reach hub at that IP" | Hub is off or on a different subnet | Check IP; try `ping <hub-ip>` from the HA host |
| "Cloud authentication failed" | Wrong Vera credentials | Try logging in to the Vera mobile app to confirm |
| Lock/switch shows unavailable | Hub WebSocket dropped | Wait 10 s; integration auto-reconnects |
| Garage door always unavailable | Hub reports device unreachable | Check Z-Wave device; may need to re-include it |
| Entity missing after restart | Hub was unreachable during HA start | Hub will reappear after reconnect; wait ~30 s |

To capture detailed logs:

```yaml
logger:
  logs:
    custom_components.ezlo: debug
```

---

## Development

### Running Tests

```bash
# From the repo root
pip install -r requirements_test.txt
pytest tests/ -v
```

Tests use lightweight mock WebSocket and aiohttp sessions — no live hub or Home
Assistant installation needed.

### Project Layout

```
custom_components/ezlo/
├── __init__.py         Integration setup; logs unsupported devices
├── manifest.json       HACS / HA metadata
├── config_flow.py      Setup wizard (IP + cloud credentials → local token)
├── const.py            Constants; SUPPORTED_DEVICE_TYPES set
├── hub.py              WebSocket client + Vera/Ezlo cloud auth chain
├── switch.py           switch.inwall → HA switch
├── lock.py             doorlock → HA lock + battery sensors
├── cover.py            shutter.garage → HA cover
├── sensor.py           Battery % and maintenance state sensors
└── strings.json        UI labels

tests/
├── conftest.py         HA module stubs + shared fixtures
├── test_hub.py         Cloud auth, WebSocket client, broadcast dispatch
├── test_switch.py      Switch entity properties and control
├── test_lock.py        Lock entity properties and control
├── test_cover.py       Cover entity properties and control
└── test_sensor.py      Sensor values + unsupported-device logging
```

### Cloud Auth Chain

The integration reverse-engineers the Vera mobile app's auth flow:

1. `SHA1(username.lower() + password + salt)` → salted hash
2. `GET vera-us-oem-autha11.mios.com/autha/auth/username/…` → Identity JWT
3. `GET cloud.ezlo.com/mca-router/token/exchange/legacy-to-cloud` → API JWT
4. `POST api-cloud.ezlo.com/v1/request` `{"call": "access_keys_sync"}` → per-hub tokens
5. Match by hub UUID → `{user, token}` stored in HA config entry

The stored token authenticates directly with the hub's local `hub.offline.login.ui`
WebSocket call — no internet required after setup.

---

## License

MIT
