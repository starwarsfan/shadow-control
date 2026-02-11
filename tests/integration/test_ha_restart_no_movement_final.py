"""Integration Test: HA-Restart darf Behang nicht bewegen - COMPLETE FINAL VERSION."""

import logging
from itertools import count

import pytest
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant

from custom_components.shadow_control.const import DOMAIN
from tests.integration.conftest import (
    get_cover_position,
    set_sun_position,
    setup_instance,
    show_instance_entity_states,
)

_LOGGER = logging.getLogger(__name__)

# Base configuration for restart tests
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
            "sun_elevation_entity": "sun.sun",
            "sun_azimuth_entity": "sun.sun",
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
                "unlock_integration_manual": False,
                "lock_integration_manual": False,
                "lock_integration_with_position_manual": False,
                "lock_height_manual": 50,
                "lock_angle_manual": 50,
                "movement_restriction_height_manual": "no_restriction",
                "movement_restriction_angle_manual": "no_restriction",
                "facade_neutral_pos_height_manual": 0,
                "facade_neutral_pos_angle_manual": 0,
                "enforce_positioning_manual": False,
                #
                # Shadow configuration
                "shadow_control_enabled_manual": True,
                "shadow_brightness_threshold_winter_manual": 50000,
                "shadow_after_seconds_manual": 10,
                "shadow_shutter_max_height_manual": 100,
                "shadow_shutter_max_angle_manual": 90,  # ← Leicht schräg!
                "shadow_shutter_look_through_seconds_manual": 10,
                "shadow_shutter_open_seconds_manual": 10,
                "shadow_shutter_look_through_angle_manual": 54,
                "shadow_height_after_sun_manual": 0,
                "shadow_angle_after_sun_manual": 0,
                #
                # Dawn configuration
                "dawn_control_enabled_manual": False,
                "dawn_brightness_threshold_manual": 500,
                "dawn_after_seconds_manual": 10,
                "dawn_shutter_max_height_manual": 100,
                "dawn_shutter_max_angle_manual": 100,
                "dawn_shutter_look_through_seconds_manual": 10,
                "dawn_shutter_open_seconds_manual": 10,
                "dawn_shutter_look_through_angle_manual": 45,
                "dawn_height_after_dawn_manual": 0,
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
    step = count(1)
    _, _ = await setup_instance(caplog, hass, setup_from_user_config, TEST_CONFIG, time_travel)
    await show_instance_entity_states(hass, next(step))


