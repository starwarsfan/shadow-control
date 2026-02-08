"""Constants for the Shadow Control integration."""

from enum import Enum, IntEnum

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass

DOMAIN = "shadow_control"
DOMAIN_DATA_MANAGERS = f"{DOMAIN}_managers"  # A good practice for unique keys
DEFAULT_NAME = "Shadow Control"
SC_CONF_COVERS = "covers"  # Constant for 'covers' key within configuration

# Config schema version
VERSION = 5

SC_CONF_NAME = "name"
DEBUG_ENABLED = "debug_enabled"
TARGET_COVER_ENTITY = "target_cover_entity"


class SCInternal(Enum):
    """Instance specific internal Shadow Control entities."""

    ENFORCE_POSITIONING_MANUAL = "enforce_positioning_manual"
    LOCK_INTEGRATION_MANUAL = "lock_integration_manual"
    LOCK_INTEGRATION_WITH_POSITION_MANUAL = "lock_integration_with_position_manual"
    LOCK_HEIGHT_MANUAL = "lock_height_manual"
    LOCK_ANGLE_MANUAL = "lock_angle_manual"
    MOVEMENT_RESTRICTION_HEIGHT_MANUAL = "movement_restriction_height_manual"
    MOVEMENT_RESTRICTION_ANGLE_MANUAL = "movement_restriction_angle_manual"
    NEUTRAL_POS_HEIGHT_MANUAL = "facade_neutral_pos_height_manual"
    NEUTRAL_POS_ANGLE_MANUAL = "facade_neutral_pos_angle_manual"

    SHADOW_CONTROL_ENABLED_MANUAL = "shadow_control_enabled_manual"
    SHADOW_BRIGHTNESS_THRESHOLD_WINTER_MANUAL = "shadow_brightness_threshold_winter_manual"
    SHADOW_BRIGHTNESS_THRESHOLD_SUMMER_MANUAL = "shadow_brightness_threshold_summer_manual"
    SHADOW_BRIGHTNESS_THRESHOLD_MINIMAL_MANUAL = "shadow_brightness_threshold_minimal_manual"
    SHADOW_AFTER_SECONDS_MANUAL = "shadow_after_seconds_manual"
    SHADOW_SHUTTER_MAX_HEIGHT_MANUAL = "shadow_shutter_max_height_manual"
    SHADOW_SHUTTER_MAX_ANGLE_MANUAL = "shadow_shutter_max_angle_manual"
    SHADOW_SHUTTER_LOOK_THROUGH_SECONDS_MANUAL = "shadow_shutter_look_through_seconds_manual"
    SHADOW_SHUTTER_OPEN_SECONDS_MANUAL = "shadow_shutter_open_seconds_manual"
    SHADOW_SHUTTER_LOOK_THROUGH_ANGLE_MANUAL = "shadow_shutter_look_through_angle_manual"
    SHADOW_HEIGHT_AFTER_SUN_MANUAL = "shadow_height_after_sun_manual"
    SHADOW_ANGLE_AFTER_SUN_MANUAL = "shadow_angle_after_sun_manual"

    DAWN_CONTROL_ENABLED_MANUAL = "dawn_control_enabled_manual"
    DAWN_BRIGHTNESS_THRESHOLD_MANUAL = "dawn_brightness_threshold_manual"
    DAWN_AFTER_SECONDS_MANUAL = "dawn_after_seconds_manual"
    DAWN_SHUTTER_MAX_HEIGHT_MANUAL = "dawn_shutter_max_height_manual"
    DAWN_SHUTTER_MAX_ANGLE_MANUAL = "dawn_shutter_max_angle_manual"
    DAWN_SHUTTER_LOOK_THROUGH_SECONDS_MANUAL = "dawn_shutter_look_through_seconds_manual"
    DAWN_SHUTTER_OPEN_SECONDS_MANUAL = "dawn_shutter_open_seconds_manual"
    DAWN_SHUTTER_LOOK_THROUGH_ANGLE_MANUAL = "dawn_shutter_look_through_angle_manual"
    DAWN_HEIGHT_AFTER_DAWN_MANUAL = "dawn_height_after_dawn_manual"
    DAWN_ANGLE_AFTER_DAWN_MANUAL = "dawn_angle_after_dawn_manual"

    @property
    def domain(self) -> str:
        """Handle domain for internal entities."""
        if self in (
            SCInternal.LOCK_INTEGRATION_MANUAL,
            SCInternal.LOCK_INTEGRATION_WITH_POSITION_MANUAL,
            SCInternal.SHADOW_CONTROL_ENABLED_MANUAL,
            SCInternal.DAWN_CONTROL_ENABLED_MANUAL,
        ):
            return "switch"
        if self in (
            SCInternal.MOVEMENT_RESTRICTION_HEIGHT_MANUAL,
            SCInternal.MOVEMENT_RESTRICTION_ANGLE_MANUAL,
        ):
            return "select"
        if self == SCInternal.ENFORCE_POSITIONING_MANUAL:
            return "button"
        if self in (
            SCInternal.LOCK_HEIGHT_MANUAL,
            SCInternal.LOCK_ANGLE_MANUAL,
            SCInternal.NEUTRAL_POS_HEIGHT_MANUAL,
            SCInternal.NEUTRAL_POS_ANGLE_MANUAL,
            SCInternal.SHADOW_BRIGHTNESS_THRESHOLD_WINTER_MANUAL,
            SCInternal.SHADOW_BRIGHTNESS_THRESHOLD_SUMMER_MANUAL,
            SCInternal.SHADOW_BRIGHTNESS_THRESHOLD_MINIMAL_MANUAL,
            SCInternal.SHADOW_AFTER_SECONDS_MANUAL,
            SCInternal.SHADOW_SHUTTER_MAX_HEIGHT_MANUAL,
            SCInternal.SHADOW_SHUTTER_MAX_ANGLE_MANUAL,
            SCInternal.SHADOW_SHUTTER_LOOK_THROUGH_SECONDS_MANUAL,
            SCInternal.SHADOW_SHUTTER_OPEN_SECONDS_MANUAL,
            SCInternal.SHADOW_SHUTTER_LOOK_THROUGH_ANGLE_MANUAL,
            SCInternal.SHADOW_HEIGHT_AFTER_SUN_MANUAL,
            SCInternal.SHADOW_ANGLE_AFTER_SUN_MANUAL,
            SCInternal.DAWN_BRIGHTNESS_THRESHOLD_MANUAL,
            SCInternal.DAWN_AFTER_SECONDS_MANUAL,
            SCInternal.DAWN_SHUTTER_MAX_HEIGHT_MANUAL,
            SCInternal.DAWN_SHUTTER_MAX_ANGLE_MANUAL,
            SCInternal.DAWN_SHUTTER_LOOK_THROUGH_SECONDS_MANUAL,
            SCInternal.DAWN_SHUTTER_OPEN_SECONDS_MANUAL,
            SCInternal.DAWN_SHUTTER_LOOK_THROUGH_ANGLE_MANUAL,
            SCInternal.DAWN_HEIGHT_AFTER_DAWN_MANUAL,
            SCInternal.DAWN_ANGLE_AFTER_DAWN_MANUAL,
        ):
            return "number"
        return "select"  # default/fallback


