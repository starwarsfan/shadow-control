"""Tests for async_calculate_and_apply_cover_position method."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import Event

from custom_components.shadow_control import ShadowControlManager
from custom_components.shadow_control.const import (
    SCDawnInput,
    SCDynamicInput,
    SCShadowInput,
)


class TestAsyncCalculateAndApplyCoverPosition:
    """Test async_calculate_and_apply_cover_position method."""

    @pytest.fixture
    def manager(self):
        """Create a mock ShadowControlManager instance."""
        # Mock the instance with required attributes
        instance = MagicMock(spec=ShadowControlManager)
        instance.logger = MagicMock()
        instance.hass = MagicMock()
        instance._config = MagicMock()
        instance._dynamic_config = MagicMock()
        instance._facade_config = MagicMock()

        # Set default values for lock states
        instance._dynamic_config.lock_integration = False
        instance._dynamic_config.lock_integration_with_position = False

        # Mock internal state variables
        instance._enforce_position_update = False
        instance._previous_shutter_height = 50.0
        instance._previous_shutter_angle = 45.0
        instance._height_during_lock_state = 50.0
        instance._angle_during_lock_state = 45.0

        # Mock methods that are called by async_calculate_and_apply_cover_position
        instance._update_input_values = AsyncMock()
        instance.get_internal_entity_id = MagicMock(return_value="test.entity")
        instance._check_if_facade_is_in_sun = AsyncMock(return_value=True)
        instance._shadow_handling_was_disabled = AsyncMock()
        instance._dawn_handling_was_disabled = AsyncMock()
        instance._force_immediate_positioning = AsyncMock()
        instance._process_shutter_state = AsyncMock()
        instance._handle_external_enforce_trigger = AsyncMock()
        instance._calculate_shutter_height = MagicMock(return_value=50.0)
        instance._calculate_shutter_angle = MagicMock(return_value=45.0)

        instance._last_unlock_time = None

        # Bind the actual method to the mock instance
        instance.async_calculate_and_apply_cover_position = ShadowControlManager.async_calculate_and_apply_cover_position.__get__(instance)

        return instance

    # ========================================================================
    # PHASE 1: EVENT-TYPE BRANCHES
    # ========================================================================

    async def test_initial_run_no_event(self, manager):
        """Test initial run with event=None (Branch 1B)."""
        await manager.async_calculate_and_apply_cover_position(event=None)

        manager._update_input_values.assert_called_once()
        manager._process_shutter_state.assert_called_once()
        manager._shadow_handling_was_disabled.assert_not_called()
        manager._dawn_handling_was_disabled.assert_not_called()
        manager._force_immediate_positioning.assert_not_called()

    async def test_state_changed_event(self, manager):
        """Test with state_changed event (Branch 2A)."""
        event = Event(
            "state_changed",
            {
                "entity_id": "sensor.brightness",
                "old_state": MagicMock(state="1000"),
                "new_state": MagicMock(state="50000"),
            },
        )

        await manager.async_calculate_and_apply_cover_position(event=event)
        manager._update_input_values.assert_called_once()

    async def test_time_changed_event(self, manager):
        """Test with time_changed event (Branch 2B)."""
        event = Event(
            "time_changed",
            {"now": datetime.now(tz=UTC)},
        )

        await manager.async_calculate_and_apply_cover_position(event=event)
        manager._update_input_values.assert_called_once()
        manager._process_shutter_state.assert_called_once()

    async def test_unhandled_event_type(self, manager):
        """Test with unhandled event type (Branch 2C)."""
        event = Event(
            "custom_event",
            {"some": "data"},
        )

        await manager.async_calculate_and_apply_cover_position(event=event)
        manager._update_input_values.assert_called_once()
        manager._process_shutter_state.assert_called_once()

    # ========================================================================
    # PHASE 2: ENTITY-TYPE BRANCHES (Config entities)
    # ========================================================================

    async def test_config_entity_change_with_lock_active(self, manager):
        """Test config entity change when lock is active (Branch 3A + 4A)."""
        manager._dynamic_config.lock_integration = True

        test_entity = "number.max_height"
        manager._config.get = MagicMock(return_value=test_entity)

        event = Event(
            "state_changed",
            {
                "entity_id": test_entity,
                "old_state": MagicMock(state="80"),
                "new_state": MagicMock(state="90"),
            },
        )

        await manager.async_calculate_and_apply_cover_position(event=event)

        manager._force_immediate_positioning.assert_not_called()
        manager._process_shutter_state.assert_called_once()

    async def test_config_entity_change_without_lock(self, manager):
        """Test config entity change when no lock is active (Branch 3A + 4B)."""
        manager._dynamic_config.lock_integration = False
        manager._dynamic_config.lock_integration_with_position = False

        test_entity = "number.max_height"
        manager._config.get = MagicMock(return_value=test_entity)

        event = Event(
            "state_changed",
            {
                "entity_id": test_entity,
                "old_state": MagicMock(state="80"),
                "new_state": MagicMock(state="90"),
            },
        )

        await manager.async_calculate_and_apply_cover_position(event=event)

        manager._force_immediate_positioning.assert_called_once()
        manager._process_shutter_state.assert_not_called()

    # ========================================================================
    # PHASE 3: LOCK-LOGIC BRANCHES
    # ========================================================================

    async def test_simple_lock_disabled_no_lock_with_position(self, manager):
        """Test simple lock disabled when lock_with_position is off (Branch 7A1)."""
        manager._dynamic_config.lock_integration_with_position = False
        lock_entity = "switch.lock"

        manager._config.get = MagicMock(side_effect=lambda key: lock_entity if key == SCDynamicInput.LOCK_INTEGRATION_ENTITY.value else None)

        event = Event(
            "state_changed",
            {
                "entity_id": lock_entity,
                "old_state": MagicMock(state=STATE_ON),
                "new_state": MagicMock(state=STATE_OFF),
            },
        )

        await manager.async_calculate_and_apply_cover_position(event=event)

        assert manager._last_unlock_time is not None
        assert manager._previous_shutter_height == 50.0
        assert manager._previous_shutter_angle == 45.0

    async def test_simple_lock_enabled(self, manager):
        """Test simple lock enabled (Branch 7A3)."""
        lock_entity = "switch.lock"

        manager._config.get = MagicMock(side_effect=lambda key: lock_entity if key == SCDynamicInput.LOCK_INTEGRATION_ENTITY.value else None)

        manager._previous_shutter_height = 60.0
        manager._previous_shutter_angle = 50.0

        event = Event(
            "state_changed",
            {
                "entity_id": lock_entity,
                "old_state": MagicMock(state=STATE_OFF),
                "new_state": MagicMock(state=STATE_ON),
            },
        )

        await manager.async_calculate_and_apply_cover_position(event=event)

        assert manager._height_during_lock_state == 60.0
        assert manager._angle_during_lock_state == 50.0

    async def test_lock_with_position_disabled_position_differs(self, manager):
        """Test lock with position disabled and position differs (Branch 8A1 + 9A)."""
        manager._dynamic_config.lock_integration = False
        manager._dynamic_config.lock_height = 40.0
        manager._dynamic_config.lock_angle = 30.0

        lock_entity = "switch.lock_with_position"

        manager._config.get = MagicMock(
            side_effect=lambda key: lock_entity if key == SCDynamicInput.LOCK_INTEGRATION_WITH_POSITION_ENTITY.value else None
        )

        manager._calculate_shutter_height = MagicMock(return_value=80.0)
        manager._calculate_shutter_angle = MagicMock(return_value=70.0)
        manager._facade_config.neutral_pos_height = 80.0
        manager._facade_config.neutral_pos_angle = 70.0

        event = Event(
            "state_changed",
            {
                "entity_id": lock_entity,
                "old_state": MagicMock(state=STATE_ON),
                "new_state": MagicMock(state=STATE_OFF),
            },
        )

        await manager.async_calculate_and_apply_cover_position(event=event)

        assert manager._enforce_position_update is True

    async def test_lock_with_position_disabled_position_same(self, manager):
        """Test lock with position disabled but position is same (Branch 8A1 + 9B)."""
        manager._dynamic_config.lock_integration = False
        manager._dynamic_config.lock_height = 50.0
        manager._dynamic_config.lock_angle = 45.0

        lock_entity = "switch.lock_with_position"

        manager._config.get = MagicMock(
            side_effect=lambda key: lock_entity if key == SCDynamicInput.LOCK_INTEGRATION_WITH_POSITION_ENTITY.value else None
        )

        manager._calculate_shutter_height = MagicMock(return_value=50.0)
        manager._calculate_shutter_angle = MagicMock(return_value=45.0)
        manager._facade_config.neutral_pos_height = 50.0
        manager._facade_config.neutral_pos_angle = 45.0

        event = Event(
            "state_changed",
            {
                "entity_id": lock_entity,
                "old_state": MagicMock(state=STATE_ON),
                "new_state": MagicMock(state=STATE_OFF),
            },
        )

        await manager.async_calculate_and_apply_cover_position(event=event)

        assert manager._enforce_position_update is False

    # ========================================================================
    # PHASE 4: FINAL EXECUTION BRANCHES
    # ========================================================================

    async def test_shadow_handling_disabled_execution_path(self, manager):
        """Test execution path when shadow handling was disabled (Branch 11A)."""
        shadow_enable_entity = "switch.shadow_enable"

        def config_get(key):
            if key == SCShadowInput.CONTROL_ENABLED_ENTITY.value:
                return shadow_enable_entity
            return None

        manager._config.get = MagicMock(side_effect=config_get)

        event = Event(
            "state_changed",
            {
                "entity_id": shadow_enable_entity,
                "old_state": MagicMock(state=STATE_ON),
                "new_state": MagicMock(state=STATE_OFF),
            },
        )

        await manager.async_calculate_and_apply_cover_position(event=event)

        manager._shadow_handling_was_disabled.assert_called_once()
        manager._dawn_handling_was_disabled.assert_not_called()
        manager._force_immediate_positioning.assert_not_called()
        manager._process_shutter_state.assert_not_called()

    async def test_dawn_handling_disabled_execution_path(self, manager):
        """Test execution path when dawn handling was disabled (Branch 11B)."""
        dawn_enable_entity = "switch.dawn_enable"

        def config_get(key):
            if key == SCDawnInput.CONTROL_ENABLED_ENTITY.value:
                return dawn_enable_entity
            return None

        manager._config.get = MagicMock(side_effect=config_get)

        event = Event(
            "state_changed",
            {
                "entity_id": dawn_enable_entity,
                "old_state": MagicMock(state=STATE_ON),
                "new_state": MagicMock(state=STATE_OFF),
            },
        )

        await manager.async_calculate_and_apply_cover_position(event=event)

        manager._shadow_handling_was_disabled.assert_not_called()
        manager._dawn_handling_was_disabled.assert_called_once()
        manager._force_immediate_positioning.assert_not_called()
        manager._process_shutter_state.assert_not_called()
