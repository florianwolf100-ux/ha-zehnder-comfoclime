"""Sensor platform for Zehnder ComfoClime and ComfoAir Q."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfVolumeFlowRate,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ZehnderDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class ZehnderSensorEntityDescription(SensorEntityDescription):
    """Class describing Zehnder sensor entities."""

    device_target: str  # "clime" or "q350"
    value_fn: Callable[[dict[str, Any]], Any]


SENSOR_DESCRIPTIONS: tuple[ZehnderSensorEntityDescription, ...] = (
    # --- ComfoAir Q350 Sensors ---
    ZehnderSensorEntityDescription(
        key="outdoor_temp",
        translation_key="outdoor_temp",
        device_target="q350",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("q350", {}).get("outdoor_temp"),
    ),
    ZehnderSensorEntityDescription(
        key="supply_temp_wrg",
        translation_key="supply_temp_wrg",
        device_target="q350",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("q350", {}).get("supply_temp_wrg"),
    ),
    ZehnderSensorEntityDescription(
        key="supply_airflow",
        translation_key="supply_airflow",
        device_target="q350",
        device_class=SensorDeviceClass.VOLUME_FLOW_RATE,
        native_unit_of_measurement=UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("q350", {}).get("supply_airflow"),
    ),
    ZehnderSensorEntityDescription(
        key="exhaust_airflow",
        translation_key="exhaust_airflow",
        device_target="q350",
        device_class=SensorDeviceClass.VOLUME_FLOW_RATE,
        native_unit_of_measurement=UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("q350", {}).get("exhaust_airflow"),
    ),
    ZehnderSensorEntityDescription(
        key="rmot_temp",
        translation_key="rmot_temp",
        device_target="q350",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("q350", {}).get("rmot_temp"),
    ),
    ZehnderSensorEntityDescription(
        key="target_comfort_temp",
        translation_key="target_comfort_temp",
        device_target="q350",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda data: data.get("q350", {}).get("target_comfort_temp"),
    ),
    ZehnderSensorEntityDescription(
        key="bypass_state_pct",
        translation_key="bypass_state_pct",
        device_target="q350",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("q350", {}).get("bypass_state_pct"),
    ),
    # --- ComfoClime 24 Sensors ---
    ZehnderSensorEntityDescription(
        key="indoor_temp",
        translation_key="indoor_temp",
        device_target="clime",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("clime", {}).get("indoor_temp"),
    ),
    ZehnderSensorEntityDescription(
        key="supply_temp_after_hp",
        translation_key="supply_temp_after_hp",
        device_target="clime",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("clime", {}).get("supply_temp_after_hp"),
    ),
    ZehnderSensorEntityDescription(
        key="exhaust_temp_after_hp",
        translation_key="exhaust_temp_after_hp",
        device_target="clime",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("clime", {}).get("exhaust_temp_after_hp"),
    ),
    ZehnderSensorEntityDescription(
        key="supply_coil_temp",
        translation_key="supply_coil_temp",
        device_target="clime",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("clime", {}).get("supply_coil_temp"),
    ),
    ZehnderSensorEntityDescription(
        key="exhaust_coil_temp",
        translation_key="exhaust_coil_temp",
        device_target="clime",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("clime", {}).get("exhaust_coil_temp"),
    ),
    ZehnderSensorEntityDescription(
        key="compressor_temp",
        translation_key="compressor_temp",
        device_target="clime",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("clime", {}).get("compressor_temp"),
    ),
    ZehnderSensorEntityDescription(
        key="power_watts",
        translation_key="power_watts",
        device_target="clime",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("clime", {}).get("power_watts"),
    ),
    ZehnderSensorEntityDescription(
        key="heatpump_modulation_pct",
        translation_key="heatpump_modulation_pct",
        device_target="clime",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("clime", {}).get("heatpump_modulation_pct"),
    ),
    ZehnderSensorEntityDescription(
        key="tpma_temp",
        translation_key="tpma_temp",
        device_target="clime",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("clime", {}).get("tpma_temp"),
    ),
    ZehnderSensorEntityDescription(
        key="comfort_temp",
        translation_key="comfort_temp",
        device_target="clime",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("clime", {}).get("comfort_temp"),
    ),
    ZehnderSensorEntityDescription(
        key="setpoint_temp",
        translation_key="setpoint_temp",
        device_target="clime",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda data: data.get("dashboard", {}).get("setPointTemperature"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Zehnder sensor entities."""
    coordinator: ZehnderDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    has_q350 = bool(coordinator.api.q350_uuid or entry.data.get("q350_uuid"))
    entities = [
        ZehnderSensor(coordinator, entry, desc)
        for desc in SENSOR_DESCRIPTIONS
        if desc.device_target == "clime" or has_q350
    ]
    async_add_entities(entities)


class ZehnderSensor(CoordinatorEntity[ZehnderDataUpdateCoordinator], SensorEntity):
    """Representation of a Zehnder Sensor."""

    entity_description: ZehnderSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ZehnderDataUpdateCoordinator,
        entry: ConfigEntry,
        description: ZehnderSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._clime_uuid = (
            coordinator.api.clime_uuid or entry.data.get("clime_uuid") or "clime"
        )
        self._q350_uuid = (
            coordinator.api.q350_uuid
            or entry.data.get("q350_uuid")
            or f"{self._clime_uuid}_q350"
        )

        target_uuid = (
            self._q350_uuid
            if description.device_target == "q350"
            else self._clime_uuid
        )
        self._attr_unique_id = f"{target_uuid}_{description.key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info based on target device."""
        if self.entity_description.device_target == "q350":
            return DeviceInfo(
                identifiers={(DOMAIN, self._q350_uuid)},
                name=self.coordinator.api.q350_name,
                manufacturer="Zehnder",
                model="ComfoAir Q350",
                via_device=(DOMAIN, self._clime_uuid),
            )
        return DeviceInfo(
            identifiers={(DOMAIN, self._clime_uuid)},
            name=self.coordinator.api.clime_name,
            manufacturer="Zehnder",
            model="ComfoClime 24",
            sw_version=self.coordinator.api.clime_version,
            configuration_url=f"http://{self.coordinator.api.host}",
        )

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        return self.entity_description.value_fn(self.coordinator.data)
