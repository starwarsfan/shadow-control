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
    SCInternal,
)

# ========================================================================
# YAML IMPORT TESTS
# ========================================================================


class TestConfigFlowYAMLImport:
    """Test YAML import functionality."""

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
    # TEST 15: Successful YAML Import
    # ========================================================================

    async def test_yaml_import_success(self, flow_handler):
        """Test successful YAML import."""
        import_config = {
            SC_CONF_NAME: "YAML Instance",
            SCFacadeConfig2.SHUTTER_TYPE_STATIC.value: "mode1",
            TARGET_COVER_ENTITY: ["cover.test"],
            SCFacadeConfig1.AZIMUTH_STATIC.value: 180,
            SCDynamicInput.BRIGHTNESS_ENTITY.value: "sensor.brightness",
            SCDynamicInput.SUN_ELEVATION_ENTITY.value: "sensor.sun_elevation",
            SCDynamicInput.SUN_AZIMUTH_ENTITY.value: "sensor.sun_azimuth",
            SCFacadeConfig2.MAX_MOVEMENT_DURATION_STATIC.value: 30,
            # Additional optional fields
            SCFacadeConfig1.OFFSET_SUN_IN_STATIC.value: -90,
            SCFacadeConfig1.OFFSET_SUN_OUT_STATIC.value: 90,
        }

        result = await flow_handler.async_step_import(import_config)

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == "YAML Instance"

        # Check data (immutable)
        assert result["data"][SC_CONF_NAME] == "YAML Instance"
        assert result["data"][SCFacadeConfig2.SHUTTER_TYPE_STATIC.value] == "mode1"

        # Check options (editable)
        assert result["options"][TARGET_COVER_ENTITY] == ["cover.test"]
        assert result["options"][SCFacadeConfig1.AZIMUTH_STATIC.value] == 180
        assert result["options"][SCFacadeConfig1.OFFSET_SUN_IN_STATIC.value] == -90

    # ========================================================================
    # TEST 16: YAML Import - Duplicate Name
    # ========================================================================

    async def test_yaml_import_duplicate_name(self, flow_handler):
        """Test YAML import aborts when instance name already exists."""
        # Mock existing entry
        existing_entry = MockConfigEntry(
            domain=DOMAIN,
            data={SC_CONF_NAME: "YAML Instance"},
        )
        flow_handler.hass.config_entries.async_entries.return_value = [existing_entry]

        import_config = {
            SC_CONF_NAME: "YAML Instance",  # Duplicate!
            SCFacadeConfig2.SHUTTER_TYPE_STATIC.value: "mode1",
            TARGET_COVER_ENTITY: ["cover.test"],
            SCFacadeConfig1.AZIMUTH_STATIC.value: 180,
            SCDynamicInput.BRIGHTNESS_ENTITY.value: "sensor.brightness",
            SCDynamicInput.SUN_ELEVATION_ENTITY.value: "sensor.sun_elevation",
            SCDynamicInput.SUN_AZIMUTH_ENTITY.value: "sensor.sun_azimuth",
        }

        result = await flow_handler.async_step_import(import_config)

        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "already_configured"

    # ========================================================================
    # TEST 17: YAML Import - Mode3
    # ========================================================================

    async def test_yaml_import_mode3(self, flow_handler):
        """Test successful YAML import with mode3."""
        import_config = {
            SC_CONF_NAME: "YAML Mode3",
            SCFacadeConfig2.SHUTTER_TYPE_STATIC.value: "mode3",
            TARGET_COVER_ENTITY: ["cover.jalousie"],
            SCFacadeConfig1.AZIMUTH_STATIC.value: 270,
            SCDynamicInput.BRIGHTNESS_ENTITY.value: "sensor.brightness",
            SCDynamicInput.SUN_ELEVATION_ENTITY.value: "sensor.sun_elevation",
            SCDynamicInput.SUN_AZIMUTH_ENTITY.value: "sensor.sun_azimuth",
            SCFacadeConfig2.MAX_MOVEMENT_DURATION_STATIC.value: 35,
            # Mode3 specific - no angle options
            SCFacadeConfig2.SLAT_WIDTH_STATIC.value: 95,
        }

        result = await flow_handler.async_step_import(import_config)

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"][SCFacadeConfig2.SHUTTER_TYPE_STATIC.value] == "mode3"

    # ========================================================================
    # TEST 18: YAML Import with SCInternal Values
    # ========================================================================

    async def test_yaml_import_with_sc_internal_values(self, flow_handler):
        """Test YAML import correctly handles SCInternal values."""

        import_config = {
            SC_CONF_NAME: "YAML with Internal",
            SCFacadeConfig2.SHUTTER_TYPE_STATIC.value: "mode1",
            TARGET_COVER_ENTITY: ["cover.test"],
            SCFacadeConfig1.AZIMUTH_STATIC.value: 180,
            SCDynamicInput.BRIGHTNESS_ENTITY.value: "sensor.brightness",
            SCDynamicInput.SUN_ELEVATION_ENTITY.value: "sensor.sun_elevation",
            SCDynamicInput.SUN_AZIMUTH_ENTITY.value: "sensor.sun_azimuth",
            SCFacadeConfig2.MAX_MOVEMENT_DURATION_STATIC.value: 30,
            # SCInternal values (manual overrides from YAML)
            SCInternal.LOCK_INTEGRATION_MANUAL.value: True,
            SCInternal.LOCK_HEIGHT_MANUAL.value: 50.0,
            SCInternal.SHADOW_CONTROL_ENABLED_MANUAL.value: True,
        }

        result = await flow_handler.async_step_import(import_config)

        assert result["type"] == FlowResultType.CREATE_ENTRY

        # SCInternal values should be stored separately
        assert "sc_internal_values" in result["data"]
        assert result["data"]["sc_internal_values"][SCInternal.LOCK_INTEGRATION_MANUAL.value] is True
        assert result["data"]["sc_internal_values"][SCInternal.LOCK_HEIGHT_MANUAL.value] == 50.0

        # SCInternal values should NOT be in options
        assert SCInternal.LOCK_INTEGRATION_MANUAL.value not in result["options"]

    # ========================================================================
    # TEST 19: YAML Import - Full Configuration
    # ========================================================================

    async def test_yaml_import_full_config(self, flow_handler):
        """Test YAML import with comprehensive configuration."""
        import_config = {
            # Required
            SC_CONF_NAME: "Full YAML Config",
            SCFacadeConfig2.SHUTTER_TYPE_STATIC.value: "mode1",
            TARGET_COVER_ENTITY: ["cover.living_room", "cover.dining_room"],
            SCFacadeConfig1.AZIMUTH_STATIC.value: 180,
            SCDynamicInput.BRIGHTNESS_ENTITY.value: "sensor.brightness",
            SCDynamicInput.SUN_ELEVATION_ENTITY.value: "sensor.sun_elevation",
            SCDynamicInput.SUN_AZIMUTH_ENTITY.value: "sensor.sun_azimuth",
            # Facade settings
            SCFacadeConfig1.OFFSET_SUN_IN_STATIC.value: -90,
            SCFacadeConfig1.OFFSET_SUN_OUT_STATIC.value: 90,
            SCFacadeConfig1.ELEVATION_SUN_MIN_STATIC.value: 5,
            SCFacadeConfig1.ELEVATION_SUN_MAX_STATIC.value: 85,
            SCFacadeConfig2.SLAT_WIDTH_STATIC.value: 95,
            SCFacadeConfig2.SLAT_DISTANCE_STATIC.value: 67,
            SCFacadeConfig2.MAX_MOVEMENT_DURATION_STATIC.value: 35,
            SCFacadeConfig2.MODIFICATION_TOLERANCE_HEIGHT_STATIC.value: 2,
            SCFacadeConfig2.MODIFICATION_TOLERANCE_ANGLE_STATIC.value: 2,
            # Dynamic inputs
            SCDynamicInput.LOCK_INTEGRATION_ENTITY.value: "input_boolean.lock",
            SCDynamicInput.BRIGHTNESS_DAWN_ENTITY.value: "sensor.brightness_dawn",
            # Shadow settings
            "shadow_brightness_threshold_entity": "input_number.shadow_threshold",
            "shadow_after_seconds_entity": "input_number.shadow_delay",
        }

        result = await flow_handler.async_step_import(import_config)

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == "Full YAML Config"
        assert len(result["options"][TARGET_COVER_ENTITY]) == 2
        assert result["options"][SCFacadeConfig2.MAX_MOVEMENT_DURATION_STATIC.value] == 35

    # ========================================================================
    # TEST 20: YAML Import - Invalid Config (should abort)
    # ========================================================================

    async def test_yaml_import_invalid_config(self, flow_handler):
        """Test YAML import with invalid configuration aborts."""
        import_config = {
            SC_CONF_NAME: "Invalid Config",
            SCFacadeConfig2.SHUTTER_TYPE_STATIC.value: "mode1",
            TARGET_COVER_ENTITY: ["cover.test"],
            SCFacadeConfig1.AZIMUTH_STATIC.value: 180,
            SCDynamicInput.BRIGHTNESS_ENTITY.value: "sensor.brightness",
            SCDynamicInput.SUN_ELEVATION_ENTITY.value: "sensor.sun_elevation",
            SCDynamicInput.SUN_AZIMUTH_ENTITY.value: "sensor.sun_azimuth",
            # Invalid value - outside range
            SCFacadeConfig1.AZIMUTH_STATIC.value: 500,  # Max is 359!
        }

        result = await flow_handler.async_step_import(import_config)

        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "invalid_yaml_config"

    # ========================================================================
    # TEST 21: YAML Import - Minimal Configuration
    # ========================================================================

    async def test_yaml_import_minimal_config(self, flow_handler):
        """Test YAML import with only required fields."""
        import_config = {
            SC_CONF_NAME: "Minimal YAML",
            SCFacadeConfig2.SHUTTER_TYPE_STATIC.value: "mode1",
            TARGET_COVER_ENTITY: ["cover.test"],
            SCFacadeConfig1.AZIMUTH_STATIC.value: 180,
            SCDynamicInput.BRIGHTNESS_ENTITY.value: "sensor.brightness",
            SCDynamicInput.SUN_ELEVATION_ENTITY.value: "sensor.sun_elevation",
            SCDynamicInput.SUN_AZIMUTH_ENTITY.value: "sensor.sun_azimuth",
            SCFacadeConfig2.MAX_MOVEMENT_DURATION_STATIC.value: 30,
            # No optional fields - all should get defaults
        }

        result = await flow_handler.async_step_import(import_config)

        assert result["type"] == FlowResultType.CREATE_ENTRY
        # Defaults should be applied by schema
        assert TARGET_COVER_ENTITY in result["options"]
