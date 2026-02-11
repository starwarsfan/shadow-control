"""Integration Test: Komplette Shutter Automation."""

import logging
from itertools import count

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.shadow_control import LockState
from custom_components.shadow_control.const import DOMAIN
from tests.integration.conftest import (
    assert_equal,
    get_actual_cover_position,
    get_cover_position,
    get_entity_and_show_state,
    set_lock_state,
    set_sun_position,
    setup_instance,
    show_instance_entity_states,
    simulate_manual_cover_change,
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
            # "sunrise_entity": "input_number.sunrise",
            # "sunset_entity": "input_number.sunset",
            "facade_azimuth_static": 96,
            "facade_offset_sun_in_static": -86,
            "facade_offset_sun_out_static": 86,
            "facade_elevation_sun_min_static": 18,
            "facade_elevation_sun_max_static": 90,
            "facade_shutter_stepping_height_static": 5,
            "facade_light_strip_width_static": 0,
            "facade_shutter_height_static": 1000,
            "facade_neutral_pos_height_manual": 0,
            # "facade_neutral_pos_angle_manual": 0,
            "facade_modification_tolerance_height_static": 0,
            "facade_max_movement_duration_static": 18,
            "sc_internal_values": {
                "lock_integration_manual": False,
                # "lock_integration_entity": input_boolean.d07_lock_integration
                "lock_integration_with_position_manual": False,
                # "lock_integration_with_position_entity": input_boolean.d08_lock_integration_with_position
                "lock_height_manual": 0,
                # "lock_height_entity": input_number.lock_height_sc_dummy
                "lock_angle_manual": 15,
                # "lock_angle_entity": input_number.lock_angle_sc_dummy
                # no_restriction, only_open, only_close
                "movement_restriction_height_manual": "only_open",
                # "movement_restriction_angle_manual": "no_restriction",
                # "movement_restriction_height_entity":
                # "movement_restriction_angle_entity":
                # "enforce_positioning_entity": input_button.d13_enforce_positioning
                #
                "facade_neutral_pos_height_manual": 0,
                # "facade_neutral_pos_height_entity": input_number.g15_neutral_pos_height
                # "facade_neutral_pos_angle_manual": 0,
                # "facade_neutral_pos_angle_entity": input_number.g16_neutral_pos_angle
                #
                # Shadow configuration
                # "shadow_control_enabled_entity":
                "shadow_control_enabled_manual": True,
                # "shadow_brightness_threshold_entity":
                "shadow_brightness_threshold_winter_manual": 50000,
                # "shadow_after_seconds_entity":
                "shadow_after_seconds_manual": 10,
                # "shadow_shutter_max_height_entity": input_number.automation_shadow_max_height_sc_dummy
                "shadow_shutter_max_height_manual": 100,
                # "shadow_shutter_max_angle_entity": input_number.automation_shadow_max_angle_sc_dummy
                # "shadow_shutter_max_angle_manual": 100,
                # "shadow_shutter_look_through_seconds_entity":
                "shadow_shutter_look_through_seconds_manual": 10,
                # "shadow_shutter_open_seconds_entity":
                "shadow_shutter_open_seconds_manual": 10,
                # "shadow_shutter_look_through_angle_entity":
                # "shadow_shutter_look_through_angle_manual": 54,
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
                # "dawn_shutter_max_angle_manual": 100,
                # "dawn_shutter_look_through_seconds_entity":
                "dawn_shutter_look_through_seconds_manual": 10,
                # "dawn_shutter_open_seconds_entity":
                "dawn_shutter_open_seconds_manual": 10,
                # "dawn_shutter_look_through_angle_entity":
                # "dawn_shutter_look_through_angle_manual": 45,
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
        # ("mode1", True),
        # ("mode2", True),
        ("mode3", False),
    ],
)
async def test_lock(hass: HomeAssistant, setup_from_user_config, time_travel, caplog, shutter_type, check_angle):
    """Test that SC auto-locks when user manually moves cover."""
    # === INIT =====================================================================================
    config = {DOMAIN: [TEST_CONFIG[DOMAIN][0].copy()]}
    config[DOMAIN][0]["facade_shutter_type_static"] = shutter_type
    pos_calls, tilt_calls = await setup_instance(caplog, hass, setup_from_user_config, config, time_travel)

    _ = await time_travel_and_check(
        time_travel, hass, "sensor.sc_test_instance_state", seconds=2, executions=2, pos_calls=pos_calls, tilt_calls=tilt_calls
    )

    state1 = await get_entity_and_show_state(hass, "sensor.sc_test_instance_lock_state")
    assert_equal(state1.state, LockState.UNLOCKED, "Lock state")

    await set_lock_state(hass, "sc_test_instance", lock=True)

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
    height, angle = get_cover_position(pos_calls, tilt_calls)
    assert_equal(height, "100", "SC height")
    if check_angle:
        assert_equal(angle, "100", "SC angle")


