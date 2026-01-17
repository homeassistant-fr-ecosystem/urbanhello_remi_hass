"""Switch platform for Rémi UrbanHello alarm clocks."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, BRAND_NAME, get_device_info

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Rémi alarm clock switch entities."""
    api = hass.data[DOMAIN]["api"]
    devices = hass.data[DOMAIN]["devices"]

    entities = []
    for device in devices:
        device_id = device["objectId"]
        device_name = device.get("name", "Rémi")

        alarms = await api.get_alarms(device_id, refresh=True)
        _LOGGER.info(
                "Found %d alarms for device %s (%s)",
                len(alarms) if alarms else 0,
                device_name,
                device_id,
        )

        # Create switch entities only for alarms that exist
        if alarms:
            for alarm in alarms:
                alarm_object_id = alarm.get("objectId")

                if alarm_object_id:
                    entities.append(
                        RemiAlarmSwitch(
                            api=api,
                            device_id=device_id,
                            device_name=device_name,
                            device_data=device,
                            alarm_data=alarm,
                        )
                    )

    async_add_entities(entities)


class RemiAlarmSwitch(SwitchEntity):
    """Representation of a Rémi alarm clock enable/disable switch."""

    def __init__(
        self,
        api,
        device_id: str,
        device_name: str,
        device_data: dict,
        alarm_data: dict,
    ) -> None:
        """Initialize the alarm clock switch entity."""
        self._api = api
        self._device_id = device_id
        self._device_name = device_name
        self._device_data = device_data
        self._attr_is_on = False

        # Additional alarm attributes
        self._alarm_object_id = alarm_data.get("objectId")
        self._alarm_name = alarm_data.get("name", "Alarm")
        self._brightness = alarm_data.get("brightness")
        self._volume = alarm_data.get("volume")
        self._lightnight = alarm_data.get("lightnight")
        self._days = alarm_data.get("days", [])
        self._recurrence = alarm_data.get("recurrence", [])
        # Resolve face name from face pointer
        face_obj = alarm_data.get("face")
        if isinstance(face_obj, dict) and face_obj.get("objectId"):
            face_id = face_obj.get("objectId")
            # Look up face name from API faces cache
            face_name = None
            for name, fid in self._api.faces.items():
                if fid == face_id:
                    face_name = name
                    break
                self._face = face_name
        else:
            self._face = None

        # Set entity attributes with correct objectId-based unique_id
        self._attr_name = f"{device_name} {self._alarm_name}"
        self._attr_unique_id = f"{BRAND_NAME}_{device_id}_alarm_{self._alarm_object_id}"
        if "enabled" in alarm_data:
            self._attr_is_on = bool(alarm_data.get("enabled"))
            _LOGGER.info(
                "Initialized alarm (%s) state from API: %s for device %s",
                self._alarm_name,
                "enabled" if self._attr_is_on else "disabled",
                self._device_id,
            )

    async def async_added_to_hass(self) -> None:
        """Run when entity is added to hass - initialize from API or use defaults."""
        await super().async_added_to_hass()

        # Use default state (disabled)
        _LOGGER.debug(
            "Using default state (disabled) for alarm %s on device %s",
            self._alarm_name,
            self._device_id,
        )

    @property
    def device_info(self):
        """Return device information."""
        return get_device_info(DOMAIN, self._device_id, self._device_name, self._device_data)

    @property
    def icon(self) -> str:
        """Return the icon."""
        if self._attr_is_on:
            return "mdi:alarm-check"
        return "mdi:alarm-off"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the alarm clock on."""
        self._attr_is_on = True

        # Store state
        alarm_key = f"alarm_{self._alarm_number}_enabled"
        if self._device_id not in self.hass.data[DOMAIN]["alarm_states"]:
            self.hass.data[DOMAIN]["alarm_states"][self._device_id] = {}
        self.hass.data[DOMAIN]["alarm_states"][self._device_id][alarm_key] = True

        _LOGGER.info(
            "Enabled alarm clock %d for device %s",
            self._alarm_number,
            self._device_id,
        )

        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the alarm clock off."""
        self._attr_is_on = False

        # Store state
        alarm_key = f"alarm_{self._alarm_number}_enabled"
        if self._device_id not in self.hass.data[DOMAIN]["alarm_states"]:
            self.hass.data[DOMAIN]["alarm_states"][self._device_id] = {}
        self.hass.data[DOMAIN]["alarm_states"][self._device_id][alarm_key] = False

        _LOGGER.info(
            "Disabled alarm clock %d for device %s",
            self._alarm_number,
            self._device_id,
        )

        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return True

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes for the alarm."""
        attributes = {}

        if self._alarm_name is not None:
            attributes["name"] = self._alarm_name

        if self._alarm_object_id is not None:
            attributes["alarm_id"] = self._alarm_object_id

        if self._brightness is not None:
            attributes["brightness"] = self._brightness

        if self._volume is not None:
            attributes["volume"] = self._volume

        if self._face is not None:
            attributes["face"] = self._face

        if self._lightnight is not None:
            attributes["lightnight"] = self._lightnight

        if self._days is not None:
            # Convert day indices to day names
            day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            selected_days = [day_names[i] for i in self._days if i < len(day_names)]
            attributes["days"] = selected_days
            attributes["days_indices"] = self._days

        if self._recurrence is not None:
            attributes["recurrence"] = self._recurrence

        return attributes