class SCDynamicInput(Enum):
    """Dynamic configuration input enums."""

    BRIGHTNESS_ENTITY = "brightness_entity"
    BRIGHTNESS_DAWN_ENTITY = "brightness_dawn_entity"
    SUN_ELEVATION_ENTITY = "sun_elevation_entity"
    SUN_AZIMUTH_ENTITY = "sun_azimuth_entity"
    SUNRISE_ENTITY = "sunrise_entity"
    SUNSET_ENTITY = "sunset_entity"
    SHUTTER_CURRENT_HEIGHT_ENTITY = "shutter_current_height_entity"
    SHUTTER_CURRENT_ANGLE_ENTITY = "shutter_current_angle_entity"
    LOCK_INTEGRATION_ENTITY = "lock_integration_entity"
    LOCK_INTEGRATION_WITH_POSITION_ENTITY = "lock_integration_with_position_entity"
    LOCK_HEIGHT_ENTITY = "lock_height_entity"
    LOCK_ANGLE_ENTITY = "lock_angle_entity"
    MOVEMENT_RESTRICTION_HEIGHT_ENTITY = "movement_restriction_height_entity"
    MOVEMENT_RESTRICTION_ANGLE_ENTITY = "movement_restriction_angle_entity"
    ENFORCE_POSITIONING_ENTITY = "enforce_positioning_entity"


class SCFacadeConfig1(Enum):
    """General facade configuration enums, part 1."""

    AZIMUTH_STATIC = "facade_azimuth_static"
    OFFSET_SUN_IN_STATIC = "facade_offset_sun_in_static"
    OFFSET_SUN_OUT_STATIC = "facade_offset_sun_out_static"
    ELEVATION_SUN_MIN_STATIC = "facade_elevation_sun_min_static"
    ELEVATION_SUN_MAX_STATIC = "facade_elevation_sun_max_static"


class SCFacadeConfig2(Enum):
    """General facade configuration enums, part 2."""

    NEUTRAL_POS_HEIGHT_ENTITY = "facade_neutral_pos_height_entity"
    NEUTRAL_POS_ANGLE_ENTITY = "facade_neutral_pos_angle_entity"
    SLAT_WIDTH_STATIC = "facade_slat_width_static"
    SLAT_DISTANCE_STATIC = "facade_slat_distance_static"
    SLAT_ANGLE_OFFSET_STATIC = "facade_slat_angle_offset_static"
    SLAT_MIN_ANGLE_STATIC = "facade_slat_min_angle_static"
    SHUTTER_STEPPING_HEIGHT_STATIC = "facade_shutter_stepping_height_static"
    SHUTTER_STEPPING_ANGLE_STATIC = "facade_shutter_stepping_angle_static"
    SHUTTER_TYPE_STATIC = "facade_shutter_type_static"
    LIGHT_STRIP_WIDTH_STATIC = "facade_light_strip_width_static"
    SHUTTER_HEIGHT_STATIC = "facade_shutter_height_static"
    MAX_MOVEMENT_DURATION_STATIC = "facade_max_movement_duration_static"
    MODIFICATION_TOLERANCE_HEIGHT_STATIC = "facade_modification_tolerance_height_static"
    MODIFICATION_TOLERANCE_ANGLE_STATIC = "facade_modification_tolerance_angle_static"


class SCShadowInput(Enum):
    """Shadow configuration enums."""

    CONTROL_ENABLED_ENTITY = "shadow_control_enabled_entity"
    BRIGHTNESS_THRESHOLD_WINTER_ENTITY = "shadow_brightness_threshold_winter_entity"
    BRIGHTNESS_THRESHOLD_SUMMER_ENTITY = "shadow_brightness_threshold_summer_entity"
    BRIGHTNESS_THRESHOLD_MINIMAL_ENTITY = "shadow_brightness_threshold_minimal_entity"
    AFTER_SECONDS_ENTITY = "shadow_after_seconds_entity"
    SHUTTER_MAX_HEIGHT_ENTITY = "shadow_shutter_max_height_entity"
    SHUTTER_MAX_ANGLE_ENTITY = "shadow_shutter_max_angle_entity"
    SHUTTER_LOOK_THROUGH_SECONDS_ENTITY = "shadow_shutter_look_through_seconds_entity"
    SHUTTER_OPEN_SECONDS_ENTITY = "shadow_shutter_open_seconds_entity"
    SHUTTER_LOOK_THROUGH_ANGLE_ENTITY = "shadow_shutter_look_through_angle_entity"
    HEIGHT_AFTER_SUN_ENTITY = "shadow_height_after_sun_entity"
    ANGLE_AFTER_SUN_ENTITY = "shadow_angle_after_sun_entity"


