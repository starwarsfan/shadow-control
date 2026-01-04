"""Tests for travelling_time configuration check."""

from unittest.mock import MagicMock

import pytest
from homeassistant.core import HomeAssistant, State
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.shadow_control import ShadowControlManager
from custom_components.shadow_control.const import (
    DOMAIN,
    SC_CONF_NAME,
    TARGET_COVER_ENTITY,
    SCFacadeConfig2,
)


class TestTravellingTimeCheck:
    """Test travelling_time configuration check."""

    @pytest.fixture
    def mock_hass(self):
        """Create a mock Home Assistant instance."""
        hass = MagicMock(spec=HomeAssistant)
        hass.states = MagicMock()
        return hass

    @pytest.fixture
    def mock_config_entry(self):
        """Create a mock config entry."""
        return MockConfigEntry(
            domain=DOMAIN,
            entry_id="test_entry",
            data={
                SC_CONF_NAME: "Test Instance",
                SCFacadeConfig2.SHUTTER_TYPE_STATIC.value: "mode1",
            },
            options={
                TARGET_COVER_ENTITY: ["cover.test"],
                SCFacadeConfig2.MAX_MOVEMENT_DURATION_STATIC.value: 35,
            },
        )

    @pytest.fixture
    def manager(self, mock_hass, mock_config_entry):
        """Create a ShadowControlManager instance."""
        manager = MagicMock(spec=ShadowControlManager)
        manager.hass = mock_hass
        manager.logger = MagicMock()
        manager._target_cover_entity_id = ["cover.test"]

        # Mock facade config
        manager._facade_config = MagicMock()
        manager._facade_config.max_movement_duration = 35

        # Bind real method
        manager._check_travelling_time_configuration = ShadowControlManager._check_travelling_time_configuration.__get__(manager)

        return manager

    def create_cover_state(self, travelling_down=None, travelling_up=None):
        """Create a mock cover state with travelling_time attributes."""
        state = MagicMock(spec=State)
        state.attributes = {}

        if travelling_down is not None:
            state.attributes["travelling_time_down"] = travelling_down
        if travelling_up is not None:
            state.attributes["travelling_time_up"] = travelling_up

        return state

    # ========================================================================
    # TEST 1: No max_movement_duration configured → No check
    # ========================================================================

    def test_no_max_duration_configured(self, manager):
        """Test that check is skipped when max_duration is not configured."""
        manager._facade_config.max_movement_duration = None

        manager._check_travelling_time_configuration()

        # No warnings should be logged
        manager.logger.warning.assert_not_called()

    # ========================================================================
    # TEST 2: max_duration = 0 → No check
    # ========================================================================

    def test_max_duration_zero(self, manager):
        """Test that check is skipped when max_duration is 0."""
        manager._facade_config.max_movement_duration = 0

        manager._check_travelling_time_configuration()

        # No warnings should be logged
        manager.logger.warning.assert_not_called()

    # ========================================================================
    # TEST 3: Cover entity not found → Debug log
    # ========================================================================

    def test_cover_entity_not_found(self, manager):
        """Test that missing cover entity is handled gracefully."""
        manager.hass.states.get.return_value = None

        manager._check_travelling_time_configuration()

        # Debug log should be called
        manager.logger.debug.assert_called()
        assert "not found" in manager.logger.debug.call_args[0][0]

    # ========================================================================
    # TEST 4: No travelling_time attributes → Debug log, no warning
    # ========================================================================

    def test_no_travelling_time_attributes(self, manager):
        """Test that covers without travelling_time are skipped."""
        cover_state = self.create_cover_state()  # No travelling_time
        manager.hass.states.get.return_value = cover_state

        manager._check_travelling_time_configuration()

        # Debug log should be called
        manager.logger.debug.assert_called()
        assert "no travelling_time attributes" in manager.logger.debug.call_args[0][0]

        # No warnings
        manager.logger.warning.assert_not_called()

    # ========================================================================
    # TEST 5: travelling_time < max_duration → OK, no warning
    # ========================================================================

    def test_travelling_time_less_than_max_duration(self, manager):
        """Test that correct configuration produces no warnings."""
        # travelling_time (30s) < max_duration (35s) ✅
        cover_state = self.create_cover_state(travelling_down=30, travelling_up=30)
        manager.hass.states.get.return_value = cover_state

        manager._check_travelling_time_configuration()

        # No warnings should be logged
        manager.logger.warning.assert_not_called()

    # ========================================================================
    # TEST 6: travelling_time_down > max_duration → WARNING
    # ========================================================================

    def test_travelling_time_down_greater_than_max_duration(self, manager):
        """Test warning when travelling_time_down > max_duration."""
        # travelling_time_down (40s) > max_duration (35s) ❌
        cover_state = self.create_cover_state(travelling_down=40)
        manager.hass.states.get.return_value = cover_state

        manager._check_travelling_time_configuration()

        # Warning should be logged
        manager.logger.warning.assert_called()

        call_args = manager.logger.warning.call_args
        assert "travelling_time_down" in call_args[0][0]  # Message template
        assert call_args[0][1] == "cover.test"  # cover_entity_id
        assert call_args[0][2] == 40  # travelling_down
        assert call_args[0][3] == SCFacadeConfig2.MAX_MOVEMENT_DURATION_STATIC.value  # Config key
        assert call_args[0][4] == 35  # max_duration
        assert call_args[0][5] == 43  # travelling_down + 3

    # ========================================================================
    # TEST 7: travelling_time_up > max_duration → WARNING
    # ========================================================================

    def test_travelling_time_up_greater_than_max_duration(self, manager):
        """Test warning when travelling_time_up > max_duration."""
        # travelling_time_up (40s) > max_duration (35s) ❌
        cover_state = self.create_cover_state(travelling_up=40)
        manager.hass.states.get.return_value = cover_state

        manager._check_travelling_time_configuration()

        # Warning should be logged
        manager.logger.warning.assert_called()

        call_args = manager.logger.warning.call_args
        assert "travelling_time_up" in call_args[0][0]
        assert call_args[0][2] == 40  # travelling_up
        assert call_args[0][4] == 35  # max_duration

    # ========================================================================
    # TEST 8: travelling_time_down == max_duration → WARNING
    # ========================================================================

    def test_travelling_time_down_equals_max_duration(self, manager):
        """Test warning when travelling_time_down == max_duration."""
        # travelling_time_down (35s) == max_duration (35s) ⚠️
        cover_state = self.create_cover_state(travelling_down=35)
        manager.hass.states.get.return_value = cover_state

        manager._check_travelling_time_configuration()

        # Warning should be logged
        manager.logger.warning.assert_called()
        warning_msg = manager.logger.warning.call_args[0][0]
        assert "travelling_time_down" in warning_msg
        assert "==" in warning_msg or "might cause" in warning_msg

    # ========================================================================
    # TEST 9: travelling_time_up == max_duration → WARNING
    # ========================================================================

    def test_travelling_time_up_equals_max_duration(self, manager):
        """Test warning when travelling_time_up == max_duration."""
        # travelling_time_up (35s) == max_duration (35s) ⚠️
        cover_state = self.create_cover_state(travelling_up=35)
        manager.hass.states.get.return_value = cover_state

        manager._check_travelling_time_configuration()

        # Warning should be logged
        manager.logger.warning.assert_called()

    # ========================================================================
    # TEST 10: Both travelling_time > max_duration → 2 Warnings
    # ========================================================================

    def test_both_travelling_times_greater(self, manager):
        """Test that both directions are checked independently."""
        # Both > max_duration
        cover_state = self.create_cover_state(travelling_down=40, travelling_up=45)
        manager.hass.states.get.return_value = cover_state

        manager._check_travelling_time_configuration()

        # Should log 2 warnings (one for down, one for up)
        assert manager.logger.warning.call_count == 2

    # ========================================================================
    # TEST 11: Only travelling_time_down set
    # ========================================================================

    def test_only_travelling_time_down_set(self, manager):
        """Test with only travelling_time_down configured."""
        cover_state = self.create_cover_state(travelling_down=40)
        manager.hass.states.get.return_value = cover_state

        manager._check_travelling_time_configuration()

        # Should check and warn about down only
        manager.logger.warning.assert_called_once()
        warning_msg = manager.logger.warning.call_args[0][0]
        assert "travelling_time_down" in warning_msg

    # ========================================================================
    # TEST 12: Only travelling_time_up set
    # ========================================================================

    def test_only_travelling_time_up_set(self, manager):
        """Test with only travelling_time_up configured."""
        cover_state = self.create_cover_state(travelling_up=40)
        manager.hass.states.get.return_value = cover_state

        manager._check_travelling_time_configuration()

        # Should check and warn about up only
        manager.logger.warning.assert_called_once()
        warning_msg = manager.logger.warning.call_args[0][0]
        assert "travelling_time_up" in warning_msg

    # ========================================================================
    # TEST 13: Multiple covers - mixed configuration
    # ========================================================================

    def test_multiple_covers_mixed_configuration(self, manager):
        """Test with multiple covers, some OK, some not."""
        manager._target_cover_entity_id = ["cover.test1", "cover.test2", "cover.test3"]

        # Cover 1: OK (30s < 35s)
        cover1 = self.create_cover_state(travelling_down=30, travelling_up=30)
        # Cover 2: NOT OK (40s > 35s)
        cover2 = self.create_cover_state(travelling_down=40, travelling_up=40)
        # Cover 3: No travelling_time
        cover3 = self.create_cover_state()

        manager.hass.states.get.side_effect = [cover1, cover2, cover3]

        manager._check_travelling_time_configuration()

        # Should log 2 warnings (both directions for cover2)
        assert manager.logger.warning.call_count == 2

    # ========================================================================
    # TEST 14: Recommended fix value in warning
    # ========================================================================

    def test_recommended_fix_value(self, manager):
        """Test that warning includes recommended fix value."""
        cover_state = self.create_cover_state(travelling_down=40)
        manager.hass.states.get.return_value = cover_state

        manager._check_travelling_time_configuration()

        call_args = manager.logger.warning.call_args
        assert call_args[0][5] == 43  # travelling_down (40) + 5

    # ========================================================================
    # TEST 15: Edge case - max_duration very small
    # ========================================================================

    def test_edge_case_small_max_duration(self, manager):
        """Test with very small max_duration."""
        manager._facade_config.max_movement_duration = 5
        cover_state = self.create_cover_state(travelling_down=30)
        manager.hass.states.get.return_value = cover_state

        manager._check_travelling_time_configuration()

        # Should warn
        manager.logger.warning.assert_called()

        call_args = manager.logger.warning.call_args
        assert call_args[0][2] == 30  # travelling_down
        assert call_args[0][4] == 5  # max_duration
        assert call_args[0][5] == 33  # recommended (30 + 5)
