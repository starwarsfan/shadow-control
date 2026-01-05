"""Tests for manual movement detection and auto-lock."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import Event

from custom_components.shadow_control import ShadowControlManager
from custom_components.shadow_control.const import ShutterType


class TestManualMovementDetection:
    """Test manual movement detection and auto-lock feature."""

    @pytest.fixture
    def manager(self):
        """Create a mock ShadowControlManager instance."""
        instance = MagicMock(spec=ShadowControlManager)
        instance.logger = MagicMock()
        instance.hass = MagicMock()
        instance._config = MagicMock()
        instance._dynamic_config = MagicMock()
        instance._facade_config = MagicMock()

        # Default: No locks active
        instance._dynamic_config.lock_integration = False
        instance._dynamic_config.lock_integration_with_position = False

        # Default: Mode1 (Raffstore with tilt)
        instance._facade_config.shutter_type = ShutterType.MODE1
        instance._facade_config.modification_tolerance_height = 2.0
        instance._facade_config.modification_tolerance_angle = 2.0
        instance._facade_config.max_movement_duration = 30.0

        # Tracking variables
        instance._last_positioning_time = None
        instance._last_calculated_height = 80.0
        instance._last_calculated_angle = 45.0
        instance._last_unlock_time = None
        instance._last_reported_height = None
        instance._last_reported_angle = None

        # Mock methods
        instance.get_internal_entity_id = MagicMock(return_value="switch.test_lock")
        instance._activate_auto_lock = AsyncMock()
        instance._check_positioning_completed = AsyncMock()

        # Bind real methods
        instance._is_positioning_in_progress = ShadowControlManager._is_positioning_in_progress.__get__(instance)
        instance._async_target_cover_entity_state_change_listener = ShadowControlManager._async_target_cover_entity_state_change_listener.__get__(
            instance
        )

        return instance

    # ========================================================================
    # TEST: Position in progress
    # ===================================================================

    def test_is_positioning_in_progress_no_positioning_yet(self, manager):
        """Test positioning check returns False when no positioning occurred yet."""
        manager._last_positioning_time = None

        result = manager._is_positioning_in_progress()  # ← Kein await mehr!

        assert result is False

    def test_is_positioning_in_progress_yes(self, manager):
        """Test positioning check returns True when within timer duration."""
        # Positioning happened 10 seconds ago, timer is 30 seconds
        manager._last_positioning_time = datetime.now(UTC) - timedelta(seconds=10)
        manager._facade_config.max_movement_duration = 30.0

        result = manager._is_positioning_in_progress()  # ← Kein await mehr!

        assert result is True

    def test_is_positioning_in_progress_no(self, manager):
        """Test positioning check returns False when timer expired."""
        # Positioning happened 40 seconds ago, timer is 30 seconds
        manager._last_positioning_time = datetime.now(UTC) - timedelta(seconds=40)
        manager._facade_config.max_movement_duration = 30.0

        result = manager._is_positioning_in_progress()  # ← Kein await mehr!

        assert result is False

    # ========================================================================
    # TEST: Manual Movement Detection - Mode1/2 (with tilt)
    # ========================================================================

    async def test_manual_movement_triggers_auto_lock(self, manager):
        """Test that manual movement triggers auto-lock."""
        # Create state change event with significant position change
        old_state = MagicMock()
        old_state.state = "open"
        old_state.attributes = {"current_position": 80, "current_tilt_position": 45}

        new_state = MagicMock()
        new_state.state = "open"
        new_state.attributes = {"current_position": 50, "current_tilt_position": 20}

        event = Event(
            "state_changed",
            {
                "entity_id": "cover.test",
                "old_state": old_state,
                "new_state": new_state,
            },
        )

        # Call listener
        await manager._async_target_cover_entity_state_change_listener(event)

        # Verify auto-lock was called
        manager._activate_auto_lock.assert_called_once_with(50.0, 80.0)

    async def test_no_auto_lock_within_grace_period(self, manager):
        """Test that no auto-lock is triggered when positioning timer is active."""
        # Set last positioning to 5 seconds ago (timer: 30s)
        manager._last_positioning_time = datetime.now(UTC) - timedelta(seconds=5)
        manager._last_calculated_height = 80.0
        manager._last_calculated_angle = 45.0

        old_state = MagicMock()
        old_state.state = "open"
        old_state.attributes = {"current_position": 80, "current_tilt_position": 45}

        new_state = MagicMock()
        new_state.state = "open"
        new_state.attributes = {"current_position": 50, "current_tilt_position": 20}  # Große Änderung

        event = Event(
            "state_changed",
            {
                "entity_id": "cover.test",
                "old_state": old_state,
                "new_state": new_state,
            },
        )

        await manager._async_target_cover_entity_state_change_listener(event)

        # ✅ GEÄNDERT: Position sollte gespeichert worden sein
        assert manager._last_reported_height == 50.0  # 100 - 50
        assert manager._last_reported_angle == 80.0  # 100 - 20

        # Verify auto-lock was NOT called (timer still running)
        manager._activate_auto_lock.assert_not_called()

    async def test_no_auto_lock_when_already_locked(self, manager):
        """Test that no auto-lock is triggered when already locked."""
        manager._dynamic_config.lock_integration = True

        old_state = MagicMock()
        old_state.state = "open"
        old_state.attributes = {"current_position": 80, "current_tilt_position": 45}

        new_state = MagicMock()
        new_state.state = "open"
        new_state.attributes = {"current_position": 50, "current_tilt_position": 20}

        event = Event(
            "state_changed",
            {
                "entity_id": "cover.test",
                "old_state": old_state,
                "new_state": new_state,
            },
        )

        await manager._async_target_cover_entity_state_change_listener(event)

        # Verify auto-lock was NOT called
        manager._activate_auto_lock.assert_not_called()

    async def test_no_auto_lock_within_tolerance(self, manager):
        """Test that small changes within tolerance don't trigger auto-lock."""
        # Change is only 1% height and 1° angle (within 2.0 tolerance)
        old_state = MagicMock()
        old_state.state = "open"
        old_state.attributes = {"current_position": 80, "current_tilt_position": 45}

        new_state = MagicMock()
        new_state.state = "open"
        new_state.attributes = {"current_position": 19, "current_tilt_position": 54}

        event = Event(
            "state_changed",
            {
                "entity_id": "cover.test",
                "old_state": old_state,
                "new_state": new_state,
            },
        )

        await manager._async_target_cover_entity_state_change_listener(event)

        # Verify auto-lock was NOT called
        manager._activate_auto_lock.assert_not_called()

    async def test_no_auto_lock_when_position_unchanged(self, manager):
        """Test that no auto-lock when position didn't change."""
        # Same position, only state changed (e.g. "opening" -> "open")
        old_state = MagicMock()
        old_state.state = "opening"
        old_state.attributes = {"current_position": 80, "current_tilt_position": 45}

        new_state = MagicMock()
        new_state.state = "open"
        new_state.attributes = {"current_position": 80, "current_tilt_position": 45}

        event = Event(
            "state_changed",
            {
                "entity_id": "cover.test",
                "old_state": old_state,
                "new_state": new_state,
            },
        )

        await manager._async_target_cover_entity_state_change_listener(event)

        # Verify auto-lock was NOT called
        manager._activate_auto_lock.assert_not_called()

    # ========================================================================
    # TEST: Mode3 (Jalousie/Rollo - no tilt)
    # ========================================================================

    async def test_mode3_manual_movement_only_height(self, manager):
        """Test Mode3 (no tilt) triggers auto-lock on height change only."""
        manager._facade_config.shutter_type = ShutterType.MODE3
        manager._last_calculated_height = 80.0

        old_state = MagicMock()
        old_state.state = "open"
        old_state.attributes = {"current_position": 80}  # No tilt

        new_state = MagicMock()
        new_state.state = "open"
        new_state.attributes = {"current_position": 50}  # No tilt

        event = Event(
            "state_changed",
            {
                "entity_id": "cover.test",
                "old_state": old_state,
                "new_state": new_state,
            },
        )

        await manager._async_target_cover_entity_state_change_listener(event)

        # Verify auto-lock was called (only with height, angle=0)
        manager._activate_auto_lock.assert_called_once_with(50.0, 0.0)

    async def test_mode3_ignores_tilt_changes(self, manager):
        """Test Mode3 ignores tilt changes (shouldn't happen, but just in case)."""
        manager._facade_config.shutter_type = ShutterType.MODE3

        # Height unchanged, only tilt changed (which shouldn't exist for Mode3)
        old_state = MagicMock()
        old_state.state = "open"
        old_state.attributes = {"current_position": 80, "current_tilt_position": 45}

        new_state = MagicMock()
        new_state.state = "open"
        new_state.attributes = {"current_position": 80, "current_tilt_position": 20}

        event = Event(
            "state_changed",
            {
                "entity_id": "cover.test",
                "old_state": old_state,
                "new_state": new_state,
            },
        )

        await manager._async_target_cover_entity_state_change_listener(event)

        # Verify auto-lock was NOT called (tilt change ignored in Mode3)
        manager._activate_auto_lock.assert_not_called()
