"""Integration tests for deprecated configuration handling."""

import logging

import pytest
from homeassistant.core import HomeAssistant

from custom_components.shadow_control.const import DEPRECATED_CONFIG_KEYS, DOMAIN
from tests.integration.conftest import setup_instance

_LOGGER = logging.getLogger(__name__)


# Base configuration for tests
def get_base_config():
    """Return base configuration for Shadow Control instance."""
    return {
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
                    "shadow_control_enabled_manual": True,
                    "shadow_brightness_threshold_winter_manual": 30000,
                    "shadow_brightness_threshold_summer_manual": 70000,
                    "shadow_brightness_threshold_buffer_manual": 5000,
                    "dawn_control_enabled_manual": False,
                },
            }
        ]
    }


@pytest.mark.parametrize(
    ("deprecated_key", "test_value"),
    [
        # v5 Adaptive Brightness
        ("shadow_brightness_threshold_manual", 30000),
        ("shadow_brightness_threshold_static", 30000),
        # v5 Static to Manual
        ("lock_height_static", 50),
        ("lock_angle_static", 45),
        ("shadow_control_enabled_static", True),
        ("dawn_control_enabled_static", False),
    ],
)
async def test_deprecated_config_key_handling(
    caplog,
    hass: HomeAssistant,
    setup_from_user_config,
    time_travel,
    deprecated_key: str,
    test_value: bool | float | str,
):
    """Test that deprecated config keys are handled correctly during setup."""

    # Register mock persistent_notification service
    async def mock_create(**kwargs):
        """Mock notification creation."""

    hass.services.async_register("persistent_notification", "create", mock_create)

    # Create config with deprecated key
    config = get_base_config()
    config[DOMAIN][0][deprecated_key] = test_value

    caplog.set_level(logging.WARNING)

    # Setup instance with deprecated config - should not fail
    test_config = config
    await setup_instance(caplog, hass, setup_from_user_config, test_config, time_travel, enforce_positioning=False)

    # Verify integration is running
    assert hass.data.get("shadow_control_managers") is not None

    # Verify warning was logged
    warning_logs = [record for record in caplog.records if record.levelname == "WARNING"]
    deprecated_warnings = [log for log in warning_logs if "DEPRECATED" in log.message]
    assert len(deprecated_warnings) > 0, f"No deprecation warning for key '{deprecated_key}'"


async def test_multiple_deprecated_keys_in_single_instance(
    caplog,
    hass: HomeAssistant,
    setup_from_user_config,
    time_travel,
):
    """Test handling of multiple deprecated keys in one instance."""

    # Register mock persistent_notification service
    async def mock_create(**kwargs):
        """Mock notification creation."""

    hass.services.async_register("persistent_notification", "create", mock_create)

    config = get_base_config()
    config[DOMAIN][0]["shadow_brightness_threshold_manual"] = 30000
    config[DOMAIN][0]["lock_height_static"] = 50
    config[DOMAIN][0]["lock_angle_static"] = 45

    caplog.set_level(logging.WARNING)

    # Setup should succeed despite deprecated keys
    test_config = config
    await setup_instance(caplog, hass, setup_from_user_config, test_config, time_travel, enforce_positioning=False)

    # Verify integration is running
    assert hass.data.get("shadow_control_managers") is not None

    # Verify all three deprecated keys were logged
    warning_logs = [record for record in caplog.records if record.levelname == "WARNING"]
    deprecated_warnings = [log for log in warning_logs if "DEPRECATED CONFIG" in log.message or "deprecated configuration option(s)" in log.message]
    assert len(deprecated_warnings) >= 4  # 3 detail + 1 summary


async def test_deprecated_key_in_sc_internal_values(
    caplog,
    hass: HomeAssistant,
    setup_from_user_config,
    time_travel,
):
    """Test deprecated keys in sc_internal_values are handled."""

    # Register mock persistent_notification service
    async def mock_create(**kwargs):
        """Mock notification creation."""

    hass.services.async_register("persistent_notification", "create", mock_create)

    config = get_base_config()
    config[DOMAIN][0]["sc_internal_values"]["shadow_brightness_threshold_manual"] = 30000

    caplog.set_level(logging.WARNING)

    # Setup should succeed
    test_config = config
    await setup_instance(caplog, hass, setup_from_user_config, test_config, time_travel, enforce_positioning=False)

    # Verify warning mentions sc_internal_values
    warning_logs = [record for record in caplog.records if record.levelname == "WARNING"]
    sc_internal_warnings = [log for log in warning_logs if "sc_internal_values" in log.message]
    assert len(sc_internal_warnings) > 0


