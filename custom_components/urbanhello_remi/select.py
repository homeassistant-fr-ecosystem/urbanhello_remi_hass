import logging

from homeassistant.components.select import SelectEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    BRAND_NAME,
    DOMAIN,
    FACE_MAP_API_TO_HA,
    FACE_MAP_HA_TO_API,
    MUSIC_MODE_OPTIONS,
    get_device_info,
)
from .coordinator import RemiCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, _config_entry, async_add_entities):
    """Set up select entities for Rémi devices."""
    api = hass.data[DOMAIN]["api"]
    devices = hass.data[DOMAIN]["devices"]
    coordinators = hass.data[DOMAIN]["coordinators"]

    selects = []
    for device in devices:
        device_id = device["objectId"]
        device_name = device.get("name", "Rémi")
        coordinator = coordinators.get(device_id)

        if not coordinator:
            _LOGGER.error(
                "No coordinator found for device %s (%s)", device_name, device_id
            )
            continue

        selects.append(RemiFaceSelect(coordinator, api, device))
        selects.append(RemiClockFormatSelect(coordinator, api, device))
        selects.append(RemiMusicModeSelect(coordinator, api, device))

    async_add_entities(selects)


class RemiFaceSelect(CoordinatorEntity, SelectEntity):
    """Representation of a Rémi face selector."""

    _attr_translation_key = "face"

    def __init__(self, coordinator: RemiCoordinator, api, device):
        """Initialize the face select entity."""
        super().__init__(coordinator)
        self._api = api
        self._device = device
        self._device_name = device.get("name", "Rémi")
        self._device_id = device["objectId"]

        self._attr_name = f"{BRAND_NAME} {self._device_name} Face"
        self._attr_unique_id = f"{self._device_id}_face_select"

    @property
    def device_info(self):
        """Return device information to link the entity to the integration."""
        return get_device_info(DOMAIN, self._device_id, self._device_name, self._device)

    @property
    def current_option(self):
        """Return the currently selected face."""
        if self.coordinator.data and "device_info" in self.coordinator.data:
            device_info = self.coordinator.data["device_info"]
            face_id = device_info.get("face")
            if face_id:
                # Reverse lookup face name from ID
                for name, fid in self._api.faces.items():
                    if fid == face_id:
                        return FACE_MAP_API_TO_HA.get(name, name)
        return None

    @property
    def options(self):
        """Return the list of available faces."""
        if self._api.faces:
            return sorted(
                [FACE_MAP_API_TO_HA.get(name, name) for name in self._api.faces]
            )
        return list(FACE_MAP_API_TO_HA.values())

    @property
    def icon(self):
        """Return the icon to use in the frontend based on current face."""
        current_face = self.current_option
        if current_face is None:
            return "mdi:emoticon-neutral-outline"

        face_lower = current_face.lower()

        # Map face names to appropriate icons
        icons = {
            "sleep": "mdi:sleep",
            "awake": "mdi:emoticon-happy",
            "blank": "mdi:emoticon-neutral",
            "semi": "mdi:emoticon-cool",
            "smily": "mdi:emoticon-happy-outline",
            "smile": "mdi:emoticon-happy-outline",
        }

        for key, icon in icons.items():
            if key in face_lower:
                return icon

        return "mdi:emoticon-outline"

    async def async_select_option(self, option: str) -> None:
        """Change the selected face."""
        try:
            api_option = FACE_MAP_HA_TO_API.get(option, option)
            await self._api.set_face_by_name(self._device_id, api_option)
            _LOGGER.info("Changed face to %s for %s", option, self._attr_name)

            # Request immediate refresh from coordinator
            await self.coordinator.async_request_refresh()

        except Exception as e:
            _LOGGER.error("Failed to set face for %s: %s", self._attr_name, e)
            raise


class RemiClockFormatSelect(CoordinatorEntity, SelectEntity):
    """Select entity to choose 12h or 24h clock display format."""

    _attr_translation_key = "clock_format"
    _attr_options = ["12h", "24h"]
    _attr_icon = "mdi:clock-outline"

    def __init__(self, coordinator: RemiCoordinator, api, device):
        super().__init__(coordinator)
        self._api = api
        self._device = device
        self._device_name = device.get("name", "Rémi")
        self._device_id = device["objectId"]
        self._attr_name = f"{BRAND_NAME} {self._device_name} Clock Format"
        self._attr_unique_id = f"{self._device_id}_clock_format"

    @property
    def device_info(self):
        return get_device_info(DOMAIN, self._device_id, self._device_name, self._device)

    @property
    def current_option(self):
        if self.coordinator.data and "device_info" in self.coordinator.data:
            use_24h = self.coordinator.data["device_info"].get("hour_format_24")
            if use_24h is None:
                return None
            return "24h" if use_24h else "12h"
        return None

    async def async_select_option(self, option: str) -> None:
        try:
            await self._api.set_clock_format(self._device_id, option == "24h")
            await self.coordinator.async_request_refresh()
        except Exception as e:
            _LOGGER.error("Failed to set clock format for %s: %s", self._attr_name, e)
            raise


class RemiMusicModeSelect(CoordinatorEntity, SelectEntity):
    """Select entity to choose the music mode."""

    _attr_translation_key = "music_mode"
    _attr_icon = "mdi:music"

    def __init__(self, coordinator: RemiCoordinator, api, device):
        super().__init__(coordinator)
        self._api = api
        self._device = device
        self._device_name = device.get("name", "Rémi")
        self._device_id = device["objectId"]
        self._attr_name = f"{BRAND_NAME} {self._device_name} Music Mode"
        self._attr_unique_id = f"{self._device_id}_music_mode"
        self._attr_options = list(MUSIC_MODE_OPTIONS.values())

    @property
    def device_info(self):
        return get_device_info(DOMAIN, self._device_id, self._device_name, self._device)

    @property
    def current_option(self):
        if self.coordinator.data and "device_info" in self.coordinator.data:
            mode = self.coordinator.data["device_info"].get("music_mode")
            if mode is None:
                return None
            return MUSIC_MODE_OPTIONS.get(mode)
        return None

    async def async_select_option(self, option: str) -> None:
        try:
            mode = next(k for k, v in MUSIC_MODE_OPTIONS.items() if v == option)
            await self._api.set_music_mode(self._device_id, mode)
            await self.coordinator.async_request_refresh()
        except StopIteration:
            _LOGGER.error("Unknown music mode option: %s", option)
        except Exception as e:
            _LOGGER.error("Failed to set music mode for %s: %s", self._attr_name, e)
            raise
