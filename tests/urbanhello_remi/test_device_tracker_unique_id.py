"""Regression tests for device tracker unique_id (HA 2027.8.0 breaking change).

Home Assistant 2027.8.0 warns when an integration attaches device info to an
entity without a unique_id. ``ScannerEntity.unique_id`` falls back to
``mac_address``, which the Rémi API may not report. The device tracker must
always expose a stable unique_id so it never attaches a device without one.
"""

from __future__ import annotations

import asyncio
import sys
from unittest.mock import MagicMock

import pytest

# HA 2026.11 moved Store from helpers.store to helpers.storage; shim so the
# integration's alarm_store.py import path resolves on either version.
if "homeassistant.helpers.store" not in sys.modules:
    import homeassistant.helpers.storage as _storage

    sys.modules["homeassistant.helpers.store"] = _storage

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from custom_components.urbanhello_remi.device_tracker import RemiDeviceTracker


class FakeCoordinator(DataUpdateCoordinator):
    """Minimal stand-in for RemiCoordinator used to build entities."""

    def __init__(self, _hass, device_id: str, device_name: str, with_mac: bool) -> None:
        self.device_id = device_id
        self.device_name = device_name
        self.api = MagicMock()
        self.api.faces = {}
        raw = {
            "current_firmware_version": "1.0",
            "bt_hardware_version": "1",
            "ipv4Address": "1.2.3.4",
            "online": True,
            "alive": True,
            "latest_firmware_version": "1.0",
            "rssi": -50,
            "noise_notification_threshold": 50,
            "hour_format_24": True,
        }
        if with_mac:
            raw["macAddress"] = "AA:BB:CC"
        self.data = {
            "device_info": {"name": device_name, "raw": raw},
            "alarms": {},
        }
        self.last_update_success = True

    async def _async_update_data(self):
        return self.data


def _make_hass() -> MagicMock:
    hass = MagicMock()
    hass.loop = asyncio.get_running_loop()
    return hass


@pytest.mark.parametrize("with_mac", [True, False])
async def test_device_tracker_always_has_unique_id(with_mac: bool) -> None:
    """The device tracker must never attach a device without a unique_id."""
    hass = _make_hass()
    coordinator = FakeCoordinator(hass, "dev1", "Rémi", with_mac=with_mac)
    device = {"objectId": "dev1", "name": "Rémi"}

    entity = RemiDeviceTracker(coordinator, coordinator.api, device)

    # device_info is always set by RemiEntity
    assert entity.device_info is not None
    # unique_id must be stable and never None, even without a MAC address
    assert entity.unique_id is not None
    assert entity.unique_id == f"{device['objectId']}_device_tracker"
