"""Integration Test: Dawn Time Constraints (open_not_before / close_not_later_than)."""

import logging
from datetime import timedelta
from itertools import count

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from custom_components.shadow_control.const import DOMAIN, SCInternal, ShutterState
from tests.integration.conftest import (
    set_sun_position,
    setup_instance,
    show_instance_entity_states,
    time_travel_and_check,
)

_LOGGER = logging.getLogger(__name__)

INSTANCE = "sc_test_instance"
STATE_ENTITY = f"sensor.{INSTANCE}_state"

# Sun position that puts the sun squarely in the south-facing facade
SUN_IN_FACADE = {"elevation": 60, "azimuth": 180}

# Brightness values relative to dawn_brightness_threshold_manual=500
BRIGHTNESS_BELOW_DAWN = 100  # < 500 -> Dawn triggers close
BRIGHTNESS_ABOVE_DAWN = 5000  # > 500 -> Dawn triggers open (from DAWN_FULL_CLOSED)


# =============================================================================
# Base configuration - Dawn active, shadow disabled, south-facing facade
# State path for closing:   NEUTRAL -> DAWN_FULL_CLOSE_TIMER_RUNNING -> DAWN_FULL_CLOSED
# State path for opening:   DAWN_FULL_CLOSED -> DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING
#                           -> DAWN_HORIZONTAL_NEUTRAL -> DAWN_NEUTRAL_TIMER_RUNNING
#                           -> DAWN_NEUTRAL
# =============================================================================
BASE_CONFIG = {
    DOMAIN: [
        {
            "name": "SC Test Instance",
            "debug_enabled": False,
            "target_cover_entity": ["cover.sc_dummy"],
            "facade_shutter_type_static": "mode1",
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
            "brightness_entity": "input_number.d01_brightness",
            "sun_elevation_entity": "input_number.d03_sun_elevation",
            "sun_azimuth_entity": "input_number.d04_sun_azimuth",
            "sunrise_entity": "input_datetime.sunrise",
            "sunset_entity": "input_datetime.sunset",
            "sc_internal_values": {
                "lock_integration_manual": False,
                "lock_integration_with_position_manual": False,
                "lock_height_manual": 50,
                "lock_angle_manual": 50,
                "movement_restriction_height_manual": "no_restriction",
                "movement_restriction_angle_manual": "no_restriction",
                "facade_neutral_pos_height_manual": 0,
                "facade_neutral_pos_angle_manual": 0,
                "enforce_positioning_manual": False,
                # Shadow: disabled
                "shadow_control_enabled_manual": False,
                "shadow_brightness_threshold_winter_manual": 50000,
                "shadow_brightness_threshold_summer_manual": 50000,
                "shadow_brightness_threshold_minimal_manual": 5000,
                "shadow_after_seconds_manual": 10,
                "shadow_shutter_max_height_manual": 100,
                "shadow_shutter_max_angle_manual": 100,
                "shadow_shutter_look_through_seconds_manual": 10,
                "shadow_shutter_open_seconds_manual": 10,
                "shadow_shutter_look_through_angle_manual": 54,
                "shadow_height_after_sun_manual": 0,
                "shadow_angle_after_sun_manual": 0,
                # Dawn: enabled, threshold=500 Lux, short timers for tests
                "dawn_control_enabled_manual": True,
                "dawn_brightness_threshold_manual": 500,
                "dawn_after_seconds_manual": 5,
                "dawn_shutter_max_height_manual": 100,
                "dawn_shutter_max_angle_manual": 0,
                "dawn_shutter_look_through_seconds_manual": 5,
                "dawn_shutter_open_seconds_manual": 5,
                "dawn_shutter_look_through_angle_manual": 45,
                "dawn_height_after_dawn_manual": 0,
                "dawn_angle_after_dawn_manual": 0,
            },
        }
    ]
}


# =============================================================================
# Helpers
# =============================================================================


