"""Config flow for Zehnder ComfoClime integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import AbortFlow
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import voluptuous as vol

from .api import ZehnderApiClient, ZehnderConnectionError, ZehnderError
from .const import (
    CONF_HOST,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class ZehnderConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Zehnder ComfoClime."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            if host.startswith("http://"):
                host = host[7:]
            elif host.startswith("https://"):
                host = host[8:]
            host = host.rstrip("/")

            session = async_get_clientsession(self.hass)
            api = ZehnderApiClient(host=host, session=session)

            try:
                ping_info = await api.ping()
                clime_uuid = ping_info.get("uuid")
                if not clime_uuid:
                    errors["base"] = "cannot_connect"
                else:
                    await api.discover_devices()
                    await self.async_set_unique_id(clime_uuid)
                    self._abort_if_unique_id_configured(updates={CONF_HOST: host})

                    return self.async_create_entry(
                        title=f"Zehnder ComfoClime ({host})",
                        data={
                            CONF_HOST: host,
                            "clime_uuid": api.clime_uuid,
                            "q350_uuid": api.q350_uuid,
                            "clime_name": api.clime_name,
                            "q350_name": api.q350_name,
                            "version": api.clime_version,
                        },
                    )
            except AbortFlow:
                raise
            except ZehnderConnectionError:
                errors["base"] = "cannot_connect"
            except ZehnderError:
                errors["base"] = "api_error"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception during Zehnder setup")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default="192.168.178.106"): str,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get options flow handler."""
        return ZehnderOptionsFlowHandler(config_entry)


class ZehnderOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Zehnder options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_interval = self._config_entry.options.get(
            CONF_SCAN_INTERVAL,
            self._config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=current_interval,
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                    ),
                }
            ),
        )
