"""Test the SHADOW_FULL_CLOSED state handler."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.shadow_control import ShadowControlManager
from custom_components.shadow_control.const import ShutterState


@pytest.fixture
def manager(mock_manager):
    """Bind the real handler to the mock manager."""
    manager = mock_manager
    manager._handle_state_shadow_full_closed = ShadowControlManager._handle_state_shadow_full_closed.__get__(manager)

    # Dependencies specific to this handler
    manager._check_if_facade_is_in_sun = AsyncMock(return_value=True)
    manager._is_shadow_control_enabled = AsyncMock(return_value=True)
    manager._get_current_brightness = MagicMock(return_value=60000)
    manager._start_timer = AsyncMock()
    manager._calculate_shutter_height = MagicMock(return_value=50.0)
    manager._calculate_shutter_angle = MagicMock(return_value=0.0)
    manager._position_shutter = AsyncMock()

    # Config mocks
    manager._shadow_config = MagicMock()
    manager._facade_config = MagicMock()

    return manager


@pytest.mark.asyncio
class TestHandleStateShadowFullClosed:
    """Test branches of the SHADOW_FULL_CLOSED handler."""

    async def test_brightness_drops_starts_timer(self, manager):
        """Test starting the timer to open slats when brightness drops."""
        manager._get_current_brightness.return_value = 10000
        manager.brightness_threshold = 50000
        manager._shadow_config.shutter_look_through_seconds = 300

        result = await manager._handle_state_shadow_full_closed()

        assert result == ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING
        manager._start_timer.assert_called_once_with(300)

    async def test_brightness_remains_high_recalculates(self, manager):
        """Test recalculating and positioning shutter while staying in state."""
        manager._get_current_brightness.return_value = 60000
        manager.brightness_threshold = 50000
        manager._calculate_shutter_height.return_value = 55.0
        manager._calculate_shutter_angle.return_value = 5.0

        result = await manager._handle_state_shadow_full_closed()

        assert result == ShutterState.SHADOW_FULL_CLOSED
        manager._position_shutter.assert_called_once_with(55.0, 5.0, stop_timer=False)

    async def test_sun_gone_moves_to_neutral(self, manager):
        """Test transition to NEUTRAL when sun leaves the facade."""
        manager._check_if_facade_is_in_sun.return_value = False
        manager._facade_config.neutral_pos_height = 100
        manager._facade_config.neutral_pos_angle = 0

        result = await manager._handle_state_shadow_full_closed()

        assert result == ShutterState.NEUTRAL
        manager._position_shutter.assert_called_once_with(100.0, 0.0, stop_timer=True)

    async def test_recalculate_error_stays_in_state(self, manager):
        """Test that a calculation error doesn't crash the handler."""
        manager._get_current_brightness.return_value = 60000
        manager.brightness_threshold = 50000
        manager._calculate_shutter_height.return_value = None  # Simulating error

        result = await manager._handle_state_shadow_full_closed()

        assert result == ShutterState.SHADOW_FULL_CLOSED
        manager._position_shutter.assert_not_called()

    async def test_neutral_config_missing_warning(self, manager):
        """Test handling missing neutral configuration."""
        manager._check_if_facade_is_in_sun.return_value = False
        manager._facade_config.neutral_pos_height = None

        result = await manager._handle_state_shadow_full_closed()

        assert result == ShutterState.NEUTRAL
        assert manager.logger.warning.called
