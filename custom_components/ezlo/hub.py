"""Ezlo hub WebSocket client and Vera/Ezlo cloud authentication."""
from __future__ import annotations

import asyncio
import base64
import contextlib
import hashlib
import json
import logging
import ssl
from typing import Any, Callable

import aiohttp
import websockets
import websockets.exceptions

from .const import (
    ACCESS_KEYS_URL,
    HUB_PORT,
    HUB_TLS_CIPHER,
    JWT_EXCHANGE_URL,
    PING_INTERVAL,
    RECONNECT_DELAY,
    REQUEST_TIMEOUT,
    VERA_AUTH_URL,
    VERA_AUTH_URL_ALT,
    VERA_SHA1_SALT,
)

_LOGGER = logging.getLogger(__name__)


def _make_ssl_context() -> ssl.SSLContext:
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    # The hub only accepts this cipher (ARM hardware constraint).
    ctx.set_ciphers(HUB_TLS_CIPHER)
    return ctx


async def async_get_hub_info(host: str) -> dict | None:
    """
    Connect to the hub and return hub.info.get result.

    No authentication is required for this call — the hub responds to
    hub.info.get before login, which lets the config flow discover the
    hub serial and UUID before fetching cloud credentials.

    Returns None on any failure.
    """
    ctx = _make_ssl_context()
    ws = None
    try:
        ws = await asyncio.wait_for(
            websockets.connect(f"wss://{host}:{HUB_PORT}", ssl=ctx, open_timeout=10),
            timeout=15,
        )
        await ws.send(json.dumps({"id": "info", "method": "hub.info.get", "params": {}}))
        while True:
            raw = await asyncio.wait_for(ws.recv(), timeout=REQUEST_TIMEOUT)
            msg = json.loads(raw)
            if msg.get("id") == "info":
                if msg.get("error"):
                    return None
                return msg.get("result")
    except Exception as err:
        _LOGGER.debug("hub.info.get failed for %s: %s", host, err)
        return None
    finally:
        if ws is not None:
            with contextlib.suppress(Exception):
                await ws.close()


