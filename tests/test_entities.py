"""Tests for Zehnder ComfoClime Home Assistant entities and config flow."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from homeassistant.components.climate import HVACAction, HVACMode, PRESET_NONE
from homeassistant.components.fan import FanEntityFeature
from homeassistant.const import UnitOfTemperature

from custom_components.zehnder_comfoclime.climate import ZehnderClimate
from custom_components.zehnder_comfoclime.fan import ZehnderVentilationFan
from custom_components.zehnder_comfoclime.sensor import (
    SENSOR_DESCRIPTIONS,
    ZehnderSensor,
)
from custom_components.zehnder_comfoclime.binary_sensor import (
    BINARY_SENSOR_DESCRIPTIONS,
    ZehnderBinarySensor,
)
from custom_components.zehnder_comfoclime.switch import (
    ZehnderAutoModeSwitch,
    ZehnderHeatPumpSwitch,
)
from custom_components.zehnder_comfoclime.select import (
    ZehnderProfileSelect,
    ZehnderSeasonSelect,
)
from custom_components.zehnder_comfoclime.const import (
    DOMAIN,
    PRESET_COMFORT,
    PRESET_ECO,
    PRESET_POWER,
    SEASON_COOLING,
    SEASON_HEATING,
    SEASON_TRANSITION,
    STATUS_AUTO,
    STATUS_MANUAL,
)


@pytest.fixture
def mock_coordinator():
    """Create a mock DataUpdateCoordinator with representative data."""
    coord = MagicMock()
    coord.api = MagicMock()
    coord.api.host = "192.168.178.106"
    coord.api.clime_uuid = "MBE6cc8400b5159"
    coord.api.q350_uuid = "SIT252401498"
    coord.api.clime_name = "ComfoClime 24"
    coord.api.q350_name = "ComfoAir Q350"
    coord.api.clime_version = "R1.5.5"

    coord.data = {
        "dashboard": {
            "indoorTemperature": 22.8,
            "outdoorTemperature": 6.2,
            "exhaustAirFlow": 160,
            "supplyAirFlow": 160,
            "fanSpeed": 2,
            "setPointTemperature": 22.5,
            "season": SEASON_HEATING,
            "status": STATUS_AUTO,
            "hpStandby": False,
            "temperatureProfile": 1,  # power
            "caqFreeCoolingAvailable": True,
            "freeCoolingEnabled": False,
        },
        "q350": {
            "outdoor_temp": 6.2,
            "supply_temp_wrg": 18.5,
            "supply_airflow": 160.0,
            "exhaust_airflow": 160.0,
            "rmot_temp": 8.1,
            "target_comfort_temp": 23.9,
            "bypass_state_pct": 0.0,
        },
        "clime": {
            "indoor_temp": 22.8,
            "setpoint_temp": 22.5,
            "supply_temp_after_hp": 24.5,
            "exhaust_temp_after_hp": 10.2,
            "supply_coil_temp": 23.0,
            "exhaust_coil_temp": 9.5,
            "compressor_temp": 45.0,
            "heatpump_modulation_pct": 60.0,
            "power_watts": 350.0,
            "tpma_temp": 6.5,
            "comfort_temp": 21.0,
        },
    }
    coord.async_request_refresh = AsyncMock()
    return coord


@pytest.fixture
def mock_entry():
    """Create a mock ConfigEntry."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.data = {
        "host": "192.168.178.106",
        "clime_uuid": "MBE6cc8400b5159",
        "q350_uuid": "SIT252401498",
        "clime_name": "ComfoClime 24",
        "q350_name": "ComfoAir Q350",
    }
    return entry


