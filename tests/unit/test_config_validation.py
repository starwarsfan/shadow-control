"""Unit tests for config_validation module."""

import logging
from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.core import HomeAssistant

from custom_components.shadow_control.config_validation import (
    validate_and_warn_deprecated_config,
)
from custom_components.shadow_control.const import DEPRECATED_CONFIG_KEYS


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = Mock(spec=HomeAssistant)
    hass.async_create_task = Mock(side_effect=lambda _: None)
    hass.services = Mock()
    hass.services.async_call = AsyncMock()
    return hass


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    return Mock(spec=logging.Logger)


class TestValidateAndWarnDeprecatedConfig:
    """Tests for validate_and_warn_deprecated_config function."""

    def test_no_deprecated_keys_no_warnings(self, mock_hass, mock_logger):
        """Test that valid config passes without warnings."""
        config = {
            "name": "Test Instance",
            "target_cover_entity": ["cover.test"],
            "shadow_brightness_threshold_winter_manual": 30000,
            "shadow_brightness_threshold_summer_manual": 70000,
        }

        result = validate_and_warn_deprecated_config(
            mock_hass,
            config.copy(),
            mock_logger,
            "Test Instance",
        )

        # No warnings should be logged
        mock_logger.warning.assert_not_called()

        # Config should be unchanged
        assert result == config

        # No notification task should be created
        mock_hass.async_create_task.assert_not_called()

    def test_deprecated_key_removed_from_config(self, mock_hass, mock_logger):
        """Test that deprecated keys are removed from config."""
        config = {
            "name": "Test Instance",
            "shadow_brightness_threshold_manual": 30000,  # Deprecated
            "shadow_brightness_threshold_winter_manual": 30000,  # Current
        }

        result = validate_and_warn_deprecated_config(
            mock_hass,
            config,
            mock_logger,
            "Test Instance",
        )

        # Deprecated key should be removed
        assert "shadow_brightness_threshold_manual" not in result

        # Current key should remain
        assert result["shadow_brightness_threshold_winter_manual"] == 30000

    def test_deprecated_key_triggers_warning(self, mock_hass, mock_logger):
        """Test that deprecated keys trigger appropriate warnings."""
        config = {
            "name": "Test Instance",
            "shadow_brightness_threshold_manual": 30000,
        }

        validate_and_warn_deprecated_config(
            mock_hass,
            config,
            mock_logger,
            "Test Instance",
        )

        # Should log warning about deprecated config
        assert mock_logger.warning.call_count == 2  # One detailed, one summary

        # Check detailed warning - args are passed as format parameters
        detailed_call = mock_logger.warning.call_args_list[0]
        # Format: logger.warning("text %s %s", arg1, arg2, ...)
        assert "DEPRECATED CONFIG" in detailed_call[0][0]
        assert "shadow_brightness_threshold_manual" in detailed_call[0][1]  # First arg
        assert "v5 (Adaptive Brightness)" in detailed_call[0][2]  # Second arg

        # Check summary warning - count is first arg after format string
        summary_call = mock_logger.warning.call_args_list[1]
        assert "Found %d deprecated configuration option(s)" in summary_call[0][0]
        assert summary_call[0][1] == 1  # Count argument

    def test_multiple_deprecated_keys(self, mock_hass, mock_logger):
        """Test handling of multiple deprecated keys."""
        config = {
            "name": "Test Instance",
            "shadow_brightness_threshold_manual": 30000,
            "lock_height_static": 50,
            "lock_angle_static": 25,
        }

        result = validate_and_warn_deprecated_config(
            mock_hass,
            config,
            mock_logger,
            "Test Instance",
        )

        # All deprecated keys should be removed
        assert "shadow_brightness_threshold_manual" not in result
        assert "lock_height_static" not in result
        assert "lock_angle_static" not in result

        # Should log 3 detailed warnings + 1 summary
        assert mock_logger.warning.call_count == 4

        # Check summary mentions all 3 - count is first arg
        summary_call = mock_logger.warning.call_args_list[3]
        assert "Found %d deprecated configuration option(s)" in summary_call[0][0]
        assert summary_call[0][1] == 3  # Count argument

    def test_deprecated_key_in_sc_internal_values(self, mock_hass, mock_logger):
        """Test that deprecated keys in sc_internal_values are handled."""
        config = {
            "name": "Test Instance",
            "sc_internal_values": {
                "shadow_brightness_threshold_manual": 30000,  # Deprecated
                "shadow_brightness_threshold_winter_manual": 30000,  # Current
            },
        }

        result = validate_and_warn_deprecated_config(
            mock_hass,
            config,
            mock_logger,
            "Test Instance",
        )

        # Deprecated key should be removed from sc_internal_values
        assert "shadow_brightness_threshold_manual" not in result["sc_internal_values"]

        # Current key should remain
        assert result["sc_internal_values"]["shadow_brightness_threshold_winter_manual"] == 30000

        # Should log warning about deprecated config in sc_internal_values
        warning_text = str(mock_logger.warning.call_args_list[0])
        assert "sc_internal_values" in warning_text

    def test_notification_task_created(self, mock_hass, mock_logger):
        """Test that notification task is created for deprecated keys."""
        config = {
            "name": "Test Instance",
            "shadow_brightness_threshold_manual": 30000,
        }

        validate_and_warn_deprecated_config(
            mock_hass,
            config,
            mock_logger,
            "Test Instance",
        )

        # Should create a task for notification
        mock_hass.async_create_task.assert_called_once()

    def test_no_instance_name_in_warning(self, mock_hass, mock_logger):
        """Test warning when no instance name provided."""
        config = {
            "shadow_brightness_threshold_manual": 30000,
        }

        validate_and_warn_deprecated_config(
            mock_hass,
            config,
            mock_logger,
            None,  # No instance name
        )

        # Should still log warnings
        assert mock_logger.warning.call_count == 2

        # Summary should mention "configuration" instead of instance name
        summary_call = mock_logger.warning.call_args_list[1]
        summary_text = summary_call[0][0]
        # Should say "in configuration" not "in instance 'X'"
        assert "configuration" in summary_text

    def test_all_deprecated_keys_handled(self, mock_hass, mock_logger):
        """Test that all keys in DEPRECATED_CONFIG_KEYS can be validated."""
        # Test with a few representative keys from different categories
        test_keys = [
            ("shadow_brightness_threshold_manual", 30000),
            ("lock_height_static", 50),
            ("dawn_control_enabled_static", True),
            ("shadow_after_seconds_static", 15),
        ]

        for key, value in test_keys:
            config = {"name": "Test", key: value}
            mock_logger.reset_mock()
            mock_hass.reset_mock()

            result = validate_and_warn_deprecated_config(
                mock_hass,
                config.copy(),
                mock_logger,
                "Test",
            )

            # Key should be removed
            assert key not in result, f"Key {key} was not removed"

            # Warning should be logged
            assert mock_logger.warning.called, f"No warning for key {key}"

    def test_config_modified_inplace(self, mock_hass, mock_logger):
        """Test that config dict is modified in-place."""
        config = {
            "name": "Test Instance",
            "shadow_brightness_threshold_manual": 30000,
        }

        original_id = id(config)

        result = validate_and_warn_deprecated_config(
            mock_hass,
            config,
            mock_logger,
            "Test Instance",
        )

        # Should return the same dict object (modified in-place)
        assert id(result) == original_id

        # Original dict should be modified
        assert "shadow_brightness_threshold_manual" not in config

    def test_empty_config(self, mock_hass, mock_logger):
        """Test handling of empty config."""
        config = {}

        result = validate_and_warn_deprecated_config(
            mock_hass,
            config,
            mock_logger,
            "Test Instance",
        )

        # Should not crash
        assert result == {}

        # No warnings
        mock_logger.warning.assert_not_called()

    def test_deprecated_key_value_logged(self, mock_hass, mock_logger):
        """Test that the deprecated value is included in warning."""
        config = {
            "name": "Test Instance",
            "shadow_brightness_threshold_manual": 12345.67,
        }

        validate_and_warn_deprecated_config(
            mock_hass,
            config,
            mock_logger,
            "Test Instance",
        )

        # Check that value appears in warning args
        detailed_call = mock_logger.warning.call_args_list[0]
        # Value is the third argument (after key and version)
        assert 12345.67 in detailed_call[0] or "12345.67" in str(detailed_call[0])

    def test_migration_hint_in_warning(self, mock_hass, mock_logger):
        """Test that migration hint is included in warning."""
        config = {
            "name": "Test Instance",
            "shadow_brightness_threshold_manual": 30000,
        }

        validate_and_warn_deprecated_config(
            mock_hass,
            config,
            mock_logger,
            "Test Instance",
        )

        # Check that migration hint appears in warning args
        detailed_call = mock_logger.warning.call_args_list[0]
        migration_hint = DEPRECATED_CONFIG_KEYS["shadow_brightness_threshold_manual"]["migration_hint"]
        # Migration hint is the fourth argument
        assert migration_hint in detailed_call[0]


