"""Test the NEUTRAL state handler."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.shadow_control import ShadowControlManager
from custom_components.shadow_control.const import ShutterState


@pytest.fixture
def manager(mock_manager):
    """Bind the real handler to the mock manager."""
    manager = mock_manager
    manager._handle_state_neutral = ShadowControlManager._handle_state_neutral.__get__(manager)

    # Dependencies
    manager._check_if_facade_is_in_sun = AsyncMock(return_value=False)
    manager._is_shadow_control_enabled = AsyncMock(return_value=True)
    manager._is_dawn_control_enabled = AsyncMock(return_value=False)
    manager._get_current_brightness = MagicMock(return_value=10000)
    manager._get_current_dawn_brightness = MagicMock(return_value=500)
    manager._start_timer = AsyncMock()
    manager._position_shutter = AsyncMock()

    # Config mocks
    manager._shadow_config = MagicMock()
    manager._dawn_config = MagicMock()
    manager._facade_config = MagicMock()

    return manager


@pytest.mark.asyncio
class TestHandleStateNeutral:
    """Test branches of the NEUTRAL handler."""

    async def test_trigger_shadow_flow(self, manager):
        """Test transitioning to shadow timer when sun hits facade and brightness is high."""
        manager._check_if_facade_is_in_sun.return_value = True
        manager._get_current_brightness.return_value = 60000
        manager.brightness_threshold = 50000
        manager._shadow_config.after_seconds = 60

        result = await manager._handle_state_neutral()

        assert result == ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING
        manager._start_timer.assert_called_once_with(60)

    async def test_trigger_dawn_flow(self, manager):
        """Test transitioning to dawn timer when dawn mode is active and it gets dark."""
        # Ensure shadow conditions aren't met
        manager._check_if_facade_is_in_sun.return_value = False

        manager._is_dawn_control_enabled.return_value = True
        manager._get_current_dawn_brightness.return_value = 5
        manager._dawn_config.brightness_threshold = 10
        manager._dawn_config.after_seconds = 300

        result = await manager._handle_state_neutral()

        assert result == ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING
        manager._start_timer.assert_called_once_with(300)

    async def test_stay_neutral_and_reposition(self, manager):
        """Test staying in NEUTRAL and ensuring shutter is at neutral position."""
        manager._check_if_facade_is_in_sun.return_value = False
        manager._is_dawn_control_enabled.return_value = False
        manager._facade_config.neutral_pos_height = 100.0
        manager._facade_config.neutral_pos_angle = 0.0

        result = await manager._handle_state_neutral()

        assert result == ShutterState.NEUTRAL
        manager._position_shutter.assert_called_once_with(100.0, 0.0, stop_timer=True)

    async def test_shadow_brightness_low_stays_neutral(self, manager):
        """Test that low brightness prevents shadow trigger even if in sun."""
        manager._check_if_facade_is_in_sun.return_value = True
        manager._get_current_brightness.return_value = 10000
        manager.brightness_threshold = 50000

        result = await manager._handle_state_neutral()

        assert result == ShutterState.NEUTRAL
