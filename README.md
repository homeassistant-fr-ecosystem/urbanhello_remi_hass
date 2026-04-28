# Rémi UrbanHello Integration for Home Assistant

Home Assistant integration for **Rémi UrbanHello**, a smart baby monitor and sleep trainer device.
This is not an official integration by UrbanHello.

## Overview

This integration allows you to control and monitor your Rémi UrbanHello device through Home Assistant. It provides comprehensive control over the device's features including nightlight, faces, volume, alarms, and various diagnostic sensors.

## Features

### Multilingual Support

Built-in translations for:
- **English** (en)
- **French** (fr)

Face names and entity names are automatically translated based on your Home Assistant language settings.

### Alarm Management

Manage your Rémi alarms directly from Home Assistant:
- **View Alarms**: Each alarm is represented as a switch entity and a time entity.
- **Control Alarms**: Enable/disable alarms using the switch.
- **Edit Alarms**: Change alarm time and active days using dedicated services.
- **Custom Services**: Create, delete, update, trigger, and snooze alarms.

### Entities Created

For each Rémi device, the following entities are created:

#### Light
- **Night Light**: Nightlight brightness control (0-100%)

#### Sensors
- **Temperature**: Current room temperature in °C
- **Ambient Light**: Ambient luminosity in lux (diagnostic)
- **Firmware Version**: Current device firmware version (diagnostic)
- **Signal Strength (RSSI)**: WiFi signal strength in dBm (diagnostic, disabled by default)
- **IP Address**: Device IPv4 address (diagnostic, disabled by default)

#### Binary Sensors
- **Firmware Update Available**: Indicates when a firmware update is available
- **Connectivity**: Device online/offline status (diagnostic, disabled by default)
- **Alive**: Device running status (diagnostic, disabled by default)

#### Numbers
- **Volume**: Control device volume (0-100%)
- **Night Light Level**: Minimum brightness for the nightlight (0-100%)
- **Night Face Level**: Face display brightness during night mode (0-100%)
- **Noise Threshold**: Noise notification trigger level (0-100%)

#### Select
- **Face**: Choose which face to display on the device
  - Options: Sleepy, Awake, Blank, Semi-Awake, Smiley
- **Clock Format**: 12h or 24h time display
- **Music Mode**: Off, Music, or White Noise

#### Time
- **Alarm 1/2/3 Time**: View and set the time for each alarm.

#### Switch
- **Alarm 1/2/3**: Enable or disable each alarm.

#### Device Tracker
- **Network Status**: Track device connection status (diagnostic, disabled by default)

## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Go to "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add `https://github.com/homeassistant-fr-ecosystem/urbanhello_remi_hass` as an integration
6. Click "Install"
7. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/urbanhello_remi` folder to your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "Rémi UrbanHello"
4. Enter your UrbanHello account credentials:
   - **Username**: Your UrbanHello account email
   - **Password**: Your UrbanHello account password

## Services

The integration provides several services for advanced alarm management:

| Service | Description |
|---|---|
| `urbanhello_remi.create_alarm` | Create a new alarm (time, name, days, enabled) |
| `urbanhello_remi.delete_alarm` | Delete an existing alarm by ID |
| `urbanhello_remi.update_alarm` | Update alarm settings (time, days, enabled, face, brightness) |
| `urbanhello_remi.trigger_alarm` | Manually trigger an alarm |
| `urbanhello_remi.snooze_alarm` | Snooze a currently active alarm (default: 9 min) |

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
          entity_id: light.remi_baby_room_night_light
        data:
          brightness_pct: 30
      - service: select.select_option
        target:
          entity_id: select.remi_baby_room_face
        data:
          option: "sleepy_face"
      - service: select.select_option
        target:
          entity_id: select.remi_baby_room_music_mode
        data:
          option: "white_noise"
```

#### Wake Up Routine
```yaml
automation:
  - alias: "Baby Wake Up"
    trigger:
      - platform: time
        at: "07:00:00"
    action:
      - service: select.select_option
        target:
          entity_id: select.remi_baby_room_face
        data:
          option: "awake_face"
      - service: select.select_option
        target:
          entity_id: select.remi_baby_room_music_mode
        data:
          option: "off"
```

## Update Interval

All entities update every 1 minute by default. This can be customized in the integration options.

## Support

- **Issues**: [GitHub Issues](https://github.com/homeassistant-fr-ecosystem/urbanhello_remi_hass/issues)

## Credits

This integration is maintained by the [Home Assistant French Ecosystem](https://github.com/homeassistant-fr-ecosystem).
Based on original work by [@pdruart](https://github.com/pdruart).

## Disclaimer

This is an unofficial integration, not affiliated with, endorsed by, or connected to UrbanHello in any way. Use at your own risk.
