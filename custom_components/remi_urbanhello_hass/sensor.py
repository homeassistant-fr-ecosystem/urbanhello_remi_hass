from datetime import timedelta
from homeassistant.helpers.entity import Entity
from homeassistant.const import PERCENTAGE
from homeassistant.components.sensor import SensorDeviceClass, SensorEntityDescription
from .const import DOMAIN, MANUFACTURER, MODEL, get_device_info
import logging

_LOGGER = logging.getLogger(__name__)

# Define update interval (1 minute)
SCAN_INTERVAL = timedelta(minutes=1)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up sensors for Rémi devices."""
    api = hass.data[DOMAIN]["api"]
    devices = hass.data[DOMAIN]["devices"]

    sensors = []
    for device in devices:
        sensors.append(RemiTemperatureSensor(api, device))
        sensors.append(RemiFaceSensor(api, device))
        sensors.append(RemiRawDataSensor(api, device))
        # Diagnostic sensors
        sensors.append(RemiRssiSensor(api, device))

    async_add_entities(sensors, update_before_add=True)

class RemiTemperatureSensor(Entity):
    """Representation of a Rémi temperature sensor."""

    def __init__(self, api, device):
        self._api = api
        self._device = device
        self._name = f"Rémi {device.get('name', 'Unknown Device')} temperature"
        self._id = device["objectId"]
        self._temperature = None

    @property
    def device_info(self):
        """Return device information to link the entity to the integration."""
        info = get_device_info(DOMAIN, self._id, self._name, self._device)
        info["via_device"] = (DOMAIN, self._id)
        return info

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def unique_id(self):
        """Return a unique ID for the sensor."""
        return f"{self._id}_temperature"

    @property
    def state(self):
        """Return the current temperature."""
        return self._temperature

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return "°C"

    async def async_update(self):
        """Fetch the latest temperature from the API."""
        try:
            info = await self._api.get_remi_info(self._id)
            self._temperature = info["temperature"] / 10.0
        except Exception as e:
            _LOGGER.error("Failed to update temperature for %s: %s", self._name, e)


class RemiFaceSensor(Entity):
    """Representation of a Rémi face sensor."""

    def __init__(self, api, device):
        self._api = api
        self._device = device
        self._name = f"Rémi {device.get('name', 'Unknown Device')} Face"
        self._id = device["objectId"]
        self._face = None

    @property
    def device_info(self):
        """Return device information to link the entity to the integration."""
        return get_device_info(DOMAIN, self._id, f"Rémi {self._device.get('name', 'Unknown Device')}", self._device)

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def unique_id(self):
        """Return a unique ID for the sensor."""
        return f"{self._id}_face"

    @property
    def state(self):
        """Return the current face name."""
        return self._face

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return "mdi:emoticon"

    async def async_update(self):
        """Fetch the latest face from the API."""
        try:
            face_name = await self._api.get_current_face(self._id)
            self._face = face_name
        except Exception as e:
            _LOGGER.error("Failed to update face for %s: %s", self._name, e)


class RemiRawDataSensor(Entity):
    """Representation of a Rémi raw data sensor with all API fields."""

    def __init__(self, api, device):
        self._api = api
        self._device = device
        self._name = f"Rémi {device.get('name', 'Unknown Device')} Raw Data"
        self._id = device["objectId"]
        self._raw_data = {}

    @property
    def device_info(self):
        """Return device information to link the entity to the integration."""
        return get_device_info(DOMAIN, self._id, f"Rémi {self._device.get('name', 'Unknown Device')}", self._device)

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def unique_id(self):
        """Return a unique ID for the sensor."""
        return f"{self._id}_raw_data"

    @property
    def state(self):
        """Return the state as 'available' or 'unavailable'."""
        return "available" if self._raw_data else "unavailable"

    @property
    def extra_state_attributes(self):
        """Return all raw data as attributes."""
        if not self._raw_data:
            return {}

        # Return the raw data with friendly formatting
        raw = self._raw_data.get("raw", {})

        # Create a clean attributes dictionary
        attributes = {}

        # Add all raw fields
        for key, value in raw.items():
            # Skip internal fields that start with underscore
            if not key.startswith("_"):
                attributes[key] = value

        # Add parsed/normalized fields from the API
        if "temperature" in self._raw_data:
            attributes["temperature_normalized"] = self._raw_data["temperature"]
        if "luminosity" in self._raw_data:
            attributes["luminosity_normalized"] = self._raw_data["luminosity"]
        if "face" in self._raw_data:
            attributes["face_id"] = self._raw_data["face"]
        if "volume" in self._raw_data:
            attributes["volume_normalized"] = self._raw_data["volume"]
        if "light_min" in self._raw_data:
            attributes["light_min_normalized"] = self._raw_data["light_min"]
        if "name" in self._raw_data:
            attributes["device_name"] = self._raw_data["name"]

        return attributes

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return "mdi:code-json"

    async def async_update(self):
        """Fetch the latest raw data from the API."""
        try:
            info = await self._api.get_remi_info(self._id)
            self._raw_data = info
        except Exception as e:
            _LOGGER.error("Failed to update raw data for %s: %s", self._name, e)
            self._raw_data = {}


class RemiRssiSensor(Entity):
    """Representation of a Rémi RSSI (WiFi signal strength) sensor."""

    _attr_entity_category = "diagnostic"
    _attr_entity_registry_enabled_default = True

    def __init__(self, api, device):
        self._api = api
        self._device = device
        self._name = f"Rémi {device.get('name', 'Unknown Device')} RSSI"
        self._id = device["objectId"]
        self._rssi = None

    @property
    def device_info(self):
        """Return device information to link the entity to the integration."""
        return get_device_info(DOMAIN, self._id, f"Rémi {self._device.get('name', 'Unknown Device')}", self._device)

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def unique_id(self):
        """Return a unique ID for the sensor."""
        return f"{self._id}_rssi"

    @property
    def state(self):
        """Return the current RSSI value."""
        return self._rssi

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return "dBm"

    @property
    def device_class(self):
        """Return the device class."""
        return SensorDeviceClass.SIGNAL_STRENGTH

    @property
    def icon(self):
        """Return the icon to use in the frontend based on signal strength."""
        if self._rssi is None:
            return "mdi:wifi-strength-alert-outline"
        elif self._rssi >= -50:
            return "mdi:wifi-strength-4"
        elif self._rssi >= -60:
            return "mdi:wifi-strength-3"
        elif self._rssi >= -70:
            return "mdi:wifi-strength-2"
        else:
            return "mdi:wifi-strength-1"

    async def async_update(self):
        """Fetch the latest RSSI from the API."""
        try:
            info = await self._api.get_remi_info(self._id)
            raw = info.get("raw", {})
            self._rssi = raw.get("rssi")
        except Exception as e:
            _LOGGER.error("Failed to update RSSI for %s: %s", self._name, e)