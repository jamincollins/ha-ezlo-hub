"""Tests for lock.py — door lock entities."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.ezlo.lock import EzloLock

# ── helpers ───────────────────────────────────────────────────────────────────


def _make_hub(available=True, item_value="secured"):
    hub = MagicMock()
    hub.serial = "90030191"
    hub.available = available
    hub.register_callback = MagicMock()
    hub.unregister_callback = MagicMock()
    hub.async_set_item_value = AsyncMock(return_value=True)
    hub.get_item = MagicMock(return_value={"_id": "item-lk", "value": item_value})
    return hub


def _make_lock(lock_value="secured", hub_available=True, dev_reachable=True) -> EzloLock:
    hub = _make_hub(available=hub_available, item_value=lock_value)
    dev = {"_id": "dev-lk", "name": "Front Door", "type": "doorlock", "reachable": dev_reachable}
    item = {"_id": "item-lk", "deviceId": "dev-lk", "name": "door_lock", "value": lock_value, "valueType": "token"}
    return EzloLock(hub, dev, item)


# ── is_locked ─────────────────────────────────────────────────────────────────


def test_lock_is_locked_when_value_is_secured():
    lock = _make_lock("secured")
    assert lock.is_locked is True


def test_lock_is_unlocked_when_value_is_unsecured():
    lock = _make_lock("unsecured")
    assert lock.is_locked is False


def test_lock_returns_none_for_unknown_value():
    lock = _make_lock("unknown_state")
    assert lock.is_locked is None


# ── availability ──────────────────────────────────────────────────────────────


def test_lock_available_when_hub_up_and_device_reachable():
    lock = _make_lock(hub_available=True, dev_reachable=True)
    assert lock.available is True


def test_lock_unavailable_when_hub_not_available():
    lock = _make_lock(hub_available=False)
    assert lock.available is False


def test_lock_unavailable_when_device_not_reachable():
    lock = _make_lock(dev_reachable=False)
    assert lock.available is False


# ── control ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_locking_sends_secured_value():
    lock = _make_lock("unsecured")
    await lock.async_lock()
    lock._hub.async_set_item_value.assert_called_once_with("item-lk", "secured")


@pytest.mark.asyncio
async def test_unlocking_sends_unsecured_value():
    lock = _make_lock("secured")
    await lock.async_unlock()
    lock._hub.async_set_item_value.assert_called_once_with("item-lk", "unsecured")


# ── callback-driven state update ──────────────────────────────────────────────


def test_state_refreshed_when_matching_item_id_fires():
    lock = _make_lock("secured")
    lock._hub.get_item.return_value = {"_id": "item-lk", "value": "unsecured"}
    lock.async_write_ha_state = MagicMock()

    lock._on_hub_update("item-lk")

    assert lock.is_locked is False
    lock.async_write_ha_state.assert_called_once()


def test_state_not_refreshed_for_unrelated_item_id():
    lock = _make_lock("secured")
    lock.async_write_ha_state = MagicMock()

    lock._on_hub_update("other-item")

    lock.async_write_ha_state.assert_not_called()
