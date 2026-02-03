from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .api import RemiAPI
from .const import DOMAIN
from .coordinator import RemiCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the Remi integration."""
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Rémi from a config entry."""
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    # Create an API instance
    api = RemiAPI(entry.data["username"], entry.data["password"])
    await api.login()
    hass.data[DOMAIN]["api"] = api

    # Get scan interval from options, default to 60 seconds
    scan_interval = entry.options.get("scan_interval", 60)

    # Retrieve and store details of all Rémi devices
    devices = []
    for remi in api.remis:
        try:
            # Handle both dict and string formats
            if isinstance(remi, dict):
                remi_id = remi.get("objectId")
            else:
                remi_id = remi

            if remi_id:
                device_info = await api.get_remi_info(remi_id)
                device_info["objectId"] = remi_id  # Add ID to the object

                # Extract version information from raw data
                raw = device_info.get("raw", {})
                device_info["sw_version"] = raw.get("currentFirmwareVersion")
                device_info["hw_version"] = raw.get("currentBluetoothVersion")

                devices.append(device_info)
        except Exception as e:
            _LOGGER.error("Failed to fetch device info for Remi ID %s: %s", remi_id if 'remi_id' in locals() else remi, e)

    hass.data[DOMAIN]["devices"] = devices

    # Initialize coordinators for each device
    coordinators = {}
    for device in devices:
        device_id = device["objectId"]
        device_name = device.get("name", "Rémi")

        coordinator = RemiCoordinator(hass, api, device_id, device_name, update_interval=scan_interval)
        # Perform initial refresh
        await coordinator.async_config_entry_first_refresh()
        coordinators[device_id] = coordinator

    hass.data[DOMAIN]["coordinators"] = coordinators

    # Register update listener
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    # Forward setup to all platforms
    await hass.config_entries.async_forward_entry_setups(
        entry, ["light", "sensor", "binary_sensor", "number", "device_tracker", "select", "time", "switch"]
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, ["light", "sensor", "binary_sensor", "number", "device_tracker", "select", "time", "switch"]
    )

    if unload_ok:
        # Close the API session
        if DOMAIN in hass.data and "api" in hass.data[DOMAIN]:
            api = hass.data[DOMAIN]["api"]
            await api.close()

        # Clean up stored data
        hass.data[DOMAIN].pop("api", None)
        hass.data[DOMAIN].pop("devices", None)
        hass.data[DOMAIN].pop("coordinators", None)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload_entry(entry)
