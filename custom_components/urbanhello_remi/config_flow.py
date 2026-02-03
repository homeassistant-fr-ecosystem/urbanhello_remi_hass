from __future__ import annotations

import logging
from typing import Any

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
import voluptuous as vol

from .api import RemiAPI
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema({
    vol.Required("username"): str,
    vol.Required("password"): str,
})

class RemiConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Rémi."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input["username"].lower())
            self._abort_if_unique_id_configured()

            try:
                api = RemiAPI(user_input["username"], user_input["password"])
                await api.login()
                return self.async_create_entry(
                    title=f"Rémi ({user_input['username']})",
                    data=user_input,
                )
            except Exception as e:
                _LOGGER.error("Unexpected error during login: %s", e)
                error_str = str(e).lower()
                if "401" in error_str or "auth" in error_str or "login" in error_str:
                    errors["base"] = "auth_failed"
                else:
                    errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> FlowResult:
        """Handle re-authentication."""
        return await self.async_step_reauth_confirm(entry_data)

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm re-authentication."""
        errors = {}
        if user_input is not None:
            try:
                api = RemiAPI(user_input["username"], user_input["password"])
                await api.login()
                
                entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
                self.hass.config_entries.async_update_entry(
                    entry,
                    data=user_input,
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")
            except Exception as e:
                _LOGGER.error("Re-authentication failed: %s", e)
                errors["base"] = "auth_failed"

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=DATA_SCHEMA,
            errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> RemiOptionsFlowHandler:
        """Get the options flow for this handler."""
        return RemiOptionsFlowHandler()


class RemiOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Rémi."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    "scan_interval",
                    default=self.config_entry.options.get("scan_interval", 60),
                ): vol.All(vol.Coerce(int), vol.Range(min=30, max=3600)),
            }),
        )
