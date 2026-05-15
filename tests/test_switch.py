"""Tests for switch.py — in-wall switch entities."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.ezlo.switch import EzloSwitch

# ── helpers ───────────────────────────────────────────────────────────────────


def _make_hub(available=True, reachable=True, item_value=False):
    hub = MagicMock()
    hub.serial = "90030191"
    hub.available = available
    hub.register_callback = MagicMock()
    hub.unregister_callback = MagicMock()
    hub.async_set_item_value = AsyncMock(return_value=True)
    hub.get_item = MagicMock(return_value={"_id": "item-sw", "value": item_value})
    return hub


def _make_device(reachable=True) -> dict:
    return {"_id": "dev-fan", "name": "Fan", "type": "switch.inwall", "reachable": reachable}


def _make_item(value=False) -> dict:
    return {"_id": "item-sw", "deviceId": "dev-fan", "name": "switch", "value": value, "valueType": "bool"}


def _make_switch(item_value=False, hub_available=True, dev_reachable=True) -> EzloSwitch:
    hub = _make_hub(available=hub_available, reachable=dev_reachable, item_value=item_value)
    dev = _make_device(reachable=dev_reachable)
    item = _make_item(value=item_value)
    return EzloSwitch(hub, dev, item)


# ── is_on ─────────────────────────────────────────────────────────────────────


def test_switch_is_on_when_item_value_is_true():
    switch = _make_switch(item_value=True)
    assert switch.is_on is True


def test_switch_is_off_when_item_value_is_false():
    switch = _make_switch(item_value=False)
    assert switch.is_on is False


# ── availability ──────────────────────────────────────────────────────────────


def test_switch_available_when_hub_up_and_device_reachable():
    switch = _make_switch(hub_available=True, dev_reachable=True)
    assert switch.available is True


def test_switch_unavailable_when_hub_not_available():
    switch = _make_switch(hub_available=False)
    assert switch.available is False


def test_switch_unavailable_when_device_not_reachable():
    switch = _make_switch(dev_reachable=False)
    assert switch.available is False


# ── control ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_turn_on_calls_set_item_value_with_true():
    switch = _make_switch()
    await switch.async_turn_on()
    switch._hub.async_set_item_value.assert_called_once_with("item-sw", True)


@pytest.mark.asyncio
async def test_turn_off_calls_set_item_value_with_false():
    switch = _make_switch()
    await switch.async_turn_off()
    switch._hub.async_set_item_value.assert_called_once_with("item-sw", False)


# ── callback-driven state update ──────────────────────────────────────────────


def test_state_refreshed_when_callback_fires_with_matching_item_id():
    switch = _make_switch(item_value=False)
    switch._hub.get_item.return_value = {"_id": "item-sw", "value": True}
    switch.async_write_ha_state = MagicMock()

    switch._on_hub_update("item-sw")

    assert switch.is_on is True
    switch.async_write_ha_state.assert_called_once()


def test_state_refreshed_when_callback_fires_with_none_item_id():
    switch = _make_switch()
    switch.async_write_ha_state = MagicMock()

    switch._on_hub_update(None)

    switch.async_write_ha_state.assert_called_once()


def test_state_not_refreshed_for_different_item_id():
    switch = _make_switch()
    switch.async_write_ha_state = MagicMock()

    switch._on_hub_update("some-other-item-id")

    switch.async_write_ha_state.assert_not_called()
