"""Climate platform for Zehnder ComfoClime."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import (
    ATTR_HVAC_MODE,
    PRESET_NONE,
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    PRESET_COMFORT,
    PRESET_ECO,
    PRESET_POWER,
    PRESET_TO_PROFILE_ID,
    PROFILE_ID_TO_PRESET,
    SEASON_COOLING,
    SEASON_HEATING,
    SEASON_TRANSITION,
    STATUS_AUTO,
    STATUS_MANUAL,
)
from .coordinator import ZehnderDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Zehnder climate entity."""
    coordinator: ZehnderDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ZehnderClimate(coordinator, entry)])


class ZehnderClimate(CoordinatorEntity[ZehnderDataUpdateCoordinator], ClimateEntity):
    """Climate entity representing the Zehnder ComfoClime 24 heat pump."""

    _attr_has_entity_name = True
    _attr_name = None  # Primary entity for the device
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_min_temp = 15.0
    _attr_max_temp = 30.0
    _attr_target_temperature_step = 0.5
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.PRESET_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_hvac_modes = [
        HVACMode.OFF,
        HVACMode.HEAT,
        HVACMode.COOL,
        HVACMode.FAN_ONLY,
    ]
    _attr_preset_modes = [
        PRESET_NONE,
        PRESET_COMFORT,
        PRESET_POWER,
        PRESET_ECO,
    ]

    def __init__(
        self, coordinator: ZehnderDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the climate entity."""
        super().__init__(coordinator)
        self._clime_uuid = (
            coordinator.api.clime_uuid or entry.data.get("clime_uuid") or "clime"
        )
        self._attr_unique_id = f"{self._clime_uuid}_climate"

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
    def current_temperature(self) -> float | None:
        """Return the current indoor temperature."""
        clime = self.coordinator.data.get("clime", {})
        temp = clime.get("indoor_temp")
        if temp is not None:
            return float(temp)
        dashboard = self.coordinator.data.get("dashboard", {})
        return dashboard.get("indoorTemperature")

    @property
    def target_temperature(self) -> float | None:
        """Return the target setpoint temperature."""
        dashboard = self.coordinator.data.get("dashboard", {})
        temp = dashboard.get("setPointTemperature")
        return float(temp) if temp is not None else None

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current HVAC mode."""
        dashboard = self.coordinator.data.get("dashboard", {})
        if dashboard.get("hpStandby", False):
            return HVACMode.OFF

        season = dashboard.get("season", SEASON_TRANSITION)
        if season == SEASON_HEATING:
            return HVACMode.HEAT
        if season == SEASON_COOLING:
            return HVACMode.COOL
        return HVACMode.FAN_ONLY

    @property
    def hvac_action(self) -> HVACAction:
        """Return current running action."""
        dashboard = self.coordinator.data.get("dashboard", {})
        if dashboard.get("hpStandby", False):
            return HVACAction.OFF

        season = dashboard.get("season", SEASON_TRANSITION)
        clime = self.coordinator.data.get("clime", {})
        power = clime.get("power_watts") or 0.0
        modulation = clime.get("heatpump_modulation_pct") or 0.0

        is_compressor_active = power > 15.0 or modulation > 0.0

        if season == SEASON_HEATING:
            return HVACAction.HEATING if is_compressor_active else HVACAction.IDLE
        if season == SEASON_COOLING:
            return HVACAction.COOLING if is_compressor_active else HVACAction.IDLE
        return HVACAction.FAN

    @property
    def preset_mode(self) -> str | None:
        """Return current preset mode."""
        dashboard = self.coordinator.data.get("dashboard", {})
        if dashboard.get("status") == STATUS_AUTO:
            profile_id = dashboard.get("temperatureProfile", 0)
            return PROFILE_ID_TO_PRESET.get(profile_id, PRESET_COMFORT)
        return PRESET_NONE

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature (sets status: 0 manual mode)."""
        if hvac_mode := kwargs.get(ATTR_HVAC_MODE):
            await self.async_set_hvac_mode(hvac_mode)

        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is None:
            return
        await self.coordinator.api.set_target_temperature(float(temp))
        await self.coordinator.async_request_refresh()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target HVAC mode."""
        if hvac_mode == HVACMode.OFF:
            await self.coordinator.api.set_hvac_mode("off")
        elif hvac_mode == HVACMode.HEAT:
            await self.coordinator.api.set_hvac_mode("heat")
        elif hvac_mode == HVACMode.COOL:
            await self.coordinator.api.set_hvac_mode("cool")
        elif hvac_mode == HVACMode.FAN_ONLY:
            await self.coordinator.api.set_hvac_mode("fan_only")
        else:
            _LOGGER.warning("Unsupported HVAC mode requested: %s", hvac_mode)
            return
        await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        if preset_mode in (PRESET_NONE, "none", "manual"):
            await self.coordinator.api.set_status(STATUS_MANUAL)
            await self.coordinator.async_request_refresh()
            return
        if preset_mode not in PRESET_TO_PROFILE_ID:
            _LOGGER.warning("Unsupported preset mode requested: %s", preset_mode)
            return
        await self.coordinator.api.set_preset_profile(preset_mode)
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self) -> None:
        """Turn on the heat pump (disable standby)."""
        await self.coordinator.api.set_hp_standby(False)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self) -> None:
        """Turn off the heat pump (enable standby)."""
        await self.coordinator.api.set_hp_standby(True)
        await self.coordinator.async_request_refresh()
