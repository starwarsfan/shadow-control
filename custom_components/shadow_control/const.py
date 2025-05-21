"""Constants for the Shadow Control integration."""

from enum import IntEnum

DOMAIN = "shadow_control"

CONF_NAME = "name"
CONF_SUN_ELEVATION = "elevation"
CONF_SUN_AZIMUT = "azimut"
CONF_BRIGHTNESS = "brightness"
CONF_BRIGHTNESS_DAWN = "brightness_dawn"
CONF_COVER = "cover"
CONF_LOCK = "lock"
CONF_LOCK_WITH_FORCED_POSITION = "lock_with_forced_position"
CONF_HEIGHT = "height"
CONF_ANGLE = "angle"
CONF_HEIGHT_NEUTRAL = "height_neutral"
CONF_ANGLE_NEUTRAL = "angle_neutral"
CONF_HEIGHT_AFTER_SHADOW = "height_after_shadow"
CONF_ANGLE_AFTER_SHADOW = "angle_after_shadow"
CONF_HEIGHT_AFTER_DAWN = "height_after_dawn"
CONF_ANGLE_AFTER_DAWN = "angle_after_dawn"
CONF_FACADE_AZIMUTH = "facade_azimuth"
CONF_FACADE_OFFSET_START = "facade_offset_start"
CONF_FACADE_OFFSET_END = "facade_offset_end"
CONF_NON_SHADOW_RANGE = "non_shadow_range"
CONF_SHUTTER_OVERALL_HEIGHT = "shutter_overall_height"
CONF_SHUTTER_SLAT_WIDTH = "shutter_slat_width"
CONF_SHUTTER_SLAT_DISTANCE = "shutter_slat_distance"
CONF_ANGLE_OFFSET = "angle_offset"
CONF_MIN_SHUTTER_ANGLE = "min_shutter_angle"
CONF_SHADOW_MAX_ANGLE = "shadow_max_angle"
CONF_FIX_MOVEMENT_DIRECTION_HEIGHT = "fix_movement_direction_height"
CONF_FIX_MOVEMENT_DIRECTION_ANGLE = "fix_movement_direction_angle"
CONF_MODIFICATION_RANGE_HEIGHT = "modification_range_height"
CONF_MODIFICATION_RANGE_ANGLE = "modification_range_angle"
CONF_SHADOW_MAX_HEIGHT = "shadow_max_height"
CONF_SHUTTER_TYPE = "shutter_type"
CONF_SHUTTER_ANGLE_STEPPING = "shutter_angle_stepping"
CONF_SHUTTER_HEIGHT_STEPPING = "shutter_height_stepping"
CONF_ELEVATION_MIN = "elevation_min"
CONF_ELEVATION_MAX = "elevation_max"
CONF_SHADOW_HANDLING_ACTIVATION = "shadow_handling_activation"
CONF_DAWN_HANDLING_ACTIVATION = "dawn_handling_activation"
CONF_SHADOW_THRESHOLD_CLOSE = "shadow_threshold_close"
CONF_DAWN_THRESHOLD_CLOSE = "dawn_threshold_close"
CONF_SHADOW_CLOSE_DELAY = "shadow_close_delay"
CONF_SHADOW_OPEN_SLAT_DELAY = "shadow_open_slat_delay"
CONF_SHADOW_OPEN_SHUTTER_DELAY = "shadow_open_shutter_delay"
CONF_SHADOW_THRESHOLD_OPEN = "shadow_threshold_open"
CONF_DAWN_CLOSE_DELAY = "dawn_close_delay"
CONF_DAWN_OPEN_SLAT_DELAY = "dawn_open_slat_delay"
CONF_DAWN_OPEN_SHUTTER_DELAY = "dawn_open_shutter_delay"
CONF_DAWN_THRESHOLD_OPEN = "dawn_threshold_open"
CONF_UPDATE_LOCKSTATE_OUTPUT = "update_lockstate_output"
CONF_DEBUG_ENABLED = "debug_enabled"  # Für den Debug-Schalter

# --- Status Konstanten für die Behangsteuerung -----------------------------
class ShutterState(IntEnum):
    """Enum for the possible states of the shutter."""
    STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING = 6
    STATE_SHADOW_FULL_CLOSED = 5
    STATE_SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING = 4
    STATE_SHADOW_HORIZONTAL_NEUTRAL = 3
    STATE_SHADOW_NEUTRAL_TIMER_RUNNING = 2
    STATE_SHADOW_NEUTRAL = 1
    STATE_NEUTRAL = 0
    STATE_DAWN_NEUTRAL = -1
    STATE_DAWN_NEUTRAL_TIMER_RUNNING = -2
    STATE_DAWN_HORIZONTAL_NEUTRAL = -3
    STATE_DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING = -4
    STATE_DAWN_FULL_CLOSED = -5
    STATE_DAWN_FULL_CLOSE_TIMER_RUNNING = -6

# --- Definition of all known internal lock states --------------------------
class LockState(IntEnum):
    """Enum for the possible states of the lock."""
    LOCKSTATE__UNLOCKED = 0
    LOCKSTATE__LOCKED_MANUALLY = 1
    LOCKSTATE__LOCKED_MANUALLY_WITH_FORCED_POSITION = 2
    LOCKSTATE__LOCKED_BY_EXTERNAL_MODIFICATION = 3

# --- Definition of configuration values, how to update lockstate output ----
class UpdateLockStateOutput(IntEnum):
    """Enum for the possible states of the lock."""
    UPDATE_LOCKSTATE_OUTPUT__NEVER = -1
    UPDATE_LOCKSTATE_OUTPUT__ALWAYS = 0
    UPDATE_LOCKSTATE_OUTPUT__ONLY_ON_EXTERNAL_MODIFICATION = 1
    UPDATE_LOCKSTATE_OUTPUT__ONLY_ON_MANUAL_LOCK = 2

# --- Definition of configuration values, how to update position outputs ----
class MovementRestricted(IntEnum):
    """Enum for the possible states of the lock."""
    MOVEMENT_RESTRICTED__NO_RESTRICTION = 0
    MOVEMENT_RESTRICTED__ONLY_DOWN = 1
    MOVEMENT_RESTRICTED__ONLY_UP = 2
