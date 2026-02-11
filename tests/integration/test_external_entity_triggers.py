"""Integration Test: External Entity Triggers für Enforce Positioning und Unlock Integration."""

import logging

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.shadow_control import LockState
from custom_components.shadow_control.const import DOMAIN
from tests.integration.conftest import (
    assert_equal,
    get_cover_position,
    get_entity_and_show_state,
    set_lock_state,
    set_sun_position,
    setup_instance,
    simulate_manual_cover_change,
    time_travel_and_check,
)

_LOGGER = logging.getLogger(__name__)

# Basis-Konfiguration ohne External Entities
_BASE_CONFIG = {
    "name": "SC Test Instance",
    "debug_enabled": False,
    "target_cover_entity": ["cover.sc_dummy"],
    "facade_shutter_type_static": "mode1",
    "brightness_entity": "input_number.d01_brightness",
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
        "lock_integration_with_position_manual": False,
        "lock_height_manual": 50,
        "lock_angle_manual": 50,
        "movement_restriction_height_manual": "no_restriction",
        "movement_restriction_angle_manual": "no_restriction",
        "facade_neutral_pos_height_manual": 0,
        "facade_neutral_pos_angle_manual": 0,
        "shadow_control_enabled_manual": True,
        "shadow_brightness_threshold_winter_manual": 50000,
        "shadow_after_seconds_manual": 10,
        "shadow_shutter_max_height_manual": 100,
        "shadow_shutter_max_angle_manual": 100,
        "shadow_shutter_look_through_seconds_manual": 10,
        "shadow_shutter_open_seconds_manual": 10,
        "shadow_shutter_look_through_angle_manual": 54,
        "shadow_height_after_sun_manual": 0,
        "shadow_angle_after_sun_manual": 0,
        "dawn_control_enabled_manual": True,
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


# =================================================================================================
# Hilfsfunktion: input_button State-Change simulieren
# =================================================================================================


async def _press_input_button(hass: HomeAssistant, entity_id: str) -> None:
    """Simuliert einen input_button Press via State-Change (wie HA es intern macht)."""
    # input_button State ist immer ein Timestamp des letzten Press
    new_state = dt_util.utcnow().isoformat()
    hass.states.async_set(entity_id, new_state)
    await hass.async_block_till_done()
    _LOGGER.info("Pressed input_button: %s (state: %s)", entity_id, new_state)


# =================================================================================================
# Tests: enforce_positioning_entity
# =================================================================================================


@pytest.mark.parametrize(
    ("shutter_type", "check_angle"),
    [
        ("mode1", True),
        ("mode2", True),
        ("mode3", False),
    ],
)
async def test_enforce_positioning_via_external_entity(
    hass: HomeAssistant,
    setup_from_user_config,
    time_travel,
    caplog,
    shutter_type,
    check_angle,
):
    """Test dass enforce_positioning_entity einen Positionierungsbefehl auslöst."""
    # === INIT =====================================================================================
    config = {DOMAIN: [_BASE_CONFIG.copy()]}
    config[DOMAIN][0]["facade_shutter_type_static"] = shutter_type
    # enforce_positioning_entity konfigurieren
    config[DOMAIN][0]["sc_internal_values"] = _BASE_CONFIG["sc_internal_values"].copy()
    config[DOMAIN][0]["enforce_positioning_entity"] = "input_button.test_enforce_positioning"

    # input_button Entity vorbereiten
    hass.states.async_set("input_button.test_enforce_positioning", "2026-01-01T00:00:00+00:00")

    pos_calls, tilt_calls = await setup_instance(caplog, hass, setup_from_user_config, config, time_travel)

    # Helligkeit über Threshold setzen → SC schließt Behang (elevation=45/azimuth=180 sind bereits Default)
    await set_sun_position(hass, brightness=70000)
    _ = await time_travel_and_check(
        time_travel,
        hass,
        "sensor.sc_test_instance_state",
        seconds=2,
        executions=20,
        pos_calls=pos_calls,
        tilt_calls=tilt_calls,
    )

    # SC sollte Behang geschlossen haben (Shadow state) → HA-Position 0 = physisch zu
    height, _ = get_cover_position(pos_calls, tilt_calls)
    assert_equal(height, "0", "SC height after shadow")
    lock_state = await get_entity_and_show_state(hass, "sensor.sc_test_instance_lock_state")
    assert_equal(lock_state.state, LockState.UNLOCKED, "Lock state should be UNLOCKED")

    # Merke Anzahl der Calls VOR dem Button-Press
    calls_before = len(pos_calls)

    # === enforce_positioning_entity triggern =====================================================
    _LOGGER.info("Triggering enforce positioning via external entity")
    await _press_input_button(hass, "input_button.test_enforce_positioning")
    await hass.async_block_till_done()

    # SC sollte einen Positionierungsbefehl gesendet haben
    assert len(pos_calls) > calls_before, (
        f"enforce_positioning_entity should trigger positioning! Calls before: {calls_before}, calls after: {len(pos_calls)}"
    )

    _LOGGER.info("✅ enforce_positioning_entity triggered %d new call(s)", len(pos_calls) - calls_before)


@pytest.mark.parametrize(
    ("shutter_type", "check_angle"),
    [
        ("mode1", True),
        ("mode2", True),
        ("mode3", False),
    ],
)
async def test_enforce_positioning_via_external_entity_multiple_presses(
    hass: HomeAssistant,
    setup_from_user_config,
    time_travel,
    caplog,
    shutter_type,
    check_angle,
):
    """Test dass mehrfaches Drücken der enforce_positioning_entity mehrfach triggert."""
    # === INIT =====================================================================================
    config = {DOMAIN: [_BASE_CONFIG.copy()]}
    config[DOMAIN][0]["facade_shutter_type_static"] = shutter_type
    config[DOMAIN][0]["sc_internal_values"] = _BASE_CONFIG["sc_internal_values"].copy()
    config[DOMAIN][0]["enforce_positioning_entity"] = "input_button.test_enforce_positioning"

    hass.states.async_set("input_button.test_enforce_positioning", "2026-01-01T00:00:00+00:00")

    pos_calls, tilt_calls = await setup_instance(caplog, hass, setup_from_user_config, config, time_travel)

    await set_sun_position(hass, brightness=70000)
    _ = await time_travel_and_check(
        time_travel,
        hass,
        "sensor.sc_test_instance_state",
        seconds=2,
        executions=20,
        pos_calls=pos_calls,
        tilt_calls=tilt_calls,
    )

    calls_before_first = len(pos_calls)

    # Erster Press → SC sendet enforce-Befehl
    await _press_input_button(hass, "input_button.test_enforce_positioning")
    await hass.async_block_till_done()
    calls_after_first = len(pos_calls)
    assert calls_after_first > calls_before_first, "First press should trigger positioning"

    # Brightness unter Threshold → SC öffnet Behang (verlässt shadow_full_closed)
    await set_sun_position(hass, brightness=10000)
    _ = await time_travel_and_check(
        time_travel,
        hass,
        "sensor.sc_test_instance_state",
        seconds=2,
        executions=20,
        pos_calls=pos_calls,
        tilt_calls=tilt_calls,
    )

    # Brightness wieder über Threshold → SC-Soll ist wieder shadow_full_closed
    await set_sun_position(hass, brightness=70000)
    _ = await time_travel_and_check(
        time_travel,
        hass,
        "sensor.sc_test_instance_state",
        seconds=2,
        executions=20,
        pos_calls=pos_calls,
        tilt_calls=tilt_calls,
    )

    calls_before_second = len(pos_calls)

    # Zweiter Press → SC sendet erneut enforce-Befehl
    await _press_input_button(hass, "input_button.test_enforce_positioning")
    await hass.async_block_till_done()
    calls_after_second = len(pos_calls)
    assert calls_after_second > calls_before_second, "Second press should trigger positioning again"

    _LOGGER.info("✅ Two presses triggered %d + %d calls", calls_after_first - calls_before_first, calls_after_second - calls_before_second)


# =================================================================================================
# Tests: unlock_integration_entity
# =================================================================================================


@pytest.mark.parametrize(
    ("shutter_type", "check_angle"),
    [
        ("mode1", True),
        ("mode2", True),
        ("mode3", False),
    ],
)
async def test_unlock_via_external_entity_clears_manual_lock(
    hass: HomeAssistant,
    setup_from_user_config,
    time_travel,
    caplog,
    shutter_type,
    check_angle,
):
    """Test dass unlock_integration_entity den manuellen Lock aufhebt."""
    # === INIT =====================================================================================
    config = {DOMAIN: [_BASE_CONFIG.copy()]}
    config[DOMAIN][0]["facade_shutter_type_static"] = shutter_type
    config[DOMAIN][0]["sc_internal_values"] = _BASE_CONFIG["sc_internal_values"].copy()
    config[DOMAIN][0]["unlock_integration_entity"] = "input_button.test_unlock"

    hass.states.async_set("input_button.test_unlock", "2026-01-01T00:00:00+00:00")

    pos_calls, tilt_calls = await setup_instance(caplog, hass, setup_from_user_config, config, time_travel)

    await set_sun_position(hass, brightness=70000)
    _ = await time_travel_and_check(
        time_travel,
        hass,
        "sensor.sc_test_instance_state",
        seconds=2,
        executions=20,
        pos_calls=pos_calls,
        tilt_calls=tilt_calls,
    )

    # Manuellen Lock aktivieren
    _LOGGER.info("Activating manual lock via switch")
    await set_lock_state(hass, "sc_test_instance", lock=True)

    _ = await time_travel_and_check(
        time_travel,
        hass,
        "sensor.sc_test_instance_lock_state",
        seconds=2,
        executions=8,
        pos_calls=pos_calls,
        tilt_calls=tilt_calls,
    )

    # Brightness triggern damit Lock-State sich aktualisiert
    current_brightness = hass.states.get("input_number.d01_brightness")
    if current_brightness:
        await set_sun_position(hass, brightness=float(current_brightness.state) + 0.1)

    lock_state = await time_travel_and_check(
        time_travel,
        hass,
        "sensor.sc_test_instance_lock_state",
        seconds=2,
        executions=8,
        pos_calls=pos_calls,
        tilt_calls=tilt_calls,
    )
    assert_equal(lock_state.state, LockState.LOCKED_MANUALLY, "Lock state should be LOCKED_MANUALLY")

    # === Unlock via external entity ==============================================================
    _LOGGER.info("Unlocking via external entity")
    await _press_input_button(hass, "input_button.test_unlock")
    await hass.async_block_till_done()

    # Brightness triggern damit Lock-State sich aktualisiert
    if current_brightness:
        await set_sun_position(hass, brightness=float(current_brightness.state) + 0.2)

    lock_state_after = await time_travel_and_check(
        time_travel,
        hass,
        "sensor.sc_test_instance_lock_state",
        seconds=2,
        executions=8,
        pos_calls=pos_calls,
        tilt_calls=tilt_calls,
    )
    assert_equal(lock_state_after.state, LockState.UNLOCKED, "Lock state should be UNLOCKED after pressing unlock entity")

    _LOGGER.info("✅ unlock_integration_entity cleared manual lock successfully")


@pytest.mark.parametrize(
    ("shutter_type", "check_angle"),
    [
        ("mode1", True),
        ("mode2", True),
        ("mode3", False),
    ],
)
async def test_unlock_via_external_entity_clears_auto_lock(
    hass: HomeAssistant,
    setup_from_user_config,
    time_travel,
    caplog,
    shutter_type,
    check_angle,
):
    """Test dass unlock_integration_entity den Auto-Lock (nach manueller Bewegung) aufhebt."""
    # === INIT =====================================================================================
    config = {DOMAIN: [_BASE_CONFIG.copy()]}
    config[DOMAIN][0]["facade_shutter_type_static"] = shutter_type
    config[DOMAIN][0]["sc_internal_values"] = _BASE_CONFIG["sc_internal_values"].copy()
    config[DOMAIN][0]["unlock_integration_entity"] = "input_button.test_unlock"

    hass.states.async_set("input_button.test_unlock", "2026-01-01T00:00:00+00:00")

    pos_calls, tilt_calls = await setup_instance(caplog, hass, setup_from_user_config, config, time_travel)

    # Sonne positionieren und SC in Shadow-State bringen
    await set_sun_position(hass, brightness=70000)
    _ = await time_travel_and_check(
        time_travel,
        hass,
        "sensor.sc_test_instance_state",
        seconds=2,
        executions=20,
        pos_calls=pos_calls,
        tilt_calls=tilt_calls,
    )

    height, _ = get_cover_position(pos_calls, tilt_calls)
    assert_equal(height, "0", "SC height before manual change (shadow = HA-pos 0)")

    # USER bewegt Behang manuell → Auto-Lock aktiviert sich
    _LOGGER.info("Simulating manual cover change to trigger auto-lock")
    await simulate_manual_cover_change(hass, "cover.sc_dummy", position=50, tilt_position=60)

    current_brightness = hass.states.get("input_number.d01_brightness")
    if current_brightness:
        await set_sun_position(hass, brightness=float(current_brightness.state) + 0.1)

    lock_state = await time_travel_and_check(
        time_travel,
        hass,
        "sensor.sc_test_instance_lock_state",
        seconds=2,
        executions=8,
        pos_calls=pos_calls,
        tilt_calls=tilt_calls,
    )
    assert_equal(
        lock_state.state, LockState.LOCKED_BY_EXTERNAL_MODIFICATION, "Lock state should be LOCKED_BY_EXTERNAL_MODIFICATION after manual move"
    )

    # === Unlock via external entity ==============================================================
    _LOGGER.info("Unlocking auto-lock via external entity")
    await _press_input_button(hass, "input_button.test_unlock")
    await hass.async_block_till_done()

    # Brightness triggern damit Lock-State sich aktualisiert
    if current_brightness:
        await set_sun_position(hass, brightness=float(current_brightness.state) + 0.2)

    lock_state_after = await time_travel_and_check(
        time_travel,
        hass,
        "sensor.sc_test_instance_lock_state",
        seconds=2,
        executions=8,
        pos_calls=pos_calls,
        tilt_calls=tilt_calls,
    )
    assert_equal(lock_state_after.state, LockState.UNLOCKED, "Lock state should be UNLOCKED after pressing unlock entity")

    _LOGGER.info("✅ unlock_integration_entity cleared auto-lock successfully")


@pytest.mark.parametrize(
    ("shutter_type", "check_angle"),
    [
        ("mode1", True),
        ("mode2", True),
        ("mode3", False),
    ],
)
async def test_unlock_via_external_entity_resumes_sc_control(
    hass: HomeAssistant,
    setup_from_user_config,
    time_travel,
    caplog,
    shutter_type,
    check_angle,
):
    """Test dass SC nach Unlock via external entity wieder den Behang steuert."""
    # === INIT =====================================================================================
    config = {DOMAIN: [_BASE_CONFIG.copy()]}
    config[DOMAIN][0]["facade_shutter_type_static"] = shutter_type
    config[DOMAIN][0]["sc_internal_values"] = _BASE_CONFIG["sc_internal_values"].copy()
    config[DOMAIN][0]["unlock_integration_entity"] = "input_button.test_unlock"

    hass.states.async_set("input_button.test_unlock", "2026-01-01T00:00:00+00:00")

    pos_calls, tilt_calls = await setup_instance(caplog, hass, setup_from_user_config, config, time_travel)

    await set_sun_position(hass, brightness=70000)
    _ = await time_travel_and_check(
        time_travel,
        hass,
        "sensor.sc_test_instance_state",
        seconds=2,
        executions=20,
        pos_calls=pos_calls,
        tilt_calls=tilt_calls,
    )

    # USER bewegt Behang manuell → Auto-Lock
    await simulate_manual_cover_change(hass, "cover.sc_dummy", position=50, tilt_position=60)

    current_brightness = hass.states.get("input_number.d01_brightness")
    if current_brightness:
        await set_sun_position(hass, brightness=float(current_brightness.state) + 0.1)

    lock_state = await time_travel_and_check(
        time_travel,
        hass,
        "sensor.sc_test_instance_lock_state",
        seconds=2,
        executions=8,
        pos_calls=pos_calls,
        tilt_calls=tilt_calls,
    )
    assert_equal(lock_state.state, LockState.LOCKED_BY_EXTERNAL_MODIFICATION, "Should be auto-locked after manual move")

    # Merke Anzahl der SC-Calls im gesperrten Zustand
    calls_while_locked = len(pos_calls)

    # Brightness ändern → SC sollte NICHT steuern (weil gelockt)
    if current_brightness:
        await set_sun_position(hass, brightness=float(current_brightness.state) + 0.2)
    _ = await time_travel_and_check(
        time_travel,
        hass,
        "sensor.sc_test_instance_state",
        seconds=2,
        executions=8,
        pos_calls=pos_calls,
        tilt_calls=tilt_calls,
    )
    assert len(pos_calls) == calls_while_locked, "SC should NOT send commands while locked"

    # === Unlock via external entity ==============================================================
    _LOGGER.info("Unlocking via external entity - SC should resume control")
    await _press_input_button(hass, "input_button.test_unlock")
    await hass.async_block_till_done()

    # Enforce positioning → SC sollte JETZT einen Befehl senden (nicht mehr gelockt)
    calls_after_unlock = len(pos_calls)
    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": "button.sc_test_instance_do_positioning"},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert len(pos_calls) > calls_after_unlock, (
        "SC should resume sending commands after unlock via external entity! "
        f"Calls while locked: {calls_while_locked}, calls after unlock+enforce: {len(pos_calls)}"
    )

    # SC sollte den Behang wieder in Shadow-Position gebracht haben
    height_after_unlock, _ = get_cover_position(pos_calls, tilt_calls)
    assert_equal(height_after_unlock, "0", "SC height after unlock (shadow = HA-pos 0)")

    _LOGGER.info("✅ SC resumed control after unlock via external entity")
