"""Integration Test: Timezone Handling in Adaptive Brightness."""

import logging
from datetime import UTC, datetime
from itertools import count

import pytest
from homeassistant.core import HomeAssistant

from custom_components.shadow_control.const import DOMAIN
from tests.integration.conftest import (
    setup_instance,
    show_instance_entity_states,
)

_LOGGER = logging.getLogger(__name__)

# Base configuration for timezone tests
BASE_CONFIG = {
    DOMAIN: [
        {
            "name": "SC Test Instance",
            "debug_enabled": True,
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
                "lock_height_manual": 50,
                "lock_angle_manual": 50,
                "movement_restriction_height_manual": "no_restriction",
                "movement_restriction_angle_manual": "no_restriction",
                "facade_neutral_pos_height_manual": 0,
                "facade_neutral_pos_angle_manual": 0,
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


async def test_show_timezone_setup(
    hass: HomeAssistant,
    setup_from_user_config,
    time_travel,
    caplog,
):
    """Show timezone test configuration."""
    step = count(1)

    # Setup sunrise/sunset entities (adjusted for test environment)
    sunrise_utc = datetime(2026, 2, 3, 17, 34, 31, tzinfo=UTC)  # Adjusted -1 day
    sunset_utc = datetime(2026, 2, 4, 7, 51, 56, tzinfo=UTC)

    hass.states.async_set(
        "input_datetime.sunrise",
        sunrise_utc.isoformat(),
        {"has_date": True, "has_time": True},
    )
    hass.states.async_set(
        "input_datetime.sunset",
        sunset_utc.isoformat(),
        {"has_date": True, "has_time": True},
    )

    await hass.async_block_till_done()

    _, _ = await setup_instance(
        caplog,
        hass,
        setup_from_user_config,
        BASE_CONFIG,
        time_travel,
    )

    await show_instance_entity_states(hass, next(step))


@pytest.mark.parametrize(
    ("test_name", "sunrise_utc", "sunset_utc", "should_fail"),
    [
        # New Zealand (UTC+13) - sunrise "tomorrow" in UTC, today in local
        (
            "nz_utc_plus_13",
            "2026-02-03T17:34:31+00:00",  # 04 Feb 06:34 NZ time (previous day in UTC)
            "2026-02-04T07:51:56+00:00",  # 04 Feb 20:51 NZ time
            False,  # Should work after fix
        ),
        # Tokyo (UTC+9)
        (
            "tokyo_utc_plus_9",
            "2026-02-03T21:00:00+00:00",  # 04 Feb 06:00 Tokyo time (previous day in UTC)
            "2026-02-04T08:30:00+00:00",  # 04 Feb 17:30 Tokyo time
            False,  # Should work after fix
        ),
        # Samoa (UTC+13)
        (
            "samoa_utc_plus_13",
            "2026-01-14T17:30:00+00:00",  # 15 Jan 06:30 Samoa time (previous day in UTC)
            "2026-01-15T07:45:00+00:00",  # 15 Jan 20:45 Samoa time
            False,  # Should work after fix
        ),
        # Berlin (UTC+1) - normal case
        (
            "berlin_utc_plus_1",
            "2026-02-04T06:30:00+00:00",  # 04 Feb 07:30 Berlin time
            "2026-02-04T16:45:00+00:00",  # 04 Feb 17:45 Berlin time
            False,  # Should always work
        ),
        # Los Angeles (UTC-8)
        (
            "la_utc_minus_8",
            "2026-02-04T15:00:00+00:00",  # 04 Feb 07:00 LA time
            "2026-02-05T01:30:00+00:00",  # 04 Feb 17:30 LA time
            False,  # Should work after fix
        ),
    ],
)
async def test_sunrise_sunset_timezone_normalization(
    hass: HomeAssistant,
    setup_from_user_config,
    time_travel,
    caplog,
    test_name: str,
    sunrise_utc: str,
    sunset_utc: str,
    should_fail: bool,
):
    """Test that sunrise/sunset normalization works correctly across timezones."""
    # Parse datetime strings
    sunrise_dt = datetime.fromisoformat(sunrise_utc)
    sunset_dt = datetime.fromisoformat(sunset_utc)

    # Setup sunrise/sunset entities
    hass.states.async_set(
        "input_datetime.sunrise",
        sunrise_dt.isoformat(),
        {"has_date": True, "has_time": True},
    )
    hass.states.async_set(
        "input_datetime.sunset",
        sunset_dt.isoformat(),
        {"has_date": True, "has_time": True},
    )

    await hass.async_block_till_done()

    # Setup instance
    _, _ = await setup_instance(
        caplog,
        hass,
        setup_from_user_config,
        BASE_CONFIG,
        time_travel,
    )

    await hass.async_block_till_done()

    # Check for warning logs
    warning_found = any("Invalid sun times after normalization" in record.message for record in caplog.records if record.levelname == "WARNING")

    if should_fail:
        assert warning_found, f"Test {test_name}: SHOULD have invalid sun times warning. Sunrise: {sunrise_utc}, Sunset: {sunset_utc}"
        _LOGGER.info(
            "✓ Test %s: Invalid sun times detected as expected (sunrise=%s, sunset=%s)",
            test_name,
            sunrise_utc,
            sunset_utc,
        )
    else:
        assert not warning_found, f"Test {test_name}: Should NOT have invalid sun times warning. Sunrise: {sunrise_utc}, Sunset: {sunset_utc}"
        _LOGGER.info(
            "✓ Test %s: Sun times normalized correctly (sunrise=%s, sunset=%s)",
            test_name,
            sunrise_utc,
            sunset_utc,
        )


async def test_nz_user_bug_reproduction(
    hass: HomeAssistant,
    setup_from_user_config,
    time_travel,
    caplog,
):
    """Reproduce the exact bug reported by NZ user.

    Bug report: User in NZ (UTC+13) got "Invalid sun times after normalization"
    warning with sunrise=2026-02-04 17:34:31+00:00 and sunset=2026-02-04 07:51:56+00:00.

    Note: In test environment (UTC), we adjust sunrise to previous day to simulate
    what would happen after normalization in a real UTC+13 environment.
    """
    # Adjusted times for test environment
    sunrise_utc = datetime(2026, 2, 3, 17, 34, 31, tzinfo=UTC)  # Adjusted -1 day
    sunset_utc = datetime(2026, 2, 4, 7, 51, 56, tzinfo=UTC)

    # Setup entities
    hass.states.async_set(
        "input_datetime.sunrise",
        sunrise_utc.isoformat(),
        {"has_date": True, "has_time": True},
    )
    hass.states.async_set(
        "input_datetime.sunset",
        sunset_utc.isoformat(),
        {"has_date": True, "has_time": True},
    )

    await hass.async_block_till_done()

    # Setup instance
    _, _ = await setup_instance(
        caplog,
        hass,
        setup_from_user_config,
        BASE_CONFIG,
        time_travel,
    )

    await hass.async_block_till_done()

    # Should NOT have warning after fix
    warning_found = any("Invalid sun times after normalization" in record.message for record in caplog.records if record.levelname == "WARNING")

    assert not warning_found, f"NZ bug: Should NOT have invalid sun times warning after fix. Sunrise UTC: {sunrise_utc}, Sunset UTC: {sunset_utc}"

    # Verify sensor exists and has valid value
    sensor_name = "sensor.sc_test_instance_active_brightness_threshold"
    state = hass.states.get(sensor_name)

    assert state is not None, "Brightness threshold sensor should exist"
    threshold = float(state.state)
    assert threshold > 0, "Threshold should be positive"

    _LOGGER.info("✓ NZ bug reproduction: Adaptive brightness threshold = %s lux", threshold)


async def test_midnight_date_boundary(
    hass: HomeAssistant,
    setup_from_user_config,
    time_travel,
    caplog,
):
    """Test that date boundary crossing at midnight is handled correctly."""
    # Times adjusted for test environment (UTC)
    sunrise_utc = datetime(2026, 2, 3, 17, 34, 31, tzinfo=UTC)  # Adjusted -1 day
    sunset_utc = datetime(2026, 2, 4, 7, 51, 56, tzinfo=UTC)

    hass.states.async_set("input_datetime.sunrise", sunrise_utc.isoformat())
    hass.states.async_set("input_datetime.sunset", sunset_utc.isoformat())

    await hass.async_block_till_done()

    _, _ = await setup_instance(
        caplog,
        hass,
        setup_from_user_config,
        BASE_CONFIG,
        time_travel,
    )

    await hass.async_block_till_done()

    # Should NOT have warning
    warning_found = any("Invalid sun times after normalization" in record.message for record in caplog.records if record.levelname == "WARNING")

    assert not warning_found, "Midnight crossing: Should handle date boundary without warnings"

    # Verify sensor
    sensor_name = "sensor.sc_test_instance_active_brightness_threshold"
    state = hass.states.get(sensor_name)

    assert state is not None
    threshold = float(state.state)
    assert threshold > 0

    _LOGGER.info("✓ Midnight crossing: Brightness threshold = %s lux", threshold)
