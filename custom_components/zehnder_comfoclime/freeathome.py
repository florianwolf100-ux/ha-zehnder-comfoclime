"""Free@Home SysAP Virtual RTC Bridge for Zehnder ComfoClime."""
from __future__ import annotations

import asyncio
import base64
import json
import logging
from typing import TYPE_CHECKING, Any

import aiohttp
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

if TYPE_CHECKING:
    from .coordinator import ZehnderDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Free@Home Datapoints for RTC Master with Fan (FunctionID 0x000A / A):
IDP_FAN_STAGE = "idp0010"       # pairingID 64: AL_FAN_STAGE_REQUEST ("0"=Auto, "1", "2", "3")
IDP_CONTROLLER_ON = "idp0012"   # pairingID 66: AL_CONTROLLER_ON_OFF_REQUEST ("1"=On, "0"=Off)
IDP_SETPOINT_TEMP = "idp0016"   # pairingID 320: AL_INFO_ABSOLUTE_SET_POINT_REQUEST

ODP_FAN_STAGE_HEAT = "odp0004"  # pairingID 310: AL_ACTUATING_FAN_STAGE_HEATING
ODP_FAN_STAGE_COOL = "odp0005"  # pairingID 327: AL_ACTUATING_FAN_STAGE_COOLING
ODP_SETPOINT_TEMP = "odp0006"   # pairingID 51: AL_SET_POINT_TEMPERATURE
ODP_CONTROLLER_ON = "odp0008"   # pairingID 56: AL_CONTROLLER_ON_OFF
ODP_FAN_LEVEL = "odp000a"       # pairingID 49: AL_FAN_COIL_LEVEL ("0"=Auto/Off, "1", "2", "3")
ODP_FAN_MANUAL = "odp000b"      # pairingID 55: AL_FAN_MANUAL_ON_OFF ("1"=Manual, "0"=Auto)
ODP_MEASURED_TEMP = "odp0010"   # pairingID 304: AL_MEASURED_TEMPERATURE

SYSAP_UUID = "00000000-0000-0000-0000-000000000000"
CHANNEL = "ch0000"


