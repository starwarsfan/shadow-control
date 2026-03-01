"""Test the DAWN_NEUTRAL state handler."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.shadow_control import ShadowControlManager
from custom_components.shadow_control.const import ShutterState


@pytest.fixture
def manager(mock_manager):
    """Bind the real handler to the mock manager."""
    manager = mock_manager
    manager._handle_state_dawn_neutral = ShadowControlManager._handle_state_dawn_neutral.__get__(manager)

    # Dependencies
    manager._is_dawn_control_enabled = AsyncMock(return_value=True)
    manager._is_shadow_control_enabled = AsyncMock(return_value=False)
    manager._get_current_brightness = MagicMock(return_value=5000)
    manager._get_current_dawn_brightness = MagicMock(return_value=50)
    manager._check_if_facade_is_in_sun = AsyncMock(return_value=False)
    manager._start_timer = AsyncMock()
    manager._position_shutter = AsyncMock()
    manager._check_dawn_close_time_constraint = MagicMock(return_value=False)  # Default: no time-based close

    # Config mocks
    manager._dawn_config = MagicMock()
    manager._shadow_config = MagicMock()
    manager._facade_config = MagicMock()

    # Dawn defaults
    manager._dawn_config.brightness_threshold = 10
    manager._dawn_config.after_seconds = 30
    manager._dawn_config.height_after_dawn = 50.0
    manager._dawn_config.angle_after_dawn = 45.0

    # Shadow defaults
    manager.brightness_threshold = 50000
    manager._shadow_config.after_seconds = 60

    # Facade defaults
    manager._facade_config.neutral_pos_height = 0.0
    manager._facade_config.neutral_pos_angle = 0.0

    return manager


@pytest.mark.asyncio
class TestHandleStateDawnNeutral:
    """Test branches of the DAWN_NEUTRAL handler."""

    # =========================================================================
    # Dawn handling active
    # =========================================================================

    async def test_brightness_below_threshold_starts_close_timer(self, manager):
        """Test that darkness triggers the close timer."""
        manager._get_current_dawn_brightness.return_value = 5  # Below threshold 10

        result = await manager._handle_state_dawn_neutral()

        assert result == ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING
        manager._start_timer.assert_called_once_with(30)

    async def test_close_time_constraint_starts_close_timer(self, manager):
        """Test that close_not_later_than triggers close timer even if brightness is fine."""
        manager._get_current_dawn_brightness.return_value = 50  # Brightness OK
        manager._check_dawn_close_time_constraint.return_value = True  # But time says close

        result = await manager._handle_state_dawn_neutral()

        assert result == ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING
        manager._start_timer.assert_called_once_with(30)

    async def test_brightness_ok_no_time_constraint_stays_in_after_dawn_position(self, manager):
        """Test positioning to after-dawn position when no close condition is met."""
        manager._get_current_dawn_brightness.return_value = 50  # Above threshold

        result = await manager._handle_state_dawn_neutral()

        assert result == ShutterState.DAWN_NEUTRAL
        manager._position_shutter.assert_called_once_with(50.0, 45.0, stop_timer=True)

    async def test_shadow_triggers_when_in_sun(self, manager):
        """Test that shadow mode triggers when facade is in sun and brightness is high."""
        manager._get_current_dawn_brightness.return_value = 50  # Above dawn threshold
        manager._is_shadow_control_enabled.return_value = True
        manager._check_if_facade_is_in_sun.return_value = True
        manager._get_current_brightness.return_value = 60000  # Above shadow threshold
        manager.brightness_threshold = 50000

        result = await manager._handle_state_dawn_neutral()

        assert result == ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING
        manager._start_timer.assert_called_once_with(60)

    async def test_missing_after_dawn_config_logs_warning(self, manager):
        """Test warning when height_after_dawn or angle_after_dawn is not configured."""
        manager._get_current_dawn_brightness.return_value = 50  # Above threshold
        manager._dawn_config.height_after_dawn = None

        result = await manager._handle_state_dawn_neutral()

        assert result == ShutterState.DAWN_NEUTRAL
        assert manager.logger.warning.called
        manager._position_shutter.assert_not_called()

    async def test_missing_close_delay_skips_timer(self, manager):
        """Test that missing dawn close delay prevents timer start even if brightness low."""
        manager._get_current_dawn_brightness.return_value = 5  # Below threshold
        manager._dawn_config.after_seconds = None

        result = await manager._handle_state_dawn_neutral()

        # No timer started, falls through to after-dawn position
        assert result == ShutterState.DAWN_NEUTRAL
        manager._start_timer.assert_not_called()
        manager._position_shutter.assert_called_once_with(50.0, 45.0, stop_timer=True)

    async def test_close_time_constraint_without_close_delay_skips_timer(self, manager):
        """Test that time constraint without close delay configured does not start timer."""
        manager._get_current_dawn_brightness.return_value = 50  # Brightness OK
        manager._check_dawn_close_time_constraint.return_value = True  # Time says close
        manager._dawn_config.after_seconds = None  # But no delay configured

        result = await manager._handle_state_dawn_neutral()

        # No timer, falls through to after-dawn position
        assert result == ShutterState.DAWN_NEUTRAL
        manager._start_timer.assert_not_called()

    # =========================================================================
    # Dawn handling disabled
    # =========================================================================

    async def test_dawn_disabled_shadow_triggers_when_in_sun(self, manager):
        """Test shadow mode when dawn is disabled and facade is in sun."""
        manager._is_dawn_control_enabled.return_value = False
        manager._is_shadow_control_enabled.return_value = True
        manager._check_if_facade_is_in_sun.return_value = True
        manager._get_current_brightness.return_value = 60000
        manager.brightness_threshold = 50000

        result = await manager._handle_state_dawn_neutral()

        assert result == ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING
        manager._start_timer.assert_called_once_with(60)

    async def test_dawn_disabled_moves_to_neutral(self, manager):
        """Test fallback to neutral position when dawn is disabled."""
        manager._is_dawn_control_enabled.return_value = False

        result = await manager._handle_state_dawn_neutral()

        assert result == ShutterState.NEUTRAL
        manager._position_shutter.assert_called_once_with(0.0, 0.0, stop_timer=True)

    async def test_dawn_disabled_missing_neutral_config_logs_warning(self, manager):
        """Test warning when neutral position is not configured and dawn is disabled."""
        manager._is_dawn_control_enabled.return_value = False
        manager._facade_config.neutral_pos_height = None

        result = await manager._handle_state_dawn_neutral()

        assert result == ShutterState.NEUTRAL
        assert manager.logger.warning.called
        manager._position_shutter.assert_not_called()