@pytest.mark.parametrize(
    ("shutter_type", "check_angle"),
    [
        # ("mode1", True),
        # ("mode2", True),
        ("mode3", False),
    ],
)
async def test_lock_with_position(hass: HomeAssistant, setup_from_user_config, time_travel, caplog, shutter_type, check_angle):
    """Test that SC auto-locks when user manually moves cover."""
    # === INIT =====================================================================================
    config = {DOMAIN: [TEST_CONFIG[DOMAIN][0].copy()]}
    config[DOMAIN][0]["facade_shutter_type_static"] = shutter_type
    pos_calls, tilt_calls = await setup_instance(caplog, hass, setup_from_user_config, config, time_travel)

    _ = await time_travel_and_check(
        time_travel, hass, "sensor.sc_test_instance_state", seconds=2, executions=2, pos_calls=pos_calls, tilt_calls=tilt_calls
    )

    state1 = await get_entity_and_show_state(hass, "sensor.sc_test_instance_lock_state")
    assert_equal(state1.state, LockState.UNLOCKED, "Lock state")

    await set_lock_state(hass, "sc_test_instance", lock_with_position=True)

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

    height, angle = get_cover_position(pos_calls, tilt_calls)
    assert_equal(height, "100", "SC height")
    if check_angle:
        assert_equal(angle, "50", "SC angle")


@pytest.mark.parametrize(
    ("shutter_type", "check_angle"),
    [
        # ("mode1", True),
        # ("mode2", True),
        ("mode3", False),
    ],
)
async def test_lock_then_lock_with_position(hass: HomeAssistant, setup_from_user_config, time_travel, caplog, shutter_type, check_angle):
    """Test that SC auto-locks when user manually moves cover."""
    # === INIT =====================================================================================
    config = {DOMAIN: [TEST_CONFIG[DOMAIN][0].copy()]}
    config[DOMAIN][0]["facade_shutter_type_static"] = shutter_type
    pos_calls, tilt_calls = await setup_instance(caplog, hass, setup_from_user_config, config, time_travel)

    _ = await time_travel_and_check(
        time_travel, hass, "sensor.sc_test_instance_state", seconds=2, executions=2, pos_calls=pos_calls, tilt_calls=tilt_calls
    )

    state1 = await get_entity_and_show_state(hass, "sensor.sc_test_instance_lock_state")
    assert_equal(state1.state, LockState.UNLOCKED, "Lock state")

    await set_lock_state(hass, "sc_test_instance", lock=True)

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
    height, angle = get_cover_position(pos_calls, tilt_calls)
    assert_equal(height, "100", "SC height")
    if check_angle:
        assert_equal(angle, "100", "SC angle")

    await set_lock_state(hass, "sc_test_instance", lock_with_position=True)

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
    height, angle = get_cover_position(pos_calls, tilt_calls)
    assert_equal(height, "100", "SC height")
    if check_angle:
        assert_equal(angle, "50", "SC angle")


