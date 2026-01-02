"""Test shadow_control entities."""

from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest
from homeassistant.components.button import ButtonEntityDescription
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.shadow_control import DOMAIN_DATA_MANAGERS, SCInternal
from custom_components.shadow_control.button import ShadowControlButton
from custom_components.shadow_control.button import async_setup_entry as button_async_setup_entry
from custom_components.shadow_control.const import DOMAIN


class TestButtonEntity:
    """Test Button entity."""

    @pytest.fixture
    def mock_manager(self):
        """Create a mock manager."""
        manager = MagicMock()
        manager.logger = MagicMock()
        manager.sanitized_name = "test_instance"
        manager.async_trigger_enforce_positioning = AsyncMock()
        return manager

    @pytest.fixture
    def mock_config_entry(self):
        """Create a mock config entry."""
        return MockConfigEntry(
            domain=DOMAIN,
            entry_id="test_entry_id",
            data={},
        )

    @pytest.fixture
    def mock_hass(self, mock_manager, mock_config_entry):
        """Create a mock Home Assistant instance."""
        hass = MagicMock(spec=HomeAssistant)
        hass.data = {DOMAIN_DATA_MANAGERS: {mock_config_entry.entry_id: mock_manager}}
        return hass

    async def test_button_async_setup_entry(self, mock_hass, mock_config_entry, mock_manager):
        """Test button setup entry."""
        entities_added = []

        # ✅ FIX: Nicht async machen, sondern synchron
        def mock_add_entities(entities):
            entities_added.extend(entities)

        await button_async_setup_entry(mock_hass, mock_config_entry, mock_add_entities)

        # Verify one button was added
        assert len(entities_added) == 1
        assert isinstance(entities_added[0], ShadowControlButton)
        assert entities_added[0].entity_description.key == SCInternal.ENFORCE_POSITIONING_MANUAL.value

    async def test_button_press_triggers_enforce_positioning(self, mock_hass, mock_config_entry, mock_manager):
        """Test that pressing button triggers enforce positioning."""
        button = ShadowControlButton(
            hass=mock_hass,
            config_entry=mock_config_entry,
            key=SCInternal.ENFORCE_POSITIONING_MANUAL.value,
            description=ButtonEntityDescription(
                key=SCInternal.ENFORCE_POSITIONING_MANUAL.value,
                translation_key=SCInternal.ENFORCE_POSITIONING_MANUAL.value,
                icon="mdi:ray-start-end",
            ),
            logger=mock_manager.logger,
            instance_name="test_instance",
            name="Trigger",
            icon="mdi:developer-board",
        )

        # ✅ FIX: Mock the name property to avoid platform lookup
        with patch.object(type(button), "name", new_callable=PropertyMock) as mock_name:
            mock_name.return_value = "Trigger"

            # Press the button
            await button.async_press()

        # Verify enforce positioning was called
        mock_manager.async_trigger_enforce_positioning.assert_called_once()

        # Verify logging
        mock_manager.logger.debug.assert_called_once()
        mock_manager.logger.info.assert_called_once_with("Enforce positioning triggered via button")

    def test_button_attributes(self, mock_hass, mock_config_entry, mock_manager):
        """Test button entity attributes are set correctly."""
        button = ShadowControlButton(
            hass=mock_hass,
            config_entry=mock_config_entry,
            key=SCInternal.ENFORCE_POSITIONING_MANUAL.value,
            description=ButtonEntityDescription(
                key=SCInternal.ENFORCE_POSITIONING_MANUAL.value,
                translation_key=SCInternal.ENFORCE_POSITIONING_MANUAL.value,
                icon="mdi:ray-start-end",
            ),
            logger=mock_manager.logger,
            instance_name="test_instance",
            name="Trigger",
            icon="mdi:developer-board",
        )

        # Verify attributes
        assert button._attr_unique_id == f"{mock_config_entry.entry_id}_{SCInternal.ENFORCE_POSITIONING_MANUAL.value}"
        assert button._attr_has_entity_name is True
        assert button._attr_icon == "mdi:developer-board"
        assert button._attr_translation_key == SCInternal.ENFORCE_POSITIONING_MANUAL.value

        # Verify device info
        assert button._attr_device_info is not None
        assert (DOMAIN, mock_config_entry.entry_id) in button._attr_device_info["identifiers"]
