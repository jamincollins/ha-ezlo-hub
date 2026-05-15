# From Brick to Integration: How I Used Claude Code to Reverse-Engineer an Ezlo Plus Hub into Home Assistant

My Ezlo Plus Z-Wave hub had been sitting in a frustrating limbo. The Vera Mobile app worked perfectly — lights, locks, scenes, all of it. But the Vera web dashboard showed the hub as permanently offline, and Home Assistant had no way to talk to it at all. The official integrations were built for the old Vera HTTP API, which the newer Ezlo firmware had quietly abandoned.

I created a dedicated virtual machine to use as a Claude playground.  One where I could let Claude run wild, with passwordless sudo and liberal permissions.

Once the virtual machine was created, I ssh'd into it, setup Claude with Super Powers, opened a tmux session, and fired up a Claude Code session:  

```bash
claude --dangerously-skip-permissions
```

then issued a single prompt:

> "Your goal is to get an Ezlo Plus z-wave hub working with Home Assistant.
> 
> The hub works with the Vera Mobile app, but not the Vera Web UI.  The Vera Web UI shows that it exists, but always shows it as offline. The apk for the mobile app is available in this directory, if it is of any use.
> 
> The hub is available at: 192.168.x.x
> 
> The host OS is Arch Linux.
> 
> You should have passwordless sudo, should you need to install packages."

What followed was Claude doing the heavy lifting across equal parts network forensics, Android APK reverse engineering, cloud API archaeology, and software engineering — all without me writing a single line of code. It ended with a fully published, HACS-compatible Home Assistant integration.

---

## Step 1: What's Actually Running on This Hub?

The first thing Claude did was run a full 65,535-port scan of the hub's IP address. Three open ports came back:

- **22** — SSH (though no password tried worked)
- **53** — DNS (dnsmasq, as expected)
- **4803** — Something unknown that responds with a single byte `\xFB` and then waits

That third port was the interesting one. Claude tried HTTP, WebSocket, plain TCP, and multiple TLS configurations — all rejected. Then it tried a very specific TLS cipher: `AES256-SHA256`. With that cipher specified, port 17000 (which had appeared filtered in the initial scan) suddenly answered and presented a valid TLS certificate with `CN=90030191` — the hub's own serial number.

Why that specific cipher? The Ezlo Plus runs on ARM hardware with constrained cryptographic acceleration. The hub's firmware only accepts `AES256-SHA256`, and modern TLS clients (Python, OpenSSL with defaults) immediately negotiate something else and get rejected. Once Claude identified the cipher by cross-referencing the decompiled app source against the port scan results, the WebSocket connection was straightforward:

```python
ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
ctx.set_ciphers("AES256-SHA256")
ws = await websockets.connect("wss://192.168.x.x:17000", ssl=ctx)
```

The hub confirmed it was alive with `hub.info.get` — no authentication required for that one call.

---

## Step 2: Decompiling the Mobile App

The hub needed authentication for everything else. To understand the auth flow, Claude installed `jadx` and decompiled the Vera Mobile APK (`com.vera.android_7.108.1.36.xapk`), producing 8,494 Java source files from the five DEX bundles inside. It then searched them systematically for connection logic, authentication methods, and API endpoints.

The key findings:

**Local discovery**: The app finds hubs via mDNS, advertising as `_ezlo._tcp.local`. Claude confirmed this with `avahi-browse`, which returned `eZLO h2.1 controller (90030191)` — the serial number right there in the service name.

**Local authentication**: Hub login uses `hub.offline.login.ui` with a `user` UUID and `token` string. These aren't stored in the app — they're fetched fresh from the Ezlo cloud on every session.

**The password salt**: Found inside `MiosRestCredentials.java`:
```java
private static final String SHA_1_SALT_FOR_PASSWORD = "oZ7QE6LcLJp6fiWzdqZc";
```
The cloud auth doesn't use a plain SHA-1 hash of your password. It uses `SHA1(username.lower() + password + salt)`. Without this salt — buried in compiled app code — cloud authentication always fails with a 404. This is almost certainly why the Vera web UI was broken: it was likely using a different or missing salt after Ezlo migrated their auth backend.

