from datetime import timedelta
from homeassistant.components.light import LightEntity, ColorMode, ATTR_BRIGHTNESS
from .const import DOMAIN, MANUFACTURER, MODEL, get_device_info
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
        lights.append(RemiLight(api, device))

    async_add_entities(lights, update_before_add=True)

class RemiLight(LightEntity):
    def __init__(self, api, device):
        self._api = api
        self._device = device
        self._name = f"Rémi {device.get('name', 'Unknown Device')}"
        self._id = device["objectId"]
        self._brightness = device.get("luminosity", 0)

        # Récupérer les faces dynamiquement
        self._face_on = api.faces.get("sleepyFace")  # Face associée pour "on"
        self._face_off = api.faces.get("awakeFace")  # Face associée pour "off"

        # Vérification des faces
        if not self._face_on or not self._face_off:
            _LOGGER.error("Faces not found for Remi %s", self._name)

        # Définir dynamiquement si la lumière est allumée ou éteinte
        current_face = device.get("face")
        if isinstance(current_face, dict):
            current_face = current_face.get("objectId")
        self._is_on = current_face == self._face_on

        # Use ColorMode for supported color modes
        self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    @property
    def unique_id(self):
        """Return a unique ID for the light."""
        return self._id

    @property
    def device_info(self):
        """Return device information to link the entity to the integration."""
        info = get_device_info(DOMAIN, self._id, self._name, self._device)
        info["via_device"] = (DOMAIN, self._id)
        return info

    @property
    def name(self):
        """Return the name of the light."""
        return self._name

    @property
    def is_on(self):
        """Return the state of the light."""
        return self._is_on

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
        await self._api.turn_on(self._id)
        self._is_on = True
        self._brightness = api_brightness

    async def async_turn_off(self, **kwargs):
        """Turn off the light."""
        await self._api.set_brightness(self._id, 0)
        await self._api.turn_off(self._id)
        self._brightness = 0
        self._is_on = False

    async def async_update(self):
        """Fetch the latest light state and brightness from the API."""
        try:
            info = await self._api.get_remi_info(self._id)
            self._brightness = info["luminosity"]

            # Déterminer l'état en fonction de la face actuelle
            self._is_on = info["face"] == self._face_on
        except Exception as e:
            _LOGGER.error("Failed to update light info for %s: %s", self._name, e)