"""Ezlo Hub integration for Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    CONF_HUB_SERIAL,
    CONF_HUB_TOKEN,
    CONF_HUB_USER,
    CONF_HUB_UUID,
    DOMAIN,
    PLATFORMS,
    SUPPORTED_DEVICE_TYPES,
)
from .hub import EzloHub

_LOGGER = logging.getLogger(__name__)


def _log_unsupported_devices(hub: EzloHub) -> None:
    """
    Log every device whose type is not handled by this integration.

    Unsupported devices are logged at INFO level so they appear in the default
    HA log.  All of their items are logged at DEBUG level to supply enough
    information for a developer to add support.  See the README section
    "Adding Support for New Device Types".
    """
    for dev in hub.devices:
        dev_type = dev.get("type", "unknown")
        if dev_type not in SUPPORTED_DEVICE_TYPES:
            _LOGGER.info(
                "Unsupported Ezlo device type '%s' (name='%s', id=%s). "
                "This device will not appear in Home Assistant. "
                "See README → 'Adding Support for New Device Types'.",
                dev_type,
                dev.get("name", "unknown"),
                dev.get("_id"),
            )
            for item in hub.get_items_for_device(dev["_id"]):
                _LOGGER.debug(
                    "  → item '%s': valueType=%s, value=%r",
                    item.get("name"),
                    item.get("valueType"),
                    item.get("value"),
                )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hub = EzloHub(
        host=entry.data["host"],
        user=entry.data[CONF_HUB_USER],
        token=entry.data[CONF_HUB_TOKEN],
        hub_serial=entry.data[CONF_HUB_SERIAL],
        hub_uuid=entry.data[CONF_HUB_UUID],
    )

    if not await hub.async_setup():
        raise ConfigEntryNotReady(
            f"Cannot connect to Ezlo hub {entry.data[CONF_HUB_SERIAL]}"
        )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = hub

    _log_unsupported_devices(hub)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hub: EzloHub = hass.data[DOMAIN].pop(entry.entry_id)
        await hub.async_teardown()
    return unload_ok
