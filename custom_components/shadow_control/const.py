"""Constants for the Shadow Control integration."""

from enum import Enum, IntEnum

import voluptuous as vol
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import selector

DOMAIN = "shadow_control"
DOMAIN_DATA_MANAGERS = f"{DOMAIN}_managers"  # A good practice for unique keys
DEFAULT_NAME = "Shadow Control"
SC_CONF_COVERS = "covers"  # Constant for 'covers' key within configuration

# Config schema version
VERSION = 5

SC_CONF_NAME = "name"
DEBUG_ENABLED = "debug_enabled"
TARGET_COVER_ENTITY_ID = "target_cover_entity"


class SCInternal(Enum):
    """Instance specific internal Shadow Control entities."""

    LOCK_INTEGRATION_ENTITY = "{instance}_lock_integration_entity"
    LOCK_INTEGRATION_WITH_POSITION_ENTITY = "{instance}_lock_integration_with_position_entity"

    @classmethod
    def get_entity_id(cls, key, sanitized_instance_name) -> str:
        """Return the formatted entity_id for the given key and sanitized instance name."""
        return cls[key].value.format(instance=sanitized_instance_name)


class SCDynamicInput(Enum):
    """Dynamic configuration input enums."""

    BRIGHTNESS_ENTITY = "brightness_entity"
    BRIGHTNESS_DAWN_ENTITY = "brightness_dawn_entity"
    SUN_ELEVATION_ENTITY = "sun_elevation_entity"
    SUN_AZIMUTH_ENTITY = "sun_azimuth_entity"
    SHUTTER_CURRENT_HEIGHT_ENTITY = "shutter_current_height_entity"
    SHUTTER_CURRENT_ANGLE_ENTITY = "shutter_current_angle_entity"
    LOCK_INTEGRATION_ENTITY = "lock_integration_entity"
    LOCK_INTEGRATION_WITH_POSITION_ENTITY = "lock_integration_with_position_entity"
    LOCK_HEIGHT_ENTITY = "lock_height_entity"
    LOCK_HEIGHT_STATIC = "lock_height_static"
    LOCK_ANGLE_ENTITY = "lock_angle_entity"
    LOCK_ANGLE_STATIC = "lock_angle_static"
    MOVEMENT_RESTRICTION_HEIGHT_ENTITY = "movement_restriction_height_entity"
    MOVEMENT_RESTRICTION_HEIGHT_STATIC = "movement_restriction_height_static"
    MOVEMENT_RESTRICTION_ANGLE_ENTITY = "movement_restriction_angle_entity"
    MOVEMENT_RESTRICTION_ANGLE_STATIC = "movement_restriction_angle_static"
    ENFORCE_POSITIONING_ENTITY = "enforce_positioning_entity"


class SCFacadeConfig(Enum):
    """General facade configuration enums."""

    AZIMUTH_STATIC = "facade_azimuth_static"
    OFFSET_SUN_IN_STATIC = "facade_offset_sun_in_static"
    OFFSET_SUN_OUT_STATIC = "facade_offset_sun_out_static"
    ELEVATION_SUN_MIN_STATIC = "facade_elevation_sun_min_static"
    ELEVATION_SUN_MAX_STATIC = "facade_elevation_sun_max_static"
    SLAT_WIDTH_STATIC = "facade_slat_width_static"
    SLAT_DISTANCE_STATIC = "facade_slat_distance_static"
    SLAT_ANGLE_OFFSET_STATIC = "facade_slat_angle_offset_static"
    SLAT_MIN_ANGLE_STATIC = "facade_slat_min_angle_static"
    SHUTTER_STEPPING_HEIGHT_STATIC = "facade_shutter_stepping_height_static"
    SHUTTER_STEPPING_ANGLE_STATIC = "facade_shutter_stepping_angle_static"
    SHUTTER_TYPE_STATIC = "facade_shutter_type_static"
    LIGHT_STRIP_WIDTH_STATIC = "facade_light_strip_width_static"
    SHUTTER_HEIGHT_STATIC = "facade_shutter_height_static"
    NEUTRAL_POS_HEIGHT_STATIC = "facade_neutral_pos_height_static"
    NEUTRAL_POS_HEIGHT_ENTITY = "facade_neutral_pos_height_entity"
    NEUTRAL_POS_ANGLE_STATIC = "facade_neutral_pos_angle_static"
    NEUTRAL_POS_ANGLE_ENTITY = "facade_neutral_pos_angle_entity"
    MODIFICATION_TOLERANCE_HEIGHT_STATIC = "facade_modification_tolerance_height_static"
    MODIFICATION_TOLERANCE_ANGLE_STATIC = "facade_modification_tolerance_angle_static"


