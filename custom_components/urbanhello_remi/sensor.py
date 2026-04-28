import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    EntityCategory,
    UnitOfIlluminance,
    UnitOfSignalStrength,
    UnitOfTemperature,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, get_device_info
from .coordinator import RemiCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, _config_entry, async_add_entities):
    """Set up sensor entities for Rémi devices."""
    devices = hass.data[DOMAIN]["devices"]
    coordinators = hass.data[DOMAIN]["coordinators"]

    sensors = []
    for device in devices:
        device_id = device["objectId"]
        device_name = device.get("name", "Rémi")
        coordinator = coordinators.get(device_id)

        if not coordinator:
            _LOGGER.error(
                "No coordinator found for device %s (%s)", device_name, device_id
            )
            continue

        sensors.append(RemiTemperatureSensor(coordinator, device))
        sensors.append(RemiLuminositySensor(coordinator, device))
        sensors.append(RemiFirmwareVersionSensor(coordinator, device))
        sensors.append(RemiRssiSensor(coordinator, device))
        sensors.append(RemiIpAddressSensor(coordinator, device))

    async_add_entities(sensors)


class RemiTemperatureSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Rémi temperature sensor."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_translation_key = "temperature"

    def __init__(self, coordinator: RemiCoordinator, device):
        """Initialize the temperature sensor."""
        super().__init__(coordinator)
        self._device = device
        self._device_name = device.get("name", "Rémi")
        self._device_id = device["objectId"]
        self._attr_unique_id = f"{self._device_id}_temperature"

    @property
    def device_info(self):
        """Return device information to link the entity to the integration."""
        return get_device_info(DOMAIN, self._device_id, self._device_name, self._device)

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self.coordinator.data and "device_info" in self.coordinator.data:
            temp = self.coordinator.data["device_info"].get("temperature")
            if temp is not None:
                try:
                    return float(temp) / 10.0
                except (ValueError, TypeError):
                    _LOGGER.warning(
                        "Invalid temperature value received for %s: %s", self.name, temp
                    )
        return None


class RemiLuminositySensor(CoordinatorEntity, SensorEntity):
    """Representation of a Rémi ambient luminosity sensor."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.ILLUMINANCE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfIlluminance.LUX
    _attr_translation_key = "luminosity"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: RemiCoordinator, device):
        super().__init__(coordinator)
        self._device = device
        self._device_name = device.get("name", "Rémi")
        self._device_id = device["objectId"]
        self._attr_unique_id = f"{self._device_id}_luminosity"

    @property
    def device_info(self):
        return get_device_info(DOMAIN, self._device_id, self._device_name, self._device)

    @property
    def native_value(self):
        if self.coordinator.data and "device_info" in self.coordinator.data:
            return self.coordinator.data["device_info"].get("luminosity")
        return None


class RemiFirmwareVersionSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Rémi firmware version sensor."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:chip"
    _attr_translation_key = "firmware_version"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: RemiCoordinator, device):
        super().__init__(coordinator)
        self._device = device
        self._device_name = device.get("name", "Rémi")
        self._device_id = device["objectId"]
        self._attr_unique_id = f"{self._device_id}_firmware_version"

    @property
    def device_info(self):
        return get_device_info(DOMAIN, self._device_id, self._device_name, self._device)

    @property
    def native_value(self):
        if self.coordinator.data and "device_info" in self.coordinator.data:
            raw = self.coordinator.data["device_info"].get("raw", {})
            return raw.get("current_firmware_version")
        return None


class RemiRssiSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Rémi WiFi signal strength sensor."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfSignalStrength.DECIBELS_MILLIWATT
    _attr_translation_key = "rssi"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: RemiCoordinator, device):
        super().__init__(coordinator)
        self._device = device
        self._device_name = device.get("name", "Rémi")
        self._device_id = device["objectId"]
        self._attr_unique_id = f"{self._device_id}_rssi"

    @property
    def device_info(self):
        return get_device_info(DOMAIN, self._device_id, self._device_name, self._device)

    @property
    def native_value(self):
        if self.coordinator.data and "device_info" in self.coordinator.data:
            raw = self.coordinator.data["device_info"].get("raw", {})
            return raw.get("rssi")
        return None


class RemiIpAddressSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Rémi IP address sensor."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:ip-network"
    _attr_translation_key = "ip_address"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: RemiCoordinator, device):
        super().__init__(coordinator)
        self._device = device
        self._device_name = device.get("name", "Rémi")
        self._device_id = device["objectId"]
        self._attr_unique_id = f"{self._device_id}_ip_address"

    @property
    def device_info(self):
        return get_device_info(DOMAIN, self._device_id, self._device_name, self._device)

    @property
    def native_value(self):
        if self.coordinator.data and "device_info" in self.coordinator.data:
            raw = self.coordinator.data["device_info"].get("raw", {})
            return raw.get("ipv4Address")
        return None
