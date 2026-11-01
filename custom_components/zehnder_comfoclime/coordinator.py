"""DataUpdateCoordinator for Zehnder ComfoClime."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ZehnderApiClient, ZehnderError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class ZehnderDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to fetch Zehnder ComfoClime and ComfoAir Q data."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: ZehnderApiClient,
        update_interval: int,
    ) -> None:
        """Initialize coordinator."""
        self.api = api
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API."""
        try:
            return await self.api.get_summary()
        except ZehnderError as err:
            raise UpdateFailed(f"Error communicating with Zehnder gateway: {err}") from err
