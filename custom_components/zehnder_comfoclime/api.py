"""Async REST API client for Zehnder ComfoClime & ComfoAir Q."""
from __future__ import annotations

import asyncio
from datetime import datetime
import logging
from typing import Any, Optional

import aiohttp

from .const import (
    MODEL_TYPE_COMFOCLIME,
    MODEL_TYPE_Q350,
    PRESET_TO_PROFILE_ID,
    SEASON_COOLING,
    SEASON_HEATING,
    SEASON_TRANSITION,
    TEL_CLIME_COMPRESSOR_TEMP,
    TEL_CLIME_EXHAUST_COIL_TEMP,
    TEL_CLIME_EXHAUST_TEMP_HP,
    TEL_CLIME_MODULATION,
    TEL_CLIME_POWER_WATTS,
    TEL_CLIME_SUPPLY_COIL_TEMP,
    TEL_CLIME_SUPPLY_TEMP_HP,
    TEL_CLIME_TPMA_TEMP,
    TEL_Q350_BYPASS_STATE,
    TEL_Q350_RMOT_TEMP,
    TEL_Q350_SUPPLY_TEMP_WRG,
    TEL_Q350_TARGET_COMFORT_TEMP,
)

_LOGGER = logging.getLogger(__name__)


class ZehnderError(Exception):
    """Base exception for Zehnder API errors."""


class ZehnderConnectionError(ZehnderError):
    """Raised when connection to Zehnder gateway fails."""


class ZehnderApiError(ZehnderError):
    """Raised when the Zehnder gateway returns an error response."""


def decode_telemetry_bytes(
    data: list[int], factor: float = 1.0, signed: bool = True
) -> Optional[float]:
    """Decode Little-Endian signed or unsigned byte array from Zehnder PDO telemetry."""
    if not data:
        return None

    if len(data) == 1:
        val = data[0]
        if signed and val >= 128:
            val -= 256
        return round(val * factor, 2)
    elif len(data) >= 2:
        val = data[0] | (data[1] << 8)
        if signed and val >= 32768:
            val -= 65536
        return round(val * factor, 2)
    return None


