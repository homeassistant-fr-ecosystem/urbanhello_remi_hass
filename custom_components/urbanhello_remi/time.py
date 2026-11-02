"""Time platform for Rémi UrbanHello alarm clocks."""

from __future__ import annotations

import logging
from datetime import time
from typing import Any

from homeassistant.components.time import TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    build_alarm_key,
    build_alarm_unique_id,
    find_alarm,
    get_device_info,
)
from .coordinator import RemiCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    _entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Rémi alarm clock time entities."""
    api = hass.data[DOMAIN]["api"]
    devices = hass.data[DOMAIN]["devices"]
    coordinators = hass.data[DOMAIN]["coordinators"]

    entities = []
    for device in devices:
        device_id = device["objectId"]
        device_name = device.get("name", "Rémi")
        coordinator = coordinators.get(device_id)

        if not coordinator:
            _LOGGER.error(
                "No coordinator found for device %s (%s)", device_name, device_id
            )
            continue

        # Get alarms from coordinator data
        alarms_dict = coordinator.data.get("alarms", {}) if coordinator.data else {}
        _LOGGER.info(
            "Found %d alarms for device %s (%s)",
            len(alarms_dict),
            device_name,
            device_id,
        )

        # Create time entities for each alarm
        for alarm_object_id, _alarm_data in alarms_dict.items():
            entities.append(
                RemiAlarmTime(
                    coordinator=coordinator,
                    api=api,
                    device_id=device_id,
                    device_name=device_name,
                    device_data=device,
                    alarm_object_id=alarm_object_id,
                )
            )

    async_add_entities(entities)


class RemiAlarmTime(CoordinatorEntity, TimeEntity):
    """Representation of a Rémi alarm clock time."""

    _attr_translation_key = "alarm_time"

    def __init__(
        self,
        coordinator: RemiCoordinator,
        api,
        device_id: str,
        device_name: str,
        device_data: dict,
        alarm_object_id: str,
    ) -> None:
        """Initialize the alarm clock time entity."""
        super().__init__(coordinator)
        self._api = api
        self._device_id = device_id
        self._device_name = device_name
        self._device_data = device_data
        self._alarm_object_id = alarm_object_id

        # Set entity attributes with a stable, name-based unique_id
        # Entity naming must match remi-card expectations and switch entities
        alarms = coordinator.data.get("alarms", {}) if coordinator.data else {}
        alarm_data = alarms.get(alarm_object_id, {})
        alarm_name = alarm_data.get("name", "Alarm")
        self._alarm_key = build_alarm_key(alarm_object_id, alarm_data.get("name"), alarms)

        # Use alarm name for entity_id, stable key for unique_id
        alarm_name_slug = alarm_name.lower().replace(" ", "_")

        self._attr_name = f"{device_name} {alarm_name}"
        self._attr_unique_id = build_alarm_unique_id(
            device_id, alarm_object_id, alarm_name, alarms, "time"
        )
        self._attr_suggested_object_id = f"{device_name.lower()}_{alarm_name_slug}"

    def _resolve_alarm(self) -> tuple[str | None, dict[str, Any]]:
        """Return the current objectId and data of this alarm."""
        data = self.coordinator.data or {}
        alarms = data.get("alarms", {})
        return find_alarm(alarms, self._alarm_object_id, self._alarm_key)

    @property
    def alarm_object_id(self) -> str | None:
        """Return the alarm's current objectId, or None when it is gone."""
        object_id, _ = self._resolve_alarm()
        if object_id is not None:
            self._alarm_object_id = object_id
        return object_id

    @property
    def alarm_data(self) -> dict[str, Any]:
        """Get current alarm data from coordinator."""
        _, data = self._resolve_alarm()
        return data

    def _require_alarm_id(self) -> str:
        """Return the current objectId, or fail the action if the alarm is gone."""
        object_id = self.alarm_object_id
        if object_id is None:
            msg = f"Alarm '{self._attr_name}' no longer exists on the device"
            raise HomeAssistantError(msg)
        return object_id

    @property
    def native_value(self) -> time | None:
        """Return the current alarm time."""
        alarm_data = self.alarm_data
        time_str = alarm_data.get("time")

        if time_str:
            time_parts = time_str.split(":")
            if len(time_parts) >= 2:
                try:
                    hour = int(time_parts[0])
                    minute = int(time_parts[1])
                    return time(hour, minute)
                except (ValueError, IndexError):
                    pass

        # Unknown rather than a fabricated 07:00 when the alarm is gone or the
        # payload cannot be parsed.
        return None

    async def async_added_to_hass(self) -> None:
        """Run when entity is added to hass."""
        await super().async_added_to_hass()

        alarm_name = self.alarm_data.get("name", "Alarm")
        _LOGGER.info(
            "Initialized alarm time '%s' (objectId: %s) for device %s - Time: %s",
            alarm_name,
            self.alarm_object_id,
            self._device_id,
            self.native_value.strftime("%H:%M") if self.native_value else "N/A",
        )

    @property
    def device_info(self):
        """Return device information."""
        return get_device_info(
            DOMAIN, self._device_id, self._device_name, self._device_data
        )

    @property
    def icon(self) -> str:
        """Return the icon."""
        return "mdi:alarm"

    async def async_set_value(self, value: time) -> None:
        """Set the alarm time."""
        object_id = self._require_alarm_id()
        try:
            # Format time as HH:MM string for API
            time_str = value.strftime("%H:%M")

            # Update via API
            await self._api.update_alarm(
                self._device_id,
                object_id,
                time=time_str,
            )

            _LOGGER.info(
                "Set alarm '%s' (objectId: %s) time to %s for device %s",
                self.alarm_data.get("name", "Alarm"),
                object_id,
                time_str,
                self._device_id,
            )

            # Request immediate refresh from coordinator
            await self.coordinator.async_request_refresh()

        except Exception as e:
            _LOGGER.error(
                "Failed to set alarm time for %s: %s",
                object_id,
                e,
            )
            raise

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return super().available and self.alarm_object_id is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes for the alarm."""
        alarm_data = self.alarm_data
        attributes = {}

        alarm_name = alarm_data.get("name")
        if alarm_name is not None:
            attributes["name"] = alarm_name

        if self.alarm_object_id is not None:
            attributes["alarm_id"] = self.alarm_object_id

        brightness = alarm_data.get("brightness")
        if brightness is not None:
            attributes["brightness"] = brightness

        volume = alarm_data.get("volume")
        if volume is not None:
            attributes["volume"] = volume

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
            if face_name:
                attributes["face"] = face_name

        lightnight = alarm_data.get("lightnight")
        if lightnight is not None:
            attributes["lightnight"] = lightnight

        days = alarm_data.get("days")
        if days is not None:
            # Convert day indices to day names
            day_names = [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday",
            ]
            selected_days = [day_names[i] for i in days if i < len(day_names)]
            attributes["days"] = selected_days
            attributes["days_indices"] = days

        recurrence = alarm_data.get("recurrence")
        if recurrence is not None:
            attributes["recurrence"] = recurrence

        return attributes
