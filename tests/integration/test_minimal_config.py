"""Test mit minimaler User-Config."""

from homeassistant.core import HomeAssistant

from custom_components.shadow_control.const import DOMAIN

MINIMAL_CONFIG = {
    DOMAIN: [
        {
            "name": "Minimal Test",
            "target_cover_entity": ["cover.sc_dummy"],
            "facade_shutter_type_static": "mode1",
            "brightness_entity": "input_number.d01_brightness",
            "sun_elevation_entity": "input_number.d03_sun_elevation",
            "sun_azimuth_entity": "input_number.d04_sun_azimuth",
        }
    ]
}


async def test_minimal_config_loads(
    hass: HomeAssistant,
    setup_from_user_config,
):
    """Test dass minimale Config lädt."""

    await setup_from_user_config(MINIMAL_CONFIG)

    # Integration sollte geladen sein
    assert DOMAIN in hass.data

    # Cover sollte existieren
    cover_state = hass.states.get("cover.sc_dummy")
    assert cover_state is not None