class SCShadowInput(Enum):
    """Shadow configuration enums."""

    CONTROL_ENABLED_ENTITY = "shadow_control_enabled_entity"
    CONTROL_ENABLED_STATIC = "shadow_control_enabled_static"
    BRIGHTNESS_THRESHOLD_ENTITY = "shadow_brightness_threshold_entity"
    BRIGHTNESS_THRESHOLD_STATIC = "shadow_brightness_threshold_static"
    AFTER_SECONDS_ENTITY = "shadow_after_seconds_entity"
    AFTER_SECONDS_STATIC = "shadow_after_seconds_static"
    SHUTTER_MAX_HEIGHT_ENTITY = "shadow_shutter_max_height_entity"
    SHUTTER_MAX_HEIGHT_STATIC = "shadow_shutter_max_height_static"
    SHUTTER_MAX_ANGLE_ENTITY = "shadow_shutter_max_angle_entity"
    SHUTTER_MAX_ANGLE_STATIC = "shadow_shutter_max_angle_static"
    SHUTTER_LOOK_THROUGH_SECONDS_ENTITY = "shadow_shutter_look_through_seconds_entity"
    SHUTTER_LOOK_THROUGH_SECONDS_STATIC = "shadow_shutter_look_through_seconds_static"
    SHUTTER_OPEN_SECONDS_ENTITY = "shadow_shutter_open_seconds_entity"
    SHUTTER_OPEN_SECONDS_STATIC = "shadow_shutter_open_seconds_static"
    SHUTTER_LOOK_THROUGH_ANGLE_ENTITY = "shadow_shutter_look_through_angle_entity"
    SHUTTER_LOOK_THROUGH_ANGLE_STATIC = "shadow_shutter_look_through_angle_static"
    HEIGHT_AFTER_SUN_ENTITY = "shadow_height_after_sun_entity"
    HEIGHT_AFTER_SUN_STATIC = "shadow_height_after_sun_static"
    ANGLE_AFTER_SUN_ENTITY = "shadow_angle_after_sun_entity"
    ANGLE_AFTER_SUN_STATIC = "shadow_angle_after_sun_static"


class SCDawnInput(Enum):
    """Dawn configuration enums."""

    CONTROL_ENABLED_ENTITY = "dawn_control_enabled_entity"
    CONTROL_ENABLED_STATIC = "dawn_control_enabled_static"
    BRIGHTNESS_THRESHOLD_ENTITY = "dawn_brightness_threshold_entity"
    BRIGHTNESS_THRESHOLD_STATIC = "dawn_brightness_threshold_static"
    AFTER_SECONDS_ENTITY = "dawn_after_seconds_entity"
    AFTER_SECONDS_STATIC = "dawn_after_seconds_static"
    SHUTTER_MAX_HEIGHT_ENTITY = "dawn_shutter_max_height_entity"
    SHUTTER_MAX_HEIGHT_STATIC = "dawn_shutter_max_height_static"
    SHUTTER_MAX_ANGLE_ENTITY = "dawn_shutter_max_angle_entity"
    SHUTTER_MAX_ANGLE_STATIC = "dawn_shutter_max_angle_static"
    SHUTTER_LOOK_THROUGH_SECONDS_ENTITY = "dawn_shutter_look_through_seconds_entity"
    SHUTTER_LOOK_THROUGH_SECONDS_STATIC = "dawn_shutter_look_through_seconds_static"
    SHUTTER_OPEN_SECONDS_ENTITY = "dawn_shutter_open_seconds_entity"
    SHUTTER_OPEN_SECONDS_STATIC = "dawn_shutter_open_seconds_static"
    SHUTTER_LOOK_THROUGH_ANGLE_ENTITY = "dawn_shutter_look_through_angle_entity"
    SHUTTER_LOOK_THROUGH_ANGLE_STATIC = "dawn_shutter_look_through_angle_static"
    HEIGHT_AFTER_DAWN_ENTITY = "dawn_height_after_dawn_entity"
    HEIGHT_AFTER_DAWN_STATIC = "dawn_height_after_dawn_static"
    ANGLE_AFTER_DAWN_ENTITY = "dawn_angle_after_dawn_entity"
    ANGLE_AFTER_DAWN_STATIC = "dawn_angle_after_dawn_static"