class SCDawnInput(Enum):
    """Dawn configuration enums."""

    CONTROL_ENABLED_ENTITY = "dawn_control_enabled_entity"
    BRIGHTNESS_THRESHOLD_ENTITY = "dawn_brightness_threshold_entity"
    AFTER_SECONDS_ENTITY = "dawn_after_seconds_entity"
    SHUTTER_MAX_HEIGHT_ENTITY = "dawn_shutter_max_height_entity"
    SHUTTER_MAX_ANGLE_ENTITY = "dawn_shutter_max_angle_entity"
    SHUTTER_LOOK_THROUGH_SECONDS_ENTITY = "dawn_shutter_look_through_seconds_entity"
    SHUTTER_OPEN_SECONDS_ENTITY = "dawn_shutter_open_seconds_entity"
    SHUTTER_LOOK_THROUGH_ANGLE_ENTITY = "dawn_shutter_look_through_angle_entity"
    HEIGHT_AFTER_DAWN_ENTITY = "dawn_height_after_dawn_entity"
    ANGLE_AFTER_DAWN_ENTITY = "dawn_angle_after_dawn_entity"


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
        """Return the value for usage with selection (not translated)."""
        return self.value

    @classmethod
    def from_ha_state_string(cls, state_string: str) -> "MovementRestricted":
        """Convert HA state string back to enum member."""
        # Versuche direkt als value
        for member in cls:
            if member.value == state_string:
                return member

        # Versuche als name (z.B. "NO_RESTRICTION")
        try:
            return cls[state_string.upper()]
        except KeyError:
            pass

        # Fallback
        return cls.NO_RESTRICTION


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
    BRIGHTNESS_THRESHOLD_ACTIVE = "brightness_threshold_active"


class SCDefaults(Enum):
    """Enum for the Moving Colors default values."""

    LOCK_HEIGHT_VALUE = 0
    LOCK_ANGLE_VALUE = 0  # noqa: PIE796
    MAX_MOVEMENT_DURATION_VALUE = 30
    MODIFICATION_TOLERANCE_HEIGHT_STATIC = 3
    MODIFICATION_TOLERANCE_ANGLE_STATIC = 3  # noqa: PIE796
    NEUTRAL_POS_HEIGHT_VALUE = 0  # noqa: PIE796
    NEUTRAL_POS_ANGLE_VALUE = 0  # noqa: PIE796
    SHADOW_BRIGHTNESS_THRESHOLD_WINTER_VALUE = 30000
    SHADOW_BRIGHTNESS_THRESHOLD_SUMMER_VALUE = 50000
    SHADOW_BRIGHTNESS_THRESHOLD_MINIMAL_VALUE = 20000
    SHADOW_AFTER_SECONDS_VALUE = 15
    SHADOW_SHUTTER_MAX_HEIGHT_VALUE = 100
    SHADOW_SHUTTER_MAX_ANGLE_VALUE = 100  # noqa: PIE796
    SHADOW_SHUTTER_LOOK_THROUGH_SECONDS_VALUE = 15  # noqa: PIE796
    SHADOW_SHUTTER_OPEN_SECONDS_VALUE = 15  # noqa: PIE796
    SHADOW_SHUTTER_LOOK_THROUGH_ANGLE_VALUE = 50
    SHADOW_HEIGHT_AFTER_SUN_VALUE = 0  # noqa: PIE796
    SHADOW_ANGLE_AFTER_SUN_VALUE = 0  # noqa: PIE796
    DAWN_BRIGHTNESS_THRESHOLD_VALUE = 500
    DAWN_AFTER_SECONDS_VALUE = 15  # noqa: PIE796
    DAWN_SHUTTER_MAX_HEIGHT_VALUE = 100  # noqa: PIE796
    DAWN_SHUTTER_MAX_ANGLE_VALUE = 100  # noqa: PIE796
    DAWN_SHUTTER_LOOK_THROUGH_SECONDS_VALUE = 15  # noqa: PIE796
    DAWN_SHUTTER_OPEN_SECONDS_VALUE = 15  # noqa: PIE796
    DAWN_SHUTTER_LOOK_THROUGH_ANGLE_VALUE = 50  # noqa: PIE796
    DAWN_HEIGHT_AFTER_DAWN_VALUE = 0  # noqa: PIE796
    DAWN_ANGLE_AFTER_DAWN_VALUE = 0  # noqa: PIE796


