"""Constants for the Zehnder ComfoClime integration."""
from __future__ import annotations

from typing import Final

DOMAIN: Final = "zehnder_comfoclime"

# Configuration keys
CONF_HOST: Final = "host"
CONF_SCAN_INTERVAL: Final = "scan_interval"
DEFAULT_SCAN_INTERVAL: Final = 30
MIN_SCAN_INTERVAL: Final = 10
MAX_SCAN_INTERVAL: Final = 300

# Free@Home SysAP Integration
CONF_FAH_ENABLED: Final = "fah_enabled"
CONF_FAH_HOST: Final = "fah_host"
CONF_FAH_USER: Final = "fah_user"
CONF_FAH_PASSWORD: Final = "fah_password"
CONF_FAH_RTC_DEVICE_ID: Final = "fah_rtc_device_id"

DEFAULT_FAH_HOST: Final = "192.168.178.36"
DEFAULT_FAH_USER: Final = "installer"
DEFAULT_FAH_RTC_DEVICE_ID: Final = "600005D4E7DC"

# Device Model Type IDs
MODEL_TYPE_Q350: Final = 1
MODEL_TYPE_COMFOCLIME: Final = 20

# Seasons (Dashboard & Thermal profile)
SEASON_TRANSITION: Final = 0  # Übergangszeit (Nur Lüftung / Fan only)
SEASON_HEATING: Final = 1     # Heizen
SEASON_COOLING: Final = 2     # Kühlen

SEASON_NAMES: Final = {
    SEASON_TRANSITION: "transition",
    SEASON_HEATING: "heating",
    SEASON_COOLING: "cooling",
}

# Status (Manual vs Auto)
STATUS_MANUAL: Final = 0
STATUS_AUTO: Final = 1

# Presets / Profiles
PRESET_COMFORT: Final = "comfort"
PRESET_POWER: Final = "power"
PRESET_ECO: Final = "eco"

PRESET_TO_PROFILE_ID: Final = {
    PRESET_COMFORT: 0,
    PRESET_POWER: 1,
    PRESET_ECO: 2,
}

PROFILE_ID_TO_PRESET: Final = {
    0: PRESET_COMFORT,
    1: PRESET_POWER,
    2: PRESET_ECO,
}

# Telemetry IDs
# ComfoAir Q350
TEL_Q350_OUTDOOR_TEMP: Final = 117          # Außenluft vor WRG (°C)
TEL_Q350_SUPPLY_TEMP_WRG: Final = 278       # Zuluft nach WRG Wärmetauscher (°C)
TEL_Q350_EXHAUST_AIRFLOW: Final = 119       # Abluft-Volumenstrom (m³/h)
TEL_Q350_SUPPLY_AIRFLOW: Final = 120        # Zuluft-Volumenstrom (m³/h)
TEL_Q350_EXHAUST_FAN_RPM: Final = 121       # Abluft Lüfter Drehzahl (rpm)
TEL_Q350_SUPPLY_FAN_RPM: Final = 122        # Zuluft Lüfter Drehzahl (rpm)
TEL_Q350_POWER_WATTS: Final = 128           # Lüftung Leistungsaufnahme (W)
TEL_Q350_ENERGY_YEAR: Final = 129           # Lüftung Energie Jahr (kWh)
TEL_Q350_ENERGY_TOTAL: Final = 130          # Lüftung Energie Gesamt (kWh)
TEL_Q350_RMOT_TEMP: Final = 209             # Gleitende mittlere Außentemp (°C)
TEL_Q350_TARGET_COMFORT_TEMP: Final = 212   # Ziel-Komforttemperatur (°C)
TEL_Q350_BYPASS_STATE: Final = 227          # Bypass-Klappe (%)
TEL_Q350_FORTLUFT_TEMP: Final = 275         # Fortluft Temperatur (°C)
TEL_Q350_EXHAUST_HUMIDITY: Final = 290      # Abluft Feuchtigkeit (%)
TEL_Q350_FORTLUFT_HUMIDITY: Final = 291     # Fortluft Feuchtigkeit (%)
TEL_Q350_OUTDOOR_HUMIDITY: Final = 292      # Außenluft Feuchtigkeit (%)
TEL_Q350_SUPPLY_HUMIDITY: Final = 294       # Zuluft Feuchtigkeit (%)

# ComfoClime 24
TEL_CLIME_TPMA_TEMP: Final = 4145           # TPMA Mischluft (°C)
TEL_CLIME_SETPOINT_TEMP: Final = 4148       # Aktuelle Solltemperatur (°C)
TEL_CLIME_MODE: Final = 4149                # Modus (0=Aus, 1=Heizen, 2=Kühlen)
TEL_CLIME_COMFORT_TEMP: Final = 4151        # Komforttemperatur Kurvenbasis (°C)
TEL_CLIME_INDOOR_TEMP: Final = 4154         # Raumtemperatur (°C)
TEL_CLIME_SUPPLY_TEMP_HP: Final = 4193      # Zuluft in Wohnräume nach WP (°C)
TEL_CLIME_EXHAUST_TEMP_HP: Final = 4194     # Fortluft nach WP (°C)
TEL_CLIME_SUPPLY_COIL_TEMP: Final = 4195    # Register Zuluft (°C)
TEL_CLIME_EXHAUST_COIL_TEMP: Final = 4196   # Register Abluft (°C)
TEL_CLIME_COMPRESSOR_TEMP: Final = 4197     # Kompressortemperatur (°C)
TEL_CLIME_MODULATION: Final = 4198          # WP Modulation (%)
TEL_CLIME_POWER_WATTS: Final = 4201         # Elektrische Leistung (W)
