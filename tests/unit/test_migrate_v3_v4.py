"""Test config entry migration from version 3 to 4."""

from unittest.mock import MagicMock, patch

import pytest
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.shadow_control import async_migrate_entry
from custom_components.shadow_control.const import SCDynamicInput


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.config_entries = MagicMock()
    hass.config_entries.async_update_entry = MagicMock()
    return hass


@pytest.fixture
def config_entry_v3():
    """Create a version 3 config entry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.version = 3
    entry.entry_id = "test_entry_v3"
    entry.data = {}
    entry.options = {}
    return entry


class TestMigrationVersion3To4:
    """Test migration from version 3 to 4."""

    @pytest.mark.asyncio
    async def test_migrate_removes_movement_restriction_height_entity(self, mock_hass, config_entry_v3):
        """Test removal of movement_restriction_height_entity."""
        old_key = SCDynamicInput.MOVEMENT_RESTRICTION_HEIGHT_ENTITY.value
        config_entry_v3.options = {
            old_key: "some_entity_id",
        }

        with patch("custom_components.shadow_control.get_full_options_schema") as mock_schema:
            mock_schema.return_value = lambda x: x

            result = await async_migrate_entry(mock_hass, config_entry_v3)

        assert result is True

        call_args = mock_hass.config_entries.async_update_entry.call_args
        updated_options = call_args.kwargs["options"]

        # Old key should be removed
        assert old_key not in updated_options

    @pytest.mark.asyncio
    async def test_migrate_removes_movement_restriction_angle_entity(self, mock_hass, config_entry_v3):
        """Test removal of movement_restriction_angle_entity."""
        old_key = SCDynamicInput.MOVEMENT_RESTRICTION_ANGLE_ENTITY.value
        config_entry_v3.options = {
            old_key: "some_entity_id",
        }

        with patch("custom_components.shadow_control.get_full_options_schema") as mock_schema:
            mock_schema.return_value = lambda x: x

            result = await async_migrate_entry(mock_hass, config_entry_v3)

        assert result is True

        call_args = mock_hass.config_entries.async_update_entry.call_args
        updated_options = call_args.kwargs["options"]

        # Old key should be removed
        assert old_key not in updated_options

    @pytest.mark.asyncio
    async def test_migrate_removes_both_movement_restriction_entities(self, mock_hass, config_entry_v3):
        """Test removal of both movement restriction entities."""
        height_key = SCDynamicInput.MOVEMENT_RESTRICTION_HEIGHT_ENTITY.value
        angle_key = SCDynamicInput.MOVEMENT_RESTRICTION_ANGLE_ENTITY.value

        config_entry_v3.options = {
            height_key: "height_entity",
            angle_key: "angle_entity",
        }

        with patch("custom_components.shadow_control.get_full_options_schema") as mock_schema:
            mock_schema.return_value = lambda x: x

            result = await async_migrate_entry(mock_hass, config_entry_v3)

        assert result is True

        call_args = mock_hass.config_entries.async_update_entry.call_args
        updated_options = call_args.kwargs["options"]

        # Both old keys should be removed
        assert height_key not in updated_options
        assert angle_key not in updated_options

    @pytest.mark.asyncio
    async def test_migrate_when_keys_not_present(self, mock_hass, config_entry_v3):
        """Test migration succeeds when old keys are not present."""
        config_entry_v3.options = {"other_option": "value"}

        with patch("custom_components.shadow_control.get_full_options_schema") as mock_schema:
            mock_schema.return_value = lambda x: x

            result = await async_migrate_entry(mock_hass, config_entry_v3)

        assert result is True

        call_args = mock_hass.config_entries.async_update_entry.call_args
        updated_options = call_args.kwargs["options"]

        # Other options should be preserved
        assert updated_options["other_option"] == "value"

    @pytest.mark.asyncio
    async def test_migrate_preserves_other_options(self, mock_hass, config_entry_v3):
        """Test that other options are preserved during migration."""
        height_key = SCDynamicInput.MOVEMENT_RESTRICTION_HEIGHT_ENTITY.value

        config_entry_v3.options = {
            height_key: "remove_me",
            "keep_this": "important",
            "and_this": 123,
        }

        with patch("custom_components.shadow_control.get_full_options_schema") as mock_schema:
            mock_schema.return_value = lambda x: x

            result = await async_migrate_entry(mock_hass, config_entry_v3)

        assert result is True

        call_args = mock_hass.config_entries.async_update_entry.call_args
        updated_options = call_args.kwargs["options"]

        # Movement restriction should be removed
        assert height_key not in updated_options

        # Other options should be preserved
        assert updated_options["keep_this"] == "important"
        assert updated_options["and_this"] == 123

    @pytest.mark.asyncio
    async def test_migrate_with_empty_options(self, mock_hass, config_entry_v3):
        """Test migration with empty options."""
        config_entry_v3.options = {}

        with patch("custom_components.shadow_control.get_full_options_schema") as mock_schema:
            mock_schema.return_value = lambda x: x

            result = await async_migrate_entry(mock_hass, config_entry_v3)

        assert result is True

        call_args = mock_hass.config_entries.async_update_entry.call_args
        updated_options = call_args.kwargs["options"]

        # Should remain empty
        assert updated_options == {}

    @pytest.mark.asyncio
    async def test_migrate_handles_validation_failure(self, mock_hass, config_entry_v3):
        """Test that migration returns False on validation failure."""
        height_key = SCDynamicInput.MOVEMENT_RESTRICTION_HEIGHT_ENTITY.value
        config_entry_v3.options = {height_key: "entity"}

        with patch("custom_components.shadow_control.get_full_options_schema") as mock_schema:
            mock_schema.return_value = MagicMock(side_effect=vol.Invalid("Validation failed"))

            result = await async_migrate_entry(mock_hass, config_entry_v3)

        assert result is False
        mock_hass.config_entries.async_update_entry.assert_not_called()