INTERNAL_TO_DEFAULTS_MAP = {
    SCInternal.LOCK_HEIGHT_MANUAL: SCDefaults.LOCK_HEIGHT_VALUE.value,
    SCInternal.LOCK_ANGLE_MANUAL: SCDefaults.LOCK_ANGLE_VALUE.value,
    SCInternal.NEUTRAL_POS_HEIGHT_MANUAL: SCDefaults.NEUTRAL_POS_HEIGHT_VALUE.value,
    SCInternal.NEUTRAL_POS_ANGLE_MANUAL: SCDefaults.NEUTRAL_POS_ANGLE_VALUE.value,
    SCInternal.SHADOW_BRIGHTNESS_THRESHOLD_WINTER_MANUAL: SCDefaults.SHADOW_BRIGHTNESS_THRESHOLD_WINTER_VALUE.value,
    SCInternal.SHADOW_BRIGHTNESS_THRESHOLD_SUMMER_MANUAL: SCDefaults.SHADOW_BRIGHTNESS_THRESHOLD_SUMMER_VALUE.value,
    SCInternal.SHADOW_BRIGHTNESS_THRESHOLD_MINIMAL_MANUAL: SCDefaults.SHADOW_BRIGHTNESS_THRESHOLD_MINIMAL_VALUE.value,
    SCInternal.SHADOW_AFTER_SECONDS_MANUAL: SCDefaults.SHADOW_AFTER_SECONDS_VALUE.value,
    SCInternal.SHADOW_SHUTTER_MAX_HEIGHT_MANUAL: SCDefaults.SHADOW_SHUTTER_MAX_HEIGHT_VALUE.value,
    SCInternal.SHADOW_SHUTTER_MAX_ANGLE_MANUAL: SCDefaults.SHADOW_SHUTTER_MAX_ANGLE_VALUE.value,
    SCInternal.SHADOW_SHUTTER_LOOK_THROUGH_SECONDS_MANUAL: SCDefaults.SHADOW_SHUTTER_LOOK_THROUGH_SECONDS_VALUE.value,
    SCInternal.SHADOW_SHUTTER_OPEN_SECONDS_MANUAL: SCDefaults.SHADOW_SHUTTER_OPEN_SECONDS_VALUE.value,
    SCInternal.SHADOW_SHUTTER_LOOK_THROUGH_ANGLE_MANUAL: SCDefaults.SHADOW_SHUTTER_LOOK_THROUGH_ANGLE_VALUE.value,
    SCInternal.SHADOW_HEIGHT_AFTER_SUN_MANUAL: SCDefaults.SHADOW_HEIGHT_AFTER_SUN_VALUE.value,
    SCInternal.SHADOW_ANGLE_AFTER_SUN_MANUAL: SCDefaults.SHADOW_ANGLE_AFTER_SUN_VALUE.value,
    SCInternal.DAWN_BRIGHTNESS_THRESHOLD_MANUAL: SCDefaults.DAWN_BRIGHTNESS_THRESHOLD_VALUE.value,
    SCInternal.DAWN_AFTER_SECONDS_MANUAL: SCDefaults.DAWN_AFTER_SECONDS_VALUE.value,
    SCInternal.DAWN_SHUTTER_MAX_HEIGHT_MANUAL: SCDefaults.DAWN_SHUTTER_MAX_HEIGHT_VALUE.value,
    SCInternal.DAWN_SHUTTER_MAX_ANGLE_MANUAL: SCDefaults.DAWN_SHUTTER_MAX_ANGLE_VALUE.value,
    SCInternal.DAWN_SHUTTER_LOOK_THROUGH_SECONDS_MANUAL: SCDefaults.DAWN_SHUTTER_LOOK_THROUGH_SECONDS_VALUE.value,
    SCInternal.DAWN_SHUTTER_OPEN_SECONDS_MANUAL: SCDefaults.DAWN_SHUTTER_OPEN_SECONDS_VALUE.value,
    SCInternal.DAWN_SHUTTER_LOOK_THROUGH_ANGLE_MANUAL: SCDefaults.DAWN_SHUTTER_LOOK_THROUGH_ANGLE_VALUE.value,
    SCInternal.DAWN_HEIGHT_AFTER_DAWN_MANUAL: SCDefaults.DAWN_HEIGHT_AFTER_DAWN_VALUE.value,
    SCInternal.DAWN_ANGLE_AFTER_DAWN_MANUAL: SCDefaults.DAWN_ANGLE_AFTER_DAWN_VALUE.value,
}

NUMBER_INTERNAL_TO_EXTERNAL_MAP = {
    SCInternal.LOCK_HEIGHT_MANUAL.value: SCDynamicInput.LOCK_HEIGHT_ENTITY.value,
    SCInternal.LOCK_ANGLE_MANUAL.value: SCDynamicInput.LOCK_ANGLE_ENTITY.value,
    SCInternal.NEUTRAL_POS_HEIGHT_MANUAL.value: SCFacadeConfig2.NEUTRAL_POS_HEIGHT_ENTITY.value,
    SCInternal.NEUTRAL_POS_ANGLE_MANUAL.value: SCFacadeConfig2.NEUTRAL_POS_ANGLE_ENTITY.value,
    SCInternal.SHADOW_BRIGHTNESS_THRESHOLD_WINTER_MANUAL.value: SCShadowInput.BRIGHTNESS_THRESHOLD_WINTER_ENTITY.value,
    SCInternal.SHADOW_BRIGHTNESS_THRESHOLD_SUMMER_MANUAL.value: SCShadowInput.BRIGHTNESS_THRESHOLD_SUMMER_ENTITY.value,
    SCInternal.SHADOW_BRIGHTNESS_THRESHOLD_MINIMAL_MANUAL.value: SCShadowInput.BRIGHTNESS_THRESHOLD_MINIMAL_ENTITY.value,
    SCInternal.SHADOW_AFTER_SECONDS_MANUAL.value: SCShadowInput.AFTER_SECONDS_ENTITY.value,
    SCInternal.SHADOW_SHUTTER_MAX_HEIGHT_MANUAL.value: SCShadowInput.SHUTTER_MAX_HEIGHT_ENTITY.value,
    SCInternal.SHADOW_SHUTTER_MAX_ANGLE_MANUAL.value: SCShadowInput.SHUTTER_MAX_ANGLE_ENTITY.value,
    SCInternal.SHADOW_SHUTTER_LOOK_THROUGH_SECONDS_MANUAL.value: SCShadowInput.SHUTTER_LOOK_THROUGH_SECONDS_ENTITY.value,
    SCInternal.SHADOW_SHUTTER_OPEN_SECONDS_MANUAL.value: SCShadowInput.SHUTTER_OPEN_SECONDS_ENTITY.value,
    SCInternal.SHADOW_SHUTTER_LOOK_THROUGH_ANGLE_MANUAL.value: SCShadowInput.SHUTTER_LOOK_THROUGH_ANGLE_ENTITY.value,
    SCInternal.SHADOW_HEIGHT_AFTER_SUN_MANUAL.value: SCShadowInput.HEIGHT_AFTER_SUN_ENTITY.value,
    SCInternal.SHADOW_ANGLE_AFTER_SUN_MANUAL.value: SCShadowInput.ANGLE_AFTER_SUN_ENTITY.value,
    SCInternal.DAWN_BRIGHTNESS_THRESHOLD_MANUAL.value: SCDawnInput.BRIGHTNESS_THRESHOLD_ENTITY.value,
    SCInternal.DAWN_AFTER_SECONDS_MANUAL.value: SCDawnInput.AFTER_SECONDS_ENTITY.value,
    SCInternal.DAWN_SHUTTER_MAX_HEIGHT_MANUAL.value: SCDawnInput.SHUTTER_MAX_HEIGHT_ENTITY.value,
    SCInternal.DAWN_SHUTTER_MAX_ANGLE_MANUAL.value: SCDawnInput.SHUTTER_MAX_ANGLE_ENTITY.value,
    SCInternal.DAWN_SHUTTER_LOOK_THROUGH_SECONDS_MANUAL.value: SCDawnInput.SHUTTER_LOOK_THROUGH_SECONDS_ENTITY.value,
    SCInternal.DAWN_SHUTTER_OPEN_SECONDS_MANUAL.value: SCDawnInput.SHUTTER_OPEN_SECONDS_ENTITY.value,
    SCInternal.DAWN_SHUTTER_LOOK_THROUGH_ANGLE_MANUAL.value: SCDawnInput.SHUTTER_LOOK_THROUGH_ANGLE_ENTITY.value,
    SCInternal.DAWN_HEIGHT_AFTER_DAWN_MANUAL.value: SCDawnInput.HEIGHT_AFTER_DAWN_ENTITY.value,
    SCInternal.DAWN_ANGLE_AFTER_DAWN_MANUAL.value: SCDawnInput.ANGLE_AFTER_DAWN_ENTITY.value,
}

