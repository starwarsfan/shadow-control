"""Test the DAWN_FULL_CLOSE_TIMER_RUNNING state handler."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.shadow_control import ShadowControlManager
from custom_components.shadow_control.const import ShutterState


@pytest.fixture
def manager(mock_manager):
    """Bind the real handler to the mock manager."""
    manager = mock_manager
    manager._handle_state_dawn_full_close_timer_running = ShadowControlManager._handle_state_dawn_full_close_timer_running.__get__(manager)

    # Dependencies
    manager._is_dawn_control_enabled = AsyncMock(return_value=True)
    manager._get_current_dawn_brightness = MagicMock(return_value=5)
    manager._is_timer_finished = MagicMock(return_value=False)
    manager._position_shutter = AsyncMock()
    manager._cancel_timer = MagicMock()

    # Config mocks
    manager._dawn_config = MagicMock()
    manager._facade_config = MagicMock()

    # Defaults
    manager._dawn_config.brightness_threshold = 10
    manager._dawn_config.shutter_max_height = 100.0
    manager._dawn_config.shutter_max_angle = 0.0

    return manager


@pytest.mark.asyncio
class TestHandleStateDawnFullCloseTimerRunning:
    """Test branches of the DAWN_FULL_CLOSE_TIMER_RUNNING handler."""

    async def test_brightness_recovers_stops_timer(self, manager):
        """Test that if it gets bright again, the timer stops and we go back to DAWN_NEUTRAL."""
        manager._get_current_dawn_brightness.return_value = 50  # Brightness recovered

        result = await manager._handle_state_dawn_full_close_timer_running()

        assert result == ShutterState.DAWN_NEUTRAL
        manager._cancel_timer.assert_called_once()
        manager._position_shutter.assert_not_called()

    async def test_timer_finishes_closes_shutter(self, manager):
        """Test moving to FULL_CLOSED when timer expires and it's still dark."""
        manager._get_current_dawn_brightness.return_value = 5
        manager._is_timer_finished.return_value = True

        result = await manager._handle_state_dawn_full_close_timer_running()

        assert result == ShutterState.DAWN_FULL_CLOSED
        manager._position_shutter.assert_called_once_with(100.0, 0.0, stop_timer=True)

    async def test_waiting_for_timer(self, manager):
        """Test staying in state while brightness is low but timer hasn't finished."""
        manager._is_timer_finished.return_value = False

        result = await manager._handle_state_dawn_full_close_timer_running()

        assert result == ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING
        manager._position_shutter.assert_not_called()

    async def test_dawn_disabled_fallback(self, manager):
        """Test retreating to NEUTRAL if dawn control is disabled mid-timer."""
        manager._is_dawn_control_enabled.return_value = False
        manager._facade_config.neutral_pos_height = 0.0
        manager._facade_config.neutral_pos_angle = 0.0

        result = await manager._handle_state_dawn_full_close_timer_running()

        assert result == ShutterState.NEUTRAL
        manager._position_shutter.assert_called_once_with(0.0, 0.0, stop_timer=True)

    async def test_missing_config_warning(self, manager):
        """Test warning and staying in state if height config is missing when timer finishes."""
        manager._is_timer_finished.return_value = True
        manager._dawn_config.shutter_max_height = None

        result = await manager._handle_state_dawn_full_close_timer_running()

        assert result == ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING
        assert manager.logger.warning.called
