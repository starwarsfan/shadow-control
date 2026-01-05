"""Test the SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING state handler."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.shadow_control import ShadowControlManager
from custom_components.shadow_control.const import ShutterState


@pytest.fixture
def manager(mock_manager):
    """Bind the real handler to the mock manager."""
    manager = mock_manager
    manager._handle_state_shadow_horizontal_neutral_timer_running = (
        ShadowControlManager._handle_state_shadow_horizontal_neutral_timer_running.__get__(manager)
    )

    # Dependencies specific to this handler
    manager._check_if_facade_is_in_sun = AsyncMock(return_value=True)
    manager._is_shadow_control_enabled = AsyncMock(return_value=True)
    manager._get_current_brightness = MagicMock(return_value=10000)
    manager._is_timer_finished = MagicMock(return_value=False)
    manager._calculate_shutter_height = MagicMock(return_value=50.0)
    manager._position_shutter = AsyncMock()
    manager._cancel_timer = MagicMock()

    # Config mocks
    manager._shadow_config = MagicMock()
    manager._shadow_config.brightness_threshold = 50000
    manager._shadow_config.shutter_look_through_angle = 90.0
    manager._facade_config = MagicMock()

    return manager


@pytest.mark.asyncio
class TestHandleStateShadowHorizontalNeutralTimerRunning:
    """Test branches of the SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING handler."""

    async def test_brightness_spikes_returns_to_closed(self, manager):
        """Test that a brightness spike cancels the timer and goes back to full closed."""
        manager._get_current_brightness.return_value = 60000
        manager._shadow_config.brightness_threshold = 50000

        result = await manager._handle_state_shadow_horizontal_neutral_timer_running()

        assert result == ShutterState.SHADOW_FULL_CLOSED
        manager._cancel_timer.assert_called_once()
        manager._position_shutter.assert_not_called()

    async def test_timer_finishes_opens_slats(self, manager):
        """Test moving to horizontal slats when the timer expires."""
        manager._get_current_brightness.return_value = 10000
        manager._shadow_config.brightness_threshold = 50000
        manager._shadow_config.shutter_look_through_angle = 90.0
        manager._is_timer_finished.return_value = True

        result = await manager._handle_state_shadow_horizontal_neutral_timer_running()

        assert result == ShutterState.SHADOW_HORIZONTAL_NEUTRAL
        manager._position_shutter.assert_called_once_with(50.0, 90.0, stop_timer=True)

    async def test_still_waiting_for_timer(self, manager):
        """Test staying in state while brightness is low but timer isn't done."""
        manager._get_current_brightness.return_value = 10000
        manager._is_timer_finished.return_value = False

        result = await manager._handle_state_shadow_horizontal_neutral_timer_running()

        assert result == ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING
        manager._position_shutter.assert_not_called()

    async def test_sun_gone_returns_to_neutral(self, manager):
        """Test transition to NEUTRAL when sun leaves the facade."""
        manager._check_if_facade_is_in_sun.return_value = False
        manager._facade_config.neutral_pos_height = 100.0
        manager._facade_config.neutral_pos_angle = 0.0

        result = await manager._handle_state_shadow_horizontal_neutral_timer_running()

        assert result == ShutterState.NEUTRAL
        manager._position_shutter.assert_called_once_with(100.0, 0.0, stop_timer=True)

    async def test_calculation_error_stays_in_state(self, manager):
        """Test handling case where height calculation returns None."""
        manager._is_timer_finished.return_value = True
        manager._calculate_shutter_height.return_value = None

        result = await manager._handle_state_shadow_horizontal_neutral_timer_running()

        assert result == ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING
