"""Client for the Spider Grills cloud API (spidergrills.app)."""

from __future__ import annotations

import json
import logging
import socket
import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiohttp import ClientConnectorError, ClientError, ClientSession

_LOGGER = logging.getLogger(__name__)

BASE_URL = "https://spidergrills.app"

_REDACTED_KEYS = {
    "accesstoken",
    "authorization",
    "email",
    "fcmtoken",
    "password",
    "refreshtoken",
}


class SpiderVenomApiError(Exception):
    """Raised when the Spider Grills cloud API cannot be reached or fails."""


class SpiderVenomAuthError(SpiderVenomApiError):
    """Raised when the Spider Grills credentials or tokens are rejected."""


TokenCallback = Callable[[str, str | None], Awaitable[None] | None]


class SpiderGrillsAccountClient:
    """Client for the Spider Grills account API used by the mobile app."""

    def __init__(
        self,
        *,
        session: ClientSession,
        access_token: str | None = None,
        refresh_token: str | None = None,
        on_tokens_updated: TokenCallback | None = None,
        base_url: str = BASE_URL,
    ) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")
        self.access_token = access_token
        self.refresh_token = refresh_token
        self._on_tokens_updated = on_tokens_updated

    async def async_login(self, *, email: str, password: str) -> str:
        """Log in and store the access and refresh tokens."""
        response = await self._async_request(
            "POST",
            "/auth/login",
            json_payload={"email": email, "password": password},
            authenticated=False,
        )
        await self._async_store_tokens(response, "Login")
        assert self.access_token is not None
        return self.access_token

    async def async_refresh(self) -> None:
        """Exchange the refresh token for a new access token."""
        if not self.refresh_token:
            raise SpiderVenomAuthError("No refresh token available")
        try:
            response = await self._async_request(
                "POST",
                "/auth/refresh",
                json_payload={"refreshToken": self.refresh_token},
                authenticated=False,
            )
        except SpiderVenomApiError as err:
            if isinstance(err, SpiderVenomAuthError) or "HTTP 400" in str(err):
                raise SpiderVenomAuthError(f"Token refresh rejected: {err}") from err
            raise
        await self._async_store_tokens(response, "Token refresh")

    async def async_get_devices(self) -> list[dict[str, Any]]:
        """Fetch devices for the logged-in account."""
        response = await self._async_authed_request("GET", "/api/devices")
        if isinstance(response, list):
            devices = response
        elif isinstance(response, dict) and isinstance(response.get("data"), list):
            devices = response["data"]
        elif isinstance(response, dict) and isinstance(response.get("devices"), list):
            devices = response["devices"]
        else:
            raise SpiderVenomApiError("Devices response had an unexpected shape")
        return [device for device in devices if isinstance(device, dict)]

    async def async_get_graph_points(self, thing_name: str, start: int, end: int) -> list[dict[str, Any]]:
        """Fetch telemetry points (about one every 5 seconds) for a time window."""
        response = await self._async_authed_request(
            "GET", f"/api/devices/{thing_name}/graph-points/{int(start)}/{int(end)}"
        )
        if not isinstance(response, list):
            raise SpiderVenomApiError("Graph points response had an unexpected shape")
        return [point for point in response if isinstance(point, dict)]

    async def async_get_latest_point(
        self, thing_name: str, window_seconds: int = 300
    ) -> dict[str, Any] | None:
        """Return the newest telemetry point, or None if the device is not reporting."""
        now = int(time.time())
        points = await self.async_get_graph_points(thing_name, now - window_seconds, now + 60)
        if not points:
            return None
        return max(points, key=lambda point: point.get("timestamp") or 0)

    async def _async_store_tokens(self, response: Any, label: str) -> None:
        if not isinstance(response, dict):
            raise SpiderVenomApiError(f"{label} response had an unexpected shape")
        token = response.get("accessToken")
        if not isinstance(token, str) or not token:
            raise SpiderVenomAuthError(f"{label} response did not include an access token")
        self.access_token = token
        refresh = response.get("refreshToken")
        if isinstance(refresh, str) and refresh:
            self.refresh_token = refresh
        if self._on_tokens_updated is not None:
            result = self._on_tokens_updated(self.access_token, self.refresh_token)
            if result is not None:
                await result

    async def _async_authed_request(self, method: str, path: str) -> Any:
        if not self.access_token:
            await self.async_refresh()
        try:
            return await self._async_request(method, path)
        except SpiderVenomAuthError:
            if not self.refresh_token:
                raise
            _LOGGER.debug("Access token rejected; refreshing")
            await self.async_refresh()
            return await self._async_request(method, path)

    async def _async_request(
        self,
        method: str,
        path: str,
        *,
        json_payload: dict[str, Any] | None = None,
        authenticated: bool = True,
    ) -> Any:
        headers = {"Accept": "application/json"}
        if json_payload is not None:
            headers["Content-Type"] = "application/json"
        if authenticated and self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"

        try:
            async with self._session.request(
                method,
                f"{self._base_url}{path}",
                headers=headers,
                json=json_payload,
            ) as response:
                status = response.status
                body = await response.text()
                _log_response_body(f"Spider Grills API {method} {path}", status, body)
        except ClientConnectorError as err:
            raise SpiderVenomApiError(f"Spider Grills API could not connect: {err}") from err
        except (TimeoutError, socket.gaierror) as err:
            raise SpiderVenomApiError(f"Spider Grills API timed out or DNS failed: {err}") from err
        except ClientError as err:
            raise SpiderVenomApiError(f"Spider Grills API request failed: {err}") from err

        if status in (401, 403):
            raise SpiderVenomAuthError(f"Spider Grills API returned HTTP {status} for {path}")
        if status < 200 or status >= 300:
            raise SpiderVenomApiError(f"Spider Grills API returned HTTP {status} for {path}")

        try:
            return json.loads(body) if body else {}
        except json.JSONDecodeError as err:
            raise SpiderVenomApiError("Spider Grills API response was not JSON") from err


def _log_response_body(label: str, status: int, body: str) -> None:
    """Log response bodies for API discovery without leaking secrets."""
    if not _LOGGER.isEnabledFor(logging.DEBUG):
        return
    _LOGGER.debug("%s returned HTTP %s body: %s", label, status, _redacted_body(body)[:4000])


def _redacted_body(body: str) -> str:
    if not body:
        return ""
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return body
    return json.dumps(_redact_value(parsed), sort_keys=True)


def _redact_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "***REDACTED***" if _is_sensitive_key(key) else _redact_value(child)
            for key, child in value.items()
        }
    if isinstance(value, list):
        return [_redact_value(child) for child in value]
    return value


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower()
    return normalized in _REDACTED_KEYS or normalized.endswith("token")
