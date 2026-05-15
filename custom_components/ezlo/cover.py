"""Cover platform for Ezlo Hub (garage doors)."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.cover import (
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DEV_TYPE_GARAGE, DOMAIN, ITEM_BARRIER_STATE, ITEM_GARAGE_DOOR
from .hub import EzloHub

_LOGGER = logging.getLogger(__name__)

# Item names to probe, in priority order, when discovering the state item.
_GARAGE_ITEM_CANDIDATES = (
    ITEM_GARAGE_DOOR,
    ITEM_BARRIER_STATE,
    "garage_door_status",
    "shutter_position",
)

# Values the hub uses to represent a closed/open garage door.
_CLOSED_VALUES = {"closed", "false", False, 0, "0"}
_OPEN_VALUES = {"open", "true", True, 1, "1", "opened"}


def _find_garage_item(hub: EzloHub, device_id: str) -> dict | None:
    for name in _GARAGE_ITEM_CANDIDATES:
        item = hub.find_item(device_id, name)
        if item:
            return item
    # Fall back to the first item with a boolean or token value type.
    for item in hub.get_items_for_device(device_id):
        if item.get("valueType") in ("bool", "token"):
            return item
    return None


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    hub: EzloHub = hass.data[DOMAIN][entry.entry_id]
    entities = [
        EzloCover(hub, dev)
        for dev in hub.devices
        if dev.get("type") == DEV_TYPE_GARAGE
    ]
    async_add_entities(entities)


class EzloCover(CoverEntity):
    _attr_has_entity_name = True
    _attr_name = None
    _attr_device_class = CoverDeviceClass.GARAGE
    _attr_supported_features = CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE

    def __init__(self, hub: EzloHub, device: dict) -> None:
        self._hub = hub
        self._device = device
        self._item: dict | None = None
        dev_id = device["_id"]
        self._attr_unique_id = f"{hub.serial}_{dev_id}_cover"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, dev_id)},
            name=device.get("name", "Garage Door"),
            model=device.get("info", {}).get("model", device.get("deviceTypeId", "")),
            manufacturer=device.get("info", {}).get("manufacturer", "Ezlo"),
            via_device=(DOMAIN, hub.serial),
        )

    async def async_added_to_hass(self) -> None:
        self._item = _find_garage_item(self._hub, self._device["_id"])
        self._hub.register_callback(self._on_hub_update)

    async def async_will_remove_from_hass(self) -> None:
        self._hub.unregister_callback(self._on_hub_update)

    @callback
    def _on_hub_update(self, item_id: str | None) -> None:
        # Re-probe in case the device came online after being unavailable.
        if self._item is None or item_id is None:
            self._item = _find_garage_item(self._hub, self._device["_id"])
        elif item_id == self._item["_id"]:
            self._item = self._hub.get_item(item_id) or self._item
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        dev = self._hub._devices.get(self._device["_id"], self._device)
        return self._hub.available and dev.get("reachable", False)

    @property
    def is_closed(self) -> bool | None:
        if self._item is None:
            return None
        val = self._item.get("value")
        if val in _CLOSED_VALUES or str(val).lower() in _CLOSED_VALUES:
            return True
        if val in _OPEN_VALUES or str(val).lower() in _OPEN_VALUES:
            return False
        return None

    async def async_open_cover(self, **kwargs: Any) -> None:
        if self._item is None:
            return
        val = "open" if self._item.get("valueType") == "token" else True
        await self._hub.async_set_item_value(self._item["_id"], val)

    async def async_close_cover(self, **kwargs: Any) -> None:
        if self._item is None:
            return
        val = "closed" if self._item.get("valueType") == "token" else False
        await self._hub.async_set_item_value(self._item["_id"], val)
