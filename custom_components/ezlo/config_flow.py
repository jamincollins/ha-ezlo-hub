"""Config flow for Ezlo Hub integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_HUB_SERIAL, CONF_HUB_TOKEN, CONF_HUB_USER, CONF_HUB_UUID, DOMAIN
from .hub import async_get_hub_credentials, async_get_hub_info

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class EzloConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Ezlo Hub."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            username = user_input[CONF_USERNAME].strip()
            password = user_input[CONF_PASSWORD]

            # 1. Connect to the hub to discover its serial and UUID — no auth needed.
            hub_info = await async_get_hub_info(host)
            if hub_info is None:
                errors["host"] = "cannot_connect"
            else:
                hub_serial = hub_info.get("serial", "")
                hub_uuid = hub_info.get("uuid", "")

                if not hub_serial or not hub_uuid:
                    errors["base"] = "unknown"
                else:
                    await self.async_set_unique_id(hub_serial)
                    self._abort_if_unique_id_configured()

                    # 2. Fetch local access credentials via cloud.
                    session = async_get_clientsession(self.hass)
                    creds = await async_get_hub_credentials(
                        session, username, password, hub_uuid
                    )
                    if creds is None:
                        errors["base"] = "invalid_auth"
                    else:
                        return self.async_create_entry(
                            title=f"Ezlo Hub {hub_serial}",
                            data={
                                CONF_HOST: host,
                                CONF_HUB_SERIAL: hub_serial,
                                CONF_HUB_UUID: hub_uuid,
                                CONF_HUB_USER: creds["user"],
                                CONF_HUB_TOKEN: creds["token"],
                            },
                        )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )
