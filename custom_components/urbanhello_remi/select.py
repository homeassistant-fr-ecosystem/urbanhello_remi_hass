from homeassistant.components.select import SelectEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, BRAND_NAME, get_device_info
from .coordinator import RemiCoordinator
import logging

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
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
            _LOGGER.error("No coordinator found for device %s (%s)", device_name, device_id)
            continue

        selects.append(RemiFaceSelect(coordinator, api, device))

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
                        return name
        return None

    @property
    def options(self):
        """Return the list of available faces."""
        if self._api.faces:
            return sorted(list(self._api.faces.keys()))
        return ["sleepyFace", "awakeFace", "blankFace", "semiAwakeFace", "smilyFace"]

    @property
    def icon(self):
        """Return the icon to use in the frontend based on current face."""
        current_face = self.current_option
        if current_face is None:
            return "mdi:emoticon-neutral-outline"

        face_lower = current_face.lower()

        # Map face names to appropriate icons
        if "sleepy" in face_lower or "sleep" in face_lower:
            return "mdi:sleep"
        elif "awake" in face_lower:
            return "mdi:emoticon-happy"
        elif "blank" in face_lower:
            return "mdi:emoticon-neutral"
        elif "semiawake" in face_lower:
            return "mdi:emoticon-cool"
        elif "smily" in face_lower or "smile" in face_lower:
            return "mdi:emoticon-happy-outline"
        else:
            return "mdi:emoticon-outline"

    async def async_select_option(self, option: str) -> None:
        """Change the selected face."""
        try:
            await self._api.set_face_by_name(self._device_id, option)
            _LOGGER.info("Changed face to %s for %s", option, self._attr_name)

            # Request immediate refresh from coordinator
            await self.coordinator.async_request_refresh()

        except Exception as e:
            _LOGGER.error("Failed to set face for %s: %s", self._attr_name, e)
            raise
