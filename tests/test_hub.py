"""Tests for hub.py — WebSocket client and cloud authentication."""
from __future__ import annotations

import base64
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ezlo.hub import EzloHub, async_get_hub_credentials, async_get_hub_info

# ── helpers ──────────────────────────────────────────────────────────────────


def make_ws(*responses: dict) -> AsyncMock:
    """WebSocket mock that returns `responses` in sequence from recv()."""
    ws = AsyncMock()
    ws.send = AsyncMock()
    ws.ping = AsyncMock()
    ws.close = AsyncMock()
    ws.recv = AsyncMock(side_effect=[json.dumps(r) for r in responses])
    return ws


def _b64(data: dict) -> str:
    return base64.b64encode(json.dumps(data).encode()).decode().rstrip("=")


HUB_INFO_RESULT = {
    "serial": "90030191",
    "uuid": "36ff2a40-3081-11ed-a4cd-0d1e06747a2f",
    "firmware": "2.0.90.3265.5",
}

SAMPLE_DEVICES = [
    {"_id": "dev-fan", "name": "Fan", "type": "switch.inwall", "reachable": True},
    {"_id": "dev-lock", "name": "Lock", "type": "doorlock", "reachable": True},
]

SAMPLE_ITEMS = [
    {"_id": "item-sw", "deviceId": "dev-fan", "name": "switch", "value": False, "valueType": "bool"},
    {"_id": "item-lk", "deviceId": "dev-lock", "name": "door_lock", "value": "secured", "valueType": "token"},
    {"_id": "item-bt", "deviceId": "dev-lock", "name": "battery", "value": 85, "valueType": "int"},
]


# ── async_get_hub_info ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_hub_info_returns_serial_and_uuid():
    ws = make_ws({"id": "info", "result": HUB_INFO_RESULT, "error": None})

    async def fake_connect(*a, **kw):
        return ws

    with patch("custom_components.ezlo.hub.websockets.connect", side_effect=fake_connect):
        result = await async_get_hub_info("192.168.10.1")

    assert result["serial"] == "90030191"
    assert result["uuid"] == "36ff2a40-3081-11ed-a4cd-0d1e06747a2f"


@pytest.mark.asyncio
async def test_get_hub_info_returns_none_on_connection_failure():
    with patch(
        "custom_components.ezlo.hub.websockets.connect",
        side_effect=OSError("refused"),
    ):
        result = await async_get_hub_info("192.168.10.1")

    assert result is None


@pytest.mark.asyncio
async def test_get_hub_info_returns_none_when_hub_replies_with_error():
    ws = make_ws({"id": "info", "error": {"code": -1, "message": "auth"}, "result": None})

    async def fake_connect(*a, **kw):
        return ws

    with patch("custom_components.ezlo.hub.websockets.connect", side_effect=fake_connect):
        result = await async_get_hub_info("192.168.10.1")

    assert result is None


# ── async_get_hub_credentials ─────────────────────────────────────────────────


def _make_session(
    auth_status=200,
    auth_body=None,
    jwt_status=200,
    jwt_body=None,
    keys_status=200,
    keys_body=None,
):
    identity_payload = _b64({"PK_User": 1818411, "PK_Account": 584991})
    auth_body = auth_body or {
        "Identity": identity_payload,
        "IdentitySignature": "sig123",
        "Server_Account": "vera-account.mios.com",
    }
    jwt_body = jwt_body or {"token": "jwt-token-abc"}
    keys_body = keys_body or {
        "status": 1,
        "data": {
            "keys": {
                "key-1": {
                    "data": {"type": "string", "string": "local-token-xyz"},
                    "meta": {
                        "entity": {"type": "user", "uuid": "user-uuid-111"},
                        "target": {
                            "type": "controller",
                            "uuid": "36ff2a40-3081-11ed-a4cd-0d1e06747a2f",
                        },
                    },
                }
            }
        },
    }

    def _response(status, body):
        r = AsyncMock()
        r.status = status
        r.json = AsyncMock(return_value=body)
        cm = AsyncMock()
        cm.__aenter__ = AsyncMock(return_value=r)
        cm.__aexit__ = AsyncMock(return_value=False)
        return cm

    session = MagicMock()
    session.get = MagicMock(
        side_effect=[_response(auth_status, auth_body), _response(jwt_status, jwt_body)]
    )
    session.post = MagicMock(return_value=_response(keys_status, keys_body))
    return session


@pytest.mark.asyncio
async def test_get_hub_credentials_returns_user_and_token_for_hub():
    session = _make_session()
    creds = await async_get_hub_credentials(
        session, "user@example.com", "password", "36ff2a40-3081-11ed-a4cd-0d1e06747a2f"
    )
    assert creds == {"user": "user-uuid-111", "token": "local-token-xyz"}


