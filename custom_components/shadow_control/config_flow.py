"""Shadow Control ConfigFlow and OptionsFlow implementation."""

import logging

import homeassistant.helpers.entity_registry as er
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import selector
from voluptuous import Any

from .const import (
    DEBUG_ENABLED,
    DOMAIN,
    SC_CONF_NAME,
    TARGET_COVER_ENTITY_ID,
    VERSION,
    MovementRestricted,
    SCDawnInput,
    SCDynamicInput,
    SCFacadeConfig,
    SCShadowInput,
    ShutterType,
)

_LOGGER = logging.getLogger(__name__)

# =================================================================================================
# Voluptuous schemas for minimal configuration
# They are used the initial configuration of a new instance, as the instance name is the one and
# only configuration value, which is immutable. So it must be stored within `data`. All
# other options will be stored as `options`.


def get_entity_options(hass, domains: list[str]) -> list[str]:
    """Get list of entities for entity selector options for given domains."""
    entity_reg = er.async_get(hass)
    entities = [e.entity_id for e in entity_reg.entities.values() if e.domain in domains]
    return ["none", *entities]


# Wrapper for minimal configuration, which will be stored within `data`
# CFG_MINIMAL_REQUIRED = vol.Schema(
def get_cfg_minimal_required() -> vol.Schema:
    """Get minimal required configuration schema."""
    return vol.Schema(
        {
            vol.Optional(SC_CONF_NAME, default=""): selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)),
            vol.Optional(SCFacadeConfig.SHUTTER_TYPE_STATIC.value, default="mode1"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=["mode1", "mode2", "mode3"], translation_key="facade_shutter_type")
            ),
        }
    )


# Wrapper for minimal options, which will be used and validated within ConfigFlow and OptionFlow
# CFG_MINIMAL_OPTIONS = vol.Schema(
def get_cfg_minimal_options() -> vol.Schema:
    """Get minimal options configuration schema."""
    return vol.Schema(
        {
            vol.Optional(TARGET_COVER_ENTITY_ID): selector.EntitySelector(selector.EntitySelectorConfig(domain="cover", multiple=True)),
            vol.Optional(SCFacadeConfig.AZIMUTH_STATIC.value, default=180): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=359, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(SCDynamicInput.BRIGHTNESS_ENTITY.value): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number"])
            ),
            vol.Optional(SCDynamicInput.SUN_ELEVATION_ENTITY.value): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number"])
            ),
            vol.Optional(SCDynamicInput.SUN_AZIMUTH_ENTITY.value): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number"])
            ),
        }
    )


# Wrapper for minimal configuration, which is used to show initial ConfigFlow
CFG_MINIMAL = vol.Schema(get_cfg_minimal_required().schema | get_cfg_minimal_options().schema)
# End of minimal configuration schema
# =================================================================================================


# =================================================================================================
# Voluptuous schemas for options
#
# --- STEP 2: 1st part of facade configuration  ---
# CFG_FACADE_SETTINGS_PART1 = vol.Schema(
def get_cfg_facade_settings_part1() -> vol.Schema:
    """Get facade configuration schema with static options."""
    return vol.Schema(
        {
            vol.Optional(TARGET_COVER_ENTITY_ID): selector.EntitySelector(selector.EntitySelectorConfig(domain="cover", multiple=True)),
            vol.Optional(SCFacadeConfig.AZIMUTH_STATIC.value, default=180): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=359, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(SCFacadeConfig.OFFSET_SUN_IN_STATIC.value, default=-90): selector.NumberSelector(
                selector.NumberSelectorConfig(min=-90, max=0, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(SCFacadeConfig.OFFSET_SUN_OUT_STATIC.value, default=90): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=90, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(SCFacadeConfig.ELEVATION_SUN_MIN_STATIC.value, default=0): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=90, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(SCFacadeConfig.ELEVATION_SUN_MAX_STATIC.value, default=90): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=90, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(DEBUG_ENABLED, default=False): selector.BooleanSelector(),
        }
    )


####################################################################################################
# === Mode1 / Mode2
# --- STEP 3: 2nd part of facade configuration ---
# CFG_FACADE_SETTINGS_PART2 = vol.Schema(
def get_cfg_facade_settings_part2(hass) -> vol.Schema:
    """Get facade configuration schema with static and entity options."""
    entity_options_number = get_entity_options(hass, ["sensor", "input_number"])
    return vol.Schema(
        {
            vol.Optional(SCFacadeConfig.NEUTRAL_POS_HEIGHT_STATIC.value, default=0): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(SCFacadeConfig.NEUTRAL_POS_HEIGHT_ENTITY.value, default="none"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=entity_options_number)
            ),
            vol.Optional(SCFacadeConfig.NEUTRAL_POS_ANGLE_STATIC.value, default=0): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(SCFacadeConfig.NEUTRAL_POS_ANGLE_ENTITY.value, default="none"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=entity_options_number)
            ),
            vol.Optional(SCFacadeConfig.SLAT_WIDTH_STATIC.value, default=95): selector.NumberSelector(
                selector.NumberSelectorConfig(min=20, max=150, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(SCFacadeConfig.SLAT_DISTANCE_STATIC.value, default=67): selector.NumberSelector(
                selector.NumberSelectorConfig(min=20, max=150, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(SCFacadeConfig.SLAT_ANGLE_OFFSET_STATIC.value, default=0): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=10, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(SCFacadeConfig.SLAT_MIN_ANGLE_STATIC.value, default=0): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=90, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(SCFacadeConfig.SHUTTER_STEPPING_HEIGHT_STATIC.value, default=5): selector.NumberSelector(
                selector.NumberSelectorConfig(min=1, max=20, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(SCFacadeConfig.SHUTTER_STEPPING_ANGLE_STATIC.value, default=5): selector.NumberSelector(
                selector.NumberSelectorConfig(min=1, max=20, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(SCFacadeConfig.LIGHT_STRIP_WIDTH_STATIC.value, default=0): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=2000, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(SCFacadeConfig.SHUTTER_HEIGHT_STATIC.value, default=1000): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=3000, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(SCFacadeConfig.MODIFICATION_TOLERANCE_HEIGHT_STATIC.value, default=0): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=20, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(SCFacadeConfig.MODIFICATION_TOLERANCE_ANGLE_STATIC.value, default=0): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=20, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
        }
    )


# --- STEP 4: Dynamic settings ---
def get_cfg_dynamic_inputs(hass) -> vol.Schema:
    """Get dynamic input configuration schema with entity options."""
    entity_options_number = get_entity_options(hass, ["sensor", "input_number"])
    entity_options_boolean = get_entity_options(hass, ["input_boolean", "binary_sensor"])
    entity_options_select = get_entity_options(hass, ["sensor", "select", "input_select", "input_text"])
    return vol.Schema(
        {
            vol.Optional(SCDynamicInput.BRIGHTNESS_ENTITY.value): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number"])
            ),
            vol.Optional(SCDynamicInput.BRIGHTNESS_DAWN_ENTITY.value, default="none"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=entity_options_number)
            ),
            vol.Optional(SCDynamicInput.SUN_ELEVATION_ENTITY.value): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number"])
            ),
            vol.Optional(SCDynamicInput.SUN_AZIMUTH_ENTITY.value): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number"])
            ),
            # vol.Optional(SCDynamicInput.SHUTTER_CURRENT_HEIGHT_ENTITY.value): selector.EntitySelector(
            #     selector.EntitySelectorConfig(domain=["sensor", "input_number"])
            # ),
            # vol.Optional(SCDynamicInput.SHUTTER_CURRENT_ANGLE_ENTITY.value): selector.EntitySelector(
            #     selector.EntitySelectorConfig(domain=["sensor", "input_number"])
            # ),
            vol.Optional(SCDynamicInput.LOCK_INTEGRATION_ENTITY.value, default="none"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=entity_options_boolean)
            ),
            vol.Optional(SCDynamicInput.LOCK_INTEGRATION_WITH_POSITION_ENTITY.value, default="none"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=entity_options_boolean)
            ),
            vol.Optional(SCDynamicInput.LOCK_HEIGHT_ENTITY.value, default="none"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=entity_options_number)
            ),
            vol.Optional(SCDynamicInput.LOCK_ANGLE_ENTITY.value, default="none"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=entity_options_number)
            ),
            vol.Optional(SCDynamicInput.MOVEMENT_RESTRICTION_HEIGHT_ENTITY.value, default="none"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=entity_options_select)
            ),
            vol.Optional(SCDynamicInput.MOVEMENT_RESTRICTION_ANGLE_ENTITY.value, default="none"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=entity_options_select)
            ),
            vol.Optional(SCDynamicInput.ENFORCE_POSITIONING_ENTITY.value, default="none"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=entity_options_boolean)
            ),
        }
    )


