"""Test the facade sun illumination calculation."""

from unittest.mock import AsyncMock

import pytest

from custom_components.shadow_control import ShadowControlManager


@pytest.fixture
def manager(mock_manager):
    """Bind the real calculation to the mock manager."""
    manager = mock_manager
    manager._check_if_facade_is_in_sun = ShadowControlManager._check_if_facade_is_in_sun.__get__(manager)

    # Mock the helper for effective elevation
    manager._calculate_effective_elevation = AsyncMock(return_value=25.0)

    # Default Config: South-facing (180°) facade with 90° spread
    manager._facade_config.azimuth = 180
    manager._facade_config.offset_sun_in = 45  # Entry at 135°
    manager._facade_config.offset_sun_out = 45  # Exit at 225°
    manager._facade_config.elevation_sun_min = 10
    manager._facade_config.elevation_sun_max = 50

    # Default Dynamic state
    manager._dynamic_config.sun_azimuth = 180
    manager._dynamic_config.sun_elevation = 30

    return manager


@pytest.mark.asyncio
class TestCheckIfFacadeIsInSun:
    """Test suite for sun azimuth and elevation logic."""

    async def test_sun_directly_in_front(self, manager):
        """Sun is at 180° and facade is 180°. Should be True."""
        result = await manager._check_if_facade_is_in_sun()
        assert result is True
        assert manager._effective_elevation == 25.0

    async def test_sun_outside_azimuth_window(self, manager):
        """Sun is at 90° (East), facade is 180° (South). Should be False."""
        manager._dynamic_config.sun_azimuth = 90
        result = await manager._check_if_facade_is_in_sun()
        assert result is False

    async def test_elevation_too_low(self, manager):
        """Sun is in azimuth window, but effective elevation is below min."""
        manager._calculate_effective_elevation.return_value = 5.0
        result = await manager._check_if_facade_is_in_sun()
        assert result is False

    async def test_north_wrap_around(self, manager):
        """Test a North-facing facade (0°) with sun crossing the 360/0 boundary."""
        manager._facade_config.azimuth = 0
        manager._facade_config.offset_sun_in = 20  # Entry: 340°
        manager._facade_config.offset_sun_out = 20  # Exit: 20°

        # Sun at 350° (Should be IN)
        manager._dynamic_config.sun_azimuth = 350
        assert await manager._check_if_facade_is_in_sun() is True

        # Sun at 10° (Should be IN)
        manager._dynamic_config.sun_azimuth = 10
        assert await manager._check_if_facade_is_in_sun() is True

        # Sun at 30° (Should be OUT)
        manager._dynamic_config.sun_azimuth = 30
        assert await manager._check_if_facade_is_in_sun() is False

    async def test_missing_values_returns_false(self, manager):
        """Ensure it handles None values gracefully."""
        manager._dynamic_config.sun_azimuth = None
        result = await manager._check_if_facade_is_in_sun()
        assert result is False
        assert manager._effective_elevation is None

    async def test_sun_exit_angle_modulo_wrap(self, manager):
        """Test the logic when sun_exit_angle exceeds 360 degrees."""
        # Facade at 350° + 20° offset = 370° -> should become 10°
        manager._facade_config.azimuth = 350
        manager._facade_config.offset_sun_in = 10
        manager._facade_config.offset_sun_out = 20

        # We set sun to 5° (Which is between 340° and 10°)
        manager._dynamic_config.sun_azimuth = 5

        result = await manager._check_if_facade_is_in_sun()

        assert result is True
        # If the modulo works, internal sun_exit_angle became 10.0
        # We can verify the logic correctly identified 5 is within [340, 10]
