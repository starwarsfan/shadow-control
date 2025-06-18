"""Constants for the Shadow Control integration."""
from enum import Enum, IntEnum

DOMAIN = "shadow_control"
DOMAIN_DATA_MANAGERS = f"{DOMAIN}_managers" # A good practice for unique keys
DEFAULT_NAME = "Shadow Control"
SC_CONF_COVERS = "covers" # Constant for 'covers' key within configuration

SC_CONF_NAME = "name"
DEBUG_ENABLED = "debug_enabled"
TARGET_COVER_ENTITY_ID = "target_cover_entity"

# Dynamic configuration inputs
class SCDynamicInput(Enum):
    BRIGHTNESS_ENTITY = "brightness_entity"
    BRIGHTNESS_DAWN_ENTITY = "brightness_dawn_entity"
    SUN_ELEVATION_ENTITY = "sun_elevation_entity"
    SUN_AZIMUTH_ENTITY = "sun_azimuth_entity"
    SHUTTER_CURRENT_HEIGHT_ENTITY = "shutter_current_height_entity"
    SHUTTER_CURRENT_ANGLE_ENTITY = "shutter_current_angle_entity"
    LOCK_INTEGRATION_ENTITY = "lock_integration_entity"
    LOCK_INTEGRATION_WITH_POSITION_ENTITY = "lock_integration_with_position_entity"
    LOCK_HEIGHT_STATIC = "lock_height_static"
    LOCK_ANGLE_STATIC = "lock_angle_static"
    MOVEMENT_RESTRICTION_HEIGHT_ENTITY = "movement_restriction_height_entity"
    MOVEMENT_RESTRICTION_ANGLE_ENTITY = "movement_restriction_angle_entity"
    ENFORCE_POSITIONING_ENTITY = "enforce_positioning_entity"

# General facade configuration
class SCFacadeConfig(Enum):
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
    NEUTRAL_POS_ANGLE_STATIC = "facade_neutral_pos_angle_static"
    MODIFICATION_TOLERANCE_HEIGHT_STATIC = "facade_modification_tolerance_height_static"
    MODIFICATION_TOLERANCE_ANGLE_STATIC = "facade_modification_tolerance_angle_static"

# Shadow configuration
class SCShadowInput(Enum):
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

# Dawn configuration
class SCDawnInput(Enum):
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

# Configuration values of known shutter types
class ShutterType(Enum):
    """Enum for the possible shutter types."""
    MODE1 = "mode1"
    MODE2 = "mode2"

class SensorEntries(Enum):
    """Enum for the possible sensor entries."""
    TARGET_HEIGHT = "target_height"
    TARGET_ANGLE = "target_angle"
    TARGET_ANGLE_DEGREES = "target_angle_degrees"
    CURRENT_STATE = "current_state"
    LOCK_STATE = "lock_state"
    NEXT_SHUTTER_MODIFICATION = "next_shutter_modification"
    IS_IN_SUN = "is_in_sun"
