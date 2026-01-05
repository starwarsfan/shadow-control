"""Tests for Shadow Control config flow."""

from unittest.mock import MagicMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.shadow_control.config_flow import (
    ShadowControlConfigFlowHandler,
)
from custom_components.shadow_control.const import (
    DOMAIN,
    SC_CONF_NAME,
    TARGET_COVER_ENTITY,
    SCDynamicInput,
    SCFacadeConfig1,
    SCFacadeConfig2,
)


class TestConfigFlow:
    """Test Shadow Control config flow."""

    @pytest.fixture
    def mock_hass(self):
        """Create a mock Home Assistant instance."""
        hass = MagicMock(spec=HomeAssistant)
        hass.config_entries = MagicMock()
        hass.config_entries.async_entries = MagicMock(return_value=[])
        return hass

    @pytest.fixture
    async def flow_handler(self, mock_hass):
        """Create a config flow handler."""
        handler = ShadowControlConfigFlowHandler()
        handler.hass = mock_hass
        return handler

    # ========================================================================
    # TEST 1: Initial Form Display
    # ========================================================================

    async def test_user_step_shows_form(self, flow_handler):
        """Test that user step shows the form when no input provided."""
        result = await flow_handler.async_step_user(user_input=None)

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {}

    # ========================================================================
    # TEST 2: Missing Name Error
    # ========================================================================

    async def test_user_step_missing_name(self, flow_handler):
        """Test validation error when name is missing."""
        user_input = {
            # SC_CONF_NAME: missing!
            SCFacadeConfig2.SHUTTER_TYPE_STATIC.value: "mode1",
            TARGET_COVER_ENTITY: ["cover.test"],
            SCFacadeConfig1.AZIMUTH_STATIC.value: 180,
            SCDynamicInput.BRIGHTNESS_ENTITY.value: "sensor.brightness",
            SCDynamicInput.SUN_ELEVATION_ENTITY.value: "sensor.sun_elevation",
            SCDynamicInput.SUN_AZIMUTH_ENTITY.value: "sensor.sun_azimuth",
        }

        result = await flow_handler.async_step_user(user_input=user_input)

        assert result["type"] == FlowResultType.FORM
        assert result["errors"][SC_CONF_NAME] == "name_missing"

    # ========================================================================
    # TEST 3: Missing Cover Entity Error
    # ========================================================================

    async def test_user_step_missing_cover(self, flow_handler):
        """Test validation error when cover entity is missing."""
        user_input = {
            SC_CONF_NAME: "Test Instance",
            SCFacadeConfig2.SHUTTER_TYPE_STATIC.value: "mode1",
            # TARGET_COVER_ENTITY: missing!
            SCFacadeConfig1.AZIMUTH_STATIC.value: 180,
            SCDynamicInput.BRIGHTNESS_ENTITY.value: "sensor.brightness",
            SCDynamicInput.SUN_ELEVATION_ENTITY.value: "sensor.sun_elevation",
            SCDynamicInput.SUN_AZIMUTH_ENTITY.value: "sensor.sun_azimuth",
        }

        result = await flow_handler.async_step_user(user_input=user_input)

        assert result["type"] == FlowResultType.FORM
        assert result["errors"][TARGET_COVER_ENTITY] == "target_cover_entity_missing"

    # ========================================================================
    # TEST 4: Missing Shutter Type Error
    # ========================================================================

    async def test_user_step_missing_shutter_type(self, flow_handler):
        """Test validation error when shutter type is missing."""
        user_input = {
            SC_CONF_NAME: "Test Instance",
            # SCFacadeConfig2.SHUTTER_TYPE_STATIC.value: missing!
            TARGET_COVER_ENTITY: ["cover.test"],
            SCFacadeConfig1.AZIMUTH_STATIC.value: 180,
            SCDynamicInput.BRIGHTNESS_ENTITY.value: "sensor.brightness",
            SCDynamicInput.SUN_ELEVATION_ENTITY.value: "sensor.sun_elevation",
            SCDynamicInput.SUN_AZIMUTH_ENTITY.value: "sensor.sun_azimuth",
        }

        result = await flow_handler.async_step_user(user_input=user_input)

        assert result["type"] == FlowResultType.FORM
        assert result["errors"][SCFacadeConfig2.SHUTTER_TYPE_STATIC.value] == "facade_shutter_type_static_missing"

    # ========================================================================
    # TEST 5: Missing Azimuth Error
    # ========================================================================

    async def test_user_step_missing_azimuth(self, flow_handler):
        """Test validation error when azimuth is missing."""
        user_input = {
            SC_CONF_NAME: "Test Instance",
            SCFacadeConfig2.SHUTTER_TYPE_STATIC.value: "mode1",
            TARGET_COVER_ENTITY: ["cover.test"],
            # SCFacadeConfig1.AZIMUTH_STATIC.value: missing!
            SCDynamicInput.BRIGHTNESS_ENTITY.value: "sensor.brightness",
            SCDynamicInput.SUN_ELEVATION_ENTITY.value: "sensor.sun_elevation",
            SCDynamicInput.SUN_AZIMUTH_ENTITY.value: "sensor.sun_azimuth",
        }

        result = await flow_handler.async_step_user(user_input=user_input)

        assert result["type"] == FlowResultType.FORM
        assert result["errors"][SCFacadeConfig1.AZIMUTH_STATIC.value] == "facade_azimuth_static_missing"

    # ========================================================================
    # TEST 6: Missing Brightness Entity Error
    # ========================================================================

    async def test_user_step_missing_brightness(self, flow_handler):
        """Test validation error when brightness entity is missing."""
        user_input = {
            SC_CONF_NAME: "Test Instance",
            SCFacadeConfig2.SHUTTER_TYPE_STATIC.value: "mode1",
            TARGET_COVER_ENTITY: ["cover.test"],
            SCFacadeConfig1.AZIMUTH_STATIC.value: 180,
            # SCDynamicInput.BRIGHTNESS_ENTITY.value: missing!
            SCDynamicInput.SUN_ELEVATION_ENTITY.value: "sensor.sun_elevation",
            SCDynamicInput.SUN_AZIMUTH_ENTITY.value: "sensor.sun_azimuth",
        }

        result = await flow_handler.async_step_user(user_input=user_input)

        assert result["type"] == FlowResultType.FORM
        assert result["errors"][SCDynamicInput.BRIGHTNESS_ENTITY.value] == "dynamic_brightness_missing"

    # ========================================================================
    # TEST 7: Missing Sun Elevation Error
    # ========================================================================

    async def test_user_step_missing_sun_elevation(self, flow_handler):
        """Test validation error when sun elevation entity is missing."""
        user_input = {
            SC_CONF_NAME: "Test Instance",
            SCFacadeConfig2.SHUTTER_TYPE_STATIC.value: "mode1",
            TARGET_COVER_ENTITY: ["cover.test"],
            SCFacadeConfig1.AZIMUTH_STATIC.value: 180,
            SCDynamicInput.BRIGHTNESS_ENTITY.value: "sensor.brightness",
            # SCDynamicInput.SUN_ELEVATION_ENTITY.value: missing!
            SCDynamicInput.SUN_AZIMUTH_ENTITY.value: "sensor.sun_azimuth",
        }

        result = await flow_handler.async_step_user(user_input=user_input)

        assert result["type"] == FlowResultType.FORM
        assert result["errors"][SCDynamicInput.SUN_ELEVATION_ENTITY.value] == "dynamic_sun_elevation_missing"

    # ========================================================================
    # TEST 8: Missing Sun Azimuth Error
    # ========================================================================

    async def test_user_step_missing_sun_azimuth(self, flow_handler):
        """Test validation error when sun azimuth entity is missing."""
        user_input = {
            SC_CONF_NAME: "Test Instance",
            SCFacadeConfig2.SHUTTER_TYPE_STATIC.value: "mode1",
            TARGET_COVER_ENTITY: ["cover.test"],
            SCFacadeConfig1.AZIMUTH_STATIC.value: 180,
            SCDynamicInput.BRIGHTNESS_ENTITY.value: "sensor.brightness",
            SCDynamicInput.SUN_ELEVATION_ENTITY.value: "sensor.sun_elevation",
            # SCDynamicInput.SUN_AZIMUTH_ENTITY.value: missing!
        }

        result = await flow_handler.async_step_user(user_input=user_input)

        assert result["type"] == FlowResultType.FORM
        assert result["errors"][SCDynamicInput.SUN_AZIMUTH_ENTITY.value] == "dynamic_sun_azimuth_missing"

    # ========================================================================
    # TEST 9: Multiple Missing Fields
    # ========================================================================

    async def test_user_step_multiple_missing_fields(self, flow_handler):
        """Test validation with multiple missing fields."""
        user_input = {
            # Most fields missing
            SCFacadeConfig2.SHUTTER_TYPE_STATIC.value: "mode1",
            TARGET_COVER_ENTITY: ["cover.test"],
        }

        result = await flow_handler.async_step_user(user_input=user_input)

        assert result["type"] == FlowResultType.FORM
        # Should have multiple errors
        assert SC_CONF_NAME in result["errors"]
        assert SCFacadeConfig1.AZIMUTH_STATIC.value in result["errors"]
        assert SCDynamicInput.BRIGHTNESS_ENTITY.value in result["errors"]

    # ========================================================================
    # TEST 10: Duplicate Instance Name
    # ========================================================================

    async def test_user_step_duplicate_name(self, flow_handler):
        """Test error when instance name already exists."""
        # Mock existing entry
        existing_entry = MockConfigEntry(
            domain=DOMAIN,
            data={SC_CONF_NAME: "Test Instance"},
        )
        flow_handler.hass.config_entries.async_entries.return_value = [existing_entry]

        user_input = {
            SC_CONF_NAME: "Test Instance",  # Same name!
            SCFacadeConfig2.SHUTTER_TYPE_STATIC.value: "mode1",
            TARGET_COVER_ENTITY: ["cover.test"],
            SCFacadeConfig1.AZIMUTH_STATIC.value: 180,
            SCDynamicInput.BRIGHTNESS_ENTITY.value: "sensor.brightness",
            SCDynamicInput.SUN_ELEVATION_ENTITY.value: "sensor.sun_elevation",
            SCDynamicInput.SUN_AZIMUTH_ENTITY.value: "sensor.sun_azimuth",
        }

        result = await flow_handler.async_step_user(user_input=user_input)

        assert result["type"] == FlowResultType.FORM
        assert result["errors"]["base"] == "already_configured"

    # ========================================================================
    # TEST 11: Successful Entry Creation
    # ========================================================================

    async def test_user_step_success(self, flow_handler):
        """Test successful config entry creation."""
        user_input = {
            SC_CONF_NAME: "Test Instance",
            SCFacadeConfig2.SHUTTER_TYPE_STATIC.value: "mode1",
            TARGET_COVER_ENTITY: ["cover.test"],
            SCFacadeConfig1.AZIMUTH_STATIC.value: 180,
            SCDynamicInput.BRIGHTNESS_ENTITY.value: "sensor.brightness",
            SCDynamicInput.SUN_ELEVATION_ENTITY.value: "sensor.sun_elevation",
            SCDynamicInput.SUN_AZIMUTH_ENTITY.value: "sensor.sun_azimuth",
        }

        result = await flow_handler.async_step_user(user_input=user_input)

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == "Test Instance"

        # Check data (immutable)
        assert result["data"][SC_CONF_NAME] == "Test Instance"
        assert result["data"][SCFacadeConfig2.SHUTTER_TYPE_STATIC.value] == "mode1"

        # Check options (editable)
        assert result["options"][TARGET_COVER_ENTITY] == ["cover.test"]
        assert result["options"][SCFacadeConfig1.AZIMUTH_STATIC.value] == 180
        assert result["options"][SCDynamicInput.BRIGHTNESS_ENTITY.value] == "sensor.brightness"

    # ========================================================================
    # TEST 12: Entry Creation with Mode2
    # ========================================================================

    async def test_user_step_success_mode2(self, flow_handler):
        """Test successful entry creation with mode2."""
        user_input = {
            SC_CONF_NAME: "Mode2 Instance",
            SCFacadeConfig2.SHUTTER_TYPE_STATIC.value: "mode2",
            TARGET_COVER_ENTITY: ["cover.test"],
            SCFacadeConfig1.AZIMUTH_STATIC.value: 90,
            SCDynamicInput.BRIGHTNESS_ENTITY.value: "sensor.brightness",
            SCDynamicInput.SUN_ELEVATION_ENTITY.value: "sensor.sun_elevation",
            SCDynamicInput.SUN_AZIMUTH_ENTITY.value: "sensor.sun_azimuth",
        }

        result = await flow_handler.async_step_user(user_input=user_input)

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"][SCFacadeConfig2.SHUTTER_TYPE_STATIC.value] == "mode2"

    # ========================================================================
    # TEST 13: Entry Creation with Mode3
    # ========================================================================

    async def test_user_step_success_mode3(self, flow_handler):
        """Test successful entry creation with mode3."""
        user_input = {
            SC_CONF_NAME: "Mode3 Instance",
            SCFacadeConfig2.SHUTTER_TYPE_STATIC.value: "mode3",
            TARGET_COVER_ENTITY: ["cover.jalousie"],
            SCFacadeConfig1.AZIMUTH_STATIC.value: 270,
            SCDynamicInput.BRIGHTNESS_ENTITY.value: "sensor.brightness",
            SCDynamicInput.SUN_ELEVATION_ENTITY.value: "sensor.sun_elevation",
            SCDynamicInput.SUN_AZIMUTH_ENTITY.value: "sensor.sun_azimuth",
        }

        result = await flow_handler.async_step_user(user_input=user_input)

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"][SCFacadeConfig2.SHUTTER_TYPE_STATIC.value] == "mode3"

    # ========================================================================
    # TEST 14: Multiple Cover Entities
    # ========================================================================

    async def test_user_step_multiple_covers(self, flow_handler):
        """Test successful entry with multiple cover entities."""
        user_input = {
            SC_CONF_NAME: "Multi Cover",
            SCFacadeConfig2.SHUTTER_TYPE_STATIC.value: "mode1",
            TARGET_COVER_ENTITY: ["cover.test1", "cover.test2", "cover.test3"],
            SCFacadeConfig1.AZIMUTH_STATIC.value: 180,
            SCDynamicInput.BRIGHTNESS_ENTITY.value: "sensor.brightness",
            SCDynamicInput.SUN_ELEVATION_ENTITY.value: "sensor.sun_elevation",
            SCDynamicInput.SUN_AZIMUTH_ENTITY.value: "sensor.sun_azimuth",
        }

        result = await flow_handler.async_step_user(user_input=user_input)

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert len(result["options"][TARGET_COVER_ENTITY]) == 3
