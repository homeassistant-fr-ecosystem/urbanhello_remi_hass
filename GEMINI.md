# Project Rules: Rémi UrbanHello Home Assistant Integration

## 1. Project Context
This integration allows Home Assistant to monitor and interact with Rémi UrbanHello devices, exposing device data and enabling control functionalities.

## 2. Standards
@../.gemini/rules/shared_python.md

## 3. Project-Specific Notes
- **Domain**: `urbanhello_remi`
- **Imports**: Ensure proper imports from `custom_components.urbanhello_remi`.
- **API client**: depends on the published [urbanhello-remi-api](../urbanhello-remi-api/) package (`RemiAPI`) — do not vendor a local copy of the client. The package exposes a few backward-compat shims (`get_remi_info()`, `faces`) that return dict-shaped data for HA platform compatibility; prefer those over the package's native dataclass-returning methods (`get_device()`, `list_faces()`) when a call site needs dict-style access.
