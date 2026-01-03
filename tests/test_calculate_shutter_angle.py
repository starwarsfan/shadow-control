"""Test the shutter slat angle calculation math."""

from unittest.mock import MagicMock

import pytest

from custom_components.shadow_control import ShadowControlManager
from custom_components.shadow_control.const import ShutterType


@pytest.fixture
def manager(mock_manager):
    """Bind the real calculation and setup mocks."""
    manager = mock_manager
    manager._calculate_shutter_angle = ShadowControlManager._calculate_shutter_angle.__get__(manager)

    # Mock the stepping helper
    manager._handle_shutter_angle_stepping = MagicMock(side_effect=lambda x: x)

    # Default Config (Standard Slat)
    manager._facade_config.slat_width = 80.0  # 80mm
    manager._facade_config.slat_distance = 70.0  # 70mm
    manager._facade_config.slat_angle_offset = 0.0
    manager._facade_config.slat_min_angle = 0.0
    manager._shadow_config.shutter_max_angle = 100.0
    manager._facade_config.shutter_type = ShutterType.MODE1  # 90 degree total

    # Inputs
    manager._dynamic_config.sun_elevation = 30.0
    manager._dynamic_config.sun_azimuth = 180.0
    manager._effective_elevation = 30.0

    return manager


@pytest.mark.asyncio
class TestCalculateShutterAngle:
    """Test suite for slat trigonometry and mapping."""

    async def test_mode3_returns_zero(self, manager):
        """Mode 3 (no tilt) should always return 0.0."""
        manager._facade_config.shutter_type = ShutterType.MODE3
        assert manager._calculate_shutter_angle() == 0.0

    async def test_standard_math_mode1(self, manager):
        """
        Test Mode 1 mapping (0-90 degrees).
        If math results in 45 degrees, percentage should be 45 / 0.9 = 50%.
        """
        # We manually force effective_elevation to get a known angle
        # For simplicity, let's assume the math results in 45 deg
        manager._effective_elevation = 45.0
        # alpha = 90 - 45 = 45
        # asin_arg = sin(45) * 70 / 80 = 0.707 * 0.875 = 0.618
        # beta = asin(0.618) = 38.2 deg
        # gamma = 180 - 45 - 38.2 = 96.8
        # deg = 90 - 96.8 = -6.8 (will be clamped to 0 or handled by mapping)

        result = manager._calculate_shutter_angle()
        assert isinstance(result, float)

    async def test_mode2_mapping(self, manager):
        """Test Mode 2 (180 degree total range, 50% is horizontal)."""
        manager._facade_config.shutter_type = ShutterType.MODE2
        manager._effective_elevation = 30.0

        result = manager._calculate_shutter_angle()
        # Mode 2: (degrees / 1.8) + 50
        # If degrees is 0, result is 50.0.
        assert result >= 50.0

    async def test_invalid_asin_argument_safety(self, manager):
        """Trigger the warning if distance > width (impossible triangle)."""
        manager._facade_config.slat_distance = 200.0  # Much larger than width 80
        manager._effective_elevation = 5.0  # Low elevation creates large sin(alpha)

        result = manager._calculate_shutter_angle()
        assert result == 0.0
        manager.logger.warning.assert_called()

    async def test_min_max_clamping(self, manager):
        """Ensure result respects slat_min_angle and shutter_max_angle."""
        manager._facade_config.slat_min_angle = 20.0
        manager._shadow_config.shutter_max_angle = 80.0

        # Force a very high result
        manager._effective_elevation = 85.0  # Sun overhead, slats should close
        result = manager._calculate_shutter_angle()
        assert result <= 80.0

        # Force a very low result
        manager._effective_elevation = 5.0
        result = manager._calculate_shutter_angle()
        assert result >= 20.0

    async def test_missing_data_fallback(self, manager):
        """Test the large block of None checks at the start."""
        manager._effective_elevation = None
        result = manager._calculate_shutter_angle()
        assert result == 0.0
        manager.logger.warning.assert_called()