async def test_no_warning_with_only_current_keys(
    caplog,
    hass: HomeAssistant,
    setup_from_user_config,
    time_travel,
):
    """Test that no warnings are generated with only current configuration."""
    config = get_base_config()
    # Only use current keys (already in base config)

    caplog.set_level(logging.WARNING)

    # Setup should succeed without warnings
    test_config = config
    await setup_instance(caplog, hass, setup_from_user_config, test_config, time_travel, enforce_positioning=False)

    # Verify integration is running
    assert hass.data.get("shadow_control_managers") is not None

    # Verify no deprecation warnings were logged
    warning_logs = [record for record in caplog.records if record.levelname == "WARNING"]
    deprecated_warnings = [log for log in warning_logs if "DEPRECATED" in log.message.upper()]
    assert len(deprecated_warnings) == 0


async def test_migration_from_v5_static_to_manual(
    caplog,
    hass: HomeAssistant,
    setup_from_user_config,
    time_travel,
):
    """Test migration path from v5 _static keys to _manual keys."""

    # Register mock persistent_notification service
    async def mock_create(**kwargs):
        """Mock notification creation."""

    hass.services.async_register("persistent_notification", "create", mock_create)

    # Simulate old v5 config with _static keys
    config = get_base_config()
    config[DOMAIN][0]["lock_height_static"] = 50
    config[DOMAIN][0]["lock_angle_static"] = 45
    config[DOMAIN][0]["shadow_control_enabled_static"] = True
    config[DOMAIN][0]["shadow_after_seconds_static"] = 15

    caplog.set_level(logging.WARNING)

    # Setup should succeed with warnings
    test_config = config
    await setup_instance(caplog, hass, setup_from_user_config, test_config, time_travel, enforce_positioning=False)

    # Verify integration is running
    assert hass.data.get("shadow_control_managers") is not None

    # Verify warnings for each _static key
    warning_logs = [record for record in caplog.records if record.levelname == "WARNING"]
    all_warnings_text = " ".join(log.message for log in warning_logs)

    assert "lock_height_static" in all_warnings_text
    assert "lock_angle_static" in all_warnings_text


async def test_all_deprecated_keys_have_metadata():
    """Test that all deprecated keys have complete metadata."""
    required_fields = ["replacement", "deprecated_in", "migration_hint"]

    for key, info in DEPRECATED_CONFIG_KEYS.items():
        # Check all required fields exist
        for field in required_fields:
            assert field in info, f"Key '{key}' missing field '{field}'"

        # Verify replacement is a non-empty list
        assert isinstance(info["replacement"], list), f"Key '{key}' replacement is not a list"
        assert len(info["replacement"]) > 0, f"Key '{key}' has empty replacement list"

        # Verify migration hint mentions at least one replacement
        assert any(replacement in info["migration_hint"] for replacement in info["replacement"]), (
            f"Key '{key}' migration_hint does not mention any replacement keys"
        )


async def test_deprecated_keys_count():
    """Test that we have the expected number of deprecated keys."""
    # We expect at least 30+ deprecated keys from various migrations
    assert len(DEPRECATED_CONFIG_KEYS) >= 30, f"Expected at least 30 deprecated keys, found {len(DEPRECATED_CONFIG_KEYS)}"

    # Verify some key categories exist
    v5_brightness_keys = [key for key in DEPRECATED_CONFIG_KEYS if "brightness_threshold" in key and "shadow" in key]
    assert len(v5_brightness_keys) >= 2, "Missing v5 brightness threshold keys"

    v5_static_keys = [key for key in DEPRECATED_CONFIG_KEYS if key.endswith("_static")]
    assert len(v5_static_keys) >= 25, "Missing v5 _static migration keys"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