# State constants for shutter control
class ShutterState(IntEnum):
    """Enum for the possible states of the shutter."""

    SHADOW_FULL_CLOSE_TIMER_RUNNING = 6
    SHADOW_FULL_CLOSED = 5
    SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING = 4
    SHADOW_HORIZONTAL_NEUTRAL = 3
    SHADOW_NEUTRAL_TIMER_RUNNING = 2
    SHADOW_NEUTRAL = 1
    NEUTRAL = 0
    DAWN_NEUTRAL = -1
    DAWN_NEUTRAL_TIMER_RUNNING = -2
    DAWN_HORIZONTAL_NEUTRAL = -3
    DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING = -4
    DAWN_FULL_CLOSED = -5
    DAWN_FULL_CLOSE_TIMER_RUNNING = -6

    def to_ha_state_string(self) -> str:
        """Return the lowercase name for usage with SensorDeviceClass.ENUM options."""
        return self.name.lower()


# All known internal lock states
class LockState(IntEnum):
    """Enum for the possible states of the lock."""

    UNLOCKED = 0
    LOCKED_MANUALLY = 1
    LOCKED_MANUALLY_WITH_FORCED_POSITION = 2
    LOCKED_BY_EXTERNAL_MODIFICATION = 3


# Configuration values, how to update lock state output
class UpdateLockStateOutput(IntEnum):
    """Enum for the possible states of the lock."""

    UPDATE_LOCKSTATE_OUTPUT__NEVER = -1
    UPDATE_LOCKSTATE_OUTPUT__ALWAYS = 0
    UPDATE_LOCKSTATE_OUTPUT__ONLY_ON_EXTERNAL_MODIFICATION = 1
    UPDATE_LOCKSTATE_OUTPUT__ONLY_ON_MANUAL_LOCK = 2


# Configuration values for possible movements restriction
class MovementRestricted(Enum):
    """Enum for the possible movement restrictions."""

    NO_RESTRICTION = "no_restriction"
    ONLY_CLOSE = "only_close"
    ONLY_OPEN = "only_open"

    def to_ha_state_string(self) -> str:
        """Return the lowercase name for usage with selection."""
        return self.name.lower()


# Configuration values of known shutter types
class ShutterType(Enum):
    """Enum for the possible shutter types."""

    MODE1 = "mode1"
    MODE2 = "mode2"
    MODE3 = "mode3"


class SensorEntries(Enum):
    """Enum for the possible sensor entries."""

    USED_HEIGHT = "target_height"
    USED_ANGLE = "target_angle"
    USED_ANGLE_DEGREES = "target_angle_degrees"
    COMPUTED_HEIGHT = "computed_height"
    COMPUTED_ANGLE = "computed_angle"
    CURRENT_STATE = "current_state"
    LOCK_STATE = "lock_state"
    NEXT_SHUTTER_MODIFICATION = "next_shutter_modification"
    IS_IN_SUN = "is_in_sun"


# =================================================================================================
# Voluptuous schemas for minimal configuration
# They are used the initial configuration of a new instance, as the instance name is the one and
# only configuration value, which is immutable. So it must be stored within `data`. All
# other options will be stored as `options`.

# Wrapper for minimal configuration, which will be stored within `data`
CFG_MINIMAL_REQUIRED = vol.Schema(
    {
        vol.Optional(SC_CONF_NAME, default=""): selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)),
        vol.Optional(SCFacadeConfig.SHUTTER_TYPE_STATIC.value, default="mode1"): selector.SelectSelector(
            selector.SelectSelectorConfig(options=["mode1", "mode2", "mode3"], translation_key="facade_shutter_type")
        ),
    }
)

