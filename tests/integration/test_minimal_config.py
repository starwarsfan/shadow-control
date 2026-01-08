"""Test mit minimaler User-Config."""

import logging
from itertools import count
from typing import Any

from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import HomeAssistant, State
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.shadow_control.const import DOMAIN
from tests.integration.conftest import setup_instance, get_entity_and_show_state, \
    show_instance_entity_states

_LOGGER = logging.getLogger(__name__)

MINIMAL_CONFIG = {
    DOMAIN: [
        {
            "name": "SC Test Instance",
            "debug_enabled": False,
            "target_cover_entity": ["cover.sc_dummy"],
            "facade_shutter_type_static": "mode1",
            "brightness_entity": "input_number.d01_brightness",
            "sun_elevation_entity": "input_number.d03_sun_elevation",
            "sun_azimuth_entity": "input_number.d04_sun_azimuth",
            "sc_internal_values": {
                "shadow_control_enabled_manual": True,
                "shadow_brightness_threshold_manual": 15000,
                "shadow_after_seconds_manual": 10,
            },
        }
    ]
}


async def test_minimal_config_loads(
    hass: HomeAssistant,
    setup_from_user_config,
    caplog,
):
    """Test dass minimale Config lädt."""

    # Counter to distinct repeated outputs on the log
    # step = count(1)

    # Setup instance
    _, _ = await setup_instance(caplog, hass, setup_from_user_config, MINIMAL_CONFIG)

    # Integration sollte geladen sein
    assert DOMAIN in hass.data

    # Cover sollte existieren
    cover_state = hass.states.get("cover.sc_dummy")
    assert cover_state is not None


async def test_show_initial_state(
    hass: HomeAssistant,
    setup_from_user_config,
    caplog,
):
    """Debug: Zeige Initial State."""

    # Counter to distinct repeated outputs on the log
    step = count(1)

    # Setup instance
    _, _ = await setup_instance(caplog, hass, setup_from_user_config, MINIMAL_CONFIG)

    # 2. Prüfen, ob die Entität überhaupt schon im State-Machine ist
    # Falls hier None kommt, sind die Plattformen noch nicht geladen!
    entity = await get_entity_and_show_state(hass, "number.sc_test_instance_s_brightness_threshold")
    assert entity is not None

    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    await hass.async_block_till_done()

    # Zeige alle Shadow Control Entities
    await show_instance_entity_states(hass, next(step))

    # Prüfe gezielt einen Wert aus 'sc_internal_values'
    threshold = await get_entity_and_show_state(hass, "number.sc_test_instance_s_brightness_threshold")
    assert threshold.state == "15000"

    # Zeige Input Numbers
    _LOGGER.info("=" * 80)
    _LOGGER.info("INPUT NUMBERS:")
    brightness = hass.states.get("input_number.d01_brightness")
    elevation = hass.states.get("input_number.d03_sun_elevation")
    azimuth = hass.states.get("input_number.d04_sun_azimuth")

    _LOGGER.info("Brightness: %s", brightness.state if brightness else "NOT FOUND")
    _LOGGER.info("Elevation: %s", elevation.state if elevation else "NOT FOUND")
    _LOGGER.info("Azimuth: %s", azimuth.state if azimuth else "NOT FOUND")
