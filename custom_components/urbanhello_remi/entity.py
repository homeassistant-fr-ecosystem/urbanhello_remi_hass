"""Base entity class for Rémi UrbanHello integration."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, get_device_info
from .coordinator import RemiCoordinator


class RemiEntity(CoordinatorEntity):
    """Base class for all Rémi entities.

    Provides common device info, device identity, and API access so that
    individual platform entities don't repeat the same boilerplate.
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: RemiCoordinator,
        device: dict[str, Any],
        api: Any | None = None,
    ) -> None:
        """Initialize the base entity.

        Args:
            coordinator: Data update coordinator for the device.
            device: Device info dict from the API.
            api: Optional RemiAPI instance for entities that write to the API.
        """
        super().__init__(coordinator)
        self._device = device
        self._device_name = device.get("name", "Rémi")
        self._device_id = device["objectId"]
        self._api = api

        # Cache device info at construction time instead of rebuilding on
        # every state write (P2.11).
        self._attr_device_info: DeviceInfo = get_device_info(
            DOMAIN, self._device_id, self._device_name, device
        )

    @property
    def device_data(self) -> dict[str, Any]:
        """Return the raw device data dict."""
        return self._device