# Wrapper for minimal options, which will be used and validated within ConfigFlow and OptionFlow
CFG_MINIMAL_OPTIONS = vol.Schema(
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
CFG_MINIMAL = vol.Schema(CFG_MINIMAL_REQUIRED.schema | CFG_MINIMAL_OPTIONS.schema)
# End of minimal configuration schema
# =================================================================================================


# =================================================================================================
# Voluptuous schemas for options
#
# --- STEP 2: 1st part of facade configuration  ---
CFG_FACADE_SETTINGS_PART1 = vol.Schema(
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
CFG_FACADE_SETTINGS_PART2 = vol.Schema(
    {
        vol.Optional(SCFacadeConfig.NEUTRAL_POS_HEIGHT_STATIC.value, default=0): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(SCFacadeConfig.NEUTRAL_POS_HEIGHT_ENTITY.value): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number"])
        ),
        vol.Optional(SCFacadeConfig.NEUTRAL_POS_ANGLE_STATIC.value, default=0): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(SCFacadeConfig.NEUTRAL_POS_ANGLE_ENTITY.value): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number"])
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
CFG_DYNAMIC_INPUTS = vol.Schema(
    {
        vol.Optional(SCDynamicInput.BRIGHTNESS_ENTITY.value): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number"])
        ),
        vol.Optional(SCDynamicInput.BRIGHTNESS_DAWN_ENTITY.value): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number"])
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
        vol.Optional(SCDynamicInput.LOCK_INTEGRATION_ENTITY.value): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["input_boolean", "binary_sensor"])
        ),
        vol.Optional(SCDynamicInput.LOCK_INTEGRATION_WITH_POSITION_ENTITY.value): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["input_boolean", "binary_sensor"])
        ),
        vol.Optional(SCDynamicInput.LOCK_HEIGHT_STATIC.value, default=0): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(SCDynamicInput.LOCK_HEIGHT_ENTITY.value): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number"])
        ),
        vol.Optional(SCDynamicInput.LOCK_ANGLE_STATIC.value, default=0): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(SCDynamicInput.LOCK_ANGLE_ENTITY.value): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number"])
        ),
        vol.Optional(SCDynamicInput.MOVEMENT_RESTRICTION_HEIGHT_STATIC.value, default=MovementRestricted.NO_RESTRICTION.value): vol.In(
            [state.value for state in MovementRestricted]
        ),
        vol.Optional(SCDynamicInput.MOVEMENT_RESTRICTION_HEIGHT_ENTITY.value): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["input_text", "input_select", "select", "sensor"])
        ),
        vol.Optional(SCDynamicInput.MOVEMENT_RESTRICTION_ANGLE_STATIC.value, default=MovementRestricted.NO_RESTRICTION.value): vol.In(
            [state.value for state in MovementRestricted]
        ),
        vol.Optional(SCDynamicInput.MOVEMENT_RESTRICTION_ANGLE_ENTITY.value): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["input_text", "input_select", "select", "sensor"])
        ),
        vol.Optional(SCDynamicInput.ENFORCE_POSITIONING_ENTITY.value): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["input_boolean", "binary_sensor"])
        ),
    }
)

