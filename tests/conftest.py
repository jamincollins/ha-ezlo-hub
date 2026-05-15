"""
Shared fixtures and HA module stubs.

homeassistant is not installed in the test environment; we stub the parts
our code imports so tests remain runnable with only the packages in
requirements_test.txt.
"""
from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock

import pytest  # noqa: E402

# ── HA module stubs (built before any integration code is imported) ──────────

def _stub(name: str, **attrs) -> ModuleType:
    m = ModuleType(name)
    for k, v in attrs.items():
        setattr(m, k, v)
    sys.modules[name] = m
    return m


class _SwitchEntity:
    async_write_ha_state = MagicMock()
    _attr_unique_id: str = ""
    _attr_device_info: object = None
    _attr_has_entity_name: bool = False
    _attr_name: str | None = None


class _LockEntity(_SwitchEntity):
    pass


class _CoverEntity(_SwitchEntity):
    pass


class _SensorEntity(_SwitchEntity):
    _attr_native_unit_of_measurement: str | None = None
    _attr_device_class: object = None
    _attr_state_class: object = None
    _attr_entity_category: object = None


# Platform enum
_Platform = MagicMock()
_Platform.SWITCH = "switch"
_Platform.LOCK = "lock"
_Platform.COVER = "cover"
_Platform.SENSOR = "sensor"

_CoverDeviceClass = MagicMock()
_CoverDeviceClass.GARAGE = "garage"
_CoverEntityFeature = MagicMock()
_CoverEntityFeature.OPEN = 1
_CoverEntityFeature.CLOSE = 2

_SensorDeviceClass = MagicMock()
_SensorDeviceClass.BATTERY = "battery"
_SensorStateClass = MagicMock()
_SensorStateClass.MEASUREMENT = "measurement"
_EntityCategory = MagicMock()
_EntityCategory.DIAGNOSTIC = "diagnostic"

_stub("homeassistant")
_stub("homeassistant.core", HomeAssistant=MagicMock, callback=lambda f: f)
_stub("homeassistant.const", Platform=_Platform, PERCENTAGE="%")
_stub("homeassistant.exceptions", ConfigEntryNotReady=Exception)
_stub("homeassistant.config_entries", ConfigEntry=MagicMock, config_entries=MagicMock())
_stub("homeassistant.helpers")
_stub("homeassistant.helpers.entity", DeviceInfo=dict, EntityCategory=_EntityCategory)
_stub("homeassistant.helpers.entity_platform", AddEntitiesCallback=MagicMock)
_stub("homeassistant.helpers.aiohttp_client", async_get_clientsession=MagicMock())
_stub("homeassistant.components")
_stub("homeassistant.components.switch", SwitchEntity=_SwitchEntity)
_stub("homeassistant.components.lock", LockEntity=_LockEntity)
_stub(
    "homeassistant.components.cover",
    CoverEntity=_CoverEntity,
    CoverDeviceClass=_CoverDeviceClass,
    CoverEntityFeature=_CoverEntityFeature,
)
_stub(
    "homeassistant.components.sensor",
    SensorEntity=_SensorEntity,
    SensorDeviceClass=_SensorDeviceClass,
    SensorStateClass=_SensorStateClass,
)
_stub(
    "homeassistant.data_entry_flow",
    FlowResult=dict,
    FlowResultType=MagicMock(),
)


# ── Shared data fixtures ─────────────────────────────────────────────────────

HUB_SERIAL = "90030191"
HUB_UUID = "36ff2a40-3081-11ed-a4cd-0d1e06747a2f"
HUB_USER = "67464420-a7dd-11e9-bb96-67bdc8303c0f"
HUB_TOKEN = "test-token-value"
HUB_IP = "192.168.10.171"


@pytest.fixture
def hub_serial():
    return HUB_SERIAL


@pytest.fixture
def hub_uuid():
    return HUB_UUID


@pytest.fixture
def sample_devices():
    return [
        {"_id": "dev-fan", "name": "Fan", "type": "switch.inwall", "reachable": True},
        {
            "_id": "dev-lock",
            "name": "Front Door",
            "type": "doorlock",
            "reachable": True,
        },
        {
            "_id": "dev-garage",
            "name": "Garage Door",
            "type": "shutter.garage",
            "reachable": False,
            "info": {"manufacturer": "Linear", "model": "GD00Z-5"},
        },
        {
            "_id": "dev-unknown",
            "name": "Mystery Sensor",
            "type": "sensor.unknown",
            "reachable": True,
        },
    ]


@pytest.fixture
def sample_items():
    return [
        {
            "_id": "item-switch",
            "deviceId": "dev-fan",
            "name": "switch",
            "value": False,
            "valueType": "bool",
        },
        {
            "_id": "item-lock",
            "deviceId": "dev-lock",
            "name": "door_lock",
            "value": "secured",
            "valueType": "token",
        },
        {
            "_id": "item-batt",
            "deviceId": "dev-lock",
            "name": "battery",
            "value": 87,
            "valueType": "int",
        },
        {
            "_id": "item-batt-maint",
            "deviceId": "dev-lock",
            "name": "battery_maintenance_state",
            "value": "replace_battery_soon",
            "valueType": "token",
        },
    ]
