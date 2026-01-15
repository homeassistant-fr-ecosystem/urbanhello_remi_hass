from datetime import timedelta
from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import ScannerEntity
from homeassistant.helpers.entity import EntityCategory
from .const import DOMAIN, BRAND_NAME, MANUFACTURER, MODEL, get_device_info
import logging

_LOGGER = logging.getLogger(__name__)

# Define update interval (1 minute)
SCAN_INTERVAL = timedelta(minutes=1)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up device tracker for Rémi devices."""
    api = hass.data[DOMAIN]["api"]
    devices = hass.data[DOMAIN]["devices"]

    trackers = []
    for device in devices:
        trackers.append(RemiDeviceTracker(api, device))

    async_add_entities(trackers, update_before_add=True)


class RemiDeviceTracker(ScannerEntity):
    """Representation of a Rémi device tracker."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, api, device):
        self._api = api
        self._device = device
        self._name = f"{BRAND_NAME} {device.get('name', 'Unknown Device')}"
        self._id = device["objectId"]
        self._ip_address = None
        self._is_connected = None
        self._mac_address = None

    @property
    def device_info(self):
        """Return device information to link the entity to the integration."""
        return get_device_info(DOMAIN, self._id, f"{BRAND_NAME} {self._device.get('name', 'Unknown Device')}", self._device)

    @property
    def name(self):
        """Return the name of the device tracker."""
        return self._name

    @property
    def unique_id(self):
        """Return a unique ID for the device tracker."""
        return f"{self._id}_device_tracker"

    @property
    def source_type(self):
        """Return the source type of the device tracker."""
        return SourceType.ROUTER

    @property
    def is_connected(self):
        """Return true if the device is connected to the network."""
        return self._is_connected if self._is_connected is not None else False

    @property
    def ip_address(self):
        """Return the primary IP address of the device."""
        return self._ip_address

    @property
    def mac_address(self):
        """Return the MAC address of the device."""
        return self._mac_address

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        if self._is_connected:
            return "mdi:lan-connect"
        return "mdi:lan-disconnect"

    @property
    def extra_state_attributes(self):
        """Return additional attributes."""
        attributes = {}
        if self._ip_address:
            attributes["ip_address"] = self._ip_address
        if self._mac_address:
            attributes["mac_address"] = self._mac_address
        if self._is_connected is not None:
            attributes["connected"] = self._is_connected
        return attributes

    async def async_update(self):
        """Fetch the latest device tracker information from the API."""
        try:
            info = await self._api.get_remi_info(self._id)
            raw = info.get("raw", {})

            # Get IP address
            self._ip_address = raw.get("ipv4Address")

            # Get connection status
            self._is_connected = raw.get("online", False)

            # Get MAC address if available
            self._mac_address = raw.get("macAddress")

        except Exception as e:
            _LOGGER.error("Failed to update device tracker for %s: %s", self._name, e)
            self._is_connected = False
