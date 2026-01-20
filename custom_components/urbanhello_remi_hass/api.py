from __future__ import annotations

import aiohttp
import asyncio
import logging
import time
from typing import Any

_LOGGER = logging.getLogger(__name__)


class RemiAPIError(Exception):
    """Generic exception for RemiAPI failures."""


class RemiAPI:
    """Async client for UrbanHello (Rémi) Parse-based API.

    This client aims to encapsulate operations used by the Home Assistant
    integration and other consumers: authentication, listing Remi devices,
    reading device state, changing face/volume/brightness and playing media.

    Notes:
    - Some Parse servers reject GET requests against /classes/* endpoints and
      instead accept POST with payload {"_method": "GET"}. This client will
      attempt a normal request first and fall back to the POST technique when
      a GET against a /classes/ path fails.
    - The API uses Parse pointers for linked objects (faces). Helper
      functions create the correct payload for updates.
    """

    BASE_URL = "https://remi2.urbanhello.com/parse"
    APP_ID = "jf1a0bADt5fq"

    def __init__(self, username: str, password: str, cache_duration: int = 60, request_timeout: int = 15) -> None:
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
        self._session: aiohttp.ClientSession | None = None
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
        """Perform an HTTP request and return parsed JSON or raw text.

        If a GET against a /classes/ path fails due to server behavior, retry
        using POST with payload {'_method': 'GET'}.
        """
        session = await self._ensure_session()
        url = f"{self.BASE_URL}{path}"
        timeout = timeout or self._request_timeout

        try:
            async with session.request(method, url, headers=self._headers(include_session), json=json, timeout=timeout) as resp:
                text = await resp.text()
                if resp.status >= 400:
                    _LOGGER.debug("Request %s %s failed: %s - %s", method, url, resp.status, text)
                    raise RemiAPIError(f"HTTP {resp.status}: {text}")
                # Try to parse JSON; if not JSON return raw text
                try:
                    return await resp.json()
                except Exception:
                    return text
        except Exception as exc:
            # If GET fails on /classes paths, retry using POST + _method=GET
            if method.upper() == "GET" and "/classes/" in path:
                _LOGGER.debug("GET failed for %s, retrying with POST _method=GET: %s", url, exc)
                fallback = (json or {}).copy()
                fallback["_method"] = "GET"
                try:
                    async with session.post(url, headers=self._headers(include_session), json=fallback, timeout=timeout) as resp:
                        text = await resp.text()
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
            # Other failures bubble up as RemiAPIError
            _LOGGER.debug("Request exception for %s %s: %s", method, url, exc)
            raise RemiAPIError(str(exc))

    async def login(self) -> dict[str, Any]:
        """Authenticate and populate session token, known Remi devices and faces.

        Returns the parsed JSON response from /login.
        """
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

        # Warm faces cache
        try:
            await self.get_faces(refresh=True)
        except Exception:
            _LOGGER.debug("Could not retrieve faces during login", exc_info=True)

        _LOGGER.debug("Logged in as %s, session token length=%s, remis=%d", self.username, len(self.session_token or ""), len(self.remis))
        return data

    async def logout(self) -> None:
        """Invalidate the current session token on the server and close session.

        The server's /logout endpoint is called, local token is cleared and the
        aiohttp session closed.
        """
        if not self.session_token:
            return
        try:
            await self._request("POST", "/logout", json={}, include_session=True)
        except RemiAPIError:
            _LOGGER.debug("Logout request failed but session will be cleared locally")
        finally:
            self.session_token = None
            # Close the underlying HTTP session
            if self._session and not self._session.closed:
                await self._session.close()
                self._session = None

    async def get_faces(self, refresh: bool = False) -> dict[str, str]:
        """Retrieve available faces and return mapping name -> objectId.

        Results are cached in self.faces unless refresh=True.
        """
        if self.faces and not refresh:
            return self.faces

        result = await self._request("GET", "/classes/Face")
        results = result.get("results", []) if isinstance(result, dict) else []
        # Build mapping name -> objectId
        faces: dict[str, str] = {}
        for item in results:
            name = item.get("name")
            oid = item.get("objectId")
            if name and oid:
                faces[name] = oid
        self.faces = faces
        _LOGGER.debug("Retrieved %d faces", len(self.faces))
        return self.faces

    async def list_remis(self, refresh: bool = False) -> list[dict[str, Any]]:
        """List Remi devices. Cached unless refresh=True."""
        if self.remis and not refresh:
            return self.remis
        result = await self._request("GET", "/classes/Remi")
        results = result.get("results", []) if isinstance(result, dict) else []
        self.remis = results
        _LOGGER.debug("Found %d remis", len(self.remis))
        return self.remis

    def _is_cache_valid(self, key: str) -> bool:
        expiry = self.cache_expiry.get(key)
        return expiry is not None and expiry > time.time()

    async def get_remi_info(self, object_id: str, refresh: bool = False) -> dict[str, Any]:
        """Retrieve Remi information with optional caching.

        Returns a normalized dict containing fields commonly used by the
        integration. The raw response is available under the 'raw' key.
        """
        if not refresh and self._is_cache_valid(object_id):
            return self.cache[object_id]

        data = await self._request("GET", f"/classes/Remi/{object_id}")
        if not isinstance(data, dict):
            raise RemiAPIError("Unexpected response when fetching Remi info")

        # Normalise fields with fallbacks
        remi_info: dict[str, Any] = {
            "temperature": (data.get("temp") + 40) if data.get("temp") is not None else None,
            "luminosity": data.get("luminosity"),
            "name": data.get("name"),
            "face": data.get("face", {}).get("objectId") if data.get("face") else None,
            "volume": data.get("volume"),
            "light_min": data.get("light_min"),
            "raw": data,
        }

        # Cache it
        self.cache[object_id] = remi_info
        self.cache_expiry[object_id] = time.time() + self.cache_duration
        _LOGGER.debug("Cached remi %s for %.1fs", object_id, self.cache_duration)
        return remi_info

    def _pointer(self, class_name: str, object_id: str) -> dict[str, str]:
        return {"__type": "Pointer", "className": class_name, "objectId": object_id}

    async def _update_remi(self, object_id: str, payload: dict[str, Any]) -> Any:
        """Generic helper to update a Remi object via PUT and invalidate cache."""
        result = await self._request("PUT", f"/classes/Remi/{object_id}", json=payload)
        # Invalidate cache for that Remi
        self.cache_expiry.pop(object_id, None)
        self.cache.pop(object_id, None)
        _LOGGER.debug("Updated remi %s with %s", object_id, payload)
        return result

    async def set_brightness(self, object_id: str, brightness: int) -> Any:
        """Set the brightness (luminosity) of a Remi device.

        brightness expected range is 0..100 depending on server.
        """
        if not (0 <= brightness <= 100):
            _LOGGER.debug("Brightness %s out of expected range 0..100", brightness)
        return await self._update_remi(object_id, {"luminosity": brightness})

    async def set_night_luminosity(self, object_id: str, level: int) -> Any:
        """Set the night/minimum luminosity (light_min)."""
        return await self._update_remi(object_id, {"light_min": level})

    async def set_volume(self, object_id: str, level: int) -> Any:
        """Set the device volume."""
        return await self._update_remi(object_id, {"volume": level})

    async def set_noise_threshold(self, object_id: str, threshold: int) -> Any:
        """Set the noise notification threshold."""
        return await self._update_remi(object_id, {"noise_threshold": threshold})

    async def turn_on(self, object_id: str) -> Any:
        """Turn on the device by setting an appropriate face (sleepyFace by convention)."""
        face_id = self.faces.get("sleepyFace")
        if not face_id:
            await self.get_faces(refresh=True)
            face_id = self.faces.get("sleepyFace")
            if not face_id:
                raise RemiAPIError("sleepyFace not found in faces")
        payload = {"face": self._pointer("Face", face_id)}
        return await self._update_remi(object_id, payload)

    async def turn_off(self, object_id: str) -> Any:
        """Turn off the device by setting an appropriate face (awakeFace by convention)."""
        face_id = self.faces.get("awakeFace")
        if not face_id:
            await self.get_faces(refresh=True)
            face_id = self.faces.get("awakeFace")
            if not face_id:
                raise RemiAPIError("awakeFace not found in faces")
        payload = {"face": self._pointer("Face", face_id)}
        return await self._update_remi(object_id, payload)

    async def get_current_face(self, object_id: str) -> str | None:
        """Return the friendly name of the current face for the given Remi, if known."""
        info = await self.get_remi_info(object_id)
        fid = info.get("face")
        if not fid:
            return None
        # Reverse lookup
        for name, oid in self.faces.items():
            if oid == fid:
                return name
        # Try to refresh faces once and lookup again
        await self.get_faces(refresh=True)
        for name, oid in self.faces.items():
            if oid == fid:
                return name
        return None

    async def set_face_by_name(self, object_id: str, face_name: str) -> Any:
        """Set the device face by friendly name (e.g. 'sleepyFace')."""
        face_id = self.faces.get(face_name)
        if not face_id:
            await self.get_faces(refresh=True)
            face_id = self.faces.get(face_name)
            if not face_id:
                raise RemiAPIError(f"Unknown face '{face_name}'")
        payload = {"face": self._pointer("Face", face_id)}
        return await self._update_remi(object_id, payload)

    async def play_media(self, object_id: str, sound: str, volume: int | None = None) -> Any:
        """Instruct the device to play a sound.

        The implementation sets a 'sound' field on the Remi object. If the
        server uses a different mechanism (cloud function, dedicated field)
        this method should be adapted.

        Args:
            object_id: The Remi device objectId
            sound: Sound identifier to play
            volume: Optional volume level (0-100) for this playback

        Returns:
            Result of the update operation
        """
        payload: dict[str, Any] = {"sound": sound}
        if volume is not None:
            payload["volume"] = volume
        return await self._update_remi(object_id, payload)

    async def stop_sound(self, object_id: str) -> Any:
        """Stop currently playing sound/alarm.

        Args:
            object_id: The Remi device objectId

        Returns:
            Result of the update operation
        """
        # Setting sound to empty/null should stop playback
        payload: dict[str, Any] = {"sound": ""}
        return await self._update_remi(object_id, payload)

    async def close(self) -> None:
        """Close the underlying HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    # ========================================================================
    # ALARM MANAGEMENT METHODS
    # ========================================================================

    async def get_alarms(self, object_id: str, refresh: bool = False) -> list[dict[str, Any]]:
        """Retrieve all alarms for a specific Remi device from Event class.

        Args:
            object_id: The Remi device objectId
            refresh: Force refresh from server, bypass cache

        Returns:
            List of alarm dictionaries with normalized fields
        """
        if not refresh and object_id in self.alarms:
            return self.alarms[object_id]

        alarms: list[dict[str, Any]] = []

        # Try to get alarms from Event class (this is where Remi stores alarm clocks)
        try:
            where = {"remi": self._pointer("Remi", object_id)}
            result = await self._request("GET", "/classes/Event", json={"where": where})
            if isinstance(result, dict) and "results" in result:
                events = result.get("results", [])
                _LOGGER.info("Found %d events for Remi device %s", len(events), object_id)

                # Convert Event objects to standardized alarm format
                for event in events:
                    alarm = self._convert_event_to_alarm(event, object_id)
                    if alarm:
                        alarms.append(alarm)

                _LOGGER.info("Converted %d events to alarms for device %s", len(alarms), object_id)
        except RemiAPIError as e:
            _LOGGER.warning("Failed to get events from Event class: %s", e)

        # Cache the results
        self.alarms[object_id] = alarms
        return alarms

    def _convert_event_to_alarm(self, event: dict[str, Any], device_id: str) -> dict[str, Any] | None:
        """Convert an Event object to a standardized alarm format.

        Args:
            event: Event object from Parse
            device_id: The Remi device objectId

        Returns:
            Standardized alarm dictionary or None if conversion fails
        """
        try:
            # Extract time from event_time array [hour, minute]
            event_time = event.get("event_time", [0, 0])
            if len(event_time) >= 2:
                hour = event_time[0]
                minute = event_time[1]
                time_str = f"{hour:02d}:{minute:02d}"
            else:
                time_str = "00:00"

            # Convert recurrence array to day indices (0=Monday, 6=Sunday)
            recurrence = event.get("recurrence", [0, 0, 0, 0, 0, 0, 0])
            days = [i for i, enabled in enumerate(recurrence) if enabled]

            # Create standardized alarm object
            alarm = {
                "objectId": event.get("objectId"),
                "name": event.get("name", f"Event {time_str}"),
                "time": time_str,
                "enabled": event.get("enabled", False),
                "days": days,  # List of day indices
                "recurrence": recurrence,  # Original recurrence array
                "event_time": event_time,  # Original event_time array
                "cmd": event.get("cmd", 0),
                "brightness": event.get("brightness", 100),
                "volume": event.get("volume", 0),
                "length_min": event.get("length_min", 0),
                "remi": self._pointer("Remi", device_id),
                "face": event.get("face", {}),
                "lightnight": event.get("lightnight", [255, 255, 255])
            }

            return alarm
        except Exception as e:
            _LOGGER.error("Failed to convert event to alarm: %s", e)
            return None

    async def create_alarm(
        self,
        object_id: str,
        time: str,
        enabled: bool = True,
        days: list[int] | None = None,
        sound: str | None = None,
        face: str | None = None,
        volume: int | None = None,
        label: str | None = None,
    ) -> dict[str, Any]:
        """Create a new alarm for a Remi device.

        Args:
            object_id: The Remi device objectId
            time: Alarm time in format "HH:MM" (24-hour)
            enabled: Whether the alarm is enabled
            days: List of weekdays (0=Monday, 6=Sunday), None for daily
            sound: Sound identifier to play
            face: Face name to display when alarm triggers
            volume: Volume level (0-100) for alarm
            label: Human-readable label for the alarm

        Returns:
            The created alarm object
        """
        # Prepare the alarm payload
        payload: dict[str, Any] = {
            "remi": self._pointer("Remi", object_id),
            "time": time,
            "enabled": enabled,
        }

        if days is not None:
            payload["days"] = days
        if sound is not None:
            payload["sound"] = sound
        if face is not None:
            # Get face objectId
            face_id = self.faces.get(face)
            if not face_id:
                await self.get_faces(refresh=True)
                face_id = self.faces.get(face)
            if face_id:
                payload["face"] = self._pointer("Face", face_id)
        if volume is not None:
            payload["volume"] = volume
        if label is not None:
            payload["label"] = label

        # Try to create via Alarm class
        try:
            result = await self._request("POST", "/classes/Alarm", json=payload)
            # Invalidate cache
            self.alarms.pop(object_id, None)
            _LOGGER.debug("Created alarm for %s: %s", object_id, result)
            return result
        except RemiAPIError as e:
            _LOGGER.debug("Could not create via Alarm class: %s", e)

            # Fallback: Try Schedule class
            try:
                result = await self._request("POST", "/classes/Schedule", json=payload)
                self.alarms.pop(object_id, None)
                _LOGGER.debug("Created schedule for %s: %s", object_id, result)
                return result
            except RemiAPIError as e2:
                _LOGGER.error("Could not create alarm/schedule: %s", e2)
                raise RemiAPIError(f"Failed to create alarm: {e2}")

    async def update_alarm(
        self,
        object_id: str,
        alarm_id: str,
        time: str | None = None,
        enabled: bool | None = None,
        days: list[int] | None = None,
        sound: str | None = None,
        face: str | None = None,
        volume: int | None = None,
        label: str | None = None,
    ) -> dict[str, Any]:
        """Update an existing alarm.

        Args:
            object_id: The Remi device objectId
            alarm_id: The alarm objectId to update
            time: New alarm time in format "HH:MM"
            enabled: Whether the alarm is enabled
            days: List of weekdays (0=Monday, 6=Sunday)
            sound: Sound identifier to play
            face: Face name to display
            volume: Volume level (0-100)
            label: Human-readable label

        Returns:
            The updated alarm object
        """
        payload: dict[str, Any] = {}

        if time is not None:
            payload["time"] = time
        if enabled is not None:
            payload["enabled"] = enabled
        if days is not None:
            payload["days"] = days
        if sound is not None:
            payload["sound"] = sound
        if face is not None:
            face_id = self.faces.get(face)
            if not face_id:
                await self.get_faces(refresh=True)
                face_id = self.faces.get(face)
            if face_id:
                payload["face"] = self._pointer("Face", face_id)
        if volume is not None:
            payload["volume"] = volume
        if label is not None:
            payload["label"] = label

        if not payload:
            raise ValueError("No fields to update")

        # Try Alarm class first
        try:
            result = await self._request("PUT", f"/classes/Alarm/{alarm_id}", json=payload)
            self.alarms.pop(object_id, None)
            _LOGGER.debug("Updated alarm %s: %s", alarm_id, result)
            return result
        except RemiAPIError as e:
            _LOGGER.debug("Could not update via Alarm class: %s", e)

            # Fallback to Schedule class
            try:
                result = await self._request("PUT", f"/classes/Schedule/{alarm_id}", json=payload)
                self.alarms.pop(object_id, None)
                _LOGGER.debug("Updated schedule %s: %s", alarm_id, result)
                return result
            except RemiAPIError as e2:
                _LOGGER.error("Could not update alarm/schedule: %s", e2)
                raise RemiAPIError(f"Failed to update alarm: {e2}")

    async def delete_alarm(self, object_id: str, alarm_id: str) -> bool:
        """Delete an alarm.

        Args:
            object_id: The Remi device objectId
            alarm_id: The alarm objectId to delete

        Returns:
            True if deletion was successful
        """
        # Try Alarm class first
        try:
            await self._request("DELETE", f"/classes/Alarm/{alarm_id}")
            self.alarms.pop(object_id, None)
            _LOGGER.debug("Deleted alarm %s", alarm_id)
            return True
        except RemiAPIError as e:
            _LOGGER.debug("Could not delete via Alarm class: %s", e)

            # Fallback to Schedule class
            try:
                await self._request("DELETE", f"/classes/Schedule/{alarm_id}")
                self.alarms.pop(object_id, None)
                _LOGGER.debug("Deleted schedule %s", alarm_id)
                return True
            except RemiAPIError as e2:
                _LOGGER.error("Could not delete alarm/schedule: %s", e2)
                raise RemiAPIError(f"Failed to delete alarm: {e2}")

    async def enable_alarm(self, object_id: str, alarm_id: str) -> dict[str, Any]:
        """Enable an alarm.

        Args:
            object_id: The Remi device objectId
            alarm_id: The alarm objectId to enable

        Returns:
            The updated alarm object
        """
        return await self.update_alarm(object_id, alarm_id, enabled=True)

    async def disable_alarm(self, object_id: str, alarm_id: str) -> dict[str, Any]:
        """Disable an alarm.

        Args:
            object_id: The Remi device objectId
            alarm_id: The alarm objectId to disable

        Returns:
            The updated alarm object
        """
        return await self.update_alarm(object_id, alarm_id, enabled=False)

    async def snooze_alarm(self, object_id: str, alarm_id: str, duration: int = 9) -> dict[str, Any]:
        """Snooze an alarm for a specified duration.

        Args:
            object_id: The Remi device objectId
            alarm_id: The alarm objectId to snooze
            duration: Snooze duration in minutes (default: 9)

        Returns:
            The updated alarm object or result
        """
        # Calculate new time based on current time + duration
        from datetime import datetime, timedelta

        now = datetime.now()
        snooze_time = now + timedelta(minutes=duration)
        new_time = snooze_time.strftime("%H:%M")

        # Create a snooze flag or update the alarm
        payload = {
            "snoozed": True,
            "snoozeUntil": snooze_time.isoformat(),
        }

        try:
            result = await self._request("PUT", f"/classes/Alarm/{alarm_id}", json=payload)
            self.alarms.pop(object_id, None)
            _LOGGER.debug("Snoozed alarm %s for %d minutes", alarm_id, duration)
            return result
        except RemiAPIError as e:
            _LOGGER.debug("Could not snooze via standard method: %s", e)
            # Fallback: just disable and re-enable later
            raise RemiAPIError(f"Snooze not supported by API: {e}")

    async def trigger_alarm(self, object_id: str, alarm_id: str) -> dict[str, Any]:
        """Manually trigger an alarm (for testing).

        Args:
            object_id: The Remi device objectId
            alarm_id: The alarm objectId to trigger

        Returns:
            Result of the trigger action
        """
        # Get alarm details
        alarms = await self.get_alarms(object_id, refresh=True)
        alarm = next((a for a in alarms if a.get("objectId") == alarm_id), None)

        if not alarm:
            raise RemiAPIError(f"Alarm {alarm_id} not found")

        # Apply alarm settings to the device
        actions = []

        # Set face if specified
        if "face" in alarm:
            face_id = alarm["face"].get("objectId") if isinstance(alarm["face"], dict) else alarm["face"]
            if face_id:
                # Find face name
                face_name = None
                for name, fid in self.faces.items():
                    if fid == face_id:
                        face_name = name
                        break
                if face_name:
                    await self.set_face_by_name(object_id, face_name)

        # Set volume if specified
        if "volume" in alarm:
            await self.set_volume(object_id, alarm["volume"])

        # Play sound if specified
        if "sound" in alarm:
            await self.play_media(object_id, alarm["sound"])

        _LOGGER.debug("Manually triggered alarm %s", alarm_id)
        return {"triggered": True, "alarm_id": alarm_id}
