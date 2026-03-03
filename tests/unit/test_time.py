"""Unit tests for Shadow Control time entities."""

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.time import DOMAIN as TIME_DOMAIN
from homeassistant.components.time import TimeEntityDescription
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
    ShadowControlTimeEntity,
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


class TestTimeEntityValues:
    """Test TimeEntity value handling (datetime.time objects)."""

    def test_valid_time_objects(self):
        """Test that valid datetime.time objects work correctly."""
        valid_times = [
            datetime.time(0, 0),
            datetime.time(6, 0),
            datetime.time(12, 30),
            datetime.time(23, 59),
        ]
        for t in valid_times:
            assert isinstance(t, datetime.time)

    def test_time_state_string_format(self):
        """Test that HA formats time as HH:MM:SS string."""
        t = datetime.time(6, 30)
        assert t.strftime("%H:%M:%S") == "06:30:00"


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
        assert all(isinstance(e, ShadowControlTimeEntity) for e in entities)

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
            TIME_DOMAIN,
            DOMAIN,
            f"{mock_config_entry.entry_id}_{SCInternal.DAWN_OPEN_NOT_BEFORE_MANUAL.value}",
        )

        # Configure external entity so internal one should be removed
        mock_config_entry.options = {"dawn_open_not_before_entity": "input_datetime.wake_time"}
        mock_add_entities = MagicMock()

        await async_setup_entry(hass_with_manager, mock_config_entry, mock_add_entities)

        # Old entity should be removed from registry
        assert registry.async_get(old_entity.entity_id) is None


class TestShadowControlTimeEntity:
    """Test the ShadowControlTimeEntity entity."""

    @pytest.fixture
    def time_entity(self, hass_with_manager, mock_config_entry):
        """Create a time entity."""
        entity = ShadowControlTimeEntity(
            hass_with_manager,
            mock_config_entry,
            key=SCInternal.DAWN_OPEN_NOT_BEFORE_MANUAL.value,
            instance_name="Test Instance",
            logger=MagicMock(),
            description=TimeEntityDescription(
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
        assert time_entity._attr_icon == "mdi:clock-start"

    async def test_set_valid_time(self, time_entity):
        """Test setting a valid time value."""
        time_entity.entity_id = "time.test_instance_dawn_open_not_before"
        time_entity.async_write_ha_state = MagicMock()

        t = datetime.time(6, 0)
        await time_entity.async_set_value(t)

        assert time_entity.native_value == t
        assert time_entity._state == t

    async def test_set_time_triggers_state_write(self, time_entity):
        """Test that setting a time value writes HA state."""
        time_entity.entity_id = "time.test_instance_dawn_open_not_before"
        time_entity.async_write_ha_state = MagicMock()

        t = datetime.time(7, 30)
        await time_entity.async_set_value(t)

        time_entity.async_write_ha_state.assert_called_once()
        assert time_entity._state == t

    async def test_notify_integration_called(self, time_entity, mock_manager):
        """Test that changing value notifies the integration."""
        time_entity.entity_id = "time.test_instance_dawn_open_not_before"
        time_entity.async_write_ha_state = MagicMock()

        await time_entity.async_set_value(datetime.time(8, 30))

        # Should trigger recalculation
        assert mock_manager.async_calculate_and_apply_cover_position.called

    async def test_restore_valid_state(self, hass_with_manager, time_entity):
        """Test restoring a valid state after HA restart."""
        time_entity.entity_id = "time.test_instance_dawn_open_not_before"

        # HA stores TimeEntity state as "HH:MM:SS"
        mock_state = MagicMock()
        mock_state.state = "07:15:00"

        with patch.object(time_entity, "async_get_last_state", return_value=mock_state):
            await time_entity.async_added_to_hass()

        assert time_entity._state == datetime.time(7, 15)

    async def test_restore_invalid_state_uses_default(self, hass_with_manager, time_entity):
        """Test that invalid restored state falls back to default."""
        # Set entity_id for the test
        time_entity.entity_id = "time.test_instance_dawn_open_not_before"

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
        time_entity.entity_id = "time.test_instance_dawn_open_not_before"

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
        time_entity.entity_id = "time.test_instance_dawn_open_not_before"

        with (
            patch.object(time_entity, "async_get_last_state", return_value=None),
            patch.object(time_entity, "_get_default_value", return_value=None),
        ):
            await time_entity.async_added_to_hass()

        assert time_entity._state is None

    def test_get_default_value_from_map(self, time_entity):
        """Test getting default value from INTERNAL_TO_DEFAULTS_MAP."""
        with patch.dict(INTERNAL_TO_DEFAULTS_MAP, {SCInternal.DAWN_OPEN_NOT_BEFORE_MANUAL: "06:00"}):
            default = time_entity._get_default_value()
            assert default == datetime.time(6, 0)

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
        time_entity.entity_id = "time.test_instance_dawn_open_not_before"

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
        entity = ShadowControlTimeEntity(
            hass_with_manager,
            mock_config_entry,
            key=SCInternal.DAWN_OPEN_NOT_BEFORE_MANUAL.value,
            instance_name="Test",
            logger=MagicMock(),
            description=TimeEntityDescription(
                key=SCInternal.DAWN_OPEN_NOT_BEFORE_MANUAL.value,
                name="Test",
            ),
        )
        # Mock the platform
        entity.platform = MagicMock()
        entity.platform.platform_name = DOMAIN
        entity.entity_id = "time.test_dawn_open_not_before"
        entity.async_write_ha_state = MagicMock()

        await entity.async_set_value(datetime.time(7, 0))

        # Verify manager was notified
        mock_manager.async_calculate_and_apply_cover_position.assert_called_once()

    async def test_multiple_value_changes(self, hass_with_manager, mock_config_entry, mock_manager):
        """Test that multiple value changes are each reflected correctly."""
        entity = ShadowControlTimeEntity(
            hass_with_manager,
            mock_config_entry,
            key=SCInternal.DAWN_OPEN_NOT_BEFORE_MANUAL.value,
            instance_name="Test",
            logger=MagicMock(),
            description=TimeEntityDescription(
                key=SCInternal.DAWN_OPEN_NOT_BEFORE_MANUAL.value,
                name="Test",
            ),
        )
        entity.platform = MagicMock()
        entity.platform.platform_name = DOMAIN
        entity.entity_id = "time.test_dawn_open_not_before"
        entity.async_write_ha_state = MagicMock()

        for t in [datetime.time(6, 0), datetime.time(7, 30), datetime.time(23, 59)]:
            await entity.async_set_value(t)
            assert entity._state == t
            assert entity.native_value == t