@pytest.mark.asyncio
async def test_get_hub_credentials_returns_none_when_auth_fails():
    session = _make_session(auth_status=404, auth_body={})
    creds = await async_get_hub_credentials(
        session, "bad_user", "wrong_pass", "any-uuid"
    )
    assert creds is None


@pytest.mark.asyncio
async def test_get_hub_credentials_returns_none_when_no_identity_in_response():
    session = _make_session(auth_body={"Server_Account": "s"})  # no Identity key
    creds = await async_get_hub_credentials(session, "u", "p", "uuid")
    assert creds is None


@pytest.mark.asyncio
async def test_get_hub_credentials_returns_none_when_jwt_exchange_fails():
    session = _make_session(jwt_status=500, jwt_body={})
    creds = await async_get_hub_credentials(session, "u", "p", "uuid")
    assert creds is None


@pytest.mark.asyncio
async def test_get_hub_credentials_returns_none_when_hub_uuid_not_in_keys():
    session = _make_session(
        keys_body={
            "status": 1,
            "data": {
                "keys": {
                    "k1": {
                        "data": {"type": "string", "string": "tok"},
                        "meta": {
                            "entity": {"type": "user", "uuid": "u1"},
                            "target": {"type": "controller", "uuid": "different-uuid"},
                        },
                    }
                }
            },
        }
    )
    creds = await async_get_hub_credentials(
        session, "u", "p", "36ff2a40-3081-11ed-a4cd-0d1e06747a2f"
    )
    assert creds is None


# ── EzloHub._connect_and_load ─────────────────────────────────────────────────


def _load_responses(serial: str = "90030191") -> list[dict]:
    """Minimal responses for a successful _connect_and_load."""
    return [
        {"id": "ha1", "result": {}, "error": None},  # login
        {"id": "ha2", "result": {"devices": SAMPLE_DEVICES}, "error": None},
        {"id": "ha3", "result": {"items": SAMPLE_ITEMS}, "error": None},
    ]


def _make_hub(**kwargs) -> EzloHub:
    defaults = dict(
        host="192.168.10.1",
        user="user-uuid",
        token="token-value",
        hub_serial="90030191",
        hub_uuid="hub-uuid",
    )
    defaults.update(kwargs)
    return EzloHub(**defaults)


@pytest.mark.asyncio
async def test_hub_connect_and_load_sets_available_true():
    ws = make_ws(*_load_responses())

    async def fake_connect(*a, **kw):
        return ws

    hub = _make_hub()
    with patch("custom_components.ezlo.hub.websockets.connect", side_effect=fake_connect):
        ok = await hub._connect_and_load()

    assert ok is True
    assert hub.available is True


@pytest.mark.asyncio
async def test_hub_connect_and_load_populates_devices_and_items():
    ws = make_ws(*_load_responses())

    async def fake_connect(*a, **kw):
        return ws

    hub = _make_hub()
    with patch("custom_components.ezlo.hub.websockets.connect", side_effect=fake_connect):
        await hub._connect_and_load()

    assert len(hub.devices) == 2
    assert hub.find_item("dev-fan", "switch") is not None
    assert hub.find_item("dev-lock", "door_lock") is not None
    assert hub.find_item("dev-lock", "battery") is not None


@pytest.mark.asyncio
async def test_hub_connect_and_load_returns_false_on_connection_error():
    hub = _make_hub()
    with patch(
        "custom_components.ezlo.hub.websockets.connect",
        side_effect=OSError("refused"),
    ):
        ok = await hub._connect_and_load()

    assert ok is False
    assert hub.available is False


@pytest.mark.asyncio
async def test_hub_connect_and_load_returns_false_when_auth_rejected():
    ws = make_ws({"id": "ha1", "error": {"code": -1, "message": "bad token"}, "result": None})

    async def fake_connect(*a, **kw):
        return ws

    hub = _make_hub()
    with patch("custom_components.ezlo.hub.websockets.connect", side_effect=fake_connect):
        ok = await hub._connect_and_load()

    assert ok is False


# ── EzloHub.find_item ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_find_item_returns_correct_item():
    ws = make_ws(*_load_responses())

    async def fake_connect(*a, **kw):
        return ws

    hub = _make_hub()
    with patch("custom_components.ezlo.hub.websockets.connect", side_effect=fake_connect):
        await hub._connect_and_load()

    item = hub.find_item("dev-lock", "battery")
    assert item is not None
    assert item["value"] == 85


@pytest.mark.asyncio
async def test_find_item_returns_none_for_missing_name():
    ws = make_ws(*_load_responses())

    async def fake_connect(*a, **kw):
        return ws

    hub = _make_hub()
    with patch("custom_components.ezlo.hub.websockets.connect", side_effect=fake_connect):
        await hub._connect_and_load()

    assert hub.find_item("dev-fan", "nonexistent") is None


