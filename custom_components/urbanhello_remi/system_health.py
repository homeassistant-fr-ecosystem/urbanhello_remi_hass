"""Provide info to system health."""
from __future__ import annotations

from typing import Any

from homeassistant.components.system_health import (
    SystemHealthRegistration,
    async_register_system_health_component,
)
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN


@callback
def async_register_system_health(
    hass: HomeAssistant, register: SystemHealthRegistration
) -> None:
    """Register system health callbacks."""
    register.async_register_info(system_health_info)


async def system_health_info(hass: HomeAssistant) -> dict[str, Any]:
    """Get info for the info page."""
    api = hass.data[DOMAIN].get("api")
    
    return {
        "can_reach_server": "ok" if api and api.session_token else "failed",
        "api_endpoint_reachable": "ok" if api and await api._ensure_session() else "failed",
    }
