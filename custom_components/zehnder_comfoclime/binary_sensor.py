"""Binary sensor platform for Zehnder ComfoClime and ComfoAir Q."""
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
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ZehnderDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class ZehnderBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Class describing Zehnder binary sensor entities."""

    device_target: str  # "clime" or "q350"
    is_on_fn: Callable[[dict[str, Any]], bool]


BINARY_SENSOR_DESCRIPTIONS: tuple[ZehnderBinarySensorEntityDescription, ...] = (
    ZehnderBinarySensorEntityDescription(
        key="hp_active",
        translation_key="hp_active",
        device_target="clime",
        device_class=BinarySensorDeviceClass.RUNNING,
        is_on_fn=lambda data: not data.get("dashboard", {}).get("hpStandby", False),
    ),
    ZehnderBinarySensorEntityDescription(
        key="free_cooling_available",
        translation_key="free_cooling_available",
        device_target="clime",
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda data: bool(
            data.get("dashboard", {}).get("caqFreeCoolingAvailable", False)
        ),
    ),
    ZehnderBinarySensorEntityDescription(
        key="free_cooling_active",
        translation_key="free_cooling_active",
        device_target="clime",
        device_class=BinarySensorDeviceClass.RUNNING,
        is_on_fn=lambda data: bool(
            data.get("dashboard", {}).get("freeCoolingEnabled", False)
        ),
    ),
    ZehnderBinarySensorEntityDescription(
        key="bypass_active",
        translation_key="bypass_active",
        device_target="q350",
        device_class=BinarySensorDeviceClass.OPENING,
        is_on_fn=lambda data: (data.get("q350", {}).get("bypass_state_pct") or 0) > 0,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Zehnder binary sensor entities."""
    coordinator: ZehnderDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    has_q350 = bool(coordinator.api.q350_uuid or entry.data.get("q350_uuid"))
    entities = [
        ZehnderBinarySensor(coordinator, entry, desc)
        for desc in BINARY_SENSOR_DESCRIPTIONS
        if desc.device_target == "clime" or has_q350
    ]
    async_add_entities(entities)


class ZehnderBinarySensor(
    CoordinatorEntity[ZehnderDataUpdateCoordinator], BinarySensorEntity
):
    """Representation of a Zehnder Binary Sensor."""

    entity_description: ZehnderBinarySensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ZehnderDataUpdateCoordinator,
        entry: ConfigEntry,
        description: ZehnderBinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._clime_uuid = (
            coordinator.api.clime_uuid or entry.data.get("clime_uuid") or "clime"
        )
        self._q350_uuid = (
            coordinator.api.q350_uuid
            or entry.data.get("q350_uuid")
            or f"{self._clime_uuid}_q350"
        )

        target_uuid = (
            self._q350_uuid
            if description.device_target == "q350"
            else self._clime_uuid
        )
        self._attr_unique_id = f"{target_uuid}_{description.key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info based on target device."""
        if self.entity_description.device_target == "q350":
            return DeviceInfo(
                identifiers={(DOMAIN, self._q350_uuid)},
                name=self.coordinator.api.q350_name,
                manufacturer="Zehnder",
                model="ComfoAir Q350",
                via_device=(DOMAIN, self._clime_uuid),
            )
        return DeviceInfo(
            identifiers={(DOMAIN, self._clime_uuid)},
            name=self.coordinator.api.clime_name,
            manufacturer="Zehnder",
            model="ComfoClime 24",
            sw_version=self.coordinator.api.clime_version,
            configuration_url=f"http://{self.coordinator.api.host}",
        )

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        return self.entity_description.is_on_fn(self.coordinator.data)
