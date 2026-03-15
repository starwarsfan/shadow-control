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
    manager._get_current_dawn_brightness = MagicMock(return_value=50)
    manager._start_timer = AsyncMock()
    manager._position_shutter = AsyncMock()
    manager._check_dawn_open_time_constraint = MagicMock(return_value=True)  # Default: opening allowed
    manager._check_dawn_close_time_constraint = MagicMock(return_value=False)  # Default: no close constraint

    # Config mocks
    manager._dawn_config = MagicMock()
    manager._facade_config = MagicMock()

    # Dawn defaults — brightness above threshold → open condition met
    manager._dawn_config.brightness_threshold = 10
    manager._dawn_config.shutter_look_through_seconds = 120
    manager._dawn_config.shutter_max_height = 100.0
    manager._dawn_config.shutter_max_angle = 0.0
    manager._dawn_config.close_not_later_than = None  # No close constraint by default

    # Facade defaults
    manager._facade_config.neutral_pos_height = 0.0
    manager._facade_config.neutral_pos_angle = 0.0

    return manager


@pytest.mark.asyncio
class TestHandleStateDawnFullClosed:
    """Test branches of the DAWN_FULL_CLOSED handler."""

    # =========================================================================
    # Dawn handling active
    # =========================================================================

    async def test_brightness_above_threshold_starts_open_timer(self, manager):
        """Test that sufficient brightness starts the opening timer."""
        manager._get_current_dawn_brightness.return_value = 50  # Above threshold 10

        result = await manager._handle_state_dawn_full_closed()

        assert result == ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING
        manager._start_timer.assert_called_once_with(120)

    async def test_open_not_before_blocks_timer_start(self, manager):
        """Test that open_not_before prevents starting the opening timer."""
        manager._get_current_dawn_brightness.return_value = 50  # Brightness OK
        manager._check_dawn_open_time_constraint.return_value = False  # Too early to open

        result = await manager._handle_state_dawn_full_closed()

        assert result == ShutterState.DAWN_FULL_CLOSED
        manager._start_timer.assert_not_called()
        manager._position_shutter.assert_not_called()

    async def test_close_not_later_than_blocks_re_opening(self, manager):
        """Test that active close_not_later_than prevents re-opening from DAWN_FULL_CLOSED."""
        manager._get_current_dawn_brightness.return_value = 50  # Brightness above threshold
        manager._check_dawn_open_time_constraint.return_value = True  # open_not_before OK
        manager._check_dawn_close_time_constraint.return_value = True  # close time reached → block

        result = await manager._handle_state_dawn_full_closed()

        assert result == ShutterState.DAWN_FULL_CLOSED
        manager._start_timer.assert_not_called()
        manager._position_shutter.assert_called_once_with(100.0, 0.0, stop_timer=True)

    async def test_open_not_before_respected_then_timer_starts(self, manager):
        """Test that timer starts once open_not_before is reached."""
        manager._get_current_dawn_brightness.return_value = 50  # Brightness OK
        manager._check_dawn_open_time_constraint.return_value = True  # Time reached

        result = await manager._handle_state_dawn_full_closed()

        assert result == ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING
        manager._start_timer.assert_called_once_with(120)

    async def test_brightness_below_threshold_positions_to_dawn_closed(self, manager):
        """Test that low brightness keeps shutter in dawn closed position."""
        manager._get_current_dawn_brightness.return_value = 5  # Below threshold 10

        result = await manager._handle_state_dawn_full_closed()

        assert result == ShutterState.DAWN_FULL_CLOSED
        manager._position_shutter.assert_called_once_with(100.0, 0.0, stop_timer=True)
        manager._start_timer.assert_not_called()

    async def test_missing_open_slat_delay_skips_timer(self, manager):
        """Test that missing look_through_seconds prevents timer start."""
        manager._get_current_dawn_brightness.return_value = 50  # Brightness OK
        manager._dawn_config.shutter_look_through_seconds = None

        result = await manager._handle_state_dawn_full_closed()

        # Falls through to dawn-position branch
        assert result == ShutterState.DAWN_FULL_CLOSED
        manager._start_timer.assert_not_called()
        manager._position_shutter.assert_called_once_with(100.0, 0.0, stop_timer=True)

    async def test_missing_dawn_height_config_logs_warning(self, manager):
        """Test warning when dawn height/angle is not configured."""
        manager._get_current_dawn_brightness.return_value = 5  # Below threshold
        manager._dawn_config.shutter_max_height = None

        result = await manager._handle_state_dawn_full_closed()

        assert result == ShutterState.DAWN_FULL_CLOSED
        assert manager.logger.warning.called
        manager._position_shutter.assert_not_called()

    # =========================================================================
    # Dawn handling disabled
    # =========================================================================

    async def test_dawn_disabled_moves_to_neutral(self, manager):
        """Test fallback to neutral position when dawn is disabled."""
        manager._is_dawn_control_enabled.return_value = False

        result = await manager._handle_state_dawn_full_closed()

        assert result == ShutterState.NEUTRAL
        manager._position_shutter.assert_called_once_with(0.0, 0.0, stop_timer=True)

    async def test_dawn_disabled_missing_neutral_config_logs_warning(self, manager):
        """Test warning when neutral position is not configured and dawn is disabled."""
        manager._is_dawn_control_enabled.return_value = False
        manager._facade_config.neutral_pos_height = None

        result = await manager._handle_state_dawn_full_closed()

        assert result == ShutterState.NEUTRAL
        assert manager.logger.warning.called
        manager._position_shutter.assert_not_called()