# --- STEP 5: Shadow settings ---
CFG_SHADOW_SETTINGS = vol.Schema(
    {
        vol.Optional(SCShadowInput.CONTROL_ENABLED_STATIC.value, default=True): selector.BooleanSelector(),
        vol.Optional(SCShadowInput.CONTROL_ENABLED_ENTITY.value): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["input_boolean", "binary_sensor"])
        ),
        # -----------------------------------------------------------------------
        vol.Optional(SCShadowInput.BRIGHTNESS_THRESHOLD_STATIC.value, default=50000): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=300000, step=1, mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(SCShadowInput.BRIGHTNESS_THRESHOLD_ENTITY.value): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number"])
        ),
        # -----------------------------------------------------------------------
        vol.Optional(SCShadowInput.AFTER_SECONDS_STATIC.value, default=15): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(SCShadowInput.AFTER_SECONDS_ENTITY.value): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number"])
        ),
        # -----------------------------------------------------------------------
        vol.Optional(SCShadowInput.SHUTTER_MAX_HEIGHT_STATIC.value, default=100): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
        ),
        vol.Optional(SCShadowInput.SHUTTER_MAX_HEIGHT_ENTITY.value): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number"])
        ),
        # -----------------------------------------------------------------------
        vol.Optional(SCShadowInput.SHUTTER_MAX_ANGLE_STATIC.value, default=100): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
        ),
        vol.Optional(SCShadowInput.SHUTTER_MAX_ANGLE_ENTITY.value): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number"])
        ),
        # -----------------------------------------------------------------------
        vol.Optional(SCShadowInput.SHUTTER_LOOK_THROUGH_SECONDS_STATIC.value, default=15): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(SCShadowInput.SHUTTER_LOOK_THROUGH_SECONDS_ENTITY.value): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number"])
        ),
        # -----------------------------------------------------------------------
        vol.Optional(SCShadowInput.SHUTTER_OPEN_SECONDS_STATIC.value, default=15): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(SCShadowInput.SHUTTER_OPEN_SECONDS_ENTITY.value): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number"])
        ),
        # -----------------------------------------------------------------------
        vol.Optional(SCShadowInput.SHUTTER_LOOK_THROUGH_ANGLE_STATIC.value, default=0): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
        ),
        vol.Optional(SCShadowInput.SHUTTER_LOOK_THROUGH_ANGLE_ENTITY.value): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number"])
        ),
        # -----------------------------------------------------------------------
        vol.Optional(SCShadowInput.HEIGHT_AFTER_SUN_STATIC.value, default=0): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
        ),
        vol.Optional(SCShadowInput.HEIGHT_AFTER_SUN_ENTITY.value): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number"])
        ),
        # -----------------------------------------------------------------------
        vol.Optional(SCShadowInput.ANGLE_AFTER_SUN_STATIC.value, default=0): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
        ),
        vol.Optional(SCShadowInput.ANGLE_AFTER_SUN_ENTITY.value): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number"])
        ),
    }
)

# --- STEP 6: Dawn settings ---
CFG_DAWN_SETTINGS = vol.Schema(
    {
        vol.Optional(SCDawnInput.CONTROL_ENABLED_STATIC.value, default=True): selector.BooleanSelector(),
        vol.Optional(SCDawnInput.CONTROL_ENABLED_ENTITY.value): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["input_boolean", "binary_sensor"])
        ),
        # -----------------------------------------------------------------------
        vol.Optional(SCDawnInput.BRIGHTNESS_THRESHOLD_STATIC.value, default=500): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=10000, step=1, mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(SCDawnInput.BRIGHTNESS_THRESHOLD_ENTITY.value): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number"])
        ),
        # -----------------------------------------------------------------------
        vol.Optional(SCDawnInput.AFTER_SECONDS_STATIC.value, default=15): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(SCDawnInput.AFTER_SECONDS_ENTITY.value): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number"])
        ),
        # -----------------------------------------------------------------------
        vol.Optional(SCDawnInput.SHUTTER_MAX_HEIGHT_STATIC.value, default=100): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
        ),
        vol.Optional(SCDawnInput.SHUTTER_MAX_HEIGHT_ENTITY.value): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number"])
        ),
        # -----------------------------------------------------------------------
        vol.Optional(SCDawnInput.SHUTTER_MAX_ANGLE_STATIC.value, default=100): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
        ),
        vol.Optional(SCDawnInput.SHUTTER_MAX_ANGLE_ENTITY.value): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number"])
        ),
        # -----------------------------------------------------------------------
        vol.Optional(SCDawnInput.SHUTTER_LOOK_THROUGH_SECONDS_STATIC.value, default=15): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(SCDawnInput.SHUTTER_LOOK_THROUGH_SECONDS_ENTITY.value): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number"])
        ),
        # -----------------------------------------------------------------------
        vol.Optional(SCDawnInput.SHUTTER_OPEN_SECONDS_STATIC.value, default=15): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(SCDawnInput.SHUTTER_OPEN_SECONDS_ENTITY.value): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number"])
        ),
        # -----------------------------------------------------------------------
        vol.Optional(SCDawnInput.SHUTTER_LOOK_THROUGH_ANGLE_STATIC.value, default=0): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
        ),
        vol.Optional(SCDawnInput.SHUTTER_LOOK_THROUGH_ANGLE_ENTITY.value): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number"])
        ),
        # -----------------------------------------------------------------------
        vol.Optional(SCDawnInput.HEIGHT_AFTER_DAWN_STATIC.value, default=0): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
        ),
        vol.Optional(SCDawnInput.HEIGHT_AFTER_DAWN_ENTITY.value): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number"])
        ),
        # -----------------------------------------------------------------------
        vol.Optional(SCDawnInput.ANGLE_AFTER_DAWN_STATIC.value, default=0): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
        ),
        vol.Optional(SCDawnInput.ANGLE_AFTER_DAWN_ENTITY.value): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number"])
        ),
    }
)

