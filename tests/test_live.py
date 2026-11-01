"""Live integration tests against physical Zehnder device at 192.168.178.106."""
from __future__ import annotations

import asyncio
import socket
import pytest
import aiohttp

from custom_components.zehnder_comfoclime.api import ZehnderApiClient

LIVE_IP = "192.168.178.106"


def is_live_host_reachable() -> bool:
    """Check if the physical ComfoClime gateway is reachable."""
    try:
        with socket.create_connection((LIVE_IP, 80), timeout=1.0):
            return True
    except OSError:
        return False


@pytest.mark.skipif(not is_live_host_reachable(), reason="Live Zehnder device not reachable")
@pytest.mark.asyncio
async def test_live_ping_and_discovery():
    """Verify live ping and device discovery on actual hardware."""
    async with aiohttp.ClientSession() as session:
        client = ZehnderApiClient(host=LIVE_IP, session=session)
        ping_res = await client.ping()
        assert "uuid" in ping_res
        assert ping_res["uuid"] == "MBE6cc8400b5159"

        devices = await client.discover_devices()
        assert len(devices) >= 2
        assert client.clime_uuid == "MBE6cc8400b5159"
        assert client.q350_uuid == "SIT252401498"
        assert client.clime_version == "R1.5.5"


@pytest.mark.skipif(not is_live_host_reachable(), reason="Live Zehnder device not reachable")
@pytest.mark.asyncio
async def test_live_summary_retrieval():
    """Verify live summary retrieval without socket exhaustion."""
    async with aiohttp.ClientSession() as session:
        client = ZehnderApiClient(host=LIVE_IP, session=session)
        await client.discover_devices()

        summary = await client.get_summary()
        dash = summary.get("dashboard", {})
        q350 = summary.get("q350", {})
        clime = summary.get("clime", {})

        assert "fanSpeed" in dash
        assert "setPointTemperature" in dash
        assert "season" in dash
        assert "indoorTemperature" in dash
        assert "temperatureProfile" in dash
        assert dash["temperatureProfile"] is not None

        assert "thermal_profile" in summary
        assert "heatingThermalProfileSeasonData" in summary["thermal_profile"]

        assert "outdoor_temp" in q350
        assert "supply_temp_wrg" in q350
        assert "supply_airflow" in q350
        assert "exhaust_airflow" in q350

        assert "indoor_temp" in clime
        assert "supply_temp_after_hp" in clime
        assert "power_watts" in clime
        assert "heatpump_modulation_pct" in clime
        assert "comfort_temp" in clime
        assert clime["comfort_temp"] is not None
