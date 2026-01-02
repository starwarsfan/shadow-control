"""Test shadow_control select entities."""

from unittest.mock import MagicMock, patch

import pytest
from homeassistant.components.select import SelectEntityDescription
from homeassistant.const import Platform
from homeassistant.core import State
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.shadow_control import DOMAIN_DATA_MANAGERS, SCInternal
from custom_components.shadow_control.const import (
    DOMAIN,
    SELECT_INTERNAL_TO_EXTERNAL_MAP,
    MovementRestricted,
)
from custom_components.shadow_control.select import ShadowControlSelect
from custom_components.shadow_control.select import async_setup_entry as select_async_setup_entry

# --- Fixtures ---


@pytest.fixture
def mock_manager():
    """Create a mock manager."""
    manager = MagicMock()
    manager.logger = MagicMock()
    manager.sanitized_name = "test_instance"
    return manager


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        entry_id="test_entry_id",
        data={},
        options={},
    )


@pytest.fixture
def mock_hass(hass, mock_manager, mock_config_entry):
    """Setup hass with required domain data and registered config entry."""
    mock_config_entry.add_to_hass(hass)

    hass.data[DOMAIN_DATA_MANAGERS] = {mock_config_entry.entry_id: mock_manager}
    # Ensure the select_states dictionary exists to prevent KeyErrors
    hass.data.setdefault(DOMAIN, {})["select_states"] = {}
    return hass


# --- Helper ---


def setup_test_entity(entity, hass, entity_id):
    """Set required internal HA attributes for testing."""
    entity.hass = hass
    entity.entity_id = entity_id

    # Create a more robust mock platform
    mock_platform = MagicMock()
    mock_platform.platform_name = "number"
    mock_platform.domain = DOMAIN

    # This nested structure is required for self.name to resolve without crashing
    # in newer HA versions when translation keys are present.
    mock_platform.default_language_platform_translations = MagicMock()
    mock_platform.default_language_platform_translations.get.return_value = None

    # This satisfies the internal translation lookup engine
    mock_platform.component.get_platform.return_value = mock_platform

    entity.platform = mock_platform


# --- Tests ---


class TestSelectEntity:
    """Test Select entity functionality."""

    async def test_async_setup_entry_all_added(self, mock_hass, mock_config_entry):
        """Test all select entities are added when no external entities are configured."""
        entities_added = []

        def mock_add_entities(entities):
            entities_added.extend(entities)

        await select_async_setup_entry(mock_hass, mock_config_entry, mock_add_entities)

        # select.py defines 2 entities
        assert len(entities_added) == 2
        assert isinstance(entities_added[0], ShadowControlSelect)

    async def test_async_setup_entry_skips_external(self, mock_hass, mock_config_entry):
        """Test that internal entities are skipped if an external entity is mapped."""
        internal_key = SCInternal.MOVEMENT_RESTRICTION_HEIGHT_MANUAL.value
        external_key = SELECT_INTERNAL_TO_EXTERNAL_MAP[internal_key]

        mock_hass.config_entries.async_update_entry(mock_config_entry, options={external_key: "select.external_control"})

        entities_added = []
        await select_async_setup_entry(mock_hass, mock_config_entry, entities_added.extend)

        assert len(entities_added) == 1
        assert not any(e.entity_description.key == internal_key for e in entities_added)

    async def test_registry_cleanup(self, mock_hass, mock_config_entry):
        """Test removal of deprecated entities from the registry."""
        registry = er.async_get(mock_hass)
        internal_key = SCInternal.MOVEMENT_RESTRICTION_HEIGHT_MANUAL.value
        unique_id = f"{mock_config_entry.entry_id}_{internal_key}"

        registry.async_get_or_create(
            domain=DOMAIN,
            platform=Platform.SELECT,
            unique_id=unique_id,
            config_entry=mock_config_entry,
        )

        external_key = SELECT_INTERNAL_TO_EXTERNAL_MAP[internal_key]
        mock_hass.config_entries.async_update_entry(mock_config_entry, options={external_key: "select.external_one"})

        await select_async_setup_entry(mock_hass, mock_config_entry, lambda _: None)

        assert registry.async_get_entity_id(Platform.SELECT, DOMAIN, unique_id) is None

    async def test_select_option_logic(self, mock_hass, mock_config_entry, mock_manager):
        """Test selecting an option updates hass.data and triggers state write."""
        entity = ShadowControlSelect(
            mock_hass, mock_config_entry, "test_key", SelectEntityDescription(key="test_key", name="Test"), "test_instance", mock_manager.logger
        )
        setup_test_entity(entity, mock_hass, "select.test_entity")

        # Dynamically pick a valid option from the Enum to avoid AttributeError
        valid_options = [state.value for state in MovementRestricted]
        test_option = valid_options[0]

        await entity.async_select_option(test_option)

        # Verify storage in the custom map
        assert mock_hass.data[DOMAIN]["select_states"][entity.unique_id] == test_option
        assert entity.current_option == test_option

    async def test_unique_id_mapping(self, mock_hass, mock_config_entry, mock_manager):
        """Test that entities register themselves in the unique_id_map."""
        entity = ShadowControlSelect(
            mock_hass, mock_config_entry, "test_key", SelectEntityDescription(key="test_key", name="Test"), "test_instance", mock_manager.logger
        )
        setup_test_entity(entity, mock_hass, "select.test_unique")

        await entity.async_added_to_hass()

        assert mock_hass.data[DOMAIN]["unique_id_map"][entity.unique_id] == "select.test_unique"

    async def test_restore_state_logic(self, mock_hass, mock_config_entry, mock_manager):
        """Test successful state restoration into select_states."""
        entity = ShadowControlSelect(
            mock_hass, mock_config_entry, "test_key", SelectEntityDescription(key="test_key", name="Test"), "test_instance", mock_manager.logger
        )
        setup_test_entity(entity, mock_hass, "select.test_restore")

        # Dynamically pick a valid option
        valid_options = [state.value for state in MovementRestricted]
        restored_val = valid_options[-1]  # Pick the last option
        mock_state = State(entity.entity_id, restored_val)

        with patch("homeassistant.helpers.restore_state.RestoreEntity.async_get_last_state", return_value=mock_state):
            await entity.async_added_to_hass()

        # Verify the restored state reached the data dict
        assert mock_hass.data[DOMAIN]["select_states"][entity.unique_id] == restored_val
        assert entity.current_option == restored_val
