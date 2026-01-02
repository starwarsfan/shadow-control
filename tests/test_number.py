"""Test shadow_control entities."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.shadow_control import DOMAIN_DATA_MANAGERS, SCInternal
from custom_components.shadow_control.const import DOMAIN
from custom_components.shadow_control.number import ShadowControlNumber
from custom_components.shadow_control.number import async_setup_entry as number_async_setup_entry

@pytest.fixture
def mock_manager():
    manager = MagicMock()
    manager.logger = MagicMock()
    manager.sanitized_name = "test_instance"
    return manager

@pytest.fixture
def mock_config_entry():
    return MockConfigEntry(
        domain=DOMAIN,
        entry_id="test_entry_id",
        data={},
    )

@pytest.fixture
def mock_hass(hass, mock_manager, mock_config_entry):
    """Now 'hass' correctly refers to the HA fixture."""
    hass.data[DOMAIN_DATA_MANAGERS] = {
        mock_config_entry.entry_id: mock_manager
    }
    return hass

class TestNumberEntity:
    """Test Number entity."""

    async def test_number_async_setup_entry(self, mock_hass, mock_config_entry, mock_manager):
        """Test Number setup entry."""
        entities_added = []

        def mock_add_entities(entities):
            entities_added.extend(entities)

        await number_async_setup_entry(mock_hass, mock_config_entry, mock_add_entities)

        # Verify one Number was added
        assert len(entities_added) == 22
        assert isinstance(entities_added[0], ShadowControlNumber)
        assert entities_added[0].entity_description.key == SCInternal.LOCK_HEIGHT_MANUAL.value