####################################################################################################
# === Mode3
# --- STEP 3: 2nd part of facade configuration ---
CFG_FACADE_SETTINGS_PART2_MODE3 = vol.Schema(
    {
        vol.Optional(SCFacadeConfig.NEUTRAL_POS_HEIGHT_STATIC.value, default=0): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(SCFacadeConfig.NEUTRAL_POS_HEIGHT_ENTITY.value): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number"])
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
CFG_DYNAMIC_INPUTS_MODE3 = vol.Schema(
    {
        vol.Optional(SCDynamicInput.BRIGHTNESS_ENTITY.value): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number"])
        ),
        vol.Optional(SCDynamicInput.BRIGHTNESS_DAWN_ENTITY.value): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number"])
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
        vol.Optional(SCDynamicInput.LOCK_INTEGRATION_ENTITY.value): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["input_boolean", "binary_sensor"])
        ),
        vol.Optional(SCDynamicInput.LOCK_INTEGRATION_WITH_POSITION_ENTITY.value): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["input_boolean", "binary_sensor"])
        ),
        vol.Optional(SCDynamicInput.LOCK_HEIGHT_STATIC.value, default=0): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(SCDynamicInput.LOCK_HEIGHT_ENTITY.value): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number"])
        ),
        vol.Optional(SCDynamicInput.MOVEMENT_RESTRICTION_HEIGHT_ENTITY.value): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["input_text", "input_select", "select", "sensor"])
        ),
        vol.Optional(SCDynamicInput.MOVEMENT_RESTRICTION_HEIGHT_STATIC.value, default=MovementRestricted.NO_RESTRICTION.value): vol.In(
            [state.value for state in MovementRestricted]
        ),
        vol.Optional(SCDynamicInput.ENFORCE_POSITIONING_ENTITY.value): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["input_boolean", "binary_sensor"])
        ),
    }
)

# --- STEP 5: Shadow settings ---
CFG_SHADOW_SETTINGS_MODE3 = vol.Schema(
    {
        vol.Optional(SCShadowInput.CONTROL_ENABLED_STATIC.value, default=True): selector.BooleanSelector(),
        vol.Optional(SCShadowInput.CONTROL_ENABLED_ENTITY.value): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["input_boolean", "binary_sensor"])
        ),
        # -----------------------------------------------------------------------
        vol.Optional(SCShadowInput.BRIGHTNESS_THRESHOLD_STATIC.value, default=50000): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=300000, step=1, mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(SCShadowInput.BRIGHTNESS_THRESHOLD_ENTITY.value): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number"])
        ),
        # -----------------------------------------------------------------------
        vol.Optional(SCShadowInput.AFTER_SECONDS_STATIC.value, default=15): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(SCShadowInput.AFTER_SECONDS_ENTITY.value): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number"])
        ),
        # -----------------------------------------------------------------------
        vol.Optional(SCShadowInput.SHUTTER_MAX_HEIGHT_STATIC.value, default=100): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
        ),
        vol.Optional(SCShadowInput.SHUTTER_MAX_HEIGHT_ENTITY.value): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number"])
        ),
        # -----------------------------------------------------------------------
        vol.Optional(SCShadowInput.SHUTTER_LOOK_THROUGH_SECONDS_STATIC.value, default=15): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(SCShadowInput.SHUTTER_LOOK_THROUGH_SECONDS_ENTITY.value): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number"])
        ),
        # -----------------------------------------------------------------------
        vol.Optional(SCShadowInput.SHUTTER_OPEN_SECONDS_STATIC.value, default=15): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(SCShadowInput.SHUTTER_OPEN_SECONDS_ENTITY.value): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number"])
        ),
        # -----------------------------------------------------------------------
        vol.Optional(SCShadowInput.HEIGHT_AFTER_SUN_STATIC.value, default=0): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
        ),
        vol.Optional(SCShadowInput.HEIGHT_AFTER_SUN_ENTITY.value): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number"])
        ),
    }
)

