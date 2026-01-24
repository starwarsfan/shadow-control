"""Integration Test: Komplette Shutter Automation."""

import logging
from itertools import count

import pytest
from homeassistant.core import HomeAssistant

from custom_components.shadow_control import ShutterState
from custom_components.shadow_control.const import DOMAIN
from tests.integration.conftest import (
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
                "shadow_brightness_threshold_winter_manual": 50000,
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


async def test_show_initial_state(
    hass: HomeAssistant,
    setup_from_user_config,
    time_travel,
    caplog,
):
    """Debug: Zeige Initial State."""

    # === INIT =====================================================================================
    _, _ = await setup_instance(caplog, hass, setup_from_user_config, TEST_CONFIG, time_travel)

    # Zeige Input Numbers
    _LOGGER.info("=" * 80)
    _LOGGER.info("INPUT NUMBERS:")
    brightness = hass.states.get("input_number.d01_brightness")
    elevation = hass.states.get("input_number.d03_sun_elevation")
    azimuth = hass.states.get("input_number.d04_sun_azimuth")

    _LOGGER.info("Brightness: %s", brightness.state if brightness else "NOT FOUND")
    _LOGGER.info("Elevation: %s", elevation.state if elevation else "NOT FOUND")
    _LOGGER.info("Azimuth: %s", azimuth.state if azimuth else "NOT FOUND")


async def test_sun_entity_update(
    hass: HomeAssistant,
    setup_from_user_config,
    time_travel,
    caplog,
):
    """Debug: Prüfe ob Sun Updates funktionieren."""

    # === INIT =====================================================================================
    _, _ = await setup_instance(caplog, hass, setup_from_user_config, TEST_CONFIG, time_travel)

    _LOGGER.info("=" * 80)
    _LOGGER.info("BEFORE SUN UPDATE:")
    _LOGGER.info("=" * 80)
    brightness = hass.states.get("input_number.d01_brightness")
    elevation = hass.states.get("input_number.d03_sun_elevation")
    azimuth = hass.states.get("input_number.d04_sun_azimuth")
    sc_state = hass.states.get("sensor.sc_test_instance_state")

    _LOGGER.info("Brightness: %s", brightness.state if brightness else "NOT FOUND")
    _LOGGER.info("Elevation: %s", elevation.state if elevation else "NOT FOUND")
    _LOGGER.info("Azimuth: %s", azimuth.state if azimuth else "NOT FOUND")
    _LOGGER.info("SC State: %s", sc_state.state if sc_state else "NOT FOUND")

    # Update Sun
    await set_sun_position(hass, elevation=60, azimuth=180, brightness=70000)

    _LOGGER.info("=" * 80)
    _LOGGER.info("AFTER SUN UPDATE:")
    _LOGGER.info("=" * 80)
    brightness = hass.states.get("input_number.d01_brightness")
    elevation = hass.states.get("input_number.d03_sun_elevation")
    azimuth = hass.states.get("input_number.d04_sun_azimuth")
    sc_state = hass.states.get("sensor.sc_test_instance_state")

    _LOGGER.info("Brightness: %s", brightness.state if brightness else "NOT FOUND")
    _LOGGER.info("Elevation: %s", elevation.state if elevation else "NOT FOUND")
    _LOGGER.info("Azimuth: %s", azimuth.state if azimuth else "NOT FOUND")
    _LOGGER.info("SC State: %s", sc_state.state if sc_state else "NOT FOUND")

    # Prüfe ob Facade in Sun ist
    facade_in_sun = hass.states.get("binary_sensor.sc_test_instance_facade_in_sun")
    if facade_in_sun:
        _LOGGER.info("Facade in Sun: %s, Attributes: %s", facade_in_sun.state, facade_in_sun.attributes)


async def test_shadow_full_closed(
    hass: HomeAssistant,
    setup_from_user_config,
    time_travel,
    caplog,
):
    """Test Timer mit Time Travel."""

    # === INIT =====================================================================================
    pos_calls, tilt_calls = await setup_instance(caplog, hass, setup_from_user_config, TEST_CONFIG, time_travel)

    # Initial instance state
    state1 = await get_entity_and_show_state(hass, "sensor.sc_test_instance_state")
    assert state1.state == ShutterState.NEUTRAL.name.lower()

    # === Shadow -> close ==========================================================================
    await set_sun_position(hass, elevation=60, azimuth=180, brightness=70000)

    # Prüfe ob Timer gestartet wurde
    state2 = await get_entity_and_show_state(hass, "sensor.sc_test_instance_state")

    # Prüfe Timer Attribute (falls vorhanden)
    if "next_modification" in state2.attributes:
        _LOGGER.info("Next modification: %s", state2.attributes["next_modification"])

    state3 = await time_travel_and_check(
        time_travel, hass, "sensor.sc_test_instance_state", seconds=2, executions=12, pos_calls=pos_calls, tilt_calls=tilt_calls
    )

    # Der Timer sollte den State geändert haben
    assert state3.state != state1.state, f"State sollte sich geändert haben: {state1.state} -> {state3.state}"

    # State sollte jetzt Shadow-Full-Closed sein
    assert state3.state == ShutterState.SHADOW_FULL_CLOSED.name.lower()

    assert len(pos_calls) > 0
    assert pos_calls[-1].data["position"] == 0  # KNX: 100% geschlossen
    assert len(tilt_calls) > 0
    assert tilt_calls[-1].data["tilt_position"] == 100


async def test_full_run_without_assert(
    hass: HomeAssistant,
    setup_from_user_config,
    time_travel,
    caplog,
):
    """Test Timer mit Time Travel."""

    # === INIT =====================================================================================
    pos_calls, tilt_calls = await setup_instance(caplog, hass, setup_from_user_config, TEST_CONFIG, time_travel)

    _ = await time_travel_and_check(
        time_travel, hass, "sensor.sc_test_instance_state", seconds=2, executions=12, pos_calls=pos_calls, tilt_calls=tilt_calls
    )

    # === open -> close (shadow) ===================================================================
    await set_sun_position(hass, elevation=60, azimuth=180, brightness=70000)
    # await asyncio.sleep(4)
    _ = await time_travel_and_check(
        time_travel, hass, "sensor.sc_test_instance_state", seconds=2, executions=12, pos_calls=pos_calls, tilt_calls=tilt_calls
    )

    # === close -> open=============================================================================
    await set_sun_position(hass, elevation=60, azimuth=180, brightness=5000)
    _ = await time_travel_and_check(
        time_travel, hass, "sensor.sc_test_instance_state", seconds=2, executions=12, pos_calls=pos_calls, tilt_calls=tilt_calls
    )

    # === open -> close ============================================================================
    await set_sun_position(hass, elevation=60, azimuth=180, brightness=70000)
    _ = await time_travel_and_check(
        time_travel, hass, "sensor.sc_test_instance_state", seconds=2, executions=12, pos_calls=pos_calls, tilt_calls=tilt_calls
    )

    # === close -> open ============================================================================
    await set_sun_position(hass, elevation=60, azimuth=180, brightness=5000)
    _ = await time_travel_and_check(
        time_travel, hass, "sensor.sc_test_instance_state", seconds=2, executions=12, pos_calls=pos_calls, tilt_calls=tilt_calls
    )

    # === open -> close (dawn) =====================================================================
    await set_sun_position(hass, elevation=60, azimuth=180, brightness=400)
    _ = await time_travel_and_check(
        time_travel, hass, "sensor.sc_test_instance_state", seconds=2, executions=12, pos_calls=pos_calls, tilt_calls=tilt_calls
    )

    # === close -> open (dawn) =====================================================================
    await set_sun_position(hass, elevation=60, azimuth=180, brightness=5000)
    _ = await time_travel_and_check(
        time_travel, hass, "sensor.sc_test_instance_state", seconds=2, executions=12, pos_calls=pos_calls, tilt_calls=tilt_calls
    )


async def test_dawn_full_closed(
    hass: HomeAssistant,
    setup_from_user_config,
    time_travel,
    caplog,
):
    """Test Timer mit Time Travel."""

    # === INIT =====================================================================================
    pos_calls, tilt_calls = await setup_instance(caplog, hass, setup_from_user_config, TEST_CONFIG, time_travel)

    # Initial instance state
    state1 = await get_entity_and_show_state(hass, "sensor.sc_test_instance_state")
    assert state1.state == ShutterState.NEUTRAL.name.lower()

    # === Dawn -> close ============================================================================
    await set_sun_position(hass, elevation=60, azimuth=180, brightness=100)

    # Prüfe ob Timer gestartet wurde
    state2 = await time_travel_and_check(
        time_travel, hass, "sensor.sc_test_instance_state", seconds=2, executions=12, pos_calls=pos_calls, tilt_calls=tilt_calls
    )

    # Prüfe Timer Attribute (falls vorhanden)
    if "next_modification" in state2.attributes:
        _LOGGER.info("Next modification: %s", state2.attributes["next_modification"])

    state3 = await time_travel_and_check(
        time_travel, hass, "sensor.sc_test_instance_state", seconds=2, executions=12, pos_calls=pos_calls, tilt_calls=tilt_calls
    )

    # Der Timer sollte den State geändert haben
    assert state3.state != state1.state, f"State sollte sich geändert haben: {state1.state} -> {state3.state}"

    # State sollte jetzt Shadow-Full-Closed sein
    assert state3.state == ShutterState.DAWN_FULL_CLOSED.name.lower()

    assert len(pos_calls) > 0
    assert pos_calls[-1].data["position"] == 0  # KNX: 100% geschlossen
    assert len(tilt_calls) > 0
    assert tilt_calls[-1].data["tilt_position"] == 0  # KNX: 100% geschlossen


@pytest.mark.parametrize(
    ("shutter_type", "check_angle"),
    [
        ("mode1", True),
        ("mode2", True),
        ("mode3", False),
    ],
)
async def test_look_through_after_dawn_full_closed(hass: HomeAssistant, setup_from_user_config, time_travel, caplog, shutter_type, check_angle):
    """Test Timer mit Time Travel."""

    # === INIT =====================================================================================
    config = {DOMAIN: [TEST_CONFIG[DOMAIN][0].copy()]}
    config[DOMAIN][0]["facade_shutter_type_static"] = shutter_type
    pos_calls, tilt_calls = await setup_instance(caplog, hass, setup_from_user_config, config, time_travel)

    # Initial instance state
    state1 = await time_travel_and_check(
        time_travel, hass, "sensor.sc_test_instance_state", seconds=2, executions=12, pos_calls=pos_calls, tilt_calls=tilt_calls
    )

    assert state1.state == ShutterState.NEUTRAL.name.lower()

    # === Dawn -> close ============================================================================
    await set_sun_position(hass, elevation=60, azimuth=180, brightness=100)

    # Prüfe ob Timer gestartet wurde
    state2 = await time_travel_and_check(
        time_travel, hass, "sensor.sc_test_instance_state", seconds=2, executions=12, pos_calls=pos_calls, tilt_calls=tilt_calls
    )

    # Prüfe Timer Attribute (falls vorhanden)
    if "next_modification" in state2.attributes:
        _LOGGER.info("Next modification: %s", state2.attributes["next_modification"])

    # Prüfe dass Timer abgelaufen ist
    state3 = await time_travel_and_check(
        time_travel, hass, "sensor.sc_test_instance_state", seconds=2, executions=12, pos_calls=pos_calls, tilt_calls=tilt_calls
    )

    # Der Timer sollte den State geändert haben
    assert state3.state != state1.state, f"State sollte sich geändert haben: {state1.state} -> {state3.state}"

    # State sollte jetzt Shadow-Full-Closed sein
    assert state3.state == ShutterState.DAWN_FULL_CLOSED.name.lower()

    assert len(pos_calls) > 0
    assert pos_calls[-1].data["position"] == 0  # KNX: 100% geschlossen
    if check_angle:
        assert len(tilt_calls) > 0
        assert tilt_calls[-1].data["tilt_position"] == 0  # KNX: 100% geschlossen

    # === After Dawn -> Lookthrough timer started ==================================================
    # Trigger Shadow (sollte Timer starten)
    await set_sun_position(hass, elevation=60, azimuth=180, brightness=5000)

    # Prüfe ob Timer gestartet wurde
    state4 = await time_travel_and_check(
        time_travel, hass, "sensor.sc_test_instance_state", seconds=2, executions=12, pos_calls=pos_calls, tilt_calls=tilt_calls
    )

    # Prüfe Timer Attribute (falls vorhanden)
    if "next_modification" in state4.attributes:
        _LOGGER.info("Next modification: %s", state4.attributes["next_modification"])

    # Prüfe dass Timer abgelaufen ist
    state5 = await time_travel_and_check(
        time_travel, hass, "sensor.sc_test_instance_state", seconds=2, executions=12, pos_calls=pos_calls, tilt_calls=tilt_calls
    )

    # Der Timer sollte den State geändert haben
    assert state5.state != state1.state, f"State sollte sich geändert haben: {state1.state} -> {state5.state}"

    # State sollte jetzt Shadow-Full-Closed sein
    assert state5.state == ShutterState.DAWN_NEUTRAL.name.lower()

    assert len(pos_calls) > 0
    assert pos_calls[-1].data["position"] == 100  # KNX: 0% (offen)
    if check_angle:
        assert len(tilt_calls) > 0
        assert tilt_calls[-1].data["tilt_position"] == 100  # KNX: 0% (offen)


# async def test_debug_mode(hass, setup_from_user_config):
#    entry = await setup_from_user_config(TEST_CONFIG)
#
#    # Prüfe ob debug_enabled in options ist:
#    _LOGGER.info("Entry options: %s", entry.options)
#    assert entry.options.get("debug_enabled") is True
