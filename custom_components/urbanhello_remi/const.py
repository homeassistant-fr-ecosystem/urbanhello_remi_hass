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

# Alarm clock service names
SERVICE_TRIGGER_ALARM = "trigger_alarm"
SERVICE_SNOOZE_ALARM = "snooze_alarm"
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


def _normalize_mac(value: str | None) -> str | None:
    """Normalize a MAC address to the canonical XX:XX:XX:XX:XX:XX format.

    Accepts common separators (``:``, ``-``, ``.``) or no separator at all.
    Returns ``None`` when the value is missing or not a valid 6-byte MAC.
    """
    if not value:
        return None
    cleaned = value.replace(":", "").replace("-", "").replace(".", "").strip().upper()
    if len(cleaned) != 12 or any(c not in "0123456789ABCDEF" for c in cleaned):
        return None
    return ":".join(cleaned[i : i + 2] for i in range(0, 12, 2))


def get_device_info(
    domain: str,
    device_id: str,
    device_name: str,
    device_data: dict[str, Any] | None = None,
) -> DeviceInfo:
    """Generate device info dictionary for Home Assistant."""
    device_data = device_data or {}
    raw_data = device_data.get("raw", {})
    connections: set[tuple[str, str]] = set()
    if ipv4 := raw_data.get("ipv4Address"):
        connections.add(("ip", ipv4))
    mac = _normalize_mac(raw_data.get("macAddress"))
    if mac:
        connections.add(("mac", mac))
    return DeviceInfo(
        identifiers={(domain, device_id)},
        name=device_name,
        manufacturer=MANUFACTURER,
        model=MODEL,
        sw_version=_device_version(raw_data.get("current_firmware_version")),
        hw_version=_device_version(raw_data.get("bt_hardware_version")),
        connections=connections,
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
    stable_uuid: str,
    suffix: str,
) -> str:
    """Return the unique_id of an alarm entity."""
    key = build_alarm_key(alarm_object_id, alarm_name, alarms)
    return f"{device_id}_alarm_{key}_{suffix}"


def build_alarm_suggested_object_id(
    device_name: str,
    alarm_name: str | None,
) -> str:
    """Return the suggested entity_id of an alarm entity.

    Device and alarm names can contain accents, spaces or punctuation that are
    not valid in an entity_id. Both parts go through the same ``slugify``
    normalization as the unique_id built by :func:`build_alarm_key`.
    """
    return f"{slugify(device_name)}_{slugify(alarm_name or 'alarm')}"