class ZehnderApiClient:
    """Asynchronous client for Zehnder ComfoClime REST API."""

    def __init__(
        self,
        host: str,
        session: Optional[aiohttp.ClientSession] = None,
        timeout: float = 5.0,
    ) -> None:
        """Initialize the client."""
        self.host = host
        self.base_url = f"http://{host}"
        self._session = session
        self._close_session = False
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._req_lock = asyncio.Lock()

        # Discovered UUIDs & metadata
        self.clime_uuid: Optional[str] = None
        self.q350_uuid: Optional[str] = None
        self.clime_name: str = "ComfoClime 24"
        self.q350_name: str = "ComfoAir Q350"
        self.clime_version: Optional[str] = None

        # Telemetry cache to retain values across temporary communication drops
        self._telemetry_cache: dict[str, dict[int, Any]] = {}

    async def _get_session(self) -> aiohttp.ClientSession:
        """Return an active aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self._timeout)
            self._close_session = True
        return self._session

    async def close(self) -> None:
        """Close the underlying session if created by this client."""
        if self._close_session and self._session and not self._session.closed:
            await self._session.close()

    async def _request(
        self,
        path: str,
        method: str = "GET",
        data: Optional[dict[str, Any]] = None,
        timeout_override: Optional[float] = None,
    ) -> Any:
        """Execute HTTP request with concurrency control and error handling."""
        session = await self._get_session()
        url = f"{self.base_url}{path}"
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "HomeAssistant-ZehnderComfoClime/1.0",
        }
        timeout = (
            aiohttp.ClientTimeout(total=timeout_override)
            if timeout_override
            else self._timeout
        )

        async with self._req_lock:
            try:
                async with session.request(
                    method=method,
                    url=url,
                    json=data,
                    headers=headers,
                    timeout=timeout,
                ) as resp:
                    if resp.status >= 400:
                        text = await resp.text()
                        raise ZehnderApiError(
                            f"HTTP {resp.status} for {path}: {text}"
                        )
                    if resp.status == 204:
                        return {}
                    content_type = resp.headers.get("Content-Type", "")
                    if "application/json" in content_type:
                        return await resp.json()
                    text = await resp.text()
                    return {"raw": text} if text else {}
            except (aiohttp.ClientError, asyncio.TimeoutError) as err:
                raise ZehnderConnectionError(
                    f"Communication error with Zehnder at {url}: {err}"
                ) from err

    async def ping(self) -> dict[str, Any]:
        """Verify reachability and retrieve ComfoClime UUID."""
        res = await self._request("/monitoring/ping")
        uuid = res.get("uuid")
        if uuid:
            self.clime_uuid = uuid
        return res

    async def discover_devices(self) -> list[dict[str, Any]]:
        """Discover all devices connected to the ComfoNet bus."""
        if not self.clime_uuid:
            await self.ping()
        if not self.clime_uuid:
            raise ZehnderApiError("ComfoClime UUID could not be determined")

        res = await self._request(f"/system/{self.clime_uuid}/devices")
        devices = res.get("devices", [])
        for dev in devices:
            model_id = dev.get("modelTypeId")
            uuid = dev.get("uuid")
            name = dev.get("displayName") or dev.get("name")
            if model_id == MODEL_TYPE_COMFOCLIME:
                self.clime_uuid = uuid
                if name:
                    self.clime_name = name
                self.clime_version = dev.get("version")
            elif model_id == MODEL_TYPE_Q350:
                self.q350_uuid = uuid
                if name:
                    self.q350_name = name
        return devices

    async def get_dashboard(self) -> dict[str, Any]:
        """Fetch current dashboard summary."""
        if not self.clime_uuid:
            await self.ping()
        return await self._request(f"/system/{self.clime_uuid}/dashboard")

    async def get_thermal_profile(self) -> dict[str, Any]:
        """Fetch thermal profile curves and boundaries."""
        if not self.clime_uuid:
            await self.ping()
        return await self._request(f"/system/{self.clime_uuid}/thermalprofile")

    async def read_telemetry(
        self,
        device_uuid: str,
        telemetry_id: int,
        factor: float = 1.0,
        signed: bool = True,
    ) -> Optional[float]:
        """Read and decode a single PDO telemetry metric."""
        try:
            res = await self._request(
                f"/device/{device_uuid}/telemetry/{telemetry_id}",
                timeout_override=2.5,
            )
            raw_data = res.get("data", [])
            val = decode_telemetry_bytes(raw_data, factor=factor, signed=signed)
            if val is not None:
                if device_uuid not in self._telemetry_cache:
                    self._telemetry_cache[device_uuid] = {}
                self._telemetry_cache[device_uuid][telemetry_id] = val
            return val
        except Exception as err:
            _LOGGER.debug(
                "Telemetry %s for device %s failed (%s), using cache if available",
                telemetry_id,
                device_uuid,
                err,
            )
            return self._telemetry_cache.get(device_uuid, {}).get(telemetry_id)

    async def get_summary(self) -> dict[str, Any]:
        """Fetch full aggregated status for coordinator update."""
        if not self.clime_uuid:
            await self.discover_devices()

        dashboard = await self.get_dashboard()

        # Telemetry queries (executed sequentially via _request lock to avoid ESP socket congestion)
        q350_telemetry: dict[str, Any] = {}
        if self.q350_uuid:
            q350_telemetry = {
                "outdoor_temp": dashboard.get("outdoorTemperature"),
                "supply_airflow": dashboard.get("supplyAirFlow"),
                "exhaust_airflow": dashboard.get("exhaustAirFlow"),
                "supply_temp_wrg": await self.read_telemetry(
                    self.q350_uuid, TEL_Q350_SUPPLY_TEMP_WRG, factor=0.1
                ),
                "rmot_temp": await self.read_telemetry(
                    self.q350_uuid, TEL_Q350_RMOT_TEMP, factor=0.1
                ),
                "target_comfort_temp": await self.read_telemetry(
                    self.q350_uuid, TEL_Q350_TARGET_COMFORT_TEMP, factor=0.1
                ),
                "bypass_state_pct": await self.read_telemetry(
                    self.q350_uuid, TEL_Q350_BYPASS_STATE, factor=1.0, signed=False
                ),
            }

        clime_telemetry: dict[str, Any] = {}
        if self.clime_uuid:
            clime_telemetry = {
                "indoor_temp": dashboard.get("indoorTemperature"),
                "setpoint_temp": dashboard.get("setPointTemperature"),
                "supply_temp_after_hp": await self.read_telemetry(
                    self.clime_uuid, TEL_CLIME_SUPPLY_TEMP_HP, factor=0.1
                ),
                "exhaust_temp_after_hp": await self.read_telemetry(
                    self.clime_uuid, TEL_CLIME_EXHAUST_TEMP_HP, factor=0.1
                ),
                "supply_coil_temp": await self.read_telemetry(
                    self.clime_uuid, TEL_CLIME_SUPPLY_COIL_TEMP, factor=0.1
                ),
                "exhaust_coil_temp": await self.read_telemetry(
                    self.clime_uuid, TEL_CLIME_EXHAUST_COIL_TEMP, factor=0.1
                ),
                "compressor_temp": await self.read_telemetry(
                    self.clime_uuid, TEL_CLIME_COMPRESSOR_TEMP, factor=0.1
                ),
                "heatpump_modulation_pct": await self.read_telemetry(
                    self.clime_uuid, TEL_CLIME_MODULATION, factor=1.0, signed=False
                ),
                "power_watts": await self.read_telemetry(
                    self.clime_uuid, TEL_CLIME_POWER_WATTS, factor=1.0, signed=False
                ),
                "tpma_temp": await self.read_telemetry(
                    self.clime_uuid, TEL_CLIME_TPMA_TEMP, factor=0.1
                ),
            }

        return {
            "dashboard": dashboard,
            "q350": q350_telemetry,
            "clime": clime_telemetry,
        }

    # --- Write operations ---

    async def set_fan_speed(self, speed: int) -> bool:
        """Set fan speed (1, 2, or 3)."""
        if speed not in (1, 2, 3):
            raise ValueError(f"Fan speed must be 1, 2, or 3, got: {speed}")
        payload = {
            "fanSpeed": speed,
            "timestamp": datetime.now().isoformat(),
        }
        await self._request(
            f"/system/{self.clime_uuid}/dashboard", method="PUT", data=payload
        )
        return True

    async def set_target_temperature(self, temp: float) -> bool:
        """Set manual target temperature. Must include status: 0 to lock in manual mode."""
        payload = {
            "setPointTemperature": round(temp, 1),
            "status": 0,
            "timestamp": datetime.now().isoformat(),
        }
        await self._request(
            f"/system/{self.clime_uuid}/dashboard", method="PUT", data=payload
        )
        return True

    async def set_preset_profile(self, profile: str) -> bool:
        """Activate automatic temperature profile (status: 1)."""
        profile_lower = profile.lower()
        if profile_lower not in PRESET_TO_PROFILE_ID:
            raise ValueError(
                f"Unknown preset profile: {profile}. Allowed: {list(PRESET_TO_PROFILE_ID.keys())}"
            )
        payload = {
            "temperatureProfile": PRESET_TO_PROFILE_ID[profile_lower],
            "status": 1,
            "timestamp": datetime.now().isoformat(),
        }
        await self._request(
            f"/system/{self.clime_uuid}/dashboard", method="PUT", data=payload
        )
        return True

    async def set_hvac_mode(self, mode: str) -> bool:
        """Set HVAC operating mode."""
        mode_lower = mode.lower()
        if mode_lower == "off":
            payload = {"hpStandby": True}
        elif mode_lower == "heat":
            payload = {"season": SEASON_HEATING, "hpStandby": False}
        elif mode_lower == "cool":
            payload = {"season": SEASON_COOLING, "hpStandby": False}
        elif mode_lower in ("fan_only", "transition"):
            payload = {"season": SEASON_TRANSITION, "hpStandby": False}
        else:
            raise ValueError(
                f"Invalid HVAC mode: {mode}. Allowed: off, heat, cool, fan_only"
            )

        payload["timestamp"] = datetime.now().isoformat()
        await self._request(
            f"/system/{self.clime_uuid}/dashboard", method="PUT", data=payload
        )
        return True

    async def set_hp_standby(self, standby: bool) -> bool:
        """Set heat pump standby mode."""
        payload = {
            "hpStandby": bool(standby),
            "timestamp": datetime.now().isoformat(),
        }
        await self._request(
            f"/system/{self.clime_uuid}/dashboard", method="PUT", data=payload
        )
        return True

    async def set_status(self, status: int) -> bool:
        """Set status: 0 for manual setpoint, 1 for automatic profile."""
        if status not in (0, 1):
            raise ValueError(f"Status must be 0 (manual) or 1 (auto), got {status}")
        payload = {
            "status": status,
            "timestamp": datetime.now().isoformat(),
        }
        await self._request(
            f"/system/{self.clime_uuid}/dashboard", method="PUT", data=payload
        )
        return True

    async def set_season(self, season: int) -> bool:
        """Set season: 0 for transition, 1 for heating, 2 for cooling."""
        if season not in (SEASON_TRANSITION, SEASON_HEATING, SEASON_COOLING):
            raise ValueError(f"Season must be 0, 1, or 2, got {season}")
        payload = {
            "season": season,
            "hpStandby": False,
            "timestamp": datetime.now().isoformat(),
        }
        await self._request(
            f"/system/{self.clime_uuid}/dashboard", method="PUT", data=payload
        )
        return True
