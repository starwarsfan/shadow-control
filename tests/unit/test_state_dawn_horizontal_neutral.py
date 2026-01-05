"""Test the DAWN_HORIZONTAL_NEUTRAL state handler."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.shadow_control import ShadowControlManager
from custom_components.shadow_control.const import ShutterState


@pytest.fixture
def manager(mock_manager):
    """Bind the real handler to the mock manager."""
    manager = mock_manager
    manager._handle_state_dawn_horizontal_neutral = ShadowControlManager._handle_state_dawn_horizontal_neutral.__get__(manager)

    # Dependencies
    manager._is_dawn_control_enabled = AsyncMock(return_value=True)
    manager._get_current_dawn_brightness = MagicMock(return_value=50)
    manager._start_timer = AsyncMock()
    manager._position_shutter = AsyncMock()

    # Config mocks
    manager._dawn_config = MagicMock()
    manager._facade_config = MagicMock()

    # Default thresholds
    manager._dawn_config.brightness_threshold = 10
    manager._dawn_config.shutter_max_height = 100.0
    manager._dawn_config.shutter_look_through_angle = 90.0
    manager._dawn_config.shutter_look_through_seconds = 600

    return manager


@pytest.mark.asyncio
class TestHandleStateDawnHorizontalNeutral:
    """Test branches of the DAWN_HORIZONTAL_NEUTRAL handler."""

    async def test_darkness_returns_recloses_shutter(self, manager):
        """Test transitioning to FULL_CLOSED if brightness drops below threshold."""
        manager._get_current_dawn_brightness.return_value = 5  # Below 10

        result = await manager._handle_state_dawn_horizontal_neutral()

        assert result == ShutterState.DAWN_FULL_CLOSED
        manager._position_shutter.assert_called_once_with(100.0, 90.0, stop_timer=False)

    async def test_brightness_ok_starts_opening_timer(self, manager):
        """Test starting the timer to open further when brightness is stable."""
        manager._get_current_dawn_brightness.return_value = 50  # Above 10

        result = await manager._handle_state_dawn_horizontal_neutral()

        assert result == ShutterState.DAWN_NEUTRAL_TIMER_RUNNING
        manager._start_timer.assert_called_once_with(600)

    async def test_missing_timer_config_stays_in_state(self, manager):
        """Test warning and staying in state if look_through_seconds is missing."""
        manager._get_current_dawn_brightness.return_value = 50
        manager._dawn_config.shutter_look_through_seconds = None

        result = await manager._handle_state_dawn_horizontal_neutral()

        assert result == ShutterState.DAWN_HORIZONTAL_NEUTRAL
        assert manager.logger.warning.called

    async def test_dawn_disabled_retreats_to_neutral(self, manager):
        """Test falling back to global NEUTRAL if dawn mode is turned off."""
        manager._is_dawn_control_enabled.return_value = False
        manager._facade_config.neutral_pos_height = 0.0
        manager._facade_config.neutral_pos_angle = 0.0

        result = await manager._handle_state_dawn_horizontal_neutral()

        assert result == ShutterState.NEUTRAL
        manager._position_shutter.assert_called_once_with(0.0, 0.0, stop_timer=True)

    async def test_missing_height_config_skips_reclose_logic(self, manager):
        """Test that missing height/angle config prevents movement but allows timer flow."""
        manager._get_current_dawn_brightness.return_value = 5
        manager._dawn_config.shutter_max_height = None

        # In your code, if height is None, it bypasses the re-close block
        # and falls through to the timer block.
        result = await manager._handle_state_dawn_horizontal_neutral()

        assert result == ShutterState.DAWN_NEUTRAL_TIMER_RUNNING
        manager._start_timer.assert_called_once()
