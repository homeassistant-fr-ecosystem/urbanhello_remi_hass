"""DataUpdateCoordinator for Remi device and alarm updates."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import RemiAPI, RemiAPIError

_LOGGER = logging.getLogger(__name__)

# Update interval for polling device state from the API
UPDATE_INTERVAL = timedelta(minutes=1)


class RemiCoordinator(DataUpdateCoordinator):
    """Coordinator to manage fetching Remi device and alarm data from the API."""

    def __init__(self, hass: HomeAssistant, api: RemiAPI, device_id: str, device_name: str) -> None:
        """Initialize the coordinator.

        Args:
            hass: Home Assistant instance
            api: RemiAPI instance
            device_id: The Remi device objectId
            device_name: Human-readable device name
        """
        self.api = api
        self.device_id = device_id
        self.device_name = device_name

        super().__init__(
            hass,
            _LOGGER,
            name=f"Remi {device_name}",
            update_interval=UPDATE_INTERVAL,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch device info and alarm data from the API.

        Returns:
            Dictionary with device_info and alarms data
        """
        try:
            # Fetch fresh device info from API
            device_info = await self.api.get_remi_info(self.device_id, refresh=True)

            # Fetch fresh alarm data from API
            alarms = await self.api.get_alarms(self.device_id, refresh=True)

            # Convert list of alarms to dictionary keyed by objectId
            alarm_dict = {}
            for alarm in alarms:
                alarm_id = alarm.get("objectId")
                if alarm_id:
                    alarm_dict[alarm_id] = alarm

            _LOGGER.debug(
                "Updated data for device %s (%s): %d alarms, temp=%s, face=%s",
                self.device_name,
                self.device_id,
                len(alarm_dict),
                device_info.get("temperature"),
                device_info.get("face"),
            )

            # Return combined data structure
            return {
                "device_info": device_info,
                "alarms": alarm_dict,
            }

        except RemiAPIError as err:
            raise UpdateFailed(f"Error fetching data for {self.device_name}: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error fetching data for {self.device_name}: {err}") from err
