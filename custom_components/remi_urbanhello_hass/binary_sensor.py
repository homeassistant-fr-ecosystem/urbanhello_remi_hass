from datetime import timedelta
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.helpers.entity import EntityCategory
from .const import DOMAIN, BRAND_NAME, MANUFACTURER, MODEL, get_device_info
import logging

_LOGGER = logging.getLogger(__name__)

# Define update interval (1 minute)
SCAN_INTERVAL = timedelta(minutes=1)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up binary sensors for Rémi devices."""
    api = hass.data[DOMAIN]["api"]
    devices = hass.data[DOMAIN]["devices"]

    binary_sensors = []
    for device in devices:
        binary_sensors.append(RemiConnectivityBinarySensor(api, device))

    async_add_entities(binary_sensors, update_before_add=True)


class RemiConnectivityBinarySensor(BinarySensorEntity):
    """Representation of a Rémi connectivity binary sensor."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "connectivity"

    def __init__(self, api, device):
        self._api = api
        self._device = device
        self._name = f"{BRAND_NAME} {device.get('name', 'Unknown Device')} Connectivity"
        self._id = device["objectId"]
        self._is_on = None

    @property
    def device_info(self):
        """Return device information to link the entity to the integration."""
        return get_device_info(DOMAIN, self._id, f"{BRAND_NAME} {self._device.get('name', 'Unknown Device')}", self._device)

    @property
    def name(self):
        """Return the name of the binary sensor."""
        return self._name

    @property
    def unique_id(self):
        """Return a unique ID for the binary sensor."""
        return f"{self._id}_connectivity"

    @property
    def is_on(self):
        """Return true if the device is connected."""
        return self._is_on if self._is_on is not None else False

    @property
    def available(self):
        """Return True if entity is available."""
        return self._is_on is not None

    @property
    def extra_state_attributes(self):
        """Return additional attributes."""
        return {
            "online": self._is_on,
        }

    async def async_update(self):
        """Fetch the latest connectivity status from the API."""
        try:
            info = await self._api.get_remi_info(self._id)
            raw = info.get("raw", {})
            self._is_on = raw.get("online")
        except Exception as e:
            _LOGGER.error("Failed to update connectivity for %s: %s", self._name, e)
            self._is_on = None