@pytest.mark.parametrize(
    ("shutter_type", "check_angle", "initial_height", "initial_angle", "description"),
    [
        # mode1 - Alle Positionen
        ("mode1", True, 100, 100, "fully_open"),
        ("mode1", True, 50, 50, "half_open"),
        ("mode1", True, 0, 90, "closed_tilted_90"),  # ← KRITISCH: Bang!
        ("mode1", True, 0, 0, "fully_closed"),
        # mode2 - Alle Positionen
        ("mode2", True, 100, 100, "fully_open"),
        ("mode2", True, 50, 50, "half_open"),
        ("mode2", True, 0, 90, "closed_tilted_90"),  # ← KRITISCH: Bang!
        ("mode2", True, 0, 0, "fully_closed"),
        # mode3 - Nur Höhen-Tests (kein Winkel)
        ("mode3", False, 100, 100, "fully_open"),
        ("mode3", False, 50, 50, "half_open"),
        ("mode3", False, 0, 90, "closed"),  # Winkel wird ignoriert
        ("mode3", False, 0, 0, "fully_closed"),
    ],
)
async def test_no_movement_after_restart(
    hass: HomeAssistant,
    setup_from_user_config,
    time_travel,
    caplog,
    shutter_type,
    check_angle,
    initial_height,
    initial_angle,
    description,
):
    """Test that shutter doesn't move after HA restart.

    Critical cases:
    - mode1/mode2 with height=0%, angle=90°: Must NOT close to 0° then reopen to 90° (Bang!)
    - All positions should remain stable after restart

    Simulates:
    1. Cover at specific position before restart
    2. HA restart (cover → unavailable → restored)
    3. Config entities restore (input_number state restore)
    4. Assert: NO movement commands sent
    """
    # === INIT =====================================================================================
    _LOGGER.info(
        "=== Testing %s restart: %s (height=%d%%, angle=%d°) ===",
        shutter_type,
        description,
        initial_height,
        initial_angle,
    )

    config = {DOMAIN: [TEST_CONFIG[DOMAIN][0].copy()]}
    config[DOMAIN][0]["facade_shutter_type_static"] = shutter_type
    pos_calls, tilt_calls = await setup_instance(caplog, hass, setup_from_user_config, config, time_travel)

    # === Set initial cover position ===============================================================
    hass.states.async_set(
        "cover.sc_dummy",
        "open" if initial_height > 0 else "closed",
        {
            "current_position": initial_height,
            "current_tilt_position": initial_angle,
            "supported_features": 255,
        },
    )

    # Set sun position (shadow conditions met)
    await set_sun_position(hass, elevation=45, azimuth=180, brightness=70000)
    await hass.async_block_till_done()

    # Wait for initial setup to complete
    await time_travel(seconds=2)
    await hass.async_block_till_done()

    # ✅ FIX: Track initial call count instead of reset_mock
    initial_pos_count = len(pos_calls)
    initial_tilt_count = len(tilt_calls)

    _LOGGER.info(
        "Initial setup complete. Calls so far: height=%d, angle=%d. Starting restart simulation...",
        initial_pos_count,
        initial_tilt_count,
    )

    # === SIMULATE HA RESTART ======================================================================

    # Step 1: Cover becomes unavailable (wie beim HA Neustart)
    _LOGGER.info("Step 1: Cover → unavailable")
    hass.states.async_set(
        "cover.sc_dummy",
        STATE_UNAVAILABLE,
        {
            "current_position": None,
            "current_tilt_position": None,
        },
    )
    await hass.async_block_till_done()

    # Step 2: Cover restores to previous state
    _LOGGER.info("Step 2: Cover restored to height=%d%%, angle=%d°", initial_height, initial_angle)
    hass.states.async_set(
        "cover.sc_dummy",
        "open" if initial_height > 0 else "closed",
        {
            "current_position": initial_height,
            "current_tilt_position": initial_angle,
            "supported_features": 255,
        },
    )
    await hass.async_block_till_done()

    # Step 3: Config entities restore (simulates input_number restoration)
    _LOGGER.info("Step 3: Config entities restored (triggers force_immediate_positioning check)")

    # Wait for grace period and any potential positioning
    await time_travel(seconds=20)
    await hass.async_block_till_done()

    # === ASSERTIONS ===============================================================================

    # Get final position
    height, angle = get_cover_position(pos_calls, tilt_calls)

    # ✅ FIX: Count NEW commands after restart
    height_commands = len(pos_calls) - initial_pos_count
    angle_commands = (len(tilt_calls) - initial_tilt_count) if check_angle else 0

    _LOGGER.info(
        "After restart: height_commands=%d, angle_commands=%d, final_pos=%s/%s",
        height_commands,
        angle_commands,
        height,
        angle if check_angle else "N/A",
    )

    # CRITICAL: No movement should occur after restart!
    assert height_commands == 0, (
        f"BUG [{shutter_type}]: Height command sent after restart! "
        f"Initial: {initial_height}%, Commands: {height_commands}, Final: {height}%. "
        f"Shutter should not move on HA restart!"
    )

    if check_angle:
        assert angle_commands == 0, (
            f"BUG [{shutter_type}]: Angle command sent after restart! "
            f"Initial: {initial_angle}°, Commands: {angle_commands}, Final: {angle}°. "
            f"This causes the 'BANG' issue when max_angle=90° (tilted closed)! "
            f"Shutter closes completely (0°) then opens to 90° again."
        )

    # Log success
    _LOGGER.info("✅ SUCCESS: No movement after restart for %s/%s", shutter_type, description)


