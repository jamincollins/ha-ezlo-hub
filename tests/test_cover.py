"""Tests for cover.py — garage door entities."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.ezlo.cover import EzloCover

# ── helpers ───────────────────────────────────────────────────────────────────


def _make_hub(available=True, items=None):
    hub = MagicMock()
    hub.serial = "90030191"
    hub.available = available
    hub.register_callback = MagicMock()
    hub.unregister_callback = MagicMock()
    hub.async_set_item_value = AsyncMock(return_value=True)
    hub._devices = {}
    hub.get_items_for_device = MagicMock(return_value=items or [])
    hub.find_item = MagicMock(return_value=None)
    hub.get_item = MagicMock(side_effect=lambda iid: next(
        (i for i in (items or []) if i["_id"] == iid), None
    ))
    return hub


def _make_garage(
    reachable=False, item_value=None, item_name="garage_door", value_type="token",
    hub_available=True,
) -> EzloCover:
    items = []
    if item_value is not None:
        items = [
            {"_id": "item-gd", "deviceId": "dev-gr", "name": item_name,
             "value": item_value, "valueType": value_type}
        ]
    hub = _make_hub(available=hub_available, items=items)

    if items:
        hub.find_item = MagicMock(return_value=items[0])

    dev = {
        "_id": "dev-gr",
        "name": "Garage Door",
        "type": "shutter.garage",
        "reachable": reachable,
        "info": {"manufacturer": "Linear", "model": "GD00Z-5"},
    }
    hub._devices["dev-gr"] = dev
    return EzloCover(hub, dev)


# ── availability ──────────────────────────────────────────────────────────────


def test_cover_unavailable_when_device_not_reachable():
    cover = _make_garage(reachable=False)
    assert cover.available is False


def test_cover_available_when_hub_up_and_device_reachable():
    cover = _make_garage(reachable=True, item_value="closed")
    assert cover.available is True


def test_cover_unavailable_when_hub_not_available():
    cover = _make_garage(reachable=True, hub_available=False, item_value="closed")
    assert cover.available is False


# ── is_closed ────────────────────────────────────────────────────────────────


def test_cover_is_closed_when_value_is_closed_token():
    cover = _make_garage(reachable=True, item_value="closed")
    cover._item = cover._hub.find_item.return_value
    assert cover.is_closed is True


def test_cover_is_open_when_value_is_open_token():
    cover = _make_garage(reachable=True, item_value="open")
    cover._item = cover._hub.find_item.return_value
    assert cover.is_closed is False


def test_cover_is_closed_when_bool_value_is_false():
    cover = _make_garage(reachable=True, item_value=False, value_type="bool")
    cover._item = cover._hub.find_item.return_value
    assert cover.is_closed is True


def test_cover_is_open_when_bool_value_is_true():
    cover = _make_garage(reachable=True, item_value=True, value_type="bool")
    cover._item = cover._hub.find_item.return_value
    assert cover.is_closed is False


def test_cover_is_none_when_no_item_found():
    cover = _make_garage(reachable=True)  # no item_value → no item
    cover._item = None
    assert cover.is_closed is None


# ── control ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_open_cover_sends_open_token_for_token_item():
    cover = _make_garage(reachable=True, item_value="closed")
    cover._item = cover._hub.find_item.return_value
    await cover.async_open_cover()
    cover._hub.async_set_item_value.assert_called_once_with("item-gd", "open")


@pytest.mark.asyncio
async def test_close_cover_sends_closed_token_for_token_item():
    cover = _make_garage(reachable=True, item_value="open")
    cover._item = cover._hub.find_item.return_value
    await cover.async_close_cover()
    cover._hub.async_set_item_value.assert_called_once_with("item-gd", "closed")


@pytest.mark.asyncio
async def test_open_cover_sends_true_for_bool_item():
    cover = _make_garage(reachable=True, item_value=False, value_type="bool")
    cover._item = cover._hub.find_item.return_value
    await cover.async_open_cover()
    cover._hub.async_set_item_value.assert_called_once_with("item-gd", True)


@pytest.mark.asyncio
async def test_open_cover_does_nothing_when_no_item():
    cover = _make_garage(reachable=True)
    cover._item = None
    await cover.async_open_cover()
    cover._hub.async_set_item_value.assert_not_called()


# ── callback-driven state update ──────────────────────────────────────────────


def test_state_refreshed_when_item_id_matches():
    cover = _make_garage(reachable=True, item_value="closed")
    cover._item = cover._hub.find_item.return_value
    cover.async_write_ha_state = MagicMock()
    updated = {"_id": "item-gd", "value": "open", "valueType": "token"}
    cover._hub.get_item.return_value = updated

    cover._on_hub_update("item-gd")

    cover.async_write_ha_state.assert_called_once()
