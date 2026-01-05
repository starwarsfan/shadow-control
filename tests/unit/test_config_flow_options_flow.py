"""Tests for Shadow Control options flow."""

from unittest.mock import PropertyMock

import pytest
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.shadow_control.config_flow import ShadowControlOptionsFlowHandler
from custom_components.shadow_control.const import (
    DOMAIN,
    SC_CONF_NAME,
    TARGET_COVER_ENTITY,
    SCDynamicInput,
    SCFacadeConfig1,
    SCFacadeConfig2,
)


class TestOptionsFlow:
    """Test Shadow Control options flow."""

    @pytest.fixture
    def mock_config_entry_mode1(self):
        """Create a mock config entry for Mode1."""
        return MockConfigEntry(
            domain=DOMAIN,
            entry_id="test_entry_mode1",
            data={
                SC_CONF_NAME: "Test Mode1",
                SCFacadeConfig2.SHUTTER_TYPE_STATIC.value: "mode1",
            },
            options={
                TARGET_COVER_ENTITY: ["cover.test"],
                SCFacadeConfig1.AZIMUTH_STATIC.value: 180,
                SCDynamicInput.BRIGHTNESS_ENTITY.value: "sensor.brightness",
                SCDynamicInput.SUN_ELEVATION_ENTITY.value: "sensor.sun_elevation",
                SCDynamicInput.SUN_AZIMUTH_ENTITY.value: "sensor.sun_azimuth",
                SCFacadeConfig2.MAX_MOVEMENT_DURATION_STATIC.value: 30,
            },
        )

    @pytest.fixture
    def mock_config_entry_mode3(self):
        """Create a mock config entry for Mode3."""
        return MockConfigEntry(
            domain=DOMAIN,
            entry_id="test_entry_mode3",
            data={
                SC_CONF_NAME: "Test Mode3",
                SCFacadeConfig2.SHUTTER_TYPE_STATIC.value: "mode3",
            },
            options={
                TARGET_COVER_ENTITY: ["cover.jalousie"],
                SCFacadeConfig1.AZIMUTH_STATIC.value: 270,
                SCDynamicInput.BRIGHTNESS_ENTITY.value: "sensor.brightness",
                SCDynamicInput.SUN_ELEVATION_ENTITY.value: "sensor.sun_elevation",
                SCDynamicInput.SUN_AZIMUTH_ENTITY.value: "sensor.sun_azimuth",
                SCFacadeConfig2.MAX_MOVEMENT_DURATION_STATIC.value: 30,
            },
        )

    @pytest.fixture
    def options_flow_mode1(self, hass, mock_config_entry_mode1):
        """Create an options flow handler for Mode1."""
        # Add entry to hass FIRST!
        mock_config_entry_mode1.add_to_hass(hass)

        # Create handler and mock the config_entry property
        handler = ShadowControlOptionsFlowHandler()
        handler.hass = hass

        # Mock the config_entry property to return our mock entry
        type(handler).config_entry = PropertyMock(return_value=mock_config_entry_mode1)

        return handler

    @pytest.fixture
    def options_flow_mode3(self, hass, mock_config_entry_mode3):
        """Create an options flow handler for Mode3."""
        # Add entry to hass FIRST!
        mock_config_entry_mode3.add_to_hass(hass)

        # Create handler and mock the config_entry property
        handler = ShadowControlOptionsFlowHandler()
        handler.hass = hass

        # Mock the config_entry property
        type(handler).config_entry = PropertyMock(return_value=mock_config_entry_mode3)

        return handler

    # ========================================================================
    # TEST 1: Init Step Redirects to User
    # ========================================================================

    async def test_options_init_redirects_to_user(self, options_flow_mode1):
        """Test that init step redirects to user step."""
        result = await options_flow_mode1.async_step_init()

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"

    # ========================================================================
    # TEST 2: Init Loads Options Data
    # ========================================================================

    async def test_options_init_loads_data(self, options_flow_mode1):
        """Test that init step loads options data correctly."""
        await options_flow_mode1.async_step_init()

        assert options_flow_mode1.options_data is not None
        assert TARGET_COVER_ENTITY in options_flow_mode1.options_data
        assert options_flow_mode1.shutter_type == "mode1"
        assert options_flow_mode1.is_mode3 is False

    # ========================================================================
    # TEST 3: Init Detects Mode3
    # ========================================================================

    async def test_options_init_detects_mode3(self, options_flow_mode3):
        """Test that init step correctly detects Mode3."""
        await options_flow_mode3.async_step_init()

        assert options_flow_mode3.shutter_type == "mode3"
        assert options_flow_mode3.is_mode3 is True

    # ========================================================================
    # TEST 4: User Step Shows Form
    # ========================================================================

    async def test_options_user_step_shows_form(self, options_flow_mode1):
        """Test that user step shows form when no input provided."""
        await options_flow_mode1.async_step_init()
        result = await options_flow_mode1.async_step_user(user_input=None)

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"

    # ========================================================================
    # TEST 5: User Step - Missing Cover Error
    # ========================================================================

    async def test_options_user_missing_cover(self, options_flow_mode1):
        """Test validation error when cover is missing."""
        await options_flow_mode1.async_step_init()

        user_input = {
            # TARGET_COVER_ENTITY: missing!
            SCFacadeConfig1.AZIMUTH_STATIC.value: 180,
            SCFacadeConfig1.OFFSET_SUN_IN_STATIC.value: -90,
            SCFacadeConfig1.OFFSET_SUN_OUT_STATIC.value: 90,
            SCFacadeConfig1.ELEVATION_SUN_MIN_STATIC.value: 0,
            SCFacadeConfig1.ELEVATION_SUN_MAX_STATIC.value: 90,
        }

        result = await options_flow_mode1.async_step_user(user_input=user_input)

        assert result["type"] == FlowResultType.FORM
        assert TARGET_COVER_ENTITY in result["errors"]

    # ========================================================================
    # TEST 6: User Step - Missing Azimuth Error
    # ========================================================================

    async def test_options_user_missing_azimuth(self, options_flow_mode1):
        """Test validation error when azimuth is missing."""
        await options_flow_mode1.async_step_init()

        user_input = {
            TARGET_COVER_ENTITY: ["cover.test"],
            # SCFacadeConfig1.AZIMUTH_STATIC.value: missing!
            SCFacadeConfig1.OFFSET_SUN_IN_STATIC.value: -90,
            SCFacadeConfig1.OFFSET_SUN_OUT_STATIC.value: 90,
            SCFacadeConfig1.ELEVATION_SUN_MIN_STATIC.value: 0,
            SCFacadeConfig1.ELEVATION_SUN_MAX_STATIC.value: 90,
        }

        result = await options_flow_mode1.async_step_user(user_input=user_input)

        assert result["type"] == FlowResultType.FORM
        assert SCFacadeConfig1.AZIMUTH_STATIC.value in result["errors"]

    # ========================================================================
    # TEST 7: User Step - Sun Min >= Max Error
    # ========================================================================

    async def test_options_user_sun_min_greater_than_max(self, options_flow_mode1):
        """Test validation error when sun_min >= sun_max."""
        await options_flow_mode1.async_step_init()

        user_input = {
            TARGET_COVER_ENTITY: ["cover.test"],
            SCFacadeConfig1.AZIMUTH_STATIC.value: 180,
            SCFacadeConfig1.OFFSET_SUN_IN_STATIC.value: -90,
            SCFacadeConfig1.OFFSET_SUN_OUT_STATIC.value: 90,
            SCFacadeConfig1.ELEVATION_SUN_MIN_STATIC.value: 50,  # Min
            SCFacadeConfig1.ELEVATION_SUN_MAX_STATIC.value: 30,  # Max < Min!
        }

        result = await options_flow_mode1.async_step_user(user_input=user_input)

        assert result["type"] == FlowResultType.FORM
        assert SCFacadeConfig1.ELEVATION_SUN_MIN_STATIC.value in result["errors"]
        assert SCFacadeConfig1.ELEVATION_SUN_MAX_STATIC.value in result["errors"]
        assert result["errors"][SCFacadeConfig1.ELEVATION_SUN_MIN_STATIC.value] == "minGreaterThanMax"

    # ========================================================================
    # TEST 8: User Step - Sun Min == Max Error
    # ========================================================================

    async def test_options_user_sun_min_equals_max(self, options_flow_mode1):
        """Test validation error when sun_min == sun_max."""
        await options_flow_mode1.async_step_init()

        user_input = {
            TARGET_COVER_ENTITY: ["cover.test"],
            SCFacadeConfig1.AZIMUTH_STATIC.value: 180,
            SCFacadeConfig1.OFFSET_SUN_IN_STATIC.value: -90,
            SCFacadeConfig1.OFFSET_SUN_OUT_STATIC.value: 90,
            SCFacadeConfig1.ELEVATION_SUN_MIN_STATIC.value: 45,  # Equal!
            SCFacadeConfig1.ELEVATION_SUN_MAX_STATIC.value: 45,  # Equal!
        }

        result = await options_flow_mode1.async_step_user(user_input=user_input)

        assert result["type"] == FlowResultType.FORM
        assert SCFacadeConfig1.ELEVATION_SUN_MIN_STATIC.value in result["errors"]

    # ========================================================================
    # TEST 9: User Step Success → Facade Settings
    # ========================================================================

    async def test_options_user_success_redirects_to_facade(self, options_flow_mode1):
        """Test successful user step redirects to facade settings."""
        await options_flow_mode1.async_step_init()

        user_input = {
            TARGET_COVER_ENTITY: ["cover.test"],
            SCFacadeConfig1.AZIMUTH_STATIC.value: 180,
            SCFacadeConfig1.OFFSET_SUN_IN_STATIC.value: -90,
            SCFacadeConfig1.OFFSET_SUN_OUT_STATIC.value: 90,
            SCFacadeConfig1.ELEVATION_SUN_MIN_STATIC.value: 0,
            SCFacadeConfig1.ELEVATION_SUN_MAX_STATIC.value: 90,
        }

        result = await options_flow_mode1.async_step_user(user_input=user_input)

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "facade_settings"

    # ========================================================================
    # TEST 10: Facade Settings Shows Form
    # ========================================================================

    async def test_options_facade_shows_form(self, options_flow_mode1):
        """Test that facade settings step shows form."""
        await options_flow_mode1.async_step_init()
        result = await options_flow_mode1.async_step_facade_settings(user_input=None)

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "facade_settings"

    # ========================================================================
    # TEST 11: Facade Settings - Slat Width <= Distance Error (Mode1)
    # ========================================================================

    async def test_options_facade_slat_width_validation(self, options_flow_mode1):
        """Test validation error when slat_width <= slat_distance."""
        await options_flow_mode1.async_step_init()

        user_input = {
            SCFacadeConfig2.SLAT_WIDTH_STATIC.value: 60,  # Width
            SCFacadeConfig2.SLAT_DISTANCE_STATIC.value: 70,  # Distance > Width!
            SCFacadeConfig2.MAX_MOVEMENT_DURATION_STATIC.value: 30,
        }

        result = await options_flow_mode1.async_step_facade_settings(user_input=user_input)

        assert result["type"] == FlowResultType.FORM
        assert SCFacadeConfig2.SLAT_WIDTH_STATIC.value in result["errors"]
        assert SCFacadeConfig2.SLAT_DISTANCE_STATIC.value in result["errors"]
        assert result["errors"][SCFacadeConfig2.SLAT_WIDTH_STATIC.value] == "slatWidthSmallerThanDistance"

    # ========================================================================
    # TEST 12: Facade Settings - Mode3 Skips Slat Validation
    # ========================================================================

    async def test_options_facade_mode3_no_slat_validation(self, options_flow_mode3):
        """Test that Mode3 skips slat validation."""
        await options_flow_mode3.async_step_init()

        user_input = {
            # Mode3 has no slat fields, so this should succeed
            SCFacadeConfig2.MAX_MOVEMENT_DURATION_STATIC.value: 30,
            SCFacadeConfig2.MODIFICATION_TOLERANCE_HEIGHT_STATIC.value: 2,
        }

        result = await options_flow_mode3.async_step_facade_settings(user_input=user_input)

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "dynamic_inputs"

    # ========================================================================
    # TEST 13: Facade Settings Success → Dynamic Inputs
    # ========================================================================

    async def test_options_facade_success_redirects_to_dynamic(self, options_flow_mode1):
        """Test successful facade settings redirects to dynamic inputs."""
        await options_flow_mode1.async_step_init()

        user_input = {
            SCFacadeConfig2.SLAT_WIDTH_STATIC.value: 95,
            SCFacadeConfig2.SLAT_DISTANCE_STATIC.value: 67,
            SCFacadeConfig2.MAX_MOVEMENT_DURATION_STATIC.value: 30,
            SCFacadeConfig2.MODIFICATION_TOLERANCE_HEIGHT_STATIC.value: 2,
            SCFacadeConfig2.MODIFICATION_TOLERANCE_ANGLE_STATIC.value: 2,
        }

        result = await options_flow_mode1.async_step_facade_settings(user_input=user_input)

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "dynamic_inputs"

    # ========================================================================
    # TEST 14: Dynamic Inputs Shows Form
    # ========================================================================

    async def test_options_dynamic_shows_form(self, options_flow_mode1):
        """Test that dynamic inputs step shows form."""
        await options_flow_mode1.async_step_init()
        result = await options_flow_mode1.async_step_dynamic_inputs(user_input=None)

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "dynamic_inputs"

    # ========================================================================
    # TEST 15: Dynamic Inputs - Missing Brightness Error
    # ========================================================================

    async def test_options_dynamic_missing_brightness(self, options_flow_mode1):
        """Test validation error when brightness is missing."""
        await options_flow_mode1.async_step_init()

        user_input = {
            # SCDynamicInput.BRIGHTNESS_ENTITY.value: missing!
            SCDynamicInput.SUN_ELEVATION_ENTITY.value: "sensor.sun_elevation",
            SCDynamicInput.SUN_AZIMUTH_ENTITY.value: "sensor.sun_azimuth",
        }

        result = await options_flow_mode1.async_step_dynamic_inputs(user_input=user_input)

        assert result["type"] == FlowResultType.FORM
        assert SCDynamicInput.BRIGHTNESS_ENTITY.value in result["errors"]

    # ========================================================================
    # TEST 16: Dynamic Inputs - Missing Sun Elevation Error
    # ========================================================================

    async def test_options_dynamic_missing_sun_elevation(self, options_flow_mode1):
        """Test validation error when sun elevation is missing."""
        await options_flow_mode1.async_step_init()

        user_input = {
            SCDynamicInput.BRIGHTNESS_ENTITY.value: "sensor.brightness",
            # SCDynamicInput.SUN_ELEVATION_ENTITY.value: missing!
            SCDynamicInput.SUN_AZIMUTH_ENTITY.value: "sensor.sun_azimuth",
        }

        result = await options_flow_mode1.async_step_dynamic_inputs(user_input=user_input)

        assert result["type"] == FlowResultType.FORM
        assert SCDynamicInput.SUN_ELEVATION_ENTITY.value in result["errors"]

    # ========================================================================
    # TEST 17: Dynamic Inputs - Missing Sun Azimuth Error
    # ========================================================================

    async def test_options_dynamic_missing_sun_azimuth(self, options_flow_mode1):
        """Test validation error when sun azimuth is missing."""
        await options_flow_mode1.async_step_init()

        user_input = {
            SCDynamicInput.BRIGHTNESS_ENTITY.value: "sensor.brightness",
            SCDynamicInput.SUN_ELEVATION_ENTITY.value: "sensor.sun_elevation",
            # SCDynamicInput.SUN_AZIMUTH_ENTITY.value: missing!
        }

        result = await options_flow_mode1.async_step_dynamic_inputs(user_input=user_input)

        assert result["type"] == FlowResultType.FORM
        assert SCDynamicInput.SUN_AZIMUTH_ENTITY.value in result["errors"]

    # ========================================================================
    # TEST 18: Dynamic Inputs Success → Shadow Settings
    # ========================================================================

    async def test_options_dynamic_success_redirects_to_shadow(self, options_flow_mode1):
        """Test successful dynamic inputs redirects to shadow settings."""
        await options_flow_mode1.async_step_init()

        user_input = {
            SCDynamicInput.BRIGHTNESS_ENTITY.value: "sensor.brightness",
            SCDynamicInput.SUN_ELEVATION_ENTITY.value: "sensor.sun_elevation",
            SCDynamicInput.SUN_AZIMUTH_ENTITY.value: "sensor.sun_azimuth",
            SCDynamicInput.LOCK_INTEGRATION_ENTITY.value: "input_boolean.lock",
        }

        result = await options_flow_mode1.async_step_dynamic_inputs(user_input=user_input)

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "shadow_settings"

    # ========================================================================
    # TEST 19: Shadow Settings Shows Form
    # ========================================================================

    async def test_options_shadow_shows_form(self, options_flow_mode1):
        """Test that shadow settings step shows form."""
        await options_flow_mode1.async_step_init()
        result = await options_flow_mode1.async_step_shadow_settings(user_input=None)

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "shadow_settings"

    # ========================================================================
    # TEST 20: Shadow Settings Success → Dawn Settings
    # ========================================================================

    async def test_options_shadow_success_redirects_to_dawn(self, options_flow_mode1):
        """Test successful shadow settings redirects to dawn settings."""
        await options_flow_mode1.async_step_init()

        user_input = {
            # Shadow settings (all optional)
        }

        result = await options_flow_mode1.async_step_shadow_settings(user_input=user_input)

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "dawn_settings"

    # ========================================================================
    # TEST 21: Dawn Settings Shows Form
    # ========================================================================

    async def test_options_dawn_shows_form(self, options_flow_mode1):
        """Test that dawn settings step shows form."""
        await options_flow_mode1.async_step_init()
        result = await options_flow_mode1.async_step_dawn_settings(user_input=None)

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "dawn_settings"

    # ========================================================================
    # TEST 22: Dawn Settings Success → Save Entry
    # ========================================================================

    async def test_options_dawn_success_saves_entry(self, options_flow_mode1):
        """Test successful dawn settings saves the config entry."""
        await options_flow_mode1.async_step_init()

        # Set up all required data through the flow
        options_flow_mode1.options_data = {
            TARGET_COVER_ENTITY: ["cover.test"],
            SCFacadeConfig1.AZIMUTH_STATIC.value: 180,
            SCDynamicInput.BRIGHTNESS_ENTITY.value: "sensor.brightness",
            SCDynamicInput.SUN_ELEVATION_ENTITY.value: "sensor.sun_elevation",
            SCDynamicInput.SUN_AZIMUTH_ENTITY.value: "sensor.sun_azimuth",
            SCFacadeConfig2.MAX_MOVEMENT_DURATION_STATIC.value: 30,
        }

        user_input = {
            # Dawn settings (all optional)
        }

        result = await options_flow_mode1.async_step_dawn_settings(user_input=user_input)

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"] is not None

    # ========================================================================
    # TEST 23: Complete Flow Mode1
    # ========================================================================

    async def test_complete_options_flow_mode1(self, options_flow_mode1):
        """Test complete options flow for Mode1."""
        # Step 1: Init
        await options_flow_mode1.async_step_init()

        # Step 2: User (Facade Part 1)
        user_input = {
            TARGET_COVER_ENTITY: ["cover.living_room"],
            SCFacadeConfig1.AZIMUTH_STATIC.value: 180,
            SCFacadeConfig1.OFFSET_SUN_IN_STATIC.value: -90,
            SCFacadeConfig1.OFFSET_SUN_OUT_STATIC.value: 90,
            SCFacadeConfig1.ELEVATION_SUN_MIN_STATIC.value: 10,
            SCFacadeConfig1.ELEVATION_SUN_MAX_STATIC.value: 80,
        }
        result = await options_flow_mode1.async_step_user(user_input)
        assert result["step_id"] == "facade_settings"

        # Step 3: Facade Settings
        facade_input = {
            SCFacadeConfig2.SLAT_WIDTH_STATIC.value: 95,
            SCFacadeConfig2.SLAT_DISTANCE_STATIC.value: 67,
            SCFacadeConfig2.MAX_MOVEMENT_DURATION_STATIC.value: 35,
            SCFacadeConfig2.MODIFICATION_TOLERANCE_HEIGHT_STATIC.value: 2,
            SCFacadeConfig2.MODIFICATION_TOLERANCE_ANGLE_STATIC.value: 2,
        }
        result = await options_flow_mode1.async_step_facade_settings(facade_input)
        assert result["step_id"] == "dynamic_inputs"

        # Step 4: Dynamic Inputs
        dynamic_input = {
            SCDynamicInput.BRIGHTNESS_ENTITY.value: "sensor.brightness",
            SCDynamicInput.SUN_ELEVATION_ENTITY.value: "sensor.sun_elevation",
            SCDynamicInput.SUN_AZIMUTH_ENTITY.value: "sensor.sun_azimuth",
        }
        result = await options_flow_mode1.async_step_dynamic_inputs(dynamic_input)
        assert result["step_id"] == "shadow_settings"

        # Step 5: Shadow Settings
        shadow_input = {}
        result = await options_flow_mode1.async_step_shadow_settings(shadow_input)
        assert result["step_id"] == "dawn_settings"

        # Step 6: Dawn Settings (Final)
        dawn_input = {}
        result = await options_flow_mode1.async_step_dawn_settings(dawn_input)

        assert result["type"] == FlowResultType.CREATE_ENTRY

    # ========================================================================
    # TEST 24: Complete Flow Mode3
    # ========================================================================

    async def test_complete_options_flow_mode3(self, options_flow_mode3):
        """Test complete options flow for Mode3."""
        # Step 1: Init
        await options_flow_mode3.async_step_init()
        assert options_flow_mode3.is_mode3 is True

        # Step 2-6: Same as Mode1, but with Mode3 schemas
        user_input = {
            TARGET_COVER_ENTITY: ["cover.jalousie"],
            SCFacadeConfig1.AZIMUTH_STATIC.value: 270,
            SCFacadeConfig1.OFFSET_SUN_IN_STATIC.value: -90,
            SCFacadeConfig1.OFFSET_SUN_OUT_STATIC.value: 90,
            SCFacadeConfig1.ELEVATION_SUN_MIN_STATIC.value: 5,
            SCFacadeConfig1.ELEVATION_SUN_MAX_STATIC.value: 85,
        }
        result = await options_flow_mode3.async_step_user(user_input)
        assert result["step_id"] == "facade_settings"

        facade_input = {
            # Mode3 - no slat fields
            SCFacadeConfig2.MAX_MOVEMENT_DURATION_STATIC.value: 30,
            SCFacadeConfig2.MODIFICATION_TOLERANCE_HEIGHT_STATIC.value: 2,
        }
        result = await options_flow_mode3.async_step_facade_settings(facade_input)
        assert result["step_id"] == "dynamic_inputs"

        dynamic_input = {
            SCDynamicInput.BRIGHTNESS_ENTITY.value: "sensor.brightness",
            SCDynamicInput.SUN_ELEVATION_ENTITY.value: "sensor.sun_elevation",
            SCDynamicInput.SUN_AZIMUTH_ENTITY.value: "sensor.sun_azimuth",
        }
        result = await options_flow_mode3.async_step_dynamic_inputs(dynamic_input)
        assert result["step_id"] == "shadow_settings"

        shadow_input = {}
        result = await options_flow_mode3.async_step_shadow_settings(shadow_input)
        assert result["step_id"] == "dawn_settings"

        dawn_input = {}
        result = await options_flow_mode3.async_step_dawn_settings(dawn_input)

        assert result["type"] == FlowResultType.CREATE_ENTRY
