"""Integration Test: Komplette Shutter Automation."""

import logging
from itertools import count

import pytest
from homeassistant.core import HomeAssistant

from custom_components.shadow_control.const import DOMAIN, ShutterState
from tests.integration.conftest import (
    assert_equal,
    get_cover_position,
    get_entity_and_show_state,
    set_sun_position,
    setup_instance,
    show_instance_entity_states,
    time_travel_and_check,
)

_LOGGER = logging.getLogger(__name__)

TEST_CONFIG = {
    DOMAIN: [
        {
            "name": "SC Test Instance",
            "debug_enabled": False,
            # "debug_enabled": True,
            "target_cover_entity": ["cover.sc_dummy"],
            "facade_shutter_type_static": "mode1",
            #
            # Dynamic configuration inputs
            "brightness_entity": "input_number.d01_brightness",
            # "brightness_dawn_entity":
            "sun_elevation_entity": "input_number.d03_sun_elevation",
            "sun_azimuth_entity": "input_number.d04_sun_azimuth",
            "facade_azimuth_static": 180,
            "facade_offset_sun_in_static": -80,
            "facade_offset_sun_out_static": 80,
            "facade_elevation_sun_min_static": 10,
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
                "shadow_brightness_threshold_manual": 50000,
                # "shadow_after_seconds_entity":
                "shadow_after_seconds_manual": 10,
                # "shadow_shutter_max_height_entity": input_number.automation_shadow_max_height_sc_dummy
                "shadow_shutter_max_height_manual": 100,
                # "shadow_shutter_max_angle_entity": input_number.automation_shadow_max_angle_sc_dummy
                "shadow_shutter_max_angle_manual": 100,
                # "shadow_shutter_look_through_seconds_entity":
                "shadow_shutter_look_through_seconds_manual": 10,
                # "shadow_shutter_open_seconds_entity":
                "shadow_shutter_open_seconds_manual": 10,
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
                "dawn_brightness_threshold_manual": 500,
                # "dawn_after_seconds_entity":
                "dawn_after_seconds_manual": 10,
                # "dawn_shutter_max_height_entity": input_number.automation_dawn_max_height_sc_dummy
                "dawn_shutter_max_height_manual": 100,
                # "dawn_shutter_max_angle_entity": input_number.automation_dawn_max_angle_sc_dummy
                "dawn_shutter_max_angle_manual": 100,
                # "dawn_shutter_look_through_seconds_entity":
                "dawn_shutter_look_through_seconds_manual": 10,
                # "dawn_shutter_open_seconds_entity":
                "dawn_shutter_open_seconds_manual": 10,
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


async def test_show_setup(
    hass: HomeAssistant,
    setup_from_user_config,
    time_travel,
    caplog,
):
    """Not really a test but show whole instance configuration."""

    # Counter to distinct repeated outputs on the log
    step = count(1)

    # === INIT =====================================================================================
    _, _ = await setup_instance(caplog, hass, setup_from_user_config, TEST_CONFIG, time_travel)

    await show_instance_entity_states(hass, next(step))


@pytest.mark.parametrize(
    ("shutter_type", "check_angle"),
    [
        ("mode1", True),
        ("mode2", True),
        ("mode3", False),
    ],
)
async def test_increasing_sun_azimut(hass: HomeAssistant, setup_from_user_config, time_travel, caplog, shutter_type, check_angle):
    """Test that SC closes if sun azimut increases sun position through offset range."""
    # === INIT =====================================================================================
    config = {DOMAIN: [TEST_CONFIG[DOMAIN][0].copy()]}
    config[DOMAIN][0]["facade_shutter_type_static"] = shutter_type
    pos_calls, tilt_calls = await setup_instance(caplog, hass, setup_from_user_config, config, time_travel)

    # Initial instance state
    state1 = await get_entity_and_show_state(hass, "sensor.sc_test_instance_state")
    assert state1.state == ShutterState.NEUTRAL.name.lower()

    # === Set brightness above threshold and azimuth outside of offset =============================
    await set_sun_position(hass, elevation=60, azimuth=90, brightness=70000)

    state2 = await time_travel_and_check(
        time_travel, hass, "sensor.sc_test_instance_state", seconds=2, executions=2, pos_calls=pos_calls, tilt_calls=tilt_calls
    )

    # State should not have changed
    assert_equal(state2.state, state1.state, "Instance state")
    height, angle = get_cover_position(pos_calls, tilt_calls)
    assert_equal(height, "N/A", "SC height")
    if check_angle:
        assert_equal(angle, "N/A", "SC angle")

    # === Move sun into offset range ===============================================================
    await set_sun_position(hass, elevation=60, azimuth=180, brightness=70000)

    state3 = await time_travel_and_check(
        time_travel, hass, "sensor.sc_test_instance_state", seconds=2, executions=10, pos_calls=pos_calls, tilt_calls=tilt_calls
    )

    # State should have changed to SHADOW_FULL_CLOSED
    assert_equal(state3.state, ShutterState.SHADOW_FULL_CLOSED, "Instance state")
    height, angle = get_cover_position(pos_calls, tilt_calls)
    assert_equal(height, "0", "SC height")  # HA 0% == KNX 100%
    if check_angle:
        if shutter_type == "mode1":
            assert_equal(angle, "100", "SC angle")  # HA 100% == KNX 0%
        elif shutter_type == "mode2":
            assert_equal(angle, "65", "SC angle")  # HA 100% == KNX 0%

    # === Move sun out of offset range ===============================================================
    await set_sun_position(hass, elevation=60, azimuth=270, brightness=70000)

    state3 = await time_travel_and_check(
        time_travel, hass, "sensor.sc_test_instance_state", seconds=2, executions=10, pos_calls=pos_calls, tilt_calls=tilt_calls
    )

    # State should have changed back to NEUTRAL
    assert_equal(state3.state, ShutterState.NEUTRAL, "Instance state")
    height, angle = get_cover_position(pos_calls, tilt_calls)
    assert_equal(height, "100", "SC height")  # HA 100% == KNX 0%
    if check_angle and shutter_type in {"mode1", "mode2"}:
        assert_equal(angle, "100", "SC angle")  # HA 100% == KNX 0%


@pytest.mark.parametrize(
    ("shutter_type", "check_angle"),
    [
        ("mode1", True),
        ("mode2", True),
        ("mode3", False),
    ],
)
async def test_increasing_sun_elevation(hass: HomeAssistant, setup_from_user_config, time_travel, caplog, shutter_type, check_angle):
    """Test that SC closes if sun azimut increases sun position through offset range."""
    # === INIT =====================================================================================
    config = {DOMAIN: [TEST_CONFIG[DOMAIN][0].copy()]}
    config[DOMAIN][0]["facade_shutter_type_static"] = shutter_type
    pos_calls, tilt_calls = await setup_instance(caplog, hass, setup_from_user_config, config, time_travel)

    # Initial instance state
    state1 = await get_entity_and_show_state(hass, "sensor.sc_test_instance_state")
    assert state1.state == ShutterState.NEUTRAL.name.lower()

    # === Set brightness above threshold and elevation below min value =============================
    await set_sun_position(hass, elevation=10, azimuth=180, brightness=70000)

    state2 = await time_travel_and_check(
        time_travel, hass, "sensor.sc_test_instance_state", seconds=2, executions=2, pos_calls=pos_calls, tilt_calls=tilt_calls
    )

    # State should not have changed
    assert_equal(state2.state, state1.state, "Instance state")
    height, angle = get_cover_position(pos_calls, tilt_calls)
    assert_equal(height, "N/A", "SC height")
    if check_angle:
        assert_equal(angle, "N/A", "SC angle")

    # === Move sun into min-max range ==============================================================
    await set_sun_position(hass, elevation=60, azimuth=180, brightness=70000)

    state3 = await time_travel_and_check(
        time_travel, hass, "sensor.sc_test_instance_state", seconds=2, executions=10, pos_calls=pos_calls, tilt_calls=tilt_calls
    )

    # State should have changed to SHADOW_FULL_CLOSED
    assert_equal(state3.state, ShutterState.SHADOW_FULL_CLOSED, "Instance state")
    height, angle = get_cover_position(pos_calls, tilt_calls)
    assert_equal(height, "0", "SC height")  # HA 0% == KNX 100%
    if check_angle:
        if shutter_type == "mode1":
            assert_equal(angle, "100", "SC angle")  # HA 100% == KNX 0%
        elif shutter_type == "mode2":
            assert_equal(angle, "65", "SC angle")  # HA 100% == KNX 0%

    # === Move sun out of min-max range ============================================================
    await set_sun_position(hass, elevation=80, azimuth=180, brightness=70000)

    state3 = await time_travel_and_check(
        time_travel, hass, "sensor.sc_test_instance_state", seconds=2, executions=10, pos_calls=pos_calls, tilt_calls=tilt_calls
    )

    # State should have changed back to NEUTRAL
    assert_equal(state3.state, ShutterState.NEUTRAL, "Instance state")
    height, angle = get_cover_position(pos_calls, tilt_calls)
    assert_equal(height, "100", "SC height")  # HA 100% == KNX 0%
    if check_angle and shutter_type in {"mode1", "mode2"}:
        assert_equal(angle, "100", "SC angle")  # HA 100% == KNX 0%
