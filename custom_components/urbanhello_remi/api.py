from __future__ import annotations

import aiohttp
import asyncio
import logging
import time
from typing import Any
from datetime import datetime, timedelta

_LOGGER = logging.getLogger(__name__)


class RemiAPIError(Exception):
    """Generic exception for RemiAPI failures."""


class RemiAPIAuthError(RemiAPIError):
    """Exception for authentication failures."""


class RemiAPI:
    """Async client for UrbanHello (Rémi) Parse-based API."""

    BASE_URL = "https://remi2.urbanhello.com/parse"
    APP_ID = "jf1a0bADt5fq"

    def __init__(
        self, 
        username: str, 
        password: str, 
        session: aiohttp.ClientSession | None = None,
        cache_duration: int = 60, 
        request_timeout: int = 15
    ) -> None:
        self.username = username
        self.password = password
        self.session_token: str | None = None
        self.remis: list[dict[str, Any]] = []
        # Generic cache storage for Remi objects keyed by objectId
        self.cache: dict[str, Any] = {}
        self.cache_expiry: dict[str, float] = {}
        self.cache_duration = float(cache_duration)
        # Faces map name -> objectId
        self.faces: dict[str, str] = {}
        # Alarms cache keyed by remi objectId
        self.alarms: dict[str, list[dict[str, Any]]] = {}
        self._session = session
        self._request_timeout = request_timeout

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    def _headers(self, include_session: bool = True) -> dict[str, str]:
        headers = {
            "X-Parse-Application-Id": self.APP_ID,
            "Content-Type": "application/json",
        }
        if include_session and self.session_token:
            headers["X-Parse-Session-Token"] = self.session_token
        return headers

    async def _request(self, method: str, path: str, json: dict | None = None, timeout: int | None = None, include_session: bool = True) -> Any:
        """Perform an HTTP request and return parsed JSON or raw text."""
        session = await self._ensure_session()
        url = f"{self.BASE_URL}{path}"
        timeout_ctrl = aiohttp.ClientTimeout(total=timeout or self._request_timeout)

        try:
            async with session.request(method, url, headers=self._headers(include_session), json=json, timeout=timeout_ctrl) as resp:
                text = await resp.text()
                if resp.status == 401:
                    raise RemiAPIAuthError(f"Authentication failed: {text}")
                if resp.status >= 400:
                    _LOGGER.debug("Request %s %s failed: %s - %s", method, url, resp.status, text)
                    raise RemiAPIError(f"HTTP {resp.status}: {text}")
                try:
                    return await resp.json()
                except Exception:
                    return text
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            if method.upper() == "GET" and "/classes/" in path:
                _LOGGER.debug("GET failed for %s, retrying with POST _method=GET: %s", url, exc)
                fallback = (json or {}).copy()
                fallback["_method"] = "GET"
                try:
                    async with session.post(url, headers=self._headers(include_session), json=fallback, timeout=timeout_ctrl) as resp:
                        text = await resp.text()
                        if resp.status == 401:
                            raise RemiAPIAuthError(f"Authentication failed: {text}")
                        if resp.status >= 400:
                            _LOGGER.debug("Fallback POST failed: %s - %s", resp.status, text)
                            raise RemiAPIError(f"HTTP {resp.status}: {text}")
                        try:
                            return await resp.json()
                        except Exception:
                            return text
                except Exception as exc2:
                    _LOGGER.debug("Fallback POST also failed for %s: %s", url, exc2)
                    raise RemiAPIError(f"Request failed: {exc2}")
            raise RemiAPIError(str(exc))

    async def login(self) -> dict[str, Any]:
        """Authenticate and populate session token, known Remi devices and faces."""
        payload = {"username": self.username, "password": self.password}
        # Login should not include a session header
        data = await self._request("POST", "/login", json=payload, include_session=False)

        if not isinstance(data, dict):
            raise RemiAPIError("Unexpected response during login")

        self.session_token = data.get("sessionToken")
        if not self.session_token:
            raise RemiAPIError("Login succeeded but session token was not returned")

        # Some servers return remis on login, otherwise perform a query
        self.remis = data.get("remis") or []
        if not self.remis:
            try:
                await self.list_remis(refresh=True)
            except Exception:
                # Non-fatal, keep empty list
                _LOGGER.debug("Could not auto-refresh remis after login", exc_info=True)

        try:
            await self.get_faces(refresh=True)
        except Exception:
            _LOGGER.debug("Could not retrieve faces during login", exc_info=True)

        return data

    async def logout(self) -> None:
        """Invalidate the current session token on the server and close session."""
        if not self.session_token:
            return
        try:
            await self._request("POST", "/logout", json={}, include_session=True)
        except RemiAPIError:
            _LOGGER.debug("Logout request failed but session will be cleared locally")
        finally:
            self.session_token = None

    async def get_faces(self, refresh: bool = False) -> dict[str, str]:
        """Retrieve available faces."""
        if self.faces and not refresh:
            return self.faces

        result = await self._request("GET", "/classes/Face")
        results = result.get("results", []) if isinstance(result, dict) else []
        self.faces = {item.get("name"): item.get("objectId") for item in results if item.get("name") and item.get("objectId")}
        return self.faces

    async def list_remis(self, refresh: bool = False) -> list[dict[str, Any]]:
        """List Remi devices."""
        if self.remis and not refresh:
            return self.remis
        result = await self._request("GET", "/classes/Remi")
        self.remis = result.get("results", []) if isinstance(result, dict) else []
        return self.remis

    def _is_cache_valid(self, key: str) -> bool:
        expiry = self.cache_expiry.get(key)
        return expiry is not None and expiry > time.time()

    async def get_remi_info(self, object_id: str, refresh: bool = False) -> dict[str, Any]:
        """Retrieve Remi information."""
        if not refresh and self._is_cache_valid(object_id):
            return self.cache[object_id]

        data = await self._request("GET", f"/classes/Remi/{object_id}")
        if not isinstance(data, dict):
            raise RemiAPIError("Unexpected response when fetching Remi info")

        raw_temp = data.get("temp")
        normalized_temp = (raw_temp + 40) if raw_temp is not None else None

        remi_info: dict[str, Any] = {
            "temperature": normalized_temp,
            "luminosity": data.get("luminosity"),
            "name": data.get("name"),
            "face": data.get("face", {}).get("objectId") if data.get("face") else None,
            "volume": data.get("volume"),
            "light_min": data.get("light_min"),
            "raw": data,
        }

        self.cache[object_id] = remi_info
        self.cache_expiry[object_id] = time.time() + self.cache_duration
        return remi_info

    def _pointer(self, class_name: str, object_id: str) -> dict[str, str]:
        return {"__type": "Pointer", "className": class_name, "objectId": object_id}

    async def _update_remi(self, object_id: str, payload: dict[str, Any]) -> Any:
        """Generic helper to update a Remi object."""
        result = await self._request("PUT", f"/classes/Remi/{object_id}", json=payload)
        self.cache_expiry.pop(object_id, None)
        self.cache.pop(object_id, None)
        return result

    async def set_brightness(self, object_id: str, brightness: int) -> Any:
        """Set the brightness."""
        return await self._update_remi(object_id, {"luminosity": brightness})

    async def set_night_luminosity(self, object_id: str, level: int) -> Any:
        """Set the night luminosity."""
        return await self._update_remi(object_id, {"light_min": level})

    async def set_volume(self, object_id: str, level: int) -> Any:
        """Set the volume."""
        return await self._update_remi(object_id, {"volume": level})

    async def set_noise_threshold(self, object_id: str, threshold: int) -> Any:
        """Set the noise threshold."""
        return await self._update_remi(object_id, {"noise_threshold": threshold})

    async def turn_on(self, object_id: str) -> Any:
        """Turn on."""
        face_id = self.faces.get("sleepyFace")
        if not face_id:
            await self.get_faces(refresh=True)
            face_id = self.faces.get("sleepyFace")
        if not face_id: raise RemiAPIError("sleepyFace not found")
        return await self._update_remi(object_id, {"face": self._pointer("Face", face_id)})

    async def turn_off(self, object_id: str) -> Any:
        """Turn off."""
        face_id = self.faces.get("awakeFace")
        if not face_id:
            await self.get_faces(refresh=True)
            face_id = self.faces.get("awakeFace")
        if not face_id: raise RemiAPIError("awakeFace not found")
        return await self._update_remi(object_id, {"face": self._pointer("Face", face_id)})

    async def set_face_by_name(self, object_id: str, face_name: str) -> Any:
        """Set face by name."""
        face_mapping = {
            "sleepy_face": "sleepyFace",
            "awake_face": "awakeFace",
            "blank_face": "blankFace",
            "semi_awake_face": "semiAwakeFace",
            "smily_face": "smilyFace",
        }
        api_face_name = face_mapping.get(face_name, face_name)
        face_id = self.faces.get(api_face_name)
        if not face_id:
            await self.get_faces(refresh=True)
            face_id = self.faces.get(api_face_name)
        if not face_id: raise RemiAPIError(f"Unknown face '{api_face_name}'")
        return await self._update_remi(object_id, {"face": self._pointer("Face", face_id)})

    async def play_media(self, object_id: str, sound: str, volume: int | None = None) -> Any:
        """Play media."""
        payload: dict[str, Any] = {"sound": sound}
        if volume is not None: payload["volume"] = volume
        return await self._update_remi(object_id, payload)

    async def stop_sound(self, object_id: str) -> Any:
        """Stop sound."""
        return await self._update_remi(object_id, {"sound": ""})

    async def close(self) -> None:
        pass

    # ========================================================================
    # ALARM MANAGEMENT METHODS
    # ========================================================================

    async def get_alarms(self, object_id: str, refresh: bool = False) -> list[dict[str, Any]]:
        """Retrieve all alarms from Event class."""
        if not refresh and object_id in self.alarms:
            return self.alarms[object_id]

        alarms: list[dict[str, Any]] = []
        try:
            where = {"remi": self._pointer("Remi", object_id)}
            result = await self._request("GET", "/classes/Event", json={"where": where})
            if isinstance(result, dict) and "results" in result:
                for event in result.get("results", []):
                    alarm = self._convert_event_to_alarm(event, object_id)
                    if alarm: alarms.append(alarm)
        except RemiAPIError as e:
            _LOGGER.warning("Failed to get events: %s", e)

        self.alarms[object_id] = alarms
        return alarms

    def _convert_event_to_alarm(self, event: dict[str, Any], device_id: str) -> dict[str, Any] | None:
        try:
            event_time = event.get("event_time", [0, 0])
            time_str = f"{event_time[0]:02d}:{event_time[1]:02d}" if len(event_time) >= 2 else "00:00"
            recurrence = event.get("recurrence", [0] * 7)
            days = [i for i, enabled in enumerate(recurrence) if enabled]
            return {
                "objectId": event.get("objectId"),
                "name": event.get("name", f"Event {time_str}"),
                "time": time_str,
                "enabled": event.get("enabled", False),
                "days": days,
                "recurrence": recurrence,
                "event_time": event_time,
                "cmd": event.get("cmd", 0),
                "brightness": event.get("brightness", 100),
                "volume": event.get("volume", 0),
                "length_min": event.get("length_min", 0),
                "remi": self._pointer("Remi", device_id),
                "face": event.get("face", {}),
                "lightnight": event.get("lightnight", [255, 255, 255])
            }
        except Exception: return None

    async def create_alarm(self, object_id: str, time: str, **kwargs) -> dict[str, Any]:
        """Create a new alarm for a Remi device."""
        # Convert time HH:MM to [H, M] for Event class
        time_parts = time.split(":")
        event_time = [int(time_parts[0]), int(time_parts[1])] if len(time_parts) >= 2 else [0, 0]
        
        payload = {
            "remi": self._pointer("Remi", object_id),
            "event_time": event_time,
            "enabled": kwargs.get("enabled", True),
            "recurrence": kwargs.get("recurrence", [1] * 7),
        }
        # Add other kwargs as needed
        
        for cls in ["Event", "Alarm", "Schedule"]:
            try:
                result = await self._request("POST", f"/classes/{cls}", json=payload)
                self.alarms.pop(object_id, None)
                return result
            except RemiAPIError:
                continue
        raise RemiAPIError("Failed to create alarm")

    async def update_alarm(self, object_id: str, alarm_id: str, **kwargs) -> dict[str, Any]:
        """Update an existing alarm, trying multiple classes with correct payloads."""
        for cls in ["Event", "Alarm", "Schedule"]:
            payload = kwargs.copy()
            
            # Class-specific payload mapping
            if cls == "Event":
                # Map 'time' to 'event_time'
                if "time" in payload:
                    time_parts = payload["time"].split(":")
                    if len(time_parts) >= 2:
                        payload["event_time"] = [int(time_parts[0]), int(time_parts[1])]
                    del payload["time"]
                
                # Map 'days' to 'recurrence'
                if "days" in payload:
                    recurrence = [0] * 7
                    for day_index in payload["days"]:
                        if 0 <= day_index < 7:
                            recurrence[day_index] = 1
                    payload["recurrence"] = recurrence
                    del payload["days"]
                
                # Map 'face' (name) to face pointer
                if "face" in payload and isinstance(payload["face"], str):
                    face_mapping = {
                        "sleepy_face": "sleepyFace",
                        "awake_face": "awakeFace",
                        "blank_face": "blankFace",
                        "semi_awake_face": "semiAwakeFace",
                        "smily_face": "smilyFace",
                    }
                    api_face_name = face_mapping.get(payload["face"], payload["face"])
                    face_id = self.faces.get(api_face_name)
                    if not face_id:
                        await self.get_faces(refresh=True)
                        face_id = self.faces.get(api_face_name)
                    if face_id:
                        payload["face"] = self._pointer("Face", face_id)
                    else:
                        del payload["face"]
            
            try:
                result = await self._request("PUT", f"/classes/{cls}/{alarm_id}", json=payload)
                self.alarms.pop(object_id, None)
                _LOGGER.info("Successfully updated alarm %s via class %s", alarm_id, cls)
                return result
            except RemiAPIError as e:
                _LOGGER.warning("Update failed for class %s (id: %s): %s", cls, alarm_id, e)
                continue
        
        raise RemiAPIError(f"Failed to update alarm {alarm_id} after trying all classes")

    async def delete_alarm(self, object_id: str, alarm_id: str) -> bool:
        """Delete an alarm."""
        for cls in ["Event", "Alarm", "Schedule"]:
            try:
                await self._request("DELETE", f"/classes/{cls}/{alarm_id}")
                self.alarms.pop(object_id, None)
                return True
            except RemiAPIError:
                continue
        return False

    async def enable_alarm(self, object_id: str, alarm_id: str) -> dict[str, Any]:
        """Enable an alarm."""
        return await self.update_alarm(object_id, alarm_id, enabled=True)

    async def disable_alarm(self, object_id: str, alarm_id: str) -> dict[str, Any]:
        """Disable an alarm."""
        return await self.update_alarm(object_id, alarm_id, enabled=False)

    async def snooze_alarm(self, object_id: str, alarm_id: str, duration: int = 9) -> dict[str, Any]:
        """Snooze an alarm for a specified duration."""
        now = datetime.now()
        snooze_until = now + timedelta(minutes=duration)
        payload = {
            "snoozed": True,
            "snoozeUntil": snooze_until.isoformat(),
        }
        for cls in ["Event", "Alarm", "Schedule"]:
            try:
                result = await self._request("PUT", f"/classes/{cls}/{alarm_id}", json=payload)
                self.alarms.pop(object_id, None)
                return result
            except RemiAPIError:
                continue
        raise RemiAPIError("Snooze not supported")

    async def trigger_alarm(self, object_id: str, alarm_id: str) -> dict[str, Any]:
        """Manually trigger an alarm."""
        # Get alarm details
        alarms = await self.get_alarms(object_id, refresh=True)
        alarm = next((a for a in alarms if a.get("objectId") == alarm_id), None)

        if not alarm:
            raise RemiAPIError(f"Alarm {alarm_id} not found")

        # Apply alarm settings to the device
        if "face" in alarm:
            face_id = alarm["face"].get("objectId") if isinstance(alarm["face"], dict) else alarm["face"]
            if face_id:
                face_name = None
                for name, fid in self.faces.items():
                    if fid == face_id:
                        face_name = name
                        break
                if face_name:
                    await self.set_face_by_name(object_id, face_name)

        if "volume" in alarm:
            await self.set_volume(object_id, alarm["volume"])

        if "sound" in alarm:
            await self.play_media(object_id, alarm["sound"])

        _LOGGER.debug("Manually triggered alarm %s", alarm_id)
        return {"triggered": True, "alarm_id": alarm_id}
