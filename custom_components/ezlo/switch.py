"""Switch platform for Ezlo Hub (in-wall switches)."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DEV_TYPE_SWITCH, DOMAIN, ITEM_SWITCH
from .hub import EzloHub

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    hub: EzloHub = hass.data[DOMAIN][entry.entry_id]
    entities = [
        EzloSwitch(hub, dev, hub.find_item(dev["_id"], ITEM_SWITCH))
        for dev in hub.devices
        if dev.get("type") == DEV_TYPE_SWITCH
        and hub.find_item(dev["_id"], ITEM_SWITCH) is not None
    ]
    async_add_entities(entities)


class EzloSwitch(SwitchEntity):
    _attr_has_entity_name = True
    _attr_name = None  # device name becomes the entity name

    def __init__(self, hub: EzloHub, device: dict, item: dict) -> None:
        self._hub = hub
        self._device = device
        self._item = item
        dev_id = device["_id"]
        self._attr_unique_id = f"{hub.serial}_{dev_id}_switch"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, dev_id)},
            name=device.get("name", "Switch"),
            model=device.get("deviceTypeId", ""),
            manufacturer="Ezlo",
            via_device=(DOMAIN, hub.serial),
        )

    async def async_added_to_hass(self) -> None:
        self._hub.register_callback(self._on_hub_update)

    async def async_will_remove_from_hass(self) -> None:
        self._hub.unregister_callback(self._on_hub_update)

    @callback
    def _on_hub_update(self, item_id: str | None) -> None:
        if item_id is not None and item_id != self._item["_id"]:
            return
        current = self._hub.get_item(self._item["_id"])
        if current:
            self._item = current
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        return bool(self._item.get("value"))

    @property
    def available(self) -> bool:
        return self._hub.available and self._device.get("reachable", True)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._hub.async_set_item_value(self._item["_id"], True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._hub.async_set_item_value(self._item["_id"], False)
