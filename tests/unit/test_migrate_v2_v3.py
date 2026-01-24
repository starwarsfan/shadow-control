"""Test config entry migration from version 2 to 3."""

from unittest.mock import MagicMock, patch

import pytest
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.shadow_control import async_migrate_entry
from custom_components.shadow_control.const import SCFacadeConfig2


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.config_entries = MagicMock()
    hass.config_entries.async_update_entry = MagicMock()
    return hass


@pytest.fixture
def config_entry_v2():
    """Create a version 2 config entry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.version = 2
    entry.entry_id = "test_entry_v2"
    entry.data = {}
    entry.options = {}
    return entry


class TestMigrationVersion2To3:
    """Test migration from version 2 to 3."""

    @pytest.mark.asyncio
    async def test_migrate_shutter_type_from_options_to_data(self, mock_hass, config_entry_v2):
        """Test migration of shutter_type from config options to config data."""
        shutter_type_key = SCFacadeConfig2.SHUTTER_TYPE_STATIC.value
        config_entry_v2.options = {
            shutter_type_key: "venetian_blind",
        }
        config_entry_v2.data = {}

        with patch("custom_components.shadow_control.get_full_options_schema") as mock_schema:
            mock_schema.return_value = lambda x: x

            result = await async_migrate_entry(mock_hass, config_entry_v2)

        assert result is True

        call_args = mock_hass.config_entries.async_update_entry.call_args
        updated_options = call_args.kwargs["options"]
        updated_data = call_args.kwargs["data"]

        # Key should be removed from options
        assert shutter_type_key not in updated_options

        # Key should be moved to data
        assert shutter_type_key in updated_data
        assert updated_data[shutter_type_key] == "venetian_blind"

    @pytest.mark.asyncio
    async def test_migrate_with_different_shutter_types(self, mock_hass, config_entry_v2):
        """Test migration with different shutter type values."""
        shutter_type_key = SCFacadeConfig2.SHUTTER_TYPE_STATIC.value

        test_types = ["roller_shutter", "awning", "vertical_blind"]

        for shutter_type in test_types:
            config_entry_v2.options = {shutter_type_key: shutter_type}
            config_entry_v2.data = {}

            with patch("custom_components.shadow_control.get_full_options_schema") as mock_schema:
                mock_schema.return_value = lambda x: x

                result = await async_migrate_entry(mock_hass, config_entry_v2)

            assert result is True

            call_args = mock_hass.config_entries.async_update_entry.call_args
            updated_data = call_args.kwargs["data"]

            assert updated_data[shutter_type_key] == shutter_type

    @pytest.mark.asyncio
    async def test_migrate_when_shutter_type_not_in_options(self, mock_hass, config_entry_v2):
        """Test migration when shutter_type is not in options."""
        config_entry_v2.options = {"other_option": "value"}
        config_entry_v2.data = {}

        with patch("custom_components.shadow_control.get_full_options_schema") as mock_schema:
            mock_schema.return_value = lambda x: x

            result = await async_migrate_entry(mock_hass, config_entry_v2)

        assert result is True

        call_args = mock_hass.config_entries.async_update_entry.call_args
        updated_options = call_args.kwargs["options"]
        updated_data = call_args.kwargs["data"]

        # Options should remain unchanged
        assert updated_options["other_option"] == "value"

        # Data should remain empty (no shutter_type to migrate)
        assert SCFacadeConfig2.SHUTTER_TYPE_STATIC.value not in updated_data

    @pytest.mark.asyncio
    async def test_migrate_preserves_existing_data(self, mock_hass, config_entry_v2):
        """Test that existing data is preserved during migration."""
        shutter_type_key = SCFacadeConfig2.SHUTTER_TYPE_STATIC.value
        config_entry_v2.options = {shutter_type_key: "roller_shutter"}
        config_entry_v2.data = {"existing_key": "existing_value"}

        with patch("custom_components.shadow_control.get_full_options_schema") as mock_schema:
            mock_schema.return_value = lambda x: x

            result = await async_migrate_entry(mock_hass, config_entry_v2)

        assert result is True

        call_args = mock_hass.config_entries.async_update_entry.call_args
        updated_data = call_args.kwargs["data"]

        # Existing data should be preserved
        assert updated_data["existing_key"] == "existing_value"

        # New data should be added
        assert updated_data[shutter_type_key] == "roller_shutter"

    @pytest.mark.asyncio
    async def test_migrate_preserves_other_options(self, mock_hass, config_entry_v2):
        """Test that other options are preserved during migration."""
        shutter_type_key = SCFacadeConfig2.SHUTTER_TYPE_STATIC.value
        config_entry_v2.options = {
            shutter_type_key: "venetian_blind",
            "keep_this": "important_value",
            "and_this": 42,
        }

        with patch("custom_components.shadow_control.get_full_options_schema") as mock_schema:
            mock_schema.return_value = lambda x: x

            result = await async_migrate_entry(mock_hass, config_entry_v2)

        assert result is True

        call_args = mock_hass.config_entries.async_update_entry.call_args
        updated_options = call_args.kwargs["options"]

        # Other options should be preserved
        assert updated_options["keep_this"] == "important_value"
        assert updated_options["and_this"] == 42

    @pytest.mark.asyncio
    async def test_migrate_handles_validation_failure(self, mock_hass, config_entry_v2):
        """Test that migration returns False on validation failure."""
        shutter_type_key = SCFacadeConfig2.SHUTTER_TYPE_STATIC.value
        config_entry_v2.options = {shutter_type_key: "venetian_blind"}

        with patch("custom_components.shadow_control.get_full_options_schema") as mock_schema:
            mock_schema.return_value = MagicMock(side_effect=vol.Invalid("Validation failed"))

            result = await async_migrate_entry(mock_hass, config_entry_v2)

        assert result is False
        mock_hass.config_entries.async_update_entry.assert_not_called()
