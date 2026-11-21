"""Sensor entities for Spider Grills Venom."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import SpiderVenomDataUpdateCoordinator
from .entity import SpiderVenomEntity


@dataclass(frozen=True, kw_only=True)
class SpiderVenomSensorDescription(SensorEntityDescription):
    """Description of a Spider Grills sensor."""

    value_fn: Callable[[dict[str, Any]], Any]
    is_temperature: bool = False


def _key(name: str) -> Callable[[dict[str, Any]], Any]:
    return lambda state: state.get(name)


def _timestamp(state: dict[str, Any]) -> datetime | None:
    value = state.get("timestamp")
    if not isinstance(value, int | float) or value <= 0:
        return None
    return datetime.fromtimestamp(value, UTC)


def _temp(key: str, name: str, source: str) -> SpiderVenomSensorDescription:
    return SpiderVenomSensorDescription(
        key=key,
        name=name,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        is_temperature=True,
        value_fn=_key(source),
    )


SENSORS: tuple[SpiderVenomSensorDescription, ...] = (
    _temp("main_temp", "Current temperature", "pit_temp"),
    _temp("display_temp", "Displayed temperature", "pit_display_temp"),
    _temp("target_temp", "Target temperature", "pit_target"),
    _temp("probe_1_temp", "Probe 1 temperature", "p1_temp"),
    _temp("probe_1_target", "Probe 1 target", "p1_target"),
    _temp("probe_2_temp", "Probe 2 temperature", "p2_temp"),
    _temp("probe_2_target", "Probe 2 target", "p2_target"),
    SpiderVenomSensorDescription(
        key="target_min",
        name="Minimum target temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        entity_category=EntityCategory.DIAGNOSTIC,
        is_temperature=True,
        value_fn=_key("pit_min"),
    ),
    SpiderVenomSensorDescription(
        key="target_max",
        name="Maximum target temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        entity_category=EntityCategory.DIAGNOSTIC,
        is_temperature=True,
        value_fn=_key("pit_max"),
    ),
    SpiderVenomSensorDescription(
        key="heat_intensity",
        name="Heat intensity",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_key("intensity"),
    ),
    SpiderVenomSensorDescription(
        key="rssi",
        name="Signal strength",
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_key("rssi"),
    ),
    SpiderVenomSensorDescription(
        key="firmware_version",
        name="Firmware version",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_key("vers"),
    ),
    SpiderVenomSensorDescription(
        key="last_report",
        name="Last report",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_timestamp,
    ),
    SpiderVenomSensorDescription(
        key="model",
        name="Model",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_key("model"),
    ),
    SpiderVenomSensorDescription(
        key="mac_address",
        name="MAC address",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_key("mac"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Spider Grills sensors."""
    coordinator: SpiderVenomDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(SpiderVenomSensor(coordinator, entry, description) for description in SENSORS)


class SpiderVenomSensor(SpiderVenomEntity, SensorEntity):
    """Spider Grills sensor."""

    entity_description: SpiderVenomSensorDescription

    def __init__(
        self,
        coordinator: SpiderVenomDataUpdateCoordinator,
        entry: ConfigEntry,
        description: SpiderVenomSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, description.key)
        self.entity_description = description

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Report Fahrenheit or Celsius depending on the controller setting."""
        if self.entity_description.is_temperature:
            if self.coordinator.reported.get("fah") is False:
                return UnitOfTemperature.CELSIUS
            return UnitOfTemperature.FAHRENHEIT
        return self.entity_description.native_unit_of_measurement

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        return self.entity_description.value_fn(self.coordinator.reported)
