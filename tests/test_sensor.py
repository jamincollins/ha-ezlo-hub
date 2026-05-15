"""Tests for sensor.py — battery sensors."""
from __future__ import annotations

from unittest.mock import MagicMock

from custom_components.ezlo.sensor import EzloBatteryMaintSensor, EzloBatterySensor

# ── helpers ───────────────────────────────────────────────────────────────────


def _make_hub(available=True, item_value=None):
    hub = MagicMock()
    hub.serial = "90030191"
    hub.available = available
    hub.register_callback = MagicMock()
    hub.unregister_callback = MagicMock()
    hub.get_item = MagicMock(
        return_value={"_id": "item-b", "value": item_value} if item_value is not None else None
    )
    return hub


def _make_battery(value=85, hub_available=True, dev_reachable=True) -> EzloBatterySensor:
    hub = _make_hub(available=hub_available, item_value=value)
    dev = {"_id": "dev-lk", "name": "Lock", "type": "doorlock", "reachable": dev_reachable}
    item = {"_id": "item-b", "deviceId": "dev-lk", "name": "battery", "value": value, "valueType": "int"}
    return EzloBatterySensor(hub, dev, item)


def _make_maint(value="replace_battery_soon") -> EzloBatteryMaintSensor:
    hub = _make_hub(item_value=value)
    dev = {"_id": "dev-lk", "name": "Lock", "type": "doorlock", "reachable": True}
    item = {"_id": "item-bm", "deviceId": "dev-lk", "name": "battery_maintenance_state", "value": value, "valueType": "token"}
    return EzloBatteryMaintSensor(hub, dev, item)


# ── EzloBatterySensor ─────────────────────────────────────────────────────────


def test_battery_native_value_returns_integer():
    sensor = _make_battery(value=87)
    assert sensor.native_value == 87


def test_battery_native_value_returns_none_for_non_numeric():
    sensor = _make_battery(value="unknown")
    sensor._item["value"] = "unknown"
    assert sensor.native_value is None


def test_battery_available_when_hub_up_and_device_reachable():
    sensor = _make_battery(hub_available=True, dev_reachable=True)
    assert sensor.available is True


def test_battery_unavailable_when_hub_down():
    sensor = _make_battery(hub_available=False)
    assert sensor.available is False


def test_battery_unavailable_when_device_not_reachable():
    sensor = _make_battery(dev_reachable=False)
    assert sensor.available is False


def test_battery_state_refreshed_on_matching_callback():
    sensor = _make_battery(value=85)
    sensor._hub.get_item.return_value = {"_id": "item-b", "value": 72}
    sensor.async_write_ha_state = MagicMock()

    sensor._on_hub_update("item-b")

    assert sensor.native_value == 72
    sensor.async_write_ha_state.assert_called_once()


# ── EzloBatteryMaintSensor ────────────────────────────────────────────────────


def test_maint_sensor_converts_snake_case_to_title_case():
    sensor = _make_maint("replace_battery_soon")
    assert sensor.native_value == "Replace Battery Soon"


def test_maint_sensor_converts_single_word():
    sensor = _make_maint("normal")
    sensor._item["value"] = "normal"
    assert sensor.native_value == "Normal"


def test_maint_sensor_returns_none_for_none_value():
    sensor = _make_maint("x")
    sensor._item["value"] = None
    assert sensor.native_value is None


# ── test_init: unsupported devices are logged ─────────────────────────────────


def test_unsupported_device_types_are_logged(caplog):
    """Any device type not in SUPPORTED_DEVICE_TYPES must produce an INFO log."""
    import logging
    from unittest.mock import MagicMock

    from custom_components.ezlo.const import SUPPORTED_DEVICE_TYPES

    unknown_dev = {
        "_id": "dev-unk",
        "name": "Mystery Sensor",
        "type": "sensor.mystery",
        "reachable": True,
    }
    assert unknown_dev["type"] not in SUPPORTED_DEVICE_TYPES, (
        "Test pre-condition: sensor.mystery must not be a supported type"
    )

    hub = MagicMock()
    hub.devices = [unknown_dev]
    hub.get_items_for_device = MagicMock(return_value=[])

    with caplog.at_level(logging.INFO, logger="custom_components.ezlo"):
        from custom_components.ezlo import _log_unsupported_devices
        _log_unsupported_devices(hub)

    assert any(
        "sensor.mystery" in r.message and "Mystery Sensor" in r.message
        for r in caplog.records
    ), "Expected an INFO log mentioning the unsupported device type and name"
