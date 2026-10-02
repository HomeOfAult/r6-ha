"""The R6 Data Relay integration."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import R6DataRelayApiClient
from .const import CONF_API_TOKEN, CONF_BASE_URL, CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL, LOGGER
from .coordinator import R6DataRelayConfigEntry, R6DataRelayDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: R6DataRelayConfigEntry) -> bool:
    """Set up R6 Data Relay from a config entry."""
    verify_ssl = entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)
    LOGGER.debug("Setting up R6 Data Relay for %s (verify_ssl=%s)", entry.data[CONF_BASE_URL], verify_ssl)
    client = R6DataRelayApiClient(
        entry.data[CONF_BASE_URL],
        entry.data[CONF_API_TOKEN],
        async_get_clientsession(hass, verify_ssl=verify_ssl),
    )
    coordinator = R6DataRelayDataUpdateCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: R6DataRelayConfigEntry) -> bool:
    """Unload a config entry."""
    LOGGER.debug("Unloading R6 Data Relay for %s", entry.data[CONF_BASE_URL])
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
