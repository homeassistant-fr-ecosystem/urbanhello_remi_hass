from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfTemperature,
)
from homeassistant.util import slugify

from .coordinator import RemiCoordinator
from .entity import RemiEntity

LIGHT_LUX = "lx"

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(_hass, entry, async_add_entities):
    """Set up sensor entities for Rémi devices."""
    devices = entry.runtime_data.devices
    coordinators = entry.runtime_data.coordinators

    sensors = []
    for device in devices:
        device_id = device["objectId"]
        coordinator = coordinators.get(device_id)

        if not coordinator:
            _LOGGER.error(
                "No coordinator found for device %s (%s)",
                device.get("name", "Rémi"),
                device_id,
            )
            continue

        sensors.append(RemiTemperatureSensor(coordinator, device))
        sensors.append(RemiLuminositySensor(coordinator, device))
        sensors.append(RemiFirmwareVersionSensor(coordinator, device))
        sensors.append(RemiRssiSensor(coordinator, device))
        sensors.append(RemiIpAddressSensor(coordinator, device))

    async_add_entities(sensors)


class RemiTemperatureSensor(RemiEntity, SensorEntity):
    """Representation of a Rémi temperature sensor."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_translation_key = "temperature"

    def __init__(self, coordinator: RemiCoordinator, device):
        """Initialize the temperature sensor."""
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{self._device_id}_temperature"
        self._attr_suggested_object_id = (
            f"{slugify(self._device_name)}_temperature"
        )

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
                        "Invalid temperature value received for %s: %s",
                        self.name,
                        temp,
                    )
        return None


class RemiLuminositySensor(RemiEntity, SensorEntity):
    """Representation of a Rémi ambient luminosity sensor."""

    _attr_device_class = SensorDeviceClass.ILLUMINANCE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = LIGHT_LUX
    _attr_translation_key = "luminosity"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: RemiCoordinator, device):
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{self._device_id}_luminosity"
        self._attr_suggested_object_id = (
            f"{slugify(self._device_name)}_luminosity"
        )

    @property
    def native_value(self):
        if self.coordinator.data and "device_info" in self.coordinator.data:
            return self.coordinator.data["device_info"].get("luminosity")
        return None


class RemiFirmwareVersionSensor(RemiEntity, SensorEntity):
    """Representation of a Rémi firmware version sensor."""

    _attr_icon = "mdi:chip"
    _attr_translation_key = "firmware_version"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: RemiCoordinator, device):
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{self._device_id}_firmware_version"
        self._attr_suggested_object_id = (
            f"{slugify(self._device_name)}_firmware_version"
        )

    @property
    def native_value(self):
        if self.coordinator.data and "device_info" in self.coordinator.data:
            raw = self.coordinator.data["device_info"].get("raw", {})
            return raw.get("current_firmware_version")
        return None


class RemiRssiSensor(RemiEntity, SensorEntity):
    """Representation of a Rémi WiFi signal strength sensor."""

    _attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
    _attr_translation_key = "rssi"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: RemiCoordinator, device):
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{self._device_id}_rssi"
        self._attr_suggested_object_id = (
            f"{slugify(self._device_name)}_rssi"
        )

    @property
    def native_value(self):
        if self.coordinator.data and "device_info" in self.coordinator.data:
            raw = self.coordinator.data["device_info"].get("raw", {})
            return raw.get("rssi")
        return None


class RemiIpAddressSensor(RemiEntity, SensorEntity):
    """Representation of a Rémi IP address sensor."""

    _attr_icon = "mdi:ip-network"
    _attr_translation_key = "ip_address"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: RemiCoordinator, device):
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{self._device_id}_ip_address"
        self._attr_suggested_object_id = (
            f"{slugify(self._device_name)}_ip_address"
        )

    @property
    def native_value(self):
        if self.coordinator.data and "device_info" in self.coordinator.data:
            raw = self.coordinator.data["device_info"].get("raw", {})
            return raw.get("ipv4Address")
        return None