def _offset_hhmm(hass: HomeAssistant, minutes: int) -> str:
    """Return simulated HA time offset by `minutes` as HH:MM string."""
    # Convert string to tzinfo object
    tz = dt_util.get_time_zone(hass.config.time_zone)
    # Get now with the proper tzinfo
    now = dt_util.now(tz)
    t = now + timedelta(minutes=minutes)
    return t.strftime("%H:%M")


async def _set_time_constraint(hass: HomeAssistant, internal_enum: SCInternal, value: str) -> None:
    """Set a dawn time constraint (TextEntity under Platform.TEXT) to a HH:MM value."""
    registry = er.async_get(hass)
    entity_id = None
    for entry in registry.entities.values():
        if entry.platform == "shadow_control" and internal_enum.value in entry.unique_id and INSTANCE.lower() in entry.entity_id.lower():
            entity_id = entry.entity_id
            break

    if not entity_id:
        msg = f"Could not find time constraint entity for {internal_enum.name}"
        raise ValueError(msg)

    # TimeEntity service expects HH:MM:SS format
    hhmm_len = 5
    time_value = value + ":00" if len(value) == hhmm_len else value
    await hass.services.async_call("time", "set_value", {"entity_id": entity_id, "time": str(time_value)}, blocking=True)
    await hass.async_block_till_done()
    _LOGGER.info("Set %s = %s", entity_id, value)


async def _skip_grace_period(hass, time_travel, pos_calls, tilt_calls) -> None:
    """Travel past the 30s HA restart grace period before running dawn tests.

    Without this, timer callbacks are skipped and states never transition.
    Uses 2s steps to ensure async_fire_time_changed triggers properly.
    """
    await time_travel_and_check(
        time_travel,
        hass,
        STATE_ENTITY,
        seconds=2,
        executions=16,  # 32s > 30s grace period
        pos_calls=pos_calls,
        tilt_calls=tilt_calls,
    )


async def _drive_to_dawn_full_closed(hass, time_travel, pos_calls, tilt_calls) -> None:
    """Drive state machine: NEUTRAL -> DAWN_FULL_CLOSE_TIMER_RUNNING -> DAWN_FULL_CLOSED.

    Requires brightness < threshold (100 < 500) with sun in facade.
    Timer fires after 5 seconds (dawn_after_seconds_manual).
    """
    await set_sun_position(hass, brightness=BRIGHTNESS_BELOW_DAWN, **SUN_IN_FACADE)
    # First pass: enter DAWN_FULL_CLOSE_TIMER_RUNNING
    await time_travel_and_check(
        time_travel,
        hass,
        STATE_ENTITY,
        seconds=2,
        executions=12,
        pos_calls=pos_calls,
        tilt_calls=tilt_calls,
    )
    # Second pass: let timer fire -> DAWN_FULL_CLOSED
    await time_travel_and_check(
        time_travel,
        hass,
        STATE_ENTITY,
        seconds=2,
        executions=12,
        pos_calls=pos_calls,
        tilt_calls=tilt_calls,
    )


async def _drive_to_dawn_neutral(hass, time_travel, pos_calls, tilt_calls) -> None:
    """Drive state machine: DAWN_FULL_CLOSED -> ... -> DAWN_NEUTRAL (full opening path).

    Path: DAWN_FULL_CLOSED -> DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING (5s)
          -> DAWN_HORIZONTAL_NEUTRAL -> DAWN_NEUTRAL_TIMER_RUNNING (5s) -> DAWN_NEUTRAL
    Each timer step needs 5 seconds to fire.
    """
    await set_sun_position(hass, brightness=BRIGHTNESS_ABOVE_DAWN, **SUN_IN_FACADE)
    # First timer: DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING -> DAWN_HORIZONTAL_NEUTRAL
    await time_travel_and_check(
        time_travel,
        hass,
        STATE_ENTITY,
        seconds=2,
        executions=12,
        pos_calls=pos_calls,
        tilt_calls=tilt_calls,
    )
    # Second timer: DAWN_NEUTRAL_TIMER_RUNNING -> DAWN_NEUTRAL
    await time_travel_and_check(
        time_travel,
        hass,
        STATE_ENTITY,
        seconds=2,
        executions=12,
        pos_calls=pos_calls,
        tilt_calls=tilt_calls,
    )


