"""Test mit minimaler User-Config."""

import logging

from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import HomeAssistant

from custom_components.shadow_control.const import DOMAIN

_LOGGER = logging.getLogger(__name__)

MINIMAL_CONFIG = {
    DOMAIN: [
        {
            "name": "Minimal Test",
            "target_cover_entity": "cover.sc_dummy",
            "brightness_entity": "input_number.d01_brightness",
            "sun_elevation_entity": "input_number.d03_sun_elevation",
            "sun_azimuth_entity": "input_number.d04_sun_azimuth",
            # Hier landen die Werte für die internen Numbers/Switches/Selects:
            "sc_internal_values": {
                "shadow_control_enabled_manual": True,  # Schaltet den Switch direkt ein!
                "shadow_brightness_threshold_manual": 15000,
                "shadow_after_seconds_manual": 10,
                "debug_mode": True,
            },
            # Alle anderen Felder, die NICHT in sc_internal_values stehen,
            # landen in den normalen Manager-Optionen.
            "facade_shutter_type_static": "mode1",
        }
    ]
}


async def test_minimal_config_loads(
    hass: HomeAssistant,
    setup_from_user_config,
):
    """Test dass minimale Config lädt."""

    await setup_from_user_config(MINIMAL_CONFIG)
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    await hass.async_block_till_done()

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

    caplog.set_level(logging.DEBUG)

    await setup_from_user_config(MINIMAL_CONFIG)

    # 2. Prüfen, ob die Entität überhaupt schon im State-Machine ist
    # Falls hier None kommt, sind die Plattformen noch nicht geladen!
    entity_id = "number.minimal_test_s_brightness_threshold"
    assert hass.states.get(entity_id) is not None

    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    await hass.async_block_till_done()

    # Zeige alle Shadow Control Entities
    states = hass.states.async_all()
    sc_entities = [s for s in states if "minimal_test" in s.entity_id]

    _LOGGER.info("=" * 80)
    _LOGGER.info("SHADOW CONTROL ENTITIES:")
    for entity in sc_entities:
        # _LOGGER.info("%s: %s, Attributes: %s", entity.entity_id, entity.state, entity.attributes)
        _LOGGER.info("%s: %s", entity.entity_id, entity.state)

    # Prüfe gezielt einen Wert aus 'sc_internal_values'
    threshold = hass.states.get("number.minimal_test_s_brightness_threshold")
    if threshold:
        _LOGGER.info("S-Brightness Threshold: %s (Expected: 15000)", threshold.state)
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