class TestDeprecatedConfigKeysStructure:
    """Tests for DEPRECATED_CONFIG_KEYS constant."""

    def test_all_keys_have_required_fields(self):
        """Test that all deprecated keys have required metadata."""
        required_fields = ["replacement", "deprecated_in", "migration_hint"]

        for key, info in DEPRECATED_CONFIG_KEYS.items():
            for field in required_fields:
                assert field in info, f"Key '{key}' missing required field '{field}'"

    def test_replacement_is_list(self):
        """Test that replacement field is always a list."""
        for key, info in DEPRECATED_CONFIG_KEYS.items():
            assert isinstance(info["replacement"], list), f"Key '{key}' replacement is not a list"
            assert len(info["replacement"]) > 0, f"Key '{key}' replacement list is empty"

    def test_deprecated_in_not_empty(self):
        """Test that deprecated_in field is not empty."""
        for key, info in DEPRECATED_CONFIG_KEYS.items():
            assert info["deprecated_in"], f"Key '{key}' has empty deprecated_in field"
            assert isinstance(info["deprecated_in"], str), f"Key '{key}' deprecated_in is not string"

    def test_migration_hint_not_empty(self):
        """Test that migration_hint field is not empty."""
        for key, info in DEPRECATED_CONFIG_KEYS.items():
            assert info["migration_hint"], f"Key '{key}' has empty migration_hint field"
            assert isinstance(info["migration_hint"], str), f"Key '{key}' migration_hint is not string"

    def test_no_duplicate_keys(self):
        """Test that there are no duplicate keys."""
        keys = list(DEPRECATED_CONFIG_KEYS.keys())
        assert len(keys) == len(set(keys)), "Duplicate keys found in DEPRECATED_CONFIG_KEYS"

    def test_v5_migration_keys_present(self):
        """Test that v5 migration keys are present."""
        v5_keys = [
            "shadow_brightness_threshold_manual",
            "shadow_brightness_threshold_entity",
            "lock_height_static",
            "lock_angle_static",
        ]

        for key in v5_keys:
            assert key in DEPRECATED_CONFIG_KEYS, f"Expected v5 key '{key}' not found"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