**The full auth chain**: Tracing through `AccessKeysManager.java`, `NmaControllerService.java`, and `EzloCloudService.java`, Claude mapped the complete flow:

1. Salted SHA-1 → `vera-us-oem-autha11.mios.com` → Identity JWT
2. Legacy JWT → `cloud.ezlo.com/mca-router/token/exchange/legacy-to-cloud` → API JWT
3. API JWT → `api-cloud.ezlo.com/v1/request` with `{"call": "access_keys_sync"}` → per-hub `{user, token}` pairs

The access keys response matches a controller UUID to a user UUID and a local token string. That pair authenticates directly with the hub's WebSocket API — no cloud connection required after that point.

---

## Step 3: Talking to the Hub

With the auth chain understood and implemented, Claude connected and authenticated. The full device list came back:

```
- Fan                    (switch.inwall)
- Garage Deadbolt        (doorlock)   battery: 88%
- Front Door Deadbolt    (doorlock)   battery: 87%, replace_battery_soon
- Garage Door Opener     (shutter.garage, reachable: false)
```

The garage door opener — a NuTone/Linear GD00Z-5, Z-Wave node 12 — was offline. The hub knew about it but had no live items. Everything else had full state: lock positions, battery levels, switch state, and the 24 items that represent them in the hub's internal model.

Broadcasts from the hub use the `ui_broadcast` message ID with `msg_subclass: hub.item.updated`, giving real-time push updates whenever a device state changes. No polling required.

---

## Step 4: Building the Home Assistant Integration

No working HA integration existed for Ezlo Plus hubs. The built-in Vera integration uses the old HTTP API on port 3480, which Ezlo firmware dropped. The most-referenced HACS integration (`fuatakgun/ezlo_ha`) had disappeared from GitHub. The `ezmqtt` project works but requires running a separate MQTT bridge process alongside HA — another moving part to keep alive.

Claude proposed writing a proper native integration instead: correct entity types, real-time WebSocket push updates, no extra processes. When I asked whether that was better than the MQTT approach, it laid out the tradeoffs clearly and I agreed.

It followed Test-Driven Development strictly — writing all 65 tests first, watching them fail because the production code didn't exist yet, then writing the minimal code to make them pass:

```
65 tests across 5 files:
  test_hub.py     — cloud auth chain, WebSocket client, broadcast dispatch
  test_switch.py  — switch entity properties and control
  test_lock.py    — lock entity properties and control
  test_cover.py   — cover/garage door entity
  test_sensor.py  — battery sensors + unsupported device logging
```

The test suite mocks both the WebSocket connection and the cloud API, so it runs entirely without a live hub or Home Assistant installation in under a second.

The integration structure:

| Platform | Ezlo Device Type | Entities |
|---|---|---|
| `switch` | `switch.inwall` | On/off switch |
| `lock` | `doorlock` | Lock/unlock |
| `sensor` | `doorlock` | Battery %, battery status |
| `cover` | `shutter.garage` | Open/close (unavailable when hub reports device offline) |

The config flow asks for three things: hub IP, Vera cloud username, and Vera cloud password. It runs the full auth chain automatically and stores only the local access token — your cloud password never persists in HA's config.

After writing the code, Claude ran its own code review. It caught three real bugs:

**WebSocket leak**: `async_get_hub_info` (used during setup to discover the hub serial before cloud auth) left the WebSocket open if `ws.close()` raised an exception. Fixed with a `finally` block.

**Deprecated API**: `asyncio.get_event_loop()` in two places, deprecated since Python 3.10 in favour of `asyncio.get_running_loop()`.

**Double reconnect delay**: The listen loop was sleeping before calling `_reconnect()`, which also sleeps — meaning a dropped connection took 20 seconds to recover instead of 10.

---

## Step 5: Local Testing with Home Assistant

Rather than asking me to deploy to my separate HA device for testing, Claude installed HA Container via Docker directly on the local Arch Linux machine:

```bash
docker run -d \
  --name homeassistant \
  --privileged \
  --restart=unless-stopped \
  -e TZ=America/Denver \
  -v /path/to/ha-config:/config \
  --network=host \
  ghcr.io/home-assistant/home-assistant:stable
```