SWITCH_INTERNAL_TO_EXTERNAL_MAP = {
    SCInternal.LOCK_INTEGRATION_MANUAL.value: SCDynamicInput.LOCK_INTEGRATION_ENTITY.value,
    SCInternal.LOCK_INTEGRATION_WITH_POSITION_MANUAL.value: SCDynamicInput.LOCK_INTEGRATION_WITH_POSITION_ENTITY.value,
    SCInternal.SHADOW_CONTROL_ENABLED_MANUAL.value: SCShadowInput.CONTROL_ENABLED_ENTITY.value,
    SCInternal.DAWN_CONTROL_ENABLED_MANUAL.value: SCDawnInput.CONTROL_ENABLED_ENTITY.value,
}

# Switches that should always be created, regardless of external entity configuration
ALWAYS_REQUIRED_SWITCHES = {
    SCInternal.LOCK_INTEGRATION_MANUAL.value,
}

SELECT_INTERNAL_TO_EXTERNAL_MAP = {
    SCInternal.MOVEMENT_RESTRICTION_HEIGHT_MANUAL.value: SCDynamicInput.MOVEMENT_RESTRICTION_HEIGHT_ENTITY.value,
    SCInternal.MOVEMENT_RESTRICTION_ANGLE_MANUAL.value: SCDynamicInput.MOVEMENT_RESTRICTION_ANGLE_ENTITY.value,
}

