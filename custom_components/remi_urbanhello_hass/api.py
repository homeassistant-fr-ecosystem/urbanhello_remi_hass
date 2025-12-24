import aiohttp
import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

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

    def __init__(self, username: str, password: str, cache_duration: int = 60, request_timeout: int = 15):
        self.username = username
        self.password = password
        self.session_token: Optional[str] = None
        self.remis: List[Dict[str, Any]] = []
        # Generic cache storage for Remi objects keyed by objectId
        self.cache: Dict[str, Any] = {}
        self.cache_expiry: Dict[str, float] = {}
        self.cache_duration = float(cache_duration)
        # Faces map name -> objectId
        self.faces: Dict[str, str] = {}
        self._session: Optional[aiohttp.ClientSession] = None
        self._request_timeout = request_timeout

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    def _headers(self, include_session: bool = True) -> Dict[str, str]:
        headers = {
            "X-Parse-Application-Id": self.APP_ID,
            "Content-Type": "application/json",
        }
        if include_session and self.session_token:
            headers["X-Parse-Session-Token"] = self.session_token
        return headers

    async def _request(self, method: str, path: str, json: Optional[Dict] = None, timeout: Optional[int] = None, include_session: bool = True) -> Any:
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

    async def login(self) -> Dict[str, Any]:
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

    async def get_faces(self, refresh: bool = False) -> Dict[str, str]:
        """Retrieve available faces and return mapping name -> objectId.

        Results are cached in self.faces unless refresh=True.
        """
        if self.faces and not refresh:
            return self.faces

        result = await self._request("GET", "/classes/Face")
        results = result.get("results", []) if isinstance(result, dict) else []
        # Build mapping name -> objectId
        faces: Dict[str, str] = {}
        for item in results:
            name = item.get("name")
            oid = item.get("objectId")
            if name and oid:
                faces[name] = oid
        self.faces = faces
        _LOGGER.debug("Retrieved %d faces", len(self.faces))
        return self.faces

    async def list_remis(self, refresh: bool = False) -> List[Dict[str, Any]]:
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

    async def get_remi_info(self, object_id: str, refresh: bool = False) -> Dict[str, Any]:
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
        remi_info: Dict[str, Any] = {
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

    def _pointer(self, class_name: str, object_id: str) -> Dict[str, str]:
        return {"__type": "Pointer", "className": class_name, "objectId": object_id}

    async def _update_remi(self, object_id: str, payload: Dict[str, Any]) -> Any:
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

    async def get_current_face(self, object_id: str) -> Optional[str]:
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

    async def play_media(self, object_id: str, sound: str, volume: Optional[int] = None) -> Any:
        """Instruct the device to play a sound.

        The implementation sets a 'sound' field on the Remi object. If the
        server uses a different mechanism (cloud function, dedicated field)
        this method should be adapted.
        """
        payload: Dict[str, Any] = {"sound": sound}
        if volume is not None:
            payload["volume"] = volume
        return await self._update_remi(object_id, payload)

    async def close(self) -> None:
        """Close the underlying HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
