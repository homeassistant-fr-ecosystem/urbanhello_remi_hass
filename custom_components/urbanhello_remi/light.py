from homeassistant.components.light import LightEntity, ColorMode, ATTR_BRIGHTNESS
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, BRAND_NAME, get_device_info
from .coordinator import RemiCoordinator
import logging

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Rémi lights based on a config entry."""
    api = hass.data[DOMAIN]["api"]
    devices = hass.data[DOMAIN]["devices"]
    coordinators = hass.data[DOMAIN]["coordinators"]

    lights = []
    for device in devices:
        device_id = device["objectId"]
        device_name = device.get("name", "Rémi")
        coordinator = coordinators.get(device_id)

        if not coordinator:
            _LOGGER.error("No coordinator found for device %s (%s)", device_name, device_id)
            continue

        _LOGGER.debug("Setting up light for device: %s", device)
        lights.append(RemiNightLight(coordinator, api, device))

    async_add_entities(lights)

class RemiNightLight(CoordinatorEntity, LightEntity):
    """Representation of a Rémi Night Light (brightness-only control)."""

    _attr_translation_key = "night_light"
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _attr_color_mode = ColorMode.BRIGHTNESS

    def __init__(self, coordinator: RemiCoordinator, api, device):
        """Initialize the night light."""
        super().__init__(coordinator)
        self._api = api
        self._device = device
        self._device_name = device.get("name", "Rémi")
        self._device_id = device["objectId"]

        self._attr_name = f"{BRAND_NAME} {self._device_name} Night Light"
        self._attr_unique_id = f"{self._device_id}_night_light"

    @property
    def device_info(self):
        """Return device information to link the entity to the integration."""
        return get_device_info(DOMAIN, self._device_id, self._device_name, self._device)

    @property
    def is_on(self):
        """Return the state of the light."""
        brightness = self._get_brightness()
        return brightness > 0 if brightness is not None else False

    @property
    def brightness(self):
        """Return the brightness of the light (0-255)."""
        # Convert brightness from 0-100 to 0-255
        brightness = self._get_brightness()
        if brightness is not None:
            return min(int(brightness * 255 / 100), 255)
        return 0

    def _get_brightness(self):
        """Get current brightness from coordinator data."""
        if self.coordinator.data and "device_info" in self.coordinator.data:
            device_info = self.coordinator.data["device_info"]
            return device_info.get("luminosity")
        return None

    async def async_turn_on(self, **kwargs):
        """Turn on the light."""
        # Get the brightness from kwargs, defaulting to 255
        brightness = kwargs.get(ATTR_BRIGHTNESS, 255)

        # Convert brightness from 0-255 to 0-100 for the API
        api_brightness = min(int(brightness * 100 / 255), 100)

        await self._api.set_brightness(self._device_id, api_brightness)
        _LOGGER.debug("Set Night Light brightness to %d for %s", api_brightness, self._attr_name)

        # Request immediate refresh from coordinator
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **_kwargs):
        """Turn off the light."""
        await self._api.set_brightness(self._device_id, 0)
        _LOGGER.debug("Turned off Night Light for %s", self._attr_name)

        # Request immediate refresh from coordinator
        await self.coordinator.async_request_refresh()