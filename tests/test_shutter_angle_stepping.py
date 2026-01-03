"""Test the shutter angle stepping (quantization) logic."""

import pytest

from custom_components.shadow_control import ShadowControlManager


@pytest.fixture
def manager(mock_manager):
    """Bind the real stepping method to the mock manager."""
    manager = mock_manager
    manager._handle_shutter_angle_stepping = ShadowControlManager._handle_shutter_angle_stepping.__get__(manager)

    # Default config
    manager._facade_config.shutter_stepping_angle = 5.0  # 5% steps

    return manager


@pytest.mark.asyncio
class TestHandleShutterAngleStepping:
    """Test suite for motor-wear protection logic."""

    async def test_angle_snaps_up_to_next_step(self, manager):
        """12% with a 5% step should snap up to 15%."""
        result = manager._handle_shutter_angle_stepping(12.0)
        assert result == 15.0

    async def test_angle_already_aligned_stays_same(self, manager):
        """20% with a 5% step should stay 20%."""
        result = manager._handle_shutter_angle_stepping(20.0)
        assert result == 20.0

    async def test_zero_stepping_disables_logic(self, manager):
        """If stepping is 0, return the input exactly."""
        manager._facade_config.shutter_stepping_angle = 0.0
        result = manager._handle_shutter_angle_stepping(12.7)
        assert result == 12.7

    async def test_none_config_warning_and_fallback(self, manager):
        """Handle missing configuration gracefully."""
        manager._facade_config.shutter_stepping_angle = None
        result = manager._handle_shutter_angle_stepping(42.0)

        assert result == 42.0
        manager.logger.warning.assert_called_once()

    async def test_floating_point_stepping(self, manager):
        """Verify it handles non-integer steps (e.g., 2.5%)."""
        manager._facade_config.shutter_stepping_angle = 2.5
        # 6.0 % 2.5 = 1.0. Adjusted: 6.0 + 2.5 - 1.0 = 7.5
        result = manager._handle_shutter_angle_stepping(6.0)
        assert result == 7.5
