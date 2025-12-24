# Rémi UrbanHello Integration for Home Assistant

Home Assistant integration `remi_urbanhello_hass` is designed for Rémi UrbanHello.
This is not an official integration by UrbanHello.

## Features

### Multilingual Support

This integration includes built-in translations for:
- **English** (en)
- **French** (fr)
## Installation

Copy the content of the 'custom_components' folder to your home-assistant folder 'config/custom_components' or install through HACS.
After reboot of Home-Assistant, this integration can be configured through the integration setup UI

## Translations

The integration supports multiple languages with translated entity names and face names. Current supported languages:

- **English** (en)
- **French** (fr)

To add additional languages:
1. Copy [custom_components/remi_urbanhello_hass/translations/en.json](custom_components/remi_urbanhello_hass/translations/en.json)
2. Create a new file with your language code (e.g., `de.json` for German)
3. Translate the values while keeping the keys unchanged
4. Submit a pull request to add it to the integration

Click here to install over HACS:
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=pdruart&repository=Remi_UrbanHello_hass&category=integration)