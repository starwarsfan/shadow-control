"""Integration Test: Komplette Shutter Automation."""

import logging

from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import HomeAssistant

from custom_components.shadow_control.const import DOMAIN

_LOGGER = logging.getLogger(__name__)

TEST_CONFIG = {
    DOMAIN: [
        {
            "name": "TC 01",
            "debug_enabled": False,
            "target_cover_entity": ["cover.sc_dummy"],
            "facade_shutter_type_static": "mode1",
            #
            # Dynamic configuration inputs
            "brightness_entity": "input_number.d01_brightness",
            # "brightness_dawn_entity":
            "sun_elevation_entity": "input_number.d03_sun_elevation",
            "sun_azimuth_entity": "input_number.d04_sun_azimuth",
            "sc_internal_values": {
                "lock_integration_manual": False,
                # "lock_integration_entity": input_boolean.d07_lock_integration
                "lock_integration_with_position_manual": False,
                # "lock_integration_with_position_entity": input_boolean.d08_lock_integration_with_position
                "lock_height_manual": 50,
                # "lock_height_entity": input_number.lock_height_sc_dummy
                "lock_angle_manual": 50,
                # "lock_angle_entity": input_number.lock_angle_sc_dummy
                # no_restriction, only_open, only_close
                "movement_restriction_height_manual": "no_restriction",
                "movement_restriction_angle_manual": "no_restriction",
                # "movement_restriction_height_entity":
                # "movement_restriction_angle_entity":
                # "enforce_positioning_entity": input_boolean.d13_enforce_positioning
                #
                # General facade configuration
                "facade_azimuth_static": 200,
                "facade_offset_sun_in_static": -45,
                "facade_offset_sun_out_static": 45,
                "facade_elevation_sun_min_static": 23,
                "facade_elevation_sun_max_static": 80,
                "facade_slat_width_static": 60,
                "facade_slat_distance_static": 50,
                "facade_slat_angle_offset_static": 0,
                "facade_slat_min_angle_static": 0,
                "facade_shutter_stepping_height_static": 5,
                "facade_shutter_stepping_angle_static": 5,
                "facade_light_strip_width_static": 0,
                "facade_shutter_height_static": 1000,
                "facade_neutral_pos_height_manual": 0,
                # "facade_neutral_pos_height_entity": input_number.g15_neutral_pos_height
                "facade_neutral_pos_angle_manual": 0,
                # "facade_neutral_pos_angle_entity": input_number.g16_neutral_pos_angle
                "facade_max_movement_duration_static": 3,
                "facade_modification_tolerance_height_static": 3,
                "facade_modification_tolerance_angle_static": 3,
                #
                # Shadow configuration
                # "shadow_control_enabled_entity":
                "shadow_control_enabled_manual": True,
                # "shadow_brightness_threshold_entity":
                "shadow_brightness_threshold_manual": 54321,
                # "shadow_after_seconds_entity":
                "shadow_after_seconds_manual": 5,
                # "shadow_shutter_max_height_entity": input_number.automation_shadow_max_height_sc_dummy
                "shadow_shutter_max_height_manual": 90,
                # "shadow_shutter_max_angle_entity": input_number.automation_shadow_max_angle_sc_dummy
                "shadow_shutter_max_angle_manual": 90,
                # "shadow_shutter_look_through_seconds_entity":
                "shadow_shutter_look_through_seconds_manual": 5,
                # "shadow_shutter_open_seconds_entity":
                "shadow_shutter_open_seconds_manual": 5,
                # "shadow_shutter_look_through_angle_entity":
                "shadow_shutter_look_through_angle_manual": 54,
                # "shadow_height_after_sun_entity":
                "shadow_height_after_sun_manual": 80,
                # "shadow_angle_after_sun_entity":
                "shadow_angle_after_sun_manual": 80,
                #
                # Dawn configuration
                # "dawn_control_enabled_entity":
                "dawn_control_enabled_manual": True,
                # "dawn_brightness_threshold_entity":
                "dawn_brightness_threshold_manual": 5000,
                # "dawn_after_seconds_entity":
                "dawn_after_seconds_manual": 5,
                # "dawn_shutter_max_height_entity": input_number.automation_dawn_max_height_sc_dummy
                "dawn_shutter_max_height_manual": 90,
                # "dawn_shutter_max_angle_entity": input_number.automation_dawn_max_angle_sc_dummy
                "dawn_shutter_max_angle_manual": 90,
                # "dawn_shutter_look_through_seconds_entity":
                "dawn_shutter_look_through_seconds_manual": 5,
                # "dawn_shutter_open_seconds_entity":
                "dawn_shutter_open_seconds_manual": 5,
                # "dawn_shutter_look_through_angle_entity":
                "dawn_shutter_look_through_angle_manual": 45,
                # "dawn_height_after_dawn_entity":
                "dawn_height_after_dawn_manual": 10,
                # "dawn_angle_after_dawn_entity":
                "dawn_angle_after_dawn_manual": 10,
            },
        }
    ]
}


