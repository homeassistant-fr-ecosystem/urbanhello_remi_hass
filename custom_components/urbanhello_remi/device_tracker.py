from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import ScannerEntity
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, BRAND_NAME, get_device_info
from .coordinator import RemiCoordinator
import logging

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up device tracker for Rémi devices."""
    api = hass.data[DOMAIN]["api"]
    devices = hass.data[DOMAIN]["devices"]
    coordinators = hass.data[DOMAIN]["coordinators"]

    trackers = []
    for device in devices:
        device_id = device["objectId"]
        device_name = device.get("name", "Rémi")
        coordinator = coordinators.get(device_id)

        if not coordinator:
            _LOGGER.error("No coordinator found for device %s (%s)", device_name, device_id)
            continue

        trackers.append(RemiDeviceTracker(coordinator, api, device))

    async_add_entities(trackers)


class RemiDeviceTracker(CoordinatorEntity, ScannerEntity):
    """Representation of a Rémi device tracker."""

    _attr_translation_key = "remi"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: RemiCoordinator, api, device):
        """Initialize the device tracker."""
        super().__init__(coordinator)
        self._api = api
        self._device = device
        self._device_name = device.get("name", "Rémi")
        self._device_id = device["objectId"]

        self._attr_name = f"{BRAND_NAME} {self._device_name}"
        self._attr_unique_id = f"{self._device_id}_device_tracker"

    @property
    def device_info(self):
        """Return device information to link the entity to the integration."""
        return get_device_info(DOMAIN, self._device_id, self._device_name, self._device)

    @property
    def source_type(self):
        """Return the source type of the device tracker."""
        return SourceType.ROUTER

    @property
    def is_connected(self):
        """Return true if the device is connected to the network."""
        if self.coordinator.data and "device_info" in self.coordinator.data:
            device_info = self.coordinator.data["device_info"]
            raw = device_info.get("raw", {})
            is_online = raw.get("online")
            return is_online if is_online is not None else False
        return False

    @property
    def ip_address(self):
        """Return the primary IP address of the device."""
        if self.coordinator.data and "device_info" in self.coordinator.data:
            device_info = self.coordinator.data["device_info"]
            raw = device_info.get("raw", {})
            return raw.get("ipv4Address")
        return None

    @property
    def mac_address(self):
        """Return the MAC address of the device."""
        if self.coordinator.data and "device_info" in self.coordinator.data:
            device_info = self.coordinator.data["device_info"]
            raw = device_info.get("raw", {})
            return raw.get("macAddress")
        return None

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        if self.is_connected:
            return "mdi:lan-connect"
        return "mdi:lan-disconnect"

    @property
    def extra_state_attributes(self):
        """Return additional attributes."""
        attributes = {}
        if self.ip_address:
            attributes["ip_address"] = self.ip_address
        if self.mac_address:
            attributes["mac_address"] = self.mac_address
        attributes["connected"] = self.is_connected
        return attributes
