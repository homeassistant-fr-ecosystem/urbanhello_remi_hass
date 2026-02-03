# Rémi UrbanHello Integration for Home Assistant

Home Assistant integration for **Rémi UrbanHello**, a smart baby monitor and sleep trainer device.
This is not an official integration by UrbanHello.

## Overview

This integration allows you to control and monitor your Rémi UrbanHello device through Home Assistant. It provides comprehensive control over the device's features including nightlight, faces, volume, alarms, and various diagnostic sensors.

## Features

### Multilingual Support

This integration includes built-in translations for:
- **English** (en)
- **French** (fr)

Face names and entity names are automatically translated based on your Home Assistant language settings.

### Alarm Management

Manage your Rémi alarms directly from Home Assistant:
- **View Alarms**: Each alarm is represented as a switch entity.
- **Control Alarms**: Enable/disable alarms using the switch.
- **Edit Alarms**: Change alarm time and active days using dedicated services.
- **Custom Services**: Create, delete, update, trigger, and snooze alarms.

### Entities Created

For each Rémi device, the following entities are created:

#### Light
- **Rémi [Device Name]**: Main nightlight control with brightness adjustment (0-100%)
  - Uses "sleepy_face" when on, "awake_face" when off
  - Full brightness control

#### Sensors
- **Temperature**: Current room temperature in °C
- **Face**: Current face displayed on the device
- **RSSI**: WiFi signal strength (diagnostic sensor, dBm)

#### Binary Sensors
- **Connectivity**: Device online/offline status (diagnostic sensor)

#### Numbers
- **Volume**: Control device volume (0-100%)
- **Night Light Level**: Set minimum brightness for night light (0-100%)
- **Night Face Level**: Set brightness for the face display during night (0-100%)
- **Noise Threshold**: Set the noise notification threshold

#### Select
- **Face**: Choose which face to display on the device
  - Options: sleepy_face, awake_face, blank_face, semi_awake_face, smily_face
  - Face names are automatically translated to your language

#### Time
- **Alarm Time**: View and set the time for each of the 3 supported alarms.

#### Switch
- **Alarm**: Enable or disable each of the 3 supported alarms.

#### Device Tracker
- **Network Status**: Track device IP address and connection status (diagnostic)

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

- **urbanhello_remi.create_alarm**: Create a new alarm.
- **urbanhello_remi.delete_alarm**: Delete an existing alarm.
- **urbanhello_remi.update_alarm**: Update alarm settings (time, days, enabled, face, brightness).
- **urbanhello_remi.trigger_alarm**: Manually trigger an alarm.
- **urbanhello_remi.snooze_alarm**: Snooze a currently active alarm.

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
          option: "sleepy_face"
```

## Update Interval

All entities update every 1 minute by default. This can be customized in the integration options.

## Support

- **Issues**: [GitHub Issues](https://github.com/homeassistant-fr-ecosystem/urbanhello_remi_hass/issues)

## Credit

This integration is maintained by the [Home Assistant French Ecosystem](https://github.com/homeassistant-fr-ecosystem).
Based on original work by [@pdruart](https://github.com/pdruart).

## License

This project is not affiliated with, endorsed by, or connected to UrbanHello in any way.

## Disclaimer

This is an unofficial integration. Use at your own risk.