async def test_show_initial_state(
    hass: HomeAssistant,
    setup_from_user_config,
    caplog,
):
    """Debug: Zeige Initial State."""

    caplog.set_level(logging.DEBUG)

    await setup_from_user_config(TEST_CONFIG)
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    await hass.async_block_till_done()

    # Zeige alle Shadow Control Entities
    states = hass.states.async_all()
    sc_entities = [s for s in states if "tc_01" in s.entity_id]

    _LOGGER.info("=" * 80)
    _LOGGER.info("SHADOW CONTROL ENTITIES:")
    for entity in sc_entities:
        # _LOGGER.info("%s: %s, Attributes: %s", entity.entity_id, entity.state, entity.attributes)
        _LOGGER.info("%s: %s", entity.entity_id, entity.state)

    # Zeige Input Numbers
    _LOGGER.info("=" * 80)
    _LOGGER.info("INPUT NUMBERS:")
    brightness = hass.states.get("input_number.d01_brightness")
    elevation = hass.states.get("input_number.d03_sun_elevation")
    azimuth = hass.states.get("input_number.d04_sun_azimuth")

    _LOGGER.info("Brightness: %s", brightness.state if brightness else "NOT FOUND")
    _LOGGER.info("Elevation: %s", elevation.state if elevation else "NOT FOUND")
    _LOGGER.info("Azimuth: %s", azimuth.state if azimuth else "NOT FOUND")


async def test_issue_123_timer_sequence(
    hass: HomeAssistant,
    setup_from_user_config,
    time_travel,
    update_sun,
):
    """Test Timer-Sequenz: Shadow-After → Look-Through → Open."""

    await setup_from_user_config(TEST_CONFIG)

    # 1. Trigger Shadow Conditions
    await update_sun(elevation=60, azimuth=180, brightness=70000)

    # 2. Nach shadow_after_seconds (5s) sollte Shadow starten
    await time_travel(seconds=6)

    sc_state = hass.states.get("sensor.sc_dummy_state")
    assert "shadow" in sc_state.state.lower()

    # 3. Nach look_through_seconds (5s) sollte Look-Through aktiv sein
    await time_travel(seconds=6)

    sc_state = hass.states.get("sensor.sc_dummy_state")
    # Je nach State-Namen
    assert "look_through" in sc_state.state.lower() or "neutral" in sc_state.state.lower()

    # 4. Nach open_seconds (5s) sollte wieder offen sein
    await time_travel(seconds=6)

    # TODO: Prüfe finale Position
    # cover_state = hass.states.get("cover.sc_dummy")


async def test_issue_123_dawn_sequence(
    hass: HomeAssistant,
    setup_from_user_config,
    time_travel,
    update_sun,
):
    """Test Dawn-Sequenz mit Timern."""

    await setup_from_user_config(TEST_CONFIG)

    # Dawn Conditions: Niedrige Helligkeit
    await update_sun(
        elevation=10,
        azimuth=90,  # Osten (Morgen)
        brightness=4000,  # Unter Dawn-Threshold (5000)
    )

    # Nach dawn_after_seconds (5s)
    await time_travel(seconds=6)

    sc_state = hass.states.get("sensor.sc_dummy_state")
    assert "dawn" in sc_state.state.lower()

    # TODO: Assert basierend auf deiner Logik
    # Cover sollte auf dawn_height_after_dawn (10%) sein
    # expected_height = 10  # dawn_height_after_dawn_manual


async def test_issue_123_no_timer_wait_with_time_travel(
    hass: HomeAssistant,
    setup_from_user_config,
    time_travel,
    update_sun,
):
    """Zeige dass Time-Travel keine echte Wartezeit braucht."""

    await setup_from_user_config(TEST_CONFIG)

    start_time = real_time.time()

    # Trigger Shadow
    await update_sun(elevation=60, azimuth=180, brightness=70000)

    # "Warte" 5 Sekunden (aber ohne echte Zeit)
    await time_travel(seconds=6)

    end_time = real_time.time()
    elapsed = end_time - start_time

    # Test sollte < 1 Sekunde dauern, nicht 5+
    assert elapsed < 1.0, f"Test dauerte {elapsed}s - Time Travel funktioniert nicht!"

    # Shadow sollte trotzdem aktiv sein
    sc_state = hass.states.get("sensor.sc_dummy_state")
    assert "shadow" in sc_state.state.lower()
