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


async def test_sensor_entities_created(hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_cover, mock_sun) -> None:
    """Test all sensor entities are created."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Check expected sensors exist
    expected_sensors = [
        "sensor.test_shadow_control_height",
        "sensor.test_shadow_control_angle",
        "sensor.test_shadow_control_state",
        # ... add all expected sensor entity_ids
    ]

    for sensor_id in expected_sensors:
        state = hass.states.get(sensor_id)
        assert state is not None, f"Sensor {sensor_id} not found"


async def test_button_entity_press(hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_cover, mock_sun) -> None:
    """Test button entity can be pressed."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Press the button
    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": "button.test_shadow_control_do_positioning"},
        blocking=True,
    )

    # Verify button was pressed (add appropriate assertions based on behavior)


async def test_switch_entity_toggle(hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_cover, mock_sun) -> None:
    """Test switch entity can be toggled."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Toggle the switch
    await hass.services.async_call(
        "switch",
        "turn_on",
        {"entity_id": "switch.test_shadow_control_lock"},
        blocking=True,
    )

    state = hass.states.get("switch.test_shadow_control_lock")
    assert state.state == "on"


# ========================================================================
# NEW TESTS: Button Coverage
# ========================================================================


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
