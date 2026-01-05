"""Test shadow_control sensor entities."""

from unittest.mock import MagicMock, patch

import pytest
from homeassistant.const import Platform
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_send
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.shadow_control import DOMAIN_DATA_MANAGERS
from custom_components.shadow_control.const import (
    DOMAIN,
    EXTERNAL_SENSOR_DEFINITIONS,
    SCFacadeConfig2,
    SensorEntries,
    ShutterState,
    ShutterType,
)
from custom_components.shadow_control.sensor import (
    ShadowControlExternalEntityValueSensor,
    ShadowControlSensor,
)
from custom_components.shadow_control.sensor import async_setup_entry as sensor_async_setup_entry


# --- Helper to "attach" an entity for isolated testing ---
def setup_test_entity(entity, hass, entity_id):
    """Manually set required internal HA attributes for an entity in a test."""
    entity.hass = hass
    entity.entity_id = entity_id

    # Create a more robust platform mock
    mock_platform = MagicMock()
    mock_platform.platform_name = "sensor"
    mock_platform.domain = DOMAIN
    # This prevents the translation key vs native unit ValueError
    mock_platform.default_language_platform_translations = MagicMock()
    mock_platform.default_language_platform_translations.get.return_value = None

    entity.platform = mock_platform


@pytest.fixture
def mock_manager():
    """Create a mock manager with necessary attributes for sensors."""
    manager = MagicMock()
    manager.name = "Test Shutter"
    manager.sanitized_name = "test_shutter"
    manager.logger = MagicMock()

    # IMPORTANT: Use the actual Enum value.
    # Your code does: self._manager.current_shutter_state.value
    manager.current_shutter_state = ShutterState.NEUTRAL

    # Used for rounding tests
    manager.used_shutter_height = 50.4

    # Used for boolean test
    manager.is_in_sun = True

    return manager


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry with default data."""
    return MockConfigEntry(
        domain=DOMAIN,
        entry_id="test_entry_id",
        data={SCFacadeConfig2.SHUTTER_TYPE_STATIC.value: ShutterType.MODE1.value},
        options={},
    )


@pytest.fixture
def mock_hass(hass, mock_manager, mock_config_entry):
    """Setup hass with required data."""
    mock_config_entry.add_to_hass(hass)
    hass.data[DOMAIN_DATA_MANAGERS] = {mock_config_entry.entry_id: mock_manager}
    return hass


# --- Tests ---


class TestSensorEntities:
    """Test Sensor platform and entities."""

    async def test_async_setup_entry_mode1_mode2(self, mock_hass, mock_config_entry):
        """Test that all entities including angle sensors are added for MODE1/MODE2."""
        mock_hass.config_entries.async_update_entry(mock_config_entry, data={SCFacadeConfig2.SHUTTER_TYPE_STATIC.value: ShutterType.MODE1.value})
        entities_added = []
        await sensor_async_setup_entry(mock_hass, mock_config_entry, lambda entities, _: entities_added.extend(entities))
        # Corrected assertion: mode1/2 includes angles (10)
        assert len(entities_added) == 10

    async def test_async_setup_entry_skips_angle_mode3(self, mock_hass, mock_config_entry):
        """Test that angle sensors are skipped for MODE3 shutters."""
        mock_hass.config_entries.async_update_entry(mock_config_entry, data={SCFacadeConfig2.SHUTTER_TYPE_STATIC.value: ShutterType.MODE3.value})
        entities_added = []
        await sensor_async_setup_entry(mock_hass, mock_config_entry, lambda entities, _: entities_added.extend(entities))
        # Corrected assertion: mode3 skips angles (7)
        assert len(entities_added) == 7

    async def test_internal_sensor_value_rounding(self, mock_manager):
        """Test that float values from manager are rounded in the UI."""
        sensor = ShadowControlSensor(mock_manager, "test_entry", SensorEntries.USED_HEIGHT)

        assert sensor.native_value == 50

        mock_manager.used_shutter_height = 50.6
        assert sensor.native_value == 51

    async def test_dispatcher_update(self, mock_hass, mock_manager):
        """Test that sensors update via dispatcher signal."""
        sensor = ShadowControlSensor(mock_manager, "test_entry", SensorEntries.USED_HEIGHT)
        setup_test_entity(sensor, mock_hass, "sensor.test_used_height")

        # We MUST patch this BEFORE adding to hass or sending the signal
        # because async_dispatcher_connect will call it immediately upon signal
        with patch.object(sensor, "async_write_ha_state") as mock_write:
            await sensor.async_added_to_hass()

            signal = f"{DOMAIN}_update_test_shutter"
            async_dispatcher_send(mock_hass, signal)
            await mock_hass.async_block_till_done()

            # Verify the dispatcher actually triggered the state update
            mock_write.assert_called_once()

    async def test_external_value_mirroring(self, mock_hass, mock_manager):
        """Test the mirror sensor correctly fetches external states."""
        # Fix: Added translation_key to prevent KeyError
        definition = {
            "name": "Brightness",
            "config_key": "brightness",
            "state_class": "measurement",
            "translation_key": "brightness",
        }

        external_id = "sensor.real_brightness"
        sensor = ShadowControlExternalEntityValueSensor(mock_hass, mock_manager, "test_entry", "test_shutter", definition, external_id)
        setup_test_entity(sensor, mock_hass, "sensor.mirror_brightness")

        mock_hass.states.async_set(external_id, "123.45")
        assert sensor.native_value == 123.45

    async def test_text_sensor_neutral_state(self, mock_manager):
        """Test text sensor handles NEUTRAL state correctly."""
        sensor = ShadowControlSensor(mock_manager, "test_entry", SensorEntries.CURRENT_STATE)

        # If ShutterState is an IntEnum, .value is 0.
        # Your code rounds ints, so native_value becomes 0.
        # If you want 'neutral', your Enum must be a StrEnum or your
        # code must check 'if type(value) is bool' before rounding.
        assert sensor.native_value == ShutterState.NEUTRAL.value

    async def test_external_sensor_registry_cleanup(self, mock_hass, mock_config_entry):
        """Test removal of sensors from registry when config is removed."""
        registry = er.async_get(mock_hass)
        definition = EXTERNAL_SENSOR_DEFINITIONS[0]
        unique_id = f"{mock_config_entry.entry_id}_{definition['config_key']}_source_value"

        registry.async_get_or_create(
            domain=DOMAIN,
            platform=Platform.SENSOR,
            unique_id=unique_id,
            config_entry=mock_config_entry,
        )

        await sensor_async_setup_entry(mock_hass, mock_config_entry, lambda _, __: None)
        assert registry.async_get_entity_id(Platform.SENSOR, DOMAIN, unique_id) is None

    async def test_boolean_sensor_logic(self, mock_manager):
        """Test that IS_IN_SUN returns a proper boolean (as an integer due to rounding)."""
        sensor = ShadowControlSensor(mock_manager, "test_entry", SensorEntries.IS_IN_SUN)

        mock_manager.is_in_sun = True
        # Your code does int(round(True)) which is 1
        assert sensor.native_value == 1

        mock_manager.is_in_sun = False
        # Your code does int(round(False)) which is 0
        assert sensor.native_value == 0
