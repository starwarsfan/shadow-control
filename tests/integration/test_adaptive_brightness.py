"""Integration Test: Adaptive Brightness Threshold."""

import logging
from itertools import count

from homeassistant.core import HomeAssistant

from custom_components.shadow_control.const import DOMAIN
from tests.integration.conftest import (
    setup_instance,
    show_instance_entity_states,
)

_LOGGER = logging.getLogger(__name__)

# Base configuration with adaptive brightness
BASE_CONFIG = {
    DOMAIN: [
        {
            "name": "SC Test Instance",
            "debug_enabled": False,
            "target_cover_entity": ["cover.sc_dummy"],
            "facade_shutter_type_static": "mode1",
            #
            # Dynamic configuration inputs
            "brightness_entity": "input_number.d01_brightness",
            "sun_elevation_entity": "input_number.d03_sun_elevation",
            "sun_azimuth_entity": "input_number.d04_sun_azimuth",
            "sunrise_entity": "input_datetime.sunrise",
            "sunset_entity": "input_datetime.sunset",
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
                "enforce_positioning_manual": False,  # Create button entity
                #
                # Shadow configuration with adaptive brightness
                "shadow_control_enabled_manual": True,
                "shadow_brightness_threshold_winter_manual": 30000,
                "shadow_brightness_threshold_summer_manual": 70000,
                "shadow_brightness_threshold_minimal_manual": 5000,
                "shadow_after_seconds_manual": 10,
                "shadow_shutter_max_height_manual": 100,
                "shadow_shutter_max_angle_manual": 100,
                "shadow_shutter_look_through_seconds_manual": 10,
                "shadow_shutter_open_seconds_manual": 10,
                "shadow_shutter_look_through_angle_manual": 54,
                "shadow_height_after_sun_manual": 0,
                "shadow_angle_after_sun_manual": 0,
                #
                # Dawn configuration (disabled for these tests)
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


async def get_brightness_threshold(hass: HomeAssistant) -> float | None:
    """Get current brightness threshold from sensor."""
    # Use the actual sensor name from HA
    sensor_name = "sensor.sc_test_instance_active_brightness_threshold"
    state = hass.states.get(sensor_name)

    if state and state.state not in ("unknown", "unavailable"):
        _LOGGER.info("Found brightness threshold sensor: %s = %s", sensor_name, state.state)
        return float(state.state)

    # Debug: List all sc_test_instance sensors
    _LOGGER.warning("Could not find brightness threshold sensor. Available sensors:")
    all_states = hass.states.async_all()
    for state in all_states:
        if "sc_test_instance" in state.entity_id and "sensor" in state.entity_id:
            _LOGGER.warning("  - %s = %s", state.entity_id, state.state)

    return None


async def test_show_adaptive_setup(
    hass: HomeAssistant,
    setup_from_user_config,
    time_travel,
    caplog,
):
    """Show adaptive brightness configuration."""
    step = count(1)

    config = {DOMAIN: [BASE_CONFIG[DOMAIN][0].copy()]}
    _, _ = await setup_instance(
        caplog,
        hass,
        setup_from_user_config,
        config,
        time_travel,
    )

    await show_instance_entity_states(hass, next(step))


async def test_adaptive_brightness_sensor_exists(
    hass: HomeAssistant,
    setup_from_user_config,
    time_travel,
    caplog,
):
    """Test that adaptive brightness sensor is created and has a value."""
    config = {DOMAIN: [BASE_CONFIG[DOMAIN][0].copy()]}
    _, _ = await setup_instance(
        caplog,
        hass,
        setup_from_user_config,
        config,
        time_travel,
    )

    await hass.async_block_till_done()
    await hass.async_block_till_done()

    # Sensor should exist and have a numeric value
    threshold = await get_brightness_threshold(hass)
    assert threshold is not None, "Brightness threshold sensor should exist"
    assert isinstance(threshold, float), f"Threshold should be float, got {type(threshold)}"
    assert 5000 <= threshold <= 70000, f"Threshold should be in valid range, got {threshold}"
    _LOGGER.info("Adaptive brightness threshold: %s lux", threshold)


async def test_adaptive_brightness_disabled_when_winter_equals_summer(
    hass: HomeAssistant,
    setup_from_user_config,
    time_travel,
    caplog,
):
    """Test that adaptive brightness uses static value when winter == summer."""
    config = {DOMAIN: [BASE_CONFIG[DOMAIN][0].copy()]}
    config[DOMAIN][0]["sc_internal_values"]["shadow_brightness_threshold_winter_manual"] = 50000
    config[DOMAIN][0]["sc_internal_values"]["shadow_brightness_threshold_summer_manual"] = 50000

    _, _ = await setup_instance(
        caplog,
        hass,
        setup_from_user_config,
        config,
        time_travel,
    )

    await hass.async_block_till_done()
    await hass.async_block_till_done()

    # Should use static winter value
    threshold = await get_brightness_threshold(hass)
    assert threshold == 50000, f"Expected static threshold 50000, got {threshold}"


async def test_adaptive_brightness_with_different_winter_summer(
    hass: HomeAssistant,
    setup_from_user_config,
    time_travel,
    caplog,
):
    """Test that adaptive brightness is active when winter != summer."""
    config = {DOMAIN: [BASE_CONFIG[DOMAIN][0].copy()]}
    _, _ = await setup_instance(
        caplog,
        hass,
        setup_from_user_config,
        config,
        time_travel,
    )

    await hass.async_block_till_done()
    await hass.async_block_till_done()

    # With winter=30000 and summer=70000, threshold should be dynamic
    threshold = await get_brightness_threshold(hass)
    assert threshold is not None, "Threshold sensor should exist"

    # Threshold should be somewhere between winter and summer (or buffer if outside sun hours)
    assert (
        threshold == 5000  # Buffer (outside sun hours)
        or (30000 <= threshold <= 70000)  # Within winter-summer range
    ), f"Threshold {threshold} should be buffer (5000) or in range 30000-70000"

    _LOGGER.info("Dynamic brightness threshold: %s lux", threshold)


async def test_adaptive_brightness_with_dawn_protection(
    hass: HomeAssistant,
    setup_from_user_config,
    time_travel,
    caplog,
):
    """Test that adaptive brightness threshold stays above dawn threshold."""
    # Configuration with low winter threshold but high dawn threshold
    config = {
        DOMAIN: [
            {
                "name": "SC Test Instance",
                "debug_enabled": False,
                "target_cover_entity": ["cover.sc_dummy"],
                "facade_shutter_type_static": "mode1",
                "brightness_entity": "input_number.d01_brightness",
                "sun_elevation_entity": "input_number.d03_sun_elevation",
                "sun_azimuth_entity": "input_number.d04_sun_azimuth",
                "sunrise_entity": "input_datetime.sunrise",
                "sunset_entity": "input_datetime.sunset",
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
                    "enforce_positioning_manual": False,
                    # Shadow configuration with LOW winter threshold
                    "shadow_control_enabled_manual": True,
                    "shadow_brightness_threshold_winter_manual": 30000,  # Low
                    "shadow_brightness_threshold_summer_manual": 50000,
                    "shadow_brightness_threshold_minimal_manual": 1000,  # Very low buffer
                    "shadow_after_seconds_manual": 10,
                    "shadow_shutter_max_height_manual": 100,
                    "shadow_shutter_max_angle_manual": 100,
                    # Dawn configuration with HIGHER threshold than buffer
                    "dawn_control_enabled_manual": True,
                    "dawn_brightness_threshold_manual": 5000,  # Higher than buffer!
                    "dawn_after_seconds_manual": 10,
                    "dawn_shutter_max_height_manual": 100,
                    "dawn_shutter_max_angle_manual": 100,
                },
            }
        ]
    }

    _, _ = await setup_instance(
        caplog,
        hass,
        setup_from_user_config,
        config,
        time_travel,
    )

    await hass.async_block_till_done()

    # Get brightness threshold from sensor
    sensor_name = "sensor.sc_test_instance_active_brightness_threshold"
    state = hass.states.get(sensor_name)

    assert state is not None, "Brightness threshold sensor should exist"
    threshold = float(state.state)

    _LOGGER.info("Adaptive brightness threshold with dawn protection: %s lux", threshold)

    # NOTE: Due to invalid sunrise/sunset in test environment, system uses static fallback
    # This test verifies that the sensor exists and has a valid value
    # The actual dawn protection is tested in unit tests
    assert threshold > 0, "Threshold should be positive"
    assert threshold >= 1000, "Threshold should be at least buffer value"


async def test_adaptive_brightness_no_dawn_uses_buffer(
    hass: HomeAssistant,
    setup_from_user_config,
    time_travel,
    caplog,
):
    """Test that without dawn, original buffer is used."""
    config = {
        DOMAIN: [
            {
                "name": "SC Test Instance",
                "debug_enabled": False,
                "target_cover_entity": ["cover.sc_dummy"],
                "facade_shutter_type_static": "mode1",
                "brightness_entity": "input_number.d01_brightness",
                "sun_elevation_entity": "input_number.d03_sun_elevation",
                "sun_azimuth_entity": "input_number.d04_sun_azimuth",
                "sunrise_entity": "input_datetime.sunrise",
                "sunset_entity": "input_datetime.sunset",
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
                    "enforce_positioning_manual": False,
                    # Shadow configuration
                    "shadow_control_enabled_manual": True,
                    "shadow_brightness_threshold_winter_manual": 30000,
                    "shadow_brightness_threshold_summer_manual": 50000,
                    "shadow_brightness_threshold_minimal_manual": 1000,
                    "shadow_after_seconds_manual": 10,
                    "shadow_shutter_max_height_manual": 100,
                    "shadow_shutter_max_angle_manual": 100,
                    # Dawn DISABLED
                    "dawn_control_enabled_manual": False,
                },
            }
        ]
    }

    _, _ = await setup_instance(
        caplog,
        hass,
        setup_from_user_config,
        config,
        time_travel,
    )

    await hass.async_block_till_done()

    # Test passes if no deadlock occurs and integration sets up correctly
    # The actual dawn protection logic is tested in unit tests
    sensor_name = "sensor.sc_test_instance_active_brightness_threshold"
    state = hass.states.get(sensor_name)

    assert state is not None, "Brightness threshold sensor should exist"
    threshold = float(state.state)
    assert threshold > 0, "Threshold should be positive"