EXTERNAL_SENSOR_DEFINITIONS = [
    # Lock control and position values
    {
        "config_key": SCDynamicInput.LOCK_INTEGRATION_ENTITY.value,
        "translation_key": SCDynamicInput.LOCK_INTEGRATION_ENTITY.value,
        "unit": None,
        "state_class": None,
        "icon": "mdi:toggle-switch",
    },
    {
        "config_key": SCDynamicInput.LOCK_INTEGRATION_WITH_POSITION_ENTITY.value,
        "translation_key": SCDynamicInput.LOCK_INTEGRATION_WITH_POSITION_ENTITY.value,
        "unit": None,
        "state_class": None,
        "icon": "mdi:toggle-switch",
    },
    {
        "config_key": SCDynamicInput.LOCK_HEIGHT_ENTITY.value,
        "translation_key": SCDynamicInput.LOCK_HEIGHT_ENTITY.value,
        "unit": "%",
        "state_class": SensorStateClass.MEASUREMENT.value,
        "icon": "mdi:pan-vertical",
    },
    {
        "config_key": SCDynamicInput.LOCK_ANGLE_ENTITY.value,
        "translation_key": SCDynamicInput.LOCK_ANGLE_ENTITY.value,
        "unit": "%",
        "state_class": SensorStateClass.MEASUREMENT.value,
        "icon": "mdi:rotate-3d",
    },
    #
    # Neutral position values
    {
        "config_key": SCFacadeConfig2.NEUTRAL_POS_HEIGHT_ENTITY.value,
        "translation_key": SCFacadeConfig2.NEUTRAL_POS_HEIGHT_ENTITY.value,
        "unit": "%",
        "state_class": SensorStateClass.MEASUREMENT.value,
        "icon": "mdi:pan-vertical",
    },
    {
        "config_key": SCFacadeConfig2.NEUTRAL_POS_ANGLE_ENTITY.value,
        "translation_key": SCFacadeConfig2.NEUTRAL_POS_ANGLE_ENTITY.value,
        "unit": "%",
        "state_class": SensorStateClass.MEASUREMENT.value,
        "icon": "mdi:rotate-3d",
    },
    #
    # Movement restriction sensors
    {
        "config_key": SCDynamicInput.MOVEMENT_RESTRICTION_HEIGHT_ENTITY.value,
        "translation_key": SCDynamicInput.MOVEMENT_RESTRICTION_HEIGHT_ENTITY.value,
        "unit": None,
        "state_class": None,
        "icon": "mdi:state-machine",
    },
    {
        "config_key": SCDynamicInput.MOVEMENT_RESTRICTION_ANGLE_ENTITY.value,
        "translation_key": SCDynamicInput.MOVEMENT_RESTRICTION_ANGLE_ENTITY.value,
        "unit": None,
        "state_class": None,
        "icon": "mdi:state-machine",
    },
    #
    # Sun entities for adaptive brightness calculation
    {
        "config_key": SCDynamicInput.SUNRISE_ENTITY.value,
        "translation_key": SCDynamicInput.SUNRISE_ENTITY.value,
        "unit": None,  # Datetime hat keine Unit
        "state_class": None,
        "device_class": SensorDeviceClass.TIMESTAMP,
        "icon": "mdi:weather-sunset-up",
    },
    {
        "config_key": SCDynamicInput.SUNSET_ENTITY.value,
        "translation_key": SCDynamicInput.SUNSET_ENTITY.value,
        "unit": None,
        "state_class": None,
        "device_class": SensorDeviceClass.TIMESTAMP,
        "icon": "mdi:weather-sunset-down",
    },
    #
    # Shadow control sensor definitions
    {
        "config_key": SCShadowInput.CONTROL_ENABLED_ENTITY.value,
        "translation_key": SCShadowInput.CONTROL_ENABLED_ENTITY.value,
        "unit": None,
        "state_class": None,
        "icon": "mdi:toggle-switch",
    },
    {
        "config_key": SCShadowInput.BRIGHTNESS_THRESHOLD_WINTER_ENTITY.value,
        "translation_key": SCShadowInput.BRIGHTNESS_THRESHOLD_WINTER_ENTITY.value,
        "unit": "lx",
        "state_class": SensorStateClass.MEASUREMENT.value,
        "icon": "mdi:brightness-5",
    },
    {
        "config_key": SCShadowInput.BRIGHTNESS_THRESHOLD_SUMMER_ENTITY.value,
        "translation_key": SCShadowInput.BRIGHTNESS_THRESHOLD_SUMMER_ENTITY.value,
        "unit": "lx",
        "state_class": SensorStateClass.MEASUREMENT.value,
        "icon": "mdi:brightness-6",
    },
    {
        "config_key": SCShadowInput.BRIGHTNESS_THRESHOLD_MINIMAL_ENTITY.value,
        "translation_key": SCShadowInput.BRIGHTNESS_THRESHOLD_MINIMAL_ENTITY.value,
        "unit": "lx",
        "state_class": SensorStateClass.MEASUREMENT.value,
        "icon": "mdi:brightness-4",
    },
    {
        "config_key": SCShadowInput.AFTER_SECONDS_ENTITY.value,
        "translation_key": SCShadowInput.AFTER_SECONDS_ENTITY.value,
        "unit": "s",
        "state_class": SensorStateClass.MEASUREMENT.value,
        "icon": "mdi:timer-sand",
    },
    {
        "config_key": SCShadowInput.SHUTTER_MAX_HEIGHT_ENTITY.value,
        "translation_key": SCShadowInput.SHUTTER_MAX_HEIGHT_ENTITY.value,
        "unit": "%",
        "state_class": SensorStateClass.MEASUREMENT.value,
        "icon": "mdi:pan-vertical",
    },
    {
        "config_key": SCShadowInput.SHUTTER_MAX_ANGLE_ENTITY.value,
        "translation_key": SCShadowInput.SHUTTER_MAX_ANGLE_ENTITY.value,
        "unit": "%",
        "state_class": SensorStateClass.MEASUREMENT.value,
        "icon": "mdi:rotate-3d",
    },
    {
        "config_key": SCShadowInput.SHUTTER_LOOK_THROUGH_SECONDS_ENTITY.value,
        "translation_key": SCShadowInput.SHUTTER_LOOK_THROUGH_SECONDS_ENTITY.value,
        "unit": "s",
        "state_class": SensorStateClass.MEASUREMENT.value,
        "icon": "mdi:timer-sand",
    },
    {
        "config_key": SCShadowInput.SHUTTER_OPEN_SECONDS_ENTITY.value,
        "translation_key": SCShadowInput.SHUTTER_OPEN_SECONDS_ENTITY.value,
        "unit": "s",
        "state_class": SensorStateClass.MEASUREMENT.value,
        "icon": "mdi:timer-sand",
    },
    {
        "config_key": SCShadowInput.SHUTTER_LOOK_THROUGH_ANGLE_ENTITY.value,
        "translation_key": SCShadowInput.SHUTTER_LOOK_THROUGH_ANGLE_ENTITY.value,
        "unit": "%",
        "state_class": SensorStateClass.MEASUREMENT.value,
        "icon": "mdi:rotate-3d",
    },
    {
        "config_key": SCShadowInput.HEIGHT_AFTER_SUN_ENTITY.value,
        "translation_key": SCShadowInput.HEIGHT_AFTER_SUN_ENTITY.value,
        "unit": "%",
        "state_class": SensorStateClass.MEASUREMENT.value,
        "icon": "mdi:pan-vertical",
    },
    {
        "config_key": SCShadowInput.ANGLE_AFTER_SUN_ENTITY.value,
        "translation_key": SCShadowInput.ANGLE_AFTER_SUN_ENTITY.value,
        "unit": "%",
        "state_class": SensorStateClass.MEASUREMENT.value,
        "icon": "mdi:rotate-3d",
    },
    #
    # Dawn control sensor definitions
    {
        "config_key": SCDawnInput.CONTROL_ENABLED_ENTITY.value,
        "translation_key": SCDawnInput.CONTROL_ENABLED_ENTITY.value,
        "unit": None,
        "state_class": None,
        "icon": "mdi:toggle-switch",
    },
    {
        "config_key": SCDawnInput.BRIGHTNESS_THRESHOLD_ENTITY.value,
        "translation_key": SCDawnInput.BRIGHTNESS_THRESHOLD_ENTITY.value,
        "unit": "lx",
        "state_class": SensorStateClass.MEASUREMENT.value,
        "icon": "mdi:brightness-5",
    },
    {
        "config_key": SCDawnInput.AFTER_SECONDS_ENTITY.value,
        "translation_key": SCDawnInput.AFTER_SECONDS_ENTITY.value,
        "unit": "s",
        "state_class": SensorStateClass.MEASUREMENT.value,
        "icon": "mdi:timer-sand",
    },
    {
        "config_key": SCDawnInput.SHUTTER_MAX_HEIGHT_ENTITY.value,
        "translation_key": SCDawnInput.SHUTTER_MAX_HEIGHT_ENTITY.value,
        "unit": "%",
        "state_class": SensorStateClass.MEASUREMENT.value,
        "icon": "mdi:pan-vertical",
    },
    {
        "config_key": SCDawnInput.SHUTTER_MAX_ANGLE_ENTITY.value,
        "translation_key": SCDawnInput.SHUTTER_MAX_ANGLE_ENTITY.value,
        "unit": "%",
        "state_class": SensorStateClass.MEASUREMENT.value,
        "icon": "mdi:rotate-3d",
    },
    {
        "config_key": SCDawnInput.SHUTTER_LOOK_THROUGH_SECONDS_ENTITY.value,
        "translation_key": SCDawnInput.SHUTTER_LOOK_THROUGH_SECONDS_ENTITY.value,
        "unit": "s",
        "state_class": SensorStateClass.MEASUREMENT.value,
        "icon": "mdi:timer-sand",
    },
    {
        "config_key": SCDawnInput.SHUTTER_OPEN_SECONDS_ENTITY.value,
        "translation_key": SCDawnInput.SHUTTER_OPEN_SECONDS_ENTITY.value,
        "unit": "s",
        "state_class": SensorStateClass.MEASUREMENT.value,
        "icon": "mdi:timer-sand",
    },
    {
        "config_key": SCDawnInput.SHUTTER_LOOK_THROUGH_ANGLE_ENTITY.value,
        "translation_key": SCDawnInput.SHUTTER_LOOK_THROUGH_ANGLE_ENTITY.value,
        "unit": "%",
        "state_class": SensorStateClass.MEASUREMENT.value,
        "icon": "mdi:rotate-3d",
    },
    {
        "config_key": SCDawnInput.HEIGHT_AFTER_DAWN_ENTITY.value,
        "translation_key": SCDawnInput.HEIGHT_AFTER_DAWN_ENTITY.value,
        "unit": "%",
        "state_class": SensorStateClass.MEASUREMENT.value,
        "icon": "mdi:pan-vertical",
    },
    {
        "config_key": SCDawnInput.ANGLE_AFTER_DAWN_ENTITY.value,
        "translation_key": SCDawnInput.ANGLE_AFTER_DAWN_ENTITY.value,
        "unit": "%",
        "state_class": SensorStateClass.MEASUREMENT.value,
        "icon": "mdi:rotate-3d",
    },
]