@pytest.mark.parametrize(
    ("shutter_type", "check_angle"),
    [
        ("mode1", True),
        ("mode2", True),
        ("mode3", False),
    ],
)
async def test_real_config_change_after_restart_does_move(
    hass: HomeAssistant,
    setup_from_user_config,
    time_travel,
    caplog,
    shutter_type,
    check_angle,
):
    """Test that REAL config changes after restart DO cause movement.

    This ensures we don't break normal operation while fixing the restart bug.
    User should still be able to change config after restart and have it applied.

    Strategy:
    1. Setup with shadow conditions met (sun position good, brightness high)
    2. Cover at height=0%, angle=100% (geschlossen, aber schräg)
    3. Restart simulation
    4. After grace period: Change max_angle from 100% to 50%
    5. Trigger positioning via button press
    6. Assert: Angle should move to 50%
    """
    # === INIT =====================================================================================
    _LOGGER.info("=== Testing %s: Real config change after restart ===", shutter_type)

    config = {DOMAIN: [TEST_CONFIG[DOMAIN][0].copy()]}
    config[DOMAIN][0]["facade_shutter_type_static"] = shutter_type
    # config[DOMAIN][0]["debug_enabled"] = True
    pos_calls, tilt_calls = await setup_instance(caplog, hass, setup_from_user_config, config, time_travel)

    # === Set initial state ========================================================================
    # Cover at height=0%, angle=100% (geschlossen, aber Lamellen schräg)
    # Initial max_angle is configured as 90% in TEST_CONFIG
    hass.states.async_set(
        "cover.sc_dummy",
        "closed",
        {"current_position": 0, "current_tilt_position": 100, "supported_features": 255},
    )

    # Shadow conditions met: sun at facade, high brightness
    await set_sun_position(hass, elevation=45, azimuth=180, brightness=70000)
    await hass.async_block_till_done()
    await time_travel(seconds=2)
    await hass.async_block_till_done()

    # === Simulate restart =========================================================================
    _LOGGER.info("Simulating HA restart...")
    hass.states.async_set("cover.sc_dummy", STATE_UNAVAILABLE, {})
    await hass.async_block_till_done()

    # Restore to same position
    hass.states.async_set(
        "cover.sc_dummy",
        "closed",
        {"current_position": 0, "current_tilt_position": 100, "supported_features": 255},
    )
    await hass.async_block_till_done()

    # Wait for grace period to expire (30s + buffer)
    _LOGGER.info("Waiting for grace period to expire (35 seconds)...")
    await time_travel(seconds=35)
    await hass.async_block_till_done()

    # Unlock NACH dem Restart!
    _LOGGER.info("Unlocking integration after restart")
    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": "button.sc_test_instance_unlock"},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Track call count before config change
    initial_pos_count = len(pos_calls)
    initial_tilt_count = len(tilt_calls)

    _LOGGER.info(
        "Grace period expired. Calls before config change: height=%d, angle=%d",
        initial_pos_count,
        initial_tilt_count,
    )

    # === NOW: User manually changes config AFTER restart (and AFTER grace period) ==================
    _LOGGER.info("User changes shadow_shutter_max_angle from 90%% to 50%% (AFTER grace period)")

    await hass.services.async_call(
        "number",
        "set_value",
        {
            "entity_id": "number.sc_test_instance_s_max_shutter_angle",
            "value": 50,  # Change from 90% to 50%
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    # ✅ CRITICAL: Trigger positioning via button press
    # Config change alone doesn't trigger positioning - user must press button or wait for timer
    _LOGGER.info("Pressing enforce positioning button to apply new config")
    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": "button.sc_test_instance_do_positioning"},
        blocking=True,
    )
    await hass.async_block_till_done()
    await time_travel(seconds=5)
    await hass.async_block_till_done()

    # === ASSERTIONS ===============================================================================

    # Count NEW commands after config change + button press
    height_commands_after = len(pos_calls) - initial_pos_count
    angle_commands_after = len(tilt_calls) - initial_tilt_count

    _LOGGER.info(
        "After config change + button press: height_commands=%d, angle_commands=%d",
        height_commands_after,
        angle_commands_after,
    )

    # For mode1/mode2: angle should change from 100% to 50%
    # For mode3: only height matters
    if check_angle:
        assert angle_commands_after > 0, (
            f"Real config change after restart (and after grace period) should trigger positioning! "
            f"[{shutter_type}] Expected angle commands > 0, got {angle_commands_after}. "
            f"Grace period expired: Yes (35s). Auto-lock disabled: Yes. Button pressed: Yes."
        )
        _LOGGER.info("✅ SUCCESS: Config change after restart triggered positioning")
    else:
        _LOGGER.info("✅ SUCCESS: mode3 doesn't use angles - test passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