# --- STEP 5: Shadow settings ---
# CFG_SHADOW_SETTINGS = vol.Schema(
def get_cfg_shadow_settings(hass) -> vol.Schema:
    """Get shadow configuration schema with static and entity options."""
    entity_options_number = get_entity_options(hass, ["sensor", "input_number"])
    entity_options_boolean = get_entity_options(hass, ["input_boolean", "binary_sensor"])
    return vol.Schema(
        {
            vol.Optional(SCShadowInput.CONTROL_ENABLED_STATIC.value, default=True): selector.BooleanSelector(),
            vol.Optional(SCShadowInput.CONTROL_ENABLED_ENTITY.value, default="none"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=entity_options_boolean)
            ),
            # -----------------------------------------------------------------------
            vol.Optional(SCShadowInput.BRIGHTNESS_THRESHOLD_STATIC.value, default=50000): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=300000, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(SCShadowInput.BRIGHTNESS_THRESHOLD_ENTITY.value, default="none"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=entity_options_number)
            ),
            # -----------------------------------------------------------------------
            vol.Optional(SCShadowInput.AFTER_SECONDS_STATIC.value, default=15): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(SCShadowInput.AFTER_SECONDS_ENTITY.value, default="none"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=entity_options_number)
            ),
            # -----------------------------------------------------------------------
            vol.Optional(SCShadowInput.SHUTTER_MAX_HEIGHT_STATIC.value, default=100): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
            ),
            vol.Optional(SCShadowInput.SHUTTER_MAX_HEIGHT_ENTITY.value, default="none"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=entity_options_number)
            ),
            # -----------------------------------------------------------------------
            vol.Optional(SCShadowInput.SHUTTER_MAX_ANGLE_STATIC.value, default=100): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
            ),
            vol.Optional(SCShadowInput.SHUTTER_MAX_ANGLE_ENTITY.value, default="none"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=entity_options_number)
            ),
            # -----------------------------------------------------------------------
            vol.Optional(SCShadowInput.SHUTTER_LOOK_THROUGH_SECONDS_STATIC.value, default=15): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(SCShadowInput.SHUTTER_LOOK_THROUGH_SECONDS_ENTITY.value, default="none"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=entity_options_number)
            ),
            # -----------------------------------------------------------------------
            vol.Optional(SCShadowInput.SHUTTER_OPEN_SECONDS_STATIC.value, default=15): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(SCShadowInput.SHUTTER_OPEN_SECONDS_ENTITY.value, default="none"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=entity_options_number)
            ),
            # -----------------------------------------------------------------------
            vol.Optional(SCShadowInput.SHUTTER_LOOK_THROUGH_ANGLE_STATIC.value, default=0): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
            ),
            vol.Optional(SCShadowInput.SHUTTER_LOOK_THROUGH_ANGLE_ENTITY.value, default="none"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=entity_options_number)
            ),
            # -----------------------------------------------------------------------
            vol.Optional(SCShadowInput.HEIGHT_AFTER_SUN_STATIC.value, default=0): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
            ),
            vol.Optional(SCShadowInput.HEIGHT_AFTER_SUN_ENTITY.value, default="none"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=entity_options_number)
            ),
            # -----------------------------------------------------------------------
            vol.Optional(SCShadowInput.ANGLE_AFTER_SUN_STATIC.value, default=0): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
            ),
            vol.Optional(SCShadowInput.ANGLE_AFTER_SUN_ENTITY.value, default="none"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=entity_options_number)
            ),
        }
    )


