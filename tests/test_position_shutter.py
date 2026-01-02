"""Tests for _position_shutter method."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.shadow_control import ShadowControlManager
from custom_components.shadow_control.const import LockState, ShutterType


class TestPositionShutter:
    """Test _position_shutter method."""

    @pytest.fixture
    def manager(self):
        """Create a mock ShadowControlManager instance."""
        instance = MagicMock(spec=ShadowControlManager)
        instance.logger = MagicMock()
        instance.hass = MagicMock()
        instance.name = "Test Manager"
        instance._config = MagicMock()
        instance._dynamic_config = MagicMock()
        instance._facade_config = MagicMock()

        # Default state
        instance._is_initial_run = False
        instance.current_lock_state = LockState.UNLOCKED
        instance._target_cover_entity_id = ["cover.test"]
        instance._enforce_position_update = False

        # Facade config defaults
        instance._facade_config.shutter_type = ShutterType.MODE1

        # Previous values
        instance._previous_shutter_height = 50.0
        instance._previous_shutter_angle = 40.0

        # Tracking
        instance._last_positioning_time = None
        instance._last_calculated_height = 0.0
        instance._last_calculated_angle = 0.0
        instance._last_unlock_time = None
        instance._last_reported_height = None
        instance._last_reported_angle = None

        # Mock methods
        instance._cancel_timer = MagicMock()
        instance._update_extra_state_attributes = MagicMock()
        instance._should_output_be_updated = MagicMock(side_effect=lambda **kwargs: kwargs.get("new_value"))
        instance._convert_shutter_angle_percent_to_degrees = MagicMock(return_value=45.0)

        # Mock hass
        instance.hass.states.get = MagicMock(
            return_value=MagicMock(
                attributes={"supported_features": 15}  # SET_POSITION | SET_TILT_POSITION
            )
        )
        instance.hass.services.has_service = MagicMock(return_value=True)

        # Better async_call mock
        async def mock_async_call(domain, service, service_data, blocking=False):
            """Mock async_call."""
            return

        instance.hass.services.async_call = AsyncMock(side_effect=mock_async_call)

        # Bind real method
        instance._position_shutter = ShadowControlManager._position_shutter.__get__(instance)

        return instance

    # ========================================================================
    # PHASE 1: TIMER HANDLING
    # ========================================================================

    async def test_stops_timer_when_requested(self, manager):
        """Test that timer is cancelled when stop_timer=True."""
        manager._is_initial_run = True  # Exit early to isolate timer test

        await manager._position_shutter(80.0, 45.0, stop_timer=True)

        manager._cancel_timer.assert_called_once()

    async def test_does_not_stop_timer_when_not_requested(self, manager):
        """Test that timer is not cancelled when stop_timer=False."""
        manager._is_initial_run = True  # Exit early

        await manager._position_shutter(80.0, 45.0, stop_timer=False)

        manager._cancel_timer.assert_not_called()

    # ========================================================================
    # PHASE 2: INITIAL RUN HANDLING
    # ========================================================================

    async def test_initial_run_sets_values_no_positioning(self, manager):
        """Test that initial run sets values but doesn't position."""
        manager._is_initial_run = True

        await manager._position_shutter(80.0, 45.0, stop_timer=False)

        # Should set calculated values
        assert manager.calculated_shutter_height == 80.0
        assert manager.calculated_shutter_angle == 45.0

        # Should set previous values
        assert manager._previous_shutter_height == 80.0
        assert manager._previous_shutter_angle == 45.0

        # Should NOT call positioning services
        manager.hass.services.async_call.assert_not_called()

        # Should update attributes
        manager._update_extra_state_attributes.assert_called_once()

    # ========================================================================
    # PHASE 3: LOCK STATE HANDLING
    # ========================================================================

    async def test_locked_skips_positioning(self, manager):
        """Test that locked state skips positioning."""
        manager._is_initial_run = False
        manager.current_lock_state = LockState.LOCKED_MANUALLY

        await manager._position_shutter(80.0, 45.0, stop_timer=False)

        # Should NOT call positioning services
        manager.hass.services.async_call.assert_not_called()

    async def test_locked_with_forced_position_sends_forced_values(self, manager):
        """Test that lock with forced position sends configured values."""
        manager._is_initial_run = False
        manager.current_lock_state = LockState.LOCKED_MANUALLY_WITH_FORCED_POSITION
        manager._dynamic_config.lock_height = 30.0
        manager._dynamic_config.lock_angle = 20.0

        await manager._position_shutter(80.0, 45.0, stop_timer=False)

        # Verify forced position was sent
        calls = manager.hass.services.async_call.call_args_list

        # Check position call (inverted: 100 - 30 = 70)
        position_call = next(c for c in calls if c[0][1] == "set_cover_position")
        assert position_call[0][2]["position"] == 70  # [0][2] statt [1]

        # Check tilt call (inverted: 100 - 20 = 80)
        tilt_call = next(c for c in calls if c[0][1] == "set_cover_tilt_position")
        assert tilt_call[0][2]["tilt_position"] == 80  # [0][2] statt [1]

    # ========================================================================
    # PHASE 4: NORMAL POSITIONING
    # ========================================================================

    async def test_normal_positioning_sends_both_commands(self, manager):
        """Test normal positioning sends height and angle commands."""
        manager._is_initial_run = False
        manager.current_lock_state = LockState.UNLOCKED
        manager._previous_shutter_height = 50.0  # Different from target
        manager._previous_shutter_angle = 40.0  # Different from target

        # Mock to ensure both commands are sent
        manager.used_shutter_height = 80.0
        manager.used_shutter_angle = 45.0

        await manager._position_shutter(80.0, 45.0, stop_timer=False)

        # Should send at least 1 command (height is different)
        assert manager.hass.services.async_call.call_count >= 1

        calls = manager.hass.services.async_call.call_args_list

        # Verify position call exists
        position_calls = [c for c in calls if c[0][1] == "set_cover_position"]
        assert len(position_calls) >= 1

        position_call = position_calls[0]
        assert position_call[0][2]["entity_id"] == "cover.test"
        assert position_call[0][2]["position"] == 20  # 100 - 80

    async def test_no_positioning_when_values_unchanged(self, manager):
        """Test that no commands are sent when values didn't change."""
        manager._is_initial_run = False
        manager.current_lock_state = LockState.UNLOCKED
        manager._previous_shutter_height = 80.0  # Same as target
        manager._previous_shutter_angle = 45.0  # Same as target

        await manager._position_shutter(80.0, 45.0, stop_timer=False)

        # Should NOT send any commands (values unchanged)
        manager.hass.services.async_call.assert_not_called()

    async def test_enforce_position_update_forces_positioning(self, manager):
        """Test that enforce flag forces positioning even when values unchanged."""
        manager._is_initial_run = False
        manager.current_lock_state = LockState.UNLOCKED
        manager._previous_shutter_height = 80.0  # Same as target
        manager._previous_shutter_angle = 45.0  # Same as target
        manager._enforce_position_update = True  # But force it!

        # Mock to ensure values are set
        manager.used_shutter_height = 80.0
        manager.used_shutter_angle = 45.0

        await manager._position_shutter(80.0, 45.0, stop_timer=False)

        # Should send commands despite values being unchanged
        assert manager.hass.services.async_call.call_count >= 1

    # ========================================================================
    # PHASE 5: MODE3 (NO TILT) HANDLING
    # ========================================================================

    async def test_mode3_skips_tilt_positioning(self, manager):
        """Test that Mode3 (Jalousie) skips tilt positioning."""
        manager._is_initial_run = False
        manager.current_lock_state = LockState.UNLOCKED
        manager._facade_config.shutter_type = ShutterType.MODE3
        manager._previous_shutter_height = 50.0
        manager._previous_shutter_angle = 40.0

        await manager._position_shutter(80.0, 45.0, stop_timer=False)

        # Should only send position command (not tilt)
        assert manager.hass.services.async_call.call_count == 1

        # Verify it's a position call (not tilt)
        call = manager.hass.services.async_call.call_args_list[0]
        assert call[0][1] == "set_cover_position"

    # ========================================================================
    # PHASE 6: TRACKING UPDATE
    # ========================================================================

    async def test_tracking_updated_after_positioning(self, manager):
        """Test that tracking is updated after successful positioning."""
        manager._is_initial_run = False
        manager.current_lock_state = LockState.UNLOCKED
        manager._previous_shutter_height = 50.0
        manager._previous_shutter_angle = 40.0
        manager.used_shutter_height = 80.0
        manager.used_shutter_angle = 45.0

        # Mock should_output_be_updated to return the new values
        manager._should_output_be_updated = MagicMock(side_effect=lambda **kwargs: kwargs.get("new_value"))

        await manager._position_shutter(80.0, 45.0, stop_timer=False)

        # Verify tracking was updated
        assert manager._last_positioning_time is not None
        assert isinstance(manager._last_positioning_time, datetime)
        assert manager._last_calculated_height == 80.0
        assert manager._last_calculated_angle == 45.0

    async def test_tracking_not_updated_when_no_positioning(self, manager):
        """Test that tracking is NOT updated when no positioning occurred."""
        manager._is_initial_run = False
        manager.current_lock_state = LockState.UNLOCKED
        manager._previous_shutter_height = 80.0  # Same = no positioning
        manager._previous_shutter_angle = 45.0
        manager._last_positioning_time = None

        await manager._position_shutter(80.0, 45.0, stop_timer=False)

        # Verify tracking was NOT updated (no positioning happened)
        assert manager._last_positioning_time is None

    async def test_tracking_not_updated_on_initial_run(self, manager):
        """Test that tracking is NOT updated on initial run."""
        manager._is_initial_run = True
        manager._last_positioning_time = None

        await manager._position_shutter(80.0, 45.0, stop_timer=False)

        # Verify tracking was NOT updated (initial run)
        assert manager._last_positioning_time is None
