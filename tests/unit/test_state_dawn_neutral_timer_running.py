"""Test the DAWN_NEUTRAL_TIMER_RUNNING state handler."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.shadow_control import ShadowControlManager
from custom_components.shadow_control.const import ShutterState


@pytest.fixture
def manager(mock_manager):
    """Bind the real handler to the mock manager."""
    manager = mock_manager
    manager._handle_state_dawn_neutral_timer_running = ShadowControlManager._handle_state_dawn_neutral_timer_running.__get__(manager)

    # Dependencies
    manager._is_dawn_control_enabled = AsyncMock(return_value=True)
    manager._get_current_dawn_brightness = MagicMock(return_value=50)
    manager._is_timer_finished = MagicMock(return_value=False)
    manager._position_shutter = AsyncMock()
    manager._cancel_timer = MagicMock()

    # Config mocks
    manager._dawn_config = MagicMock()
    manager._facade_config = MagicMock()

    # Defaults
    manager._dawn_config.brightness_threshold = 10

    return manager


@pytest.mark.asyncio
class TestHandleStateDawnNeutralTimerRunning:
    """Test branches of the DAWN_NEUTRAL_TIMER_RUNNING handler."""

    async def test_brightness_drops_returns_to_closed(self, manager):
        """Test that dropping brightness cancels timer and re-closes."""
        manager._get_current_dawn_brightness.return_value = 5  # Below 10

        result = await manager._handle_state_dawn_neutral_timer_running()

        assert result == ShutterState.DAWN_FULL_CLOSED
        manager._cancel_timer.assert_called_once()
        manager._position_shutter.assert_not_called()

    async def test_timer_finishes_moves_to_dawn_neutral(self, manager):
        """Test moving to open slats position when timer expires."""
        manager._get_current_dawn_brightness.return_value = 50  # Above 10
        manager._is_timer_finished.return_value = True
        manager._dawn_config.shutter_max_height = 100.0
        manager._dawn_config.shutter_look_through_angle = 90.0

        result = await manager._handle_state_dawn_neutral_timer_running()

        assert result == ShutterState.DAWN_NEUTRAL
        manager._position_shutter.assert_called_once_with(100.0, 90.0, stop_timer=True)

    async def test_waiting_for_timer(self, manager):
        """Test staying in state while timer is still running."""
        manager._is_timer_finished.return_value = False

        result = await manager._handle_state_dawn_neutral_timer_running()

        assert result == ShutterState.DAWN_NEUTRAL_TIMER_RUNNING
        manager._position_shutter.assert_not_called()

    async def test_dawn_disabled_retreats_to_neutral(self, manager):
        """Test falling back to global NEUTRAL if dawn mode is turned off."""
        manager._is_dawn_control_enabled.return_value = False
        manager._facade_config.neutral_pos_height = 0.0
        manager._facade_config.neutral_pos_angle = 0.0

        result = await manager._handle_state_dawn_neutral_timer_running()

        assert result == ShutterState.NEUTRAL
        manager._position_shutter.assert_called_once_with(0.0, 0.0, stop_timer=True)

    async def test_missing_config_stays_in_state(self, manager):
        """Test handling of missing dawn height/angle configuration."""
        manager._is_timer_finished.return_value = True
        manager._dawn_config.shutter_max_height = None

        result = await manager._handle_state_dawn_neutral_timer_running()

        assert result == ShutterState.DAWN_NEUTRAL_TIMER_RUNNING
        assert manager.logger.warning.called
