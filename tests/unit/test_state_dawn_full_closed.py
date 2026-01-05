"""Test the DAWN_FULL_CLOSED state handler."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.shadow_control import ShadowControlManager
from custom_components.shadow_control.const import ShutterState


@pytest.fixture
def manager(mock_manager):
    """Bind the real handler to the mock manager."""
    manager = mock_manager
    manager._handle_state_dawn_full_closed = ShadowControlManager._handle_state_dawn_full_closed.__get__(manager)

    # Dependencies
    manager._is_dawn_control_enabled = AsyncMock(return_value=True)
    manager._get_current_dawn_brightness = MagicMock(return_value=5)
    manager._start_timer = AsyncMock()
    manager._position_shutter = AsyncMock()

    # Config mocks
    manager._dawn_config = MagicMock()
    manager._facade_config = MagicMock()

    # Default threshold (Dark)
    manager._dawn_config.brightness_threshold = 10
    manager._dawn_config.shutter_max_height = 100.0
    manager._dawn_config.shutter_max_angle = 0.0
    manager._dawn_config.shutter_look_through_seconds = 300

    return manager


@pytest.mark.asyncio
class TestHandleStateDawnFullClosed:
    """Test branches of the DAWN_FULL_CLOSED handler."""

    async def test_sunrise_starts_look_through_timer(self, manager):
        """Test transitioning to look-through timer when brightness rises."""
        manager._get_current_dawn_brightness.return_value = 15  # Above 10

        result = await manager._handle_state_dawn_full_closed()

        assert result == ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING
        manager._start_timer.assert_called_once_with(300)

    async def test_remains_closed_during_night(self, manager):
        """Test staying in state and positioning shutter while it is dark."""
        manager._get_current_dawn_brightness.return_value = 5  # Below 10

        result = await manager._handle_state_dawn_full_closed()

        assert result == ShutterState.DAWN_FULL_CLOSED
        manager._position_shutter.assert_called_once_with(100.0, 0.0, stop_timer=True)

    async def test_dawn_disabled_retreats_to_neutral(self, manager):
        """Test falling back to global NEUTRAL if dawn mode is turned off."""
        manager._is_dawn_control_enabled.return_value = False
        manager._facade_config.neutral_pos_height = 0.0
        manager._facade_config.neutral_pos_angle = 0.0

        result = await manager._handle_state_dawn_full_closed()

        assert result == ShutterState.NEUTRAL
        manager._position_shutter.assert_called_once_with(0.0, 0.0, stop_timer=True)

    async def test_missing_config_warning(self, manager):
        """Test warning and staying in state if dawn height config is missing."""
        manager._get_current_dawn_brightness.return_value = 5
        manager._dawn_config.shutter_max_height = None

        result = await manager._handle_state_dawn_full_closed()

        assert result == ShutterState.DAWN_FULL_CLOSED
        assert manager.logger.warning.called
