"""Test shadow_control binary sensor entities."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.shadow_control import DOMAIN_DATA_MANAGERS
from custom_components.shadow_control.binary_sensor import (
    ShadowControlAutoLockBinarySensor,
)
from custom_components.shadow_control.binary_sensor import async_setup_entry as binary_sensor_async_setup_entry
from custom_components.shadow_control.const import DOMAIN, SCInternal


@pytest.fixture
def mock_manager():
    """Mock manager for binary sensor tests."""
    manager = MagicMock()
    manager.logger = MagicMock()
    manager.sanitized_name = "test_shutter"
    manager.name = "Test Shutter"
    manager.auto_lock_active = False
    manager.restore_auto_lock = MagicMock()
    return manager


@pytest.fixture
def mock_config_entry():
    """Mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        entry_id="test_entry_id",
        data={},
        options={},
    )


@pytest.fixture
def mock_hass(hass, mock_manager, mock_config_entry):
    """Setup hass with required data."""
    mock_config_entry.add_to_hass(hass)
    hass.data[DOMAIN_DATA_MANAGERS] = {mock_config_entry.entry_id: mock_manager}
    return hass


class TestBinarySensorEntities:
    """Test BinarySensor platform logic."""

    async def test_async_setup_entry_adds_one_entity(self, mock_hass, mock_config_entry):
        """Test that exactly one binary sensor is added."""
        entities_added = []
        await binary_sensor_async_setup_entry(mock_hass, mock_config_entry, entities_added.extend)
        assert len(entities_added) == 1
        assert isinstance(entities_added[0], ShadowControlAutoLockBinarySensor)

    async def test_initial_state_is_false(self, mock_hass, mock_config_entry, mock_manager):
        """Test that the sensor initialises to False."""
        sensor = ShadowControlAutoLockBinarySensor(
            mock_hass, mock_config_entry, instance_name="Test", logger=mock_manager.logger
        )
        assert sensor.is_on is False

    async def test_unique_id(self, mock_hass, mock_config_entry, mock_manager):
        """Test that unique_id is built from entry_id and enum value."""
        sensor = ShadowControlAutoLockBinarySensor(
            mock_hass, mock_config_entry, instance_name="Test", logger=mock_manager.logger
        )
        assert sensor._attr_unique_id == f"test_entry_id_{SCInternal.AUTO_LOCK_ACTIVE.value}"

    async def test_async_added_to_hass_no_prior_state(self, mock_hass, mock_config_entry, mock_manager):
        """When there is no prior HA state the sensor stays False and restores the manager."""
        sensor = ShadowControlAutoLockBinarySensor(
            mock_hass, mock_config_entry, instance_name="Test", logger=mock_manager.logger
        )
        with patch.object(sensor, "async_get_last_state", AsyncMock(return_value=None)), \
             patch.object(sensor, "async_write_ha_state"):
            await sensor.async_added_to_hass()

        assert sensor.is_on is False
        mock_manager.restore_auto_lock.assert_called_once_with(False)

    async def test_async_added_to_hass_restores_true(self, mock_hass, mock_config_entry, mock_manager):
        """When last HA state was 'on' the sensor restores True into the manager."""
        sensor = ShadowControlAutoLockBinarySensor(
            mock_hass, mock_config_entry, instance_name="Test", logger=mock_manager.logger
        )
        last_state = MagicMock()
        last_state.state = "on"
        with patch.object(sensor, "async_get_last_state", AsyncMock(return_value=last_state)), \
             patch.object(sensor, "async_write_ha_state"):
            await sensor.async_added_to_hass()

        assert sensor.is_on is True
        mock_manager.restore_auto_lock.assert_called_once_with(True)

    async def test_async_added_to_hass_restores_false(self, mock_hass, mock_config_entry, mock_manager):
        """When last HA state was 'off' the sensor restores False into the manager."""
        sensor = ShadowControlAutoLockBinarySensor(
            mock_hass, mock_config_entry, instance_name="Test", logger=mock_manager.logger
        )
        last_state = MagicMock()
        last_state.state = "off"
        with patch.object(sensor, "async_get_last_state", AsyncMock(return_value=last_state)), \
             patch.object(sensor, "async_write_ha_state"):
            await sensor.async_added_to_hass()

        assert sensor.is_on is False
        mock_manager.restore_auto_lock.assert_called_once_with(False)

    async def test_handle_manager_update_changes_state(self, mock_hass, mock_config_entry, mock_manager):
        """When manager.auto_lock_active flips, the sensor state updates and writes HA state."""
        sensor = ShadowControlAutoLockBinarySensor(
            mock_hass, mock_config_entry, instance_name="Test", logger=mock_manager.logger
        )
        sensor._state = False
        mock_manager.auto_lock_active = True

        with patch.object(sensor, "async_write_ha_state") as mock_write:
            sensor._handle_manager_update()

        assert sensor.is_on is True
        mock_write.assert_called_once()

    async def test_handle_manager_update_no_change(self, mock_hass, mock_config_entry, mock_manager):
        """When manager.auto_lock_active is unchanged, async_write_ha_state is not called."""
        sensor = ShadowControlAutoLockBinarySensor(
            mock_hass, mock_config_entry, instance_name="Test", logger=mock_manager.logger
        )
        sensor._state = False
        mock_manager.auto_lock_active = False

        with patch.object(sensor, "async_write_ha_state") as mock_write:
            sensor._handle_manager_update()

        assert sensor.is_on is False
        mock_write.assert_not_called()
