# Zehnder ComfoClime & ComfoAir Q Home Assistant Integration

[![HACS Custom Repository](https://img.shields.io/badge/HACS-Custom%20Repository-orange.svg?style=for-the-badge)](https://github.com/hacs/default)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-41BDF5?style=for-the-badge&logo=homeassistant&logoColor=white)](https://www.home-assistant.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

Home Assistant integration for **Zehnder ComfoClime 24** and connected **Zehnder ComfoAir Q (Q350 / Q450 / Q600)** ventilation systems.

Direct, fully local REST communication with the ComfoClime gateway over your local network — no cloud, no Zehnder app required, completely offline.

---

## 🌟 Features

- **100% Local Control**: Fast, direct REST API communication via the ComfoClime's built-in network gateway.
- **Climate Entity (`climate.zehnder_comfoclime`)**:
  - Full HVAC mode control: `Off` (Standby), `Heat`, `Cool`, `Fan only` (Transition / Übergangszeit).
  - Target temperature control with automatic manual-lock (`status: 0`) preventing the device from reverting setpoints.
  - Profile presets: `Comfort` (0), `Power / Boost` (1), `Eco` (2).
  - Active state reporting: Heating, Cooling, Fan, or Idle based on heat pump power and compressor modulation.
- **Ventilation Fan (`fan.ventilation`)**:
  - Direct control of the ComfoAir Q ventilation levels (Stufe 1, 2, 3 / speed percentage).
- **Comprehensive Sensor Suite (18+ Sensors)**:
  - **Indoor & Outdoor**: Room temperature, Outdoor temperature before heat exchanger, RMOT (running mean outdoor temperature).
  - **Supply & Exhaust Air**: Supply air after heat exchanger (WRG), Supply air into rooms after heat pump, Exhaust air after heat pump.
  - **Airflows**: Exact supply and exhaust volume flows in $m^3/h$.
  - **Heat Pump Diagnostics**: Electrical power consumption in Watts ($W$), Compressor modulation ($0-100\%$), Compressor temperature, Evaporator and Condenser coil temperatures, TPMA mixed-air reference.
  - **Bypass & Free Cooling**: Bypass damper position in $\%$, free cooling status.
- **Switches & Selects**:
  - Heat Pump Standby / Power switch.
  - Automatic profile vs. manual temperature switch.
  - Profile selector (`comfort`, `power`, `eco`).
  - Season mode selector (`transition`, `heating`, `cooling`).
- **Hardware-Aware Robustness**:
  - Features internal request locking and sequential telemetry querying designed specifically for the embedded microcontroller (ESP/Airduino) to prevent socket exhaustion and `HTTP 500: Could not allocate memory` errors.
- **Full German & English Localization**:
  - Native translations for all configuration steps, entity names, and state attributes.

---

## 🏗️ System Architecture

```text
               +-------------------------------------------+
               |              Home Assistant               |
               +-------------------------------------------+
                                     │
                     Local HTTP / REST (Port 80)
                                     │
                                     ▼
                     ┌──────────────────────────────┐
                     │    Zehnder ComfoClime 24     │
                     │  (Gateway / Master Unit)     │
                     │  IP: e.g. 192.168.178.106    │
                     └──────────────┬───────────────┘
                                    │
                         Internal ComfoNet (CAN)
                                    │
                                    ▼
                     ┌──────────────────────────────┐
                     │    Zehnder ComfoAir Q350     │
                     │  (Ventilation Unit / Slave)  │
                     └──────────────────────────────┘
```

The ComfoClime 24 functions as the network gateway for the entire ventilation and heating/cooling system. Both devices are registered in Home Assistant:
1. **Zehnder ComfoClime 24** (Gateway / Heat pump)
2. **Zehnder ComfoAir Q** (Ventilation unit, linked via the ComfoClime)

---

## 📦 Installation

### Option 1: Via HACS (Recommended)

1. Open **HACS** in your Home Assistant.
2. Click on the 3 dots in the top right corner and choose **Custom repositories**.
3. Enter the repository URL:
   ```text
   https://github.com/florianwolf100-ux/ha-zehnder-comfoclime
   ```
4. Category: **Integration**.
5. Click **Add** and search for `Zehnder ComfoClime & ComfoAir Q`.
6. Click **Download**, then restart Home Assistant.

### Option 2: Manual Installation

1. Clone or download this repository.
2. Copy the `custom_components/zehnder_comfoclime` directory into your Home Assistant's `config/custom_components/` directory:
   ```text
   config/
   └── custom_components/
       └── zehnder_comfoclime/
           ├── __init__.py
           ├── api.py
           ├── binary_sensor.py
           ├── climate.py
           ├── config_flow.py
           ├── const.py
           ├── coordinator.py
           ├── fan.py
           ├── manifest.json
           ├── select.py
           ├── sensor.py
           ├── strings.json
           ├── switch.py
           └── translations/
   ```
3. Restart Home Assistant.

---

## ⚙️ Configuration

1. In Home Assistant, go to **Settings** → **Devices & Services**.
2. Click **Add Integration** and search for **Zehnder ComfoClime**.
3. Enter the IP address of your ComfoClime unit (e.g. `192.168.178.106`).
4. Home Assistant will connect to the device, query `/monitoring/ping`, discover both the ComfoClime and connected ComfoAir Q on the ComfoNet bus, and set up all entities automatically.

### Integration Options

Under **Settings** → **Devices & Services** → **Zehnder ComfoClime** → **Configure**:
- **Update Interval**: Polling interval in seconds (default: 30s, adjustable from 10s to 300s).

---

## 📊 Provided Entities

### Climate
| Entity | Description | Modes |
| :--- | :--- | :--- |
| `climate.zehnder_comfoclime` | Heat Pump Climate Control | `off`, `heat`, `cool`, `fan_only` |

### Fan
| Entity | Description | Speeds |
| :--- | :--- | :--- |
| `fan.ventilation` | ComfoAir Q Ventilation Speed | Level 1, 2, 3 ($33\%$, $67\%$, $100\%$) |

### Sensors (ComfoAir Q)
| Entity | Unit | Description |
| :--- | :--- | :--- |
| `sensor.outdoor_temperature` | °C | Outdoor air temperature before heat exchanger |
| `sensor.supply_temperature_heat_exchanger` | °C | Supply air temperature after heat exchanger (WRG) |
| `sensor.supply_air_flow` | $m^3/h$ | Supply air volume flow |
| `sensor.exhaust_air_flow` | $m^3/h$ | Exhaust air volume flow |
| `sensor.rmot_outdoor_temperature` | °C | Running mean outdoor temperature |
| `sensor.target_comfort_temperature` | °C | Q350 comfort target temperature |
| `sensor.bypass_position` | % | Bypass damper position ($0-100\%$) |

### Sensors (ComfoClime 24)
| Entity | Unit | Description |
| :--- | :--- | :--- |
| `sensor.indoor_temperature` | °C | Room temperature |
| `sensor.supply_temperature_after_heat_pump` | °C | Supply air into living spaces after heat pump |
| `sensor.exhaust_temperature_after_heat_pump` | °C | Exhaust air to outside after heat pump |
| `sensor.heat_pump_power` | W | Electrical power consumption |
| `sensor.heat_pump_modulation` | % | Heat pump output modulation |
| `sensor.compressor_temperature` | °C | Compressor temperature |
| `sensor.supply_coil_temperature` | °C | Evaporator/Condenser supply coil temp |
| `sensor.exhaust_coil_temperature` | °C | Evaporator/Condenser exhaust coil temp |
| `sensor.tpma_reference_temperature` | °C | TPMA mixed-air reference temperature |
| `sensor.setpoint_temperature` | °C | Active target temperature setpoint |

### Binary Sensors
| Entity | Device Class | Description |
| :--- | :--- | :--- |
| `binary_sensor.heat_pump_active` | `running` | On when heat pump is active (not standby) |
| `binary_sensor.free_cooling_available` | `diagnostic` | On when free cooling is available |
| `binary_sensor.free_cooling_active` | `running` | On when free cooling is currently cooling |
| `binary_sensor.bypass_open` | `opening` | On when bypass damper is opened ($>0\%$) |

### Switches & Selects
| Entity | Type | Options / Function |
| :--- | :--- | :--- |
| `switch.heat_pump_power` | Switch | Toggles heat pump Standby on/off |
| `switch.automatic_profile_mode` | Switch | Toggles between Auto profile (`status: 1`) and Manual setpoint (`status: 0`) |
| `select.temperature_profile` | Select | `comfort`, `power`, `eco` |
| `select.season_mode` | Select | `transition`, `heating`, `cooling` |

---

## 🔍 Technical Details & Quirks Discovered

1. **Manual Temperature vs Automatic Profile (`status: 0` vs `1`)**:
   - When setting a manual temperature setpoint via the REST API, the payload **must** include `"status": 0`. If omitted, the ComfoClime's internal curve calculator will overwrite the setpoint after a few seconds.
   - When changing a preset profile (`comfort`, `power`, `eco`), `"status": 1` is sent to restore automatic curve control.
2. **Microcontroller Socket Exhaustion**:
   - The ComfoClime network interface runs on an embedded ESP controller with a limited socket pool. Firing 15+ concurrent requests causes socket starvation and connection drops.
   - This integration uses an asynchronous request queue/lock with keep-alive sessions to query all metrics sequentially in under 700 ms, completely avoiding socket exhaustion.
3. **Data Encoding**:
   - All PDO telemetry values are Little-Endian encoded (LSB first, MSB second) and scaled by $0.1$ for temperatures or $1.0$ for power and airflows.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
