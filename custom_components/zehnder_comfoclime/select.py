"""Select platform for Zehnder ComfoClime."""
from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
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
    SEASON_NAMES,
    SEASON_TRANSITION,
)
from .coordinator import ZehnderDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

SEASONS = ["transition", "heating", "cooling"]
SEASON_MAP = {
    "transition": SEASON_TRANSITION,
    "heating": SEASON_HEATING,
    "cooling": SEASON_COOLING,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Zehnder select entities."""
    coordinator: ZehnderDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SelectEntity] = [
        ZehnderProfileSelect(coordinator, entry),
        ZehnderSeasonSelect(coordinator, entry),
    ]
    async_add_entities(entities)


class ZehnderProfileSelect(
    CoordinatorEntity[ZehnderDataUpdateCoordinator], SelectEntity
):
    """Select entity for temperature profile (comfort, power, eco)."""

    _attr_has_entity_name = True
    _attr_translation_key = "temperature_profile"
    _attr_options = [PRESET_COMFORT, PRESET_POWER, PRESET_ECO]

    def __init__(
        self, coordinator: ZehnderDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the profile select."""
        super().__init__(coordinator)
        self._clime_uuid = (
            coordinator.api.clime_uuid or entry.data.get("clime_uuid") or "clime"
        )
        self._attr_unique_id = f"{self._clime_uuid}_temperature_profile"

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
    def current_option(self) -> str | None:
        """Return current profile option."""
        dashboard = self.coordinator.data.get("dashboard", {})
        profile_id = dashboard.get("temperatureProfile", 0)
        return PROFILE_ID_TO_PRESET.get(profile_id, PRESET_COMFORT)

    async def async_select_option(self, option: str) -> None:
        """Change the selected profile."""
        if option not in PRESET_TO_PROFILE_ID:
            _LOGGER.warning("Invalid profile selected: %s", option)
            return
        await self.coordinator.api.set_preset_profile(option)
        await self.coordinator.async_request_refresh()


class ZehnderSeasonSelect(
    CoordinatorEntity[ZehnderDataUpdateCoordinator], SelectEntity
):
    """Select entity for seasonal operating mode."""

    _attr_has_entity_name = True
    _attr_translation_key = "season_mode"
    _attr_options = SEASONS

    def __init__(
        self, coordinator: ZehnderDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the season select."""
        super().__init__(coordinator)
        self._clime_uuid = (
            coordinator.api.clime_uuid or entry.data.get("clime_uuid") or "clime"
        )
        self._attr_unique_id = f"{self._clime_uuid}_season_mode"

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
    def current_option(self) -> str | None:
        """Return current season option."""
        dashboard = self.coordinator.data.get("dashboard", {})
        season_id = dashboard.get("season", SEASON_TRANSITION)
        return SEASON_NAMES.get(season_id, "transition")

    async def async_select_option(self, option: str) -> None:
        """Change the selected season."""
        if option not in SEASON_MAP:
            _LOGGER.warning("Invalid season selected: %s", option)
            return
        season_val = SEASON_MAP[option]
        await self.coordinator.api.set_season(season_val)
        await self.coordinator.async_request_refresh()
