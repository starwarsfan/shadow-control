"""Integration Test: Komplette Shutter Automation."""

import logging
from itertools import count

from homeassistant.core import HomeAssistant

from custom_components.shadow_control import LockState
from custom_components.shadow_control.const import DOMAIN
from tests.integration.conftest import (
    assert_equal,
    get_entity_and_show_state,
    set_lock_state,
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
            # "debug_enabled": False,
            "debug_enabled": True,
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


async def test_lock(
    hass: HomeAssistant,
    setup_from_user_config,
    update_sun,
    time_travel,
    caplog,
):
    """Test Timer mit Time Travel."""

    # Counter to distinct repeated outputs on the log
    step = count(1)

    # === INIT =====================================================================================
    pos_calls, tilt_calls = await setup_instance(caplog, hass, setup_from_user_config, TEST_CONFIG)

    await show_instance_entity_states(hass, next(step))

    _ = await get_entity_and_show_state(hass, "sensor.sc_test_instance_state")
    _ = await time_travel_and_check(
        time_travel, hass, "sensor.sc_test_instance_state", seconds=2, executions=2, pos_calls=pos_calls, tilt_calls=tilt_calls
    )

    state1 = await get_entity_and_show_state(hass, "sensor.sc_test_instance_lock_state")
    assert_equal(state1.state, LockState.UNLOCKED, "Lock state")

    await set_lock_state(hass, "sc_test_instance", lock=True)
    await hass.async_block_till_done()

    _ = await get_entity_and_show_state(hass, "sensor.sc_test_instance_lock_state")
    _ = await time_travel_and_check(
        time_travel, hass, "sensor.sc_test_instance_lock_state", seconds=2, executions=8, pos_calls=pos_calls, tilt_calls=tilt_calls
    )

    current_brightness = hass.states.get("input_number.d01_brightness")
    if current_brightness:
        new_brightness = float(current_brightness.state) + 0.1
        await set_sun_position(hass, brightness=new_brightness)  # Minimal ändern

    state2 = await time_travel_and_check(
        time_travel, hass, "sensor.sc_test_instance_lock_state", seconds=2, executions=8, pos_calls=pos_calls, tilt_calls=tilt_calls
    )
    assert_equal(state2.state, LockState.LOCKED_MANUALLY, "Lock state")


async def test_lock_with_position(
    hass: HomeAssistant,
    setup_from_user_config,
    update_sun,
    time_travel,
    caplog,
):
    """Test Timer mit Time Travel."""

    # Counter to distinct repeated outputs on the log
    step = count(1)

    # === INIT =====================================================================================
    pos_calls, tilt_calls = await setup_instance(caplog, hass, setup_from_user_config, TEST_CONFIG)

    await show_instance_entity_states(hass, next(step))

    _ = await get_entity_and_show_state(hass, "sensor.sc_test_instance_state")
    _ = await time_travel_and_check(
        time_travel, hass, "sensor.sc_test_instance_state", seconds=2, executions=2, pos_calls=pos_calls, tilt_calls=tilt_calls
    )

    state1 = await get_entity_and_show_state(hass, "sensor.sc_test_instance_lock_state")
    assert_equal(state1.state, LockState.UNLOCKED, "Lock state")

    await set_lock_state(hass, "sc_test_instance", lock_with_position=True)
    await hass.async_block_till_done()

    _ = await get_entity_and_show_state(hass, "sensor.sc_test_instance_lock_state")
    _ = await time_travel_and_check(
        time_travel, hass, "sensor.sc_test_instance_lock_state", seconds=2, executions=8, pos_calls=pos_calls, tilt_calls=tilt_calls
    )

    current_brightness = hass.states.get("input_number.d01_brightness")
    if current_brightness:
        new_brightness = float(current_brightness.state) + 0.1
        await set_sun_position(hass, brightness=new_brightness)  # Minimal ändern

    state2 = await time_travel_and_check(
        time_travel, hass, "sensor.sc_test_instance_lock_state", seconds=2, executions=8, pos_calls=pos_calls, tilt_calls=tilt_calls
    )
    assert_equal(state2.state, LockState.LOCKED_MANUALLY_WITH_FORCED_POSITION, "Lock state")


async def test_lock_then_lock_with_position(
    hass: HomeAssistant,
    setup_from_user_config,
    update_sun,
    time_travel,
    caplog,
):
    """Test Timer mit Time Travel."""

    # Counter to distinct repeated outputs on the log
    step = count(1)

    # === INIT =====================================================================================
    pos_calls, tilt_calls = await setup_instance(caplog, hass, setup_from_user_config, TEST_CONFIG)

    await show_instance_entity_states(hass, next(step))

    _ = await get_entity_and_show_state(hass, "sensor.sc_test_instance_state")
    _ = await time_travel_and_check(
        time_travel, hass, "sensor.sc_test_instance_state", seconds=2, executions=2, pos_calls=pos_calls, tilt_calls=tilt_calls
    )

    state1 = await get_entity_and_show_state(hass, "sensor.sc_test_instance_lock_state")
    assert_equal(state1.state, LockState.UNLOCKED, "Lock state")

    await set_lock_state(hass, "sc_test_instance", lock=True)
    await hass.async_block_till_done()

    _ = await get_entity_and_show_state(hass, "sensor.sc_test_instance_lock_state")
    _ = await time_travel_and_check(
        time_travel, hass, "sensor.sc_test_instance_lock_state", seconds=2, executions=8, pos_calls=pos_calls, tilt_calls=tilt_calls
    )

    current_brightness = hass.states.get("input_number.d01_brightness")
    if current_brightness:
        new_brightness = float(current_brightness.state) + 0.1
        await set_sun_position(hass, brightness=new_brightness)  # Minimal ändern

    state2 = await time_travel_and_check(
        time_travel, hass, "sensor.sc_test_instance_lock_state", seconds=2, executions=8, pos_calls=pos_calls, tilt_calls=tilt_calls
    )
    assert_equal(state2.state, LockState.LOCKED_MANUALLY, "Lock state")

    await set_lock_state(hass, "sc_test_instance", lock_with_position=True)
    await hass.async_block_till_done()

    _ = await get_entity_and_show_state(hass, "sensor.sc_test_instance_lock_state")
    _ = await time_travel_and_check(
        time_travel, hass, "sensor.sc_test_instance_lock_state", seconds=2, executions=8, pos_calls=pos_calls, tilt_calls=tilt_calls
    )

    current_brightness = hass.states.get("input_number.d01_brightness")
    if current_brightness:
        new_brightness = float(current_brightness.state) + 0.1
        await set_sun_position(hass, brightness=new_brightness)  # Minimal ändern

    state3 = await time_travel_and_check(
        time_travel, hass, "sensor.sc_test_instance_lock_state", seconds=2, executions=8, pos_calls=pos_calls, tilt_calls=tilt_calls
    )
    assert_equal(state3.state, LockState.LOCKED_MANUALLY_WITH_FORCED_POSITION, "Lock state")


async def test_lock_with_position_then_lock(
    hass: HomeAssistant,
    setup_from_user_config,
    update_sun,
    time_travel,
    caplog,
):
    """Test Timer mit Time Travel."""

    # Counter to distinct repeated outputs on the log
    step = count(1)

    # === INIT =====================================================================================
    pos_calls, tilt_calls = await setup_instance(caplog, hass, setup_from_user_config, TEST_CONFIG)

    await show_instance_entity_states(hass, next(step))

    _ = await get_entity_and_show_state(hass, "sensor.sc_test_instance_state")
    _ = await time_travel_and_check(
        time_travel, hass, "sensor.sc_test_instance_state", seconds=2, executions=2, pos_calls=pos_calls, tilt_calls=tilt_calls
    )

    state1 = await get_entity_and_show_state(hass, "sensor.sc_test_instance_lock_state")
    assert_equal(state1.state, LockState.UNLOCKED, "Lock state")

    await set_lock_state(hass, "sc_test_instance", lock_with_position=True)
    await hass.async_block_till_done()

    _ = await get_entity_and_show_state(hass, "sensor.sc_test_instance_lock_state")
    _ = await time_travel_and_check(
        time_travel, hass, "sensor.sc_test_instance_lock_state", seconds=2, executions=8, pos_calls=pos_calls, tilt_calls=tilt_calls
    )

    current_brightness = hass.states.get("input_number.d01_brightness")
    if current_brightness:
        new_brightness = float(current_brightness.state) + 0.1
        await set_sun_position(hass, brightness=new_brightness)  # Minimal ändern

    state2 = await time_travel_and_check(
        time_travel, hass, "sensor.sc_test_instance_lock_state", seconds=2, executions=8, pos_calls=pos_calls, tilt_calls=tilt_calls
    )
    assert_equal(state2.state, LockState.LOCKED_MANUALLY_WITH_FORCED_POSITION, "Lock state")

    await set_lock_state(hass, "sc_test_instance", lock=True)
    await hass.async_block_till_done()

    _ = await get_entity_and_show_state(hass, "sensor.sc_test_instance_lock_state")
    _ = await time_travel_and_check(
        time_travel, hass, "sensor.sc_test_instance_lock_state", seconds=2, executions=8, pos_calls=pos_calls, tilt_calls=tilt_calls
    )

    current_brightness = hass.states.get("input_number.d01_brightness")
    if current_brightness:
        new_brightness = float(current_brightness.state) + 0.1
        await set_sun_position(hass, brightness=new_brightness)  # Minimal ändern

    state3 = await time_travel_and_check(
        time_travel, hass, "sensor.sc_test_instance_lock_state", seconds=2, executions=8, pos_calls=pos_calls, tilt_calls=tilt_calls
    )
    assert_equal(state3.state, LockState.LOCKED_MANUALLY_WITH_FORCED_POSITION, "Lock state")