@pytest.mark.parametrize(
    ("shutter_type", "check_angle"),
    [
        # ("mode1", True),
        # ("mode2", True),
        ("mode3", False),
    ],
)
async def test_lock_with_position_then_lock(hass: HomeAssistant, setup_from_user_config, time_travel, caplog, shutter_type, check_angle):
    """Test that SC auto-locks when user manually moves cover."""
    # === INIT =====================================================================================
    config = {DOMAIN: [TEST_CONFIG[DOMAIN][0].copy()]}
    config[DOMAIN][0]["facade_shutter_type_static"] = shutter_type
    pos_calls, tilt_calls = await setup_instance(caplog, hass, setup_from_user_config, config, time_travel)

    _ = await time_travel_and_check(
        time_travel, hass, "sensor.sc_test_instance_state", seconds=2, executions=2, pos_calls=pos_calls, tilt_calls=tilt_calls
    )

    state1 = await get_entity_and_show_state(hass, "sensor.sc_test_instance_lock_state")
    assert_equal(state1.state, LockState.UNLOCKED, "Lock state")

    await set_lock_state(hass, "sc_test_instance", lock_with_position=True)

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
    height, angle = get_cover_position(pos_calls, tilt_calls)
    assert_equal(height, "100", "SC height")
    if check_angle:
        assert_equal(angle, "50", "SC angle")

    await set_lock_state(hass, "sc_test_instance", lock=True)

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
    height, angle = get_cover_position(pos_calls, tilt_calls)
    assert_equal(height, "100", "SC height")
    if check_angle:
        assert_equal(angle, "50", "SC angle")


@pytest.mark.parametrize(
    ("shutter_type", "check_angle"),
    [
        # ("mode1", True),
        # ("mode2", True),
        ("mode3", False),
    ],
)
async def test_auto_lock_on_manual_change(hass: HomeAssistant, setup_from_user_config, time_travel, caplog, shutter_type, check_angle):
    """Test that SC auto-locks when user manually moves cover."""
    # === INIT =====================================================================================
    config = {DOMAIN: [TEST_CONFIG[DOMAIN][0].copy()]}
    config[DOMAIN][0]["facade_shutter_type_static"] = shutter_type
    pos_calls, tilt_calls = await setup_instance(caplog, hass, setup_from_user_config, config, time_travel)

    _ = await get_entity_and_show_state(hass, "sensor.sc_test_instance_state")

    current_brightness = hass.states.get("input_number.d01_brightness")
    if current_brightness:
        await set_sun_position(hass, brightness=70000)
        _ = await time_travel_and_check(
            time_travel, hass, "sensor.sc_test_instance_state", seconds=2, executions=20, pos_calls=pos_calls, tilt_calls=tilt_calls
        )
        await set_sun_position(hass, brightness=current_brightness.state)
        _ = await time_travel_and_check(
            time_travel, hass, "sensor.sc_test_instance_state", seconds=2, executions=20, pos_calls=pos_calls, tilt_calls=tilt_calls
        )

    # Prüfe dass SC den Cover gesteuert hat
    height, angle = get_cover_position(pos_calls, tilt_calls)
    assert_equal(height, "100", "SC height")
    if check_angle:
        assert_equal(angle, "100", "SC angle")

    # Lock state sollte UNLOCKED sein
    lock_state = await get_entity_and_show_state(hass, "sensor.sc_test_instance_lock_state")
    assert_equal(lock_state.state, LockState.UNLOCKED, "Lock state before manual change")

    # USER bewegt Behang manuell!
    await simulate_manual_cover_change(hass, "cover.sc_dummy", position=50, tilt_position=60)

    # Prüfe dass Cover TATSÄCHLICH auf 50/60 ist (nicht SC calls!)
    actual_height, actual_angle = get_actual_cover_position(hass, "cover.sc_dummy")  # ← NEU!
    assert_equal(actual_height, 50, "Actual cover height after manual change")
    if check_angle:
        assert_equal(actual_angle, 60, "Actual cover angle after manual change")

    # Trigger sensor update
    if current_brightness:
        new_brightness = float(current_brightness.state) + 0.1
        await set_sun_position(hass, brightness=new_brightness)  # Minimal ändern

    lock_state = await time_travel_and_check(
        time_travel, hass, "sensor.sc_test_instance_lock_state", seconds=2, executions=8, pos_calls=pos_calls, tilt_calls=tilt_calls
    )
    assert_equal(lock_state.state, LockState.LOCKED_BY_EXTERNAL_MODIFICATION, "Lock state after manual change")

    # SC sollte NICHT mehr gesteuert haben (weil gelockt)
    # Also: pos_calls/tilt_calls sollten immer noch bei 100 sein
    sc_height, sc_angle = get_cover_position(pos_calls, tilt_calls)  # ← Letzter SC Call
    assert_equal(sc_height, "100", "SC should not have made new calls (still at 100)")
    if check_angle:
        assert_equal(sc_angle, "100", "SC should not have made new calls (still at 100)")

    # Aber tatsächliche Position sollte bei 50/60 bleiben (vom User)
    actual_height, actual_angle = get_actual_cover_position(hass, "cover.sc_dummy")  # ← NEU!
    assert_equal(actual_height, 50, "Actual cover should stay at manual position (locked)")
    if check_angle:
        assert_equal(actual_angle, 60, "Actual cover should stay at manual position (locked)")


