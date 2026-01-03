"""Tests for _process_shutter_state()."""

import pytest

from custom_components.shadow_control.const import ShutterState


@pytest.mark.asyncio
async def test_process_shutter_state_recursion_path(mock_manager):
    """Test that the orchestrator follows a multi-step transition path."""

    # Scenario: Sun rises -> Transition from NEUTRAL to SHADOW_NEUTRAL
    # and then immediately to TIMER_RUNNING.

    # 1. Setup the chain of returns
    mock_manager._state_handlers[ShutterState.NEUTRAL].return_value = ShutterState.SHADOW_NEUTRAL
    mock_manager._state_handlers[ShutterState.SHADOW_NEUTRAL].return_value = ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING
    # The last one returns itself to break the recursion
    mock_manager._state_handlers[ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING].return_value = ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING

    # 2. Run the logic
    await mock_manager._process_shutter_state()

    # 3. Verify the final state
    assert mock_manager.current_shutter_state == ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING

    # 4. Verify the "Path" taken
    mock_manager._state_handlers[ShutterState.NEUTRAL].assert_called_once()
    mock_manager._state_handlers[ShutterState.SHADOW_NEUTRAL].assert_called_once()
    mock_manager._state_handlers[ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING].assert_called_once()

    # Verify attributes were updated at each step
    assert mock_manager._update_extra_state_attributes.call_count == 2


@pytest.mark.asyncio
async def test_process_shutter_state_missing_handler(mock_manager):
    """Test behavior when a state has no assigned handler."""
    mock_manager.current_shutter_state = ShutterState.DAWN_FULL_CLOSED

    # Simulate a missing entry in the dictionary
    mock_manager._state_handlers = {}

    await mock_manager._process_shutter_state()

    # Should log and cleanup
    mock_manager._cancel_timer.assert_called_once()
    mock_manager._update_extra_state_attributes.assert_called_once()
