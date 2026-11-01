"""Switch platform for Zehnder ComfoClime."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, STATUS_AUTO, STATUS_MANUAL
from .coordinator import ZehnderDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Zehnder switch entities."""
    coordinator: ZehnderDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SwitchEntity] = [
        ZehnderHeatPumpSwitch(coordinator, entry),
        ZehnderAutoModeSwitch(coordinator, entry),
        ZehnderAutoSeasonSwitch(coordinator, entry),
    ]
    async_add_entities(entities)


class ZehnderHeatPumpSwitch(
    CoordinatorEntity[ZehnderDataUpdateCoordinator], SwitchEntity
):
    """Switch to toggle the heat pump between Active and Standby."""

    _attr_has_entity_name = True
    _attr_translation_key = "heatpump_power"
    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(
        self, coordinator: ZehnderDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._clime_uuid = (
            coordinator.api.clime_uuid or entry.data.get("clime_uuid") or "clime"
        )
        self._attr_unique_id = f"{self._clime_uuid}_heatpump_power"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
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
        """Return true if heat pump is active (not in standby)."""
        dashboard = self.coordinator.data.get("dashboard", {})
        return not dashboard.get("hpStandby", False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the heat pump (disable standby)."""
        await self.coordinator.api.set_hp_standby(False)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the heat pump (enable standby)."""
        await self.coordinator.api.set_hp_standby(True)
        await self.coordinator.async_request_refresh()


class ZehnderAutoModeSwitch(
    CoordinatorEntity[ZehnderDataUpdateCoordinator], SwitchEntity
):
    """Switch to toggle between Automatic Profile and Manual Setpoint mode."""

    _attr_has_entity_name = True
    _attr_translation_key = "auto_mode"
    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(
        self, coordinator: ZehnderDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._clime_uuid = (
            coordinator.api.clime_uuid or entry.data.get("clime_uuid") or "clime"
        )
        self._attr_unique_id = f"{self._clime_uuid}_auto_mode"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
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
        """Return true if in automatic profile mode (status == 1)."""
        dashboard = self.coordinator.data.get("dashboard", {})
        return dashboard.get("status") == STATUS_AUTO

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable automatic profile mode."""
        await self.coordinator.api.set_status(STATUS_AUTO)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Switch to manual mode."""
        await self.coordinator.api.set_status(STATUS_MANUAL)
        await self.coordinator.async_request_refresh()


class ZehnderAutoSeasonSwitch(
    CoordinatorEntity[ZehnderDataUpdateCoordinator], SwitchEntity
):
    """Switch to toggle between Automatic Season Recognition and Manual Season mode."""

    _attr_has_entity_name = True
    _attr_translation_key = "auto_season"
    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(
        self, coordinator: ZehnderDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._clime_uuid = (
            coordinator.api.clime_uuid or entry.data.get("clime_uuid") or "clime"
        )
        self._attr_unique_id = f"{self._clime_uuid}_auto_season"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
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
        """Return true if automatic season mode is enabled (season.status == 1)."""
        tp = self.coordinator.data.get("thermal_profile", {})
        return tp.get("season", {}).get("status") == 1

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable automatic season mode."""
        await self.coordinator.api.set_auto_season(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable automatic season mode (manual season)."""
        await self.coordinator.api.set_auto_season(False)
        await self.coordinator.async_request_refresh()