def test_climate_entity(mock_coordinator, mock_entry):
    """Test ZehnderClimate entity states and actions."""
    climate = ZehnderClimate(mock_coordinator, mock_entry)

    assert climate.unique_id == "MBE6cc8400b5159_climate"
    assert climate.temperature_unit == UnitOfTemperature.CELSIUS
    assert climate.current_temperature == 22.8
    assert climate.target_temperature == 22.5
    assert climate.hvac_mode == HVACMode.HEAT
    assert climate.hvac_action == HVACAction.HEATING
    assert climate.preset_mode == PRESET_POWER

    # When hpStandby is True -> HVACMode.OFF, HVACAction.OFF
    mock_coordinator.data["dashboard"]["hpStandby"] = True
    assert climate.hvac_mode == HVACMode.OFF
    assert climate.hvac_action == HVACAction.OFF

    # When Cooling season and compressor running -> HVACMode.COOL, HVACAction.COOLING
    mock_coordinator.data["dashboard"]["hpStandby"] = False
    mock_coordinator.data["dashboard"]["season"] = SEASON_COOLING
    assert climate.hvac_mode == HVACMode.COOL
    assert climate.hvac_action == HVACAction.COOLING

    # When Transition season -> HVACMode.FAN_ONLY, HVACAction.FAN
    mock_coordinator.data["dashboard"]["season"] = SEASON_TRANSITION
    assert climate.hvac_mode == HVACMode.FAN_ONLY
    assert climate.hvac_action == HVACAction.FAN

    # When in Manual mode (status: 0) -> preset_mode is PRESET_NONE
    mock_coordinator.data["dashboard"]["status"] = STATUS_MANUAL
    assert climate.preset_mode == PRESET_NONE


@pytest.mark.asyncio
async def test_climate_actions(mock_coordinator, mock_entry):
    """Test climate service calls."""
    climate = ZehnderClimate(mock_coordinator, mock_entry)
    mock_coordinator.api.set_target_temperature = AsyncMock()
    mock_coordinator.api.set_hvac_mode = AsyncMock()
    mock_coordinator.api.set_preset_profile = AsyncMock()
    mock_coordinator.api.set_hp_standby = AsyncMock()
    mock_coordinator.api.set_status = AsyncMock()

    # Temperature set with hvac_mode simultaneously
    await climate.async_set_temperature(temperature=21.0, hvac_mode=HVACMode.HEAT)
    mock_coordinator.api.set_target_temperature.assert_called_once_with(21.0)
    mock_coordinator.api.set_hvac_mode.assert_called_once_with("heat")

    await climate.async_set_hvac_mode(HVACMode.COOL)
    mock_coordinator.api.set_hvac_mode.assert_called_with("cool")

    await climate.async_set_preset_mode("eco")
    mock_coordinator.api.set_preset_profile.assert_called_once_with("eco")

    # Setting preset to PRESET_NONE returns to manual mode
    await climate.async_set_preset_mode(PRESET_NONE)
    mock_coordinator.api.set_status.assert_called_once_with(STATUS_MANUAL)

    await climate.async_turn_off()
    mock_coordinator.api.set_hp_standby.assert_called_once_with(True)

    await climate.async_turn_on()
    mock_coordinator.api.set_hp_standby.assert_called_with(False)


def test_fan_entity(mock_coordinator, mock_entry):
    """Test ZehnderVentilationFan entity."""
    fan = ZehnderVentilationFan(mock_coordinator, mock_entry)

    assert fan.unique_id == "SIT252401498_fan"
    assert fan.is_on is True
    # fanSpeed is 2 -> percentage is 66 in HA ranged_value_to_percentage
    assert fan.percentage == 66
    assert fan.preset_mode == "2"
    assert fan.device_info["identifiers"] == {(DOMAIN, "SIT252401498")}
    assert fan.device_info["via_device"] == (DOMAIN, "MBE6cc8400b5159")


@pytest.mark.asyncio
async def test_fan_actions(mock_coordinator, mock_entry):
    """Test fan speed and preset adjustments."""
    fan = ZehnderVentilationFan(mock_coordinator, mock_entry)
    mock_coordinator.api.set_fan_speed = AsyncMock()

    # Set percentage 33 -> speed 1
    await fan.async_set_percentage(33)
    mock_coordinator.api.set_fan_speed.assert_called_with(1)

    # Set percentage 100 -> speed 3
    await fan.async_set_percentage(100)
    mock_coordinator.api.set_fan_speed.assert_called_with(3)

    # Set preset "3"
    await fan.async_set_preset_mode("3")
    mock_coordinator.api.set_fan_speed.assert_called_with(3)