# --- STEP 6: Dawn settings ---
# CFG_DAWN_SETTINGS = vol.Schema(
def get_cfg_dawn_settings(hass) -> vol.Schema:
    """Get dawn configuration schema with static and entity options."""
    entity_options_number = get_entity_options(hass, ["sensor", "input_number"])
    entity_options_boolean = get_entity_options(hass, ["input_boolean", "binary_sensor"])
    return vol.Schema(
        {
            vol.Optional(SCDawnInput.CONTROL_ENABLED_STATIC.value, default=True): selector.BooleanSelector(),
            vol.Optional(SCDawnInput.CONTROL_ENABLED_ENTITY.value, default="none"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=entity_options_boolean)
            ),
            # -----------------------------------------------------------------------
            vol.Optional(SCDawnInput.BRIGHTNESS_THRESHOLD_STATIC.value, default=500): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=10000, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(SCDawnInput.BRIGHTNESS_THRESHOLD_ENTITY.value, default="none"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=entity_options_number)
            ),
            # -----------------------------------------------------------------------
            vol.Optional(SCDawnInput.AFTER_SECONDS_STATIC.value, default=15): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(SCDawnInput.AFTER_SECONDS_ENTITY.value, default="none"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=entity_options_number)
            ),
            # -----------------------------------------------------------------------
            vol.Optional(SCDawnInput.SHUTTER_MAX_HEIGHT_STATIC.value, default=100): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
            ),
            vol.Optional(SCDawnInput.SHUTTER_MAX_HEIGHT_ENTITY.value, default="none"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=entity_options_number)
            ),
            # -----------------------------------------------------------------------
            vol.Optional(SCDawnInput.SHUTTER_MAX_ANGLE_STATIC.value, default=100): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
            ),
            vol.Optional(SCDawnInput.SHUTTER_MAX_ANGLE_ENTITY.value, default="none"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=entity_options_number)
            ),
            # -----------------------------------------------------------------------
            vol.Optional(SCDawnInput.SHUTTER_LOOK_THROUGH_SECONDS_STATIC.value, default=15): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(SCDawnInput.SHUTTER_LOOK_THROUGH_SECONDS_ENTITY.value, default="none"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=entity_options_number)
            ),
            # -----------------------------------------------------------------------
            vol.Optional(SCDawnInput.SHUTTER_OPEN_SECONDS_STATIC.value, default=15): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(SCDawnInput.SHUTTER_OPEN_SECONDS_ENTITY.value, default="none"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=entity_options_number)
            ),
            # -----------------------------------------------------------------------
            vol.Optional(SCDawnInput.SHUTTER_LOOK_THROUGH_ANGLE_STATIC.value, default=0): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
            ),
            vol.Optional(SCDawnInput.SHUTTER_LOOK_THROUGH_ANGLE_ENTITY.value, default="none"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=entity_options_number)
            ),
            # -----------------------------------------------------------------------
            vol.Optional(SCDawnInput.HEIGHT_AFTER_DAWN_STATIC.value, default=0): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
            ),
            vol.Optional(SCDawnInput.HEIGHT_AFTER_DAWN_ENTITY.value, default="none"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=entity_options_number)
            ),
            # -----------------------------------------------------------------------
            vol.Optional(SCDawnInput.ANGLE_AFTER_DAWN_STATIC.value, default=0): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
            ),
            vol.Optional(SCDawnInput.ANGLE_AFTER_DAWN_ENTITY.value, default="none"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=entity_options_number)
            ),
        }
    )


####################################################################################################
# === Mode3
# --- STEP 3: 2nd part of facade configuration ---
# CFG_FACADE_SETTINGS_PART2_MODE3 = vol.Schema(
def get_cfg_facade_settings_part2_mode3(hass) -> vol.Schema:
    """Get facade configuration schema for mode3 with static and entity options."""
    entity_options_number = get_entity_options(hass, ["sensor", "input_number"])
    return vol.Schema(
        {
            vol.Optional(SCFacadeConfig.NEUTRAL_POS_HEIGHT_STATIC.value, default=0): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(SCFacadeConfig.NEUTRAL_POS_HEIGHT_ENTITY.value, default="none"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=entity_options_number)
            ),
            vol.Optional(SCFacadeConfig.SHUTTER_STEPPING_HEIGHT_STATIC.value, default=5): selector.NumberSelector(
                selector.NumberSelectorConfig(min=1, max=20, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(SCFacadeConfig.LIGHT_STRIP_WIDTH_STATIC.value, default=0): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=2000, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(SCFacadeConfig.SHUTTER_HEIGHT_STATIC.value, default=1000): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=3000, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(SCFacadeConfig.MODIFICATION_TOLERANCE_HEIGHT_STATIC.value, default=0): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=20, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
        }
    )


# --- STEP 4: Dynamic settings ---
# CFG_DYNAMIC_INPUTS_MODE3 = vol.Schema(
def get_cfg_dynamic_inputs_mode3(hass) -> vol.Schema:
    """Get dynamic input configuration schema for mode3 with entity options."""
    entity_options_number = get_entity_options(hass, ["sensor", "input_number"])
    entity_options_boolean = get_entity_options(hass, ["input_boolean", "binary_sensor"])
    entity_options_select = get_entity_options(hass, ["sensor", "select", "input_select", "input_text"])
    return vol.Schema(
        {
            vol.Optional(SCDynamicInput.BRIGHTNESS_ENTITY.value): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number"])
            ),
            vol.Optional(SCDynamicInput.BRIGHTNESS_DAWN_ENTITY.value, default="none"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=entity_options_number)
            ),
            vol.Optional(SCDynamicInput.SUN_ELEVATION_ENTITY.value): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number"])
            ),
            vol.Optional(SCDynamicInput.SUN_AZIMUTH_ENTITY.value): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number"])
            ),
            # vol.Optional(SCDynamicInput.SHUTTER_CURRENT_HEIGHT_ENTITY.value): selector.EntitySelector(
            #     selector.EntitySelectorConfig(domain=["sensor", "input_number"])
            # ),
            vol.Optional(SCDynamicInput.LOCK_INTEGRATION_ENTITY.value, default="none"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=entity_options_boolean)
            ),
            vol.Optional(SCDynamicInput.LOCK_INTEGRATION_WITH_POSITION_ENTITY.value, default="none"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=entity_options_boolean)
            ),
            vol.Optional(SCDynamicInput.LOCK_HEIGHT_ENTITY.value, default="none"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=entity_options_number)
            ),
            vol.Optional(SCDynamicInput.MOVEMENT_RESTRICTION_HEIGHT_ENTITY.value, default="none"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=entity_options_select)
            ),
            vol.Optional(SCDynamicInput.ENFORCE_POSITIONING_ENTITY.value, default="none"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=entity_options_boolean)
            ),
        }
    )


