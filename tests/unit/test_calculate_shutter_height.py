"""Test the shutter height calculation math."""

from unittest.mock import MagicMock

import pytest

from custom_components.shadow_control import ShadowControlManager


@pytest.fixture
def manager(mock_manager):
    """Bind the real calculation and setup mocks."""
    manager = mock_manager
    manager._calculate_shutter_height = ShadowControlManager._calculate_shutter_height.__get__(manager)

    # We must mock the stepping helper since it's called at the end
    manager._handle_shutter_height_stepping = MagicMock(side_iter=lambda x: x)
    manager._handle_shutter_height_stepping.side_effect = lambda x: x

    # Default Config
    manager._facade_config.light_strip_width = 100.0  # 100cm light strip
    manager._facade_config.shutter_height = 200.0  # 200cm total window height
    manager._shadow_config.shutter_max_height = 80.0  # Don't go below 80% (top down)
    manager._dynamic_config.sun_elevation = 45.0  # 45 degrees

    return manager


@pytest.mark.asyncio
class TestCalculateShutterHeight:
    """Test suite for shutter height trigonometry."""

    async def test_standard_math_calculation(self, manager):
        """
        Elevation 45°, Light strip 100cm.
        tan(45) = 1.0.
        shutter_height_from_bottom = 100 * 1.0 = 100cm.
        Percentage: 100 - (100 * 100 / 200) = 50%.
        """
        manager._dynamic_config.sun_elevation = 45.0

        result = manager._calculate_shutter_height()

        assert result == 50.0

    async def test_max_height_constraint(self, manager):
        """
        If sun is very low (e.g. 10°), shutter would want to go very low.
        Check if it stops at shadow_max_height_percent.
        """
        manager._dynamic_config.sun_elevation = 10.0
        # tan(10) * 100 approx 17.6cm from bottom.
        # Height percent would be 100 - (17.6*100/200) = 91%
        # But our max height is 80%.

        result = manager._calculate_shutter_height()

        assert result == 80.0  # Uses the max_height default

    async def test_light_strip_zero(self, manager):
        """If light strip width is 0, it should just return max height."""
        manager._facade_config.light_strip_width = 0

        result = manager._calculate_shutter_height()

        assert result == 80.0

    async def test_missing_config_fallback(self, manager):
        """Test fallback when elevation is None."""
        manager._dynamic_config.sun_elevation = None

        result = manager._calculate_shutter_height()

        assert result == 80.0  # Returns the shadow_max_height_percent
        manager.logger.warning.assert_called()

    async def test_rounding_behavior(self, manager):
        """Ensure the rounding logic handles floating points correctly."""
        # Setup values that result in .5
        manager._facade_config.light_strip_width = 50.0
        manager._dynamic_config.sun_elevation = 45.0  # tan=1.0 -> 50cm
        manager._facade_config.shutter_height = 200.0
        # 100 - round(50 * 100 / 200) = 100 - 25 = 75

        result = manager._calculate_shutter_height()
        assert result == 75.0
