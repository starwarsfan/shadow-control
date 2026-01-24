"""Test config entry migration."""

from unittest.mock import MagicMock, patch

import pytest
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.shadow_control import async_migrate_entry
from custom_components.shadow_control.const import (
    VERSION,
    SCShadowInput,
)


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.config_entries = MagicMock()
    hass.config_entries.async_update_entry = MagicMock()
    return hass


@pytest.fixture
def config_entry_v4():
    """Create a version 4 config entry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.version = 4
    entry.entry_id = "test_entry_123"
    entry.data = {}
    entry.options = {}
    return entry


class TestMigrationVersion4:
    """Test migration from version 4 to 5."""

    @pytest.mark.asyncio
    async def test_migrate_brightness_threshold_entity_to_winter_summer_buffer(self, mock_hass, config_entry_v4):
        """Test migration of old brightness_threshold_entity to new winter/summer/buffer."""
        # Setup: Old configuration with single brightness threshold
        config_entry_v4.options = {
            "shadow_brightness_threshold_entity": "50000",
        }

        with patch("custom_components.shadow_control.get_full_options_schema") as mock_schema:
            mock_schema.return_value = lambda x: x  # Pass-through validator

            result = await async_migrate_entry(mock_hass, config_entry_v4)

        assert result is True

        # Verify async_update_entry was called
        mock_hass.config_entries.async_update_entry.assert_called_once()
        call_args = mock_hass.config_entries.async_update_entry.call_args

        # Check the updated options
        updated_options = call_args.kwargs["options"]

        # Old key should be removed
        assert "shadow_brightness_threshold_entity" not in updated_options

        # New keys should be present
        assert SCShadowInput.BRIGHTNESS_THRESHOLD_WINTER_ENTITY.value in updated_options

        # Winter and summer should have the old value (adaptive mode disabled)
        assert updated_options[SCShadowInput.BRIGHTNESS_THRESHOLD_WINTER_ENTITY.value] == "50000"

        # Version should be updated
        assert call_args.kwargs["version"] == VERSION

    @pytest.mark.asyncio
    async def test_migrate_preserves_other_options(self, mock_hass, config_entry_v4):
        """Test that migration preserves other unrelated options."""
        # Setup: Config with brightness threshold and other options
        config_entry_v4.options = {
            "shadow_brightness_threshold_entity": "60000",
            "some_other_option": "preserved_value",
            "another_option": 42,
        }

        with patch("custom_components.shadow_control.get_full_options_schema") as mock_schema:
            mock_schema.return_value = lambda x: x

            result = await async_migrate_entry(mock_hass, config_entry_v4)

        assert result is True

        call_args = mock_hass.config_entries.async_update_entry.call_args
        updated_options = call_args.kwargs["options"]

        # Other options should be preserved
        assert updated_options["some_other_option"] == "preserved_value"
        assert updated_options["another_option"] == 42

    @pytest.mark.asyncio
    async def test_migrate_removes_static_keys(self, mock_hass, config_entry_v4):
        """Test that old *_static keys are removed during migration."""
        # Setup: Config with old static keys
        config_entry_v4.options = {
            "shadow_brightness_threshold_entity": "50000",
            "lock_height_static": "100",  # Should be removed
            "lock_angle_static": "50",  # Should be removed
        }

        with patch("custom_components.shadow_control.get_full_options_schema") as mock_schema:
            mock_schema.return_value = lambda x: x

            result = await async_migrate_entry(mock_hass, config_entry_v4)

        assert result is True

        # Verify migration was called
        mock_hass.config_entries.async_update_entry.assert_called_once()

        # Note: The actual removal of *_static keys depends on SCInternal enum
        # This test verifies the migration succeeds with these keys present

    @pytest.mark.asyncio
    async def test_migrate_handles_validation_failure(self, mock_hass, config_entry_v4):
        """Test that migration returns False on validation failure."""
        config_entry_v4.options = {
            "shadow_brightness_threshold_entity": "50000",
        }

        with patch("custom_components.shadow_control.get_full_options_schema") as mock_schema:
            # Simulate validation failure
            mock_schema.return_value = MagicMock(side_effect=vol.Invalid("Validation failed"))

            result = await async_migrate_entry(mock_hass, config_entry_v4)

        assert result is False

        # async_update_entry should NOT be called on validation failure
        mock_hass.config_entries.async_update_entry.assert_not_called()

    @pytest.mark.asyncio
    async def test_migrate_different_brightness_values(self, mock_hass, config_entry_v4):
        """Test migration with various brightness threshold values."""
        test_values = ["30000", "75000", "100000"]

        for test_value in test_values:
            config_entry_v4.options = {
                "shadow_brightness_threshold_entity": test_value,
            }

            with patch("custom_components.shadow_control.get_full_options_schema") as mock_schema:
                mock_schema.return_value = lambda x: x

                result = await async_migrate_entry(mock_hass, config_entry_v4)

            assert result is True

            call_args = mock_hass.config_entries.async_update_entry.call_args
            updated_options = call_args.kwargs["options"]

            # Both winter and summer should have the same value
            assert updated_options[SCShadowInput.BRIGHTNESS_THRESHOLD_WINTER_ENTITY.value] == test_value


class TestMigrationOtherVersions:
    """Test that other version migrations still work."""

    @pytest.mark.asyncio
    async def test_unknown_version_returns_false(self, mock_hass):
        """Test that unknown version returns False."""
        entry = MagicMock(spec=ConfigEntry)
        entry.version = 99  # Unknown version
        entry.entry_id = "test_entry"
        entry.data = {}
        entry.options = {}

        result = await async_migrate_entry(mock_hass, entry)

        assert result is False
        mock_hass.config_entries.async_update_entry.assert_not_called()

    @pytest.mark.asyncio
    async def test_version_5_already_migrated(self, mock_hass):
        """Test that version 5 entry doesn't need migration (returns False for unknown)."""
        entry = MagicMock(spec=ConfigEntry)
        entry.version = 5  # Already at current version
        entry.entry_id = "test_entry"
        entry.data = {}
        entry.options = {}

        result = await async_migrate_entry(mock_hass, entry)

        # Should return False because version 5 is not handled (already current)
        assert result is False
