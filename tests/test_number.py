"""Test shadow_control entities."""

from unittest.mock import MagicMock, patch

import pytest
from homeassistant.components.number import NumberEntityDescription
from homeassistant.const import Platform
from homeassistant.core import State
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.shadow_control import DOMAIN_DATA_MANAGERS, SCInternal
from custom_components.shadow_control.const import (
    DOMAIN,
    INTERNAL_TO_DEFAULTS_MAP,
    NUMBER_INTERNAL_TO_EXTERNAL_MAP,
)
from custom_components.shadow_control.number import ShadowControlNumber
from custom_components.shadow_control.number import async_setup_entry as number_async_setup_entry

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


class TestNumberEntity:
    """Test Number entity functionality."""

    async def test_async_setup_entry_all_added(self, mock_hass, mock_config_entry):
        """Test all 22 entities are added when no external entities are configured."""
        entities_added = []
        await number_async_setup_entry(mock_hass, mock_config_entry, entities_added.extend)
        assert len(entities_added) == 22

    async def test_async_setup_entry_skips_external(self, mock_hass, mock_config_entry):
        """Test that internal entities are skipped if an external entity is mapped."""
        internal_key = SCInternal.LOCK_HEIGHT_MANUAL.value
        external_key = NUMBER_INTERNAL_TO_EXTERNAL_MAP[internal_key]
        mock_hass.config_entries.async_update_entry(mock_config_entry, options={external_key: "number.external_sensor"})

        entities_added = []
        await number_async_setup_entry(mock_hass, mock_config_entry, entities_added.extend)
        assert len(entities_added) == 21

    async def test_registry_cleanup(self, mock_hass, mock_config_entry):
        """Test removal of deprecated entities from the registry."""
        registry = er.async_get(mock_hass)
        internal_key = SCInternal.LOCK_HEIGHT_MANUAL.value
        unique_id = f"{mock_config_entry.entry_id}_{internal_key}"

        registry.async_get_or_create(
            domain=DOMAIN,
            platform=Platform.NUMBER,
            unique_id=unique_id,
            config_entry=mock_config_entry,
        )

        external_key = NUMBER_INTERNAL_TO_EXTERNAL_MAP[internal_key]
        mock_hass.config_entries.async_update_entry(mock_config_entry, options={external_key: "number.external_one"})
        await number_async_setup_entry(mock_hass, mock_config_entry, lambda _: None)
        assert registry.async_get_entity_id(Platform.NUMBER, DOMAIN, unique_id) is None

    async def test_number_state_rounding(self, mock_hass, mock_config_entry, mock_manager):
        """Test that the state property rounds and casts to string."""
        entity = ShadowControlNumber(
            mock_hass, mock_config_entry, "test_key", NumberEntityDescription(key="test_key", name="Test"), "test_instance", mock_manager.logger
        )
        entity._value = 12.6
        assert entity.state == "13"
        entity._value = 12.4
        assert entity.state == "12"

    async def test_unique_id_mapping(self, mock_hass, mock_config_entry, mock_manager):
        """Test that entities register themselves in the unique_id_map."""
        entity = ShadowControlNumber(
            mock_hass, mock_config_entry, "test_key", NumberEntityDescription(key="test_key", name="Test"), "test_instance", mock_manager.logger
        )
        setup_test_entity(entity, mock_hass, "number.test_123")
        await entity.async_added_to_hass()
        assert mock_hass.data[DOMAIN]["unique_id_map"][entity.unique_id] == "number.test_123"

    async def test_restore_state_logic(self, mock_hass, mock_config_entry, mock_manager):
        """Test successful state restoration."""
        entity = ShadowControlNumber(
            mock_hass,
            mock_config_entry,
            SCInternal.LOCK_HEIGHT_MANUAL.value,
            NumberEntityDescription(key=SCInternal.LOCK_HEIGHT_MANUAL.value, name="Test"),
            "test_instance",
            mock_manager.logger,
        )
        setup_test_entity(entity, mock_hass, "number.test_restore")
        mock_state = State(entity.entity_id, "75.0")

        with patch("homeassistant.helpers.restore_state.RestoreEntity.async_get_last_state", return_value=mock_state):
            await entity.async_added_to_hass()

        assert entity.native_value == 75.0

    async def test_fallback_to_defaults(self, mock_hass, mock_config_entry, mock_manager):
        """Test fallback to defaults when no state is restored."""
        target_key = SCInternal.LOCK_HEIGHT_MANUAL
        entity = ShadowControlNumber(
            mock_hass,
            mock_config_entry,
            target_key.value,
            NumberEntityDescription(key=target_key.value, name="Test"),
            "test_instance",
            mock_manager.logger,
        )
        setup_test_entity(entity, mock_hass, "number.test_fallback")

        with patch("homeassistant.helpers.restore_state.RestoreEntity.async_get_last_state", return_value=None):
            await entity.async_added_to_hass()

        expected_default = INTERNAL_TO_DEFAULTS_MAP[target_key]
        assert entity.native_value == expected_default
