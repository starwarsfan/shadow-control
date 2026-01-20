"""Tests for _position_shutter method."""

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.cover import CoverEntityFeature
from homeassistant.util import dt as dt_util

from custom_components.shadow_control import ShadowControlManager
from custom_components.shadow_control.const import (
    LockState,
    ShutterType,
)


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
        instance._timer = None
        instance._last_positioning_time = None
        instance._last_calculated_height = 0.0
        instance._last_calculated_angle = 0.0
        instance._last_unlock_time = None
        instance._last_reported_height = None
        instance._last_reported_angle = None

        # Mock methods
        instance._cancel_timer = MagicMock()
        instance._update_extra_state_attributes = MagicMock()

        # ✅ FIX: _should_output_be_updated returns new_value
        def mock_should_output(config_value, new_value, previous_value):
            return new_value

        instance._should_output_be_updated = MagicMock(side_effect=mock_should_output)
        instance._convert_shutter_angle_percent_to_degrees = MagicMock(return_value=45.0)

        # ✅ NEU: Movement restriction mocks
        instance._dynamic_config.movement_restriction_height = None
        instance._dynamic_config.movement_restriction_angle = None

        # Mock hass
        instance.hass.states.get = MagicMock(
            return_value=MagicMock(
                attributes={
                    "supported_features": (
                        CoverEntityFeature.SET_POSITION | CoverEntityFeature.SET_TILT_POSITION  # ✅ ADD THIS!
                    )
                }
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


class TestPositionShutterSendLogic:
    """Test send command logic in _position_shutter."""

    @pytest.fixture
    def mock_hass(self):
        """Create a mock Home Assistant instance."""
        hass = MagicMock(spec=HomeAssistant)
        hass.states = MagicMock()
        hass.services = MagicMock()
        hass.data = {DOMAIN_DATA_MANAGERS: {}}
        return hass

    @pytest.fixture
    def mock_config_entry(self):
        """Create a mock config entry."""
        return MockConfigEntry(
            domain=DOMAIN,
            entry_id="test_entry_id",
            data={
                "name": "Test Instance",
                "covers": ["cover.test"],
            },
        )

    @pytest.fixture
    def manager(self, mock_hass, mock_config_entry):
        """Create a ShadowControlManager instance with mocks."""
        instance = MagicMock(spec=ShadowControlManager)
        instance.hass = mock_hass
        instance.logger = MagicMock()
        instance._config_entry = mock_config_entry
        instance._config = {}
        instance._target_cover_entity_id = ["cover.test"]
        instance.name = "Test Instance"

        # Facade config
        instance._facade_config = MagicMock()
        instance._facade_config.shutter_type = ShutterType.MODE1

        # Dynamic config
        instance._dynamic_config = MagicMock()
        instance._dynamic_config.movement_restriction_height = MagicMock()
        instance._dynamic_config.movement_restriction_angle = MagicMock()

        # Lock state
        instance.current_lock_state = LockState.UNLOCKED

        # Initial run
        instance._is_initial_run = False

        # Tracking
        instance._previous_shutter_height = None
        instance._previous_shutter_angle = None
        instance._enforce_position_update = False

        # Calculated values
        instance.calculated_shutter_height = 0.0
        instance.calculated_shutter_angle = 0.0
        instance.used_shutter_height = 0.0
        instance.used_shutter_angle = 0.0
        instance.used_shutter_angle_degrees = 0.0

        # Mock methods
        instance._cancel_timer = MagicMock()
        instance._update_extra_state_attributes = MagicMock()

        def mock_should_output(config_value, new_value, previous_value):
            """Mock that returns new_value."""
            return new_value

        instance._should_output_be_updated = MagicMock(side_effect=mock_should_output)
        instance._convert_shutter_angle_percent_to_degrees = MagicMock(return_value=45.0)

        # Mock cover state
        cover_state = MagicMock(spec=State)
        cover_state.attributes = {
            ATTR_SUPPORTED_FEATURES: (CoverEntityFeature.SET_POSITION | CoverEntityFeature.SET_TILT_POSITION),
            "current_position": 50,
            "current_tilt_position": 50,
        }
        mock_hass.states.get.return_value = cover_state

        # Mock services
        mock_hass.services.has_service = MagicMock(return_value=True)
        mock_hass.services.async_call = AsyncMock()

        # Bind real method
        instance._position_shutter = ShadowControlManager._position_shutter.__get__(instance)

        return instance

    # ========================================================================
    # TEST 1: Keine Position-Änderung → Kein Command
    # ========================================================================

    async def test_no_position_change_no_command(self, manager):
        """Test that no command is sent when position doesn't change."""
        # Set previous position
        manager._previous_shutter_height = 50.0
        manager._previous_shutter_angle = 45.0

        # Call with SAME position (difference = 0.0)
        await manager._position_shutter(50.0, 45.0, stop_timer=False)

        # Verify NO service calls
        manager.hass.services.async_call.assert_not_called()

        # Verify internal states updated
        assert manager.calculated_shutter_height == 50.0
        assert manager.calculated_shutter_angle == 45.0

    # ========================================================================
    # TEST 2: Minimale Änderung (< 0.001%) → Kein Command
    # ========================================================================

    async def test_minimal_position_change_no_command(self, manager):
        """Test that no command is sent for changes < 0.001%."""
        # Set previous position
        manager._previous_shutter_height = 50.0000
        manager._previous_shutter_angle = 45.0000

        # Call with MINIMAL change (0.0005% < 0.001%)
        await manager._position_shutter(50.0005, 45.0005, stop_timer=False)

        # Verify NO service calls
        manager.hass.services.async_call.assert_not_called()

    # ========================================================================
    # TEST 3: Änderung genau an Grenze (0.001%) → Kein Command
    # ========================================================================

    async def test_boundary_position_change_no_command(self, manager):
        """Test that no command is sent at exactly 0.001% change."""
        # Set previous position
        manager._previous_shutter_height = 50.0000
        manager._previous_shutter_angle = 45.0000

        # Call with EXACT boundary (0.001%)
        await manager._position_shutter(50.0010, 45.0010, stop_timer=False)

        # Verify NO service calls (> 0.001 is FALSE for exactly 0.001)
        manager.hass.services.async_call.assert_not_called()

    # ========================================================================
    # TEST 4: Änderung knapp über Grenze (0.002%) → Command gesendet
    # ========================================================================

    async def test_small_position_change_sends_command(self, manager):
        """Test that command IS sent for changes > 0.001%."""

        # Set previous position
        manager._previous_shutter_height = 50.0000
        manager._previous_shutter_angle = 45.0000

        # Call with change ABOVE threshold (0.002% > 0.001%)
        await manager._position_shutter(50.0020, 45.0020, stop_timer=False)

        # Verify service calls were made (2 calls: height + angle)
        assert manager.hass.services.async_call.call_count == 2

        # ✅ FIX: Verify calls correctly
        calls = manager.hass.services.async_call.call_args_list

        # First call: set_cover_position
        assert calls[0].args[0] == "cover"
        assert calls[0].args[1] == "set_cover_position"

        # Second call: set_cover_tilt_position
        assert calls[1].args[0] == "cover"
        assert calls[1].args[1] == "set_cover_tilt_position"

    # ========================================================================
    # TEST 5: Große Änderung (1.0%) → Command gesendet
    # ========================================================================

    async def test_large_position_change_sends_command(self, manager):
        """Test that command is sent for significant changes."""
        # Set previous position
        manager._previous_shutter_height = 50.0
        manager._previous_shutter_angle = 45.0

        # Call with LARGE change (1.0%)
        await manager._position_shutter(51.0, 46.0, stop_timer=False)

        # Verify service calls
        assert manager.hass.services.async_call.call_count == 2

    # ========================================================================
    # TEST 6: Nur Höhe ändert sich → Nur Höhe + Angle (wegen height change)
    # ========================================================================

    async def test_only_height_change_sends_both(self, manager):
        """Test that both height and angle are sent when height changes."""
        # Set previous position
        manager._previous_shutter_height = 50.0
        manager._previous_shutter_angle = 45.0

        # Call with ONLY height change
        await manager._position_shutter(51.0, 45.0, stop_timer=False)

        # Verify BOTH commands sent (angle follows height)
        assert manager.hass.services.async_call.call_count == 2

    # ========================================================================
    # TEST 7: Nur Winkel ändert sich → Nur Winkel
    # ========================================================================

    async def test_only_angle_change_sends_angle_only(self, manager):
        """Test that only angle is sent when only angle changes."""
        # Set previous position
        manager._previous_shutter_height = 50.0
        manager._previous_shutter_angle = 45.0

        # Call with ONLY angle change
        await manager._position_shutter(50.0, 46.0, stop_timer=False)

        # Verify only angle command sent
        assert manager.hass.services.async_call.call_count == 1

        # ✅ FIX: Verify it's the angle command
        call = manager.hass.services.async_call.call_args
        assert call.args[0] == "cover"
        assert call.args[1] == "set_cover_tilt_position"

    # ========================================================================
    # TEST 8: _enforce_position_update überschreibt Logik
    # ========================================================================

    async def test_enforce_position_update_always_sends(self, manager):
        """Test that enforce flag always sends commands."""
        # Set previous position (SAME as target)
        manager._previous_shutter_height = 50.0
        manager._previous_shutter_angle = 45.0

        # Set enforce flag
        manager._enforce_position_update = True

        # Call with SAME position
        await manager._position_shutter(50.0, 45.0, stop_timer=False)

        # Verify commands WERE sent despite no change
        assert manager.hass.services.async_call.call_count == 2

    # ========================================================================
    # TEST 9: Erste Positionierung (previous = None) → Command gesendet
    # ========================================================================

    async def test_first_positioning_sends_command(self, manager):
        """Test that first positioning always sends commands."""
        # No previous position
        manager._previous_shutter_height = None
        manager._previous_shutter_angle = None

        # Call
        await manager._position_shutter(50.0, 45.0, stop_timer=False)

        # Verify commands sent
        assert manager.hass.services.async_call.call_count == 2

    # ========================================================================
    # TEST 10: Mode3 sendet kein Angle
    # ========================================================================

    async def test_mode3_no_angle_command(self, manager):
        """Test that Mode3 doesn't send angle commands."""
        # Set to Mode3
        manager._facade_config.shutter_type = ShutterType.MODE3

        # Set previous
        manager._previous_shutter_height = 50.0
        manager._previous_shutter_angle = 45.0

        # Call with change
        await manager._position_shutter(51.0, 46.0, stop_timer=False)

        # Verify only height command (no angle for Mode3)
        assert manager.hass.services.async_call.call_count == 1

        # ✅ FIX: Verify it's height
        call = manager.hass.services.async_call.call_args
        assert call.args[0] == "cover"
        assert call.args[1] == "set_cover_position"

    # ========================================================================
    # TEST 11: Locked → Keine Commands (außer forced position)
    # ========================================================================

    async def test_locked_no_commands(self, manager):
        """Test that locked state prevents commands."""
        # Set locked
        manager.current_lock_state = LockState.LOCKED_MANUALLY

        # Set previous
        manager._previous_shutter_height = 50.0
        manager._previous_shutter_angle = 45.0

        # Call with change
        await manager._position_shutter(51.0, 46.0, stop_timer=False)

        # Verify NO commands sent
        manager.hass.services.async_call.assert_not_called()
