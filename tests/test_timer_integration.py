"""Tests for timer-based positioning integration."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import Event, HomeAssistant, State
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.shadow_control import ShadowControlManager
from custom_components.shadow_control.const import (
    DOMAIN,
    DOMAIN_DATA_MANAGERS,
    LockState,
    ShutterType,
)


class TestTimerIntegration:
    """Test timer-based positioning integration."""

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

        # Facade config
        instance._facade_config = MagicMock()
        instance._facade_config.shutter_type = ShutterType.MODE1
        instance._facade_config.modification_tolerance_height = 2.0
        instance._facade_config.modification_tolerance_angle = 2.0
        instance._facade_config.max_movement_duration = 30.0

        # Dynamic config
        instance._dynamic_config = MagicMock()
        instance._dynamic_config.lock_integration = False
        instance._dynamic_config.lock_integration_with_position = False

        # Tracking variables
        instance._last_positioning_time = None
        instance._last_calculated_height = 50.0
        instance._last_calculated_angle = 45.0
        instance._last_reported_height = None
        instance._last_reported_angle = None
        instance._last_unlock_time = None
        instance._locked_by_auto_lock = False
        instance._height_during_lock_state = 0.0
        instance._angle_during_lock_state = 0.0
        instance.current_lock_state = LockState.UNLOCKED

        # Mock methods
        instance._activate_auto_lock = AsyncMock()

        # Bind real methods
        instance._is_positioning_in_progress = ShadowControlManager._is_positioning_in_progress.__get__(instance)
        instance._check_positioning_completed = ShadowControlManager._check_positioning_completed.__get__(instance)

        return instance

    # ========================================================================
    # TEST 1: Timer-Abbruch bei neuer Positionierung
    # ========================================================================

    async def test_new_positioning_resets_timer(self, manager):
        """Test that new positioning resets the timer."""

        # First positioning
        first_time = datetime.now(UTC)
        manager._last_positioning_time = first_time
        manager._last_reported_height = 30.0
        manager._last_reported_angle = 20.0

        # Verify timer is running
        assert manager._is_positioning_in_progress() is True

        # Simulate new positioning after 5 seconds
        second_time = first_time + timedelta(seconds=5)
        with patch("custom_components.shadow_control.datetime") as mock_datetime:
            mock_datetime.now.return_value = second_time

            # New positioning
            manager._last_positioning_time = second_time
            manager._last_calculated_height = 80.0  # New target
            manager._last_calculated_angle = 60.0  # New target
            manager._last_reported_height = None  # Reset
            manager._last_reported_angle = None  # Reset

            # Verify new timer is running
            assert manager._is_positioning_in_progress() is True

            # Old reported positions should be ignored
            # (They were from the old positioning)
            assert manager._last_reported_height is None

    # ========================================================================
    # TEST 2: Timer läuft ab - Position passt - KEIN Auto-Lock
    # ========================================================================

    async def test_timer_expires_position_matches_no_autolock(self, manager):
        """Test no auto-lock when position matches after timer."""

        # Set positioning time 40 seconds ago (timer: 30s)
        manager._last_positioning_time = datetime.now(UTC) - timedelta(seconds=40)
        manager._last_calculated_height = 50.0
        manager._last_calculated_angle = 45.0

        # Reported position matches target (within tolerance)
        manager._last_reported_height = 50.0
        manager._last_reported_angle = 45.0

        # Check positioning completed
        await manager._check_positioning_completed()

        # No auto-lock should be triggered
        manager._activate_auto_lock.assert_not_called()

        # Timer should be reset
        assert manager._last_positioning_time is None
        assert manager._last_reported_height is None
        assert manager._last_reported_angle is None

    # ========================================================================
    # TEST 3: Timer läuft ab - Position unterschiedlich - Auto-Lock!
    # ========================================================================

    async def test_timer_expires_position_differs_autolock(self, manager):
        """Test auto-lock when position differs after timer."""

        # Set positioning time 40 seconds ago (timer: 30s)
        manager._last_positioning_time = datetime.now(UTC) - timedelta(seconds=40)
        manager._last_calculated_height = 50.0
        manager._last_calculated_angle = 45.0

        # Reported position differs from target (manual intervention!)
        manager._last_reported_height = 30.0  # Different!
        manager._last_reported_angle = 20.0  # Different!

        # Check positioning completed
        await manager._check_positioning_completed()

        # Auto-lock SHOULD be triggered
        manager._activate_auto_lock.assert_called_once_with(30.0, 20.0)

        # Timer should be reset
        assert manager._last_positioning_time is None
        assert manager._last_reported_height is None
        assert manager._last_reported_angle is None

    # ========================================================================
    # TEST 4: Timer läuft noch - Keine Prüfung
    # ========================================================================

    async def test_timer_still_running_no_check(self, manager):
        """Test no validation when timer still running."""

        # Set positioning time 10 seconds ago (timer: 30s - still running!)
        manager._last_positioning_time = datetime.now(UTC) - timedelta(seconds=10)
        manager._last_reported_height = 30.0
        manager._last_reported_angle = 20.0

        # Check positioning completed
        await manager._check_positioning_completed()

        # No auto-lock (timer still running)
        manager._activate_auto_lock.assert_not_called()

        # Timer should NOT be reset (still running)
        assert manager._last_positioning_time is not None
        assert manager._last_reported_height == 30.0

    # ========================================================================
    # TEST 5: Kein Timer aktiv - Keine Prüfung
    # ========================================================================

    async def test_no_timer_no_check(self, manager):
        """Test no validation when no timer active."""
        # No positioning time set
        manager._last_positioning_time = None

        # Check positioning completed
        await manager._check_positioning_completed()

        # No auto-lock
        manager._activate_auto_lock.assert_not_called()

    # ========================================================================
    # TEST 6: Timer abgelaufen - Keine Position gemeldet
    # ========================================================================

    async def test_timer_expired_no_reported_position(self, manager):
        """Test no auto-lock when no position reported during timer."""

        # Set positioning time 40 seconds ago (timer: 30s)
        manager._last_positioning_time = datetime.now(UTC) - timedelta(seconds=40)

        # NO reported position (cover didn't report back?)
        manager._last_reported_height = None
        manager._last_reported_angle = None

        # Check positioning completed
        await manager._check_positioning_completed()

        # No auto-lock (no position to check)
        manager._activate_auto_lock.assert_not_called()

        # Timer should be reset
        assert manager._last_positioning_time is None

    # ========================================================================
    # TEST 7: Mode3 (Jalousie) - Nur Höhe prüfen
    # ========================================================================

    async def test_mode3_only_height_checked(self, manager):
        """Test Mode3 only checks height, ignores angle."""

        # Set to Mode3
        manager._facade_config.shutter_type = ShutterType.MODE3

        # Set positioning time 40 seconds ago
        manager._last_positioning_time = datetime.now(UTC) - timedelta(seconds=40)
        manager._last_calculated_height = 50.0
        manager._last_calculated_angle = 45.0

        # Height matches, angle differs (should be ignored)
        manager._last_reported_height = 50.0  # Matches
        manager._last_reported_angle = None  # Mode3 has no angle

        # Check positioning completed
        await manager._check_positioning_completed()

        # No auto-lock (height matches, angle ignored)
        manager._activate_auto_lock.assert_not_called()

    # Am Ende von tests/test_timer_integration.py hinzufügen:

    # ========================================================================
    # TEST 8: Unlock während Timer - Grace Period aktiv
    # ========================================================================

    async def test_unlock_during_timer_grace_period_active(self, manager):
        """Test that unlock during timer activates grace period."""
        # Positioning timer is running
        manager._last_positioning_time = datetime.now(UTC) - timedelta(seconds=10)

        # User unlocks
        manager._last_unlock_time = datetime.now(UTC)

        # Both timers should be active
        assert manager._is_positioning_in_progress() is True

        # Simulate manual movement would normally trigger auto-lock
        # But unlock grace period prevents it
        elapsed_unlock = (datetime.now(UTC) - manager._last_unlock_time).total_seconds()
        assert elapsed_unlock < manager._facade_config.max_movement_duration

    # ========================================================================
    # TEST 9: Mehrfach-Positionierung (Dawn-Sequenz Simulation)
    # ========================================================================

    async def test_multiple_positioning_dawn_sequence(self, manager):
        """Test multiple positioning commands (like dawn sequence)."""
        # First positioning: Lookthrough position
        first_time = datetime.now(UTC)
        manager._last_positioning_time = first_time
        manager._last_calculated_height = 30.0  # Lookthrough
        manager._last_calculated_angle = 50.0

        # Report position during first timer
        manager._last_reported_height = 25.0  # Still moving
        manager._last_reported_angle = 45.0

        # Verify first timer is running
        assert manager._is_positioning_in_progress() is True

        # Second positioning: Open position (before first timer expires!)
        second_time = first_time + timedelta(seconds=5)
        manager._last_positioning_time = second_time  # NEW timer!
        manager._last_calculated_height = 0.0  # Open
        manager._last_calculated_angle = 0.0
        manager._last_reported_height = None  # Reset
        manager._last_reported_angle = None

        # Old timer is now irrelevant, new timer is active
        # Simulate time passing
        with patch("custom_components.shadow_control.datetime") as mock_dt:
            mock_dt.now.return_value = second_time + timedelta(seconds=3)

            # New timer still running
            assert manager._is_positioning_in_progress() is True

    # ========================================================================
    # TEST 10: Position innerhalb Toleranz nach Timer
    # ========================================================================

    async def test_timer_expired_position_within_tolerance(self, manager):
        """Test no auto-lock when position within tolerance after timer."""
        # Set positioning time 40 seconds ago
        manager._last_positioning_time = datetime.now(UTC) - timedelta(seconds=40)
        manager._last_calculated_height = 50.0
        manager._last_calculated_angle = 45.0

        # Reported position within tolerance (< 2%)
        manager._last_reported_height = 51.5  # 1.5% diff
        manager._last_reported_angle = 46.5  # 1.5° diff

        # Check positioning completed
        await manager._check_positioning_completed()

        # No auto-lock (within tolerance)
        manager._activate_auto_lock.assert_not_called()

    # ========================================================================
    # TEST 11: Position außerhalb Toleranz (Höhe OK, Winkel nicht)
    # ========================================================================

    async def test_timer_expired_height_ok_angle_differs(self, manager):
        """Test auto-lock when height OK but angle differs."""
        # Set positioning time 40 seconds ago
        manager._last_positioning_time = datetime.now(UTC) - timedelta(seconds=40)
        manager._last_calculated_height = 50.0
        manager._last_calculated_angle = 45.0

        # Height OK, angle differs
        manager._last_reported_height = 50.0  # Perfect!
        manager._last_reported_angle = 60.0  # 15° diff > tolerance

        # Check positioning completed
        await manager._check_positioning_completed()

        # Auto-lock SHOULD be triggered
        manager._activate_auto_lock.assert_called_once_with(50.0, 60.0)

    # ========================================================================
    # TEST 12: Position außerhalb Toleranz (Winkel OK, Höhe nicht)
    # ========================================================================

    async def test_timer_expired_angle_ok_height_differs(self, manager):
        """Test auto-lock when angle OK but height differs."""
        # Set positioning time 40 seconds ago
        manager._last_positioning_time = datetime.now(UTC) - timedelta(seconds=40)
        manager._last_calculated_height = 50.0
        manager._last_calculated_angle = 45.0

        # Angle OK, height differs
        manager._last_reported_height = 70.0  # 20% diff > tolerance
        manager._last_reported_angle = 45.0  # Perfect!

        # Check positioning completed
        await manager._check_positioning_completed()

        # Auto-lock SHOULD be triggered
        manager._activate_auto_lock.assert_called_once_with(70.0, 45.0)

    # ========================================================================
    # TEST 13: Externe Lock-Entity Sync während Timer
    # ========================================================================

    async def test_external_lock_sync_during_timer(self, manager):
        """Test external lock sync works during positioning timer."""

        # Timer is running
        manager._last_positioning_time = datetime.now(UTC) - timedelta(seconds=10)

        # Simulate external lock entity state change
        manager._config = {"lock_integration_entity": "input_boolean.external_lock"}

        # Mock internal lock entity
        internal_lock_entity_id = "switch.test_instance_lock"

        def mock_get_internal_entity_id(internal_enum):
            return internal_lock_entity_id

        manager.get_internal_entity_id = mock_get_internal_entity_id

        # Mock hass.states.get for internal lock
        internal_lock_state = MagicMock()
        internal_lock_state.state = STATE_OFF
        manager.hass.states.get.return_value = internal_lock_state

        # Mock service call
        manager.hass.services.async_call = AsyncMock()

        # Create external lock state change event

        old_state = State("input_boolean.external_lock", STATE_OFF)
        new_state = State("input_boolean.external_lock", STATE_ON)

        # Bind the real method
        manager._async_external_lock_entity_state_change_listener = ShadowControlManager._async_external_lock_entity_state_change_listener.__get__(
            manager
        )

        # Create event
        event_data = {
            "entity_id": "input_boolean.external_lock",
            "old_state": old_state,
            "new_state": new_state,
        }
        event = Event("state_changed", event_data)

        # Call listener
        await manager._async_external_lock_entity_state_change_listener(event)

        # Verify sync happened
        manager.hass.services.async_call.assert_called_once()

        # Verify unlock time was set
        assert manager._last_unlock_time is None  # Only set when unlocking (ON->OFF)

    # ========================================================================
    # TEST 14: Externe Lock Unlock setzt Grace Period
    # ========================================================================

    async def test_external_lock_unlock_sets_grace_period(self, manager):
        """Test external lock unlock sets unlock grace period."""

        # Mock internal lock entity
        internal_lock_entity_id = "switch.test_instance_lock"
        manager.get_internal_entity_id = lambda _: internal_lock_entity_id

        # Mock internal lock state
        internal_lock_state = MagicMock()
        internal_lock_state.state = STATE_ON  # Currently locked
        manager.hass.states.get.return_value = internal_lock_state

        # Mock service call
        manager.hass.services.async_call = AsyncMock()

        # Bind the real method
        manager._async_external_lock_entity_state_change_listener = ShadowControlManager._async_external_lock_entity_state_change_listener.__get__(
            manager
        )

        # External lock unlocked: ON -> OFF
        old_state = State("input_boolean.external_lock", STATE_ON)
        new_state = State("input_boolean.external_lock", STATE_OFF)

        event_data = {
            "entity_id": "input_boolean.external_lock",
            "old_state": old_state,
            "new_state": new_state,
        }
        event = Event("state_changed", event_data)

        # Call listener
        await manager._async_external_lock_entity_state_change_listener(event)

        # Verify unlock time was set
        assert manager._last_unlock_time is not None

        # Verify it's recent
        elapsed = (datetime.now(UTC) - manager._last_unlock_time).total_seconds()
        assert elapsed < 1.0  # Should be very recent

    # ========================================================================
    # TEST 15: Timer läuft ab - Position-Check mit extremen Werten
    # ========================================================================

    async def test_timer_expired_extreme_position_difference(self, manager):
        """Test auto-lock with extreme position differences."""
        # Set positioning time 40 seconds ago
        manager._last_positioning_time = datetime.now(UTC) - timedelta(seconds=40)
        manager._last_calculated_height = 50.0
        manager._last_calculated_angle = 45.0

        # Extreme difference (user moved cover completely)
        manager._last_reported_height = 100.0  # 50% diff!
        manager._last_reported_angle = 0.0  # 45° diff!

        # Check positioning completed
        await manager._check_positioning_completed()

        # Auto-lock SHOULD be triggered
        manager._activate_auto_lock.assert_called_once_with(100.0, 0.0)

    # ========================================================================
    # TEST 16: Timer mit max_movement_duration = None (Fallback)
    # ========================================================================

    async def test_timer_with_none_max_movement_duration(self, manager):
        """Test timer uses default when max_movement_duration is None."""

        # Set max_movement_duration to None
        manager._facade_config.max_movement_duration = None

        # Set positioning time
        manager._last_positioning_time = datetime.now(UTC) - timedelta(seconds=10)

        # Timer should still work with default value
        assert manager._is_positioning_in_progress() is True

        # After default time (30s from SCDefaults), timer should expire
        manager._last_positioning_time = datetime.now(UTC) - timedelta(seconds=35)
        assert manager._is_positioning_in_progress() is False

    # ========================================================================
    # TEST 17: Positioning während Unlock Grace Period
    # ========================================================================

    async def test_positioning_during_unlock_grace_period(self, manager):
        """Test positioning can happen during unlock grace period."""
        # Set unlock time 5 seconds ago
        manager._last_unlock_time = datetime.now(UTC) - timedelta(seconds=5)

        # Unlock grace period is still active
        elapsed = (datetime.now(UTC) - manager._last_unlock_time).total_seconds()
        assert elapsed < manager._facade_config.max_movement_duration

        # New positioning starts
        manager._last_positioning_time = datetime.now(UTC)

        # Both grace periods are active
        assert manager._is_positioning_in_progress() is True
        assert manager._last_unlock_time is not None

    # Am Ende von tests/test_timer_integration.py hinzufügen:

    # ========================================================================
    # TEST 18: Cover State Change während Timer - Position wird gespeichert
    # ========================================================================

    async def test_cover_state_change_during_timer_stores_position(self, manager):
        """Test cover state changes during timer are stored."""

        # Timer is running
        manager._last_positioning_time = datetime.now(UTC) - timedelta(seconds=10)
        manager._last_calculated_height = 50.0
        manager._last_calculated_angle = 45.0

        # Bind real method
        manager._async_target_cover_entity_state_change_listener = ShadowControlManager._async_target_cover_entity_state_change_listener.__get__(
            manager
        )

        # Create cover state change event
        old_state = MagicMock()
        old_state.state = "open"
        old_state.attributes = {"current_position": 50, "current_tilt_position": 55}

        new_state = MagicMock()
        new_state.state = "open"
        new_state.attributes = {"current_position": 40, "current_tilt_position": 45}

        event_data = {
            "entity_id": "cover.test",
            "old_state": old_state,
            "new_state": new_state,
        }
        event = Event("state_changed", event_data)

        # Call listener
        await manager._async_target_cover_entity_state_change_listener(event)

        # Position should be stored (not checked yet, timer still running)
        # HA: 40, 45 → SC: 60, 55 (100 - X)
        assert manager._last_reported_height == 60.0
        assert manager._last_reported_angle == 55.0

        # No auto-lock triggered (timer running)
        manager._activate_auto_lock.assert_not_called()

    # ========================================================================
    # TEST 19: Cover State Change nach Timer - Auto-Lock Check
    # ========================================================================

    async def test_cover_state_change_after_timer_checks_autolock(self, manager):
        """Test cover state change after timer triggers auto-lock check."""

        # Timer has expired (40s ago, timer is 30s)
        manager._last_positioning_time = datetime.now(UTC) - timedelta(seconds=40)
        manager._last_calculated_height = 50.0
        manager._last_calculated_angle = 45.0

        # No reported position yet (check will happen on state change)
        manager._last_reported_height = None
        manager._last_reported_angle = None

        # Bind real method
        manager._async_target_cover_entity_state_change_listener = ShadowControlManager._async_target_cover_entity_state_change_listener.__get__(
            manager
        )

        # Create cover state change event with different position
        old_state = MagicMock()
        old_state.state = "open"
        old_state.attributes = {"current_position": 50, "current_tilt_position": 55}

        new_state = MagicMock()
        new_state.state = "open"
        # Position differs from target (manual movement!)
        new_state.attributes = {"current_position": 70, "current_tilt_position": 80}

        event_data = {
            "entity_id": "cover.test",
            "old_state": old_state,
            "new_state": new_state,
        }
        event = Event("state_changed", event_data)

        # Call listener
        await manager._async_target_cover_entity_state_change_listener(event)

        # Auto-lock should be triggered
        # HA: 70, 80 → SC: 30, 20
        manager._activate_auto_lock.assert_called_once_with(30.0, 20.0)

    # ========================================================================
    # TEST 20: Cover State Change - Bereits gesperrt
    # ========================================================================

    async def test_cover_state_change_already_locked(self, manager):
        """Test cover state change ignored when already locked."""
        # Integration is locked
        manager._dynamic_config.lock_integration = True

        # Bind real method
        manager._async_target_cover_entity_state_change_listener = ShadowControlManager._async_target_cover_entity_state_change_listener.__get__(
            manager
        )

        # Create cover state change event
        old_state = MagicMock()
        old_state.state = "open"
        old_state.attributes = {"current_position": 50, "current_tilt_position": 55}

        new_state = MagicMock()
        new_state.state = "open"
        new_state.attributes = {"current_position": 30, "current_tilt_position": 20}

        event_data = {
            "entity_id": "cover.test",
            "old_state": old_state,
            "new_state": new_state,
        }
        event = Event("state_changed", event_data)

        # Call listener
        await manager._async_target_cover_entity_state_change_listener(event)

        # No auto-lock triggered (already locked)
        manager._activate_auto_lock.assert_not_called()

        # No position stored
        assert manager._last_reported_height is None

    # ========================================================================
    # TEST 21: Cover State Change - Keine Position-Änderung
    # ========================================================================

    async def test_cover_state_change_no_position_change(self, manager):
        """Test cover state change ignored when position unchanged."""
        # Bind real method
        manager._async_target_cover_entity_state_change_listener = ShadowControlManager._async_target_cover_entity_state_change_listener.__get__(
            manager
        )

        # Create cover state change event - same position
        old_state = MagicMock()
        old_state.state = "open"
        old_state.attributes = {"current_position": 50, "current_tilt_position": 55}

        new_state = MagicMock()
        new_state.state = "open"
        new_state.attributes = {"current_position": 50, "current_tilt_position": 55}  # Same!

        event_data = {
            "entity_id": "cover.test",
            "old_state": old_state,
            "new_state": new_state,
        }
        event = Event("state_changed", event_data)

        # Call listener
        await manager._async_target_cover_entity_state_change_listener(event)

        # Nothing should happen (position unchanged)
        manager._activate_auto_lock.assert_not_called()
        assert manager._last_reported_height is None

    # ========================================================================
    # TEST 22: Cover State Change - Unlock Grace Period aktiv
    # ========================================================================

    async def test_cover_state_change_unlock_grace_period_active(self, manager):
        """Test cover state change ignored during unlock grace period."""
        # Set unlock time 5 seconds ago
        manager._last_unlock_time = datetime.now(UTC) - timedelta(seconds=5)

        # Bind real method
        manager._async_target_cover_entity_state_change_listener = ShadowControlManager._async_target_cover_entity_state_change_listener.__get__(
            manager
        )

        # Create cover state change event
        old_state = MagicMock()
        old_state.state = "open"
        old_state.attributes = {"current_position": 50, "current_tilt_position": 55}

        new_state = MagicMock()
        new_state.state = "open"
        new_state.attributes = {"current_position": 30, "current_tilt_position": 20}

        event_data = {
            "entity_id": "cover.test",
            "old_state": old_state,
            "new_state": new_state,
        }
        event = Event("state_changed", event_data)

        # Call listener
        await manager._async_target_cover_entity_state_change_listener(event)

        # No auto-lock (unlock grace period active)
        manager._activate_auto_lock.assert_not_called()

    # Am Ende von tests/test_timer_integration.py hinzufügen:

    # ========================================================================
    # TEST 23: Mode3 - Cover State Change speichert nur Höhe
    # ========================================================================

    async def test_mode3_cover_state_change_stores_only_height(self, manager):
        """Test Mode3 cover state change stores only height, no angle."""
        # Set to Mode3
        manager._facade_config.shutter_type = ShutterType.MODE3

        # Timer is running
        manager._last_positioning_time = datetime.now(UTC) - timedelta(seconds=10)
        manager._last_calculated_height = 50.0
        manager._last_calculated_angle = 0.0  # Mode3 has no angle

        # Bind real method
        manager._async_target_cover_entity_state_change_listener = ShadowControlManager._async_target_cover_entity_state_change_listener.__get__(
            manager
        )

        # Create cover state change event - Mode3 has no tilt
        old_state = MagicMock()
        old_state.state = "open"
        old_state.attributes = {"current_position": 50}  # No tilt!

        new_state = MagicMock()
        new_state.state = "open"
        new_state.attributes = {"current_position": 40}  # No tilt!

        event_data = {
            "entity_id": "cover.test",
            "old_state": old_state,
            "new_state": new_state,
        }
        event = Event("state_changed", event_data)

        # Call listener
        await manager._async_target_cover_entity_state_change_listener(event)

        # Position should be stored (only height)
        # HA: 40 → SC: 60
        assert manager._last_reported_height == 60.0
        assert manager._last_reported_angle == 0.0  # Mode3 sets to 0

        # No auto-lock triggered (timer running)
        manager._activate_auto_lock.assert_not_called()

    # ========================================================================
    # TEST 24: Mode3 - Nur Höhen-Änderung triggert Listener
    # ========================================================================

    async def test_mode3_only_height_change_triggers_listener(self, manager):
        """Test Mode3 only triggers on height change, not angle."""
        # Set to Mode3
        manager._facade_config.shutter_type = ShutterType.MODE3

        # No timer running
        manager._last_positioning_time = None
        manager._last_calculated_height = 50.0
        manager._last_calculated_angle = 0.0

        # Bind real method
        manager._async_target_cover_entity_state_change_listener = ShadowControlManager._async_target_cover_entity_state_change_listener.__get__(
            manager
        )

        # Create cover state change - same height (no change)
        old_state = MagicMock()
        old_state.state = "open"
        old_state.attributes = {"current_position": 50}

        new_state = MagicMock()
        new_state.state = "open"
        new_state.attributes = {"current_position": 50}  # Same!

        event_data = {
            "entity_id": "cover.test",
            "old_state": old_state,
            "new_state": new_state,
        }
        event = Event("state_changed", event_data)

        # Call listener
        await manager._async_target_cover_entity_state_change_listener(event)

        # Nothing should happen (no position change)
        manager._activate_auto_lock.assert_not_called()

    # ========================================================================
    # TEST 25: Kompletter Dawn-Sequenz Flow
    # ========================================================================

    async def test_complete_dawn_sequence_flow(self, manager):
        """Test complete dawn sequence: Lookthrough → Wait → Open."""
        # Step 1: First positioning to lookthrough
        first_time = datetime.now(UTC)
        manager._last_positioning_time = first_time
        manager._last_calculated_height = 30.0  # Lookthrough height
        manager._last_calculated_angle = 50.0  # Lookthrough angle

        # Bind real method
        manager._async_target_cover_entity_state_change_listener = ShadowControlManager._async_target_cover_entity_state_change_listener.__get__(
            manager
        )

        # Step 2: Cover moves to lookthrough, reports positions during movement
        old_state = MagicMock()
        old_state.state = "closed"
        old_state.attributes = {"current_position": 0, "current_tilt_position": 0}

        new_state = MagicMock()
        new_state.state = "open"
        new_state.attributes = {"current_position": 65, "current_tilt_position": 45}  # Moving

        event_data = {
            "entity_id": "cover.test",
            "old_state": old_state,
            "new_state": new_state,
        }
        event = Event("state_changed", event_data)

        await manager._async_target_cover_entity_state_change_listener(event)

        # Position stored, no auto-lock (timer running)
        assert manager._last_reported_height == 35.0  # 100 - 65
        assert manager._last_reported_angle == 55.0  # 100 - 45
        manager._activate_auto_lock.assert_not_called()

        # Step 3: Cover reaches lookthrough position
        new_state.attributes = {"current_position": 70, "current_tilt_position": 50}
        event = Event("state_changed", event_data)

        await manager._async_target_cover_entity_state_change_listener(event)

        # Position updated
        assert manager._last_reported_height == 30.0  # 100 - 70
        assert manager._last_reported_angle == 50.0  # 100 - 50

        # Step 4: New positioning command (open) BEFORE timer expires
        second_time = first_time + timedelta(seconds=10)
        manager._last_positioning_time = second_time
        manager._last_calculated_height = 0.0  # Fully open
        manager._last_calculated_angle = 0.0
        manager._last_reported_height = None  # Reset for new positioning
        manager._last_reported_angle = None

        # Step 5: Cover moves to open position
        new_state.attributes = {"current_position": 85, "current_tilt_position": 25}  # Moving
        event = Event("state_changed", event_data)

        # Need to mock datetime for positioning check
        with patch("custom_components.shadow_control.datetime") as mock_dt:
            mock_dt.now.return_value = second_time + timedelta(seconds=2)

            await manager._async_target_cover_entity_state_change_listener(event)

        # Position stored for new movement
        assert manager._last_reported_height == 15.0  # 100 - 85
        assert manager._last_reported_angle == 75.0  # 100 - 25

        # Still no auto-lock (second timer running)
        manager._activate_auto_lock.assert_not_called()

        # Step 6: Cover reaches final open position
        new_state.attributes = {"current_position": 100, "current_tilt_position": 0}
        event = Event("state_changed", event_data)

        with patch("custom_components.shadow_control.datetime") as mock_dt:
            mock_dt.now.return_value = second_time + timedelta(seconds=5)

            await manager._async_target_cover_entity_state_change_listener(event)

        # Final position stored
        assert manager._last_reported_height == 0.0  # 100 - 100
        assert manager._last_reported_angle == 100.0  # 100 - 0

        # Wait for timer to expire
        manager._last_positioning_time = datetime.now(UTC) - timedelta(seconds=40)

        # Check positioning completed
        await manager._check_positioning_completed()

        # No auto-lock (position matches or is close enough)
        # This tests the complete flow without triggering auto-lock
