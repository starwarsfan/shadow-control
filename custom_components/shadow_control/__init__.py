"""Integration for Shadow Control."""

import logging
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Shadow Control component."""
    _LOGGER.info("Setting up Shadow Control component.")
    # Die eigentliche Plattform-Einrichtung erfolgt in shadow_control.py (async_setup_platform)
    return True

async def async_setup_entry(hass: HomeAssistant, config_entry) -> bool:
    """Dieses Setup ist für Config Entries gedacht und wird hier nicht verwendet."""
    _LOGGER.warning("Shadow Control wurde als YAML-Plattform konfiguriert, aber async_setup_entry wurde aufgerufen.")
    return False

async def async_unload_entry(hass: HomeAssistant, config_entry) -> bool:
    """Dieses Unload ist für Config Entries gedacht und wird hier nicht verwendet."""
    return True
