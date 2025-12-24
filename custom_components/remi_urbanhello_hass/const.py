DOMAIN = "remi"
MANUFACTURER = "UrbanHello"
MODEL = "Rémi Clock"

# Face name translation keys
FACE_TRANSLATION_KEYS = {
    "sleepyFace": "sleepyFace",
    "awakeFace": "awakeFace",
    "blankFace": "blankFace",
    "semiAwakeFace": "semiAwakeFace",
    "smilyFace": "smilyFace",
}


def get_device_info(domain, device_id, device_name, device_data=None):
    """Generate device info dictionary for Home Assistant."""
    info = {
        "identifiers": {(domain, device_id)},
        "name": device_name,
        "manufacturer": MANUFACTURER,
        "model": MODEL,
    }

    if device_data:
        # Add firmware version
        if "sw_version" in device_data and device_data["sw_version"]:
            info["sw_version"] = device_data["sw_version"]

        # Add hardware version (Bluetooth version)
        if "hw_version" in device_data and device_data["hw_version"]:
            info["hw_version"] = device_data["hw_version"]

    return info