# =============================================================================
# Tests
# =============================================================================


async def test_show_dawn_time_constraint_setup(
    hass: HomeAssistant,
    setup_from_user_config,
    time_travel,
    caplog,
):
    """Show all entity states after setup - useful for debugging."""
    step = count(1)
    config = {DOMAIN: [BASE_CONFIG[DOMAIN][0].copy()]}
    _, _ = await setup_instance(caplog, hass, setup_from_user_config, config, time_travel)
    await show_instance_entity_states(hass, next(step))


async def test_dawn_closes_from_neutral_at_low_brightness(
    hass: HomeAssistant,
    setup_from_user_config,
    time_travel,
    caplog,
):
    """Baseline: NEUTRAL -> DAWN_FULL_CLOSED when brightness is below dawn threshold."""
    config = {DOMAIN: [BASE_CONFIG[DOMAIN][0].copy()]}
    pos_calls, tilt_calls = await setup_instance(
        caplog,
        hass,
        setup_from_user_config,
        config,
        time_travel,
    )

    # Skip 30s HA restart grace period so timer callbacks are not suppressed
    await _skip_grace_period(hass, time_travel, pos_calls, tilt_calls)

    # Skip 30s HA restart grace period so timer callbacks are not suppressed
    await _skip_grace_period(hass, time_travel, pos_calls, tilt_calls)

    state = hass.states.get(STATE_ENTITY)
    assert state.state == ShutterState.NEUTRAL.name.lower()

    # Low brightness triggers DAWN_FULL_CLOSE_TIMER_RUNNING immediately
    await set_sun_position(hass, brightness=BRIGHTNESS_BELOW_DAWN, **SUN_IN_FACADE)
    state = await time_travel_and_check(
        time_travel,
        hass,
        STATE_ENTITY,
        seconds=2,
        executions=12,
        pos_calls=pos_calls,
        tilt_calls=tilt_calls,
    )
    assert state.state in (
        ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING.name.lower(),
        ShutterState.DAWN_FULL_CLOSED.name.lower(),
    ), f"Expected close timer or closed, got: {state.state}"

    # Let timer fire -> DAWN_FULL_CLOSED
    state = await time_travel_and_check(
        time_travel,
        hass,
        STATE_ENTITY,
        seconds=2,
        executions=12,
        pos_calls=pos_calls,
        tilt_calls=tilt_calls,
    )
    assert state.state == ShutterState.DAWN_FULL_CLOSED.name.lower(), f"Expected DAWN_FULL_CLOSED after timer, got: {state.state}"


async def test_dawn_opens_fully_to_dawn_neutral(
    hass: HomeAssistant,
    setup_from_user_config,
    time_travel,
    caplog,
):
    """Baseline: full opening path DAWN_FULL_CLOSED -> DAWN_NEUTRAL."""
    config = {DOMAIN: [BASE_CONFIG[DOMAIN][0].copy()]}
    pos_calls, tilt_calls = await setup_instance(
        caplog,
        hass,
        setup_from_user_config,
        config,
        time_travel,
    )

    # Skip 30s HA restart grace period so timer callbacks are not suppressed
    await _skip_grace_period(hass, time_travel, pos_calls, tilt_calls)

    # First close
    await _drive_to_dawn_full_closed(hass, time_travel, pos_calls, tilt_calls)
    state = hass.states.get(STATE_ENTITY)
    assert state.state == ShutterState.DAWN_FULL_CLOSED.name.lower(), f"Setup: expected DAWN_FULL_CLOSED, got: {state.state}"

    # Then open fully
    await _drive_to_dawn_neutral(hass, time_travel, pos_calls, tilt_calls)
    state = hass.states.get(STATE_ENTITY)
    assert state.state == ShutterState.DAWN_NEUTRAL.name.lower(), f"Expected DAWN_NEUTRAL after full open path, got: {state.state}"


