# Rémi UrbanHello Integration for Home Assistant

Home Assistant integration for **Rémi UrbanHello**, a smart baby monitor and sleep trainer device.
This is not an official integration by UrbanHello.

## Overview

This integration allows you to control and monitor your Rémi UrbanHello device through Home Assistant. It provides comprehensive control over the device's features including nightlight, faces, volume, and various diagnostic sensors.

## Features

### Multilingual Support

This integration includes built-in translations for:
- **English** (en)
- **French** (fr)

Face names and entity names are automatically translated based on your Home Assistant language settings.

### Entities Created

For each Rémi device, the following entities are created:

#### Light
- **Rémi [Device Name]**: Main nightlight control with brightness adjustment (0-100%)
  - Uses "sleepy face" when on, "awake face" when off
  - Full brightness control

#### Sensors
- **Temperature**: Current room temperature in °C
- **Face**: Current face displayed on the device
- **Raw Data**: All API data exposed as attributes for advanced automations
- **RSSI**: WiFi signal strength (diagnostic sensor, dBm)

#### Binary Sensors
- **Connectivity**: Device online/offline status (diagnostic sensor)

#### Numbers
- **Volume**: Control device volume (0-100%)
- **Night Light Level**: Set minimum brightness for night light (0-100%)

#### Select
- **Face**: Choose which face to display on the device
  - Options dynamically loaded from your Rémi account
  - Common faces: Sleepy, Awake, Blank, Semi-Awake, and any custom faces
  - Face names are automatically translated to your language

#### Device Tracker
- **Network Status**: Track device IP address and connection status (diagnostic)
  - Provides IP address, MAC address, and online status

## Installation

### HACS (Recommended)

Click here to install via HACS:
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=homeassistant-fr-ecosystem&repository=urbanhello_remi_hass&category=integration)

Or manually:
1. Open HACS in your Home Assistant instance
2. Go to "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add `https://github.com/homeassistant-fr-ecosystem/urbanhello_remi_hass` as an integration
6. Click "Install"
7. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/urbanhello_remi_hass` folder to your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "Rémi UrbanHello"
4. Enter your UrbanHello account credentials:
   - **Username**: Your UrbanHello account email
   - **Password**: Your UrbanHello account password

All your Rémi devices will be automatically discovered and added.

## Usage Examples

### Automations

#### Bedtime Routine
```yaml
automation:
  - alias: "Baby Bedtime Routine"
    trigger:
      - platform: time
        at: "19:00:00"
    action:
      - service: light.turn_on
        target:
          entity_id: light.remi_baby_room
        data:
          brightness_pct: 30
      - service: select.select_option
        target:
          entity_id: select.remi_baby_room_face
        data:
          option: "sleepyFace"
      - service: number.set_value
        target:
          entity_id: number.remi_baby_room_volume
        data:
          value: 50
```

#### Temperature Alert
```yaml
automation:
  - alias: "Room Temperature Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.remi_baby_room_temperature
        above: 22
    action:
      - service: notify.mobile_app
        data:
          message: "Baby room temperature is above 22°C"
```

#### Automatic Night Light
```yaml
automation:
  - alias: "Dim Night Light After Sleep"
    trigger:
      - platform: time
        at: "20:00:00"
    action:
      - service: number.set_value
        target:
          entity_id: number.remi_baby_room_night_light_level
        data:
          value: 10
```

### Lovelace Card Example

```yaml
type: entities
title: Baby Monitor
entities:
  - entity: light.remi_baby_room
  - entity: sensor.remi_baby_room_temperature
  - entity: select.remi_baby_room_face
  - entity: number.remi_baby_room_volume
  - entity: number.remi_baby_room_night_light_level
  - entity: binary_sensor.remi_baby_room_connectivity
  - entity: sensor.remi_baby_room_rssi
```

## Sensor Details

### Raw Data Sensor

The Raw Data sensor exposes all API data as attributes, including:
- `temperature_normalized`: Temperature from API
- `luminosity_normalized`: Brightness level
- `face_id`: Current face ID
- `volume_normalized`: Volume level
- `light_min_normalized`: Night light minimum level
- `device_name`: Device name
- Plus all raw fields from the API

Access these in automations using templates:
```yaml
{{ state_attr('sensor.remi_baby_room_raw_data', 'temperature_normalized') }}
```

## Update Interval

All entities update every 1 minute to minimize API calls while maintaining reasonable freshness of data.

## Diagnostic Entities

The following entities are marked as diagnostic and are hidden by default:
- RSSI (WiFi signal strength)
- Connectivity (online/offline status)
- Device Tracker (network information)

These can be enabled in the entity settings if needed.

## Translations

The integration supports multiple languages with translated entity names and face names. Current supported languages:

- **English** (en)
- **French** (fr)

To add additional languages:
1. Copy [custom_components/urbanhello_remi_hass/translations/en.json](custom_components/urbanhello_remi_hass/translations/en.json)
2. Create a new file with your language code (e.g., `de.json` for German)
3. Translate the values while keeping the keys unchanged
4. Submit a pull request to add it to the integration

## Troubleshooting

### Authentication Fails
- Verify your UrbanHello credentials are correct
- Check that you can log in to the UrbanHello mobile app

### Device Not Appearing
- Ensure your Rémi device is online and connected to WiFi
- Check the device appears in your UrbanHello mobile app
- Try removing and re-adding the integration

### Entities Not Updating
- Check the integration logs for errors: **Settings** → **System** → **Logs**
- Verify your Rémi device is online
- Check your network connectivity

### Enable Debug Logging
Add to your `configuration.yaml`:
```yaml
logger:
  default: info
  logs:
    custom_components.urbanhello_remi_hass: debug
```

## Support

- **Issues**: [GitHub Issues](https://github.com/homeassistant-fr-ecosystem/urbanhello_remi_hass/issues)
- **Discussions**: [GitHub Discussions](https://github.com/homeassistant-fr-ecosystem/urbanhello_remi_hass/discussions)

## Credit

This integration is forked from the original project by [@pdruart](https://github.com/pdruart):
[Remi_UrbanHello_hass](https://github.com/pdruart/Remi_UrbanHello_hass)

## License

This project is not affiliated with, endorsed by, or connected to UrbanHello in any way.

## Disclaimer

This is an unofficial integration. Use at your own risk. The developer is not responsible for any issues that may arise from using this integration.