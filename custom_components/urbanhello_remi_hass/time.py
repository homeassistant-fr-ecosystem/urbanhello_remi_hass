"""Time platform for Rémi UrbanHello alarm clocks."""
from __future__ import annotations

from datetime import time
import logging
from typing import Any

from homeassistant.components.time import TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, get_device_info

_LOGGER = logging.getLogger(__name__)

# Number of alarm clocks per device
MAX_ALARMS = 10


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Rémi alarm clock time entities."""
    api = hass.data[DOMAIN]["api"]
    devices = hass.data[DOMAIN]["devices"]

    entities = []
    for device in devices:
        device_id = device["objectId"]
        device_name = device.get("name", "Rémi")

        # Create multiple alarm clock time entities per device
        for alarm_num in range(1, MAX_ALARMS + 1):
            entities.append(
                RemiAlarmTime(
                    api=api,
                    device_id=device_id,
                    device_name=device_name,
                    device_data=device,
                    alarm_number=alarm_num,
                )
            )

    async_add_entities(entities)


class RemiAlarmTime(TimeEntity):
    """Representation of a Rémi alarm clock time."""

    def __init__(
        self,
        api,
        device_id: str,
        device_name: str,
        device_data: dict,
        alarm_number: int,
    ) -> None:
        """Initialize the alarm clock time entity."""
        self._api = api
        self._device_id = device_id
        self._device_name = device_name
        self._device_data = device_data
        self._alarm_number = alarm_number
        self._attr_name = f"{device_name} Alarm {alarm_number} Time"
        self._attr_unique_id = f"{device_id}_alarm_{alarm_number}_time"

        # Default to 7:00 AM
        self._attr_native_value = time(7, 0)

        # Additional alarm attributes
        self._alarm_name = None
        self._brightness = None
        self._volume = None
        self._face = None
        self._lightnight = None
        self._alarm_object_id = None
        self._days = None
        self._recurrence = None

    async def async_added_to_hass(self) -> None:
        """Run when entity is added to hass - initialize from API or use defaults."""
        await super().async_added_to_hass()

        # Try to load alarm from Remi API
        try:
            alarms = await self._api.get_alarms(self._device_id, refresh=True)
            if alarms and len(alarms) >= self._alarm_number:
                # Get the alarm for this number (1-indexed)
                alarm = alarms[self._alarm_number - 1]

                # Store all alarm attributes
                self._alarm_object_id = alarm.get("objectId")
                self._alarm_name = alarm.get("name", "")
                self._brightness = alarm.get("brightness")
                self._volume = alarm.get("volume")
                self._lightnight = alarm.get("lightnight")
                self._days = alarm.get("days", [])
                self._recurrence = alarm.get("recurrence", [])

                # Resolve face name from face pointer
                face_obj = alarm.get("face")
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

                # Update entity name and unique_id with alarm name and objectId
                if self._alarm_name:
                    self._attr_name = f"{self._device_name} {self._alarm_name} Time"
                if self._alarm_object_id:
                    self._attr_unique_id = f"{self._device_id}_alarm_{self._alarm_object_id}_time"

                if "time" in alarm:
                    # Parse time from API (format might be "HH:MM" or other)
                    time_str = alarm["time"]
                    time_parts = time_str.split(":")
                    if len(time_parts) >= 2:
                        hour = int(time_parts[0])
                        minute = int(time_parts[1])
                        self._attr_native_value = time(hour, minute)
                        _LOGGER.info(
                            "Initialized alarm %d (%s) time from API: %s for device %s",
                            self._alarm_number,
                            self._alarm_name,
                            time_str,
                            self._device_id,
                        )
                        return  # Successfully loaded from API, done
        except Exception as e:
            _LOGGER.debug(
                "Could not load alarm %d from API (may not exist): %s",
                self._alarm_number,
                e,
            )

        # Use default time (7:00 AM)
        _LOGGER.debug(
            "Using default time 07:00 for alarm %d on device %s",
            self._alarm_number,
            self._device_id,
        )

    @property
    def device_info(self):
        """Return device information."""
        return get_device_info(DOMAIN, self._device_id, self._device_name, self._device_data)

    @property
    def icon(self) -> str:
        """Return the icon."""
        return "mdi:alarm"

    async def async_set_value(self, value: time) -> None:
        """Set the alarm time."""
        self._attr_native_value = value

        # Store in hass.data for persistence
        alarm_key = f"alarm_{self._alarm_number}_time"
        if self._device_id not in self.hass.data[DOMAIN]["alarm_times"]:
            self.hass.data[DOMAIN]["alarm_times"][self._device_id] = {}
        self.hass.data[DOMAIN]["alarm_times"][self._device_id][alarm_key] = value

        _LOGGER.debug(
            "Set alarm %d time to %s for device %s",
            self._alarm_number,
            value.strftime("%H:%M"),
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
        attributes = {
            "alarm_number": self._alarm_number,
        }

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