async def test_close_not_later_than_triggers_close_from_dawn_neutral(
    hass: HomeAssistant,
    setup_from_user_config,
    time_travel,
    caplog,
):
    """close_not_later_than past time triggers close from DAWN_NEUTRAL despite high brightness."""
    config = {DOMAIN: [BASE_CONFIG[DOMAIN][0].copy()]}
    pos_calls, tilt_calls = await setup_instance(
        caplog,
        hass,
        setup_from_user_config,
        config,
        time_travel,
    )

    # Skip 30s HA restart grace period so timer callbacks are not suppressed
    await _skip_grace_period(hass, time_travel, pos_calls, tilt_calls)

    # Navigate to DAWN_NEUTRAL (close -> open fully)
    await _drive_to_dawn_full_closed(hass, time_travel, pos_calls, tilt_calls)
    await _drive_to_dawn_neutral(hass, time_travel, pos_calls, tilt_calls)
    state = hass.states.get(STATE_ENTITY)
    assert state.state == ShutterState.DAWN_NEUTRAL.name.lower(), f"Setup: expected DAWN_NEUTRAL, got: {state.state}"

    # 1. Set the close constraint to the PAST
    await _set_time_constraint(hass, SCInternal.DAWN_CLOSE_NOT_LATER_THAN_MANUAL, _offset_hhmm(hass, -5))

    # 2. Set the open constraint to the FUTURE to prevent oscillation
    # This ensures that once it closes due to time, it stays closed
    await _set_time_constraint(hass, SCInternal.DAWN_OPEN_NOT_BEFORE_MANUAL, _offset_hhmm(hass, 60))

    await hass.async_block_till_done()

    # 3. POKE: Force re-evaluation
    await set_sun_position(hass, brightness=BRIGHTNESS_ABOVE_DAWN, **SUN_IN_FACADE)
    await hass.async_block_till_done()

    # 4. Travel: Now it should close and STAY closed
    state = await time_travel_and_check(
        time_travel,
        hass,
        STATE_ENTITY,
        seconds=2,
        executions=15,
        pos_calls=pos_calls,
        tilt_calls=tilt_calls,
    )

    assert state.state in (
        ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING.name.lower(),
        ShutterState.DAWN_FULL_CLOSED.name.lower(),
    )


async def test_close_not_later_than_future_does_not_trigger(
    hass: HomeAssistant,
    setup_from_user_config,
    time_travel,
    caplog,
):
    """close_not_later_than future time has no effect in DAWN_NEUTRAL."""
    config = {DOMAIN: [BASE_CONFIG[DOMAIN][0].copy()]}
    pos_calls, tilt_calls = await setup_instance(
        caplog,
        hass,
        setup_from_user_config,
        config,
        time_travel,
    )

    # Skip 30s HA restart grace period so timer callbacks are not suppressed
    await _skip_grace_period(hass, time_travel, pos_calls, tilt_calls)

    # Navigate to DAWN_NEUTRAL
    await _drive_to_dawn_full_closed(hass, time_travel, pos_calls, tilt_calls)
    await _drive_to_dawn_neutral(hass, time_travel, pos_calls, tilt_calls)
    state = hass.states.get(STATE_ENTITY)
    assert state.state == ShutterState.DAWN_NEUTRAL.name.lower(), f"Setup: expected DAWN_NEUTRAL, got: {state.state}"

    # Future close constraint -> no effect
    await _set_time_constraint(hass, SCInternal.DAWN_CLOSE_NOT_LATER_THAN_MANUAL, _offset_hhmm(hass, 60))

    state = await time_travel_and_check(
        time_travel,
        hass,
        STATE_ENTITY,
        seconds=2,
        executions=12,
        pos_calls=pos_calls,
        tilt_calls=tilt_calls,
    )
    assert state.state == ShutterState.DAWN_NEUTRAL.name.lower(), f"Should stay DAWN_NEUTRAL with future constraint, got: {state.state}"