async def test_restart_with_closed_cover_dawn_conditions(
    hass: HomeAssistant,
    setup_from_user_config,
    time_travel,
    caplog,
):
    """Test Issue #XXX: Cover öffnet sich nach HA Neustart.

    Ausgangssituation:
    - Mode 3 Rollo
    - Geschlossen (0%)
    - Nicht gesperrt
    - Dämmerung (Helligkeit unter Schwelle)
    - Bewegungseinschränkung: nur öffnen

    Erwartung:
    - Nach 90s sollte NICHT automatisch geöffnet werden
    """

    caplog.set_level(logging.DEBUG, logger="custom_components.shadow_control")

    # =========================================================================
    # PHASE 1: Simuliere Zustand VOR dem Restart
    # =========================================================================

    # Setup Cover - GESCHLOSSEN (wie vom User berichtet)
    # HA: 0%, KNX: 100% (invertiert)
    hass.states.async_set(
        "cover.sc_dummy",
        "closed",
        {
            "current_position": 0,  # Geschlossen in HA
            "current_tilt_position": 0,
            "supported_features": 255,
        },
    )

    # Setup Input Numbers - Dämmerung
    input_number_config = {
        "input_number": {
            "d01_brightness": {
                "min": 0,
                "max": 100000,
                "initial": 3000,  # ← UNTER Dawn-Schwelle (5000)!
                "name": "Brightness",
            },
            "d03_sun_elevation": {
                "min": -90,
                "max": 90,
                "initial": 5,  # Niedrig (Dämmerung)
                "name": "Sun Elevation",
            },
            "d04_sun_azimuth": {
                "min": 0,
                "max": 360,
                "initial": 90,  # Osten (Morgen)
                "name": "Sun Azimuth",
            },
        }
    }

    assert await async_setup_component(hass, "input_number", input_number_config)
    await hass.async_block_till_done()

    # =========================================================================
    # PHASE 2: Starte Shadow Control (= HA Restart)
    # =========================================================================

    _LOGGER.info("=" * 80)
    _LOGGER.info("SIMULATING HA RESTART - Starting Shadow Control")
    _LOGGER.info("=" * 80)

    await setup_from_user_config(TEST_CONFIG)

    # Initial State nach Restart
    cover_state = hass.states.get("cover.sc_dummy")
    _LOGGER.info("Cover State nach Restart: %s", cover_state.state)
    _LOGGER.info("Cover Position nach Restart: %s%%", cover_state.attributes["current_position"])

    sc_state = hass.states.get("sensor.test_restart_issue_state")
    _LOGGER.info("SC State nach Restart: %s", sc_state.state if sc_state else "NOT FOUND")

    lock_state = hass.states.get("sensor.test_restart_issue_lock_state")
    _LOGGER.info("Lock State nach Restart: %s", lock_state.state if lock_state else "NOT FOUND")

    # Cover sollte immer noch geschlossen sein
    assert cover_state.attributes["current_position"] == 0, "Cover sollte direkt nach Restart noch geschlossen sein"

    # =========================================================================
    # PHASE 3: Warte 90 Sekunden (Dawn Timer)
    # =========================================================================

    _LOGGER.info("=" * 80)
    _LOGGER.info("TIME TRAVEL: 91 seconds (past dawn_after_seconds)")
    _LOGGER.info("=" * 80)

    # Spring über den 90s Dawn Timer
    await time_travel(seconds=91)

    # =========================================================================
    # PHASE 4: Prüfe Ergebnis
    # =========================================================================

    cover_state = hass.states.get("cover.sc_dummy")
    _LOGGER.info("Cover Position nach 91s: %s%%", cover_state.attributes["current_position"])

    sc_state = hass.states.get("sensor.test_restart_issue_state")
    _LOGGER.info("SC State nach 91s: %s", sc_state.state if sc_state else "NOT FOUND")

    lock_state = hass.states.get("sensor.test_restart_issue_lock_state")
    _LOGGER.info("Lock State nach 91s: %s", lock_state.state if lock_state else "NOT FOUND")

    # ERWARTUNG: Cover sollte NICHT geöffnet haben
    # Weil: Bewegungseinschränkung "only_open" bedeutet
    # "nur öffnen erlaubt" aber nicht "automatisch öffnen"!
    # ODER: Dawn sollte bei geschlossenem Cover nicht triggern?

    # Das ist der eigentliche Bug-Test:
    assert cover_state.attributes["current_position"] == 0, (
        f"BUG: Cover hat sich nach Restart geöffnet! Position: {cover_state.attributes['current_position']}%"
    )


