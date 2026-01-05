"""Test the SHADOW_FULL_CLOSE_TIMER_RUNNING state handler."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.shadow_control import ShadowControlManager
from custom_components.shadow_control.const import ShutterState


@pytest.fixture
def manager(mock_manager):
    """Bind the real handler to the mock manager."""
    manager = mock_manager
    manager._handle_state_shadow_full_close_timer_running = ShadowControlManager._handle_state_shadow_full_close_timer_running.__get__(manager)

    # Setup standard mocks for this handler's dependencies
    manager._check_if_facade_is_in_sun = AsyncMock(return_value=True)
    manager._is_shadow_control_enabled = AsyncMock(return_value=True)
    manager._is_timer_finished = MagicMock(return_value=False)
    manager._calculate_shutter_height = MagicMock(return_value=50.0)
    manager._calculate_shutter_angle = MagicMock(return_value=0.0)
    manager._position_shutter = AsyncMock()
    manager._cancel_timer = MagicMock()

    # Config mocks
    manager._dynamic_config = MagicMock()
    manager._shadow_config = MagicMock()
    manager._facade_config = MagicMock()

    return manager


@pytest.mark.asyncio
class TestHandleStateShadowFullCloseTimerRunning:
    """Test branches of the SHADOW_FULL_CLOSE_TIMER_RUNNING handler."""

    async def test_waiting_for_timer(self, manager):
        """Test staying in state while timer is still running."""
        manager._dynamic_config.brightness = 60000
        manager._shadow_config.brightness_threshold = 50000
        manager._is_timer_finished.return_value = False

        result = await manager._handle_state_shadow_full_close_timer_running()

        assert result == ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING
        manager._position_shutter.assert_not_called()

    async def test_transition_to_full_closed(self, manager):
        """Test moving to full closed when timer finishes and brightness is high."""
        manager._dynamic_config.brightness = 60000
        manager._shadow_config.brightness_threshold = 50000
        manager._is_timer_finished.return_value = True

        result = await manager._handle_state_shadow_full_close_timer_running()

        assert result == ShutterState.SHADOW_FULL_CLOSED
        manager._position_shutter.assert_called_once_with(50.0, 0.0, stop_timer=True)

    async def test_brightness_drops_below_threshold(self, manager):
        """Test transitioning back to SHADOW_NEUTRAL if it gets dark."""
        manager._dynamic_config.brightness = 10000
        manager._shadow_config.brightness_threshold = 50000

        result = await manager._handle_state_shadow_full_close_timer_running()

        assert result == ShutterState.SHADOW_NEUTRAL
        manager._cancel_timer.assert_called_once()

    async def test_not_in_sun_transition_to_neutral(self, manager):
        """Test moving to NEUTRAL if facade is no longer in sun."""
        manager._check_if_facade_is_in_sun.return_value = False
        manager._facade_config.neutral_pos_height = 100
        manager._facade_config.neutral_pos_angle = 0

        result = await manager._handle_state_shadow_full_close_timer_running()

        assert result == ShutterState.NEUTRAL
        manager._position_shutter.assert_called_once_with(100.0, 0.0, stop_timer=True)

    async def test_calculation_error_stays_in_state(self, manager):
        """Test handling case where height/angle calculation returns None."""
        manager._dynamic_config.brightness = 60000
        manager._shadow_config.brightness_threshold = 50000
        manager._is_timer_finished.return_value = True
        manager._calculate_shutter_height.return_value = None

        result = await manager._handle_state_shadow_full_close_timer_running()

        assert result == ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING
