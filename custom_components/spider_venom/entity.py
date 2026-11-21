"""Base entities for Spider Grills Venom."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo, format_mac
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_DEVICE_NAME, CONF_MAC, CONF_MODEL, CONF_THING_NAME, DOMAIN
from .coordinator import SpiderVenomDataUpdateCoordinator


class SpiderVenomEntity(CoordinatorEntity[SpiderVenomDataUpdateCoordinator]):
    """Base Spider Grills entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SpiderVenomDataUpdateCoordinator,
        entry: ConfigEntry,
        key: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._thing_name = entry.data[CONF_THING_NAME]
        self._attr_unique_id = f"{self._thing_name}_{key}"
        mac = entry.data.get(CONF_MAC)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._thing_name)},
            connections={(CONNECTION_NETWORK_MAC, format_mac(mac))} if mac else set(),
            manufacturer="Spider Grills",
            model=entry.data.get(CONF_MODEL) or "Venom",
            name=entry.data.get(CONF_DEVICE_NAME) or "Venom",
        )
