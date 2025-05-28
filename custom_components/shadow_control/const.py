"""Constants for the Shadow Control integration."""

from enum import Enum, IntEnum

DOMAIN = "shadow_control"
DOMAIN_DATA_MANAGERS = f"{DOMAIN}_managers" # A good practice for unique keys
DEFAULT_NAME = "Shadow Control"
CONF_COVERS = "covers" # Konstante für den 'covers' Schlüssel in der Konfiguration

#CONF_NAME = "name"

# === Dynamische Eingänge (Test-Helfer) ===
class SCDynamicInput(Enum):
    CONF_BRIGHTNESS_ENTITY_ID = "brightness_entity_id"
    CONF_BRIGHTNESS_DAWN_ENTITY_ID = "brightness_dawn_entity_id"
    CONF_SUN_ELEVATION_ENTITY_ID = "sun_elevation_entity_id"
    CONF_SUN_AZIMUTH_ENTITY_ID = "sun_azimuth_entity_id"
    CONF_SHUTTER_CURRENT_HEIGHT_ENTITY_ID = "shutter_current_height_entity_id"
    CONF_SHUTTER_CURRENT_ANGLE_ENTITY_ID = "shutter_current_angle_entity_id"
    CONF_LOCK_INTEGRATION_ENTITY_ID = "lock_integration_entity_id"
    CONF_LOCK_INTEGRATION_WITH_POSITION_ENTITY_ID = "lock_integration_with_position_entity_id"
    CONF_LOCK_HEIGHT_ENTITY_ID = "lock_height_entity_id"
    CONF_LOCK_ANGLE_ENTITY_ID = "lock_angle_entity_id"
    CONF_MODIFICATION_TOLERANCE_HEIGHT_ENTITY_ID = "modification_tolerance_height_entity_id"
    CONF_MODIFICATION_TOLERANCE_ANGLE_ENTITY_ID = "modification_tolerance_angle_entity_id"

# === Allgemeine Einstellungen (Test-Helfer) ===
class SCConfigurationInput(Enum):
    CONF_FACADE_AZIMUTH_ENTITY_ID = "facade_azimuth_entity_id"
    CONF_FACADE_OFFSET_SUN_IN_ENTITY_ID = "facade_offset_sun_in_entity_id"
    CONF_FACADE_OFFSET_SUN_OUT_ENTITY_ID = "facade_offset_sun_out_entity_id"
    CONF_FACADE_ELEVATION_SUN_MIN_ENTITY_ID = "facade_elevation_sun_min_entity_id"
    CONF_FACADE_ELEVATION_SUN_MAX_ENTITY_ID = "facade_elevation_sun_max_entity_id"
    CONF_FACADE_SLAT_WIDTH_ENTITY_ID = "facade_slat_width_entity_id"
    CONF_FACADE_SLAT_DISTANCE_ENTITY_ID = "facade_slat_distance_entity_id"
    CONF_FACADE_SLAT_ANGLE_OFFSET_ENTITY_ID = "facade_slat_angle_offset_entity_id"
    CONF_FACADE_SLAT_MIN_ANGLE_ENTITY_ID = "facade_slat_min_angle_entity_id"
    CONF_FACADE_SHUTTER_STEPPING_HEIGHT_ENTITY_ID = "facade_shutter_stepping_height_entity_id"
    CONF_FACADE_SHUTTER_STEPPING_ANGLE_ENTITY_ID = "facade_shutter_stepping_angle_entity_id"
    CONF_FACADE_SHUTTER_TYPE_ENTITY_ID = "facade_shutter_type_entity_id"
    CONF_FACADE_LIGHT_STRIP_WIDTH_ENTITY_ID = "facade_light_strip_width_entity_id"
    CONF_FACADE_SHUTTER_HEIGHT_ENTITY_ID = "facade_shutter_height_entity_id"
    CONF_FACADE_NEUTRAL_POS_HEIGHT_ENTITY_ID = "facade_neutral_pos_height_entity_id"
    CONF_FACADE_NEUTRAL_POS_ANGLE_ENTITY_ID = "facade_neutral_pos_angle_entity_id"
    CONF_FACADE_MOVEMENT_RESTRICTION_HEIGHT_ENTITY_ID = "facade_movement_restriction_height_entity_id"
    CONF_FACADE_MOVEMENT_RESTRICTION_ANGLE_ENTITY_ID = "facade_movement_restriction_angle_entity_id"
    CONF_FACADE_UPDATE_LOCK_OUTPUT_ENTITY_ID = "facade_update_lock_output_entity_id"

