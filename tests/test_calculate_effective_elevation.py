"""Test the effective elevation (profile angle) calculation."""

import pytest

from custom_components.shadow_control import ShadowControlManager


@pytest.fixture
def manager(mock_manager):
    """Bind the real calculation to the mock manager."""
    manager = mock_manager
    manager._calculate_effective_elevation = ShadowControlManager._calculate_effective_elevation.__get__(manager)

    # Setup standard config
    manager._facade_config.azimuth = 180  # South
    return manager


@pytest.mark.asyncio
class TestCalculateEffectiveElevation:
    """Test suite for solar trigonometry."""

    async def test_sun_dead_center(self, manager):
        """Sun at 180°, Facade at 180°. Effective elevation should equal real elevation."""
        manager._dynamic_config.sun_azimuth = 180
        manager._dynamic_config.sun_elevation = 30.0

        result = await manager._calculate_effective_elevation()

        # When sun is dead center, cos(0) = 1. atan(tan(30)/1) = 30
        assert result == pytest.approx(30.0)

    async def test_sun_at_angle(self, manager):
        """Sun at 210° (30° off-center), elevation 45°."""
        manager._dynamic_config.sun_azimuth = 210  # 30 deg difference
        manager._dynamic_config.sun_elevation = 45.0

        result = await manager._calculate_effective_elevation()

        # virtual_depth = cos(30) ≈ 0.866
        # virtual_height = tan(45) = 1.0
        # atan(1.0 / 0.866) ≈ 49.1°
        assert result == pytest.approx(49.1, abs=0.1)

    async def test_division_by_zero_protection(self, manager):
        """Sun exactly 90° to the side of the facade."""
        manager._dynamic_config.sun_azimuth = 270  # 90 deg difference
        manager._dynamic_config.sun_elevation = 10.0

        result = await manager._calculate_effective_elevation()

        # cos(90) is 0. Your code catches < 1e-9 and returns 90.0
        assert result == 90.0

    async def test_sun_behind_facade(self, manager):
        """Sun at 0°, Facade at 180°. (Negative virtual depth)."""
        manager._dynamic_config.sun_azimuth = 0
        manager._dynamic_config.sun_elevation = 20.0

        result = await manager._calculate_effective_elevation()

        # cos(180) = -1. atan(tan(20)/-1) = -20
        assert result == pytest.approx(-20.0)

    async def test_missing_data_returns_none(self, manager):
        """Verify None is returned if values are missing."""
        manager._dynamic_config.sun_azimuth = None
        result = await manager._calculate_effective_elevation()
        assert result is None
