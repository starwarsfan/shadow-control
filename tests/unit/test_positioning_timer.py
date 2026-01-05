"""Tests for positioning timer and completion check."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.shadow_control import ShadowControlManager
from custom_components.shadow_control.const import ShutterType


class TestPositioningTimer:
    """Test positioning timer functionality."""

    @pytest.fixture
    def manager(self):
        """Create a mock ShadowControlManager instance."""
        instance = MagicMock(spec=ShadowControlManager)
        instance.logger = MagicMock()
        instance._facade_config = MagicMock()
        instance._facade_config.shutter_type = ShutterType.MODE1
        instance._facade_config.modification_tolerance_height = 2.0
        instance._facade_config.modification_tolerance_angle = 2.0
        instance._facade_config.max_movement_duration = 30.0

        # Tracking
        instance._last_positioning_time = None
        instance._last_calculated_height = 80.0
        instance._last_calculated_angle = 45.0
        instance._last_reported_height = None
        instance._last_reported_angle = None

        # Mock methods
        instance._activate_auto_lock = AsyncMock()

        # Bind real methods
        instance._is_positioning_in_progress = ShadowControlManager._is_positioning_in_progress.__get__(instance)
        instance._check_positioning_completed = ShadowControlManager._check_positioning_completed.__get__(instance)

        return instance

    # ========================================================================
    # TEST: Timer still running
    # ========================================================================

    async def test_check_positioning_timer_still_running(self, manager):
        """Test that check does nothing when timer still running."""
        manager._last_positioning_time = datetime.now(UTC) - timedelta(seconds=10)
        manager._last_reported_height = 78.0
        manager._last_reported_angle = 43.0

        await manager._check_positioning_completed()

        # Timer still running, no action
        manager._activate_auto_lock.assert_not_called()
        # Values should NOT be reset
        assert manager._last_reported_height == 78.0

    # ========================================================================
    # TEST: Timer expired, position matches
    # ========================================================================

    async def test_check_positioning_timer_expired_position_matches(self, manager):
        """Test that no auto-lock when position matches after timer."""
        manager._last_positioning_time = datetime.now(UTC) - timedelta(seconds=40)
        manager._last_reported_height = 80.0  # Matches target
        manager._last_reported_angle = 45.0  # Matches target

        await manager._check_positioning_completed()

        # Position matches, no auto-lock
        manager._activate_auto_lock.assert_not_called()

        # Timer and reported values should be reset
        assert manager._last_positioning_time is None
        assert manager._last_reported_height is None

    # ========================================================================
    # TEST: Timer expired, position differs -> Auto-lock
    # ========================================================================

    async def test_check_positioning_timer_expired_position_differs(self, manager):
        """Test that auto-lock when position differs after timer."""
        manager._last_positioning_time = datetime.now(UTC) - timedelta(seconds=40)
        manager._last_reported_height = 50.0  # Differs from target (80.0)
        manager._last_reported_angle = 30.0  # Differs from target (45.0)

        await manager._check_positioning_completed()

        # Position differs -> auto-lock!
        manager._activate_auto_lock.assert_called_once_with(50.0, 30.0)

        # Timer and reported values should be reset
        assert manager._last_positioning_time is None
        assert manager._last_reported_height is None

    # ========================================================================
    # TEST: No positioning occurred
    # ========================================================================

    async def test_check_positioning_no_positioning(self, manager):
        """Test that check does nothing when no positioning occurred."""
        manager._last_positioning_time = None

        await manager._check_positioning_completed()

        # Nothing to check
        manager._activate_auto_lock.assert_not_called()

    # ========================================================================
    # TEST: Mode3 (no tilt)
    # ========================================================================

    async def test_check_positioning_mode3_only_height(self, manager):
        """Test Mode3 only checks height, not angle."""
        manager._facade_config.shutter_type = ShutterType.MODE3
        manager._last_positioning_time = datetime.now(UTC) - timedelta(seconds=40)
        manager._last_reported_height = 80.0  # Matches
        manager._last_reported_angle = None  # No angle in Mode3

        await manager._check_positioning_completed()

        # Height matches, no auto-lock
        manager._activate_auto_lock.assert_not_called()
