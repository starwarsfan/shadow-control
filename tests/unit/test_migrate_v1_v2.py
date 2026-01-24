"""Test config entry migration from version 1 to 2."""

from unittest.mock import MagicMock, patch

import pytest
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.shadow_control import async_migrate_entry


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.config_entries = MagicMock()
    hass.config_entries.async_update_entry = MagicMock()
    return hass


@pytest.fixture
def config_entry_v1():
    """Create a version 1 config entry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.version = 1
    entry.entry_id = "test_entry_v1"
    entry.data = {}
    entry.options = {}
    return entry


class TestMigrationVersion1To2:
    """Test migration from version 1 to 2."""

    @pytest.mark.asyncio
    async def test_migrate_lock_height_entity_to_static(self, mock_hass, config_entry_v1):
        """Test migration of lock_height_entity to lock_height_static."""
        config_entry_v1.options = {
            "lock_height_entity": "100",
        }

        with patch("custom_components.shadow_control.get_full_options_schema") as mock_schema:
            mock_schema.return_value = lambda x: x

            result = await async_migrate_entry(mock_hass, config_entry_v1)

        assert result is True

        call_args = mock_hass.config_entries.async_update_entry.call_args
        updated_options = call_args.kwargs["options"]

        # Old key should be removed
        assert "lock_height_entity" not in updated_options

        # New key should be present with same value
        assert "lock_height_static" in updated_options
        assert updated_options["lock_height_static"] == "100"

    @pytest.mark.asyncio
    async def test_migrate_lock_angle_entity_to_static(self, mock_hass, config_entry_v1):
        """Test migration of lock_angle_entity to lock_angle_static."""
        config_entry_v1.options = {
            "lock_angle_entity": "50",
        }

        with patch("custom_components.shadow_control.get_full_options_schema") as mock_schema:
            mock_schema.return_value = lambda x: x

            result = await async_migrate_entry(mock_hass, config_entry_v1)

        assert result is True

        call_args = mock_hass.config_entries.async_update_entry.call_args
        updated_options = call_args.kwargs["options"]

        # Old key should be removed
        assert "lock_angle_entity" not in updated_options

        # New key should be present with same value
        assert "lock_angle_static" in updated_options
        assert updated_options["lock_angle_static"] == "50"

    @pytest.mark.asyncio
    async def test_migrate_both_lock_entities(self, mock_hass, config_entry_v1):
        """Test migration of both lock entities together."""
        config_entry_v1.options = {
            "lock_height_entity": "80",
            "lock_angle_entity": "45",
        }

        with patch("custom_components.shadow_control.get_full_options_schema") as mock_schema:
            mock_schema.return_value = lambda x: x

            result = await async_migrate_entry(mock_hass, config_entry_v1)

        assert result is True

        call_args = mock_hass.config_entries.async_update_entry.call_args
        updated_options = call_args.kwargs["options"]

        # Old keys should be removed
        assert "lock_height_entity" not in updated_options
        assert "lock_angle_entity" not in updated_options

        # New keys should be present
        assert updated_options["lock_height_static"] == "80"
        assert updated_options["lock_angle_static"] == "45"

    @pytest.mark.asyncio
    async def test_migrate_sets_defaults_when_keys_missing(self, mock_hass, config_entry_v1):
        """Test that defaults (0) are set when old keys don't exist."""
        config_entry_v1.options = {}

        with patch("custom_components.shadow_control.get_full_options_schema") as mock_schema:
            mock_schema.return_value = lambda x: x

            result = await async_migrate_entry(mock_hass, config_entry_v1)

        assert result is True

        call_args = mock_hass.config_entries.async_update_entry.call_args
        updated_options = call_args.kwargs["options"]

        # Defaults should be set to 0
        assert updated_options["lock_height_static"] == 0
        assert updated_options["lock_angle_static"] == 0

    @pytest.mark.asyncio
    async def test_migrate_preserves_other_options(self, mock_hass, config_entry_v1):
        """Test that other options are preserved during migration."""
        config_entry_v1.options = {
            "lock_height_entity": "100",
            "other_option": "keep_me",
        }

        with patch("custom_components.shadow_control.get_full_options_schema") as mock_schema:
            mock_schema.return_value = lambda x: x

            result = await async_migrate_entry(mock_hass, config_entry_v1)

        assert result is True

        call_args = mock_hass.config_entries.async_update_entry.call_args
        updated_options = call_args.kwargs["options"]

        # Other options should be preserved
        assert updated_options["other_option"] == "keep_me"

    @pytest.mark.asyncio
    async def test_migrate_handles_validation_failure(self, mock_hass, config_entry_v1):
        """Test that migration returns False on validation failure."""
        config_entry_v1.options = {
            "lock_height_entity": "100",
        }

        with patch("custom_components.shadow_control.get_full_options_schema") as mock_schema:
            mock_schema.return_value = MagicMock(side_effect=vol.Invalid("Validation failed"))

            result = await async_migrate_entry(mock_hass, config_entry_v1)

        assert result is False
        mock_hass.config_entries.async_update_entry.assert_not_called()