def test_sensor_entities(mock_coordinator, mock_entry):
    """Test all sensor entities extract valid values without KeyError."""
    sensors = [
        ZehnderSensor(mock_coordinator, mock_entry, desc)
        for desc in SENSOR_DESCRIPTIONS
    ]
    assert len(sensors) == len(SENSOR_DESCRIPTIONS)

    for sensor in sensors:
        val = sensor.native_value
        assert val is not None, f"Sensor {sensor.entity_description.key} returned None"
        if sensor.entity_description.device_target == "q350":
            assert sensor.device_info["identifiers"] == {(DOMAIN, "SIT252401498")}
        else:
            assert sensor.device_info["identifiers"] == {(DOMAIN, "MBE6cc8400b5159")}


def test_binary_sensor_entities(mock_coordinator, mock_entry):
    """Test binary sensor evaluations."""
    sensors = [
        ZehnderBinarySensor(mock_coordinator, mock_entry, desc)
        for desc in BINARY_SENSOR_DESCRIPTIONS
    ]
    assert len(sensors) == 4

    results = {s.entity_description.key: s.is_on for s in sensors}
    # hpStandby is False -> hp_active is True
    assert results["hp_active"] is True
    # caqFreeCoolingAvailable is True
    assert results["free_cooling_available"] is True
    # freeCoolingEnabled is False
    assert results["free_cooling_active"] is False
    # bypass is 0 -> bypass_active is False
    assert results["bypass_active"] is False


@pytest.mark.asyncio
async def test_switches(mock_coordinator, mock_entry):
    """Test switches for heat pump power and auto mode."""
    hp_switch = ZehnderHeatPumpSwitch(mock_coordinator, mock_entry)
    auto_switch = ZehnderAutoModeSwitch(mock_coordinator, mock_entry)

    mock_coordinator.api.set_hp_standby = AsyncMock()
    mock_coordinator.api.set_status = AsyncMock()

    # Initial state
    assert hp_switch.is_on is True  # hpStandby is False
    assert auto_switch.is_on is True  # status is STATUS_AUTO

    await hp_switch.async_turn_off()
    mock_coordinator.api.set_hp_standby.assert_called_with(True)

    await auto_switch.async_turn_off()
    mock_coordinator.api.set_status.assert_called_with(STATUS_MANUAL)


@pytest.mark.asyncio
async def test_selects(mock_coordinator, mock_entry):
    """Test select entities for profile and season."""
    profile_sel = ZehnderProfileSelect(mock_coordinator, mock_entry)
    season_sel = ZehnderSeasonSelect(mock_coordinator, mock_entry)

    mock_coordinator.api.set_preset_profile = AsyncMock()
    mock_coordinator.api.set_season = AsyncMock()

    # temperatureProfile = 1 -> "power"
    assert profile_sel.current_option == "power"
    # season = 1 -> "heating"
    assert season_sel.current_option == "heating"

    await profile_sel.async_select_option("eco")
    mock_coordinator.api.set_preset_profile.assert_called_with("eco")

    await season_sel.async_select_option("cooling")
    mock_coordinator.api.set_season.assert_called_with(SEASON_COOLING)