# --- STEP 6: Dawn settings ---
CFG_DAWN_SETTINGS_MODE3 = vol.Schema(
    {
        vol.Optional(SCDawnInput.CONTROL_ENABLED_STATIC.value, default=True): selector.BooleanSelector(),
        vol.Optional(SCDawnInput.CONTROL_ENABLED_ENTITY.value): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["input_boolean", "binary_sensor"])
        ),
        # -----------------------------------------------------------------------
        vol.Optional(SCDawnInput.BRIGHTNESS_THRESHOLD_STATIC.value, default=500): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=10000, step=1, mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(SCDawnInput.BRIGHTNESS_THRESHOLD_ENTITY.value): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number"])
        ),
        # -----------------------------------------------------------------------
        vol.Optional(SCDawnInput.AFTER_SECONDS_STATIC.value, default=15): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(SCDawnInput.AFTER_SECONDS_ENTITY.value): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number"])
        ),
        # -----------------------------------------------------------------------
        vol.Optional(SCDawnInput.SHUTTER_MAX_HEIGHT_STATIC.value, default=100): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
        ),
        vol.Optional(SCDawnInput.SHUTTER_MAX_HEIGHT_ENTITY.value): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number"])
        ),
        # -----------------------------------------------------------------------
        vol.Optional(SCDawnInput.SHUTTER_LOOK_THROUGH_SECONDS_STATIC.value, default=15): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(SCDawnInput.SHUTTER_LOOK_THROUGH_SECONDS_ENTITY.value): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number"])
        ),
        # -----------------------------------------------------------------------
        vol.Optional(SCDawnInput.SHUTTER_OPEN_SECONDS_STATIC.value, default=15): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(SCDawnInput.SHUTTER_OPEN_SECONDS_ENTITY.value): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number"])
        ),
        # -----------------------------------------------------------------------
        vol.Optional(SCDawnInput.HEIGHT_AFTER_DAWN_STATIC.value, default=0): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
        ),
        vol.Optional(SCDawnInput.HEIGHT_AFTER_DAWN_ENTITY.value): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number"])
        ),
    }
)

# Combined schema for OptionsFlow mode1/mode2
FULL_OPTIONS_SCHEMA = vol.Schema(
    {
        **CFG_FACADE_SETTINGS_PART1.schema,
        **CFG_FACADE_SETTINGS_PART2.schema,
        **CFG_DYNAMIC_INPUTS.schema,
        **CFG_SHADOW_SETTINGS.schema,
        **CFG_DAWN_SETTINGS.schema,
    },
    extra=vol.ALLOW_EXTRA,
)

# Combined schema for OptionsFlow mode1/mode2
FULL_OPTIONS_SCHEMA_MODE3 = vol.Schema(
    {
        **CFG_FACADE_SETTINGS_PART1.schema,
        **CFG_FACADE_SETTINGS_PART2_MODE3.schema,
        **CFG_DYNAMIC_INPUTS_MODE3.schema,
        **CFG_SHADOW_SETTINGS_MODE3.schema,
        **CFG_DAWN_SETTINGS_MODE3.schema,
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
        vol.Optional(SCDynamicInput.LOCK_HEIGHT_STATIC.value, default=0): vol.Coerce(float),
        vol.Optional(SCDynamicInput.LOCK_HEIGHT_ENTITY.value): cv.entity_id,
        vol.Optional(SCDynamicInput.LOCK_ANGLE_STATIC.value, default=0): vol.Coerce(float),
        vol.Optional(SCDynamicInput.LOCK_ANGLE_ENTITY.value): cv.entity_id,
        vol.Optional(SCDynamicInput.MOVEMENT_RESTRICTION_HEIGHT_STATIC.value, default="no_restriction"): vol.In(
            [
                "no_restriction",
                "only_open",
                "only_close",
            ]
        ),
        vol.Optional(SCDynamicInput.MOVEMENT_RESTRICTION_HEIGHT_ENTITY.value): cv.entity_id,
        vol.Optional(SCDynamicInput.MOVEMENT_RESTRICTION_ANGLE_STATIC.value, default="no_restriction"): vol.In(
            [
                "no_restriction",
                "only_open",
                "only_close",
            ]
        ),
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
