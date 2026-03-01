"""Unit tests for Shadow Control time text entities."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.text import DOMAIN as TEXT_DOMAIN
from homeassistant.components.text import TextEntityDescription
from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.shadow_control.const import (
    DOMAIN,
    DOMAIN_DATA_MANAGERS,
    INTERNAL_TO_DEFAULTS_MAP,
    SCInternal,
)
from custom_components.shadow_control.time import (
    TIME_PATTERN,
    ShadowControlTimeText,
    async_setup_entry,
)


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    entry = MagicMock()
    entry.entry_id = "test_entry_123"
    entry.options = {}
    return entry


@pytest.fixture
def mock_manager():
    """Create a mock Shadow Control manager."""
    manager = MagicMock()
    manager.logger = MagicMock()
    manager.sanitized_name = "test_instance"
    manager.async_calculate_and_apply_cover_position = AsyncMock()
    return manager


@pytest.fixture
async def hass_with_manager(hass: HomeAssistant, mock_config_entry, mock_manager):
    """Setup Home Assistant with mock manager."""
    # Ensure DOMAIN exists in hass.data
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    # Ensure DOMAIN_DATA_MANAGERS exists
    if DOMAIN_DATA_MANAGERS not in hass.data:
        hass.data[DOMAIN_DATA_MANAGERS] = {}

    # Set the manager
    hass.data[DOMAIN_DATA_MANAGERS][mock_config_entry.entry_id] = mock_manager

    # Ensure unique_id_map exists
    if "unique_id_map" not in hass.data[DOMAIN]:
        hass.data[DOMAIN]["unique_id_map"] = {}

    return hass


class TestTimePattern:
    """Test the time regex pattern validation."""

    def test_valid_times(self):
        """Test valid time formats."""
        valid_times = [
            "00:00",
            "06:00",
            "12:30",
            "23:59",
            "08:15",
            "20:00",
        ]
        for time_str in valid_times:
            assert TIME_PATTERN.match(time_str), f"{time_str} should be valid"

    def test_invalid_times(self):
        """Test invalid time formats."""
        invalid_times = [
            "24:00",  # Hour too high
            "25:00",  # Hour too high
            "23:60",  # Minute too high
            "6:00",  # Missing leading zero
            "06:0",  # Missing minute digit
            "6:0",  # Missing both leading zeros
            "abc",  # Not a time
            "12:345",  # Too many minute digits
            "123:45",  # Too many hour digits
            "",  # Empty string
            "12",  # Missing minutes
            "12:",  # Missing minute value
            ":30",  # Missing hour value
        ]
        for time_str in invalid_times:
            assert not TIME_PATTERN.match(time_str), f"{time_str} should be invalid"


class TestAsyncSetupEntry:
    """Test the async_setup_entry function."""

    async def test_setup_with_no_external_entities(self, hass_with_manager, mock_config_entry):
        """Test setup when no external entities are configured."""
        mock_add_entities = MagicMock()

        await async_setup_entry(hass_with_manager, mock_config_entry, mock_add_entities)

        # Should add 2 time text entities (open_not_before, close_not_later_than)
        assert mock_add_entities.called
        entities = mock_add_entities.call_args[0][0]
        assert len(entities) == 2
        assert all(isinstance(e, ShadowControlTimeText) for e in entities)

    async def test_setup_with_external_entity_configured(self, hass_with_manager, mock_config_entry):
        """Test setup when external entity is configured - internal entity should be skipped."""
        mock_config_entry.options = {"dawn_open_not_before_entity": "input_datetime.wake_time"}
        mock_add_entities = MagicMock()

        await async_setup_entry(hass_with_manager, mock_config_entry, mock_add_entities)

        entities = mock_add_entities.call_args[0][0]
        # Should only add 1 entity (close_not_later_than), skip open_not_before
        assert len(entities) == 1
        assert entities[0].entity_description.key == SCInternal.DAWN_CLOSE_NOT_LATER_THAN_MANUAL.value

    async def test_cleanup_deprecated_entities(self, hass_with_manager, mock_config_entry):
        """Test that deprecated entities are removed from registry."""
        # Setup registry with an old entity
        registry = er.async_get(hass_with_manager)
        old_entity = registry.async_get_or_create(
            TEXT_DOMAIN,
            DOMAIN,
            f"{mock_config_entry.entry_id}_{SCInternal.DAWN_OPEN_NOT_BEFORE_MANUAL.value}",
        )

        # Configure external entity so internal one should be removed
        mock_config_entry.options = {"dawn_open_not_before_entity": "input_datetime.wake_time"}
        mock_add_entities = MagicMock()

        await async_setup_entry(hass_with_manager, mock_config_entry, mock_add_entities)

        # Old entity should be removed from registry
        assert registry.async_get(old_entity.entity_id) is None


class TestShadowControlTimeText:
    """Test the ShadowControlTimeText entity."""

    @pytest.fixture
    def time_entity(self, hass_with_manager, mock_config_entry):
        """Create a time text entity."""
        entity = ShadowControlTimeText(
            hass_with_manager,
            mock_config_entry,
            key=SCInternal.DAWN_OPEN_NOT_BEFORE_MANUAL.value,
            instance_name="Test Instance",
            logger=MagicMock(),
            description=TextEntityDescription(
                key=SCInternal.DAWN_OPEN_NOT_BEFORE_MANUAL.value,
                name="Dawn open not before",
            ),
            icon="mdi:clock-start",
        )
        # Mock the platform
        entity.platform = MagicMock()
        entity.platform.platform_name = DOMAIN
        return entity

    def test_entity_properties(self, time_entity):
        """Test basic entity properties."""
        assert time_entity.unique_id == "test_entry_123_dawn_open_not_before_manual"
        assert time_entity._attr_pattern == TIME_PATTERN.pattern
        assert time_entity._attr_mode == "text"
        assert time_entity._attr_native_max == 5
        assert time_entity._attr_native_min == 5
        assert time_entity._attr_icon == "mdi:clock-start"

    async def test_set_valid_time(self, time_entity):
        """Test setting a valid time value."""
        time_entity.entity_id = "text.test_instance_dawn_open_not_before"
        time_entity.async_write_ha_state = MagicMock()

        await time_entity.async_set_value("06:00")

        assert time_entity.native_value == "06:00"
        assert time_entity._state == "06:00"

    async def test_set_invalid_time_raises_error(self, time_entity):
        """Test that setting invalid time raises ValueError."""
        time_entity.entity_id = "text.test_instance_dawn_open_not_before"
        time_entity.async_write_ha_state = MagicMock()

        with pytest.raises(ValueError, match="Invalid time format"):
            await time_entity.async_set_value("25:00")

        with pytest.raises(ValueError, match="Invalid time format"):
            await time_entity.async_set_value("6:00")

        with pytest.raises(ValueError, match="Invalid time format"):
            await time_entity.async_set_value("abc")

    async def test_notify_integration_called(self, time_entity, mock_manager):
        """Test that changing value notifies the integration."""
        time_entity.entity_id = "text.test_instance_dawn_open_not_before"
        time_entity.async_write_ha_state = MagicMock()

        await time_entity.async_set_value("08:30")

        # Should trigger recalculation
        assert mock_manager.async_calculate_and_apply_cover_position.called

    async def test_restore_valid_state(self, hass_with_manager, time_entity):
        """Test restoring a valid state after HA restart."""
        # Set entity_id for the test
        time_entity.entity_id = "text.test_instance_dawn_open_not_before"

        # Mock restored state
        mock_state = MagicMock()
        mock_state.state = "07:15"

        with patch.object(time_entity, "async_get_last_state", return_value=mock_state):
            await time_entity.async_added_to_hass()

        assert time_entity._state == "07:15"

    async def test_restore_invalid_state_uses_default(self, hass_with_manager, time_entity):
        """Test that invalid restored state falls back to default."""
        # Set entity_id for the test
        time_entity.entity_id = "text.test_instance_dawn_open_not_before"

        # Mock restored state with invalid format
        mock_state = MagicMock()
        mock_state.state = "invalid_time"

        with (
            patch.object(time_entity, "async_get_last_state", return_value=mock_state),
            patch.object(time_entity, "_get_default_value", return_value=None),
        ):
            await time_entity.async_added_to_hass()

        # Should use default (None in this case)
        assert time_entity._state is None

    async def test_restore_unknown_state_uses_default(self, hass_with_manager, time_entity):
        """Test that unknown/unavailable state uses default."""
        # Set entity_id for the test
        time_entity.entity_id = "text.test_instance_dawn_open_not_before"

        # Mock restored state as unknown
        mock_state = MagicMock()
        mock_state.state = STATE_UNKNOWN

        with (
            patch.object(time_entity, "async_get_last_state", return_value=mock_state),
            patch.object(time_entity, "_get_default_value", return_value=None),
        ):
            await time_entity.async_added_to_hass()

        assert time_entity._state is None

    async def test_no_restored_state_uses_default(self, hass_with_manager, time_entity):
        """Test that no restored state uses default value."""
        # Set entity_id for the test
        time_entity.entity_id = "text.test_instance_dawn_open_not_before"

        with (
            patch.object(time_entity, "async_get_last_state", return_value=None),
            patch.object(time_entity, "_get_default_value", return_value=None),
        ):
            await time_entity.async_added_to_hass()

        assert time_entity._state is None

    def test_get_default_value_from_map(self, time_entity):
        """Test getting default value from INTERNAL_TO_DEFAULTS_MAP."""
        # Mock the defaults map
        with patch.dict(INTERNAL_TO_DEFAULTS_MAP, {SCInternal.DAWN_OPEN_NOT_BEFORE_MANUAL: "06:00"}):
            default = time_entity._get_default_value()
            assert default == "06:00"

    def test_get_default_value_invalid_format_returns_none(self, time_entity):
        """Test that invalid default format returns None."""
        # Mock the defaults map with invalid time
        with patch.dict(INTERNAL_TO_DEFAULTS_MAP, {SCInternal.DAWN_OPEN_NOT_BEFORE_MANUAL: "invalid"}):
            default = time_entity._get_default_value()
            assert default is None

    def test_get_default_value_no_default_returns_none(self, time_entity):
        """Test that missing default returns None."""
        # Mock empty defaults map
        with patch.dict(INTERNAL_TO_DEFAULTS_MAP, {}, clear=True):
            default = time_entity._get_default_value()
            assert default is None

    async def test_unique_id_map_registration(self, hass_with_manager, time_entity):
        """Test that entity registers in unique_id_map."""
        # Set entity_id for the test
        time_entity.entity_id = "text.test_instance_dawn_open_not_before"

        await time_entity.async_added_to_hass()

        unique_id_map = hass_with_manager.data[DOMAIN]["unique_id_map"]
        assert time_entity.unique_id in unique_id_map
        assert unique_id_map[time_entity.unique_id] == time_entity.entity_id


class TestTimeEntityIntegration:
    """Integration tests for time entities."""

    async def test_both_entities_created_by_default(self, hass_with_manager, mock_config_entry):
        """Test that both time entities are created when no external entities configured."""
        mock_add_entities = MagicMock()

        await async_setup_entry(hass_with_manager, mock_config_entry, mock_add_entities)

        entities = mock_add_entities.call_args[0][0]
        entity_keys = [e.entity_description.key for e in entities]

        assert SCInternal.DAWN_OPEN_NOT_BEFORE_MANUAL.value in entity_keys
        assert SCInternal.DAWN_CLOSE_NOT_LATER_THAN_MANUAL.value in entity_keys

    async def test_entity_value_change_triggers_recalculation(self, hass_with_manager, mock_config_entry, mock_manager):
        """Test that changing entity value triggers integration recalculation."""
        entity = ShadowControlTimeText(
            hass_with_manager,
            mock_config_entry,
            key=SCInternal.DAWN_OPEN_NOT_BEFORE_MANUAL.value,
            instance_name="Test",
            logger=MagicMock(),
            description=TextEntityDescription(
                key=SCInternal.DAWN_OPEN_NOT_BEFORE_MANUAL.value,
                name="Test",
            ),
        )
        # Mock the platform
        entity.platform = MagicMock()
        entity.platform.platform_name = DOMAIN
        entity.entity_id = "text.test_dawn_open_not_before"
        entity.async_write_ha_state = MagicMock()

        await entity.async_set_value("07:00")

        # Verify manager was notified
        mock_manager.async_calculate_and_apply_cover_position.assert_called_once()

    async def test_validation_prevents_invalid_values(self, hass_with_manager, mock_config_entry):
        """Test that validation prevents storing invalid time values."""
        entity = ShadowControlTimeText(
            hass_with_manager,
            mock_config_entry,
            key=SCInternal.DAWN_OPEN_NOT_BEFORE_MANUAL.value,
            instance_name="Test",
            logger=MagicMock(),
            description=TextEntityDescription(
                key=SCInternal.DAWN_OPEN_NOT_BEFORE_MANUAL.value,
                name="Test",
            ),
        )
        # Mock the platform
        entity.platform = MagicMock()
        entity.platform.platform_name = DOMAIN
        entity.entity_id = "text.test_dawn_open_not_before"
        entity.async_write_ha_state = MagicMock()

        # Try to set invalid values
        invalid_values = ["24:00", "6:00", "abc", "12:345", ""]

        for invalid in invalid_values:
            with pytest.raises(ValueError, match="Invalid time format"):
                await entity.async_set_value(invalid)

            # State should remain None (not set)
            assert entity._state is None
