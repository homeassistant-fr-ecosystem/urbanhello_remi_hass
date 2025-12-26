from datetime import timedelta
from homeassistant.components.number import NumberEntity, NumberMode
from .const import DOMAIN, BRAND_NAME, MANUFACTURER, MODEL, get_device_info
import logging

_LOGGER = logging.getLogger(__name__)

# Define update interval (1 minute)
SCAN_INTERVAL = timedelta(minutes=1)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up number entities for Rémi devices."""
    api = hass.data[DOMAIN]["api"]
    devices = hass.data[DOMAIN]["devices"]

    numbers = []
    for device in devices:
        numbers.append(RemiVolumeNumber(api, device))
        numbers.append(RemiNoiseThresholdNumber(api, device))
        numbers.append(RemiNightFaceLevel(api, device))

    async_add_entities(numbers, update_before_add=True)


class RemiVolumeNumber(NumberEntity):
    """Representation of a Rémi volume control."""

    _attr_translation_key = "volume"

    def __init__(self, api, device):
        self._api = api
        self._device = device
        self._name = f"{BRAND_NAME} {device.get('name', 'Unknown Device')} Volume"
        self._id = device["objectId"]
        self._volume = device.get("volume", 0)
        self._attr_native_min_value = 0
        self._attr_native_max_value = 100
        self._attr_native_step = 1
        self._attr_mode = NumberMode.SLIDER

    @property
    def device_info(self):
        """Return device information to link the entity to the integration."""
        return get_device_info(DOMAIN, self._id, f"{BRAND_NAME} {self._device.get('name', 'Unknown Device')}", self._device)

    @property
    def name(self):
        """Return the name of the number entity."""
        return self._name

    @property
    def unique_id(self):
        """Return a unique ID for the number entity."""
        return f"{self._id}_volume_control"

    @property
    def native_value(self):
        """Return the current volume level."""
        return self._volume

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        if self._volume == 0:
            return "mdi:volume-off"
        elif self._volume < 33:
            return "mdi:volume-low"
        elif self._volume < 66:
            return "mdi:volume-medium"
        else:
            return "mdi:volume-high"

    async def async_set_native_value(self, value: float) -> None:
        """Set the volume level."""
        try:
            volume_int = int(value)
            await self._api.set_volume(self._id, volume_int)
            self._volume = volume_int
            _LOGGER.debug("Set volume to %d for %s", volume_int, self._name)
        except Exception as e:
            _LOGGER.error("Failed to set volume for %s: %s", self._name, e)

    async def async_update(self):
        """Fetch the latest volume from the API."""
        try:
            info = await self._api.get_remi_info(self._id)
            self._volume = info.get("volume", self._volume)
        except Exception as e:
            _LOGGER.error("Failed to update volume for %s: %s", self._name, e)


class RemiNoiseThresholdNumber(NumberEntity):
    """Representation of a Rémi noise notification threshold control."""

    _attr_translation_key = "noise_threshold"

    def __init__(self, api, device):
        self._api = api
        self._device = device
        self._name = f"{BRAND_NAME} {device.get('name', 'Unknown Device')} Noise Threshold"
        self._id = device["objectId"]
        self._threshold = device.get("noise_notification_threshold", 0)
        self._attr_native_min_value = 0
        self._attr_native_max_value = 100
        self._attr_native_step = 1
        self._attr_mode = NumberMode.SLIDER

    @property
    def device_info(self):
        """Return device information to link the entity to the integration."""
        return get_device_info(DOMAIN, self._id, f"{BRAND_NAME} {self._device.get('name', 'Unknown Device')}", self._device)

    @property
    def name(self):
        """Return the name of the number entity."""
        return self._name

    @property
    def unique_id(self):
        """Return a unique ID for the number entity."""
        return f"{self._id}_noise_threshold"

    @property
    def native_value(self):
        """Return the current noise threshold level."""
        return self._threshold

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        if self._threshold == 0:
            return "mdi:volume-off"
        elif self._threshold < 33:
            return "mdi:volume-low"
        elif self._threshold < 66:
            return "mdi:volume-medium"
        else:
            return "mdi:volume-high"

    async def async_set_native_value(self, value: float) -> None:
        """Set the noise threshold level."""
        try:
            threshold_int = int(value)
            await self._api.set_noise_threshold(self._id, threshold_int)
            self._threshold = threshold_int
            _LOGGER.debug("Set noise threshold to %d for %s", threshold_int, self._name)
        except Exception as e:
            _LOGGER.error("Failed to set noise threshold for %s: %s", self._name, e)

    async def async_update(self):
        """Fetch the latest noise threshold from the API."""
        try:
            info = await self._api.get_remi_info(self._id)
            raw = info.get("raw", {})
            self._threshold = raw.get("noise_notification_threshold", self._threshold)
        except Exception as e:
            _LOGGER.error("Failed to update noise threshold for %s: %s", self._name, e)


class RemiNightFaceLevel(NumberEntity):
    """Representation of a Rémi night face level control."""

    _attr_translation_key = "night_face_level"

    def __init__(self, api, device):
        self._api = api
        self._device = device
        self._name = f"{BRAND_NAME} {device.get('name', 'Unknown Device')} Night Face Level"
        self._id = device["objectId"]
        self._level = device.get("light_min", 0)
        self._attr_native_min_value = 0
        self._attr_native_max_value = 100
        self._attr_native_step = 1
        self._attr_mode = NumberMode.SLIDER

    @property
    def device_info(self):
        """Return device information to link the entity to the integration."""
        return get_device_info(DOMAIN, self._id, f"{BRAND_NAME} {self._device.get('name', 'Unknown Device')}", self._device)

    @property
    def name(self):
        """Return the name of the number entity."""
        return self._name

    @property
    def unique_id(self):
        """Return a unique ID for the number entity."""
        return f"{self._id}_night_face_level"

    @property
    def native_value(self):
        """Return the current night face level."""
        return self._level

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        if self._level == 0:
            return "mdi:brightness-1"
        elif self._level < 33:
            return "mdi:brightness-4"
        elif self._level < 66:
            return "mdi:brightness-5"
        else:
            return "mdi:brightness-6"

    async def async_set_native_value(self, value: float) -> None:
        """Set the night face level."""
        try:
            level_int = int(value)
            await self._api.set_night_luminosity(self._id, level_int)
            self._level = level_int
            _LOGGER.debug("Set night face level to %d for %s", level_int, self._name)
        except Exception as e:
            _LOGGER.error("Failed to set night face level for %s: %s", self._name, e)

    async def async_update(self):
        """Fetch the latest night face level from the API."""
        try:
            info = await self._api.get_remi_info(self._id)
            self._level = info.get("light_min", self._level)
        except Exception as e:
            _LOGGER.error("Failed to update night face level for %s: %s", self._name, e)
