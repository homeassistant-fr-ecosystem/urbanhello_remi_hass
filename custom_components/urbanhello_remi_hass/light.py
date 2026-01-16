from datetime import timedelta
from homeassistant.components.light import LightEntity, ColorMode, ATTR_BRIGHTNESS
from .const import DOMAIN, BRAND_NAME, MANUFACTURER, MODEL, get_device_info
import logging

_LOGGER = logging.getLogger(__name__)

# Définir l'intervalle de mise à jour (1 minute)
SCAN_INTERVAL = timedelta(minutes=1)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Rémi lights based on a config entry."""
    api = hass.data[DOMAIN]["api"]
    devices = hass.data[DOMAIN]["devices"]

    lights = []
    for device in devices:
        _LOGGER.debug("Setting up light for device: %s", device)
        lights.append(RemiNightLight(api, device))

    async_add_entities(lights, update_before_add=True)

class RemiNightLight(LightEntity):
    """Representation of a Rémi Night Light (brightness-only control)."""

    _attr_translation_key = "night_light"

    def __init__(self, api, device):
        self._api = api
        self._device = device
        self._name = f"{BRAND_NAME} {device.get('name', 'Unknown Device')} Night Light"
        self._id = device["objectId"]
        self._brightness = device.get("luminosity", 0)

        # Use ColorMode for supported color modes
        self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    @property
    def unique_id(self):
        """Return a unique ID for the light."""
        return f"{self._id}_night_light"

    @property
    def device_info(self):
        """Return device information to link the entity to the integration."""
        return get_device_info(DOMAIN, self._id, f"{BRAND_NAME} {self._device.get('name', 'Unknown Device')}", self._device)

    @property
    def name(self):
        """Return the name of the light."""
        return self._name

    @property
    def is_on(self):
        """Return the state of the light."""
        return self._brightness > 0

    @property
    def color_mode(self):
        """Return the current color mode of the light."""
        return ColorMode.BRIGHTNESS

    @property
    def brightness(self):
        """Return the brightness of the light (0-255)."""
        # Convert brightness from 0-100 to 0-255
        return min(int(self._brightness * 255 / 100), 255)

    async def async_turn_on(self, **kwargs):
        """Turn on the light."""
        # Get the brightness from kwargs, defaulting to 255
        brightness = kwargs.get(ATTR_BRIGHTNESS, 255)

        # Convert brightness from 0-255 to 0-100 for the API
        api_brightness = min(int(brightness * 100 / 255), 100)

        await self._api.set_brightness(self._id, api_brightness)
        self._brightness = api_brightness
        _LOGGER.debug("Set Night Light brightness to %d for %s", api_brightness, self._name)

    async def async_turn_off(self, **_kwargs):
        """Turn off the light."""
        await self._api.set_brightness(self._id, 0)
        self._brightness = 0
        _LOGGER.debug("Turned off Night Light for %s", self._name)

    async def async_update(self):
        """Fetch the latest brightness from the API."""
        try:
            info = await self._api.get_remi_info(self._id)
            self._brightness = info.get("luminosity", self._brightness)
        except Exception as e:
            _LOGGER.error("Failed to update Night Light for %s: %s", self._name, e)