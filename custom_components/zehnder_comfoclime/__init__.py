"""Zehnder ComfoClime & ComfoAir Q integration for Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ZehnderApiClient
from .const import (
    CONF_HOST,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    CONF_FAH_ENABLED,
    CONF_FAH_HOST,
    CONF_FAH_USER,
    CONF_FAH_PASSWORD,
    CONF_FAH_RTC_DEVICE_ID,
    DEFAULT_FAH_HOST,
    DEFAULT_FAH_USER,
    DEFAULT_FAH_RTC_DEVICE_ID,
)
from .coordinator import ZehnderDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.CLIMATE,
    Platform.FAN,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.SELECT,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Zehnder ComfoClime from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    host = entry.data[CONF_HOST]
    scan_interval = entry.options.get(
        CONF_SCAN_INTERVAL,
        entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
    )

    session = async_get_clientsession(hass)
    api = ZehnderApiClient(host=host, session=session)

    # Initial device discovery
    clime_uuid = entry.data.get("clime_uuid")
    q350_uuid = entry.data.get("q350_uuid")
    if clime_uuid:
        api.clime_uuid = clime_uuid
    if q350_uuid:
        api.q350_uuid = q350_uuid

    try:
        await api.discover_devices()
    except Exception as err:
        _LOGGER.warning("Initial device discovery encountered issue: %s", err)

    coordinator = ZehnderDataUpdateCoordinator(
        hass, api=api, update_interval=scan_interval
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Set up Free@Home SysAP Virtual RTC Bridge if enabled
    fah_enabled = entry.options.get(
        CONF_FAH_ENABLED, entry.data.get(CONF_FAH_ENABLED, False)
    )
    if fah_enabled:
        fah_host = entry.options.get(
            CONF_FAH_HOST, entry.data.get(CONF_FAH_HOST, DEFAULT_FAH_HOST)
        )
        fah_user = entry.options.get(
            CONF_FAH_USER, entry.data.get(CONF_FAH_USER, DEFAULT_FAH_USER)
        )
        fah_password = entry.options.get(
            CONF_FAH_PASSWORD, entry.data.get(CONF_FAH_PASSWORD, "")
        )
        fah_rtc_id = entry.options.get(
            CONF_FAH_RTC_DEVICE_ID,
            entry.data.get(CONF_FAH_RTC_DEVICE_ID, DEFAULT_FAH_RTC_DEVICE_ID),
        )

        if fah_password:
            from .freeathome import FreeAtHomeBridge

            bridge = FreeAtHomeBridge(
                hass=hass,
                coordinator=coordinator,
                host=fah_host,
                username=fah_user,
                password=fah_password,
                device_id=fah_rtc_id,
            )
            await bridge.async_start()
            hass.data[DOMAIN][f"{entry.entry_id}_fah_bridge"] = bridge

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Zehnder ComfoClime config entry."""
    fah_bridge = hass.data[DOMAIN].pop(f"{entry.entry_id}_fah_bridge", None)
    if fah_bridge:
        await fah_bridge.async_stop()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)
