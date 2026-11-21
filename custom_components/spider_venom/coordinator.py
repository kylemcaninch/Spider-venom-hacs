"""Data update coordinator for Spider Grills Venom."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SpiderGrillsAccountClient, SpiderVenomApiError, SpiderVenomAuthError
from .const import (
    CONF_MAC,
    CONF_MODEL,
    CONF_THING_NAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    TELEMETRY_WINDOW_SECONDS,
)

_LOGGER = logging.getLogger(__name__)


class SpiderVenomDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Poll the latest telemetry point for one Spider Grills device."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: SpiderGrillsAccountClient,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        interval_seconds = entry.data.get(CONF_SCAN_INTERVAL)
        interval = (
            timedelta(seconds=interval_seconds)
            if isinstance(interval_seconds, int)
            else DEFAULT_SCAN_INTERVAL
        )
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=interval)
        self.client = client
        self.entry = entry
        self.thing_name: str = entry.data[CONF_THING_NAME]

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch the newest telemetry point and normalize it."""
        try:
            point = await self.client.async_get_latest_point(self.thing_name, TELEMETRY_WINDOW_SECONDS)
        except SpiderVenomAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except SpiderVenomApiError as err:
            raise UpdateFailed(str(err)) from err
        return normalize_point(point, self.entry.data)

    @property
    def reported(self) -> dict[str, Any]:
        """Return the normalized device state."""
        return self.data or {}


def normalize_point(point: dict[str, Any] | None, entry_data: Any) -> dict[str, Any]:
    """Map a graph point into the state shape the entities read."""
    state: dict[str, Any] = {
        "model": entry_data.get(CONF_MODEL),
        "mac": entry_data.get(CONF_MAC),
        "online": point is not None,
    }
    if point is None:
        return state

    pit = point.get("pit") if isinstance(point.get("pit"), dict) else {}
    state.update(
        {
            "timestamp": point.get("timestamp"),
            "fah": point.get("fah"),
            "vers": point.get("vers"),
            "rssi": point.get("rssi"),
            "pit_temp": pit.get("temp"),
            "pit_display_temp": pit.get("disp"),
            "pit_target": pit.get("trgt"),
            "pit_min": pit.get("min"),
            "pit_max": pit.get("max"),
            "intensity": pit.get("intensity"),
        }
    )
    for probe in ("p1", "p2"):
        data = point.get(probe) if isinstance(point.get(probe), dict) else {}
        state[f"{probe}_temp"] = data.get("temp")
        state[f"{probe}_target"] = data.get("trgt")
    return state
