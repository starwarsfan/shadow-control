"""Integration for Shadow Control."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from shadow_control.const import DOMAIN

from .shadow_control import ShadowControl

PLATFORMS: list[Platform] = [Platform.COVER]

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up Shadow Control from a config entry."""
    config = config_entry.data
    shadow_control = ShadowControl(hass, config)
    hass.data.setdefault(DOMAIN, {})[config_entry.entry_id] = shadow_control
    await shadow_control.async_setup()
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    ):
        hass.data[DOMAIN].pop(config_entry.entry_id)
    return unload_ok
