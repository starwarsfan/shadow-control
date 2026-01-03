"""Test the SHADOW_NEUTRAL state handler."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.shadow_control import ShadowControlManager
from custom_components.shadow_control.const import ShutterState


@pytest.fixture
def manager(mock_manager):
    """Bind the real handler to the mock manager."""
    manager = mock_manager
    manager._handle_state_shadow_neutral = ShadowControlManager._handle_state_shadow_neutral.__get__(manager)

    # Dependencies
    manager._check_if_facade_is_in_sun = AsyncMock(return_value=True)
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

    # Defaults to prevent NoneType issues in logical checks
    manager._shadow_config.brightness_threshold = 50000
    manager._shadow_config.after_seconds = 60
    manager._dawn_config.enabled = False

    return manager


@pytest.mark.asyncio
class TestHandleStateShadowNeutral:
    """Test branches of the SHADOW_NEUTRAL handler."""

    async def test_brightness_spike_triggers_shadow_timer(self, manager):
        """Test transitioning back to shadow timer when sun returns."""
        manager._get_current_brightness.return_value = 60000
        manager._shadow_config.brightness_threshold = 50000
        manager._shadow_config.after_seconds = 120

        result = await manager._handle_state_shadow_neutral()

        assert result == ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING
        manager._start_timer.assert_called_once_with(120)

    async def test_brightness_low_triggers_dawn_timer(self, manager):
        """Test transitioning to dawn timer when it gets dark."""
        manager._dawn_config.enabled = True
        manager._get_current_dawn_brightness.return_value = 5
        manager._dawn_config.brightness_threshold = 10
        manager._dawn_config.after_seconds = 300

        result = await manager._handle_state_shadow_neutral()

        assert result == ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING
        manager._start_timer.assert_called_once_with(300)

    async def test_maintains_after_shadow_position(self, manager):
        """Test staying in SHADOW_NEUTRAL and positioning shutter if configured."""
        manager._get_current_brightness.return_value = 10000
        manager._shadow_config.height_after_sun = 30.0
        manager._shadow_config.angle_after_sun = 0.0

        result = await manager._handle_state_shadow_neutral()

        assert result == ShutterState.SHADOW_NEUTRAL
        manager._position_shutter.assert_called_once_with(30.0, 0.0, stop_timer=True)

    async def test_sun_gone_retreats_to_neutral(self, manager):
        """Test moving to full NEUTRAL state when sun is no longer on facade."""
        manager._check_if_facade_is_in_sun.return_value = False
        manager._facade_config.neutral_pos_height = 100.0
        manager._facade_config.neutral_pos_angle = 0.0

        result = await manager._handle_state_shadow_neutral()

        assert result == ShutterState.NEUTRAL
        manager._position_shutter.assert_called_once_with(100.0, 0.0, stop_timer=True)

    async def test_dawn_mode_only_transition(self, manager):
        """Test transition to dawn when shadow mode is disabled but dawn is active."""
        manager._check_if_facade_is_in_sun.return_value = False
        manager._is_dawn_control_enabled.return_value = True
        manager._get_current_dawn_brightness.return_value = 5
        manager._dawn_config.brightness_threshold = 10
        manager._dawn_config.after_seconds = 300

        result = await manager._handle_state_shadow_neutral()

        assert result == ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING
        manager._start_timer.assert_called_once_with(300)
