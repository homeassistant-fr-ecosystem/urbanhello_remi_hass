from __future__ import annotations

from typing import Any

from homeassistant.helpers.entity import DeviceInfo

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
        sw_version=raw_data.get("current_firmware_version"),
        hw_version=raw_data.get("bt_hardware_version"),
        connections={("ip", raw_data.get("ipv4Address"))} if raw_data.get("ipv4Address") else set(),
    )
