"""Test the SHADOW_NEUTRAL_TIMER_RUNNING state handler."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.shadow_control import ShadowControlManager
from custom_components.shadow_control.const import ShutterState


@pytest.fixture
def manager(mock_manager):
    """Bind the real handler to the mock manager."""
    manager = mock_manager
    manager._handle_state_shadow_neutral_timer_running = ShadowControlManager._handle_state_shadow_neutral_timer_running.__get__(manager)

    # Dependencies specific to this handler
    manager._check_if_facade_is_in_sun = AsyncMock(return_value=True)
    manager._is_shadow_control_enabled = AsyncMock(return_value=True)
    manager._get_current_brightness = MagicMock(return_value=10000)
    manager._is_timer_finished = MagicMock(return_value=False)
    manager._position_shutter = AsyncMock()
    manager._cancel_timer = MagicMock()

    # Config mocks
    manager._shadow_config = MagicMock()
    manager.brightness_threshold = 50000
    manager._shadow_config.height_after_sun = 20.0
    manager._shadow_config.angle_after_sun = 10.0
    manager._facade_config = MagicMock()

    return manager


@pytest.mark.asyncio
class TestHandleStateShadowNeutralTimerRunning:
    """Test branches of the SHADOW_NEUTRAL_TIMER_RUNNING handler."""

    async def test_brightness_recovery_cancels_timer(self, manager):
        """Test that brightness spike returns to FULL_CLOSED immediately."""
        manager._get_current_brightness.return_value = 60000
        manager.brightness_threshold = 50000

        result = await manager._handle_state_shadow_neutral_timer_running()

        assert result == ShutterState.SHADOW_FULL_CLOSED
        manager._cancel_timer.assert_called_once()
        manager._position_shutter.assert_not_called()

    async def test_timer_finishes_moves_to_after_sun_pos(self, manager):
        """Test moving to the 'after sun' position when timer expires."""
        manager._is_timer_finished.return_value = True
        manager._shadow_config.height_after_sun = 20.0
        manager._shadow_config.angle_after_sun = 10.0

        result = await manager._handle_state_shadow_neutral_timer_running()

        assert result == ShutterState.SHADOW_NEUTRAL
        manager._position_shutter.assert_called_once_with(20.0, 10.0, stop_timer=True)

    async def test_waiting_for_timer(self, manager):
        """Test staying in state while timer is active and brightness is low."""
        manager._is_timer_finished.return_value = False

        result = await manager._handle_state_shadow_neutral_timer_running()

        assert result == ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING
        manager._position_shutter.assert_not_called()

    async def test_unconfigured_after_sun_warning(self, manager):
        """Test behavior when after-sun positions are missing from config."""
        manager._is_timer_finished.return_value = True
        manager._shadow_config.height_after_sun = None

        result = await manager._handle_state_shadow_neutral_timer_running()

        assert result == ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING
        assert manager.logger.warning.called

    async def test_sun_gone_emergency_neutral(self, manager):
        """Test exit to NEUTRAL if sun is no longer on facade."""
        manager._check_if_facade_is_in_sun.return_value = False
        manager._facade_config.neutral_pos_height = 100.0
        manager._facade_config.neutral_pos_angle = 0.0

        result = await manager._handle_state_shadow_neutral_timer_running()

        assert result == ShutterState.NEUTRAL
        manager._position_shutter.assert_called_once_with(100.0, 0.0, stop_timer=True)