async def test_open_not_before_future_blocks_opening_from_dawn_full_closed(
    hass: HomeAssistant,
    setup_from_user_config,
    time_travel,
    caplog,
):
    """open_not_before future time blocks re-opening from DAWN_FULL_CLOSED."""
    config = {DOMAIN: [BASE_CONFIG[DOMAIN][0].copy()]}
    pos_calls, tilt_calls = await setup_instance(
        caplog,
        hass,
        setup_from_user_config,
        config,
        time_travel,
    )

    # Skip 30s HA restart grace period so timer callbacks are not suppressed
    await _skip_grace_period(hass, time_travel, pos_calls, tilt_calls)

    # Close first
    await _drive_to_dawn_full_closed(hass, time_travel, pos_calls, tilt_calls)
    state = hass.states.get(STATE_ENTITY)
    assert state.state == ShutterState.DAWN_FULL_CLOSED.name.lower(), f"Setup: expected DAWN_FULL_CLOSED, got: {state.state}"

    # Set open_not_before to future
    await _set_time_constraint(hass, SCInternal.DAWN_OPEN_NOT_BEFORE_MANUAL, _offset_hhmm(hass, 60))

    # High brightness -> normally would start open timer, but constraint blocks it
    await set_sun_position(hass, brightness=BRIGHTNESS_ABOVE_DAWN, **SUN_IN_FACADE)
    state = await time_travel_and_check(
        time_travel,
        hass,
        STATE_ENTITY,
        seconds=2,
        executions=12,
        pos_calls=pos_calls,
        tilt_calls=tilt_calls,
    )
    assert state.state == ShutterState.DAWN_FULL_CLOSED.name.lower(), f"Should stay DAWN_FULL_CLOSED with future open_not_before, got: {state.state}"


async def test_open_not_before_past_allows_opening(
    hass: HomeAssistant,
    setup_from_user_config,
    time_travel,
    caplog,
):
    """open_not_before past time allows normal opening from DAWN_FULL_CLOSED."""
    config = {DOMAIN: [BASE_CONFIG[DOMAIN][0].copy()]}
    pos_calls, tilt_calls = await setup_instance(
        caplog,
        hass,
        setup_from_user_config,
        config,
        time_travel,
    )

    # Skip 30s HA restart grace period so timer callbacks are not suppressed
    await _skip_grace_period(hass, time_travel, pos_calls, tilt_calls)

    # Close first
    await _drive_to_dawn_full_closed(hass, time_travel, pos_calls, tilt_calls)
    state = hass.states.get(STATE_ENTITY)
    assert state.state == ShutterState.DAWN_FULL_CLOSED.name.lower(), f"Setup: expected DAWN_FULL_CLOSED, got: {state.state}"

    # Past open_not_before -> opening is allowed
    await _set_time_constraint(hass, SCInternal.DAWN_OPEN_NOT_BEFORE_MANUAL, _offset_hhmm(hass, -5))

    await set_sun_position(hass, brightness=BRIGHTNESS_ABOVE_DAWN, **SUN_IN_FACADE)
    state = await time_travel_and_check(
        time_travel,
        hass,
        STATE_ENTITY,
        seconds=2,
        executions=12,
        pos_calls=pos_calls,
        tilt_calls=tilt_calls,
    )
    assert state.state in (
        ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING.name.lower(),
        ShutterState.DAWN_HORIZONTAL_NEUTRAL.name.lower(),
        ShutterState.DAWN_NEUTRAL_TIMER_RUNNING.name.lower(),
        ShutterState.DAWN_NEUTRAL.name.lower(),
    ), f"Expected opening state with past open_not_before, got: {state.state}"


async def test_both_constraints_combined(
    hass: HomeAssistant,
    setup_from_user_config,
    time_travel,
    caplog,
):
    """close_not_later_than forces close from DAWN_NEUTRAL, open_not_before keeps closed."""
    config = {DOMAIN: [BASE_CONFIG[DOMAIN][0].copy()]}
    pos_calls, tilt_calls = await setup_instance(
        caplog,
        hass,
        setup_from_user_config,
        config,
        time_travel,
    )

    # Skip 30s HA restart grace period so timer callbacks are not suppressed
    await _skip_grace_period(hass, time_travel, pos_calls, tilt_calls)

    # Navigate to DAWN_NEUTRAL
    await _drive_to_dawn_full_closed(hass, time_travel, pos_calls, tilt_calls)
    await _drive_to_dawn_neutral(hass, time_travel, pos_calls, tilt_calls)
    state = hass.states.get(STATE_ENTITY)
    assert state.state == ShutterState.DAWN_NEUTRAL.name.lower(), f"Setup: expected DAWN_NEUTRAL, got: {state.state}"

    # Past close -> forces close; future open -> keeps closed
    await _set_time_constraint(hass, SCInternal.DAWN_CLOSE_NOT_LATER_THAN_MANUAL, _offset_hhmm(hass, -5))
    await _set_time_constraint(hass, SCInternal.DAWN_OPEN_NOT_BEFORE_MANUAL, _offset_hhmm(hass, 60))

    # Poke to trigger re-evaluation (constraints alone don't trigger state_changed)
    await set_sun_position(hass, brightness=BRIGHTNESS_ABOVE_DAWN, **SUN_IN_FACADE)
    await hass.async_block_till_done()

    # First pass: enter DAWN_FULL_CLOSE_TIMER_RUNNING
    await time_travel_and_check(
        time_travel,
        hass,
        STATE_ENTITY,
        seconds=2,
        executions=12,
        pos_calls=pos_calls,
        tilt_calls=tilt_calls,
    )
    # Second pass: timer fires -> DAWN_FULL_CLOSED
    state = await time_travel_and_check(
        time_travel,
        hass,
        STATE_ENTITY,
        seconds=2,
        executions=12,
        pos_calls=pos_calls,
        tilt_calls=tilt_calls,
    )
    assert state.state == ShutterState.DAWN_FULL_CLOSED.name.lower(), f"Expected DAWN_FULL_CLOSED with both constraints, got: {state.state}"

    # Verify: high brightness does NOT reopen (open_not_before still future)
    await set_sun_position(hass, brightness=BRIGHTNESS_ABOVE_DAWN, **SUN_IN_FACADE)
    state = await time_travel_and_check(
        time_travel,
        hass,
        STATE_ENTITY,
        seconds=2,
        executions=12,
        pos_calls=pos_calls,
        tilt_calls=tilt_calls,
    )
    assert state.state == ShutterState.DAWN_FULL_CLOSED.name.lower(), f"Should stay closed: open_not_before not reached, got: {state.state}"


async def test_close_constraint_keeps_timer_running_despite_brightness_recovery(
    hass: HomeAssistant,
    setup_from_user_config,
    time_travel,
    caplog,
):
    """close_not_later_than keeps DAWN_FULL_CLOSED stable even at high brightness.

    Without the constraint, high brightness in DAWN_FULL_CLOSED triggers re-opening.
    With past close_not_later_than, the shutter stays at DAWN_FULL_CLOSED regardless
    of brightness (fixed in _handle_state_dawn_full_closed).
    """
    config = {DOMAIN: [BASE_CONFIG[DOMAIN][0].copy()]}
    pos_calls, tilt_calls = await setup_instance(
        caplog,
        hass,
        setup_from_user_config,
        config,
        time_travel,
    )

    # Skip 30s HA restart grace period so timer callbacks are not suppressed
    await _skip_grace_period(hass, time_travel, pos_calls, tilt_calls)

    # Close first
    await _drive_to_dawn_full_closed(hass, time_travel, pos_calls, tilt_calls)
    state = hass.states.get(STATE_ENTITY)
    assert state.state == ShutterState.DAWN_FULL_CLOSED.name.lower(), f"Setup: expected DAWN_FULL_CLOSED, got: {state.state}"

    # Set past close_not_later_than (no open_not_before needed - fix blocks re-opening via close constraint)
    await _set_time_constraint(hass, SCInternal.DAWN_CLOSE_NOT_LATER_THAN_MANUAL, _offset_hhmm(hass, -5))
    await hass.async_block_till_done()

    # High brightness would normally trigger re-opening, but close constraint blocks it
    await set_sun_position(hass, brightness=BRIGHTNESS_ABOVE_DAWN, **SUN_IN_FACADE)
    state = await time_travel_and_check(
        time_travel,
        hass,
        STATE_ENTITY,
        seconds=2,
        executions=12,
        pos_calls=pos_calls,
        tilt_calls=tilt_calls,
    )
    assert state.state == ShutterState.DAWN_FULL_CLOSED.name.lower(), (
        f"close_not_later_than should keep DAWN_FULL_CLOSED despite high brightness, got: {state.state}"
    )


async def test_open_not_before_past_allows_full_open_to_dawn_neutral(
    hass: HomeAssistant,
    setup_from_user_config,
    time_travel,
    caplog,
):
    """open_not_before past time allows full opening path through DAWN_HORIZONTAL_NEUTRAL to DAWN_NEUTRAL.

    Note: Due to the recursive state machine, open_not_before is checked in DAWN_FULL_CLOSED
    and DAWN_HORIZONTAL_NEUTRAL within the same calculation pass. Setting a future constraint
    blocks at DAWN_FULL_CLOSED (already tested in test_open_not_before_future_blocks_opening).
    This test verifies the complementary case: past open_not_before allows the full open path.
    """
    config = {DOMAIN: [BASE_CONFIG[DOMAIN][0].copy()]}
    pos_calls, tilt_calls = await setup_instance(
        caplog,
        hass,
        setup_from_user_config,
        config,
        time_travel,
    )

    # Skip 30s HA restart grace period so timer callbacks are not suppressed
    await _skip_grace_period(hass, time_travel, pos_calls, tilt_calls)

    # Close first
    await _drive_to_dawn_full_closed(hass, time_travel, pos_calls, tilt_calls)
    state = hass.states.get(STATE_ENTITY)
    assert state.state == ShutterState.DAWN_FULL_CLOSED.name.lower(), f"Setup: expected DAWN_FULL_CLOSED, got: {state.state}"

    # Set open_not_before to PAST -> opening is explicitly permitted
    await _set_time_constraint(hass, SCInternal.DAWN_OPEN_NOT_BEFORE_MANUAL, _offset_hhmm(hass, -5))
    await hass.async_block_till_done()

    # Full opening path: DAWN_FULL_CLOSED -> DAWN_HORIZONTAL_NEUTRAL -> DAWN_NEUTRAL
    await set_sun_position(hass, brightness=BRIGHTNESS_ABOVE_DAWN, **SUN_IN_FACADE)
    # First timer (5s): DAWN_FULL_CLOSED -> DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING -> DAWN_HORIZONTAL_NEUTRAL
    await time_travel_and_check(
        time_travel,
        hass,
        STATE_ENTITY,
        seconds=2,
        executions=12,
        pos_calls=pos_calls,
        tilt_calls=tilt_calls,
    )
    # Second timer (5s): DAWN_HORIZONTAL_NEUTRAL -> DAWN_NEUTRAL_TIMER_RUNNING -> DAWN_NEUTRAL
    state = await time_travel_and_check(
        time_travel,
        hass,
        STATE_ENTITY,
        seconds=2,
        executions=12,
        pos_calls=pos_calls,
        tilt_calls=tilt_calls,
    )
    assert state.state == ShutterState.DAWN_NEUTRAL.name.lower(), (
        f"Past open_not_before should allow full open path to DAWN_NEUTRAL, got: {state.state}"
    )
