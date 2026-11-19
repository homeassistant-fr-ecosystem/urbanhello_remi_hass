"""Store-backed stable alarm identity mapping.

Alarms are identified by a locally-generated UUID instead of the
server-generated objectId or the mutable alarm name. This ensures:

- Renaming an alarm in the Rémi app does not create duplicate entities
- Two alarms with the same name get distinct UUIDs
- objectId rotation (unplug/replug) is handled by find_alarm() at runtime
"""

from __future__ import annotations

import uuid as uuid_module
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.store import Store

STORAGE_VERSION = 1
_STORAGE_KEY = "urbanhello_remi_alarm_identity"


class AlarmIdentityStore:
    """Persist stable UUIDs for alarms keyed by device_id."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store = Store[dict[str, dict[str, dict[str, Any]]]](
            hass, STORAGE_VERSION, f"{_STORAGE_KEY}_{entry_id}"
        )
        self._data: dict[str, dict[str, dict[str, Any]]] | None = None

    async def async_load(self) -> None:
        """Load stored mappings from disk."""
        self._data = await self._store.async_load() or {}

    def resolve_uuid(
        self,
        device_id: str,
        alarm_key: str,
        alarm_data: dict[str, Any],
    ) -> str:
        """Resolve or create a stable UUID for an alarm.

        Resolution order:
        1. Direct key match: an existing entry whose last_key == alarm_key
        2. Attribute match: same time + days + enabled → likely a rename
        3. New UUID: generate and store
        """
        if self._data is None:
            self._data = {}

        device_alarms = self._data.setdefault(device_id, {})

        # 1. Direct key match
        for stable_uuid, info in device_alarms.items():
            if info.get("last_key") == alarm_key:
                # Update the last_key in case the key rotated (e.g. name
                # changed and then changed back)
                info["last_key"] = alarm_key
                self._schedule_save()
                return stable_uuid

        # 2. Attribute match: time + days + enabled
        for stable_uuid, info in device_alarms.items():
            if (
                info.get("time") == alarm_data.get("time")
                and info.get("days") == alarm_data.get("days")
                and info.get("enabled") == alarm_data.get("enabled")
            ):
                info["last_key"] = alarm_key
                self._schedule_save()
                return stable_uuid

        # 3. New UUID
        stable_uuid = str(uuid_module.uuid4())
        device_alarms[stable_uuid] = {
            "last_key": alarm_key,
            "time": alarm_data.get("time"),
            "days": alarm_data.get("days"),
            "enabled": alarm_data.get("enabled"),
        }
        self._schedule_save()
        return stable_uuid

    def _schedule_save(self) -> None:
        """Schedule a debounced save to disk.

        Store.async_save() is called explicitly by async_unload_entry.
        Saved on every change for simplicity given the small data size.
        """

    async def async_save(self) -> None:
        """Persist mappings to disk."""
        if self._data is not None:
            await self._store.async_save(self._data)
