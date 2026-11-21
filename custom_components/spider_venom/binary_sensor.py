"""Binary sensor entities for Spider Grills Venom."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import SpiderVenomDataUpdateCoordinator
from .entity import SpiderVenomEntity


@dataclass(frozen=True, kw_only=True)
class SpiderVenomBinarySensorDescription(BinarySensorEntityDescription):
    """Description of a Spider Grills binary sensor."""

    value_fn: Callable[[dict[str, Any]], Any]


BINARY_SENSORS: tuple[SpiderVenomBinarySensorDescription, ...] = (
    SpiderVenomBinarySensorDescription(
        key="online",
        name="Reporting",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda state: state.get("online"),
    ),
    SpiderVenomBinarySensorDescription(
        key="fahrenheit_mode",
        name="Fahrenheit mode",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.get("fah"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Spider Grills binary sensors."""
    coordinator: SpiderVenomDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        SpiderVenomBinarySensor(coordinator, entry, description) for description in BINARY_SENSORS
    )


class SpiderVenomBinarySensor(SpiderVenomEntity, BinarySensorEntity):
    """Spider Grills binary sensor."""

    entity_description: SpiderVenomBinarySensorDescription

    def __init__(
        self,
        coordinator: SpiderVenomDataUpdateCoordinator,
        entry: ConfigEntry,
        description: SpiderVenomBinarySensorDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, entry, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return the binary sensor state."""
        value = self.entity_description.value_fn(self.coordinator.reported)
        return bool(value) if value is not None else None
