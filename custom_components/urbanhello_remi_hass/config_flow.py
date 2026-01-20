from __future__ import annotations

import logging
from typing import Any

from homeassistant import config_entries
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
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        _LOGGER.debug("Starting config flow for Rémi")
        if user_input is not None:
            _LOGGER.debug("User input received: %s", user_input)
            errors = {}
            try:
                api = RemiAPI(user_input["username"], user_input["password"])
                await api.login()
                _LOGGER.debug("Login successful, creating entry")
                return self.async_create_entry(
                    title="Rémi Integration",
                    data=user_input,
                )
            except ConnectionError as e:
                _LOGGER.error("Cannot connect to Rémi service: %s", e)
                errors["base"] = "cannot_connect"
            except TimeoutError as e:
                _LOGGER.error("Connection timeout to Rémi service: %s", e)
                errors["base"] = "cannot_connect"
            except Exception as e:
                error_str = str(e).lower()
                # Check if it's an authentication error
                if "401" in error_str or "auth" in error_str or "login" in error_str or "credential" in error_str:
                    _LOGGER.error("Authentication failed: %s", e)
                    errors["base"] = "auth_failed"
                else:
                    _LOGGER.error("Unexpected error during login: %s", e, exc_info=True)
                    errors["base"] = "unknown"

            if errors:
                return self.async_show_form(
                    step_id="user",
                    data_schema=DATA_SCHEMA,
                    errors=errors
                )
        return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA)