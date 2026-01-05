"""Test the cleanup logic when automation is disabled."""

from unittest.mock import MagicMock

import pytest

from custom_components.shadow_control import ShadowControlManager
from custom_components.shadow_control.const import ShutterState


@pytest.fixture
def manager(mock_manager):
    """Bind the real cleanup methods to the mock manager."""
    manager = mock_manager
    manager._shadow_handling_was_disabled = ShadowControlManager._shadow_handling_was_disabled.__get__(manager)
    manager._dawn_handling_was_disabled = ShadowControlManager._dawn_handling_was_disabled.__get__(manager)

    # Dependencies
    manager._cancel_timer = MagicMock()
    manager._update_extra_state_attributes = MagicMock()

    return manager


@pytest.mark.asyncio
class TestHandlingDisabled:
    """Test suite for Shadow and Dawn disabling logic."""

    async def test_shadow_disabled_while_in_shadow_state(self, manager):
        """Verify that disabling shadow while active resets to NEUTRAL."""
        manager.current_shutter_state = ShutterState.SHADOW_FULL_CLOSED

        await manager._shadow_handling_was_disabled()

        assert manager.current_shutter_state == ShutterState.NEUTRAL
        manager._cancel_timer.assert_called_once()
        manager._update_extra_state_attributes.assert_called_once()

    async def test_shadow_disabled_while_in_neutral(self, manager):
        """Nothing should change if already in NEUTRAL."""
        manager.current_shutter_state = ShutterState.NEUTRAL

        await manager._shadow_handling_was_disabled()

        assert manager.current_shutter_state == ShutterState.NEUTRAL
        manager._cancel_timer.assert_not_called()

    async def test_shadow_disabled_while_in_dawn_state(self, manager):
        """Disabling shadow should NOT affect an active dawn state."""
        manager.current_shutter_state = ShutterState.DAWN_FULL_CLOSED

        await manager._shadow_handling_was_disabled()

        # Should stay in Dawn
        assert manager.current_shutter_state == ShutterState.DAWN_FULL_CLOSED
        manager._cancel_timer.assert_not_called()

    async def test_dawn_disabled_while_in_dawn_state(self, manager):
        """Verify that disabling dawn while active resets to NEUTRAL."""
        manager.current_shutter_state = ShutterState.DAWN_NEUTRAL_TIMER_RUNNING

        await manager._dawn_handling_was_disabled()

        assert manager.current_shutter_state == ShutterState.NEUTRAL
        manager._cancel_timer.assert_called_once()

    async def test_dawn_disabled_while_in_shadow_state(self, manager):
        """Disabling dawn should NOT affect an active shadow state."""
        manager.current_shutter_state = ShutterState.SHADOW_HORIZONTAL_NEUTRAL

        await manager._dawn_handling_was_disabled()

        # Should stay in Shadow
        assert manager.current_shutter_state == ShutterState.SHADOW_HORIZONTAL_NEUTRAL