@pytest.mark.parametrize(
    ("initial_position", "description"),
    [
        (0, "geschlossen"),
        (50, "halb offen"),
        (100, "offen"),
    ],
)
async def test_restart_with_initial_position(
    hass: HomeAssistant,
    setup_from_user_config,
    time_travel,
    caplog,
    initial_position,
    description,
):
    """Test Restart mit verschiedenen initialen Positionen."""

    caplog.set_level(logging.DEBUG, logger="custom_components.shadow_control")

    _LOGGER.info("=" * 80)
    _LOGGER.info("Testing Restart mit Position: %s%% (%s)", initial_position, description)
    _LOGGER.info("=" * 80)

    # Setup Cover mit gewünschter Position
    hass.states.async_set(
        "cover.sc_dummy",
        "open" if initial_position > 0 else "closed",
        {
            "current_position": initial_position,
            "current_tilt_position": 0,
            "supported_features": 255,
        },
    )

    # Setup Input Numbers (Dawn Bedingungen)
    input_number_config = {
        "input_number": {
            "d01_brightness": {
                "min": 0,
                "max": 100000,
                "initial": 300,  # Unter Dawn-Schwelle
                "name": "Brightness",
            },
            "d03_sun_elevation": {
                "min": -90,
                "max": 90,
                "initial": 5,
                "name": "Sun Elevation",
            },
            "d04_sun_azimuth": {
                "min": 0,
                "max": 360,
                "initial": 90,
                "name": "Sun Azimuth",
            },
        }
    }

    assert await async_setup_component(hass, "input_number", input_number_config)
    await hass.async_block_till_done()

    # Start SC (= HA Restart)
    await setup_from_user_config(TEST_CONFIG)

    initial_pos = hass.states.get("cover.sc_dummy").attributes["current_position"]
    _LOGGER.info("Initial Position: %s%%", initial_pos)

    # Warte 120s
    await time_travel(seconds=120)

    final_pos = hass.states.get("cover.sc_dummy").attributes["current_position"]
    _LOGGER.info("Final Position: %s%%", final_pos)

    # Position sollte sich nicht ändern
    assert final_pos == initial_pos, f"Geschlossener Cover sollte geschlossen bleiben! {initial_pos}% -> {final_pos}%"
