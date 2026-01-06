"""Integration Test: Komplette Shutter Automation."""

import logging

from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.shadow_control.const import DOMAIN

_LOGGER = logging.getLogger(__name__)

TEST_CONFIG = {
    DOMAIN: [
        {
            "name": "TC 01",
            "debug_enabled": True,
            "target_cover_entity": ["cover.sc_dummy"],
            "facade_shutter_type_static": "mode1",
            #
            # Dynamic configuration inputs
            "brightness_entity": "input_number.d01_brightness",
            # "brightness_dawn_entity":
            "sun_elevation_entity": "input_number.d03_sun_elevation",
            "sun_azimuth_entity": "input_number.d04_sun_azimuth",
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
            "facade_max_movement_duration_static": 3,
            "facade_modification_tolerance_height_static": 3,
            "facade_modification_tolerance_angle_static": 3,
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
                "facade_neutral_pos_height_manual": 0,
                # "facade_neutral_pos_height_entity": input_number.g15_neutral_pos_height
                "facade_neutral_pos_angle_manual": 0,
                # "facade_neutral_pos_angle_entity": input_number.g16_neutral_pos_angle
                #
                # Shadow configuration
                # "shadow_control_enabled_entity":
                "shadow_control_enabled_manual": True,
                # "shadow_brightness_threshold_entity":
                "shadow_brightness_threshold_manual": 54321,
                # "shadow_after_seconds_entity":
                "shadow_after_seconds_manual": 5,
                # "shadow_shutter_max_height_entity": input_number.automation_shadow_max_height_sc_dummy
                "shadow_shutter_max_height_manual": 100,
                # "shadow_shutter_max_angle_entity": input_number.automation_shadow_max_angle_sc_dummy
                "shadow_shutter_max_angle_manual": 100,
                # "shadow_shutter_look_through_seconds_entity":
                "shadow_shutter_look_through_seconds_manual": 5,
                # "shadow_shutter_open_seconds_entity":
                "shadow_shutter_open_seconds_manual": 5,
                # "shadow_shutter_look_through_angle_entity":
                "shadow_shutter_look_through_angle_manual": 54,
                # "shadow_height_after_sun_entity":
                "shadow_height_after_sun_manual": 0,
                # "shadow_angle_after_sun_entity":
                "shadow_angle_after_sun_manual": 0,
                #
                # Dawn configuration
                # "dawn_control_enabled_entity":
                "dawn_control_enabled_manual": True,
                # "dawn_brightness_threshold_entity":
                "dawn_brightness_threshold_manual": 5000,
                # "dawn_after_seconds_entity":
                "dawn_after_seconds_manual": 5,
                # "dawn_shutter_max_height_entity": input_number.automation_dawn_max_height_sc_dummy
                "dawn_shutter_max_height_manual": 100,
                # "dawn_shutter_max_angle_entity": input_number.automation_dawn_max_angle_sc_dummy
                "dawn_shutter_max_angle_manual": 100,
                # "dawn_shutter_look_through_seconds_entity":
                "dawn_shutter_look_through_seconds_manual": 5,
                # "dawn_shutter_open_seconds_entity":
                "dawn_shutter_open_seconds_manual": 5,
                # "dawn_shutter_look_through_angle_entity":
                "dawn_shutter_look_through_angle_manual": 45,
                # "dawn_height_after_dawn_entity":
                "dawn_height_after_dawn_manual": 0,
                # "dawn_angle_after_dawn_entity":
                "dawn_angle_after_dawn_manual": 0,
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


async def test_debug_sun_update(
    hass: HomeAssistant,
    setup_from_user_config,
    update_sun,
    caplog,
):
    """Debug: Prüfe ob Sun Updates funktionieren."""

    caplog.set_level(logging.DEBUG)

    await setup_from_user_config(TEST_CONFIG)

    _LOGGER.info("=" * 80)
    _LOGGER.info("BEFORE SUN UPDATE:")
    _LOGGER.info("=" * 80)
    brightness = hass.states.get("input_number.d01_brightness")
    elevation = hass.states.get("input_number.d03_sun_elevation")
    azimuth = hass.states.get("input_number.d04_sun_azimuth")
    sc_state = hass.states.get("sensor.sc_dummy_state")

    _LOGGER.info("Brightness: %s", brightness.state if brightness else "NOT FOUND")
    _LOGGER.info("Elevation: %s", elevation.state if elevation else "NOT FOUND")
    _LOGGER.info("Azimuth: %s", azimuth.state if azimuth else "NOT FOUND")
    _LOGGER.info("SC State: %s", sc_state.state if sc_state else "NOT FOUND")

    # Update Sun
    await update_sun(elevation=60, azimuth=180, brightness=70000)

    _LOGGER.info("=" * 80)
    _LOGGER.info("AFTER SUN UPDATE:")
    _LOGGER.info("=" * 80)
    brightness = hass.states.get("input_number.d01_brightness")
    elevation = hass.states.get("input_number.d03_sun_elevation")
    azimuth = hass.states.get("input_number.d04_sun_azimuth")
    sc_state = hass.states.get("sensor.sc_dummy_state")

    _LOGGER.info("Brightness: %s", brightness.state if brightness else "NOT FOUND")
    _LOGGER.info("Elevation: %s", elevation.state if elevation else "NOT FOUND")
    _LOGGER.info("Azimuth: %s", azimuth.state if azimuth else "NOT FOUND")
    _LOGGER.info("SC State: %s", sc_state.state if sc_state else "NOT FOUND")

    # Prüfe ob Facade in Sun ist
    facade_in_sun = hass.states.get("binary_sensor.sc_dummy_facade_in_sun")
    if facade_in_sun:
        _LOGGER.info("Facade in Sun: %s, Attributes: %s", facade_in_sun.state, facade_in_sun.attributes)


async def test_timer_with_time_travel(
    hass: HomeAssistant,
    setup_from_user_config,
    update_sun,
    time_travel,
    caplog,
):
    """Test Timer mit Time Travel."""

    caplog.set_level(logging.DEBUG, logger="custom_components.shadow_control")

    await setup_from_user_config(TEST_CONFIG)
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    await hass.async_block_till_done()
    # Mocke die Cover-Dienste, damit das Dummy-Script gar nicht erst läuft
    tilt_calls = async_mock_service(hass, "cover", "set_cover_tilt_position")
    pos_calls = async_mock_service(hass, "cover", "set_cover_position")

    # Initial State
    sc_state = hass.states.get("sensor.tc_01_state")
    initial_state = sc_state.state
    _LOGGER.info("Initial State: %s", initial_state)

    # Trigger Shadow (sollte Timer starten)
    await update_sun(elevation=60, azimuth=180, brightness=70000)
    await hass.async_block_till_done()

    # Prüfe ob Timer gestartet wurde
    sc_state = hass.states.get("sensor.tc_01_state")
    _LOGGER.info("State after sun update: %s", sc_state.state)

    # Prüfe Timer Attribute (falls vorhanden)
    if "next_modification" in sc_state.attributes:
        _LOGGER.info("Next modification: %s", sc_state.attributes["next_modification"])

    # Time Travel - Spring über den Timer (5s Timer + 1s Buffer)
    _LOGGER.info("Time traveling 6 seconds...")
    await time_travel(seconds=6)

    # Prüfe dass Timer abgelaufen ist
    sc_state = hass.states.get("sensor.tc_01_state")
    _LOGGER.info("State after time travel: %s", sc_state.state)
    # _LOGGER.info("Attributes: %s", sc_state.attributes)

    # Der Timer sollte den State geändert haben
    assert sc_state.state != initial_state, f"State sollte sich geändert haben: {initial_state} -> {sc_state.state}"

    assert len(pos_calls) > 0
    assert pos_calls[-1].data["position"] == 0 # KNX: 100% geschlossen
    assert len(tilt_calls) > 0
    assert tilt_calls[-1].data["tilt_position"] == 100


# async def test_issue_123_shadow_not_activating(
#     hass: HomeAssistant,
#     setup_from_user_config,
#     time_travel,
#     update_sun,
#     caplog,
# ):
#     """Test Issue #123: Shadow Control aktiviert nicht bei Mittagssonne."""
#
#     caplog.set_level(logging.DEBUG)
#
#     await setup_from_user_config(TEST_CONFIG)
#
#     cover_state = hass.states.get("cover.tc_01")
#     initial_position = cover_state.attributes["current_position"]
#
#     await update_sun(elevation=60, azimuth=180, brightness=70000)
#     await time_travel(seconds=6)
#
#     sc_state = hass.states.get("sensor.tc_01_state")
#     assert sc_state is not None, "sensor.tc_01_state nicht gefunden"
#
#     # Debug Output
#     _LOGGER.info("SC State: %s", sc_state.state)
#     _LOGGER.info("SC Attributes: %s", sc_state.attributes)
#
#     facade_in_sun = hass.states.get("binary_sensor.tc_01_facade_in_sun")
#     if facade_in_sun:
#         _LOGGER.info("Facade in Sun: %s", facade_in_sun.state)
#
#     assert "neutral" in sc_state.state.lower(), f"Shadow sollte aktiv sein, ist aber: {sc_state.state}"
#
#     cover_state = hass.states.get("cover.tc_01")
#     new_position = cover_state.attributes["current_position"]
#     assert new_position != initial_position, "Cover Position sollte sich geändert haben"
#
#
# async def test_issue_123_timer_sequence(
#     hass: HomeAssistant,
#     setup_from_user_config,
#     time_travel,
#     update_sun,
# ):
#     """Test Timer-Sequenz: Shadow-After → Look-Through → Open."""
#
#     await setup_from_user_config(TEST_CONFIG)
#
#     # 1. Trigger Shadow Conditions
#     await update_sun(elevation=60, azimuth=180, brightness=70000)
#
#     # 2. Nach shadow_after_seconds (5s) sollte Shadow starten
#     await time_travel(seconds=6)
#
#     sc_state = hass.states.get("sensor.tc_01_state")
#     assert "shadow" in sc_state.state.lower()
#
#     # 3. Nach look_through_seconds (5s) sollte Look-Through aktiv sein
#     await time_travel(seconds=6)
#
#     sc_state = hass.states.get("sensor.tc_01_state")
#     # Je nach State-Namen
#     assert "look_through" in sc_state.state.lower() or "neutral" in sc_state.state.lower()
#
#     # 4. Nach open_seconds (5s) sollte wieder offen sein
#     await time_travel(seconds=6)
#
#     # TODO: Prüfe finale Position
#     # cover_state = hass.states.get("cover.tc_01")
#
#
# async def test_issue_123_dawn_sequence(
#     hass: HomeAssistant,
#     setup_from_user_config,
#     time_travel,
#     update_sun,
# ):
#     """Test Dawn-Sequenz mit Timern."""
#
#     await setup_from_user_config(TEST_CONFIG)
#
#     # Dawn Conditions: Niedrige Helligkeit
#     await update_sun(
#         elevation=10,
#         azimuth=90,  # Osten (Morgen)
#         brightness=4000,  # Unter Dawn-Threshold (5000)
#     )
#
#     # Nach dawn_after_seconds (5s)
#     await time_travel(seconds=6)
#
#     sc_state = hass.states.get("sensor.tc_01_state")
#     assert "dawn" in sc_state.state.lower()
#
#     # TODO: Assert basierend auf deiner Logik
#     # Cover sollte auf dawn_height_after_dawn (10%) sein
#     # expected_height = 10  # dawn_height_after_dawn_manual
#
#
# async def test_issue_123_no_timer_wait_with_time_travel(
#     hass: HomeAssistant,
#     setup_from_user_config,
#     time_travel,
#     update_sun,
# ):
#     """Zeige dass Time-Travel keine echte Wartezeit braucht."""
#
#     await setup_from_user_config(TEST_CONFIG)
#
#     start_time = real_time.time()
#
#     # Trigger Shadow
#     await update_sun(elevation=60, azimuth=180, brightness=70000)
#
#     # "Warte" 5 Sekunden (aber ohne echte Zeit)
#     await time_travel(seconds=6)
#
#     end_time = real_time.time()
#     elapsed = end_time - start_time
#
#     # Test sollte < 1 Sekunde dauern, nicht 5+
#     assert elapsed < 1.0, f"Test dauerte {elapsed}s - Time Travel funktioniert nicht!"
#
#     # Shadow sollte trotzdem aktiv sein
#     sc_state = hass.states.get("sensor.tc_01_state")
#     assert "shadow" in sc_state.state.lower()
