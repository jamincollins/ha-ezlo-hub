"""Sensor platform for Ezlo Hub (battery levels and maintenance state)."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, ITEM_BATTERY, ITEM_BATTERY_MAINT
from .hub import EzloHub

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    hub: EzloHub = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = []
    for dev in hub.devices:
        dev_id = dev["_id"]
        if (item := hub.find_item(dev_id, ITEM_BATTERY)):
            entities.append(EzloBatterySensor(hub, dev, item))
        if (item := hub.find_item(dev_id, ITEM_BATTERY_MAINT)):
            entities.append(EzloBatteryMaintSensor(hub, dev, item))
    async_add_entities(entities)


class _EzloBaseSensor(SensorEntity):
    """Common behaviour for all Ezlo sensor entities."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, hub: EzloHub, device: dict, item: dict, suffix: str) -> None:
        self._hub = hub
        self._device = device
        self._item = item
        dev_id = device["_id"]
        self._attr_unique_id = f"{hub.serial}_{dev_id}_{suffix}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, dev_id)},
            name=device.get("name", "Device"),
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
    def available(self) -> bool:
        return self._hub.available and self._device.get("reachable", True)


class EzloBatterySensor(_EzloBaseSensor):
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_name = "Battery"

    def __init__(self, hub: EzloHub, device: dict, item: dict) -> None:
        super().__init__(hub, device, item, "battery")

    @property
    def native_value(self) -> int | None:
        try:
            return int(self._item.get("value"))
        except (TypeError, ValueError):
            return None


class EzloBatteryMaintSensor(_EzloBaseSensor):
    _attr_name = "Battery Status"

    def __init__(self, hub: EzloHub, device: dict, item: dict) -> None:
        super().__init__(hub, device, item, "battery_maint")

    @property
    def native_value(self) -> str | None:
        val = self._item.get("value")
        if val is None:
            return None
        # Convert snake_case token to human-readable: "replace_battery_soon" → "Replace Battery Soon"
        return str(val).replace("_", " ").title()
