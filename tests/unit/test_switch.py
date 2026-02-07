"""Test shadow_control switch entities."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.shadow_control import DOMAIN_DATA_MANAGERS
from custom_components.shadow_control.const import (
    DEBUG_ENABLED,
    DOMAIN,
    SWITCH_INTERNAL_TO_EXTERNAL_MAP,
    SCInternal,
)
from custom_components.shadow_control.switch import (
    ShadowControlConfigSwitch,
    ShadowControlSwitch,
)
from custom_components.shadow_control.switch import async_setup_entry as switch_async_setup_entry


def setup_test_entity(entity, hass, entity_id):
    """Set required internal HA attributes for switch testing."""
    entity.hass = hass
    entity.entity_id = entity_id
    mock_platform = MagicMock()
    mock_platform.platform_name = "switch"
    mock_platform.domain = DOMAIN
    mock_platform.default_language_platform_translations.get.return_value = None
    entity.platform = mock_platform


@pytest.fixture
def mock_manager():
    """Mock manager for switch notifications."""
    manager = MagicMock()
    manager.logger = MagicMock()
    manager.sanitized_name = "test_shutter"
    # FIX: Use AsyncMock because the code awaits this method
    manager.async_calculate_and_apply_cover_position = AsyncMock()
    return manager


@pytest.fixture
def mock_config_entry():
    """Mock config entry with initial options."""
    return MockConfigEntry(
        domain=DOMAIN,
        entry_id="test_entry_id",
        data={},
        options={
            DEBUG_ENABLED: False,
            SCInternal.SHADOW_CONTROL_ENABLED_MANUAL.value: True,
        },
    )


@pytest.fixture
def mock_hass(hass, mock_manager, mock_config_entry):
    """Setup hass with required data."""
    mock_config_entry.add_to_hass(hass)
    hass.data[DOMAIN_DATA_MANAGERS] = {mock_config_entry.entry_id: mock_manager}
    return hass


class TestSwitchEntities:
    """Test Switch platform logic."""

    async def test_async_setup_entry_filtering(self, mock_hass, mock_config_entry):
        """Test that switches are filtered/added correctly."""
        entities_added = []
        await switch_async_setup_entry(mock_hass, mock_config_entry, entities_added.extend)
        # 5 switches total in your async_setup_entry
        assert len(entities_added) == 5

    async def test_config_switch_toggles_options(self, mock_hass, mock_config_entry, mock_manager):
        """Test ShadowControlConfigSwitch updates the ConfigEntry options."""
        switch = ShadowControlConfigSwitch(
            mock_hass,
            mock_config_entry,
            key=DEBUG_ENABLED,
            description=MagicMock(key=DEBUG_ENABLED),
            instance_name="Test",
            logger=mock_manager.logger,
        )
        setup_test_entity(switch, mock_hass, "switch.test_debug")

        assert switch.is_on is False
        await switch.async_turn_on()
        assert mock_config_entry.options[DEBUG_ENABLED] is True

    async def test_switch_notifies_manager(self, mock_hass, mock_config_entry, mock_manager):
        """Test ShadowControlSwitch updates state and notifies manager."""
        key = SCInternal.SHADOW_CONTROL_ENABLED_MANUAL.value
        switch = ShadowControlSwitch(
            mock_hass,
            mock_config_entry,
            key=key,
            description=MagicMock(key=key),
            instance_name="Test",
            logger=mock_manager.logger,
        )
        setup_test_entity(switch, mock_hass, "switch.test_manual")

        await switch.async_turn_on()
        assert switch.is_on is True

        # Wait for the async_create_task to finish
        await mock_hass.async_block_till_done()
        mock_manager.async_calculate_and_apply_cover_position.assert_called_once_with(None)

    async def test_switch_registry_cleanup(self, mock_hass, mock_config_entry, mock_manager):
        """Test that internal switches are removed if an external mapping is present."""
        registry = er.async_get(mock_hass)

        # 1. Identify an internal key that has an external mapping
        internal_key = SCInternal.SHADOW_CONTROL_ENABLED_MANUAL.value
        external_key = SWITCH_INTERNAL_TO_EXTERNAL_MAP.get(internal_key)

        # 2. Update options to simulate an external entity is now configured
        mock_hass.config_entries.async_update_entry(mock_config_entry, options={external_key: "switch.external_real_device"})

        # 3. Pre-create the internal entity in the registry
        unique_id = f"{mock_config_entry.entry_id}_{internal_key}"
        registry.async_get_or_create(
            SWITCH_DOMAIN,
            DOMAIN,
            unique_id,
            config_entry=mock_config_entry,
        )

        # 4. Run setup - this should trigger the cleanup logic in PART 2
        await switch_async_setup_entry(mock_hass, mock_config_entry, lambda _: None)

        # 5. Verify it was removed
        assert registry.async_get_entity_id(SWITCH_DOMAIN, DOMAIN, unique_id) is None