# ── EzloHub.async_set_item_value ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_set_item_value_sends_correct_command():
    responses = _load_responses() + [
        {"id": "ha4", "result": {}, "error": None}
    ]
    ws = make_ws(*responses)

    async def fake_connect(*a, **kw):
        return ws

    hub = _make_hub()
    with patch("custom_components.ezlo.hub.websockets.connect", side_effect=fake_connect):
        await hub._connect_and_load()
        ok = await hub.async_set_item_value("item-sw", True)

    assert ok is True
    # Confirm the correct JSON was sent (the 4th send call)
    sent = json.loads(ws.send.call_args_list[3][0][0])
    assert sent["method"] == "hub.item.value.set"
    assert sent["params"] == {"_id": "item-sw", "value": True}


@pytest.mark.asyncio
async def test_set_item_value_updates_local_cache():
    responses = _load_responses() + [{"id": "ha4", "result": {}, "error": None}]
    ws = make_ws(*responses)

    async def fake_connect(*a, **kw):
        return ws

    hub = _make_hub()
    with patch("custom_components.ezlo.hub.websockets.connect", side_effect=fake_connect):
        await hub._connect_and_load()
        await hub.async_set_item_value("item-sw", True)

    assert hub.get_item("item-sw")["value"] is True


@pytest.mark.asyncio
async def test_set_item_value_returns_false_on_hub_error():
    responses = _load_responses() + [
        {"id": "ha4", "error": {"code": -1, "message": "fail"}, "result": None}
    ]
    ws = make_ws(*responses)

    async def fake_connect(*a, **kw):
        return ws

    hub = _make_hub()
    with patch("custom_components.ezlo.hub.websockets.connect", side_effect=fake_connect):
        await hub._connect_and_load()
        ok = await hub.async_set_item_value("item-sw", True)

    assert ok is False


# ── EzloHub broadcast dispatch ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_broadcast_item_updated_fires_callback_with_item_id():
    ws = make_ws(*_load_responses())

    async def fake_connect(*a, **kw):
        return ws

    hub = _make_hub()
    with patch("custom_components.ezlo.hub.websockets.connect", side_effect=fake_connect):
        await hub._connect_and_load()

    fired: list[str | None] = []
    hub.register_callback(fired.append)

    broadcast = {
        "id": "ui_broadcast",
        "msg_subclass": "hub.item.updated",
        "result": {"_id": "item-sw", "deviceId": "dev-fan", "value": True},
    }
    await hub._dispatch(broadcast)

    assert fired == ["item-sw"]


@pytest.mark.asyncio
async def test_broadcast_item_updated_updates_item_value_in_cache():
    ws = make_ws(*_load_responses())

    async def fake_connect(*a, **kw):
        return ws

    hub = _make_hub()
    with patch("custom_components.ezlo.hub.websockets.connect", side_effect=fake_connect):
        await hub._connect_and_load()

    assert hub.get_item("item-sw")["value"] is False

    await hub._dispatch({
        "id": "ui_broadcast",
        "msg_subclass": "hub.item.updated",
        "result": {"_id": "item-sw", "value": True},
    })

    assert hub.get_item("item-sw")["value"] is True


@pytest.mark.asyncio
async def test_broadcast_fires_none_callback_for_availability_change():
    ws = make_ws(*_load_responses())

    async def fake_connect(*a, **kw):
        return ws

    hub = _make_hub()
    with patch("custom_components.ezlo.hub.websockets.connect", side_effect=fake_connect):
        await hub._connect_and_load()

    fired: list[str | None] = []
    hub.register_callback(fired.append)

    hub._fire_callbacks(None)

    assert fired == [None]


@pytest.mark.asyncio
async def test_unknown_broadcast_subclass_does_not_raise():
    ws = make_ws(*_load_responses())

    async def fake_connect(*a, **kw):
        return ws

    hub = _make_hub()
    with patch("custom_components.ezlo.hub.websockets.connect", side_effect=fake_connect):
        await hub._connect_and_load()

    # Must not raise even for an unrecognized subclass
    await hub._dispatch({
        "id": "ui_broadcast",
        "msg_subclass": "hub.new.thing",
        "result": {"some": "data"},
    })


# ── EzloHub callback registration ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_unregister_callback_stops_future_calls():
    ws = make_ws(*_load_responses())

    async def fake_connect(*a, **kw):
        return ws

    hub = _make_hub()
    with patch("custom_components.ezlo.hub.websockets.connect", side_effect=fake_connect):
        await hub._connect_and_load()

    fired: list = []
    hub.register_callback(fired.append)
    hub._fire_callbacks("item-sw")
    hub.unregister_callback(fired.append)
    hub._fire_callbacks("item-sw")

    assert len(fired) == 1
