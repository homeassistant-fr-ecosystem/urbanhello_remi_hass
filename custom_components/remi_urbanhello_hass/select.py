from datetime import timedelta
from homeassistant.components.select import SelectEntity
from .const import DOMAIN, MANUFACTURER, MODEL, get_device_info
import logging

_LOGGER = logging.getLogger(__name__)

# Define update interval (1 minute)
SCAN_INTERVAL = timedelta(minutes=1)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up select entities for Rémi devices."""
    api = hass.data[DOMAIN]["api"]
    devices = hass.data[DOMAIN]["devices"]

    selects = []
    for device in devices:
        selects.append(RemiFaceSelect(api, device))

    async_add_entities(selects, update_before_add=True)


class RemiFaceSelect(SelectEntity):
    """Representation of a Rémi face selector."""

    def __init__(self, api, device):
        self._api = api
        self._device = device
        self._name = f"Rémi {device.get('name', 'Unknown Device')} Face"
        self._id = device["objectId"]
        self._current_face = None
        self._options = []

    @property
    def device_info(self):
        """Return device information to link the entity to the integration."""
        return get_device_info(DOMAIN, self._id, f"Rémi {self._device.get('name', 'Unknown Device')}", self._device)

    @property
    def name(self):
        """Return the name of the select entity."""
        return self._name

    @property
    def unique_id(self):
        """Return a unique ID for the select entity."""
        return f"{self._id}_face_select"

    @property
    def current_option(self):
        """Return the currently selected face."""
        return self._current_face

    @property
    def options(self):
        """Return the list of available faces."""
        # If we haven't loaded options yet, get them from the API
        if not self._options and self._api.faces:
            self._options = sorted(list(self._api.faces.keys()))
        return self._options if self._options else ["sleepyFace", "awakeFace"]

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return "mdi:emoticon-happy-outline"

    async def async_select_option(self, option: str) -> None:
        """Change the selected face."""
        try:
            await self._api.set_face_by_name(self._id, option)
            self._current_face = option
            _LOGGER.info("Changed face to %s for %s", option, self._name)
        except Exception as e:
            _LOGGER.error("Failed to set face for %s: %s", self._name, e)
            raise

    async def async_update(self):
        """Fetch the latest face from the API."""
        try:
            # Update available options from API
            if self._api.faces:
                self._options = sorted(list(self._api.faces.keys()))

            # Get current face
            face_name = await self._api.get_current_face(self._id)
            self._current_face = face_name
        except Exception as e:
            _LOGGER.error("Failed to update face selector for %s: %s", self._name, e)