class FreeAtHomeBridge:
    """Bridges Zehnder ComfoClime with a Busch-Jaeger free@home virtual RTC."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: ZehnderDataUpdateCoordinator,
        host: str,
        username: str,
        password: str,
        device_id: str = "600005D4E7DC",
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        """Initialize the free@home bridge."""
        self.hass = hass
        self.coordinator = coordinator
        self.host = host
        self.device_id = device_id
        self.username = username
        self.password = password

        auth = base64.b64encode(f"{username}:{password}".encode()).decode()
        self._headers = {"Authorization": f"Basic {auth}"}
        self._session = session or async_get_clientsession(hass)

        self._ws_task: asyncio.Task | None = None
        self._unsub_coordinator: CALLBACK_TYPE | None = None
        self._running = False

        self._current_fan_level: int = 1
        self._is_fan_manual: bool = True
        self._current_indoor_temp: float = 22.5
        self._current_setpoint: float = 22.5

    async def set_datapoint(self, datapoint: str, value: str) -> bool:
        """Write an output datapoint to free@home SysAP via REST API."""
        url = f"http://{self.host}/fhapi/v1/api/rest/datapoint/{SYSAP_UUID}/{self.device_id}.{CHANNEL}.{datapoint}"
        headers = {**self._headers, "Content-Type": "text/plain"}
        try:
            async with self._session.put(
                url,
                data=str(value),
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status == 200:
                    return True
                _LOGGER.warning(
                    "Free@Home set_datapoint %s=%s failed: HTTP %s",
                    datapoint,
                    value,
                    resp.status,
                )
                return False
        except Exception as err:
            _LOGGER.error("Free@Home set_datapoint %s exception: %s", datapoint, err)
            return False

    async def update_fah_display(
        self,
        indoor_temp: float | None = None,
        setpoint_temp: float | None = None,
        fan_level: int | None = None,
        is_fan_manual: bool = True,
        is_on: bool | None = None,
    ) -> None:
        """Update display values on the free@home virtual RTC tile."""
        if indoor_temp is not None:
            self._current_indoor_temp = indoor_temp
            await self.set_datapoint(ODP_MEASURED_TEMP, f"{indoor_temp:.1f}")

        if setpoint_temp is not None:
            self._current_setpoint = setpoint_temp
            await self.set_datapoint(ODP_SETPOINT_TEMP, f"{setpoint_temp:.1f}")

        if fan_level is not None:
            self._current_fan_level = fan_level
            self._is_fan_manual = is_fan_manual
            fan_val = str(fan_level)
            manual_val = "1" if is_fan_manual else "0"
            await self.set_datapoint(ODP_FAN_LEVEL, fan_val)
            await self.set_datapoint(ODP_FAN_MANUAL, manual_val)
            await self.set_datapoint(ODP_FAN_STAGE_HEAT, fan_val if is_fan_manual else "0")
            await self.set_datapoint(ODP_FAN_STAGE_COOL, fan_val if is_fan_manual else "0")

        if is_on is not None:
            await self.set_datapoint(ODP_CONTROLLER_ON, "1" if is_on else "0")

        _LOGGER.debug(
            "Free@Home RTC updated: Ist=%.1f°C, Soll=%.1f°C, Fan=%s (Manual=%s)",
            self._current_indoor_temp,
            self._current_setpoint,
            self._current_fan_level,
            is_fan_manual,
        )

    def _on_coordinator_update(self) -> None:
        """Handle periodic updates from Zehnder coordinator."""
        if not self.coordinator.data:
            return

        dash = self.coordinator.data.get("dashboard", {})
        indoor = dash.get("indoorTemperature") or dash.get("indoorAirTemperature")
        soll = dash.get("setPointTemperature")
        speed = dash.get("fanSpeed")

        need_update = False
        if indoor is not None and abs(indoor - self._current_indoor_temp) >= 0.1:
            need_update = True
        if soll is not None and abs(soll - self._current_setpoint) >= 0.2:
            need_update = True
        if speed is not None and speed != self._current_fan_level and self._is_fan_manual:
            need_update = True

        if need_update:
            self.hass.async_create_task(
                self.update_fah_display(
                    indoor_temp=indoor,
                    setpoint_temp=soll,
                    fan_level=speed if self._is_fan_manual else 0,
                    is_fan_manual=self._is_fan_manual,
                )
            )

    async def _handle_ws_payload(self, msg: dict[str, Any]) -> None:
        """Handle incoming WebSocket events from free@home SysAP."""
        for sysap_id, body in msg.items():
            if not isinstance(body, dict):
                continue
            datapoints = body.get("datapoints", {})
            for dp_key, val in datapoints.items():
                if self.device_id in dp_key and CHANNEL in dp_key:
                    _LOGGER.info("Free@Home RTC Event: %s = %s", dp_key, val)

                    # 1. Fan Stage request
                    if IDP_FAN_STAGE in dp_key:
                        try:
                            stage = int(val)
                            _LOGGER.info("User selected Fan Stage %d in free@home", stage)
                            if stage in (1, 2, 3):
                                self._current_fan_level = stage
                                self._is_fan_manual = True
                                await self.coordinator.api.set_fan_speed(stage)
                                # Acknowledge back immediately so button remains highlighted
                                await self.set_datapoint(ODP_FAN_LEVEL, str(stage))
                                await self.set_datapoint(ODP_FAN_MANUAL, "1")
                                await self.set_datapoint(ODP_FAN_STAGE_HEAT, str(stage))
                                await self.set_datapoint(ODP_FAN_STAGE_COOL, str(stage))
                            elif stage == 0:
                                self._current_fan_level = 0
                                self._is_fan_manual = False
                                await self.coordinator.api.set_fan_speed(1)  # Grundlüftung
                                await self.set_datapoint(ODP_FAN_LEVEL, "0")
                                await self.set_datapoint(ODP_FAN_MANUAL, "0")
                                await self.set_datapoint(ODP_FAN_STAGE_HEAT, "0")
                                await self.set_datapoint(ODP_FAN_STAGE_COOL, "0")

                            await self.coordinator.async_request_refresh()
                        except (ValueError, TypeError):
                            pass

                    # 2. Target Temperature request
                    elif IDP_SETPOINT_TEMP in dp_key:
                        try:
                            target = float(val)
                            _LOGGER.info("User changed Target Temp to %.1f°C in free@home", target)
                            self._current_setpoint = target
                            await self.coordinator.api.set_target_temperature(target)
                            await self.set_datapoint(ODP_SETPOINT_TEMP, f"{target:.1f}")
                            await self.coordinator.async_request_refresh()
                        except (ValueError, TypeError):
                            pass

                    # 3. Controller On/Off request
                    elif IDP_CONTROLLER_ON in dp_key:
                        is_on = val == "1"
                        _LOGGER.info("User toggled RTC On/Off in free@home: %s", is_on)
                        await self.set_datapoint(ODP_CONTROLLER_ON, "1" if is_on else "0")

    async def _listen_ws(self) -> None:
        """Maintain WebSocket connection to SysAP."""
        ws_url = f"ws://{self.host}/fhapi/v1/api/ws"
        while self._running:
            try:
                _LOGGER.info("Connecting to free@home WebSocket at %s", ws_url)
                async with self._session.ws_connect(
                    ws_url,
                    headers=self._headers,
                    heartbeat=30,
                ) as ws:
                    _LOGGER.info("Free@Home WebSocket connected successfully")
                    async for msg in ws:
                        if not self._running:
                            break
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            try:
                                payload = json.loads(msg.data)
                                await self._handle_ws_payload(payload)
                            except Exception as err:
                                _LOGGER.error("Error handling free@home WS message: %s", err)
                        elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                            _LOGGER.warning("Free@Home WebSocket connection closed")
                            break
            except asyncio.CancelledError:
                break
            except Exception as err:
                _LOGGER.warning(
                    "Free@Home WebSocket exception: %s. Reconnecting in 5s...", err
                )
                await asyncio.sleep(5)

    async def async_start(self) -> None:
        """Start the free@home bridge."""
        self._running = True

        # Initial display sync from coordinator data
        if self.coordinator.data:
            dash = self.coordinator.data.get("dashboard", {})
            indoor = dash.get("indoorTemperature") or dash.get("indoorAirTemperature") or 22.5
            soll = dash.get("setPointTemperature", 22.5)
            speed = dash.get("fanSpeed", 1)
            await self.update_fah_display(
                indoor_temp=indoor,
                setpoint_temp=soll,
                fan_level=speed,
                is_fan_manual=True,
                is_on=True,
            )

        self._unsub_coordinator = self.coordinator.async_add_listener(
            self._on_coordinator_update
        )
        self._ws_task = self.hass.async_create_background_task(
            self._listen_ws(),
            name="zehnder_freeathome_ws",
        )
        _LOGGER.info("Free@Home Zehnder Bridge started for RTC %s", self.device_id)

    async def async_stop(self) -> None:
        """Stop the free@home bridge."""
        self._running = False
        if self._unsub_coordinator:
            self._unsub_coordinator()
            self._unsub_coordinator = None

        if self._ws_task:
            self._ws_task.cancel()
            try:
                await self._ws_task
            except asyncio.CancelledError:
                pass
            self._ws_task = None

        _LOGGER.info("Free@Home Zehnder Bridge stopped")