It pre-staged the custom integration, then completed the entire HA onboarding and integration setup programmatically via the REST API — no browser required:

```python
# Start the Ezlo config flow
r = requests.post(f"{BASE}/api/config/config_entries/flow",
                  headers=HEADERS,
                  json={"handler": "ezlo"})
flow_id = r.json()["flow_id"]

# Submit hub IP and cloud credentials
requests.post(f"{BASE}/api/config/config_entries/flow/{flow_id}",
              headers=HEADERS,
              json={"host": "192.168.x.x",
                    "username": "...",
                    "password": "..."})
```

The integration loaded, authenticated with the hub, and all 7 entities appeared with live data. Claude then ran a round-trip test — toggling the fan switch via HA's service API and confirming the hub state changed and reported back:

```
Fan before: off
Fan after toggle: on
Fan restored: off
```

When I asked how to view the HA UI myself, it noticed the firewall had a default DROP policy and only SSH was open — it added port 8123 with a single `ufw allow` command.

---

## Step 6: Publishing to GitHub

Claude structured the repository for HACS compatibility, wrote all the community files, and squashed the entire development history to a single clean commit before I pushed. Then it fixed the CI failures that followed — without me needing to interpret the error logs myself:

**Round 1 — Missing test dependencies**: `hub.py` imports `websockets` at the module level. Even though tests mock the WebSocket, the import fails if the package isn't installed in CI. Added `websockets>=12.0` and `aiohttp>=3.9` to the test requirements.

**Round 2 — Wrong action version**: During code review, Claude had suggested pinning `hacs/action@main` to `hacs/action@v2` for supply-chain security. Reasonable advice — but `v2` doesn't exist. When I pointed this out, it verified the available tags via the GitHub API before reverting to `@main`.

**Round 3 — Node.js 24 deprecation**: GitHub Actions deprecated Node.js 20 runners, with forced cutover on June 2nd 2026. Claude checked the GitHub API to confirm that `actions/checkout@v6` and `actions/setup-python@v6` (both released January 2026 with explicit Node.js 24 support) actually exist — then upgraded. It used `nektos/act` to run the full CI workflow locally in a matching Docker container and confirmed 65/65 tests passing before pushing.

**Round 4 — Hassfest manifest key ordering**: Claude ran the `ghcr.io/home-assistant/hassfest` Docker container locally (after I asked whether HACS validation could be run offline) and it caught a real error: `manifest.json` keys must be ordered `domain`, `name`, then strictly alphabetical. `issue_tracker` had been listed before `iot_class` — `iot_` sorts before `iss_`. One-line fix.

**Round 5 — HACS brands and topics**: The HACS validation action checks that brand assets exist at `custom_components/ezlo/brand/icon.png`. Claude generated a valid 256×256 PNG icon using only Python's standard library — no PIL or external dependencies — and committed it.

---

## What Claude Built

Starting from a single prompt about a hub that worked with one app and nothing else:

- **Reverse engineered** the Vera Mobile app's local API protocol, TLS cipher requirement, mDNS discovery, and cloud authentication chain — all from decompiled Java bytecode
- **Connected to and authenticated with** the hub's local WebSocket API using credentials obtained entirely through the cloud API chain found in the app
- **Built a complete Home Assistant integration** with switch, lock, cover, and sensor platforms; real-time WebSocket push updates; automatic reconnection; and a config flow that handles the full cloud auth chain transparently
- **Wrote 65 tests** that run without a hub, without Home Assistant, and in under a second
- **Deployed HA Container** locally, automated the onboarding, and verified all 7 entities with live device state
- **Published** to GitHub with CI across three Python versions, HACS validation, community files, and a brand icon

My contribution: the initial prompt, my Vera cloud credentials when asked for them, and the occasional directional decision like "write a native integration instead of MQTT." Claude handled everything else.

The integration is at [github.com/jamincollins/ha-ezlo-hub](https://github.com/jamincollins/ha-ezlo-hub).

If you have an Ezlo Plus hub and want to get it into Home Assistant, install it via HACS (add as a custom repository) or drop the `custom_components/ezlo/` folder into your HA config. You'll need your Vera/Ezlo cloud credentials for the first-time setup — after that, everything runs locally with no cloud dependency.
