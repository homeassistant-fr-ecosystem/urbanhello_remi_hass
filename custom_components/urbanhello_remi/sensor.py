from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, get_device_info
from .coordinator import RemiCoordinator
import logging

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up sensor entities for Rémi devices."""
    devices = hass.data[DOMAIN]["devices"]
    coordinators = hass.data[DOMAIN]["coordinators"]

    sensors = []
    for device in devices:
        device_id = device["objectId"]
        device_name = device.get("name", "Rémi")
        coordinator = coordinators.get(device_id)

        if not coordinator:
            _LOGGER.error("No coordinator found for device %s (%s)", device_name, device_id)
            continue

        sensors.append(RemiTemperatureSensor(coordinator, device))

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
                    _LOGGER.warning("Invalid temperature value received for %s: %s", self.name, temp)
        return None