# --- STEP 5: Shadow settings ---
# CFG_SHADOW_SETTINGS_MODE3 = vol.Schema(
def get_cfg_shadow_settings_mode3(hass) -> vol.Schema:
    """Get shadow configuration schema for mode3 with static and entity options."""
    entity_options_number = get_entity_options(hass, ["sensor", "input_number"])
    entity_options_boolean = get_entity_options(hass, ["input_boolean", "binary_sensor"])
    return vol.Schema(
        {
            vol.Optional(SCShadowInput.CONTROL_ENABLED_STATIC.value, default=True): selector.BooleanSelector(),
            vol.Optional(SCShadowInput.CONTROL_ENABLED_ENTITY.value, default="none"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=entity_options_boolean)
            ),
            # -----------------------------------------------------------------------
            vol.Optional(SCShadowInput.BRIGHTNESS_THRESHOLD_STATIC.value, default=50000): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=300000, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(SCShadowInput.BRIGHTNESS_THRESHOLD_ENTITY.value, default="none"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=entity_options_number)
            ),
            # -----------------------------------------------------------------------
            vol.Optional(SCShadowInput.AFTER_SECONDS_STATIC.value, default=15): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(SCShadowInput.AFTER_SECONDS_ENTITY.value, default="none"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=entity_options_number)
            ),
            # -----------------------------------------------------------------------
            vol.Optional(SCShadowInput.SHUTTER_MAX_HEIGHT_STATIC.value, default=100): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
            ),
            vol.Optional(SCShadowInput.SHUTTER_MAX_HEIGHT_ENTITY.value, default="none"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=entity_options_number)
            ),
            # -----------------------------------------------------------------------
            vol.Optional(SCShadowInput.SHUTTER_LOOK_THROUGH_SECONDS_STATIC.value, default=15): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(SCShadowInput.SHUTTER_LOOK_THROUGH_SECONDS_ENTITY.value, default="none"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=entity_options_number)
            ),
            # -----------------------------------------------------------------------
            vol.Optional(SCShadowInput.SHUTTER_OPEN_SECONDS_STATIC.value, default=15): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(SCShadowInput.SHUTTER_OPEN_SECONDS_ENTITY.value, default="none"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=entity_options_number)
            ),
            # -----------------------------------------------------------------------
            vol.Optional(SCShadowInput.HEIGHT_AFTER_SUN_STATIC.value, default=0): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
            ),
            vol.Optional(SCShadowInput.HEIGHT_AFTER_SUN_ENTITY.value, default="none"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=entity_options_number)
            ),
        }
    )


# --- STEP 6: Dawn settings ---
# CFG_DAWN_SETTINGS_MODE3 = vol.Schema(
def get_cfg_dawn_settings_mode3(hass) -> vol.Schema:
    """Get dawn configuration schema for mode3 with static and entity options."""
    entity_options_number = get_entity_options(hass, ["sensor", "input_number"])
    entity_options_boolean = get_entity_options(hass, ["input_boolean", "binary_sensor"])
    return vol.Schema(
        {
            vol.Optional(SCDawnInput.CONTROL_ENABLED_STATIC.value, default=True): selector.BooleanSelector(),
            vol.Optional(SCDawnInput.CONTROL_ENABLED_ENTITY.value, default="none"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=entity_options_boolean)
            ),
            # -----------------------------------------------------------------------
            vol.Optional(SCDawnInput.BRIGHTNESS_THRESHOLD_STATIC.value, default=500): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=10000, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(SCDawnInput.BRIGHTNESS_THRESHOLD_ENTITY.value, default="none"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=entity_options_number)
            ),
            # -----------------------------------------------------------------------
            vol.Optional(SCDawnInput.AFTER_SECONDS_STATIC.value, default=15): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(SCDawnInput.AFTER_SECONDS_ENTITY.value, default="none"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=entity_options_number)
            ),
            # -----------------------------------------------------------------------
            vol.Optional(SCDawnInput.SHUTTER_MAX_HEIGHT_STATIC.value, default=100): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
            ),
            vol.Optional(SCDawnInput.SHUTTER_MAX_HEIGHT_ENTITY.value, default="none"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=entity_options_number)
            ),
            # -----------------------------------------------------------------------
            vol.Optional(SCDawnInput.SHUTTER_LOOK_THROUGH_SECONDS_STATIC.value, default=15): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(SCDawnInput.SHUTTER_LOOK_THROUGH_SECONDS_ENTITY.value, default="none"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=entity_options_number)
            ),
            # -----------------------------------------------------------------------
            vol.Optional(SCDawnInput.SHUTTER_OPEN_SECONDS_STATIC.value, default=15): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(SCDawnInput.SHUTTER_OPEN_SECONDS_ENTITY.value, default="none"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=entity_options_number)
            ),
            # -----------------------------------------------------------------------
            vol.Optional(SCDawnInput.HEIGHT_AFTER_DAWN_STATIC.value, default=0): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
            ),
            vol.Optional(SCDawnInput.HEIGHT_AFTER_DAWN_ENTITY.value, default="none"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=entity_options_number)
            ),
        }
    )


# Combined schema for OptionsFlow mode1/mode2
# FULL_OPTIONS_SCHEMA = vol.Schema(
def get_full_options_schema(hass) -> vol.Schema:
    """Get combined schema for OptionsFlow mode1/mode2."""
    return vol.Schema(
        {
            **get_cfg_facade_settings_part1().schema,
            **get_cfg_facade_settings_part2(hass).schema,
            **get_cfg_dynamic_inputs(hass).schema,
            **get_cfg_shadow_settings(hass).schema,
            **get_cfg_dawn_settings(hass).schema,
        },
        extra=vol.ALLOW_EXTRA,
    )


# Combined schema for OptionsFlow mode1/mode2
# FULL_OPTIONS_SCHEMA_MODE3 = vol.Schema(
def get_full_options_schema_mode3(hass) -> vol.Schema:
    """Get combined schema for OptionsFlow mode3."""
    return vol.Schema(
        {
            **get_cfg_facade_settings_part1().schema,
            **get_cfg_facade_settings_part2_mode3(hass).schema,
            **get_cfg_dynamic_inputs_mode3(hass).schema,
            **get_cfg_shadow_settings_mode3(hass).schema,
            **get_cfg_dawn_settings_mode3(hass).schema,
        },
        extra=vol.ALLOW_EXTRA,
    )


