"""Unit tests for the Zehnder API client and decoding."""
from __future__ import annotations

import asyncio
import pytest
from unittest.mock import ANY, AsyncMock, MagicMock
import aiohttp

from custom_components.zehnder_comfoclime.api import (
    ZehnderApiClient,
    ZehnderConnectionError,
    ZehnderApiError,
    decode_telemetry_bytes,
)
from custom_components.zehnder_comfoclime.const import (
    MODEL_TYPE_COMFOCLIME,
    MODEL_TYPE_Q350,
    SEASON_COOLING,
    SEASON_HEATING,
    SEASON_TRANSITION,
    STATUS_AUTO,
    STATUS_MANUAL,
)


def test_decode_telemetry_bytes():
    """Test byte decoding for various telemetry data types."""
    # Empty
    assert decode_telemetry_bytes([]) is None
    assert decode_telemetry_bytes(None) is None

    # 1 byte signed positive
    assert decode_telemetry_bytes([38], factor=0.1, signed=True) == 3.8
    # 1 byte signed negative
    # 250 in 8-bit signed is -6 -> -6 * 0.1 = -0.6
    assert decode_telemetry_bytes([250], factor=0.1, signed=True) == -0.6

    # 1 byte unsigned
    assert decode_telemetry_bytes([0], factor=1.0, signed=False) == 0.0
    assert decode_telemetry_bytes([100], factor=1.0, signed=False) == 100.0

    # 2 bytes signed positive
    # 225 = 22.5 °C
    assert decode_telemetry_bytes([225, 0], factor=0.1, signed=True) == 22.5

    # 2 bytes signed negative
    # -105 (for -10.5 °C): 65536 - 105 = 65431 = 0xFF97 -> [151, 255]
    assert decode_telemetry_bytes([151, 255], factor=0.1, signed=True) == -10.5

    # 2 bytes unsigned (Airflow: 160 m³/h, Power: 250 W)
    assert decode_telemetry_bytes([160, 0], factor=1.0, signed=False) == 160.0
    assert decode_telemetry_bytes([250, 0], factor=1.0, signed=False) == 250.0


@pytest.mark.asyncio
async def test_api_ping():
    """Test ping method."""
    client = ZehnderApiClient(host="1.2.3.4")
    client._request = AsyncMock(return_value={"uuid": "MBE123", "up_time_seconds": 100})

    res = await client.ping()
    assert res["uuid"] == "MBE123"
    assert client.clime_uuid == "MBE123"


@pytest.mark.asyncio
async def test_api_discover_devices():
    """Test discover_devices."""
    client = ZehnderApiClient(host="1.2.3.4")
    client.clime_uuid = "MBE123"

    mock_devices = {
        "devices": [
            {
                "uuid": "SIT999",
                "modelTypeId": MODEL_TYPE_Q350,
                "displayName": "ComfoAirQ 350",
            },
            {
                "uuid": "MBE123",
                "modelTypeId": MODEL_TYPE_COMFOCLIME,
                "displayName": "ComfoClime 24",
                "version": "R1.5.5",
            },
        ]
    }
    client._request = AsyncMock(return_value=mock_devices)

    devices = await client.discover_devices()
    assert len(devices) == 2
    assert client.q350_uuid == "SIT999"
    assert client.clime_uuid == "MBE123"
    assert client.clime_version == "R1.5.5"


@pytest.mark.asyncio
async def test_write_operations():
    """Test write methods (fan, target temp, preset, mode, standby)."""
    client = ZehnderApiClient(host="1.2.3.4")
    client.clime_uuid = "MBE123"
    client._request = AsyncMock(return_value={})

    # Fan speed
    await client.set_fan_speed(2)
    client._request.assert_called_with(
        "/system/MBE123/dashboard",
        method="PUT",
        data={"fanSpeed": 2, "timestamp": ANY},
    )

    with pytest.raises(ValueError):
        await client.set_fan_speed(4)

    # Target temperature (must send status: 0)
    await client.set_target_temperature(21.5)
    call_args = client._request.call_args[1]
    assert call_args["data"]["setPointTemperature"] == 21.5
    assert call_args["data"]["status"] == 0

    # Preset profile (must send status: 1)
    await client.set_preset_profile("power")
    call_args = client._request.call_args[1]
    assert call_args["data"]["temperatureProfile"] == 1
    assert call_args["data"]["status"] == 1

    # HVAC Mode
    await client.set_hvac_mode("heat")
    call_args = client._request.call_args[1]
    assert call_args["data"]["season"] == SEASON_HEATING
    assert call_args["data"]["hpStandby"] is False

    await client.set_hvac_mode("off")
    call_args = client._request.call_args[1]
    assert call_args["data"]["hpStandby"] is True

    # Standby
    await client.set_hp_standby(True)
    call_args = client._request.call_args[1]
    assert call_args["data"]["hpStandby"] is True

    # Status
    await client.set_status(1)
    call_args = client._request.call_args[1]
    assert call_args["data"]["status"] == 1

    # Season
    await client.set_season(2)
    call_args = client._request.call_args[1]
    assert call_args["data"]["season"] == 2
    assert call_args["data"]["hpStandby"] is False


@pytest.mark.asyncio
async def test_telemetry_cache_fallback():
    """Test telemetry caching when an endpoint temporarily fails."""
    client = ZehnderApiClient(host="1.2.3.4")
    client.clime_uuid = "MBE123"

    # 1. Successful fetch populates cache
    client._request = AsyncMock(return_value={"data": [223, 0]})
    val = await client.read_telemetry("MBE123", 4193, factor=0.1)
    assert val == 22.3

    # 2. Subsequent failure returns cached value instead of crashing
    client._request = AsyncMock(side_effect=ZehnderConnectionError("Timeout"))
    fallback_val = await client.read_telemetry("MBE123", 4193, factor=0.1)
    assert fallback_val == 22.3