async def async_get_hub_credentials(
    session: aiohttp.ClientSession,
    username: str,
    password: str,
    hub_uuid: str,
) -> dict[str, str] | None:
    """
    Authenticate with the Vera/Ezlo cloud and return local hub credentials.

    The function performs the full cloud auth chain:
      1. SHA-1-salted password → Vera MIOS auth (Identity + IdentitySignature)
      2. Legacy token → JWT via cloud.ezlo.com token exchange
      3. JWT → access_keys_sync call to api-cloud.ezlo.com
      4. Extract the user UUID and local token for the specific hub UUID

    Returns ``{"user": <uuid>, "token": <string>}`` or None on failure.
    """
    sha1_pass = hashlib.sha1(
        f"{username.lower()}{password}{VERA_SHA1_SALT}".encode()
    ).hexdigest()

    # Step 1: MIOS cloud auth — try primary then alternate server
    auth_data: dict | None = None
    for url_tpl in (VERA_AUTH_URL, VERA_AUTH_URL_ALT):
        try:
            async with session.get(
                url_tpl.format(username),
                params={"SHA1Password": sha1_pass, "PK_Oem": "1", "TokenVersion": "2"},
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                if resp.status == 200:
                    auth_data = await resp.json(content_type=None)
                    break
        except Exception as err:
            _LOGGER.debug("Auth server %s error: %s", url_tpl, err)

    if not auth_data:
        _LOGGER.error("Cloud authentication failed for user '%s'", username)
        return None

    identity = auth_data.get("Identity")
    identity_sig = auth_data.get("IdentitySignature")
    if not identity or not identity_sig:
        _LOGGER.error("No Identity in auth response")
        return None

    # Decode PK_User from the base64-encoded Identity JSON blob
    try:
        padded = identity + "=" * (-len(identity) % 4)
        id_decoded = json.loads(base64.b64decode(padded))
        pk_user = str(id_decoded["PK_User"])
    except Exception as err:
        _LOGGER.error("Failed to decode Identity: %s", err)
        return None

    # Step 2: Exchange legacy token for JWT
    try:
        async with session.get(
            JWT_EXCHANGE_URL,
            params={"pk_user": pk_user},
            headers={"MMSAuth": identity, "MMSAuthSig": identity_sig},
            timeout=aiohttp.ClientTimeout(total=20),
        ) as resp:
            if resp.status != 200:
                _LOGGER.error("JWT exchange returned HTTP %s", resp.status)
                return None
            jwt_token: str | None = (await resp.json(content_type=None)).get("token")
    except Exception as err:
        _LOGGER.error("JWT exchange error: %s", err)
        return None

    if not jwt_token:
        _LOGGER.error("No JWT token in exchange response")
        return None

    # Step 3: Fetch access keys for all hubs
    try:
        async with session.post(
            ACCESS_KEYS_URL,
            json={"call": "access_keys_sync", "params": {"version": -1}},
            headers={"Authorization": f"Bearer {jwt_token}"},
            timeout=aiohttp.ClientTimeout(total=20),
        ) as resp:
            keys_resp = await resp.json(content_type=None)
    except Exception as err:
        _LOGGER.error("Access keys fetch error: %s", err)
        return None

    if keys_resp.get("status") != 1:
        _LOGGER.error("access_keys_sync failed: %s", keys_resp.get("data"))
        return None

    # Step 4: Find the string token for our specific hub UUID
    for key_data in keys_resp.get("data", {}).get("keys", {}).values():
        meta = key_data.get("meta", {})
        target = meta.get("target", {})
        entity = meta.get("entity", {})
        data = key_data.get("data", {})

        if (
            target.get("type") == "controller"
            and target.get("uuid") == hub_uuid
            and entity.get("type") == "user"
            and data.get("type") == "string"
        ):
            return {"user": entity["uuid"], "token": data["string"]}

    _LOGGER.error("No access key found for hub UUID %s", hub_uuid)
    return None


class EzloHub:
    """
    Manages a local WebSocket connection to an Ezlo hub.

    Handles authentication, device/item discovery, real-time broadcasts, and
    automatic reconnection.  Entities register callbacks here; the hub fires
    them with the changed item_id (or None for availability changes).
    """

    def __init__(
        self,
        host: str,
        user: str,
        token: str,
        hub_serial: str,
        hub_uuid: str,
    ) -> None:
        self.host = host
        self.user = user
        self.token = token
        self.serial = hub_serial
        self.uuid = hub_uuid

        self._ssl_ctx = _make_ssl_context()
        self._ws: Any = None
        self._devices: dict[str, dict] = {}
        self._items: dict[str, dict] = {}
        self._device_items: dict[str, list[str]] = {}
        self._callbacks: list[Callable[[str | None], None]] = []
        self._req_counter = 0
        self._pending: dict[str, asyncio.Future] = {}
        self._listen_task: asyncio.Task | None = None
        self.available = False

    # ── Public interface ─────────────────────────────────────────────────────

    def register_callback(self, cb: Callable[[str | None], None]) -> None:
        """Register a callback fired when any item changes or availability changes."""
        self._callbacks.append(cb)

    def unregister_callback(self, cb: Callable[[str | None], None]) -> None:
        if cb in self._callbacks:
            self._callbacks.remove(cb)

    @property
    def devices(self) -> list[dict]:
        return list(self._devices.values())

    def get_item(self, item_id: str) -> dict | None:
        return self._items.get(item_id)

    def get_items_for_device(self, device_id: str) -> list[dict]:
        return [
            self._items[i]
            for i in self._device_items.get(device_id, [])
            if i in self._items
        ]

    def find_item(self, device_id: str, item_name: str) -> dict | None:
        """Return the first item on *device_id* whose name equals *item_name*."""
        for item in self.get_items_for_device(device_id):
            if item.get("name") == item_name:
                return item
        return None

    async def async_set_item_value(self, item_id: str, value: Any) -> bool:
        resp = await self._send("hub.item.value.set", {"_id": item_id, "value": value})
        if resp is None or resp.get("error"):
            _LOGGER.error("hub.item.value.set failed for item %s: %s", item_id, resp)
            return False
        # Optimistic local update so entities reflect the change immediately.
        if item_id in self._items:
            self._items[item_id]["value"] = value
        return True

    # ── Lifecycle ────────────────────────────────────────────────────────────

    async def async_setup(self) -> bool:
        """Connect, authenticate, and start the background listener."""
        ok = await self._connect_and_load()
        if ok:
            self._listen_task = asyncio.create_task(self._listen_loop())
        return ok

    async def async_teardown(self) -> None:
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
        if self._ws:
            await self._ws.close()

    # ── Internal ─────────────────────────────────────────────────────────────

    async def _connect_and_load(self) -> bool:
        try:
            self._ws = await asyncio.wait_for(
                websockets.connect(
                    f"wss://{self.host}:{HUB_PORT}",
                    ssl=self._ssl_ctx,
                    open_timeout=10,
                ),
                timeout=15,
            )
        except Exception as err:
            _LOGGER.error("Cannot connect to hub %s: %s", self.serial, err)
            return False

        login = await self._send(
            "hub.offline.login.ui", {"user": self.user, "token": self.token}
        )
        if login is None or login.get("error"):
            _LOGGER.error("Hub authentication failed for %s: %s", self.serial, login)
            return False

        await self._load_devices()
        await self._load_items()
        self.available = True
        return True

    async def _load_devices(self) -> None:
        resp = await self._send("hub.devices.list", {})
        if resp and not resp.get("error"):
            for dev in resp.get("result", {}).get("devices", []):
                self._devices[dev["_id"]] = dev
                self._device_items.setdefault(dev["_id"], [])

    async def _load_items(self) -> None:
        resp = await self._send("hub.items.list", {})
        if resp and not resp.get("error"):
            for item in resp.get("result", {}).get("items", []):
                item_id = item["_id"]
                dev_id = item.get("deviceId", "")
                self._items[item_id] = item
                lst = self._device_items.setdefault(dev_id, [])
                if item_id not in lst:
                    lst.append(item_id)

    async def _send(self, method: str, params: dict) -> dict | None:
        if self._ws is None:
            return None
        self._req_counter += 1
        req_id = f"ha{self._req_counter}"
        try:
            await self._ws.send(
                json.dumps({"id": req_id, "method": method, "params": params})
            )
            # During initial setup the background listener isn't running yet,
            # so read responses directly from the socket.
            if self._listen_task is None or self._listen_task.done():
                deadline = asyncio.get_running_loop().time() + REQUEST_TIMEOUT
                while True:
                    remaining = deadline - asyncio.get_running_loop().time()
                    if remaining <= 0:
                        _LOGGER.warning("Request timed out: %s", method)
                        return None
                    raw = await asyncio.wait_for(self._ws.recv(), timeout=remaining)
                    msg = json.loads(raw)
                    if msg.get("id") == req_id:
                        return msg
                    await self._dispatch(msg)
            else:
                fut: asyncio.Future = asyncio.get_running_loop().create_future()
                self._pending[req_id] = fut
                try:
                    return await asyncio.wait_for(
                        asyncio.shield(fut), timeout=REQUEST_TIMEOUT
                    )
                finally:
                    self._pending.pop(req_id, None)
        except asyncio.TimeoutError:
            _LOGGER.warning("Request timed out: %s", method)
            return None
        except Exception as err:
            _LOGGER.error("Send error (%s): %s", method, err)
            return None

    async def _listen_loop(self) -> None:
        while True:
            if self._ws is None:
                await self._reconnect()
                continue
            try:
                raw = await asyncio.wait_for(
                    self._ws.recv(), timeout=PING_INTERVAL + 30
                )
                await self._dispatch(json.loads(raw))
            except asyncio.TimeoutError:
                try:
                    await asyncio.wait_for(self._ws.ping(), timeout=10)
                except Exception:
                    _LOGGER.warning("Hub %s ping failed — reconnecting", self.serial)
                    self.available = False
                    self._fire_callbacks(None)
                    await self._reconnect()
            except websockets.exceptions.ConnectionClosed:
                _LOGGER.warning("Hub %s connection closed — reconnecting", self.serial)
                self.available = False
                self._fire_callbacks(None)
                await self._reconnect()
            except asyncio.CancelledError:
                return
            except Exception as err:
                _LOGGER.error("Listen error: %s", err)
                await asyncio.sleep(1)

    async def _dispatch(self, msg: dict) -> None:
        msg_id = msg.get("id", "")
        if msg_id in self._pending:
            if not self._pending[msg_id].done():
                self._pending[msg_id].set_result(msg)
        elif msg_id == "ui_broadcast":
            self._handle_broadcast(msg)

    def _handle_broadcast(self, msg: dict) -> None:
        subclass = msg.get("msg_subclass", "")
        result = msg.get("result", {})

        if subclass == "hub.item.updated":
            item_id = result.get("_id")
            if item_id and item_id in self._items:
                self._items[item_id]["value"] = result.get("value")
                self._fire_callbacks(item_id)
        elif subclass in ("hub.device.updated", "hub.devices.updated"):
            dev_id = result.get("_id")
            if dev_id and dev_id in self._devices:
                self._devices[dev_id].update(result)
                for item_id in self._device_items.get(dev_id, []):
                    self._fire_callbacks(item_id)
        else:
            _LOGGER.debug("Unhandled broadcast subclass: %s", subclass)

    def _fire_callbacks(self, item_id: str | None) -> None:
        for cb in self._callbacks:
            try:
                cb(item_id)
            except Exception as err:
                _LOGGER.error("Callback error: %s", err)

    async def _reconnect(self) -> None:
        _LOGGER.info("Reconnecting to hub %s in %ss…", self.serial, RECONNECT_DELAY)
        await asyncio.sleep(RECONNECT_DELAY)
        try:
            ok = await self._connect_and_load()
            if ok:
                _LOGGER.info("Reconnected to hub %s", self.serial)
                self._fire_callbacks(None)
        except Exception as err:
            _LOGGER.error("Reconnect error: %s", err)