# End of Voluptuous schemas for options
# =================================================================================================

YAML_CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(SC_CONF_NAME): cv.string,  # Name ist hier erforderlich und einzigartig
        vol.Required(SCFacadeConfig.SHUTTER_TYPE_STATIC.value, default="mode1"): vol.In(
            [
                "mode1",
                "mode2",
                "mode3",
            ]
        ),
        vol.Required(TARGET_COVER_ENTITY_ID): vol.All(cv.ensure_list, [cv.entity_id]),
        vol.Optional(SCFacadeConfig.AZIMUTH_STATIC.value, default=180): vol.Coerce(float),
        vol.Optional(SCFacadeConfig.OFFSET_SUN_IN_STATIC.value, default=-90): vol.Coerce(float),
        vol.Optional(SCFacadeConfig.OFFSET_SUN_OUT_STATIC.value, default=90): vol.Coerce(float),
        vol.Optional(SCFacadeConfig.ELEVATION_SUN_MIN_STATIC.value, default=0): vol.Coerce(float),
        vol.Optional(SCFacadeConfig.ELEVATION_SUN_MAX_STATIC.value, default=90): vol.Coerce(float),
        vol.Optional(DEBUG_ENABLED, default=False): cv.boolean,
        vol.Optional(SCFacadeConfig.NEUTRAL_POS_HEIGHT_STATIC.value, default=0): vol.Coerce(float),
        vol.Optional(SCFacadeConfig.NEUTRAL_POS_HEIGHT_ENTITY.value): cv.entity_id,
        vol.Optional(SCFacadeConfig.NEUTRAL_POS_ANGLE_STATIC.value, default=0): vol.Coerce(float),
        vol.Optional(SCFacadeConfig.NEUTRAL_POS_ANGLE_ENTITY.value): cv.entity_id,
        vol.Optional(SCFacadeConfig.SLAT_WIDTH_STATIC.value, default=95): vol.Coerce(float),
        vol.Optional(SCFacadeConfig.SLAT_DISTANCE_STATIC.value, default=67): vol.Coerce(float),
        vol.Optional(SCFacadeConfig.SLAT_ANGLE_OFFSET_STATIC.value, default=0): vol.Coerce(float),
        vol.Optional(SCFacadeConfig.SLAT_MIN_ANGLE_STATIC.value, default=0): vol.Coerce(float),
        vol.Optional(SCFacadeConfig.SHUTTER_STEPPING_HEIGHT_STATIC.value, default=5): vol.Coerce(float),
        vol.Optional(SCFacadeConfig.SHUTTER_STEPPING_ANGLE_STATIC.value, default=5): vol.Coerce(float),
        vol.Optional(SCFacadeConfig.LIGHT_STRIP_WIDTH_STATIC.value, default=0): vol.Coerce(float),
        vol.Optional(SCFacadeConfig.SHUTTER_HEIGHT_STATIC.value, default=1000): vol.Coerce(float),
        vol.Optional(SCFacadeConfig.MODIFICATION_TOLERANCE_HEIGHT_STATIC.value, default=0): vol.Coerce(float),
        vol.Optional(SCFacadeConfig.MODIFICATION_TOLERANCE_ANGLE_STATIC.value, default=0): vol.Coerce(float),
        vol.Optional(SCDynamicInput.BRIGHTNESS_ENTITY.value): cv.entity_id,
        vol.Optional(SCDynamicInput.BRIGHTNESS_DAWN_ENTITY.value): cv.entity_id,
        vol.Optional(SCDynamicInput.SUN_ELEVATION_ENTITY.value): cv.entity_id,
        vol.Optional(SCDynamicInput.SUN_AZIMUTH_ENTITY.value): cv.entity_id,
        vol.Optional(SCDynamicInput.LOCK_INTEGRATION_ENTITY.value): cv.entity_id,
        vol.Optional(SCDynamicInput.LOCK_INTEGRATION_WITH_POSITION_ENTITY.value): cv.entity_id,
        vol.Optional(SCDynamicInput.LOCK_HEIGHT_ENTITY.value): cv.entity_id,
        vol.Optional(SCDynamicInput.LOCK_ANGLE_ENTITY.value): cv.entity_id,
        vol.Optional(SCDynamicInput.MOVEMENT_RESTRICTION_HEIGHT_ENTITY.value): cv.entity_id,
        vol.Optional(SCDynamicInput.MOVEMENT_RESTRICTION_ANGLE_ENTITY.value): cv.entity_id,
        vol.Optional(SCDynamicInput.ENFORCE_POSITIONING_ENTITY.value): cv.entity_id,
        vol.Optional(SCShadowInput.CONTROL_ENABLED_STATIC.value, default=True): cv.boolean,
        vol.Optional(SCShadowInput.CONTROL_ENABLED_ENTITY.value): cv.entity_id,
        vol.Optional(SCShadowInput.BRIGHTNESS_THRESHOLD_STATIC.value, default=50000): vol.Coerce(float),
        vol.Optional(SCShadowInput.BRIGHTNESS_THRESHOLD_ENTITY.value): cv.entity_id,
        vol.Optional(SCShadowInput.AFTER_SECONDS_STATIC.value, default=15): vol.Coerce(float),
        vol.Optional(SCShadowInput.AFTER_SECONDS_ENTITY.value): cv.entity_id,
        vol.Optional(SCShadowInput.SHUTTER_MAX_HEIGHT_STATIC.value, default=100): vol.Coerce(float),
        vol.Optional(SCShadowInput.SHUTTER_MAX_HEIGHT_ENTITY.value): cv.entity_id,
        vol.Optional(SCShadowInput.SHUTTER_MAX_ANGLE_STATIC.value, default=100): vol.Coerce(float),
        vol.Optional(SCShadowInput.SHUTTER_MAX_ANGLE_ENTITY.value): cv.entity_id,
        vol.Optional(SCShadowInput.SHUTTER_LOOK_THROUGH_SECONDS_STATIC.value, default=15): vol.Coerce(float),
        vol.Optional(SCShadowInput.SHUTTER_LOOK_THROUGH_SECONDS_ENTITY.value): cv.entity_id,
        vol.Optional(SCShadowInput.SHUTTER_OPEN_SECONDS_STATIC.value, default=15): vol.Coerce(float),
        vol.Optional(SCShadowInput.SHUTTER_OPEN_SECONDS_ENTITY.value): cv.entity_id,
        vol.Optional(SCShadowInput.SHUTTER_LOOK_THROUGH_ANGLE_STATIC.value, default=0): vol.Coerce(float),
        vol.Optional(SCShadowInput.SHUTTER_LOOK_THROUGH_ANGLE_ENTITY.value): cv.entity_id,
        vol.Optional(SCShadowInput.HEIGHT_AFTER_SUN_STATIC.value, default=0): vol.Coerce(float),
        vol.Optional(SCShadowInput.HEIGHT_AFTER_SUN_ENTITY.value): cv.entity_id,
        vol.Optional(SCShadowInput.ANGLE_AFTER_SUN_STATIC.value, default=0): vol.Coerce(float),
        vol.Optional(SCShadowInput.ANGLE_AFTER_SUN_ENTITY.value): cv.entity_id,
        vol.Optional(SCDawnInput.CONTROL_ENABLED_STATIC.value, default=True): cv.boolean,
        vol.Optional(SCDawnInput.CONTROL_ENABLED_ENTITY.value): cv.entity_id,
        vol.Optional(SCDawnInput.BRIGHTNESS_THRESHOLD_STATIC.value, default=500): vol.Coerce(float),
        vol.Optional(SCDawnInput.BRIGHTNESS_THRESHOLD_ENTITY.value): cv.entity_id,
        vol.Optional(SCDawnInput.AFTER_SECONDS_STATIC.value, default=15): vol.Coerce(float),
        vol.Optional(SCDawnInput.AFTER_SECONDS_ENTITY.value): cv.entity_id,
        vol.Optional(SCDawnInput.SHUTTER_MAX_HEIGHT_STATIC.value, default=100): vol.Coerce(float),
        vol.Optional(SCDawnInput.SHUTTER_MAX_HEIGHT_ENTITY.value): cv.entity_id,
        vol.Optional(SCDawnInput.SHUTTER_MAX_ANGLE_STATIC.value, default=100): vol.Coerce(float),
        vol.Optional(SCDawnInput.SHUTTER_MAX_ANGLE_ENTITY.value): cv.entity_id,
        vol.Optional(SCDawnInput.SHUTTER_LOOK_THROUGH_SECONDS_STATIC.value, default=15): vol.Coerce(float),
        vol.Optional(SCDawnInput.SHUTTER_LOOK_THROUGH_SECONDS_ENTITY.value): cv.entity_id,
        vol.Optional(SCDawnInput.SHUTTER_OPEN_SECONDS_STATIC.value, default=15): vol.Coerce(float),
        vol.Optional(SCDawnInput.SHUTTER_OPEN_SECONDS_ENTITY.value): cv.entity_id,
        vol.Optional(SCDawnInput.SHUTTER_LOOK_THROUGH_ANGLE_STATIC.value, default=0): vol.Coerce(float),
        vol.Optional(SCDawnInput.SHUTTER_LOOK_THROUGH_ANGLE_ENTITY.value): cv.entity_id,
        vol.Optional(SCDawnInput.HEIGHT_AFTER_DAWN_STATIC.value, default=0): vol.Coerce(float),
        vol.Optional(SCDawnInput.HEIGHT_AFTER_DAWN_ENTITY.value): cv.entity_id,
        vol.Optional(SCDawnInput.ANGLE_AFTER_DAWN_STATIC.value, default=0): vol.Coerce(float),
        vol.Optional(SCDawnInput.ANGLE_AFTER_DAWN_ENTITY.value): cv.entity_id,
    }
)


class ShadowControlConfigFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Shadow Control."""

    # Get the schema version from constants
    VERSION = VERSION
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.config_data = {}

    async def async_step_import(self, import_config: dict[str, Any]) -> FlowResult:
        """Handle a flow initiated by a YAML configuration."""
        # Check if there is already an instance to prevent duplicated entries
        # The name is the key
        instance_name = import_config.get(SC_CONF_NAME)
        if instance_name:
            for entry in self.hass.config_entries.async_entries(DOMAIN):
                if entry.data.get(SC_CONF_NAME) == instance_name:
                    _LOGGER.warning("Attempted to import duplicate Shadow Control instance '%s' from YAML. Skipping.", instance_name)
                    return self.async_abort(reason="already_configured")

        _LOGGER.debug("[ConfigFlow] Importing from YAML with config: %s", import_config)

        # Convert yaml configuration into ConfigEntry, 'name' goes to 'data' section,
        # all the rest into 'options'.
        # Must be the same as in __init__.py!
        config_data_for_entry = {
            SC_CONF_NAME: import_config.pop(SC_CONF_NAME),  # Remove name from import_config
            SCFacadeConfig.SHUTTER_TYPE_STATIC.value: import_config.pop(SCFacadeConfig.SHUTTER_TYPE_STATIC.value),
        }
        # All the rest into 'options'
        options_data_for_entry = import_config

        # Optional validation against FULL_OPTIONS_SCHEMA to verify the yaml data
        try:
            if config_data_for_entry.get(SCFacadeConfig.SHUTTER_TYPE_STATIC.value) == ShutterType.MODE3.value:
                validated_options = get_full_options_schema_mode3(self.hass)(options_data_for_entry)
            else:
                validated_options = get_full_options_schema(self.hass)(options_data_for_entry)
        except vol.Invalid:
            _LOGGER.exception("Validation error during YAML import for '%s'", instance_name)
            return self.async_abort(reason="invalid_yaml_config")

        # Create ConfigEntry with 'title' as the name within the UI
        return self.async_create_entry(
            title=instance_name,
            data=config_data_for_entry,
            options=validated_options,
        )

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        # Initialize data for the form, using user_input if available, else empty for initial display
        # This ensures fields are pre-filled if the form is redisplayed due to errors
        form_data = user_input if user_input is not None else {}

        if user_input is not None:
            _LOGGER.debug("[ConfigFlow] Received user_input: %s", user_input)

            # Manual validation of input fields to provide possible error messages
            # for each field at once and not step by step.
            if not user_input.get(SC_CONF_NAME):
                errors[SC_CONF_NAME] = "name"  # Error code from within strings.json

            if not user_input.get(TARGET_COVER_ENTITY_ID):
                errors[TARGET_COVER_ENTITY_ID] = "target_cover_entity"  # Error code from within strings.json

            if not user_input.get(SCFacadeConfig.SHUTTER_TYPE_STATIC.value):
                errors[SCFacadeConfig.SHUTTER_TYPE_STATIC.value] = "facade_shutter_type_static"

            if not user_input.get(SCFacadeConfig.AZIMUTH_STATIC.value):
                errors[SCFacadeConfig.AZIMUTH_STATIC.value] = "facade_azimuth_static_missing"

            if not user_input.get(SCDynamicInput.BRIGHTNESS_ENTITY.value):
                errors[SCDynamicInput.BRIGHTNESS_ENTITY.value] = "dynamic_brightness_missing"

            if not user_input.get(SCDynamicInput.SUN_ELEVATION_ENTITY.value):
                errors[SCDynamicInput.SUN_ELEVATION_ENTITY.value] = "dynamic_sun_elevation_missing"

            if not user_input.get(SCDynamicInput.SUN_AZIMUTH_ENTITY.value):
                errors[SCDynamicInput.SUN_AZIMUTH_ENTITY.value] = "dynamic_sun_azimuth_missing"

            # If configuration errors found, show the config form again
            if errors:
                return self.async_show_form(
                    step_id="user",
                    data_schema=self.add_suggested_values_to_schema(CFG_MINIMAL, form_data),
                    errors=errors,
                )

            instance_name = user_input.get(SC_CONF_NAME, "")

            # Check for already existing entries
            for entry in self.hass.config_entries.async_entries(DOMAIN):
                if entry.data.get(SC_CONF_NAME) == instance_name:
                    errors = {"base": "already_configured"}
                    return self.async_show_form(step_id="user", data_schema=CFG_MINIMAL, errors=errors)

            # Immutable configuration data, not available within OptionsFlow
            config_data_for_entry = {
                SC_CONF_NAME: instance_name,
                SCFacadeConfig.SHUTTER_TYPE_STATIC.value: user_input.get(SCFacadeConfig.SHUTTER_TYPE_STATIC.value, ""),
            }

            # Create list of options, which are visible and editable within OptionsFlow
            options_data_for_entry = {
                key: value
                for key, value in user_input.items()
                if key not in {SC_CONF_NAME, SCFacadeConfig.SHUTTER_TYPE_STATIC.value}  # Remove instance name and shutter type
            }

            # All fine, now perform voluptuous validation
            try:
                validated_options_initial = get_cfg_minimal_options()(options_data_for_entry)
                _LOGGER.debug("Creating entry with data: %s and options: %s", config_data_for_entry, validated_options_initial)
                return self.async_create_entry(
                    title=instance_name,
                    data=config_data_for_entry,
                    options=validated_options_initial,
                )
            except vol.Invalid as exc:
                _LOGGER.exception("Validation error during final config flow step:")
                for error in exc.errors:
                    if error.path:
                        errors[str(error.path[0])] = "invalid_input"
                    else:
                        errors["base"] = "unknown_error"

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(CFG_MINIMAL, self.config_data),
            errors=errors,
        )

    def _clean_number_inputs(self, user_input: dict[str, Any]) -> dict[str, Any]:
        """Convert empty string number fields to 0 or their default."""
        cleaned_input = user_input.copy()
        for key, value in cleaned_input.items():
            if isinstance(value, str) and value == "":
                # For selectors, the default should come from the schema itself
                # or be explicitly handled. Setting to 0 here for number fields.
                cleaned_input[key] = 0
                _LOGGER.debug("Cleaned empty string for key '%s' to 0.", key)
        return cleaned_input

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return ShadowControlOptionsFlowHandler()


class ShadowControlOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Shadow Control."""

    def __init__(self) -> None:
        """Initialize options flow."""
        self.options_data = None
        self.shutter_type = None
        self.is_mode3 = False

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage the options."""
        # Initialize options_data from config_entry.options, with all editable options
        self.options_data = dict(self.config_entry.options)
        self.shutter_type = self.config_entry.data.get(SCFacadeConfig.SHUTTER_TYPE_STATIC.value)
        if self.shutter_type == ShutterType.MODE3.value:
            self.is_mode3 = True

        _LOGGER.info("Initial options_data: %s, shutter type: %s", self.options_data, self.shutter_type)

        # Redirect to the first specific options step
        return await self.async_step_user(user_input)

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle general data options."""
        _LOGGER.debug("[OptionsFlow] -> async_step_user")
        errors: dict[str, str] = {}
        if user_input is not None:
            _LOGGER.debug("[OptionsFlow] Received user_input: %s", user_input)

            # Manual validation of input fields to provide possible error messages
            # for each field at once and not step by step.
            if not user_input.get(TARGET_COVER_ENTITY_ID):
                errors[TARGET_COVER_ENTITY_ID] = "target_cover_entity"  # Error code from within strings.json

            if not user_input.get(SCFacadeConfig.AZIMUTH_STATIC.value):
                errors[SCFacadeConfig.AZIMUTH_STATIC.value] = "facade_azimuth_static_missing"

            sun_min = user_input.get(SCFacadeConfig.ELEVATION_SUN_MIN_STATIC.value)
            sun_max = user_input.get(SCFacadeConfig.ELEVATION_SUN_MAX_STATIC.value)
            if sun_min >= sun_max:
                errors[SCFacadeConfig.ELEVATION_SUN_MIN_STATIC.value] = "minGreaterThanMax"
                errors[SCFacadeConfig.ELEVATION_SUN_MAX_STATIC.value] = "minGreaterThanMax"

            # If configuration errors found, show the config form again
            if errors:
                return self.async_show_form(
                    step_id="user",
                    data_schema=self.add_suggested_values_to_schema(get_cfg_facade_settings_part1(), self.options_data),
                    errors=errors,
                )

            self.options_data.update(user_input)
            _LOGGER.debug("[OptionsFlow] Shutter type: %s", self.shutter_type)
            # if self.shutter_type == ShutterType.MODE3.value:
            #     return await self.async_step_facade_settings_mode3()
            return await self.async_step_facade_settings()

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(get_cfg_facade_settings_part1(), self.options_data),
            errors=errors,
        )

    async def async_step_facade_settings(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle facade settings options."""
        _LOGGER.debug("[OptionsFlow] -> async_step_facade_settings")
        data_schema = get_cfg_facade_settings_part2(self.hass)
        if self.is_mode3:
            data_schema = get_cfg_facade_settings_part2_mode3(self.hass)

        errors: dict[str, str] = {}
        if user_input is not None:
            _LOGGER.debug("[OptionsFlow] Received user_input: %s", user_input)

            if not self.is_mode3:
                # Manual validation of input fields to provide possible error messages
                # for each field at once and not step by step.
                slat_width = user_input.get(SCFacadeConfig.SLAT_WIDTH_STATIC.value)
                slat_distance = user_input.get(SCFacadeConfig.SLAT_DISTANCE_STATIC.value)
                if slat_width is not None and slat_distance is not None and slat_width <= slat_distance:
                    errors[SCFacadeConfig.SLAT_WIDTH_STATIC.value] = "slatWidthSmallerThanDistance"
                    errors[SCFacadeConfig.SLAT_DISTANCE_STATIC.value] = "slatWidthSmallerThanDistance"

            # If configuration errors found, show the config form again
            if errors:
                return self.async_show_form(
                    step_id="facade_settings",
                    data_schema=self.add_suggested_values_to_schema(data_schema, self.options_data),
                    errors=errors,
                )

            self.options_data.update(self._clean_number_inputs(user_input))
            return await self.async_step_dynamic_inputs()

        return self.async_show_form(
            step_id="facade_settings",
            data_schema=self.add_suggested_values_to_schema(data_schema, self.options_data),
            errors=errors,
        )

    async def async_step_dynamic_inputs(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle dynamic inputs options."""
        _LOGGER.debug("[OptionsFlow] -> async_step_dynamic_inputs")
        data_schema = get_cfg_dynamic_inputs(self.hass)
        if self.is_mode3:
            data_schema = get_cfg_dynamic_inputs_mode3(self.hass)

        errors: dict[str, str] = {}
        if user_input is not None:
            _LOGGER.debug("[OptionsFlow] Received user_input: %s", user_input)

            # Manual validation of input fields to provide possible error messages
            # for each field at once and not step by step.
            if not user_input.get(SCDynamicInput.BRIGHTNESS_ENTITY.value):
                errors[SCDynamicInput.BRIGHTNESS_ENTITY.value] = "dynamic_brightness_missing"

            if not user_input.get(SCDynamicInput.SUN_ELEVATION_ENTITY.value):
                errors[SCDynamicInput.SUN_ELEVATION_ENTITY.value] = "dynamic_sun_elevation_missing"

            if not user_input.get(SCDynamicInput.SUN_AZIMUTH_ENTITY.value):
                errors[SCDynamicInput.SUN_AZIMUTH_ENTITY.value] = "dynamic_sun_azimuth_missing"

            # If configuration errors found, show the config form again
            if errors:
                return self.async_show_form(
                    step_id="dynamic_inputs",
                    data_schema=self.add_suggested_values_to_schema(data_schema, self.options_data),
                    errors=errors,
                )

            self.options_data.update(self._clean_number_inputs(user_input))
            return await self.async_step_shadow_settings()

        return self.async_show_form(
            step_id="dynamic_inputs",
            data_schema=self.add_suggested_values_to_schema(data_schema, self.options_data),
            errors=errors,
        )

    async def async_step_shadow_settings(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle shadow settings options."""
        _LOGGER.debug("[OptionsFlow] -> async_step_shadow_settings")
        data_schema = get_cfg_shadow_settings(self.hass)
        if self.is_mode3:
            data_schema = get_cfg_shadow_settings_mode3(self.hass)

        errors: dict[str, str] = {}
        if user_input is not None:
            self.options_data.update(self._clean_number_inputs(user_input))
            return await self.async_step_dawn_settings()

        return self.async_show_form(
            step_id="shadow_settings",
            data_schema=self.add_suggested_values_to_schema(data_schema, self.options_data),
            errors=errors,
        )

    async def async_step_dawn_settings(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle dawn settings options (final options step)."""
        _LOGGER.debug("[OptionsFlow] -> async_step_dawn_settings")
        data_schema = get_cfg_dawn_settings(self.hass)
        validation_schema = get_full_options_schema(self.hass)
        if self.is_mode3:
            data_schema = get_cfg_dawn_settings_mode3(self.hass)
            validation_schema = get_full_options_schema_mode3(self.hass)

        errors: dict[str, str] = {}
        if user_input is not None:
            self.options_data.update(self._clean_number_inputs(user_input))

            # Check for old style movement restriction configuration and remove it
            if self.options_data.get(SCDynamicInput.MOVEMENT_RESTRICTION_HEIGHT_ENTITY.value) in [state.value for state in MovementRestricted]:
                _LOGGER.debug("Removing old style movement restriction height configuration from options data.")
                self.options_data.pop(SCDynamicInput.MOVEMENT_RESTRICTION_HEIGHT_ENTITY.value)

            if self.options_data.get(SCDynamicInput.MOVEMENT_RESTRICTION_ANGLE_ENTITY.value) in [state.value for state in MovementRestricted]:
                _LOGGER.debug("Removing old style movement restriction angle configuration from options data.")
                self.options_data.pop(SCDynamicInput.MOVEMENT_RESTRICTION_ANGLE_ENTITY.value)

            _LOGGER.debug("Final options data before update: %s", self.options_data)

            try:
                # Validate the entire options configuration using the combined schema
                validated_options = validation_schema(self.options_data)
                _LOGGER.debug("Validated options data: %s", validated_options)

                self.hass.config_entries.async_update_entry(self.config_entry, data=self.config_entry.data, options=validated_options)

                return self.async_create_entry(title="", data=validated_options)

            except vol.Invalid as exc:
                _LOGGER.exception("Validation error during options flow final step:")
                for error in exc.errors:
                    if error.path:
                        errors[str(error.path[0])] = "invalid_input"
                    else:
                        errors["base"] = "unknown_error"

        return self.async_show_form(
            step_id="dawn_settings",
            data_schema=self.add_suggested_values_to_schema(data_schema, self.options_data),
            errors=errors,
        )

    def _clean_number_inputs(self, user_input: dict[str, Any]) -> dict[str, Any]:
        """Convert empty string number fields to 0 or their default."""
        cleaned_input = user_input.copy()
        for key, value in cleaned_input.items():
            if isinstance(value, str) and value == "":
                cleaned_input[key] = 0
                _LOGGER.debug("Cleaned empty string for key '%s' to 0 in options flow.", key)
        return cleaned_input
