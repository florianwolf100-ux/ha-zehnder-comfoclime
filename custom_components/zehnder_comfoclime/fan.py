"""Fan platform for Zehnder ComfoAir Q ventilation unit."""
from __future__ import annotations

import logging
import math
from typing import Any

from homeassistant.components.fan import (
    FanEntity,
    FanEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util.percentage import (
    percentage_to_ranged_value,
    ranged_value_to_percentage,
)

from .const import DOMAIN
from .coordinator import ZehnderDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

SPEED_RANGE = (1, 3)
PRESET_MODES = ["1", "2", "3"]
PRESET_MAP = {
    "1": 1,
    "2": 2,
    "3": 3,
    "low": 1,
    "medium": 2,
    "high": 3,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Zehnder ventilation fan entity."""
    coordinator: ZehnderDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ZehnderVentilationFan(coordinator, entry)])


class ZehnderVentilationFan(
    CoordinatorEntity[ZehnderDataUpdateCoordinator], FanEntity
):
    """Fan entity representing the Zehnder ComfoAir Q ventilation unit."""

    _attr_has_entity_name = True
    _attr_name = "Ventilation"
    _attr_translation_key = "ventilation"
    _attr_speed_count = 3
    _attr_preset_modes = PRESET_MODES
    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
        | FanEntityFeature.PRESET_MODE
    )

    def __init__(
        self, coordinator: ZehnderDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the fan entity."""
        super().__init__(coordinator)
        self._clime_uuid = (
            coordinator.api.clime_uuid or entry.data.get("clime_uuid") or "clime"
        )
        self._q350_uuid = (
            coordinator.api.q350_uuid
            or entry.data.get("q350_uuid")
            or f"{self._clime_uuid}_q350"
        )
        self._attr_unique_id = f"{self._q350_uuid}_fan"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information attributing the fan to ComfoAir Q."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._q350_uuid)},
            name=self.coordinator.api.q350_name,
            manufacturer="Zehnder",
            model="ComfoAir Q350",
            via_device=(DOMAIN, self._clime_uuid),
        )

    @property
    def is_on(self) -> bool:
        """Return true if fan is on."""
        speed = self._current_speed
        return speed is not None and speed > 0

    @property
    def _current_speed(self) -> int:
        """Return current speed number (1, 2, or 3)."""
        dashboard = self.coordinator.data.get("dashboard", {})
        return int(dashboard.get("fanSpeed", 1))

    @property
    def percentage(self) -> int | None:
        """Return the current speed percentage."""
        speed = self._current_speed
        if speed is None or speed < 1:
            return 0
        return ranged_value_to_percentage(SPEED_RANGE, speed)

    @property
    def preset_mode(self) -> str | None:
        """Return current preset mode."""
        speed = self._current_speed
        return str(speed) if speed in (1, 2, 3) else None

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed percentage of the fan."""
        if percentage == 0:
            # Zehnder ComfoAir Q controlled via ComfoClime minimum running speed is 1
            target_speed = 1
        else:
            target_speed = math.ceil(
                percentage_to_ranged_value(SPEED_RANGE, percentage)
            )
            target_speed = max(1, min(3, target_speed))

        await self.coordinator.api.set_fan_speed(target_speed)
        await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set preset mode."""
        mode_lower = preset_mode.lower()
        if mode_lower not in PRESET_MAP:
            _LOGGER.warning("Unsupported preset mode: %s", preset_mode)
            return
        target_speed = PRESET_MAP[mode_lower]
        await self.coordinator.api.set_fan_speed(target_speed)
        await self.coordinator.async_request_refresh()

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the fan."""
        if percentage is not None:
            await self.async_set_percentage(percentage)
        elif preset_mode is not None:
            await self.async_set_preset_mode(preset_mode)
        else:
            await self.coordinator.api.set_fan_speed(1)
            await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the fan (set to lowest background ventilation speed 1)."""
        # Standalone ventilation units remain at minimum speed for air quality
        await self.coordinator.api.set_fan_speed(1)
        await self.coordinator.async_request_refresh()
