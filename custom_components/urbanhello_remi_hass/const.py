from homeassistant.helpers.entity import DeviceInfo
DOMAIN = "urbanhello_remi"
MANUFACTURER = "UrbanHello"
MODEL = "Rémi Clock"
BRAND_NAME = "Rémi"

# Face name translation keys
FACE_TRANSLATION_KEYS = {
    "sleepyFace": "sleepyFace",
    "awakeFace": "awakeFace",
    "blankFace": "blankFace",
    "semiAwakeFace": "semiAwakeFace",
    "smilyFace": "smilyFace",
}

# Alarm clock constants
MAX_ALARMS_PER_DEVICE = 3
DEFAULT_ALARM_HOUR = 7
DEFAULT_ALARM_MINUTE = 0
DEFAULT_ALARM_VOLUME = 50
DEFAULT_ALARM_FACE = "awakeFace"
ALARM_SNOOZE_DURATION = 9  # minutes

# Alarm clock service names
SERVICE_TRIGGER_ALARM = "trigger_alarm"
SERVICE_SNOOZE_ALARM = "snooze_alarm"
SERVICE_STOP_ALARM = "stop_alarm"


def get_device_info(domain, device_id, device_name, device_data=None):
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
