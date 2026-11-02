from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.util import slugify

DOMAIN = "urbanhello_remi"
MANUFACTURER = "UrbanHello"
MODEL = "Rémi Clock"
BRAND_NAME = "Rémi"

# Face name translation keys
FACE_MAP_API_TO_HA = {
    "sleepyFace": "sleepy_face",
    "awakeFace": "awake_face",
    "blankFace": "blank_face",
    "semiAwakeFace": "semi_awake_face",
    "smilyFace": "smily_face",
}

FACE_MAP_HA_TO_API = {v: k for k, v in FACE_MAP_API_TO_HA.items()}

# Music mode options: API integer value -> display label
MUSIC_MODE_OPTIONS: dict[int, str] = {
    0: "off",
    1: "music",
    2: "white_noise",
}

# Alarm clock constants
MAX_ALARMS_PER_DEVICE = 3
DEFAULT_ALARM_HOUR = 7
DEFAULT_ALARM_MINUTE = 0
DEFAULT_ALARM_VOLUME = 50
DEFAULT_ALARM_FACE = "awake_face"
ALARM_SNOOZE_DURATION = 9  # minutes

# Alarm clock service names
SERVICE_TRIGGER_ALARM = "trigger_alarm"
SERVICE_SNOOZE_ALARM = "snooze_alarm"
SERVICE_STOP_ALARM = "stop_alarm"
SERVICE_CREATE_ALARM = "create_alarm"
SERVICE_DELETE_ALARM = "delete_alarm"
SERVICE_UPDATE_ALARM = "update_alarm"


def _device_version(value: Any) -> str | None:
    """Coerce a device version to the string the device registry requires.

    The Rémi API is not consistent about version types (``bt_hardware_version``
    is an int, firmware versions may come back as numbers too). Home Assistant
    started warning about non-string versions in 2026.10 and rejects them from
    2026.12, so normalise here instead of at every call site.
    """
    return None if value is None else str(value)


def get_device_info(
    domain: str,
    device_id: str,
    device_name: str,
    device_data: dict[str, Any] | None = None,
) -> DeviceInfo:
    """Generate device info dictionary for Home Assistant."""
    device_data = device_data or {}
    raw_data = device_data.get("raw", {})
    return DeviceInfo(
        identifiers={(domain, device_id)},
        name=device_name,
        manufacturer=MANUFACTURER,
        model=MODEL,
        sw_version=_device_version(raw_data.get("current_firmware_version")),
        hw_version=_device_version(raw_data.get("bt_hardware_version")),
        connections=(
            {("ip", raw_data.get("ipv4Address"))}
            if raw_data.get("ipv4Address")
            else set()
        ),
    )


def build_alarm_key(
    alarm_object_id: str,
    alarm_name: str | None,
    alarms: dict[str, Any],
) -> str:
    """Return a stable per-device key identifying an alarm.

    The Parse ``objectId`` of an ``Event`` is regenerated server-side whenever
    the alarm is edited from the UrbanHello app, so it must not be used as the
    basis of a unique_id: every edit would otherwise register a brand new set
    of entities and orphan the previous ones.

    The alarm name is stable across those rotations, so it is preferred. The
    objectId is only kept as a fallback when the name is empty or shared by
    several alarms of the same device, which keeps unique_ids collision-free.
    """
    slug = slugify(alarm_name or "")
    if not slug:
        return alarm_object_id

    same_name = [
        object_id
        for object_id, data in alarms.items()
        if slugify((data or {}).get("name") or "") == slug
    ]
    if len(same_name) > 1:
        return f"{slug}_{alarm_object_id}"
    return slug


def build_alarm_unique_id(
    device_id: str,
    alarm_object_id: str,
    alarm_name: str | None,
    alarms: dict[str, Any],
    suffix: str,
) -> str:
    """Return the unique_id of an alarm entity."""
    key = build_alarm_key(alarm_object_id, alarm_name, alarms)
    return f"{device_id}_alarm_{key}_{suffix}"


def find_alarm(
    alarms: dict[str, Any],
    alarm_object_id: str | None,
    alarm_key: str,
) -> tuple[str | None, dict[str, Any]]:
    """Locate an alarm in the latest coordinator payload.

    Parse regenerates the ``objectId`` of an ``Event`` when the Rémi is
    re-registered (unplugged/plugged back in) or when the alarm is edited from
    the UrbanHello app. Entities keep the id they were created with, so fall
    back to the stable name-based key to follow the alarm instead of showing
    stale values and failing writes.

    Returns the current objectId (or ``None`` when the alarm is gone) and its
    data.
    """
    if alarm_object_id is not None:
        data = alarms.get(alarm_object_id)
        if data is not None:
            return alarm_object_id, data

    for object_id, raw_alarm in alarms.items():
        candidate = raw_alarm or {}
        if build_alarm_key(object_id, candidate.get("name"), alarms) == alarm_key:
            return object_id, candidate

    return None, {}
