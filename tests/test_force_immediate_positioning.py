"""Test the immediate positioning bypass logic."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.shadow_control import ShadowControlManager
from custom_components.shadow_control.const import ShutterState


@pytest.fixture
def manager(mock_manager):
    """Bind the real method and setup common mocks."""
    manager = mock_manager
    manager._force_immediate_positioning = ShadowControlManager._force_immediate_positioning.__get__(manager)

    # Mocking positioner and timer
    manager._position_shutter = AsyncMock()
    manager._cancel_timer = MagicMock()

    # Mocking calculation helpers used in Shadow states
    manager._calculate_shutter_height = MagicMock(return_value=55.0)
    manager._calculate_shutter_angle = MagicMock(return_value=12.0)

    # Default Config Values
    manager._dawn_config.shutter_max_height = 100.0
    manager._dawn_config.shutter_max_angle = 0.0
    manager._dawn_config.shutter_look_through_angle = 90.0
    manager._dawn_config.height_after_dawn = 10.0
    manager._dawn_config.angle_after_dawn = 45.0

    manager._shadow_config.shutter_look_through_angle = 80.0
    manager._shadow_config.height_after_sun = 0.0
    manager._shadow_config.angle_after_sun = 0.0

    manager._facade_config.neutral_pos_height = 0.0
    manager._facade_config.neutral_pos_angle = 0.0

    return manager


@pytest.mark.asyncio
class TestForceImmediatePositioning:
    """Test suite for forced positioning logic."""

    async def test_initial_run_reset(self, manager):
        """Verify that _is_initial_run is flipped to False."""
        manager._is_initial_run = True
        manager.current_shutter_state = ShutterState.NEUTRAL

        await manager._force_immediate_positioning()

        assert manager._is_initial_run is False
        manager._cancel_timer.assert_called_once()

    async def test_force_dawn_full_closed(self, manager):
        """Test forcing position while in Dawn Full Closed state."""
        manager.current_shutter_state = ShutterState.DAWN_FULL_CLOSED

        await manager._force_immediate_positioning()

        manager._position_shutter.assert_called_with(100.0, 0.0, stop_timer=True)

    async def test_force_dawn_horizontal(self, manager):
        """Test forcing position while in Dawn Horizontal state."""
        manager.current_shutter_state = ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING

        await manager._force_immediate_positioning()

        manager._position_shutter.assert_called_with(100.0, 90.0, stop_timer=True)

    async def test_force_shadow_full_closed(self, manager):
        """Test forcing position while in Shadow Full Closed state (uses calc helpers)."""
        manager.current_shutter_state = ShutterState.SHADOW_FULL_CLOSED

        await manager._force_immediate_positioning()

        # Should use return values from _calculate_shutter_height/angle
        manager._position_shutter.assert_called_with(55.0, 12.0, stop_timer=True)

    async def test_force_shadow_neutral(self, manager):
        """Test forcing position while in Shadow Neutral state."""
        manager.current_shutter_state = ShutterState.SHADOW_NEUTRAL
        manager._shadow_config.height_after_sun = 15.0
        manager._shadow_config.angle_after_sun = 5.0

        await manager._force_immediate_positioning()

        manager._position_shutter.assert_called_with(15.0, 5.0, stop_timer=True)

    async def test_missing_config_warning(self, manager):
        """Test the warning branch when height is None."""
        manager.current_shutter_state = ShutterState.NEUTRAL
        manager._facade_config.neutral_pos_height = None

        await manager._force_immediate_positioning()

        manager.logger.warning.assert_called()
        manager._position_shutter.assert_not_called()
