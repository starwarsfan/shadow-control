"""Test the _get_effective_shadow_brightness_threshold helper (low-sun-elevation override, see #79)."""

from unittest.mock import MagicMock

import pytest

from custom_components.shadow_control import ShadowControlManager


@pytest.fixture
def manager():
    """Create a mock ShadowControlManager instance with the real helper bound."""
    instance = MagicMock(spec=ShadowControlManager)
    instance._shadow_config = MagicMock()
    instance._get_effective_shadow_brightness_threshold = ShadowControlManager._get_effective_shadow_brightness_threshold.__get__(instance)
    return instance


class TestGetEffectiveShadowBrightnessThreshold:
    """Test suite for the low-sun-elevation brightness threshold override."""

    def test_disabled_by_default_returns_plain_threshold(self, manager):
        """Default threshold (0°) never triggers under normal (elevation > 0) conditions."""
        manager.brightness_threshold = 20000
        manager._shadow_config.low_sun_elevation_threshold = 0.0
        manager._shadow_config.low_sun_brightness_threshold = 3500
        manager._effective_elevation = 5.0  # low, but not below the (disabled) threshold

        assert manager._get_effective_shadow_brightness_threshold() == 20000

    def test_below_low_sun_elevation_returns_low_sun_threshold(self, manager):
        """Once effective elevation drops below the configured threshold, use the low value."""
        manager.brightness_threshold = 20000
        manager._shadow_config.low_sun_elevation_threshold = 20.0
        manager._shadow_config.low_sun_brightness_threshold = 3500
        manager._effective_elevation = 10.0

        assert manager._get_effective_shadow_brightness_threshold() == 3500

    def test_at_low_sun_elevation_boundary_uses_plain_threshold(self, manager):
        """Exactly at the threshold (not below it), the normal threshold still applies."""
        manager.brightness_threshold = 20000
        manager._shadow_config.low_sun_elevation_threshold = 20.0
        manager._shadow_config.low_sun_brightness_threshold = 3500
        manager._effective_elevation = 20.0

        assert manager._get_effective_shadow_brightness_threshold() == 20000

    def test_above_low_sun_elevation_returns_plain_threshold(self, manager):
        """Well above the low-sun elevation threshold, regular daytime handling applies."""
        manager.brightness_threshold = 20000
        manager._shadow_config.low_sun_elevation_threshold = 20.0
        manager._shadow_config.low_sun_brightness_threshold = 3500
        manager._effective_elevation = 45.0

        assert manager._get_effective_shadow_brightness_threshold() == 20000

    def test_none_effective_elevation_returns_plain_threshold(self, manager):
        """If the facade is not currently in sun (no effective elevation), never override."""
        manager.brightness_threshold = 20000
        manager._shadow_config.low_sun_elevation_threshold = 20.0
        manager._shadow_config.low_sun_brightness_threshold = 3500
        manager._effective_elevation = None

        assert manager._get_effective_shadow_brightness_threshold() == 20000

    def test_none_low_sun_elevation_threshold_returns_plain_threshold(self, manager):
        """Defensive: a missing/None configured threshold must not crash or override."""
        manager.brightness_threshold = 20000
        manager._shadow_config.low_sun_elevation_threshold = None
        manager._shadow_config.low_sun_brightness_threshold = 3500
        manager._effective_elevation = 10.0

        assert manager._get_effective_shadow_brightness_threshold() == 20000