@pytest.mark.asyncio
async def test_config_flow_success(monkeypatch):
    """Test successful config flow execution."""
    from custom_components.zehnder_comfoclime.config_flow import ZehnderConfigFlow

    flow = ZehnderConfigFlow()
    flow.hass = MagicMock()
    flow.hass.config_entries.async_entries = MagicMock(return_value=[])
    flow.hass.config_entries.async_entry_for_domain_unique_id = MagicMock(return_value=None)
    flow.context = {}

    mock_api = MagicMock()
    mock_api.ping = AsyncMock(return_value={"uuid": "MBE6cc8400b5159"})
    mock_api.discover_devices = AsyncMock(return_value=[])
    mock_api.clime_uuid = "MBE6cc8400b5159"
    mock_api.q350_uuid = "SIT252401498"
    mock_api.clime_name = "ComfoClime 24"
    mock_api.q350_name = "ComfoAir Q350"
    mock_api.clime_version = "R1.5.5"

    monkeypatch.setattr(
        "custom_components.zehnder_comfoclime.config_flow.async_get_clientsession",
        lambda hass: MagicMock(),
    )
    monkeypatch.setattr(
        "custom_components.zehnder_comfoclime.config_flow.ZehnderApiClient",
        lambda *args, **kwargs: mock_api,
    )

    result = await flow.async_step_user({"host": "192.168.178.106"})
    assert result["type"] == "create_entry"
    assert result["title"] == "Zehnder ComfoClime (192.168.178.106)"
    assert result["data"]["clime_uuid"] == "MBE6cc8400b5159"
    assert result["data"]["q350_uuid"] == "SIT252401498"


@pytest.mark.asyncio
async def test_config_flow_cannot_connect(monkeypatch):
    """Test config flow when host cannot connect."""
    from custom_components.zehnder_comfoclime.config_flow import ZehnderConfigFlow
    from custom_components.zehnder_comfoclime.api import ZehnderConnectionError

    flow = ZehnderConfigFlow()
    flow.hass = MagicMock()
    flow.context = {}

    mock_api = MagicMock()
    mock_api.ping = AsyncMock(side_effect=ZehnderConnectionError("Network unreachable"))

    monkeypatch.setattr(
        "custom_components.zehnder_comfoclime.config_flow.async_get_clientsession",
        lambda hass: MagicMock(),
    )
    monkeypatch.setattr(
        "custom_components.zehnder_comfoclime.config_flow.ZehnderApiClient",
        lambda *args, **kwargs: mock_api,
    )

    result = await flow.async_step_user({"host": "192.168.178.999"})
    assert result["type"] == "form"
    assert result["errors"] == {"base": "cannot_connect"}


@pytest.mark.asyncio
async def test_setup_without_q350():
    """Verify that only ComfoClime entities are created when Q350 is absent."""
    from custom_components.zehnder_comfoclime.sensor import async_setup_entry as sensor_setup
    from custom_components.zehnder_comfoclime.fan import async_setup_entry as fan_setup
    from custom_components.zehnder_comfoclime.binary_sensor import async_setup_entry as binary_sensor_setup

    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "clime_only_entry"
    entry.data = {"host": "1.2.3.4", "clime_uuid": "MBE_ONLY"}

    coord = MagicMock()
    coord.api = MagicMock()
    coord.api.host = "1.2.3.4"
    coord.api.clime_uuid = "MBE_ONLY"
    coord.api.q350_uuid = None
    coord.api.clime_name = "ComfoClime 24"
    coord.api.q350_name = "ComfoAir Q350"
    coord.api.clime_version = "R1.5.5"
    coord.data = {
        "dashboard": {},
        "clime": {},
        "q350": {},
    }

    hass.data = {DOMAIN: {entry.entry_id: coord}}

    # Fan setup should add 0 entities without Q350
    fan_entities = []
    await fan_setup(hass, entry, lambda entities: fan_entities.extend(entities))
    assert len(fan_entities) == 0

    # Sensor setup should only add Clime sensors (11 sensors)
    sensor_entities = []
    await sensor_setup(hass, entry, lambda entities: sensor_entities.extend(entities))
    assert len(sensor_entities) == 11
    assert all(s.entity_description.device_target == "clime" for s in sensor_entities)

    # Binary sensor setup should only add Clime binary sensors (3 sensors)
    binary_entities = []
    await binary_sensor_setup(hass, entry, lambda entities: binary_entities.extend(entities))
    assert len(binary_entities) == 3
    assert all(s.entity_description.device_target == "clime" for s in binary_entities)


