try:
    from . import system_health
except ImportError:
    pass
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import device_registry as dr
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

from .api import RemiAPI, RemiAPIAuthError, RemiAPIError
from .const import (
    DOMAIN, 
    SERVICE_CREATE_ALARM, 
    SERVICE_DELETE_ALARM, 
    SERVICE_UPDATE_ALARM,
    SERVICE_TRIGGER_ALARM,
    SERVICE_SNOOZE_ALARM
)
from .coordinator import RemiCoordinator

_LOGGER = logging.getLogger(__name__)

# Service schemas
CREATE_ALARM_SCHEMA = vol.Schema({
    vol.Required("device_id"): cv.string,
    vol.Required("time"): cv.string,
    vol.Optional("name"): cv.string,
    vol.Optional("enabled"): cv.boolean,
    vol.Optional("days"): vol.All(cv.ensure_list, [vol.All(vol.Coerce(int), vol.Range(min=0, max=6))]),
})

DELETE_ALARM_SCHEMA = vol.Schema({
    vol.Required("device_id"): cv.string,
    vol.Required("alarm_id"): cv.string,
})

UPDATE_ALARM_SCHEMA = vol.Schema({
    vol.Required("device_id"): cv.string,
    vol.Required("alarm_id"): cv.string,
    vol.Optional("time"): cv.string,
    vol.Optional("enabled"): cv.boolean,
    vol.Optional("name"): cv.string,
    vol.Optional("days"): vol.All(cv.ensure_list, [vol.All(vol.Coerce(int), vol.Range(min=0, max=6))]),
    vol.Optional("face"): cv.string,
    vol.Optional("brightness"): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
})

TRIGGER_ALARM_SCHEMA = vol.Schema({
    vol.Required("device_id"): cv.string,
    vol.Required("alarm_id"): cv.string,
})

SNOOZE_ALARM_SCHEMA = vol.Schema({
    vol.Required("device_id"): cv.string,
    vol.Required("alarm_id"): cv.string,
    vol.Optional("duration"): vol.All(vol.Coerce(int), vol.Range(min=1, max=60)),
})

async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the Remi integration."""
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Rémi from a config entry."""
    session = async_get_clientsession(hass)
    api = RemiAPI(entry.data["username"], entry.data["password"], session=session)

    try:
        await api.login()
    except RemiAPIAuthError as err:
        raise ConfigEntryAuthFailed from err
    except RemiAPIError as err:
        raise ConfigEntryNotReady(f"Error connecting to Rémi API: {err}") from err
    except Exception as err:
        raise ConfigEntryNotReady(f"Unexpected error: {err}") from err

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["api"] = api

    scan_interval = entry.options.get("scan_interval", 60)

    devices = []
    coordinators = {}
    
    for remi in api.remis:
        remi_id = remi.get("objectId") if isinstance(remi, dict) else remi
        if not remi_id:
            continue

        try:
            device_info = await api.get_remi_info(remi_id)
            device_info["objectId"] = remi_id
            devices.append(device_info)

            coordinator = RemiCoordinator(
                hass, 
                api, 
                remi_id, 
                device_info.get("name", "Rémi"), 
                update_interval=scan_interval
            )
            await coordinator.async_config_entry_first_refresh()
            coordinators[remi_id] = coordinator
            
        except Exception as e:
            _LOGGER.error("Failed to setup Remi device %s: %s", remi_id, e)

    if not coordinators:
        raise ConfigEntryNotReady("No Rémi devices could be initialized")

    hass.data[DOMAIN]["devices"] = devices
    hass.data[DOMAIN]["coordinators"] = coordinators

    def get_api_device_id(ha_device_id: str) -> str | None:
        """Resolve HA device ID to API objectId."""
        dev_reg = dr.async_get(hass)
        device = dev_reg.async_get(ha_device_id)
        if not device:
            return ha_device_id # Fallback if not found in registry (user might have entered it manually)
        
        for identifier in device.identifiers:
            if identifier[0] == DOMAIN:
                return identifier[1]
        return ha_device_id

    # Register Services
    async def handle_create_alarm(call: ServiceCall):
        api_device_id = get_api_device_id(call.data["device_id"])
        time = call.data["time"]
        kwargs = {k: v for k, v in call.data.items() if k not in ["device_id", "time"]}
        api = hass.data[DOMAIN]["api"]
        await api.create_alarm(api_device_id, time, **kwargs)
        if api_device_id in coordinators:
            await coordinators[api_device_id].async_request_refresh()

    async def handle_delete_alarm(call: ServiceCall):
        api_device_id = get_api_device_id(call.data["device_id"])
        alarm_id = call.data["alarm_id"]
        api = hass.data[DOMAIN]["api"]
        await api.delete_alarm(api_device_id, alarm_id)
        if api_device_id in coordinators:
            await coordinators[api_device_id].async_request_refresh()

    async def handle_update_alarm(call: ServiceCall):
        api_device_id = get_api_device_id(call.data["device_id"])
        alarm_id = call.data["alarm_id"]
        kwargs = {k: v for k, v in call.data.items() if k not in ["device_id", "alarm_id"]}
        api = hass.data[DOMAIN]["api"]
        await api.update_alarm(api_device_id, alarm_id, **kwargs)
        if api_device_id in coordinators:
            await coordinators[api_device_id].async_request_refresh()

    async def handle_trigger_alarm(call: ServiceCall):
        api_device_id = get_api_device_id(call.data["device_id"])
        alarm_id = call.data["alarm_id"]
        api = hass.data[DOMAIN]["api"]
        await api.trigger_alarm(api_device_id, alarm_id)

    async def handle_snooze_alarm(call: ServiceCall):
        api_device_id = get_api_device_id(call.data["device_id"])
        alarm_id = call.data["alarm_id"]
        duration = call.data.get("duration", 9)
        api = hass.data[DOMAIN]["api"]
        await api.snooze_alarm(api_device_id, alarm_id, duration)
        if api_device_id in coordinators:
            await coordinators[api_device_id].async_request_refresh()

    hass.services.async_register(DOMAIN, SERVICE_CREATE_ALARM, handle_create_alarm, schema=CREATE_ALARM_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_DELETE_ALARM, handle_delete_alarm, schema=DELETE_ALARM_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_UPDATE_ALARM, handle_update_alarm, schema=UPDATE_ALARM_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_TRIGGER_ALARM, handle_trigger_alarm, schema=TRIGGER_ALARM_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_SNOOZE_ALARM, handle_snooze_alarm, schema=SNOOZE_ALARM_SCHEMA)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    await hass.config_entries.async_forward_entry_setups(
        entry, ["light", "sensor", "binary_sensor", "number", "device_tracker", "select", "time", "switch"]
    )

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, ["light", "sensor", "binary_sensor", "number", "device_tracker", "select", "time", "switch"]
    )

    if unload_ok:
        hass.data[DOMAIN].pop("api", None)
        hass.data[DOMAIN].pop("devices", None)
        hass.data[DOMAIN].pop("coordinators", None)
        
        # Unregister services if this is the last entry
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_CREATE_ALARM)
            hass.services.async_remove(DOMAIN, SERVICE_DELETE_ALARM)
            hass.services.async_remove(DOMAIN, SERVICE_UPDATE_ALARM)
            hass.services.async_remove(DOMAIN, SERVICE_TRIGGER_ALARM)
            hass.services.async_remove(DOMAIN, SERVICE_SNOOZE_ALARM)

    return unload_ok

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)