# === Beschattungseinstellungen (Test-Helfer) ===
class SCShadowInput(Enum):
    CONF_SHADOW_CONTROL_ENABLED_ENTITY_ID = "shadow_control_enabled_entity_id"
    CONF_SHADOW_BRIGHTNESS_THRESHOLD_ENTITY_ID = "shadow_brightness_threshold_entity_id"
    CONF_SHADOW_AFTER_SECONDS_ENTITY_ID = "shadow_after_seconds_entity_id"
    CONF_SHADOW_SHUTTER_MAX_HEIGHT_ENTITY_ID = "shadow_shutter_max_height_entity_id"
    CONF_SHADOW_SHUTTER_MAX_ANGLE_ENTITY_ID = "shadow_shutter_max_angle_entity_id"
    CONF_SHADOW_SHUTTER_LOOK_THROUGH_SECONDS_ENTITY_ID = "shadow_shutter_look_through_seconds_entity_id"
    CONF_SHADOW_SHUTTER_OPEN_SECONDS_ENTITY_ID = "shadow_shutter_open_seconds_entity_id"
    CONF_SHADOW_SHUTTER_LOOK_THROUGH_ANGLE_ENTITY_ID = "shadow_shutter_look_through_angle_entity_id"
    CONF_SHADOW_HEIGHT_AFTER_SUN_ENTITY_ID = "shadow_height_after_sun_entity_id"
    CONF_SHADOW_ANGLE_AFTER_SUN_ENTITY_ID = "shadow_angle_after_sun_entity_id"

# === Dämmerungseinstellungen (Test-Helfer) ===
class SCDawnInput(Enum):
    CONF_DAWN_CONTROL_ENABLED_ENTITY_ID = "dawn_control_enabled_entity_id"
    CONF_DAWN_BRIGHTNESS_THRESHOLD_ENTITY_ID = "dawn_brightness_threshold_entity_id"
    CONF_DAWN_AFTER_SECONDS_ENTITY_ID = "dawn_after_seconds_entity_id"
    CONF_DAWN_SHUTTER_MAX_HEIGHT_ENTITY_ID = "dawn_shutter_max_height_entity_id"
    CONF_DAWN_SHUTTER_MAX_ANGLE_ENTITY_ID = "dawn_shutter_max_angle_entity_id"
    CONF_DAWN_SHUTTER_LOOK_THROUGH_SECONDS_ENTITY_ID = "dawn_shutter_look_through_seconds_entity_id"
    CONF_DAWN_SHUTTER_OPEN_SECONDS_ENTITY_ID = "dawn_shutter_open_seconds_entity_id"
    CONF_DAWN_SHUTTER_LOOK_THROUGH_ANGLE_ENTITY_ID = "dawn_shutter_look_through_angle_entity_id"
    CONF_DAWN_HEIGHT_AFTER_DAWN_ENTITY_ID = "dawn_height_after_dawn_entity_id"
    CONF_DAWN_ANGLE_AFTER_DAWN_ENTITY_ID = "dawn_angle_after_dawn_entity_id"

CONF_DEBUG_ENABLED = "debug_enabled"  # Für den Debug-Schalter
CONF_TARGET_COVER_ENTITY_ID = "target_cover_entity_id"

# --- Status Konstanten für die Behangsteuerung -----------------------------
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

# --- Definition of all known internal lock states --------------------------
class LockState(IntEnum):
    """Enum for the possible states of the lock."""
    UNLOCKED = 0
    LOCKED_MANUALLY = 1
    LOCKED_MANUALLY_WITH_FORCED_POSITION = 2
    LOCKED_BY_EXTERNAL_MODIFICATION = 3

# --- Definition of configuration values, how to update lockstate output ----
class UpdateLockStateOutput(IntEnum):
    """Enum for the possible states of the lock."""
    UPDATE_LOCKSTATE_OUTPUT__NEVER = -1
    UPDATE_LOCKSTATE_OUTPUT__ALWAYS = 0
    UPDATE_LOCKSTATE_OUTPUT__ONLY_ON_EXTERNAL_MODIFICATION = 1
    UPDATE_LOCKSTATE_OUTPUT__ONLY_ON_MANUAL_LOCK = 2

# --- Definition of configuration values, how to update position outputs ----
class MovementRestricted(Enum):
    """Enum for the possible movement restrictions."""
    NO_RESTRICTION = "No restriction"
    ONLY_CLOSE = "Only close"
    ONLY_OPEN = "Only open"
