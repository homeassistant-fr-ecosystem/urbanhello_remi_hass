from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, BRAND_NAME, get_device_info
from .coordinator import RemiCoordinator
import logging

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up number entities for Rémi devices."""
    api = hass.data[DOMAIN]["api"]
    devices = hass.data[DOMAIN]["devices"]
    coordinators = hass.data[DOMAIN]["coordinators"]

    numbers = []
    for device in devices:
        device_id = device["objectId"]
        device_name = device.get("name", "Rémi")
        coordinator = coordinators.get(device_id)

        if not coordinator:
            _LOGGER.error("No coordinator found for device %s (%s)", device_name, device_id)
            continue

        numbers.append(RemiVolumeNumber(coordinator, api, device))
        numbers.append(RemiNoiseThresholdNumber(coordinator, api, device))
        numbers.append(RemiNightFaceLevel(coordinator, api, device))

    async_add_entities(numbers)


class RemiVolumeNumber(CoordinatorEntity, NumberEntity):
    """Representation of a Rémi volume control."""

    _attr_translation_key = "volume"
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: RemiCoordinator, api, device):
        """Initialize the volume number entity."""
        super().__init__(coordinator)
        self._api = api
        self._device = device
        self._device_name = device.get("name", "Rémi")
        self._device_id = device["objectId"]

        self._attr_name = f"{BRAND_NAME} {self._device_name} Volume"
        self._attr_unique_id = f"{self._device_id}_volume_control"

    @property
    def device_info(self):
        """Return device information to link the entity to the integration."""
        return get_device_info(DOMAIN, self._device_id, self._device_name, self._device)

    @property
    def native_value(self):
        """Return the current volume level."""
        if self.coordinator.data and "device_info" in self.coordinator.data:
            device_info = self.coordinator.data["device_info"]
            return device_info.get("volume")
        return None

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        volume = self.native_value or 0
        if volume == 0:
            return "mdi:volume-off"
        elif volume < 33:
            return "mdi:volume-low"
        elif volume < 66:
            return "mdi:volume-medium"
        else:
            return "mdi:volume-high"

    async def async_set_native_value(self, value: float) -> None:
        """Set the volume level."""
        try:
            volume_int = int(value)
            await self._api.set_volume(self._device_id, volume_int)
            _LOGGER.debug("Set volume to %d for %s", volume_int, self._attr_name)

            # Request immediate refresh from coordinator
            await self.coordinator.async_request_refresh()

        except Exception as e:
            _LOGGER.error("Failed to set volume for %s: %s", self._attr_name, e)
            raise


class RemiNoiseThresholdNumber(CoordinatorEntity, NumberEntity):
    """Representation of a Rémi noise notification threshold control."""

    _attr_translation_key = "noise_threshold"
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: RemiCoordinator, api, device):
        """Initialize the noise threshold number entity."""
        super().__init__(coordinator)
        self._api = api
        self._device = device
        self._device_name = device.get("name", "Rémi")
        self._device_id = device["objectId"]

        self._attr_name = f"{BRAND_NAME} {self._device_name} Noise Threshold"
        self._attr_unique_id = f"{self._device_id}_noise_threshold"

    @property
    def device_info(self):
        """Return device information to link the entity to the integration."""
        return get_device_info(DOMAIN, self._device_id, self._device_name, self._device)

    @property
    def native_value(self):
        """Return the current noise threshold level."""
        if self.coordinator.data and "device_info" in self.coordinator.data:
            device_info = self.coordinator.data["device_info"]
            raw = device_info.get("raw", {})
            return raw.get("noise_notification_threshold")
        return None

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        threshold = self.native_value or 0
        if threshold == 0:
            return "mdi:volume-off"
        elif threshold < 33:
            return "mdi:volume-low"
        elif threshold < 66:
            return "mdi:volume-medium"
        else:
            return "mdi:volume-high"

    async def async_set_native_value(self, value: float) -> None:
        """Set the noise threshold level."""
        try:
            threshold_int = int(value)
            await self._api.set_noise_threshold(self._device_id, threshold_int)
            _LOGGER.debug("Set noise threshold to %d for %s", threshold_int, self._attr_name)

            # Request immediate refresh from coordinator
            await self.coordinator.async_request_refresh()

        except Exception as e:
            _LOGGER.error("Failed to set noise threshold for %s: %s", self._attr_name, e)
            raise


class RemiNightFaceLevel(CoordinatorEntity, NumberEntity):
    """Representation of a Rémi night face level control."""

    _attr_translation_key = "night_face_level"
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: RemiCoordinator, api, device):
        """Initialize the night face level number entity."""
        super().__init__(coordinator)
        self._api = api
        self._device = device
        self._device_name = device.get("name", "Rémi")
        self._device_id = device["objectId"]

        self._attr_name = f"{BRAND_NAME} {self._device_name} Night Face Level"
        self._attr_unique_id = f"{self._device_id}_night_face_level"

    @property
    def device_info(self):
        """Return device information to link the entity to the integration."""
        return get_device_info(DOMAIN, self._device_id, self._device_name, self._device)

    @property
    def native_value(self):
        """Return the current night face level."""
        if self.coordinator.data and "device_info" in self.coordinator.data:
            device_info = self.coordinator.data["device_info"]
            return device_info.get("light_min")
        return None

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        level = self.native_value or 0
        if level == 0:
            return "mdi:brightness-1"
        elif level < 33:
            return "mdi:brightness-4"
        elif level < 66:
            return "mdi:brightness-5"
        else:
            return "mdi:brightness-6"

    async def async_set_native_value(self, value: float) -> None:
        """Set the night face level."""
        try:
            level_int = int(value)
            await self._api.set_night_luminosity(self._device_id, level_int)
            _LOGGER.debug("Set night face level to %d for %s", level_int, self._attr_name)

            # Request immediate refresh from coordinator
            await self.coordinator.async_request_refresh()

        except Exception as e:
            _LOGGER.error("Failed to set night face level for %s: %s", self._attr_name, e)
            raise
