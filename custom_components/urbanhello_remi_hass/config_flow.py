import logging
from homeassistant import config_entries
from .api import RemiAPI
from .const import DOMAIN
import voluptuous as vol

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema({
    vol.Required("username"): str,
    vol.Required("password"): str,
})

class RemiConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        _LOGGER.debug("Starting config flow for Rémi")
        if user_input is not None:
            _LOGGER.debug("User input received: %s", user_input)
            try:
                api = RemiAPI(user_input["username"], user_input["password"])
                await api.login()
                _LOGGER.debug("Login successful, creating entry")
                return self.async_create_entry(
                    title="Rémi Integration",
                    data=user_input,
                )
            except Exception as e:
                _LOGGER.error("Error during login: %s", e)
                return self.async_show_form(
                    step_id="user",
                    data_schema=DATA_SCHEMA,
                    errors={"base": "auth_failed"}
                )
        return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA)