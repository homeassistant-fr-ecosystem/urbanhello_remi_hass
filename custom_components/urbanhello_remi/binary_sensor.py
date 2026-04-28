import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import BRAND_NAME, DOMAIN, get_device_info
from .coordinator import RemiCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, _config_entry, async_add_entities):
    """Set up binary sensors for Rémi devices."""
    api = hass.data[DOMAIN]["api"]
    devices = hass.data[DOMAIN]["devices"]
    coordinators = hass.data[DOMAIN]["coordinators"]

    binary_sensors = []
    for device in devices:
        device_id = device["objectId"]
        device_name = device.get("name", "Rémi")
        coordinator = coordinators.get(device_id)

        if not coordinator:
            _LOGGER.error(
                "No coordinator found for device %s (%s)", device_name, device_id
            )
            continue

        binary_sensors.append(RemiConnectivityBinarySensor(coordinator, api, device))
        binary_sensors.append(RemiAliveBinarySensor(coordinator, device))
        binary_sensors.append(RemiFirmwareUpdateBinarySensor(coordinator, device))

    async_add_entities(binary_sensors)


class RemiConnectivityBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of a Rémi connectivity binary sensor."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "connectivity"

    def __init__(self, coordinator: RemiCoordinator, api, device):
        """Initialize the connectivity binary sensor."""
        super().__init__(coordinator)
        self._api = api
        self._device = device
        self._device_name = device.get("name", "Rémi")
        self._device_id = device["objectId"]

        self._attr_name = f"{BRAND_NAME} {self._device_name} Connectivity"
        self._attr_unique_id = f"{self._device_id}_connectivity"

    @property
    def device_info(self):
        """Return device information to link the entity to the integration."""
        return get_device_info(DOMAIN, self._device_id, self._device_name, self._device)

    @property
    def is_on(self):
        """Return true if the device is connected."""
        if self.coordinator.data and "device_info" in self.coordinator.data:
            device_info = self.coordinator.data["device_info"]
            raw = device_info.get("raw", {})
            online = raw.get("online")
            return online if online is not None else False
        return False

    @property
    def available(self):
        """Return True if entity is available."""
        return self.coordinator.last_update_success

    @property
    def extra_state_attributes(self):
        """Return additional attributes."""
        return {
            "online": self.is_on,
        }


class RemiAliveBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of a Rémi alive binary sensor."""

    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "alive"

    def __init__(self, coordinator: RemiCoordinator, device):
        super().__init__(coordinator)
        self._device = device
        self._device_name = device.get("name", "Rémi")
        self._device_id = device["objectId"]
        self._attr_unique_id = f"{self._device_id}_alive"

    @property
    def device_info(self):
        return get_device_info(DOMAIN, self._device_id, self._device_name, self._device)

    @property
    def is_on(self):
        if self.coordinator.data and "device_info" in self.coordinator.data:
            raw = self.coordinator.data["device_info"].get("raw", {})
            alive = raw.get("alive")
            return bool(alive) if alive is not None else False
        return False

    @property
    def available(self):
        return self.coordinator.last_update_success


class RemiFirmwareUpdateBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor that indicates whether a firmware update is available."""

    _attr_device_class = BinarySensorDeviceClass.UPDATE
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "firmware_update"

    def __init__(self, coordinator: RemiCoordinator, device):
        super().__init__(coordinator)
        self._device = device
        self._device_name = device.get("name", "Rémi")
        self._device_id = device["objectId"]
        self._attr_unique_id = f"{self._device_id}_firmware_update"

    @property
    def device_info(self):
        return get_device_info(DOMAIN, self._device_id, self._device_name, self._device)

    @property
    def is_on(self):
        if self.coordinator.data and "device_info" in self.coordinator.data:
            raw = self.coordinator.data["device_info"].get("raw", {})
            current = raw.get("current_firmware_version")
            latest = raw.get("latest_firmware_version")
            if current and latest:
                return current != latest
        return False

    @property
    def available(self):
        return self.coordinator.last_update_success

    @property
    def extra_state_attributes(self):
        if self.coordinator.data and "device_info" in self.coordinator.data:
            raw = self.coordinator.data["device_info"].get("raw", {})
            return {
                "current_version": raw.get("current_firmware_version"),
                "latest_version": raw.get("latest_firmware_version"),
            }
        return {}