# =============================================================================
# Deprecated Configuration Keys
# =============================================================================
# Keys that are no longer supported but accepted for backward compatibility.
# They will trigger warnings and be ignored during setup.
DEPRECATED_CONFIG_KEYS = {
    # v5 Migration - Adaptive Brightness
    "shadow_brightness_threshold_manual": {
        "replacement": [
            "shadow_brightness_threshold_winter_manual",
            "shadow_brightness_threshold_summer_manual",
        ],
        "deprecated_in": "v5 (Adaptive Brightness)",
        "migration_hint": (
            "Replace with 'shadow_brightness_threshold_winter_manual' and "
            "'shadow_brightness_threshold_summer_manual' in sc_internal_values. "
            "Set both to the same value for static behavior, or different values for adaptive brightness."
        ),
    },
    "shadow_brightness_threshold_entity": {
        "replacement": [
            "shadow_brightness_threshold_winter_entity",
            "shadow_brightness_threshold_summer_entity",
        ],
        "deprecated_in": "v5 (Adaptive Brightness)",
        "migration_hint": (
            "Replace with 'shadow_brightness_threshold_winter_entity' and "
            "'shadow_brightness_threshold_summer_entity'. "
            "Set both to the same entity for static behavior, or different entities for adaptive brightness."
        ),
    },
    # v5 Migration - Deprecated *_static keys (non-facade)
    "lock_integration_static": {
        "replacement": ["lock_integration_manual"],
        "deprecated_in": "v5",
        "migration_hint": "Use 'lock_integration_manual' instead.",
    },
    "lock_integration_with_position_static": {
        "replacement": ["lock_integration_with_position_manual"],
        "deprecated_in": "v5",
        "migration_hint": "Use 'lock_integration_with_position_manual' instead.",
    },
    "lock_height_static": {
        "replacement": ["lock_height_manual"],
        "deprecated_in": "v5",
        "migration_hint": "Use 'lock_height_manual' instead.",
    },
    "lock_angle_static": {
        "replacement": ["lock_angle_manual"],
        "deprecated_in": "v5",
        "migration_hint": "Use 'lock_angle_manual' instead.",
    },
    "movement_restriction_height_static": {
        "replacement": ["movement_restriction_height_manual"],
        "deprecated_in": "v5",
        "migration_hint": "Use 'movement_restriction_height_manual' instead.",
    },
    "movement_restriction_angle_static": {
        "replacement": ["movement_restriction_angle_manual"],
        "deprecated_in": "v5",
        "migration_hint": "Use 'movement_restriction_angle_manual' instead.",
    },
    "facade_neutral_pos_height_static": {
        "replacement": ["facade_neutral_pos_height_manual"],
        "deprecated_in": "v5",
        "migration_hint": "Use 'facade_neutral_pos_height_manual' instead.",
    },
    "facade_neutral_pos_angle_static": {
        "replacement": ["facade_neutral_pos_angle_manual"],
        "deprecated_in": "v5",
        "migration_hint": "Use 'facade_neutral_pos_angle_manual' instead.",
    },
    "shadow_control_enabled_static": {
        "replacement": ["shadow_control_enabled_manual"],
        "deprecated_in": "v5",
        "migration_hint": "Use 'shadow_control_enabled_manual' instead.",
    },
    "shadow_brightness_threshold_static": {
        "replacement": [
            "shadow_brightness_threshold_winter_manual",
            "shadow_brightness_threshold_summer_manual",
        ],
        "deprecated_in": "v5",
        "migration_hint": "Use 'shadow_brightness_threshold_winter_manual' and 'shadow_brightness_threshold_summer_manual' instead.",
    },
    "shadow_after_seconds_static": {
        "replacement": ["shadow_after_seconds_manual"],
        "deprecated_in": "v5",
        "migration_hint": "Use 'shadow_after_seconds_manual' instead.",
    },
    "shadow_shutter_max_height_static": {
        "replacement": ["shadow_shutter_max_height_manual"],
        "deprecated_in": "v5",
        "migration_hint": "Use 'shadow_shutter_max_height_manual' instead.",
    },
    "shadow_shutter_max_angle_static": {
        "replacement": ["shadow_shutter_max_angle_manual"],
        "deprecated_in": "v5",
        "migration_hint": "Use 'shadow_shutter_max_angle_manual' instead.",
    },
    "shadow_shutter_look_through_seconds_static": {
        "replacement": ["shadow_shutter_look_through_seconds_manual"],
        "deprecated_in": "v5",
        "migration_hint": "Use 'shadow_shutter_look_through_seconds_manual' instead.",
    },
    "shadow_shutter_open_seconds_static": {
        "replacement": ["shadow_shutter_open_seconds_manual"],
        "deprecated_in": "v5",
        "migration_hint": "Use 'shadow_shutter_open_seconds_manual' instead.",
    },
    "shadow_shutter_look_through_angle_static": {
        "replacement": ["shadow_shutter_look_through_angle_manual"],
        "deprecated_in": "v5",
        "migration_hint": "Use 'shadow_shutter_look_through_angle_manual' instead.",
    },
    "shadow_height_after_sun_static": {
        "replacement": ["shadow_height_after_sun_manual"],
        "deprecated_in": "v5",
        "migration_hint": "Use 'shadow_height_after_sun_manual' instead.",
    },
    "shadow_angle_after_sun_static": {
        "replacement": ["shadow_angle_after_sun_manual"],
        "deprecated_in": "v5",
        "migration_hint": "Use 'shadow_angle_after_sun_manual' instead.",
    },
    "dawn_control_enabled_static": {
        "replacement": ["dawn_control_enabled_manual"],
        "deprecated_in": "v5",
        "migration_hint": "Use 'dawn_control_enabled_manual' instead.",
    },
    "dawn_brightness_threshold_static": {
        "replacement": ["dawn_brightness_threshold_manual"],
        "deprecated_in": "v5",
        "migration_hint": "Use 'dawn_brightness_threshold_manual' instead.",
    },
    "dawn_after_seconds_static": {
        "replacement": ["dawn_after_seconds_manual"],
        "deprecated_in": "v5",
        "migration_hint": "Use 'dawn_after_seconds_manual' instead.",
    },
    "dawn_shutter_max_height_static": {
        "replacement": ["dawn_shutter_max_height_manual"],
        "deprecated_in": "v5",
        "migration_hint": "Use 'dawn_shutter_max_height_manual' instead.",
    },
    "dawn_shutter_max_angle_static": {
        "replacement": ["dawn_shutter_max_angle_manual"],
        "deprecated_in": "v5",
        "migration_hint": "Use 'dawn_shutter_max_angle_manual' instead.",
    },
    "dawn_shutter_look_through_seconds_static": {
        "replacement": ["dawn_shutter_look_through_seconds_manual"],
        "deprecated_in": "v5",
        "migration_hint": "Use 'dawn_shutter_look_through_seconds_manual' instead.",
    },
    "dawn_shutter_open_seconds_static": {
        "replacement": ["dawn_shutter_open_seconds_manual"],
        "deprecated_in": "v5",
        "migration_hint": "Use 'dawn_shutter_open_seconds_manual' instead.",
    },
    "dawn_shutter_look_through_angle_static": {
        "replacement": ["dawn_shutter_look_through_angle_manual"],
        "deprecated_in": "v5",
        "migration_hint": "Use 'dawn_shutter_look_through_angle_manual' instead.",
    },
    "dawn_height_after_dawn_static": {
        "replacement": ["dawn_height_after_dawn_manual"],
        "deprecated_in": "v5",
        "migration_hint": "Use 'dawn_height_after_dawn_manual' instead.",
    },
    "dawn_angle_after_dawn_static": {
        "replacement": ["dawn_angle_after_dawn_manual"],
        "deprecated_in": "v5",
        "migration_hint": "Use 'dawn_angle_after_dawn_manual' instead.",
    },
    # v2 Migration - Old lock keys
    # Commented out here as they already exist in later versions
    # "lock_height_entity": {
    #     "replacement": ["lock_height_manual"],
    #     "deprecated_in": "v2",
    #     "migration_hint": "Use 'lock_height_manual' instead.",
    # },
    # "lock_angle_entity": {
    #     "replacement": ["lock_angle_manual"],
    #     "deprecated_in": "v2",
    #     "migration_hint": "Use 'lock_angle_manual' instead.",
    # },
}
