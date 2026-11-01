"""Tests for Free@Home SysAP Virtual RTC Bridge."""
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from custom_components.zehnder_comfoclime.freeathome import (
    FreeAtHomeBridge,
    IDP_FAN_STAGE,
    IDP_SETPOINT_TEMP,
    ODP_FAN_LEVEL,
    ODP_FAN_MANUAL,
    ODP_MEASURED_TEMP,
    ODP_SETPOINT_TEMP,
)


@pytest.fixture
def mock_coordinator():
    """Mock Zehnder coordinator."""
    coord = MagicMock()
    coord.data = {
        "dashboard": {
            "indoorTemperature": 23.2,
            "setPointTemperature": 22.0,
            "fanSpeed": 2,
        }
    }
    coord.api = MagicMock()
    coord.api.set_fan_speed = AsyncMock()
    coord.api.set_target_temperature = AsyncMock()
    coord.async_request_refresh = AsyncMock()
    coord.async_add_listener = MagicMock(return_value=MagicMock())
    return coord


@pytest.fixture
def mock_hass():
    """Mock Home Assistant instance."""
    hass = MagicMock()
    hass.async_create_background_task = MagicMock(return_value=MagicMock())
    hass.async_create_task = MagicMock(return_value=MagicMock())
    return hass


@pytest.fixture
def mock_session():
    """Mock aiohttp ClientSession."""
    session = MagicMock()
    mock_resp = AsyncMock()
    mock_resp.status = 200
    session.put = MagicMock()
    session.put.return_value.__aenter__ = AsyncMock(return_value=mock_resp)
    session.put.return_value.__aexit__ = AsyncMock(return_value=None)
    return session


@pytest.mark.asyncio
async def test_bridge_init_and_set_datapoint(mock_hass, mock_coordinator, mock_session):
    """Test bridge initialization and REST set_datapoint."""
    bridge = FreeAtHomeBridge(
        hass=mock_hass,
        coordinator=mock_coordinator,
        host="192.168.178.36",
        username="installer",
        password="secretpassword",
        device_id="600005D4E7DC",
        session=mock_session,
    )

    success = await bridge.set_datapoint(ODP_FAN_LEVEL, "2")
    assert success is True
    assert mock_session.put.called


@pytest.mark.asyncio
async def test_bridge_update_display(mock_hass, mock_coordinator, mock_session):
    """Test updating RTC display values."""
    bridge = FreeAtHomeBridge(
        hass=mock_hass,
        coordinator=mock_coordinator,
        host="192.168.178.36",
        username="installer",
        password="secretpassword",
        session=mock_session,
    )
    bridge.set_datapoint = AsyncMock(return_value=True)

    await bridge.update_fah_display(
        indoor_temp=23.5,
        setpoint_temp=22.0,
        fan_level=2,
        is_fan_manual=True,
        is_on=True,
    )

    calls = [c.args for c in bridge.set_datapoint.call_args_list]
    assert (ODP_MEASURED_TEMP, "23.5") in calls
    assert (ODP_SETPOINT_TEMP, "22.0") in calls
    assert (ODP_FAN_LEVEL, "2") in calls
    assert (ODP_FAN_MANUAL, "1") in calls


@pytest.mark.asyncio
async def test_bridge_handle_ws_fan_stage_manual(mock_hass, mock_coordinator, mock_session):
    """Test handling user clicking Fan Stage 3 in free@home."""
    bridge = FreeAtHomeBridge(
        hass=mock_hass,
        coordinator=mock_coordinator,
        host="192.168.178.36",
        username="installer",
        password="secretpassword",
        session=mock_session,
    )
    bridge.set_datapoint = AsyncMock(return_value=True)

    msg = {
        "00000000-0000-0000-0000-000000000000": {
            "datapoints": {
                f"{bridge.device_id}/ch0000/{IDP_FAN_STAGE}": "3"
            }
        }
    }

    await bridge._handle_ws_payload(msg)

    # Zehnder fan speed should be called with 3
    mock_coordinator.api.set_fan_speed.assert_awaited_once_with(3)
    # Datapoints should be acknowledged back
    calls = [c.args for c in bridge.set_datapoint.call_args_list]
    assert (ODP_FAN_LEVEL, "3") in calls
    assert (ODP_FAN_MANUAL, "1") in calls
    assert mock_coordinator.async_request_refresh.called


@pytest.mark.asyncio
async def test_bridge_handle_ws_fan_stage_auto(mock_hass, mock_coordinator, mock_session):
    """Test handling user clicking Auto (Stage 0) in free@home."""
    bridge = FreeAtHomeBridge(
        hass=mock_hass,
        coordinator=mock_coordinator,
        host="192.168.178.36",
        username="installer",
        password="secretpassword",
        session=mock_session,
    )
    bridge.set_datapoint = AsyncMock(return_value=True)

    msg = {
        "00000000-0000-0000-0000-000000000000": {
            "datapoints": {
                f"{bridge.device_id}/ch0000/{IDP_FAN_STAGE}": "0"
            }
        }
    }

    await bridge._handle_ws_payload(msg)

    # Fan speed set to baseline (1)
    mock_coordinator.api.set_fan_speed.assert_awaited_once_with(1)
    calls = [c.args for c in bridge.set_datapoint.call_args_list]
    assert (ODP_FAN_LEVEL, "0") in calls
    assert (ODP_FAN_MANUAL, "0") in calls


@pytest.mark.asyncio
async def test_bridge_handle_ws_target_temp(mock_hass, mock_coordinator, mock_session):
    """Test handling user changing setpoint temp in free@home."""
    bridge = FreeAtHomeBridge(
        hass=mock_hass,
        coordinator=mock_coordinator,
        host="192.168.178.36",
        username="installer",
        password="secretpassword",
        session=mock_session,
    )
    bridge.set_datapoint = AsyncMock(return_value=True)

    msg = {
        "00000000-0000-0000-0000-000000000000": {
            "datapoints": {
                f"{bridge.device_id}/ch0000/{IDP_SETPOINT_TEMP}": "21.50"
            }
        }
    }

    await bridge._handle_ws_payload(msg)

    mock_coordinator.api.set_target_temperature.assert_awaited_once_with(21.5)
    calls = [c.args for c in bridge.set_datapoint.call_args_list]
    assert (ODP_SETPOINT_TEMP, "21.5") in calls
