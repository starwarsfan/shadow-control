"""Integration for Shadow Control."""

import logging
import math
import re
from datetime import UTC, datetime, timedelta
from enum import Enum
from functools import partial
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.components.cover import CoverEntityFeature
from homeassistant.config_entries import ConfigEntries, ConfigEntry
from homeassistant.const import (
    ATTR_SUPPORTED_FEATURES,
    EVENT_HOMEASSISTANT_STARTED,
    STATE_ON,
    Platform,
)
from homeassistant.core import Event, HomeAssistant, ServiceCall, State, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.helpers.event import async_call_later, async_track_state_change_event
from homeassistant.helpers.typing import ConfigType

from .const import (
    DEBUG_ENABLED,
    DOMAIN,
    DOMAIN_DATA_MANAGERS,
    FULL_OPTIONS_SCHEMA,
    SC_CONF_NAME,
    TARGET_COVER_ENTITY_ID,
    VERSION,
    YAML_CONFIG_SCHEMA,
    LockState,
    MovementRestricted,
    SCDawnInput,
    SCDynamicInput,
    SCFacadeConfig,
    SCShadowInput,
    ShutterState,
    ShutterType,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

_GLOBAL_DOMAIN_LOGGER = logging.getLogger(DOMAIN)
_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH]

SERVICE_DUMP_CONFIG = "dump_sc_configuration"

# Get the schema version from constants
CURRENT_SCHEMA_VERSION = VERSION

CONFIG_SCHEMA = vol.Schema(
    {
        # Allow multiple instances below the domain key
        DOMAIN: vol.All(cv.ensure_list, [YAML_CONFIG_SCHEMA])
    },
    extra=vol.ALLOW_EXTRA,  # Allow different sections within configuration.yaml
)


# Setup entry point, which is called at every start of Home Assistant.
# Not specific for config entries.
async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Shadow Control integration."""
    _LOGGER.debug("[%s] async_setup called.", DOMAIN)

    # Placeholder for all data of this integration within 'hass.data'.
    # Will be used to store things like the ShadowControlManager instances.
    # hass.data[DOMAIN_DATA_MANAGERS] will be a dictionary to map ConfigEntry
    # IDs to manager instances.
    hass.data.setdefault(DOMAIN_DATA_MANAGERS, {})

    if DOMAIN in config:
        for entry_config in config[DOMAIN]:
            # Import YAML configuration into ConfigEntry, separated the same way than
            # on the ConfigFlow: Name in 'data', rest in 'options'

            # Remove name from YAML configuration
            instance_name = entry_config.pop(SC_CONF_NAME)

            hass.async_create_task(
                hass.config_entries.flow.async_init(
                    DOMAIN,
                    context={"source": "import"},
                    data={
                        SC_CONF_NAME: instance_name,  # Name into the 'data' section
                        # Pass the dictionary which contains the options for the
                        # ConfigEntry. YAML content without a name will be options
                        **entry_config,
                    },
                )
            )

    _LOGGER.info("[%s] Integration 'Shadow Control' base setup complete.", DOMAIN)
    return True


# Entry point for setup using ConfigEntry (via ConfigFlow)
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Shadow Control from a config entry."""
    _LOGGER.debug("[%s] Setting up Shadow Control from config entry: %s: data=%s, options=%s", DOMAIN, entry.entry_id, entry.data, entry.options)

    # Most reliable way to store the 'name',
    # as it will be set as 'title' during the creation of an entry.
    manager_name = entry.title

    # Combined entry-data and entry.options for the configuration of the manager.
    # 'Options' overwrite 'data', if their key is identical.
    config_data = {**entry.data, **entry.options}

    instance_name = config_data[SC_CONF_NAME]
    if not instance_name:
        _LOGGER.error("Instance name not found within configuration data.")
        return False

    # Sanitize logger instance name
    # 1. Replace spaces with underscores
    # 2. All lowercase
    # 3. Remove all characters that are not alphanumeric or underscores
    sanitized_instance_name = re.sub(r"\s+", "_", instance_name).lower()
    sanitized_instance_name = re.sub(r"[^a-z0-9_]", "", sanitized_instance_name)

    # Prevent empty name if there were only special characters used
    if not sanitized_instance_name:
        _LOGGER.warning("Sanitized logger instance name would be empty, using entry_id as fallback for: '%s'", instance_name)
        sanitized_instance_name = entry.entry_id

    instance_logger_name = f"{DOMAIN}.{sanitized_instance_name}"
    instance_specific_logger = logging.getLogger(instance_logger_name)

    if entry.options.get(DEBUG_ENABLED, False):
        instance_specific_logger.setLevel(logging.DEBUG)
        instance_specific_logger.debug("Debug log for instance '%s' activated.", instance_name)
    else:
        instance_specific_logger.setLevel(logging.INFO)
        instance_specific_logger.debug("Debug log for instance '%s' disabled.", instance_name)

    # The manager can't work without a configuration.
    if not config_data:
        _LOGGER.error(
            "[%s] Config data (entry.data + entry.options) is empty for entry %s during setup/reload. This means no configuration could be loaded.",
            manager_name,
            entry.entry_id,
        )
        return False

    # The cover to handle with this integration
    target_cover_entity_id = config_data.get(TARGET_COVER_ENTITY_ID)

    if not manager_name:
        _LOGGER.error(
            "[%s] No manager name found (entry.title was empty) for entry %s. This should not happen and indicates a deeper problem.",
            DOMAIN,
            entry.entry_id,
        )
        return False

    if not target_cover_entity_id:
        _LOGGER.error("[%s] No target cover entity ID found in config for entry %s.", manager_name, entry.entry_id)
        return False

    # Hand over the combined configuration dictionary to the ShadowControlManager
    manager = ShadowControlManager(hass, config_data, entry.entry_id, instance_specific_logger)

    # Store manager within 'hass.data' to let sensors and other components access it.
    if DOMAIN_DATA_MANAGERS not in hass.data:
        hass.data[DOMAIN_DATA_MANAGERS] = {}
    hass.data[DOMAIN_DATA_MANAGERS][entry.entry_id] = manager
    _LOGGER.debug("[%s] Shadow Control manager stored for entry %s in %s.", manager_name, entry.entry_id, DOMAIN_DATA_MANAGERS)

    # Initial start of the manager
    await manager.async_start()

    # Load platforms (like sensors)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Add listeners for update of input values and integration trigger
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    # Add service to dump instance configuration
    if not hass.services.has_service(DOMAIN, SERVICE_DUMP_CONFIG):
        instance_names_from_config = [
            entry.data[SC_CONF_NAME]  # Verwenden Sie SC_CONF_NAME für den Schlüssel 'name'
            for entry in hass.config_entries.async_entries(DOMAIN)
            if SC_CONF_NAME in entry.data
        ]

        dropdown_options = []
        default_selection = ""

        if instance_names_from_config:
            # Instances found
            # Sort them and use the first as default
            dropdown_options = sorted(instance_names_from_config)
            default_selection = dropdown_options[0]
        else:
            # Fallback if no configured instances found.
            default_selection = "No instance configured"
            dropdown_options.append(default_selection)
            _LOGGER.warning(
                "[%s] No Shadow Control instances configured. The service 'dump_sc_configuration' "
                "might not be fully functional without such a instance.",
                DOMAIN,
            )

        service_dump_config_schema = vol.Schema(
            {
                vol.Optional(
                    SC_CONF_NAME, default=default_selection, description="Name of Shadow Control instance, which configuration should be dumped."
                ): vol.In(dropdown_options),
            }
        )

        hass.services.async_register(
            DOMAIN,
            SERVICE_DUMP_CONFIG,
            partial(handle_dump_config_service, hass, hass.config_entries),
            schema=service_dump_config_schema,
        )

    _LOGGER.info("[%s] Integration '%s' successfully set up from config entry.", DOMAIN, manager_name)
    return True


# Entry point to unload a ConfigEntry
async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("[%s] Unloading Shadow Control integration for entry: %s", DOMAIN, entry.entry_id)

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if not hass.data.get(DOMAIN_DATA_MANAGERS) or len(hass.data.get(DOMAIN_DATA_MANAGERS)) == 1:  # Prüfen, ob dies die letzte Manager-Instanz ist
        hass.services.async_remove(DOMAIN, SERVICE_DUMP_CONFIG)

    if unload_ok:
        # Stop manager instance
        manager: ShadowControlManager = hass.data[DOMAIN_DATA_MANAGERS].pop(entry.entry_id, None)
        if manager:
            await manager.async_stop()

        _LOGGER.info("[%s] Shadow Control integration for entry %s successfully unloaded.", DOMAIN, entry.entry_id)
    else:
        _LOGGER.error("[%s] Failed to unload platforms for entry %s.", DOMAIN, entry.entry_id)

    return unload_ok


async def handle_dump_config_service(hass: HomeAssistant, config_entries: ConfigEntries, call: ServiceCall) -> None:
    """Handle the service call to dump instance configuration."""
    instance_name = call.data.get(SC_CONF_NAME)
    _LOGGER.debug("Received dump_config service call for instance: %s", instance_name)

    manager: ShadowControlManager | None = None
    target_config_entry_id: str | None = None

    # Find the Manager by instance name or config_entry_id
    for entry_id, mgr in hass.data.get(DOMAIN_DATA_MANAGERS, {}).items():
        if mgr.name == instance_name:
            manager = mgr
            target_config_entry_id = entry_id
            break

    if manager is None:
        _LOGGER.error("[%s] dump_config service: No manager found for instance name '%s'", DOMAIN, instance_name)
        return

    _LOGGER.info("[%s] --- DUMPING INSTANCE CONFIGURATION - START ---", manager.name)

    # 1. Config entry options
    config_entry = hass.config_entries.async_get_entry(target_config_entry_id)
    if config_entry:
        _LOGGER.info("[%s] Config Entry Data: %s", manager.name, dict(config_entry.data))
        _LOGGER.info("[%s] Config Entry Options: %s", manager.name, dict(config_entry.options))
    else:
        _LOGGER.warning("[%s] No config entry found for instance %s", manager.name, instance_name)

    # 2. Manager internal configuration
    # if hasattr(manager, "_config"):
    #    _LOGGER.info("[%s] Manager Internal Config: %s", manager.name, manager._config)

    entity_registry = async_get_entity_registry(hass)

    # Find the device, to get all its entities
    dev_reg = device_registry.async_get(hass)
    device = dev_reg.async_get_device({(DOMAIN, target_config_entry_id)})

    if device:
        _LOGGER.info("[%s] Associated Device: %s (id: %s)", manager.name, device.name, device.id)
        _LOGGER.info("[%s] Associated Entities:", manager.name)
        entities_for_device = [entry for entry in entity_registry.entities.values() if entry.device_id == device.id]
        for entity_entry in entities_for_device:
            state = hass.states.get(entity_entry.entity_id)
            if state:
                _LOGGER.info("[%s] - %s: State='%s', Attributes=%s", manager.name, entity_entry.entity_id, state.state, dict(state.attributes))
            else:
                _LOGGER.info("[%s] - %s: Not available or no state", manager.name, entity_entry.entity_id)
    else:
        _LOGGER.warning("[%s] No device found for config entry ID %s. Cannot dump associated entities.", manager.name, target_config_entry_id)

    _LOGGER.info("[%s] --- DUMPING INSTANCE CONFIGURATION - END ---", manager.name)


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old config entry."""
    _LOGGER.debug(
        "[%s] Migrating config entry '%s' from version %s to %s", DOMAIN, config_entry.entry_id, config_entry.version, CURRENT_SCHEMA_VERSION
    )

    new_data = config_entry.data.copy()
    new_options = config_entry.options.copy()

    if config_entry.version == 1:
        old_lock_height_key = "lock_height_entity"
        old_lock_angle_key = "lock_angle_entity"

        lock_height_static_key = SCDynamicInput.LOCK_HEIGHT_STATIC.value
        lock_angle_static_key = SCDynamicInput.LOCK_ANGLE_STATIC.value

        if old_lock_height_key in new_options:
            new_options[lock_height_static_key] = new_options.pop(old_lock_height_key)
            _LOGGER.debug("[%s] Migrated: Renamed '%s' to '%s'.", DOMAIN, old_lock_height_key, lock_height_static_key)
        elif lock_height_static_key not in new_options:
            new_options[lock_height_static_key] = 0
            _LOGGER.debug("[%s] Set default value for '%s'.", DOMAIN, lock_height_static_key)

        if old_lock_angle_key in new_options:
            new_options[lock_angle_static_key] = new_options.pop(old_lock_angle_key)
            _LOGGER.debug("[%s] Migrated: Renamed '%s' to '%s'.", DOMAIN, old_lock_angle_key, lock_angle_static_key)
        elif lock_angle_static_key not in new_options:
            new_options[lock_angle_static_key] = 0
            _LOGGER.debug("[%s] Set default value for '%s'.", DOMAIN, lock_angle_static_key)

        try:
            validated_options = FULL_OPTIONS_SCHEMA(new_options)
            _LOGGER.debug("[%s] Migrated options successfully validated. Result: %s", DOMAIN, validated_options)
            _LOGGER.debug("[%s] Type of validated_options: %s", DOMAIN, type(validated_options))
        except vol.Invalid:
            _LOGGER.exception(
                "[%s] Validation failed after migration to version %s for entry %s", DOMAIN, CURRENT_SCHEMA_VERSION, config_entry.entry_id
            )
            return False

        _LOGGER.debug("[%s] Preparing to call hass.config_entries.async_update_entry with:", DOMAIN)
        _LOGGER.debug("[%s]   Arg 'config_entry' type: %s", DOMAIN, type(config_entry))
        _LOGGER.debug("[%s]   Arg 'data' type: %s, value: %s", DOMAIN, type(new_data), new_data)
        _LOGGER.debug("[%s]   Arg 'options' type: %s, value: %s", DOMAIN, type(validated_options), validated_options)
        _LOGGER.debug("[%s]   Arg 'version' type: %s, value: %s", DOMAIN, type(CURRENT_SCHEMA_VERSION), CURRENT_SCHEMA_VERSION)

        hass.config_entries.async_update_entry(config_entry, data=new_data, options=validated_options, version=CURRENT_SCHEMA_VERSION)
        _LOGGER.info("[%s] Config entry '%s' successfully migrated to version %s.", DOMAIN, config_entry.entry_id, CURRENT_SCHEMA_VERSION)
        return True

    if config_entry.version == 2:
        # Migrate SHUTTER_TYPE_STATIC from config options to config data

        if SCFacadeConfig.SHUTTER_TYPE_STATIC.value in new_options:
            new_data[SCFacadeConfig.SHUTTER_TYPE_STATIC.value] = new_options.pop(SCFacadeConfig.SHUTTER_TYPE_STATIC.value)
            _LOGGER.debug(
                "[%s] Migrated: Moved shutter type '%s' from config options to config data.",
                DOMAIN,
                new_data[SCFacadeConfig.SHUTTER_TYPE_STATIC.value],
            )

        try:
            validated_options = FULL_OPTIONS_SCHEMA(new_options)
            _LOGGER.debug("[%s] Migrated configuration successfully validated. Result: %s", DOMAIN, validated_options)
            _LOGGER.debug("[%s] Type of validated_options: %s", DOMAIN, type(validated_options))
        except vol.Invalid:
            _LOGGER.exception(
                "[%s] Validation failed after migration to version %s for entry %s", DOMAIN, CURRENT_SCHEMA_VERSION, config_entry.entry_id
            )
            return False

        _LOGGER.debug("[%s] Preparing to call hass.config_entries.async_update_entry with:", DOMAIN)
        _LOGGER.debug("[%s]   Arg 'config_entry' type: %s", DOMAIN, type(config_entry))
        _LOGGER.debug("[%s]   Arg 'data' type: %s, value: %s", DOMAIN, type(new_data), new_data)
        _LOGGER.debug("[%s]   Arg 'options' type: %s, value: %s", DOMAIN, type(validated_options), validated_options)
        _LOGGER.debug("[%s]   Arg 'version' type: %s, value: %s", DOMAIN, type(CURRENT_SCHEMA_VERSION), CURRENT_SCHEMA_VERSION)

        hass.config_entries.async_update_entry(config_entry, data=new_data, options=validated_options, version=CURRENT_SCHEMA_VERSION)
        _LOGGER.info("[%s] Config entry '%s' successfully migrated to version %s.", DOMAIN, config_entry.entry_id, CURRENT_SCHEMA_VERSION)
        return True

    _LOGGER.error("[%s] Unknown config entry version %s for migration. This should not happen.", DOMAIN, config_entry.version)
    return False


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update. Will be called if the user modifies the configuration using the OptionsFlow."""
    _LOGGER.debug("[%s] Options update listener triggered for entry %s.", DOMAIN, entry.entry_id)
    await hass.config_entries.async_reload(entry.entry_id)


class SCDynamicInputConfiguration:
    """Define defaults for dynamic configuration."""

    def __init__(self) -> None:
        """Define defaults for dynamic configuration."""
        self.brightness: float = 5000.0
        self.brightness_dawn: float = -1.0
        self.sun_elevation: float = 45.0
        self.sun_azimuth: float = 180.0
        self.shutter_current_height: float = -1.0
        self.shutter_current_angle: float = -1.0
        self.lock_integration: bool = False
        self.lock_integration_with_position: bool = False
        self.lock_height: float = 0.0
        self.lock_angle: float = 0.0
        self.movement_restriction_height: MovementRestricted = MovementRestricted.NO_RESTRICTION
        self.movement_restriction_angle: MovementRestricted = MovementRestricted.NO_RESTRICTION


class SCFacadeConfiguration:
    """Define defaults for facade configuration."""

    def __init__(self) -> None:
        """Define defaults for facade configuration."""
        self.azimuth: float = 180.0
        self.offset_sun_in: float = -90.0
        self.offset_sun_out: float = 90.0
        self.elevation_sun_min: float = 0.0
        self.elevation_sun_max: float = 90.0
        self.slat_width: float = 95.0
        self.slat_distance: float = 67.0
        self.slat_angle_offset: float = 0.0
        self.slat_min_angle: float = 0.0
        self.shutter_stepping_height: float = 5.0
        self.shutter_stepping_angle: float = 5.0
        self.shutter_type: ShutterType = ShutterType.MODE1
        self.light_strip_width: float = 0.0
        self.shutter_height: float = 1000.0
        self.neutral_pos_height: float = 0.0
        self.neutral_pos_angle: float = 0.0
        self.modification_tolerance_height: float = 0.0
        self.modification_tolerance_angle: float = 0.0


class SCShadowControlConfig:
    """Define defaults for trigger configuration."""

    def __init__(self) -> None:
        """Define defaults for trigger configuration."""
        self.enabled: bool = True
        self.brightness_threshold: float = 50000.0
        self.after_seconds: float = 15.0
        self.shutter_max_height: float = 100.0
        self.shutter_max_angle: float = 100.0
        self.shutter_look_through_seconds: float = 15.0
        self.shutter_open_seconds: float = 15.0
        self.shutter_look_through_angle: float = 0.0
        self.height_after_sun: float = 0.0
        self.angle_after_sun: float = 0.0


class SCDawnControlConfig:
    """Define defaults for dawn configuration."""

    def __init__(self) -> None:
        """Define defaults for dawn configuration."""
        self.enabled: bool = True
        self.brightness_threshold: float = 500.0
        self.after_seconds: float = 15.0
        self.shutter_max_height: float = 100.0
        self.shutter_max_angle: float = 100.0
        self.shutter_look_through_seconds: float = 15.0
        self.shutter_open_seconds: float = 15.0
        self.shutter_look_through_angle: float = 0.0
        self.height_after_dawn: float = 0.0
        self.angle_after_dawn: float = 0.0


class ShadowControlManager:
    """Manages the Shadow Control logic for a single cover."""

    def __init__(self, hass: HomeAssistant, config: dict[str, Any], entry_id: str, instance_logger: logging.Logger) -> None:
        """Initialize all defaults."""
        self.hass = hass
        self._config = config
        self._entry_id = entry_id
        self.logger = instance_logger

        self.name = config[SC_CONF_NAME]
        self._target_cover_entity_id = config[TARGET_COVER_ENTITY_ID]

        # Check if critical values are missing, even if this might be done within async_setup_entry
        if not self.name:
            self.logger.warning("Manager init: Manager name is missing in config for entry %s. Using fallback.", entry_id)
            self.name = f"Unnamed Shadow Control ({entry_id})"
        if not self._target_cover_entity_id:
            self.logger.error("Manager init: Target cover entity ID is missing in config for entry %s. This is critical.", entry_id)
            message = f"Target cover entity ID missing for entry {entry_id}"
            raise ValueError(message)

        self._options = config

        self._unsub_callbacks: list[Callable[[], None]] = []

        # Initialize configuration with default values
        self._dynamic_config = SCDynamicInputConfiguration()
        self._facade_config = SCFacadeConfiguration()
        self._shadow_config = SCShadowControlConfig()
        self._dawn_config = SCDawnControlConfig()

        # === Get dynamic configuration inputs
        self._dynamic_config.brightness = config.get(SCDynamicInput.BRIGHTNESS_ENTITY.value)
        self._dynamic_config.brightness_dawn = config.get(SCDynamicInput.BRIGHTNESS_DAWN_ENTITY.value)
        self._dynamic_config.sun_elevation = config.get(SCDynamicInput.SUN_ELEVATION_ENTITY.value)
        self._dynamic_config.sun_azimuth = config.get(SCDynamicInput.SUN_AZIMUTH_ENTITY.value)
        self._dynamic_config.shutter_current_height = config.get(SCDynamicInput.SHUTTER_CURRENT_HEIGHT_ENTITY.value)
        self._dynamic_config.shutter_current_angle = config.get(SCDynamicInput.SHUTTER_CURRENT_ANGLE_ENTITY.value)
        self._dynamic_config.lock_integration = config.get(SCDynamicInput.LOCK_INTEGRATION_ENTITY.value)
        self._dynamic_config.lock_integration_with_position = config.get(SCDynamicInput.LOCK_INTEGRATION_WITH_POSITION_ENTITY.value)
        self._dynamic_config.lock_height = config.get(SCDynamicInput.LOCK_HEIGHT_STATIC.value)
        self._dynamic_config.lock_angle = config.get(SCDynamicInput.LOCK_ANGLE_STATIC.value)
        self._dynamic_config.movement_restriction_height = config.get(SCDynamicInput.MOVEMENT_RESTRICTION_HEIGHT_ENTITY.value)
        self._dynamic_config.movement_restriction_angle = config.get(SCDynamicInput.MOVEMENT_RESTRICTION_ANGLE_ENTITY.value)
        self._dynamic_config.enforce_positioning_entity = config.get(SCDynamicInput.ENFORCE_POSITIONING_ENTITY.value)

        # === Get general facade configuration
        self._facade_config.azimuth = config.get(SCFacadeConfig.AZIMUTH_STATIC.value)
        self._facade_config.offset_sun_in = config.get(SCFacadeConfig.OFFSET_SUN_IN_STATIC.value)
        self._facade_config.offset_sun_out = config.get(SCFacadeConfig.OFFSET_SUN_OUT_STATIC.value)
        self._facade_config.elevation_sun_min = config.get(SCFacadeConfig.ELEVATION_SUN_MIN_STATIC.value)
        self._facade_config.elevation_sun_max = config.get(SCFacadeConfig.ELEVATION_SUN_MAX_STATIC.value)
        self._facade_config.slat_width = config.get(SCFacadeConfig.SLAT_WIDTH_STATIC.value)
        self._facade_config.slat_distance = config.get(SCFacadeConfig.SLAT_DISTANCE_STATIC.value)
        self._facade_config.slat_angle_offset = config.get(SCFacadeConfig.SLAT_ANGLE_OFFSET_STATIC.value)
        self._facade_config.slat_min_angle = config.get(SCFacadeConfig.SLAT_MIN_ANGLE_STATIC.value)
        self._facade_config.shutter_stepping_height = config.get(SCFacadeConfig.SHUTTER_STEPPING_HEIGHT_STATIC.value)
        self._facade_config.shutter_stepping_angle = config.get(SCFacadeConfig.SHUTTER_STEPPING_ANGLE_STATIC.value)
        self._facade_config.shutter_type = config.get(SCFacadeConfig.SHUTTER_TYPE_STATIC.value)
        self._facade_config.light_strip_width = config.get(SCFacadeConfig.LIGHT_STRIP_WIDTH_STATIC.value)
        self._facade_config.shutter_height = config.get(SCFacadeConfig.SHUTTER_HEIGHT_STATIC.value)
        self._facade_config.neutral_pos_height = config.get(SCFacadeConfig.NEUTRAL_POS_HEIGHT_STATIC.value)
        self._facade_config.neutral_pos_angle = config.get(SCFacadeConfig.NEUTRAL_POS_ANGLE_STATIC.value)
        self._facade_config.modification_tolerance_height = config.get(SCFacadeConfig.MODIFICATION_TOLERANCE_HEIGHT_STATIC.value)
        self._facade_config.modification_tolerance_angle = config.get(SCFacadeConfig.MODIFICATION_TOLERANCE_ANGLE_STATIC.value)

        # === Get shadow configuration
        self._shadow_config.enabled = config.get(SCShadowInput.CONTROL_ENABLED_ENTITY.value)
        self._shadow_config.brightness_threshold = config.get(SCShadowInput.BRIGHTNESS_THRESHOLD_ENTITY.value)
        self._shadow_config.after_seconds = config.get(SCShadowInput.AFTER_SECONDS_ENTITY.value)
        self._shadow_config.shutter_max_height = config.get(SCShadowInput.SHUTTER_MAX_HEIGHT_ENTITY.value)
        self._shadow_config.shutter_max_angle = config.get(SCShadowInput.SHUTTER_MAX_ANGLE_ENTITY.value)
        self._shadow_config.shutter_look_through_seconds = config.get(SCShadowInput.SHUTTER_LOOK_THROUGH_SECONDS_ENTITY.value)
        self._shadow_config.shutter_open_seconds = config.get(SCShadowInput.SHUTTER_OPEN_SECONDS_ENTITY.value)
        self._shadow_config.shutter_look_through_angle = config.get(SCShadowInput.SHUTTER_LOOK_THROUGH_ANGLE_ENTITY.value)
        self._shadow_config.height_after_sun = config.get(SCShadowInput.HEIGHT_AFTER_SUN_ENTITY.value)
        self._shadow_config.angle_after_sun = config.get(SCShadowInput.ANGLE_AFTER_SUN_ENTITY.value)

        # === Get dawn configuration
        self._dawn_config.enabled = config.get(SCDawnInput.CONTROL_ENABLED_ENTITY.value)
        self._dawn_config.brightness_threshold = config.get(SCDawnInput.BRIGHTNESS_THRESHOLD_ENTITY.value)
        self._dawn_config.after_seconds = config.get(SCDawnInput.AFTER_SECONDS_ENTITY.value)
        self._dawn_config.shutter_max_height = config.get(SCDawnInput.SHUTTER_MAX_HEIGHT_ENTITY.value)
        self._dawn_config.shutter_max_angle = config.get(SCDawnInput.SHUTTER_MAX_ANGLE_ENTITY.value)
        self._dawn_config.shutter_look_through_seconds = config.get(SCDawnInput.SHUTTER_LOOK_THROUGH_SECONDS_ENTITY.value)
        self._dawn_config.shutter_open_seconds = config.get(SCDawnInput.SHUTTER_OPEN_SECONDS_ENTITY.value)
        self._dawn_config.shutter_look_through_angle = config.get(SCDawnInput.SHUTTER_LOOK_THROUGH_ANGLE_ENTITY.value)
        self._dawn_config.height_after_dawn = config.get(SCDawnInput.HEIGHT_AFTER_DAWN_ENTITY.value)
        self._dawn_config.angle_after_dawn = config.get(SCDawnInput.ANGLE_AFTER_DAWN_ENTITY.value)

        # Define dictionary with all state handlers
        self._state_handlers: dict[ShutterState, Callable[[], Awaitable[ShutterState]]] = {
            ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING: self._handle_state_shadow_full_close_timer_running,
            ShutterState.SHADOW_FULL_CLOSED: self._handle_state_shadow_full_closed,
            ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING: self._handle_state_shadow_horizontal_neutral_timer_running,
            ShutterState.SHADOW_HORIZONTAL_NEUTRAL: self._handle_state_shadow_horizontal_neutral,
            ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING: self._handle_state_shadow_neutral_timer_running,
            ShutterState.SHADOW_NEUTRAL: self._handle_state_shadow_neutral,
            ShutterState.NEUTRAL: self._handle_state_neutral,
            ShutterState.DAWN_NEUTRAL: self._handle_state_dawn_neutral,
            ShutterState.DAWN_NEUTRAL_TIMER_RUNNING: self._handle_state_dawn_neutral_timer_running,
            ShutterState.DAWN_HORIZONTAL_NEUTRAL: self._handle_state_dawn_horizontal_neutral,
            ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING: self._handle_state_dawn_horizontal_neutral_timer_running,
            ShutterState.DAWN_FULL_CLOSED: self._handle_state_dawn_full_closed,
            ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING: self._handle_state_dawn_full_close_timer_running,
        }

        # Member vars
        self._enforce_position_update: bool = False

        # Persistant vars
        self.current_shutter_state: ShutterState = ShutterState.NEUTRAL
        self.current_lock_state: LockState = LockState.UNLOCKED
        self.calculated_shutter_height: float = 0.0
        self.calculated_shutter_angle: float = 0.0
        self.calculated_shutter_angle_degrees: float | None = None
        self._effective_elevation: float | None = None
        self._previous_shutter_height: float | None = None
        self._previous_shutter_angle: float | None = None
        self._is_initial_run: bool = True  # Flag for initial integration run
        self.is_in_sun: bool = False
        self.next_modification_timestamp: datetime | None = None

        self._last_known_height: float | None = None
        self._last_known_angle: float | None = None
        self._is_external_modification_detected: bool = False
        self._external_modification_timestamp: datetime | None = None

        self._timer_start_time: datetime | None = None
        self._timer_duration_seconds: float | None = None

        self._listeners: list[Callable[[], None]] = []
        self._timer: Callable[[], None] | None = None

        self.logger.debug("Manager initialized for target: %s.", self._target_cover_entity_id)

    async def async_start(self) -> None:
        """Start ShadowControlManager."""
        # - Register listeners
        # - Trigger initial calculation
        # Will be called after instantiation of the manager.
        self.logger.debug("Starting manager lifecycle...")
        self._async_register_listeners()
        await self._async_calculate_and_apply_cover_position(None)
        self.logger.debug("Manager lifecycle started.")

    def _async_register_listeners(self) -> None:
        """Register listener for state changes of relevant entities."""
        self.logger.debug("Registering listeners...")

        # If integration is re-loaded (e.g. by OptionsFlow), Home Assistant is already running.
        # In this case, call logic of _async_home_assistant_started directly.
        if not self.hass.is_running:
            self.logger.debug("Home Assistant not yet running, registering startup listener.")
            self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, self._async_home_assistant_started)
        else:
            self.logger.debug("Home Assistant already running, executing startup logic directly.")
            # As _async_home_assistant_started is a async method and we're not within an awaitable context
            # within this function, we use hass.async_create_task with 'None' as event object. At a direct
            # call there is no event object available.
            self.hass.async_create_task(self._async_home_assistant_started(None))

        tracked_inputs = []
        # Entities from SCDynamicInput and other relevant config inputs that trigger recalculation
        for conf_key_enum in [
            SCDynamicInput.BRIGHTNESS_ENTITY,
            SCDynamicInput.BRIGHTNESS_DAWN_ENTITY,
            SCDynamicInput.SUN_ELEVATION_ENTITY,
            SCDynamicInput.SUN_AZIMUTH_ENTITY,
            SCDynamicInput.LOCK_INTEGRATION_ENTITY,
            SCDynamicInput.LOCK_INTEGRATION_WITH_POSITION_ENTITY,
            SCDynamicInput.ENFORCE_POSITIONING_ENTITY,
            SCShadowInput.CONTROL_ENABLED_ENTITY,
            SCShadowInput.SHUTTER_MAX_HEIGHT_ENTITY,
            SCShadowInput.SHUTTER_MAX_ANGLE_ENTITY,
            SCDawnInput.CONTROL_ENABLED_ENTITY,
            SCDawnInput.SHUTTER_MAX_HEIGHT_ENTITY,
            SCDawnInput.SHUTTER_MAX_ANGLE_ENTITY,
        ]:
            # False positive "Expected type 'str' (matched generic type '_KT'), got '() -> Any | () -> Any | () -> Any' instead"
            entity_id = self._config.get(conf_key_enum.value)
            if entity_id:
                tracked_inputs.append(entity_id)

        # Handle movement restriction entities separately as they have a 'no_restriction' value
        if (
            self._config.get(SCDynamicInput.MOVEMENT_RESTRICTION_HEIGHT_ENTITY.value)
            and self._config[SCDynamicInput.MOVEMENT_RESTRICTION_HEIGHT_ENTITY.value] != "no_restriction"
        ):
            tracked_inputs.append(self._config[SCDynamicInput.MOVEMENT_RESTRICTION_HEIGHT_ENTITY.value])
        if (
            self._config.get(SCDynamicInput.MOVEMENT_RESTRICTION_ANGLE_ENTITY.value)
            and self._config[SCDynamicInput.MOVEMENT_RESTRICTION_ANGLE_ENTITY.value] != "no_restriction"
        ):
            tracked_inputs.append(self._config[SCDynamicInput.MOVEMENT_RESTRICTION_ANGLE_ENTITY.value])

        if tracked_inputs:
            self.logger.debug("Tracking input entities: %s", tracked_inputs)
            self._unsub_callbacks.append(async_track_state_change_event(self.hass, tracked_inputs, self._async_state_change_listener))

        # Listener of state changes at the handled cover entity to register external changes.
        # Important to recognize manual modification!
        if self._target_cover_entity_id:
            self.logger.debug("Tracking target cover entity: %s", self._target_cover_entity_id)
            self._unsub_callbacks.append(
                async_track_state_change_event(self.hass, self._target_cover_entity_id, self._async_target_cover_entity_state_change_listener)
            )

        self.logger.debug("Listeners registered.")

    async def _async_state_change_listener(self, event: Event) -> None:
        """Listen for state changes of monitored entites."""
        entity_id = event.data.get("entity_id")
        old_state = event.data.get("old_state")
        new_state = event.data.get("new_state")

        self.logger.debug(
            "State change detected for %s. Old state: %s, New state: %s.",
            entity_id,
            old_state.state if old_state else "None",
            new_state.state if new_state else "None",
        )

        # Check if state really was changed
        if old_state is None or new_state is None or old_state.state != new_state.state:
            self.logger.debug("Input entity '%s' changed. Triggering recalculation.", entity_id)
            await self._async_calculate_and_apply_cover_position(event)
        else:
            self.logger.debug("State change for %s detected, but value did not change. No recalculation triggered.", entity_id)

    async def _async_target_cover_entity_state_change_listener(self, event: Event) -> None:
        """Handle state changes of cover entities."""
        entity_id = event.data.get("entity_id")
        old_state: State | None = event.data.get("old_state")
        new_state: State | None = event.data.get("new_state")

        self.logger.debug(
            "Target cover state change detected for %s. Old state: %s, New state: %s.",
            entity_id,
            old_state.state if old_state else "None",
            new_state.state if new_state else "None",
        )

        # Check if the state really was changed
        old_current_height = old_state.attributes.get("current_position") if old_state else None
        new_current_height = new_state.attributes.get("current_position") if new_state else None
        old_current_angle = old_state.attributes.get("current_tilt") if old_state else None
        new_current_angle = new_state.attributes.get("current_tilt") if new_state else None

        # Wir müssen auch den Fall berücksichtigen, dass das Rollo offen oder geschlossen ist
        # und der Status sich ändert (z.B. von "opening" zu "open").
        # Hier ist es besser, auf eine Änderung von height oder angle zu prüfen,
        # da der state (open/closed/opening/closing) sich auch ohne manuelle Interaktion ändern kann.

        # Nur fortfahren, wenn sich die Höhe oder der Winkel geändert hat
        # und der Manager nicht selbst die Änderung verursacht hat (z.B. durch async_set_cover_position)
        if old_current_height != new_current_height or old_current_angle != new_current_angle:
            # Check if modification was triggerd by the ShadowControlManager himself
            if self.next_modification_timestamp and (
                (datetime.now(UTC) - self.next_modification_timestamp).total_seconds() < 5  # Less than 5 seconds since last change
            ):
                self.logger.debug("Cover state change detected, but appears to be self-initiated. Skipping lock state update.")
                self.next_modification_timestamp = None  # Reset for next external change
                return

            self.logger.debug("External change detected on target cover '%s'. (Updating lock state not implemented yet)", entity_id)

            # TODO: Implement logic for LockState handling e.g. manager.update_lock_state(LockState.LOCKED_BY_EXTERNAL_MODIFICATION)

        else:
            self.logger.debug("Target cover state change detected, but height/angle did not change or no external modification.")

    def unregister_listeners(self) -> None:
        """Unregister all listeners for this manager."""
        self.logger.debug("Unregistering listeners")
        for unsub_func in self._listeners:
            unsub_func()
        self._listeners = []

    async def _async_home_assistant_started(self, event: Event) -> None:
        """Calculate positions after start of Home Assistant."""
        self.logger.debug("Home Assistant started event received. Performing initial calculation.")
        await self._async_calculate_and_apply_cover_position(None)

    async def async_stop(self) -> None:
        """Stop ShadowControlManager."""
        # Remove listeners
        # Stop timer
        self.logger.debug("Stopping manager lifecycle...")
        if self._timer:
            self._timer()
            self._timer = None
            self.logger.debug("Recalculation timer cancelled.")

        for unsub_callback in self._unsub_callbacks:
            unsub_callback()
        self._unsub_callbacks.clear()
        self.logger.debug("Listeners unregistered.")

        self.logger.debug("Manager lifecycle stopped.")

    async def _update_input_values(self, event: Event | None = None) -> None:
        """Update all relevant input values from configuration or Home Assistant states."""
        # self.logger.debug("Updating all input values")

        # Facade Configuration (static values)
        self._facade_config.azimuth = self._get_static_value(SCFacadeConfig.AZIMUTH_STATIC.value, 180.0, float)
        self._facade_config.offset_sun_in = self._get_static_value(SCFacadeConfig.OFFSET_SUN_IN_STATIC.value, -90.0, float)
        self._facade_config.offset_sun_out = self._get_static_value(SCFacadeConfig.OFFSET_SUN_OUT_STATIC.value, 90.0, float)
        self._facade_config.elevation_sun_min = self._get_static_value(SCFacadeConfig.ELEVATION_SUN_MIN_STATIC.value, 0.0, float)
        self._facade_config.elevation_sun_max = self._get_static_value(SCFacadeConfig.ELEVATION_SUN_MAX_STATIC.value, 90.0, float)
        self._facade_config.slat_width = self._get_static_value(SCFacadeConfig.SLAT_WIDTH_STATIC.value, 95.0, float)
        self._facade_config.slat_distance = self._get_static_value(SCFacadeConfig.SLAT_DISTANCE_STATIC.value, 67.0, float)
        self._facade_config.slat_angle_offset = self._get_static_value(SCFacadeConfig.SLAT_ANGLE_OFFSET_STATIC.value, 0.0, float)
        self._facade_config.slat_min_angle = self._get_static_value(SCFacadeConfig.SLAT_MIN_ANGLE_STATIC.value, 0.0, float)
        self._facade_config.shutter_stepping_height = self._get_static_value(SCFacadeConfig.SHUTTER_STEPPING_HEIGHT_STATIC.value, 10.0, float)
        self._facade_config.shutter_stepping_angle = self._get_static_value(SCFacadeConfig.SHUTTER_STEPPING_ANGLE_STATIC.value, 10.0, float)

        # For shutter_type_static, it's a string from a selector. Convert it to ShutterType enum.
        shutter_type_str = self._get_static_value(SCFacadeConfig.SHUTTER_TYPE_STATIC.value, "mode1", str)
        try:
            self._facade_config.shutter_type = ShutterType[shutter_type_str.upper()]
        except KeyError:
            self.logger.warning("Invalid shutter type '%s' configured. Using default 'mode1'.", shutter_type_str)
            self._facade_config.shutter_type = ShutterType.MODE1

        self._facade_config.light_strip_width = self._get_static_value(SCFacadeConfig.LIGHT_STRIP_WIDTH_STATIC.value, 0.0, float)
        self._facade_config.shutter_height = self._get_static_value(SCFacadeConfig.SHUTTER_HEIGHT_STATIC.value, 1000.0, float)

        neutral_pos_height_config_value = self._get_static_value(SCFacadeConfig.NEUTRAL_POS_HEIGHT_STATIC.value, 0, float, log_warning=False)
        self._facade_config.neutral_pos_height = self._get_entity_state_value(
            SCFacadeConfig.NEUTRAL_POS_HEIGHT_ENTITY.value, neutral_pos_height_config_value, float
        )

        neutral_pos_angle_config_value = self._get_static_value(SCFacadeConfig.NEUTRAL_POS_ANGLE_STATIC.value, 0, float, log_warning=False)
        self._facade_config.neutral_pos_angle = self._get_entity_state_value(
            SCFacadeConfig.NEUTRAL_POS_ANGLE_ENTITY.value, neutral_pos_angle_config_value, float
        )

        self._facade_config.modification_tolerance_height = self._get_static_value(
            SCFacadeConfig.MODIFICATION_TOLERANCE_HEIGHT_STATIC.value, 0.0, float
        )
        self._facade_config.modification_tolerance_angle = self._get_static_value(
            SCFacadeConfig.MODIFICATION_TOLERANCE_ANGLE_STATIC.value, 0.0, float
        )

        # Dynamic Inputs (entity states or static values)
        self._dynamic_config.brightness = self._get_entity_state_value(SCDynamicInput.BRIGHTNESS_ENTITY.value, 0.0, float)
        self._dynamic_config.brightness_dawn = self._get_entity_state_value(SCDynamicInput.BRIGHTNESS_DAWN_ENTITY.value, -1.0, float)
        self._dynamic_config.sun_elevation = self._get_entity_state_value(SCDynamicInput.SUN_ELEVATION_ENTITY.value, 0.0, float)
        self._dynamic_config.sun_azimuth = self._get_entity_state_value(SCDynamicInput.SUN_AZIMUTH_ENTITY.value, 0.0, float)
        self._dynamic_config.shutter_current_height = self._get_entity_state_value(SCDynamicInput.SHUTTER_CURRENT_HEIGHT_ENTITY.value, -1.0, float)
        self._dynamic_config.shutter_current_angle = self._get_entity_state_value(SCDynamicInput.SHUTTER_CURRENT_ANGLE_ENTITY.value, -1.0, float)

        lock_integration = self._get_static_value(SCDynamicInput.LOCK_INTEGRATION_STATIC.value, False, bool, log_warning=False)
        self._dynamic_config.lock_integration = self._get_entity_state_value(SCDynamicInput.LOCK_INTEGRATION_ENTITY.value, lock_integration, bool)

        lock_integration_with_position = self._get_static_value(
            SCDynamicInput.LOCK_INTEGRATION_WITH_POSITION_STATIC.value, False, bool, log_warning=False
        )
        self._dynamic_config.lock_integration_with_position = self._get_entity_state_value(
            SCDynamicInput.LOCK_INTEGRATION_WITH_POSITION_ENTITY.value, lock_integration_with_position, bool
        )

        self.current_lock_state = self._calculate_lock_state()

        lock_height_config_value = self._get_static_value(SCDynamicInput.LOCK_HEIGHT_STATIC.value, 0, float, log_warning=False)
        self._dynamic_config.lock_height = self._get_entity_state_value(SCDynamicInput.LOCK_HEIGHT_ENTITY.value, lock_height_config_value, float)

        lock_angle_config_value = self._get_static_value(SCDynamicInput.LOCK_ANGLE_STATIC.value, 0, float, log_warning=False)
        self._dynamic_config.lock_angle = self._get_entity_state_value(SCDynamicInput.LOCK_ANGLE_ENTITY.value, lock_angle_config_value, float)

        # Movement restrictions (Enum values)
        self._dynamic_config.movement_restriction_height = self._get_entity_state_value(
            SCDynamicInput.MOVEMENT_RESTRICTION_HEIGHT_ENTITY.value, MovementRestricted.NO_RESTRICTION, MovementRestricted
        )
        self._dynamic_config.movement_restriction_angle = self._get_entity_state_value(
            SCDynamicInput.MOVEMENT_RESTRICTION_ANGLE_ENTITY.value, MovementRestricted.NO_RESTRICTION, MovementRestricted
        )

        self._enforce_position_update = self._get_entity_state_value(SCDynamicInput.ENFORCE_POSITIONING_ENTITY.value, False, bool)

        # Shadow Control Inputs
        shadow_control_enabled_static = self._get_static_value(SCShadowInput.CONTROL_ENABLED_STATIC.value, True, bool, log_warning=False)
        self._shadow_config.enabled = self._get_entity_state_value(SCShadowInput.CONTROL_ENABLED_ENTITY.value, shadow_control_enabled_static, bool)

        # Shadow Brightness Threshold
        shadow_brightness_threshold_static = self._get_static_value(
            SCShadowInput.BRIGHTNESS_THRESHOLD_STATIC.value, 50000.0, float, log_warning=False
        )
        self._shadow_config.brightness_threshold = self._get_entity_state_value(
            SCShadowInput.BRIGHTNESS_THRESHOLD_ENTITY.value, shadow_brightness_threshold_static, float
        )

        # Shadow After Seconds
        shadow_after_seconds_static = self._get_static_value(SCShadowInput.AFTER_SECONDS_STATIC.value, 15.0, float, log_warning=False)
        self._shadow_config.after_seconds = self._get_entity_state_value(SCShadowInput.AFTER_SECONDS_ENTITY.value, shadow_after_seconds_static, float)

        # Shadow Shutter Max Height
        shadow_shutter_max_height_static = self._get_static_value(SCShadowInput.SHUTTER_MAX_HEIGHT_STATIC.value, 100.0, float, log_warning=False)
        self._shadow_config.shutter_max_height = self._get_entity_state_value(
            SCShadowInput.SHUTTER_MAX_HEIGHT_ENTITY.value, shadow_shutter_max_height_static, float
        )

        # Shadow Shutter Max Angle
        shadow_shutter_max_angle_static = self._get_static_value(SCShadowInput.SHUTTER_MAX_ANGLE_STATIC.value, 100.0, float, log_warning=False)
        self._shadow_config.shutter_max_angle = self._get_entity_state_value(
            SCShadowInput.SHUTTER_MAX_ANGLE_ENTITY.value, shadow_shutter_max_angle_static, float
        )

        # Shadow Shutter Look Through Seconds
        shadow_shutter_look_through_seconds_static = self._get_static_value(
            SCShadowInput.SHUTTER_LOOK_THROUGH_SECONDS_STATIC.value, 15.0, float, log_warning=False
        )
        self._shadow_config.shutter_look_through_seconds = self._get_entity_state_value(
            SCShadowInput.SHUTTER_LOOK_THROUGH_SECONDS_ENTITY.value, shadow_shutter_look_through_seconds_static, float
        )

        # Shadow Shutter Open Seconds
        shadow_shutter_open_seconds_static = self._get_static_value(SCShadowInput.SHUTTER_OPEN_SECONDS_STATIC.value, 15.0, float, log_warning=False)
        self._shadow_config.shutter_open_seconds = self._get_entity_state_value(
            SCShadowInput.SHUTTER_OPEN_SECONDS_ENTITY.value, shadow_shutter_open_seconds_static, float
        )

        # Shadow Shutter Look Through Angle
        shadow_shutter_look_through_angle_static = self._get_static_value(
            SCShadowInput.SHUTTER_LOOK_THROUGH_ANGLE_STATIC.value, 0.0, float, log_warning=False
        )
        self._shadow_config.shutter_look_through_angle = self._get_entity_state_value(
            SCShadowInput.SHUTTER_LOOK_THROUGH_ANGLE_ENTITY.value, shadow_shutter_look_through_angle_static, float
        )

        # Shadow Height After Sun
        shadow_height_after_sun_static = self._get_static_value(SCShadowInput.HEIGHT_AFTER_SUN_STATIC.value, 0.0, float, log_warning=False)
        self._shadow_config.height_after_sun = self._get_entity_state_value(
            SCShadowInput.HEIGHT_AFTER_SUN_ENTITY.value, shadow_height_after_sun_static, float
        )

        # Shadow Angle After Sun
        shadow_angle_after_sun_static = self._get_static_value(SCShadowInput.ANGLE_AFTER_SUN_STATIC.value, 0.0, float, log_warning=False)
        self._shadow_config.angle_after_sun = self._get_entity_state_value(
            SCShadowInput.ANGLE_AFTER_SUN_ENTITY.value, shadow_angle_after_sun_static, float
        )

        # Dawn Control Inputs
        dawn_control_enabled_static = self._get_static_value(SCDawnInput.CONTROL_ENABLED_STATIC.value, True, bool, log_warning=False)
        self._dawn_config.enabled = self._get_entity_state_value(SCDawnInput.CONTROL_ENABLED_ENTITY.value, dawn_control_enabled_static, bool)

        # Dawn Brightness Threshold
        dawn_brightness_threshold_static = self._get_static_value(SCDawnInput.BRIGHTNESS_THRESHOLD_STATIC.value, 500.0, float, log_warning=False)
        self._dawn_config.brightness_threshold = self._get_entity_state_value(
            SCDawnInput.BRIGHTNESS_THRESHOLD_ENTITY.value, dawn_brightness_threshold_static, float
        )

        # Dawn After Seconds
        dawn_after_seconds_static = self._get_static_value(SCDawnInput.AFTER_SECONDS_STATIC.value, 15.0, float, log_warning=False)
        self._dawn_config.after_seconds = self._get_entity_state_value(SCDawnInput.AFTER_SECONDS_ENTITY.value, dawn_after_seconds_static, float)

        # Dawn Shutter Max Height
        dawn_shutter_max_height_static = self._get_static_value(SCDawnInput.SHUTTER_MAX_HEIGHT_STATIC.value, 100.0, float, log_warning=False)
        self._dawn_config.shutter_max_height = self._get_entity_state_value(
            SCDawnInput.SHUTTER_MAX_HEIGHT_ENTITY.value, dawn_shutter_max_height_static, float
        )

        # Dawn Shutter Max Angle
        dawn_shutter_max_angle_static = self._get_static_value(SCDawnInput.SHUTTER_MAX_ANGLE_STATIC.value, 100.0, float, log_warning=False)
        self._dawn_config.shutter_max_angle = self._get_entity_state_value(
            SCDawnInput.SHUTTER_MAX_ANGLE_ENTITY.value, dawn_shutter_max_angle_static, float
        )

        # Dawn Shutter Look Through Seconds
        dawn_shutter_look_through_seconds_static = self._get_static_value(
            SCDawnInput.SHUTTER_LOOK_THROUGH_SECONDS_STATIC.value, 15.0, float, log_warning=False
        )
        self._dawn_config.shutter_look_through_seconds = self._get_entity_state_value(
            SCDawnInput.SHUTTER_LOOK_THROUGH_SECONDS_ENTITY.value, dawn_shutter_look_through_seconds_static, float
        )

        # Dawn Shutter Open Seconds
        dawn_shutter_open_seconds_static = self._get_static_value(SCDawnInput.SHUTTER_OPEN_SECONDS_STATIC.value, 15.0, float, log_warning=False)
        self._dawn_config.shutter_open_seconds = self._get_entity_state_value(
            SCDawnInput.SHUTTER_OPEN_SECONDS_ENTITY.value, dawn_shutter_open_seconds_static, float
        )

        # Dawn Shutter Look Through Angle
        dawn_shutter_look_through_angle_static = self._get_static_value(
            SCDawnInput.SHUTTER_LOOK_THROUGH_ANGLE_STATIC.value, 0.0, float, log_warning=False
        )
        self._dawn_config.shutter_look_through_angle = self._get_entity_state_value(
            SCDawnInput.SHUTTER_LOOK_THROUGH_ANGLE_ENTITY.value, dawn_shutter_look_through_angle_static, float
        )

        # Dawn Height After Dawn
        dawn_height_after_dawn_static = self._get_static_value(SCDawnInput.HEIGHT_AFTER_DAWN_STATIC.value, 0.0, float, log_warning=False)
        self._dawn_config.height_after_dawn = self._get_entity_state_value(
            SCDawnInput.HEIGHT_AFTER_DAWN_ENTITY.value, dawn_height_after_dawn_static, float
        )

        # Dawn Angle After Dawn
        dawn_angle_after_dawn_static = self._get_static_value(SCDawnInput.ANGLE_AFTER_DAWN_STATIC.value, 0.0, float, log_warning=False)
        self._dawn_config.angle_after_dawn = self._get_entity_state_value(
            SCDawnInput.ANGLE_AFTER_DAWN_ENTITY.value, dawn_angle_after_dawn_static, float
        )

        facade = _format_config_object_for_logging(self._facade_config, " -> Facade config: ")
        dynamic = _format_config_object_for_logging(self._dynamic_config, " -> Dynamic config: ")
        shadow = _format_config_object_for_logging(self._shadow_config, " -> Shadow config: ")
        dawn = _format_config_object_for_logging(self._dawn_config, " -> Dawn config: ")
        self.logger.debug("Updated input values:\n%s,\n%s,\n%s,\n%s", facade, dynamic, shadow, dawn)

    @callback
    async def _async_handle_input_change(self, event: Event | None) -> None:
        """Handle changes to any relevant input entity for this specific cover."""
        self.logger.debug("Input change detected. Event: %s", event)

        await self._async_calculate_and_apply_cover_position(event)

    async def _async_calculate_and_apply_cover_position(self, event: Event | None) -> None:
        """Calculate and apply cover and tilt position."""
        self.logger.debug("=====================================================================")
        self.logger.debug("Calculating and applying cover position, triggered by event: %s", event.data if event else "None")

        await self._update_input_values()

        shadow_handling_was_disabled = False
        dawn_handling_was_disabled = False

        if event:  # Check for real event (not None like at the initial run)
            event_type = event.event_type
            event_data = event.data

            if event_type == "state_changed":
                entity = event_data.get("entity_id")
                old_state: State | None = event_data.get("old_state")
                new_state: State | None = event_data.get("new_state")

                self.logger.debug("State change for entity: %s", entity)
                self.logger.debug("  Old state: %s", old_state.state if old_state else "None")
                self.logger.debug("  New state: %s", new_state.state if new_state else "None")

                if entity == self._config.get(SCShadowInput.CONTROL_ENABLED_ENTITY.value):
                    self.logger.info("Shadow control enable changed to %s", new_state.state)
                    shadow_handling_was_disabled = new_state.state == "off"
                elif entity == self._config.get(SCDawnInput.CONTROL_ENABLED_ENTITY.value):
                    self.logger.info("Dawn control enable changed to %s", new_state.state)
                    dawn_handling_was_disabled = new_state.state == "off"
                elif entity == self._config.get(SCDynamicInput.LOCK_INTEGRATION_ENTITY.value) or entity == self._config.get(
                    SCDynamicInput.LOCK_INTEGRATION_STATIC.value
                ):
                    if new_state.state == "off" and not self._dynamic_config.lock_integration_with_position:
                        self.logger.info("Simple lock was disabled and lock with position is already disabled -> enforcing position update")
                        self._enforce_position_update = True
                    elif new_state.state == "off" and self._dynamic_config.lock_integration_with_position:
                        self.logger.info("Simple lock was disabled but lock with position is already enabled -> no position update")
                    else:
                        self.logger.info("Simple lock enabled -> no position update")
                elif entity == self._config.get(SCDynamicInput.LOCK_INTEGRATION_WITH_POSITION_ENTITY.value) or entity == self._config.get(
                    SCDynamicInput.LOCK_INTEGRATION_WITH_POSITION_STATIC.value
                ):
                    if new_state.state == "off" and not self._dynamic_config.lock_integration:
                        self.logger.info("Lock with position was disabled and simple lock already disabled -> enforcing position update")
                        self._enforce_position_update = True
                    elif new_state.state == "off" and self._dynamic_config.lock_integration:
                        self.logger.info("Lock with position was disabled but simple lock already enabled -> no position update")
                    else:
                        self.logger.info("Lock with position enabled -> enforcing position update")
                        self._enforce_position_update = True
                elif entity == self._config.get(SCDynamicInput.ENFORCE_POSITIONING_ENTITY.value):
                    if new_state.state == "on":
                        self.logger.debug("Enforced positioning triggered")
                        self._enforce_position_update = True
            elif event_type == "time_changed":
                self.logger.info("Time changed event received")
            else:
                self.logger.debug("Unhandled event type: %s", event_type)
        else:
            self.logger.info("No specific event data (likely initial run or manual trigger)")

        # TODO: Needs to be implemented later
        # self._check_if_position_changed_externally(self._dynamic_config.shutter_current_height, self._dynamic_config.shutter_current_angle)

        await self._check_if_facade_is_in_sun()

        if shadow_handling_was_disabled:
            await self._shadow_handling_was_disabled()
        elif dawn_handling_was_disabled:
            await self._dawn_handling_was_disabled()
        else:
            await self._process_shutter_state()

        self._enforce_position_update = False

    async def _check_if_facade_is_in_sun(self) -> bool:
        """Calculate if the sun illuminates the given facade."""
        self.logger.debug("Checking if facade is in sun")

        sun_current_azimuth = self._dynamic_config.sun_azimuth
        sun_current_elevation = self._dynamic_config.sun_elevation
        facade_azimuth = self._facade_config.azimuth
        facade_offset_start = self._facade_config.offset_sun_in
        facade_offset_end = self._facade_config.offset_sun_out
        min_elevation = self._facade_config.elevation_sun_min
        max_elevation = self._facade_config.elevation_sun_max

        if (
            sun_current_azimuth is None
            or sun_current_elevation is None
            or facade_azimuth is None
            or facade_offset_start is None
            or facade_offset_end is None
            or min_elevation is None
            or max_elevation is None
        ):
            self.logger.debug("Not all required values available to compute sun state of facade")
            self._effective_elevation = None
            return False

        sun_entry_angle = facade_azimuth - abs(facade_offset_start)
        sun_exit_angle = facade_azimuth + abs(facade_offset_end)
        if sun_entry_angle < 0:
            sun_entry_angle = 360 - abs(sun_entry_angle)
        if sun_exit_angle >= 360:
            sun_exit_angle %= 360

        sun_exit_angle_calc = sun_exit_angle - sun_entry_angle
        if sun_exit_angle_calc < 0:
            sun_exit_angle_calc += 360
        azimuth_calc = sun_current_azimuth - sun_entry_angle
        if azimuth_calc < 0:
            azimuth_calc += 360
        self.logger.debug(
            "sun_entry_angle: %s, sun_exit_angle: %s, sun_exit_angle_calc: %s, azimuth_calc: %s",
            sun_entry_angle,
            sun_exit_angle,
            sun_exit_angle_calc,
            azimuth_calc,
        )

        message = f"Finished facade check:\n -> Real azimuth {sun_current_azimuth}° and facade at {facade_azimuth}° -> "
        _sun_between_offsets = False
        if 0 <= azimuth_calc <= sun_exit_angle_calc:
            message += f"IN sun (from {sun_entry_angle}° to {sun_exit_angle}°)"
            _sun_between_offsets = True
            self._effective_elevation = await self._calculate_effective_elevation()
        else:
            message += f"NOT IN sun (shadow side, at sun from {sun_entry_angle}° to {sun_exit_angle}°)"
            self._effective_elevation = None

        effective_elevation_shortened = f"{self._effective_elevation:.1f}" if self._effective_elevation else "---"
        message += f"\n -> Effective elevation {effective_elevation_shortened}° for given elevation of {sun_current_elevation:.1f}°"
        _is_elevation_in_range = False

        if self._effective_elevation is None:
            _is_elevation_in_range = False
            message += f" -> NOT IN min-max-range ({min_elevation}°-{max_elevation}°)"
        elif min_elevation < self._effective_elevation < max_elevation:
            message += f" -> IN min-max-range ({min_elevation}°-{max_elevation}°)"
            self._sun_between_min_max = True
            _is_elevation_in_range = True
        else:
            message += f" -> NOT IN min-max-range ({min_elevation}°-{max_elevation}°)"
            self._sun_between_min_max = False
        self.logger.debug("%s", message)

        self.is_in_sun = _sun_between_offsets and _is_elevation_in_range
        return self.is_in_sun

    def _get_current_brightness(self) -> float:
        return self._dynamic_config.brightness

    def _get_current_dawn_brightness(self) -> float:
        if self._dynamic_config.brightness_dawn is not None and self._dynamic_config.brightness_dawn >= 0:
            return self._dynamic_config.brightness_dawn
        return self._dynamic_config.brightness

    async def _calculate_effective_elevation(self) -> float | None:
        """Calculate effective elevation in relation to the facade."""
        sun_current_azimuth = self._dynamic_config.sun_azimuth
        sun_current_elevation = self._dynamic_config.sun_elevation
        facade_azimuth = self._facade_config.azimuth

        if sun_current_azimuth is None or sun_current_elevation is None or facade_azimuth is None:
            self.logger.debug("Unable to compute effective elevation, not all required values available")
            return None

        self.logger.debug("Current sun position (a:e): %s°:%s°, facade: %s°", sun_current_azimuth, sun_current_elevation, facade_azimuth)

        try:
            virtual_depth = math.cos(math.radians(abs(sun_current_azimuth - facade_azimuth)))
            virtual_height = math.tan(math.radians(sun_current_elevation))

            # Prevent division by zero if virtual_depth if very small
            if abs(virtual_depth) < 1e-9:
                effective_elevation = 90.0 if virtual_height > 0 else -90.0
            else:
                effective_elevation = math.degrees(math.atan(virtual_height / virtual_depth))

        except ValueError:
            self.logger.debug("Unable to compute effective elevation: Invalid input values")
            return None
        except ZeroDivisionError:
            self.logger.debug("Unable to compute effective elevation: Division by zero")
            return None
        else:
            self.logger.debug(
                "Virtual deep and height of the sun against the facade: %s, %s, effektive Elevation: %s",
                virtual_depth,
                virtual_height,
                effective_elevation,
            )
            return effective_elevation

    def _update_extra_state_attributes(self) -> None:
        """Update the persistent values."""
        self._attr_extra_state_attributes = {
            "current_shutter_state": self.current_shutter_state,
            "calculated_shutter_height": self.calculated_shutter_height,
            "calculated_shutter_angle": self.calculated_shutter_angle,
            "calculated_shutter_angle_degrees": self.calculated_shutter_angle_degrees,
            "current_lock_state": self.current_lock_state,
            "next_modification_timestamp": self.next_modification_timestamp,
        }

    async def _shadow_handling_was_disabled(self) -> None:
        # False positive warning "This code is unreachable"
        match self.current_shutter_state:
            case (
                ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING
                | ShutterState.SHADOW_FULL_CLOSED
                | ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING
                | ShutterState.SHADOW_HORIZONTAL_NEUTRAL
                | ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING
                | ShutterState.SHADOW_NEUTRAL
            ):
                self.logger.debug("Shadow handling was disabled, position shutter at neutral height")
                self._cancel_timer()
                self.current_shutter_state = ShutterState.NEUTRAL
                self._update_extra_state_attributes()
            case ShutterState.NEUTRAL:
                self.logger.debug("Shadow handling was disabled, but shutter already at neutral height. Nothing to do")
            case _:
                self.logger.debug("Shadow handling was disabled but currently within a dawn state. Nothing to do")

    async def _dawn_handling_was_disabled(self) -> None:
        # False positive warning "This code is unreachable"
        match self.current_shutter_state:
            case (
                ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING
                | ShutterState.DAWN_FULL_CLOSED
                | ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING
                | ShutterState.DAWN_HORIZONTAL_NEUTRAL
                | ShutterState.DAWN_NEUTRAL_TIMER_RUNNING
                | ShutterState.DAWN_NEUTRAL
            ):
                self.logger.debug("Dawn handling was disabled, position shutter at neutral height")
                self._cancel_timer()
                self.current_shutter_state = ShutterState.NEUTRAL
                self._update_extra_state_attributes()
            case ShutterState.NEUTRAL:
                self.logger.debug("Dawn handling was disabled, but shutter already at neutral height. Nothing to do")
            case _:
                self.logger.debug("Dawn handling was disabled but currently within a shadow state. Nothing to do")

    async def _process_shutter_state(self) -> None:
        """Process current shutter state and call corresponding handler functions."""
        self.logger.debug("Current shutter state (before processing): %s (%s)", self.current_shutter_state.name, self.current_shutter_state.value)

        handler_func = self._state_handlers.get(self.current_shutter_state)
        new_shutter_state: ShutterState

        if handler_func:
            new_shutter_state = await handler_func()
            if new_shutter_state is not None and new_shutter_state != self.current_shutter_state:
                self.logger.debug("State change from %s to %s", self.current_shutter_state.name, new_shutter_state.name)
                self.current_shutter_state = new_shutter_state
                self._update_extra_state_attributes()
                self.logger.debug("Checking if there might be another change required")
                await self._process_shutter_state()
        else:
            self.logger.debug("No specific handler for current state or locked. Current lock state: %s", self.current_lock_state.name)
            self._cancel_timer()
            self._update_extra_state_attributes()

        self.logger.debug("New shutter state after processing: %s (%s)", self.current_shutter_state.name, self.current_shutter_state.value)

    async def _position_shutter(self, shutter_height_percent: float, shutter_angle_percent: float, shadow_position: bool, stop_timer: bool) -> None:
        """Evaluate and perform final shutter positioning commands."""
        self.logger.debug(
            "Starting _position_shutter with target height %.2f%% and angle %.2f%% (is_initial_run: %s, lock_state: %s)",
            shutter_height_percent,
            shutter_angle_percent,
            self._is_initial_run,
            self.current_lock_state.name,
        )

        # Always handle timer cancellation if required, regardless of initial run or lock state
        if stop_timer:
            self.logger.debug("Canceling timer.")
            self._cancel_timer()

        # --- Phase 1: Update internal states that should always reflect the calculation ---
        # These are the *calculated target* values.
        self.calculated_shutter_height = shutter_height_percent
        self.calculated_shutter_angle = shutter_angle_percent
        self.calculated_shutter_angle_degrees = self._convert_shutter_angle_percent_to_degrees(shutter_angle_percent)

        # --- Phase 2: Handle initial run special logic ---
        if self._is_initial_run:
            self.logger.info("Initial run of integration. Setting internal states. No physical output update.")
            # Only set internal previous values for the *next* run's send-by-change logic.
            # These are now set to the *initial target* values.
            self._previous_shutter_height = shutter_height_percent
            self._previous_shutter_angle = shutter_angle_percent
            self._is_initial_run = False  # Initial run completed

            self._update_extra_state_attributes()
            return  # Exit here, as no physical output should happen on the initial run

        # --- Phase 3: Check for Lock State BEFORE applying stepping/should_output_be_updated and sending commands ---
        # This ensures that calculations still happen, but outputs are skipped.
        is_locked = self.current_lock_state != LockState.UNLOCKED
        if is_locked:
            self.logger.info("Integration is locked (%s). Calculations are running, but physical outputs are skipped.", self.current_lock_state.name)
            # Update internal _previous values here to reflect that if it *were* unlocked,
            # it would have moved to these calculated positions.
            # This prepares for a smooth transition when unlocked.
            self._previous_shutter_height = shutter_height_percent
            self._previous_shutter_angle = shutter_angle_percent

            if self.current_lock_state == LockState.LOCKED_MANUALLY_WITH_FORCED_POSITION:
                for entity in self._target_cover_entity_id:
                    current_cover_state: State | None = self.hass.states.get(entity)

                    if not current_cover_state:
                        self.logger.warning("Target cover entity '%s' not found. Cannot send commands.", entity)
                        continue

                    shutter_height_percent = self._dynamic_config.lock_height
                    shutter_angle_percent = self._dynamic_config.lock_angle
                    self.logger.info(
                        "Integration set to locked with forced position, setting position to %.1f%%/%.1f%%",
                        shutter_height_percent,
                        shutter_angle_percent,
                    )
                    try:
                        await self.hass.services.async_call(
                            "cover", "set_cover_position", {"entity_id": entity, "position": 100 - shutter_height_percent}, blocking=False
                        )
                    except Exception:
                        self.logger.exception("Failed to set position:")
                    try:
                        await self.hass.services.async_call(
                            "cover", "set_cover_tilt_position", {"entity_id": entity, "tilt_position": 100 - shutter_angle_percent}, blocking=False
                        )
                    except Exception:
                        self.logger.exception("Failed to set tilt position:")

            self._update_extra_state_attributes()
            return  # Exit here, nothing else to do

        # --- Phase 4: Apply stepping and output restriction logic (only if not initial run AND not locked) ---
        # Computation is done with the first configured shutter
        entity = self._target_cover_entity_id[0]
        current_cover_state: State | None = self.hass.states.get(entity)

        if not current_cover_state:
            self.logger.warning("Target cover entity '%s' not found. Cannot send commands.", entity)
            return

        supported_features = current_cover_state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)

        has_pos_service = self.hass.services.has_service("cover", "set_cover_position")
        has_tilt_service = self.hass.services.has_service("cover", "set_cover_tilt_position")

        self.logger.debug("Services availability (%s): set_cover_position=%s, set_cover_tilt_position=%s", entity, has_pos_service, has_tilt_service)

        async_dispatcher_send(self.hass, f"{DOMAIN}_update_{self.name.lower().replace(' ', '_')}")

        # Height Handling
        height_to_set_percent = self._handle_shutter_height_stepping(shutter_height_percent)
        height_to_set_percent = self._should_output_be_updated(
            config_value=self._dynamic_config.movement_restriction_height,
            new_value=height_to_set_percent,
            previous_value=self._previous_shutter_height,
        )

        # Angle Handling - Crucial for "send angle if height changed" logic
        # We need the value of _previous_shutter_height *before* it's updated for height.
        # So, compare the *calculated* `shutter_height_percent` with what was previously *stored*.
        height_calculated_different_from_previous = (
            (-0.001 < abs(shutter_height_percent - self._previous_shutter_height) > 0.001) if self._previous_shutter_height is not None else True
        )

        angle_to_set_percent = self._should_output_be_updated(
            config_value=self._dynamic_config.movement_restriction_angle, new_value=shutter_angle_percent, previous_value=self._previous_shutter_angle
        )

        # --- Phase 5: Send commands if values actually changed (only if not initial run AND not locked) ---
        send_height_command = (
            -0.001 < abs(height_to_set_percent - self._previous_shutter_height) > 0.001 if self._previous_shutter_height is not None else True
        )

        # Send angle command if the angle changed OR if height changed significantly
        send_angle_command = (
            -0.001 < abs(angle_to_set_percent - self._previous_shutter_angle) > 0.001 if self._previous_shutter_angle is not None else True
        ) or height_calculated_different_from_previous

        if self._enforce_position_update:
            self.logger.debug("Enforcing position update")
            send_height_command = True
            send_angle_command = True

        # Position all configured shutters
        for entity in self._target_cover_entity_id:
            current_cover_state: State | None = self.hass.states.get(entity)

            if not current_cover_state:
                self.logger.warning("Target cover entity '%s' not found. Cannot send commands.", entity)
                continue

            # Height positioning
            if send_height_command or self._enforce_position_update:
                if (supported_features & CoverEntityFeature.SET_POSITION) and has_pos_service:
                    self.logger.debug(
                        "Setting position to %.1f%% (current: %s) for entity_id %s.", shutter_height_percent, self._previous_shutter_height, entity
                    )
                    try:
                        await self.hass.services.async_call(
                            "cover", "set_cover_position", {"entity_id": entity, "position": 100 - shutter_height_percent}, blocking=False
                        )
                    except Exception:
                        self.logger.exception("Failed to set position:")
                    self._previous_shutter_height = shutter_height_percent
                else:
                    self.logger.debug(
                        "Skipping position set. Supported: %s, Service Found: %s.",
                        supported_features & CoverEntityFeature.SET_POSITION,
                        has_pos_service,
                    )
            else:
                self.logger.debug("Height '%.2f%%' for entity_id %s not sent, value was the same or restricted.", height_to_set_percent, entity)

            # Angle positioning
            if send_angle_command or self._enforce_position_update:
                if (supported_features & CoverEntityFeature.SET_TILT_POSITION) and has_tilt_service:
                    self.logger.debug(
                        "Setting tilt position to %.1f%% (current: %s) for entity_id %s.", shutter_angle_percent, self._previous_shutter_angle, entity
                    )
                    try:
                        await self.hass.services.async_call(
                            "cover", "set_cover_tilt_position", {"entity_id": entity, "tilt_position": 100 - shutter_angle_percent}, blocking=False
                        )
                    except Exception:
                        self.logger.exception("Failed to set tilt position:")
                    self._previous_shutter_angle = shutter_angle_percent
                else:
                    self.logger.debug(
                        "Skipping tilt set. Supported: %s, Service Found: %s.",
                        supported_features & CoverEntityFeature.SET_TILT_POSITION,
                        has_tilt_service,
                    )
            else:
                self.logger.debug("Angle '%.2f%%' for entity_id %s not sent, value was the same or restricted.", angle_to_set_percent, entity)

        # Always update HA state at the end to reflect the latest internal calculated values and attributes
        self._update_extra_state_attributes()

        self.logger.debug("_position_shutter finished.")

    def _calculate_shutter_height(self) -> float:
        """Calculate shutter height based on sun position and shadow area configuration."""
        # Returns height in percent (0-100).
        self.logger.debug("Starting calculation of shutter height")

        width_of_light_strip = self._facade_config.light_strip_width
        shadow_max_height_percent = self._shadow_config.shutter_max_height
        elevation = self._dynamic_config.sun_elevation
        shutter_overall_height = self._facade_config.shutter_height

        shutter_height_to_set_percent = shadow_max_height_percent

        if (
            width_of_light_strip is None
            or elevation is None
            or shutter_overall_height is None
            or shadow_max_height_percent is None  # Muss auch None-geprüft werden
        ):
            self.logger.warning(
                "Not all required values for calcualation of shutter height available! width_of_light_strip=%s, elevation=%s, "
                "shutter_overall_height=%s, shadow_max_height_percent=%s. Using initial default value of %s%%",
                width_of_light_strip,
                elevation,
                shutter_overall_height,
                shadow_max_height_percent,
                shutter_height_to_set_percent,
            )
            return shutter_height_to_set_percent

        if width_of_light_strip != 0:
            # PHP's deg2rad equates to math.radians
            # PHP's tan equates math.tan
            shutter_height_from_bottom_raw = width_of_light_strip * math.tan(math.radians(elevation))

            # PHP's round is usually 'trading round' (round up 0.5).
            # Python's round() rounds to next even number at 0.5 ('bankers rounding').
            # For traders round one would need to use math.floor(x + 0.5) or decimal.
            # For the shutter position, the difference would be minimal, so we're using round().
            shutter_height_to_set = round(shutter_height_from_bottom_raw)

            # PHP: 100 - round($shutterHeightToSet * 100 / $shutterOverallHeight);
            new_shutter_height = 100 - round((shutter_height_to_set * 100) / shutter_overall_height)

            if new_shutter_height < shadow_max_height_percent:
                shutter_height_to_set_percent = new_shutter_height
                self.logger.debug(
                    "Elevation: %s°, Height: %s, Light strip width: %s, Resulting shutter height: %s (%s%%). Is smaller than max height",
                    elevation,
                    shutter_overall_height,
                    width_of_light_strip,
                    shutter_height_to_set,
                    shutter_height_to_set_percent,
                )
            else:
                self.logger.debug(
                    "Elevation: %s°, Height: %s, Light strip width: %s, Resulting shutter height (%s%%) is bigger or equal than given max "
                    "height (%s%%). Using max height",
                    elevation,
                    shutter_overall_height,
                    width_of_light_strip,
                    new_shutter_height,
                    shadow_max_height_percent,
                )
        else:
            self.logger.debug("width_of_light_strip is 0. No height calculation required. Using default height %s%%.", shutter_height_to_set_percent)

        return self._handle_shutter_height_stepping(shutter_height_to_set_percent)

    def _handle_shutter_height_stepping(self, calculated_height_percent: float) -> float:
        """Modify shutter height according to configured minimal stepping."""
        shutter_stepping_percent = self._facade_config.shutter_stepping_height

        if shutter_stepping_percent is None:
            self.logger.warning(
                "'shutter_stepping_angle' is None. Stepping can't be computed, returning initial angle %s%%", calculated_height_percent
            )
            return calculated_height_percent

        # Only apply stepping if the stepping value is not zero and height is not yet a multiple of the stepping
        if shutter_stepping_percent != 0:
            remainder = calculated_height_percent % shutter_stepping_percent
            if remainder != 0:
                # Example: 10% stepping, current height 23%. remainder = 3.
                # 23 + 10 - 3 = 30. (Rounds up to the next full step).
                adjusted_height = calculated_height_percent + shutter_stepping_percent - remainder
                self.logger.debug(
                    "Adjusting shutter height from %.2f%% to %.2f%% (stepping: %.2f%%).",
                    calculated_height_percent,
                    adjusted_height,
                    shutter_stepping_percent,
                )
                return adjusted_height

        self.logger.debug("Shutter height %.2f%% fits stepping or stepping is 0. No adjustment.", calculated_height_percent)
        return calculated_height_percent

    def _calculate_shutter_angle(self) -> float:
        """Calculate the shutter slat angle."""
        self.logger.debug("Starting calculation of shutter angle")

        # Prevent sunlight within the room, return angle in percent (0-100).
        elevation = self._dynamic_config.sun_elevation
        azimuth = self._dynamic_config.sun_azimuth  # For logging
        given_shutter_slat_width = self._facade_config.slat_width
        shutter_slat_distance = self._facade_config.slat_distance
        shutter_angle_offset = self._facade_config.slat_angle_offset
        min_shutter_angle_percent = self._facade_config.slat_min_angle
        max_shutter_angle_percent = self._shadow_config.shutter_max_angle
        shutter_type = self._facade_config.shutter_type  # String "90_degree_slats" or "180_degree_slats"

        effective_elevation = self._effective_elevation

        if (
            elevation is None
            or azimuth is None
            or given_shutter_slat_width is None
            or shutter_slat_distance is None
            or shutter_angle_offset is None
            or min_shutter_angle_percent is None
            or max_shutter_angle_percent is None
            or shutter_type is None
            or effective_elevation is None
        ):
            self.logger.warning(
                "Not all required values for angle calculation available. elevation=%s, azimuth=%s, slat_width=%s, slat_distance=%s, "
                "angle_offset=%s, min_angle=%s, max_angle=%s, shutter_type=%s, effective_elevation=%s. Returning 0.0",
                elevation,
                azimuth,
                given_shutter_slat_width,
                shutter_slat_distance,
                shutter_angle_offset,
                min_shutter_angle_percent,
                max_shutter_angle_percent,
                shutter_type,
                effective_elevation,
            )
            return 0.0  # Default if values missing

        # ==============================
        # Math based on oblique triangle

        # $alpha is the opposite angle of shutter slat width, so this is the difference
        # effectiveElevation and vertical
        alpha_deg = 90 - effective_elevation
        alpha_rad = math.radians(alpha_deg)

        # $beta is the opposit angle of shutter slat distance
        asin_arg = (math.sin(alpha_rad) * shutter_slat_distance) / given_shutter_slat_width

        if not (-1 <= asin_arg <= 1):
            self.logger.warning(
                "Argument for asin() out of valid range (-1 <= arg <= 1). Current value: %s. Unable to compute angle, returning 0.0", asin_arg
            )
            return 0.0

        beta_rad = math.asin(asin_arg)
        beta_deg = math.degrees(beta_rad)

        # $gamma is the angle between vertical and shutter slat
        gamma_deg = 180 - alpha_deg - beta_deg

        # $shutterAnglePercent is the difference between horizontal and shutter slat,
        # so this is the result of the calculation
        shutter_angle_degrees = round(90 - gamma_deg)

        self.logger.debug(
            "Elevation/azimuth: %s°/%s°, resulting effective elevation and shutter angle: %s°/%s° (without stepping and offset)",
            elevation,
            azimuth,
            effective_elevation,
            shutter_angle_degrees,
        )

        shutter_angle_percent: float
        if shutter_type == ShutterType.MODE1:
            shutter_angle_percent = shutter_angle_degrees / 0.9
        elif shutter_type == ShutterType.MODE2:
            shutter_angle_percent = shutter_angle_degrees / 1.8 + 50
        else:
            self.logger.warning("Unknown shutter type '%s'. Using default (mode1, 90°)", shutter_type)
            shutter_angle_percent = shutter_angle_degrees / 0.9  # Standardverhalten

        # Make sure, the angle will not be lower than 0
        if shutter_angle_percent < 0:
            shutter_angle_percent = 0.0

        # Round before stepping
        shutter_angle_percent_rounded_for_stepping = round(shutter_angle_percent)

        shutter_angle_percent_with_stepping = self._handle_shutter_angle_stepping(shutter_angle_percent_rounded_for_stepping)

        shutter_angle_percent_with_stepping += shutter_angle_offset

        if shutter_angle_percent_with_stepping < min_shutter_angle_percent:
            final_shutter_angle_percent = min_shutter_angle_percent
            self.logger.debug("Limiting angle to min: %s%%", min_shutter_angle_percent)
        elif shutter_angle_percent_with_stepping > max_shutter_angle_percent:
            final_shutter_angle_percent = max_shutter_angle_percent
            self.logger.debug("Limiting angle to max: %s%%", max_shutter_angle_percent)
        else:
            final_shutter_angle_percent = shutter_angle_percent_with_stepping

        # Round final angle
        final_shutter_angle_percent = round(final_shutter_angle_percent)

        self.logger.debug("Resulting shutter angle with offset and stepping: %s%%", final_shutter_angle_percent)
        return float(final_shutter_angle_percent)

    def _handle_shutter_angle_stepping(self, calculated_angle_percent: float) -> float:
        """Modify shutter angle according to configured minimal stepping."""
        self.logger.debug("Computing shutter angle stepping for %s%%", calculated_angle_percent)

        shutter_stepping_percent = self._facade_config.shutter_stepping_angle

        if shutter_stepping_percent is None:
            self.logger.warning(
                "'shutter_stepping_angle' is None. Stepping can't be computed, returning initial angle %s%%", calculated_angle_percent
            )
            return calculated_angle_percent

        # PHP logic in Python:
        # if ($shutterSteppingPercent != 0 && ($shutterAnglePercent % $shutterSteppingPercent) != 0) {
        #    $shutterAnglePercent = $shutterAnglePercent + $shutterSteppingPercent - ($shutterAnglePercent % $shutterSteppingPercent);
        # }

        if shutter_stepping_percent != 0:
            remainder = calculated_angle_percent % shutter_stepping_percent
            if remainder != 0:
                adjusted_angle = calculated_angle_percent + shutter_stepping_percent - remainder
                self.logger.debug(
                    "Adjusting shutter height from %.2f%% to %.2f%% (stepping: %.2f%%).",
                    calculated_angle_percent,
                    adjusted_angle,
                    shutter_stepping_percent,
                )
                return adjusted_angle

        self.logger.debug("Shutter height %.2f%% fits stepping or stepping is 0. No adjustment.", calculated_angle_percent)
        return calculated_angle_percent

    # #######################################################################
    # State handling starts here
    #
    # =======================================================================
    # State SHADOW_FULL_CLOSE_TIMER_RUNNING
    async def _handle_state_shadow_full_close_timer_running(self) -> ShutterState:
        self.logger.debug("Handle SHADOW_FULL_CLOSE_TIMER_RUNNING")
        if await self._check_if_facade_is_in_sun() and await self._is_shadow_control_enabled():
            current_brightness = self._dynamic_config.brightness
            shadow_threshold_close = self._shadow_config.brightness_threshold
            if current_brightness is not None and shadow_threshold_close is not None and current_brightness > shadow_threshold_close:
                if self._is_timer_finished():
                    target_height = self._calculate_shutter_height()
                    target_angle = self._calculate_shutter_angle()
                    if target_height is not None and target_angle is not None:
                        await self._position_shutter(
                            target_height,
                            target_angle,
                            shadow_position=True,
                            stop_timer=True,
                        )
                        self.logger.debug(
                            "State %s (%s): Timer finished, brightness above threshold, moving to shadow position (%s%%, %s%%). Next state: %s",
                            ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING,
                            ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING.name,
                            target_height,
                            target_angle,
                            ShutterState.SHADOW_FULL_CLOSED,
                        )
                        return ShutterState.SHADOW_FULL_CLOSED
                    self.logger.debug(
                        "State %s (%s): Error within calculation of height a/o angle, staying at %s",
                        ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING,
                        ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING.name,
                        ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING,
                    )
                    return ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING
                self.logger.debug(
                    "State %s (%s): Waiting for timer (Brightness big enough)",
                    ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING,
                    ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING.name,
                )
                return ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING
            self.logger.debug(
                "State %s (%s): Brightness (%s) not above threshold (%s), transitioning to %s",
                ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING,
                ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING.name,
                current_brightness,
                shadow_threshold_close,
                ShutterState.SHADOW_NEUTRAL,
            )
            self._cancel_timer()
            return ShutterState.SHADOW_NEUTRAL
        neutral_height = self._facade_config.neutral_pos_height
        neutral_angle = self._facade_config.neutral_pos_angle
        if neutral_height is not None and neutral_angle is not None:
            await self._position_shutter(
                float(neutral_height),
                float(neutral_angle),
                shadow_position=False,
                stop_timer=True,  # Stop Timer
            )
            self.logger.debug(
                "State %s (%s): Not in the sun or shadow mode disabled, transitioning to (%s%%, %s%%) with state %s",
                ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING,
                ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING.name,
                neutral_height,
                neutral_angle,
                ShutterState.NEUTRAL,
            )
            return ShutterState.NEUTRAL
        self.logger.warning(
            "State %s (%s): Neutral height or angle not configured, transitioning to %s",
            ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING,
            ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING.name,
            ShutterState.NEUTRAL,
        )
        return ShutterState.NEUTRAL

        self.logger.debug(
            "State %s (%s): Staying at previous position.",
            ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING,
            ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING.name,
        )
        return ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING

    # =======================================================================
    # State SHADOW_FULL_CLOSED
    async def _handle_state_shadow_full_closed(self) -> ShutterState:
        self.logger.debug("Handle SHADOW_FULL_CLOSED")
        if await self._check_if_facade_is_in_sun() and await self._is_shadow_control_enabled():
            current_brightness = self._get_current_brightness()
            shadow_threshold_close = self._shadow_config.brightness_threshold
            shadow_open_slat_delay = self._shadow_config.shutter_look_through_seconds
            if (
                current_brightness is not None
                and shadow_threshold_close is not None
                and shadow_open_slat_delay is not None
                and current_brightness < shadow_threshold_close
            ):
                self.logger.debug(
                    "State %s (%s): Brightness (%s) below threshold (%s), starting timer for %s (%ss)",
                    ShutterState.SHADOW_FULL_CLOSED,
                    ShutterState.SHADOW_FULL_CLOSED.name,
                    current_brightness,
                    shadow_threshold_close,
                    ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING,
                    shadow_open_slat_delay,
                )
                await self._start_timer(shadow_open_slat_delay)
                return ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING
            self.logger.debug(
                "State %s (%s): Brightness not below threshold, recalculating shadow position",
                ShutterState.SHADOW_FULL_CLOSED,
                ShutterState.SHADOW_FULL_CLOSED.name,
            )
            target_height = self._calculate_shutter_height()
            target_angle = self._calculate_shutter_angle()
            if target_height is not None and target_angle is not None:
                await self._position_shutter(
                    target_height,
                    target_angle,
                    shadow_position=True,
                    stop_timer=False,
                )
            return ShutterState.SHADOW_FULL_CLOSED
        neutral_height = self._facade_config.neutral_pos_height
        neutral_angle = self._facade_config.neutral_pos_angle
        if neutral_height is not None and neutral_angle is not None:
            await self._position_shutter(
                float(neutral_height),
                float(neutral_angle),
                shadow_position=False,
                stop_timer=True,  # Stop Timer
            )
            self.logger.debug(
                "State %s (%s): Not in sun or shadow mode deactivated, moving to neutral position (%s%%, %s%%) und state %s",
                ShutterState.SHADOW_FULL_CLOSED,
                ShutterState.SHADOW_FULL_CLOSED.name,
                neutral_height,
                neutral_angle,
                ShutterState.NEUTRAL,
            )
            return ShutterState.NEUTRAL
        self.logger.warning(
            "State %s (%s): Neutral height or angle not configured, moving to state %s",
            ShutterState.SHADOW_FULL_CLOSED,
            ShutterState.SHADOW_FULL_CLOSED.name,
            ShutterState.NEUTRAL,
        )
        return ShutterState.NEUTRAL

        self.logger.debug("State %s (%s): Staying at previous position", ShutterState.SHADOW_FULL_CLOSED, ShutterState.SHADOW_FULL_CLOSED.name)
        return ShutterState.SHADOW_FULL_CLOSED

    # =======================================================================
    # State SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING
    async def _handle_state_shadow_horizontal_neutral_timer_running(self) -> ShutterState:
        self.logger.debug("Handle SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING")
        if await self._check_if_facade_is_in_sun() and await self._is_shadow_control_enabled():
            current_brightness = self._get_current_brightness()
            shadow_threshold_close = self._shadow_config.brightness_threshold
            shadow_open_slat_angle = self._shadow_config.shutter_look_through_angle
            if (
                current_brightness is not None
                and shadow_threshold_close is not None
                and shadow_open_slat_angle is not None
                and current_brightness > shadow_threshold_close
            ):
                self.logger.debug(
                    "State %s (%s): Brightness (%s) again above threshold (%s), transitioning to %s and stopping timer",
                    ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING,
                    ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING.name,
                    current_brightness,
                    shadow_threshold_close,
                    ShutterState.SHADOW_FULL_CLOSED,
                )
                self._cancel_timer()
                return ShutterState.SHADOW_FULL_CLOSED
            if self._is_timer_finished():
                target_height = self._calculate_shutter_height()
                if target_height is not None and shadow_open_slat_angle is not None:
                    await self._position_shutter(
                        target_height,
                        float(shadow_open_slat_angle),
                        shadow_position=False,
                        stop_timer=True,
                    )
                    self.logger.debug(
                        "State %s (%s): Timer finished, moving to height %s%% with neutral slats (%s°) and state %s",
                        ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING,
                        ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING.name,
                        target_height,
                        shadow_open_slat_angle,
                        ShutterState.SHADOW_HORIZONTAL_NEUTRAL,
                    )
                    return ShutterState.SHADOW_HORIZONTAL_NEUTRAL
                self.logger.debug(
                    "State %s (%s): Error during calculation of height and angle for open slats, staying at %s",
                    ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING,
                    ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING.name,
                    ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING,
                )
                return ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING
            self.logger.debug(
                "State %s (%s): Waiting for timer (brightness not high enough)",
                ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING,
                ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING.name,
            )
            return ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING
        neutral_height = self._facade_config.neutral_pos_height
        neutral_angle = self._facade_config.neutral_pos_angle
        if neutral_height is not None and neutral_angle is not None:
            await self._position_shutter(
                float(neutral_height),
                float(neutral_angle),
                shadow_position=False,
                stop_timer=True,  # Stop Timer
            )
            self.logger.debug(
                "State %s (%s): Not in the sun or shadow mode disabled, moving to neutral position (%s%%, %s%%) and state %s",
                ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING,
                ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING.name,
                neutral_height,
                neutral_angle,
                ShutterState.NEUTRAL,
            )
            return ShutterState.NEUTRAL
        self.logger.warning(
            "State %s (%s): Neutral height or angle not configured, transitioning to %s",
            ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING,
            ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING.name,
            ShutterState.NEUTRAL,
        )
        return ShutterState.NEUTRAL

        self.logger.debug(
            "State %s (%s): Staying at previous position",
            ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING,
            ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING.name,
        )
        return ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING

    # =======================================================================
    # State SHADOW_HORIZONTAL_NEUTRAL
    async def _handle_state_shadow_horizontal_neutral(self) -> ShutterState:
        self.logger.debug("Handle SHADOW_HORIZONTAL_NEUTRAL")
        if await self._check_if_facade_is_in_sun() and await self._is_shadow_control_enabled():
            current_brightness = self._get_current_brightness()
            shadow_threshold_close = self._shadow_config.brightness_threshold
            shadow_open_shutter_delay = self._shadow_config.shutter_open_seconds
            if (
                current_brightness is not None
                and shadow_threshold_close is not None
                and shadow_open_shutter_delay is not None
                and current_brightness > shadow_threshold_close
            ):
                target_height = self._calculate_shutter_height()
                target_angle = self._calculate_shutter_angle()
                if target_height is not None and target_angle is not None:
                    await self._position_shutter(
                        target_height,
                        target_angle,
                        shadow_position=True,
                        stop_timer=True,
                    )
                    self.logger.debug(
                        "State %s (%s): Brightness (%s) above threshold (%s), moving to shadow position (%s%%, %s%%) and state %s",
                        ShutterState.SHADOW_HORIZONTAL_NEUTRAL,
                        ShutterState.SHADOW_HORIZONTAL_NEUTRAL.name,
                        current_brightness,
                        shadow_threshold_close,
                        target_height,
                        target_angle,
                        ShutterState.SHADOW_FULL_CLOSED,
                    )
                    return ShutterState.SHADOW_FULL_CLOSED
                self.logger.warning(
                    "State %s (%s): Error at calculating height or angle, staying at %s",
                    ShutterState.SHADOW_HORIZONTAL_NEUTRAL,
                    ShutterState.SHADOW_HORIZONTAL_NEUTRAL.name,
                    ShutterState.SHADOW_HORIZONTAL_NEUTRAL,
                )
                return ShutterState.SHADOW_HORIZONTAL_NEUTRAL
            if shadow_open_shutter_delay is not None:
                self.logger.debug(
                    "State %s (%s): Brightness not above threshold, starting timer for %s (%ss)",
                    ShutterState.SHADOW_HORIZONTAL_NEUTRAL,
                    ShutterState.SHADOW_HORIZONTAL_NEUTRAL.name,
                    ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING,
                    shadow_open_shutter_delay,
                )
                await self._start_timer(shadow_open_shutter_delay)
                return ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING
            self.logger.warning(
                "State %s (%s): Brightness not above threshold and 'shadow_open_shutter_delay' not configured, staying at %s",
                ShutterState.SHADOW_HORIZONTAL_NEUTRAL,
                ShutterState.SHADOW_HORIZONTAL_NEUTRAL.name,
                ShutterState.SHADOW_HORIZONTAL_NEUTRAL,
            )
            return ShutterState.SHADOW_HORIZONTAL_NEUTRAL
        neutral_height = self._facade_config.neutral_pos_height
        neutral_angle = self._facade_config.neutral_pos_angle
        if neutral_height is not None and neutral_angle is not None:
            await self._position_shutter(
                float(neutral_height),
                float(neutral_angle),
                shadow_position=False,
                stop_timer=True,  # Stop Timer (falls ein Timer aktiv war)
            )
            self.logger.debug(
                "State %s (%s): Not in sun or shadow mode disabled, moving to neutral position (%s%%, %s%%) and state %s",
                ShutterState.SHADOW_HORIZONTAL_NEUTRAL,
                ShutterState.SHADOW_HORIZONTAL_NEUTRAL.name,
                neutral_height,
                neutral_angle,
                ShutterState.NEUTRAL,
            )
            return ShutterState.NEUTRAL
        self.logger.warning(
            "State %s (%s): Neutral height or angle not configured, transitioning to %s",
            ShutterState.SHADOW_HORIZONTAL_NEUTRAL,
            ShutterState.SHADOW_HORIZONTAL_NEUTRAL.name,
            ShutterState.NEUTRAL,
        )
        return ShutterState.NEUTRAL

        self.logger.debug(
            "State %s (%s): Staying at previous position", ShutterState.SHADOW_HORIZONTAL_NEUTRAL, ShutterState.SHADOW_HORIZONTAL_NEUTRAL.name
        )
        return ShutterState.SHADOW_HORIZONTAL_NEUTRAL

    # =======================================================================
    # State SHADOW_NEUTRAL_TIMER_RUNNING
    async def _handle_state_shadow_neutral_timer_running(self) -> ShutterState:
        self.logger.debug("Handle SHADOW_NEUTRAL_TIMER_RUNNING")
        if await self._check_if_facade_is_in_sun() and await self._is_shadow_control_enabled():
            current_brightness = self._get_current_brightness()
            shadow_threshold_close = self._shadow_config.brightness_threshold
            height_after_shadow = self._shadow_config.height_after_sun
            angle_after_shadow = self._shadow_config.angle_after_sun
            if current_brightness is not None and shadow_threshold_close is not None and current_brightness > shadow_threshold_close:
                self.logger.debug(
                    "State %s (%s): Brightness (%s) again above threshold (%s), state %s and stopping timer",
                    ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING,
                    ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING.name,
                    current_brightness,
                    shadow_threshold_close,
                    ShutterState.SHADOW_FULL_CLOSED,
                )
                self._cancel_timer()
                return ShutterState.SHADOW_FULL_CLOSED
            if self._is_timer_finished():
                if height_after_shadow is not None and angle_after_shadow is not None:
                    await self._position_shutter(
                        float(height_after_shadow),
                        float(angle_after_shadow),
                        shadow_position=False,
                        stop_timer=True,
                    )
                    self.logger.debug(
                        "State %s (%s): Timer finished, moving to after-shadow position (%s%%, %s°) and state %s",
                        ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING,
                        ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING.name,
                        height_after_shadow,
                        angle_after_shadow,
                        ShutterState.SHADOW_NEUTRAL,
                    )
                    return ShutterState.SHADOW_NEUTRAL
                self.logger.warning(
                    "State %s (%s): Height or angle after shadow not configured, staying at %s",
                    ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING,
                    ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING.name,
                    ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING,
                )
                return ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING
            self.logger.debug(
                "State %s (%s): Waiting for timer (brightness not high enough)",
                ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING,
                ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING.name,
            )
            return ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING
        neutral_height = self._facade_config.neutral_pos_height
        neutral_angle = self._facade_config.neutral_pos_angle
        if neutral_height is not None and neutral_angle is not None:
            await self._position_shutter(
                float(neutral_height),
                float(neutral_angle),
                shadow_position=False,
                stop_timer=True,  # Stop Timer
            )
            self.logger.debug(
                "State %s (%s): Not in sun or shadow mode disabled, moving to neutral position (%s%%, %s%%) and state %s",
                ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING,
                ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING.name,
                neutral_height,
                neutral_angle,
                ShutterState.NEUTRAL,
            )
            return ShutterState.NEUTRAL
        self.logger.warning(
            "State %s (%s): Neutral height or angle not configured, transitioning to %s",
            ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING,
            ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING.name,
            ShutterState.NEUTRAL,
        )
        return ShutterState.NEUTRAL

        self.logger.debug(
            "State %s (%s): Staying at previous position", ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING, ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING.name
        )
        return ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING

    # =======================================================================
    # State SHADOW_NEUTRAL
    async def _handle_state_shadow_neutral(self) -> ShutterState:
        self.logger.debug("Handle SHADOW_NEUTRAL")
        if await self._check_if_facade_is_in_sun() and await self._is_shadow_control_enabled():
            current_brightness = self._get_current_brightness()
            shadow_threshold_close = self._shadow_config.brightness_threshold
            dawn_handling_active = self._dawn_config.enabled
            dawn_brightness = self._get_current_dawn_brightness()
            dawn_threshold_close = self._dawn_config.brightness_threshold
            shadow_close_delay = self._shadow_config.after_seconds
            dawn_close_delay = self._dawn_config.after_seconds
            height_after_shadow = self._shadow_config.height_after_sun
            angle_after_shadow = self._shadow_config.angle_after_sun

            if (
                current_brightness is not None
                and shadow_threshold_close is not None
                and current_brightness > shadow_threshold_close
                and shadow_close_delay is not None
            ):
                self.logger.debug(
                    "State %s (%s): Brightness (%s) above threshold (%s), starting timer for %s (%ss)",
                    ShutterState.SHADOW_NEUTRAL,
                    ShutterState.SHADOW_NEUTRAL.name,
                    current_brightness,
                    shadow_threshold_close,
                    ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING,
                    shadow_close_delay,
                )
                await self._start_timer(shadow_close_delay)
                return ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING
            if (
                dawn_handling_active
                and dawn_brightness is not None
                and dawn_threshold_close is not None
                and dawn_brightness < dawn_threshold_close
                and dawn_close_delay is not None
            ):
                self.logger.debug(
                    "State %s (%s): Dawn handling active and dawn-brighness (%s) below threshold (%s), starting timer for %s (%ss)",
                    ShutterState.SHADOW_NEUTRAL,
                    ShutterState.SHADOW_NEUTRAL.name,
                    dawn_brightness,
                    dawn_threshold_close,
                    ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING,
                    dawn_close_delay,
                )
                await self._start_timer(dawn_close_delay)
                return ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING
            if height_after_shadow is not None and angle_after_shadow is not None:
                await self._position_shutter(
                    float(height_after_shadow),
                    float(angle_after_shadow),
                    shadow_position=False,
                    stop_timer=True,
                )
                self.logger.debug(
                    "State %s (%s): Moving to after-shadow position (%s%%, %s%%)",
                    ShutterState.SHADOW_NEUTRAL,
                    ShutterState.SHADOW_NEUTRAL.name,
                    height_after_shadow,
                    angle_after_shadow,
                )
                return ShutterState.SHADOW_NEUTRAL
            self.logger.warning(
                "State %s (%s): Height or angle after shadow not configured, staying at %s",
                ShutterState.SHADOW_NEUTRAL,
                ShutterState.SHADOW_NEUTRAL.name,
                ShutterState.SHADOW_NEUTRAL,
            )
            return ShutterState.SHADOW_NEUTRAL

        if await self._is_dawn_control_enabled():
            dawn_brightness = self._get_current_dawn_brightness()
            dawn_threshold_close = self._dawn_config.brightness_threshold
            dawn_close_delay = self._dawn_config.after_seconds
            if (
                dawn_brightness is not None
                and dawn_threshold_close is not None
                and dawn_brightness < dawn_threshold_close
                and dawn_close_delay is not None
            ):
                self.logger.debug(
                    "State %s (%s): Dawn mode active and brightness (%s) below threshold (%s), starting timer for %s (%ss)",
                    ShutterState.SHADOW_NEUTRAL.name,
                    ShutterState.SHADOW_NEUTRAL.name.name,
                    dawn_brightness,
                    dawn_threshold_close,
                    ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING,
                    dawn_close_delay,
                )
                await self._start_timer(dawn_close_delay)
                return ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING

        neutral_height = self._facade_config.neutral_pos_height
        neutral_angle = self._facade_config.neutral_pos_angle
        if neutral_height is not None and neutral_angle is not None:
            await self._position_shutter(
                float(neutral_height),
                float(neutral_angle),
                shadow_position=False,
                stop_timer=True,  # Stop Timer (falls ein Timer aktiv war)
            )
            self.logger.debug(
                "State %s (%s): Not in sun or shadow mode disabled or dawn mode not active, moving to neutral position (%s%%, %s%%) and state %s",
                ShutterState.SHADOW_NEUTRAL,
                ShutterState.SHADOW_NEUTRAL.name,
                neutral_height,
                neutral_angle,
                ShutterState.NEUTRAL,
            )
            return ShutterState.NEUTRAL
        self.logger.warning(
            "State %s (%s): Neutral height or angle not configured, transitioning to %s",
            ShutterState.SHADOW_NEUTRAL,
            ShutterState.SHADOW_NEUTRAL.name,
            ShutterState.NEUTRAL,
        )
        return ShutterState.NEUTRAL

    # =======================================================================
    # State NEUTRAL
    async def _handle_state_neutral(self) -> ShutterState:
        self.logger.debug("Handle NEUTRAL")
        if await self._check_if_facade_is_in_sun() and await self._is_shadow_control_enabled():
            self.logger.debug("self._check_if_facade_is_in_sun and self._is_shadow_handling_activated")
            current_brightness = self._get_current_brightness()
            shadow_threshold_close = self._shadow_config.brightness_threshold
            shadow_close_delay = self._shadow_config.after_seconds
            if (
                current_brightness is not None
                and shadow_threshold_close is not None
                and current_brightness > shadow_threshold_close
                and shadow_close_delay is not None
            ):
                self.logger.debug(
                    "State %s (%s): Brightness (%s) above dawn threshold (%s), starting timer for %s (%ss)",
                    ShutterState.NEUTRAL,
                    ShutterState.NEUTRAL.name,
                    current_brightness,
                    shadow_threshold_close,
                    ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING,
                    shadow_close_delay,
                )
                await self._start_timer(shadow_close_delay)
                return ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING

        if await self._is_dawn_control_enabled():
            dawn_brightness = self._get_current_dawn_brightness()
            dawn_threshold_close = self._dawn_config.brightness_threshold
            dawn_close_delay = self._dawn_config.after_seconds
            if (
                dawn_brightness is not None
                and dawn_threshold_close is not None
                and dawn_brightness < dawn_threshold_close
                and dawn_close_delay is not None
            ):
                self.logger.debug(
                    "State %s (%s): Dawn mode active and brightness (%s) below dawn threshold (%s), starting timer for %s (%ss)",
                    ShutterState.NEUTRAL,
                    ShutterState.NEUTRAL.name,
                    dawn_brightness,
                    dawn_threshold_close,
                    ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING,
                    dawn_close_delay,
                )
                await self._start_timer(dawn_close_delay)
                return ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING

        neutral_height = self._facade_config.neutral_pos_height
        neutral_angle = self._facade_config.neutral_pos_angle
        if neutral_height is not None and neutral_angle is not None:
            await self._position_shutter(
                float(neutral_height),
                float(neutral_angle),
                shadow_position=False,
                stop_timer=True,
            )
            self.logger.debug(
                "State %s (%s): Moving shutter to neutral position (%s%%, %s%%).",
                ShutterState.NEUTRAL,
                ShutterState.NEUTRAL.name,
                neutral_height,
                neutral_angle,
            )
        return ShutterState.NEUTRAL

    # =======================================================================
    # State DAWN_NEUTRAL
    async def _handle_state_dawn_neutral(self) -> ShutterState:
        self.logger.debug("Handle DAWN_NEUTRAL")
        current_brightness = self._get_current_brightness()

        shadow_handling_active = await self._is_shadow_control_enabled()
        shadow_threshold_close = self._shadow_config.brightness_threshold
        shadow_close_delay = self._shadow_config.after_seconds

        dawn_handling_active = await self._is_dawn_control_enabled()
        dawn_brightness = self._get_current_dawn_brightness()
        dawn_threshold_close = self._dawn_config.brightness_threshold
        dawn_close_delay = self._dawn_config.after_seconds
        height_after_dawn = self._dawn_config.height_after_dawn
        angle_after_dawn = self._dawn_config.angle_after_dawn

        is_in_sun = await self._check_if_facade_is_in_sun()
        neutral_height = self._facade_config.neutral_pos_height
        neutral_angle = self._facade_config.neutral_pos_angle

        if dawn_handling_active:
            if (
                dawn_brightness is not None
                and dawn_threshold_close is not None
                and dawn_brightness < dawn_threshold_close
                and dawn_close_delay is not None
            ):
                self.logger.debug(
                    "State %s (%s): Dawn mode active and brightness (%s) below dawn threshold (%s), starting timer for %s (%ss)",
                    ShutterState.DAWN_NEUTRAL,
                    ShutterState.DAWN_NEUTRAL.name,
                    dawn_brightness,
                    dawn_threshold_close,
                    ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING,
                    dawn_close_delay,
                )
                await self._start_timer(dawn_close_delay)
                return ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING
            if (
                is_in_sun
                and shadow_handling_active
                and current_brightness is not None
                and shadow_threshold_close is not None
                and current_brightness > shadow_threshold_close
                and shadow_close_delay is not None
            ):
                self.logger.debug(
                    "State %s (%s): Within sun, shadow mode active and brightness (%s) above shadow threshold (%s), starting timer for %s (%ss)",
                    ShutterState.DAWN_NEUTRAL,
                    ShutterState.DAWN_NEUTRAL.name,
                    current_brightness,
                    shadow_threshold_close,
                    ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING,
                    shadow_close_delay,
                )
                await self._start_timer(shadow_close_delay)
                return ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING
            if height_after_dawn is not None and angle_after_dawn is not None:
                await self._position_shutter(
                    float(height_after_dawn),
                    float(angle_after_dawn),
                    shadow_position=False,
                    stop_timer=True,
                )
                self.logger.debug(
                    "State %s (%s): Moving shutter to after-dawn position (%s%%, %s%%).",
                    ShutterState.DAWN_NEUTRAL,
                    ShutterState.DAWN_NEUTRAL.name,
                    height_after_dawn,
                    angle_after_dawn,
                )
                return ShutterState.DAWN_NEUTRAL
            self.logger.warning(
                "State %s (%s): Height or angle after dawn not configured, staying at %s",
                ShutterState.DAWN_NEUTRAL,
                ShutterState.DAWN_NEUTRAL.name,
                ShutterState.DAWN_NEUTRAL,
            )
            return ShutterState.DAWN_NEUTRAL

        if (
            is_in_sun
            and shadow_handling_active
            and current_brightness is not None
            and shadow_threshold_close is not None
            and current_brightness > shadow_threshold_close
            and shadow_close_delay is not None
        ):
            self.logger.debug(
                "State %s (%s): Within sun, shadow mode active and brightness (%s) above shadow threshold (%s), starting timer for %s (%ss)",
                ShutterState.DAWN_NEUTRAL,
                ShutterState.DAWN_NEUTRAL.name,
                current_brightness,
                shadow_threshold_close,
                ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING,
                shadow_close_delay,
            )
            await self._start_timer(shadow_close_delay)
            return ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING

        if neutral_height is not None and neutral_angle is not None:
            await self._position_shutter(
                float(neutral_height),
                float(neutral_angle),
                shadow_position=False,
                stop_timer=True,
            )
            self.logger.debug(
                "State %s (%s): Dawn mode disabled or requirements for shadow not given, moving to neutral position (%s%%, %s%%)",
                ShutterState.DAWN_NEUTRAL,
                ShutterState.DAWN_NEUTRAL.name,
                neutral_height,
                neutral_angle,
            )
            return ShutterState.NEUTRAL
        self.logger.warning(
            "State %s (%s): Neutral height or angle not configured, transitioning to %s",
            ShutterState.DAWN_NEUTRAL,
            ShutterState.DAWN_NEUTRAL.name,
            ShutterState.NEUTRAL,
        )
        return ShutterState.NEUTRAL

    # =======================================================================
    # State DAWN_NEUTRAL_TIMER_RUNNING
    async def _handle_state_dawn_neutral_timer_running(self) -> ShutterState:
        self.logger.debug("Handle DAWN_NEUTRAL_TIMER_RUNNING")
        if await self._is_dawn_control_enabled():
            dawn_brightness = self._get_current_dawn_brightness()
            dawn_threshold_close = self._dawn_config.brightness_threshold
            dawn_height = self._dawn_config.shutter_max_height
            dawn_open_slat_angle = self._dawn_config.shutter_look_through_angle

            if dawn_brightness is not None and dawn_threshold_close is not None and dawn_brightness < dawn_threshold_close:
                self.logger.debug(
                    "State %s (%s): Dawn brightness (%s) again below threshold (%s), moving to %s and stopping timer",
                    ShutterState.DAWN_NEUTRAL_TIMER_RUNNING,
                    ShutterState.DAWN_NEUTRAL_TIMER_RUNNING.name,
                    dawn_brightness,
                    dawn_threshold_close,
                    ShutterState.DAWN_FULL_CLOSED,
                )
                self._cancel_timer()
                return ShutterState.DAWN_FULL_CLOSED
            if self._is_timer_finished():
                if dawn_height is not None and dawn_open_slat_angle is not None:
                    await self._position_shutter(
                        float(dawn_height),
                        float(dawn_open_slat_angle),
                        shadow_position=False,
                        stop_timer=True,
                    )
                    self.logger.debug(
                        "State %s (%s): Timer finished, moving to dawn height (%s%%) with open slats (%s°) and state %s",
                        ShutterState.DAWN_NEUTRAL_TIMER_RUNNING,
                        ShutterState.DAWN_NEUTRAL_TIMER_RUNNING.name,
                        dawn_height,
                        dawn_open_slat_angle,
                        ShutterState.DAWN_NEUTRAL,
                    )
                    return ShutterState.DAWN_NEUTRAL
                self.logger.warning(
                    "State %s (%s): Dawn height or angle for open slats not configured, staying at %s",
                    ShutterState.DAWN_NEUTRAL_TIMER_RUNNING,
                    ShutterState.DAWN_NEUTRAL_TIMER_RUNNING.name,
                    ShutterState.DAWN_NEUTRAL_TIMER_RUNNING,
                )
                return ShutterState.DAWN_NEUTRAL_TIMER_RUNNING
            self.logger.debug(
                "State %s (%s): Waiting for timer (brightness not low enough)",
                ShutterState.DAWN_NEUTRAL_TIMER_RUNNING,
                ShutterState.DAWN_NEUTRAL_TIMER_RUNNING.name,
            )
            return ShutterState.DAWN_NEUTRAL_TIMER_RUNNING
        neutral_height = self._facade_config.neutral_pos_height
        neutral_angle = self._facade_config.neutral_pos_angle
        if neutral_height is not None and neutral_angle is not None:
            await self._position_shutter(
                float(neutral_height),
                float(neutral_angle),
                shadow_position=False,
                stop_timer=True,  # Stop Timer
            )
            self.logger.debug(
                "State %s (%s): Dawn mode disabled, moving to neutral position (%s%%, %s%%) and state %s",
                ShutterState.DAWN_NEUTRAL_TIMER_RUNNING,
                ShutterState.DAWN_NEUTRAL_TIMER_RUNNING.name,
                neutral_height,
                neutral_angle,
                ShutterState.NEUTRAL,
            )
            return ShutterState.NEUTRAL
        self.logger.warning(
            "State %s (%s): Neutral height or angle not configured, transitioning to %s",
            ShutterState.DAWN_NEUTRAL_TIMER_RUNNING,
            ShutterState.DAWN_NEUTRAL_TIMER_RUNNING.name,
            ShutterState.NEUTRAL,
        )
        return ShutterState.NEUTRAL

        self.logger.debug(
            "State %s (%s): Staying at previous position", ShutterState.DAWN_NEUTRAL_TIMER_RUNNING, ShutterState.DAWN_NEUTRAL_TIMER_RUNNING.name
        )
        return ShutterState.DAWN_NEUTRAL_TIMER_RUNNING

    # =======================================================================
    # State DAWN_HORIZONTAL_NEUTRAL
    async def _handle_state_dawn_horizontal_neutral(self) -> ShutterState:
        self.logger.debug("Handle DAWN_HORIZONTAL_NEUTRAL")
        if await self._is_dawn_control_enabled():
            dawn_brightness = self._get_current_dawn_brightness()
            dawn_threshold_close = self._dawn_config.brightness_threshold
            dawn_height = self._dawn_config.shutter_max_height
            dawn_open_slat_angle = self._dawn_config.shutter_look_through_angle
            dawn_open_shutter_delay = self._dawn_config.shutter_look_through_seconds

            if (
                dawn_brightness is not None
                and dawn_threshold_close is not None
                and dawn_brightness < dawn_threshold_close
                and dawn_height is not None
                and dawn_open_slat_angle is not None
            ):
                await self._position_shutter(
                    float(dawn_height),
                    float(dawn_open_slat_angle),
                    shadow_position=False,
                    stop_timer=False,
                )
                self.logger.debug(
                    "State %s (%s): Dawn brightness (%s) below threshold (%s), moving to dawn height (%s%%) with open slats (%s°) and state %s",
                    ShutterState.DAWN_HORIZONTAL_NEUTRAL,
                    ShutterState.DAWN_HORIZONTAL_NEUTRAL.name,
                    dawn_brightness,
                    dawn_threshold_close,
                    dawn_height,
                    dawn_open_slat_angle,
                    ShutterState.DAWN_FULL_CLOSED,
                )
                return ShutterState.DAWN_FULL_CLOSED
            if dawn_open_shutter_delay is not None:
                self.logger.debug(
                    "State %s (%s): Dawn brightness not below threshold, starting timer for %s (%ss)",
                    ShutterState.DAWN_HORIZONTAL_NEUTRAL,
                    ShutterState.DAWN_HORIZONTAL_NEUTRAL.name,
                    ShutterState.DAWN_NEUTRAL_TIMER_RUNNING,
                    dawn_open_shutter_delay,
                )
                await self._start_timer(dawn_open_shutter_delay)
                return ShutterState.DAWN_NEUTRAL_TIMER_RUNNING
            self.logger.warning(
                "State %s (%s): Dawn brightness not below threshold and 'dawn_open_shutter_delay' not configured, staying at %s",
                ShutterState.DAWN_HORIZONTAL_NEUTRAL,
                ShutterState.DAWN_HORIZONTAL_NEUTRAL.name,
                ShutterState.DAWN_HORIZONTAL_NEUTRAL,
            )
            return ShutterState.DAWN_HORIZONTAL_NEUTRAL
        neutral_height = self._facade_config.neutral_pos_height
        neutral_angle = self._facade_config.neutral_pos_angle
        if neutral_height is not None and neutral_angle is not None:
            await self._position_shutter(
                float(neutral_height),
                float(neutral_angle),
                shadow_position=False,
                stop_timer=True,
            )
            self.logger.debug(
                "State %s (%s): Dawn mode disabled, moving to neutral position (%s%%, %s%%) and state %s",
                ShutterState.DAWN_HORIZONTAL_NEUTRAL,
                ShutterState.DAWN_HORIZONTAL_NEUTRAL.name,
                neutral_height,
                neutral_angle,
                ShutterState.NEUTRAL,
            )
            return ShutterState.NEUTRAL
        self.logger.warning(
            "State %s (%s): Neutral height or angle not configured, transitioning to %s",
            ShutterState.DAWN_HORIZONTAL_NEUTRAL,
            ShutterState.DAWN_HORIZONTAL_NEUTRAL.name,
            ShutterState.NEUTRAL,
        )
        return ShutterState.NEUTRAL

        self.logger.debug(
            "State %s (%s): Staying at previous position", ShutterState.DAWN_HORIZONTAL_NEUTRAL, ShutterState.DAWN_HORIZONTAL_NEUTRAL.name
        )
        return ShutterState.DAWN_HORIZONTAL_NEUTRAL

    # =======================================================================
    # State DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING
    async def _handle_state_dawn_horizontal_neutral_timer_running(self) -> ShutterState:
        self.logger.debug("Handle DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING")
        if await self._is_dawn_control_enabled():
            dawn_brightness = self._get_current_dawn_brightness()
            dawn_threshold_close = self._dawn_config.brightness_threshold
            dawn_height = self._dawn_config.shutter_max_height
            dawn_open_slat_angle = self._dawn_config.shutter_look_through_angle
            if dawn_brightness is not None and dawn_threshold_close is not None and dawn_brightness < dawn_threshold_close:
                self.logger.debug(
                    "State %s (%s): Dawn brightness (%s) again below threshold (%s), moving to %s and stopping timer",
                    ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING,
                    ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING.name,
                    dawn_brightness,
                    dawn_threshold_close,
                    ShutterState.DAWN_FULL_CLOSED,
                )
                self._cancel_timer()
                return ShutterState.DAWN_FULL_CLOSED
            if self._is_timer_finished():
                if dawn_height is not None and dawn_open_slat_angle is not None:
                    await self._position_shutter(
                        float(dawn_height),
                        float(dawn_open_slat_angle),
                        shadow_position=False,
                        stop_timer=False,
                    )
                    self.logger.debug(
                        "State %s (%s): Timer finished, moving to dawn height (%s%%) with open slats (%s°) and state %s",
                        ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING,
                        ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING.name,
                        dawn_height,
                        dawn_open_slat_angle,
                        ShutterState.DAWN_HORIZONTAL_NEUTRAL,
                    )
                    return ShutterState.DAWN_HORIZONTAL_NEUTRAL
                self.logger.warning(
                    "State %s (%s): Dawn height or angle for open slats not configured, staying at %s",
                    ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING,
                    ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING.name,
                    ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING,
                )
                return ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING
            self.logger.debug(
                "State %s (%s): Waiting for timer (brightness not low enough)",
                ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING,
                ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING.name,
            )
            return ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING
        neutral_height = self._facade_config.neutral_pos_height
        neutral_angle = self._facade_config.neutral_pos_angle
        if neutral_height is not None and neutral_angle is not None:
            await self._position_shutter(
                float(neutral_height),
                float(neutral_angle),
                shadow_position=False,
                stop_timer=True,  # Stop Timer
            )
            self.logger.debug(
                "State %s (%s): Dawn mode disabled, moving to neutral position (%s%%, %s%%) and state %s",
                ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING,
                ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING.name,
                neutral_height,
                neutral_angle,
                ShutterState.NEUTRAL,
            )
            return ShutterState.NEUTRAL
        self.logger.warning(
            "State %s (%s): Neutral height or angle not configured, transitioning to %s",
            ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING,
            ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING.name,
            ShutterState.NEUTRAL,
        )
        return ShutterState.NEUTRAL

        self.logger.debug(
            "State %s (%s): Staying at previous position",
            ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING,
            ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING.name,
        )
        return ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING

    # =======================================================================
    # State DAWN_FULL_CLOSED
    async def _handle_state_dawn_full_closed(self) -> ShutterState:
        self.logger.debug("Handle DAWN_FULL_CLOSED")
        if await self._is_dawn_control_enabled():
            dawn_brightness = self._get_current_dawn_brightness()
            dawn_threshold_close = self._dawn_config.brightness_threshold
            dawn_height = self._dawn_config.shutter_max_height
            dawn_open_slat_delay = self._dawn_config.shutter_look_through_seconds
            dawn_angle = self._dawn_config.shutter_max_angle
            if (
                dawn_brightness is not None
                and dawn_threshold_close is not None
                and dawn_brightness > dawn_threshold_close
                and dawn_open_slat_delay is not None
            ):
                self.logger.debug(
                    "State %s (%s): Dawn brightness (%s) above threshold (%s), starting timer for %s (%ss)",
                    ShutterState.DAWN_FULL_CLOSED,
                    ShutterState.DAWN_FULL_CLOSED.name,
                    dawn_brightness,
                    dawn_threshold_close,
                    ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING,
                    dawn_open_slat_delay,
                )
                await self._start_timer(dawn_open_slat_delay)
                return ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING
            if dawn_height is not None and dawn_angle is not None:
                await self._position_shutter(
                    float(dawn_height),
                    float(dawn_angle),
                    shadow_position=False,
                    stop_timer=True,
                )
                self.logger.debug(
                    "State %s (%s): Dawn brightness not above threshold, moving to dawn position (%s%%, %s%%)",
                    ShutterState.DAWN_FULL_CLOSED,
                    ShutterState.DAWN_FULL_CLOSED.name,
                    dawn_height,
                    dawn_angle,
                )
                return ShutterState.DAWN_FULL_CLOSED
            self.logger.warning(
                "State %s (%s): Dawn height or angle not configured, staying at %s",
                ShutterState.DAWN_FULL_CLOSED,
                ShutterState.DAWN_FULL_CLOSED.name,
                ShutterState.DAWN_FULL_CLOSED,
            )
            return ShutterState.DAWN_FULL_CLOSED
        neutral_height = self._facade_config.neutral_pos_height
        neutral_angle = self._facade_config.neutral_pos_angle
        if neutral_height is not None and neutral_angle is not None:
            await self._position_shutter(
                float(neutral_height),
                float(neutral_angle),
                shadow_position=False,
                stop_timer=True,  # Stop Timer
            )
            self.logger.debug(
                "State %s (%s): Dawn handling disabled, moving to neutral position (%s%%, %s%%) and state %s",
                ShutterState.DAWN_FULL_CLOSED,
                ShutterState.DAWN_FULL_CLOSED.name,
                neutral_height,
                neutral_angle,
                ShutterState.NEUTRAL,
            )
            return ShutterState.NEUTRAL
        self.logger.warning(
            "State %s (%s): Neutral height or angle not configured, transitioning to %s",
            ShutterState.DAWN_FULL_CLOSED,
            ShutterState.DAWN_FULL_CLOSED.name,
            ShutterState.NEUTRAL,
        )
        return ShutterState.NEUTRAL

        self.logger.debug("State %s (%s): Staying at previous position", ShutterState.DAWN_FULL_CLOSED, ShutterState.DAWN_FULL_CLOSED.name)
        return ShutterState.DAWN_FULL_CLOSED

    # =======================================================================
    # State DAWN_FULL_CLOSE_TIMER_RUNNING
    async def _handle_state_dawn_full_close_timer_running(self) -> ShutterState:
        self.logger.debug("Handle DAWN_FULL_CLOSE_TIMER_RUNNING")
        if await self._is_dawn_control_enabled():
            dawn_brightness = self._get_current_dawn_brightness()
            dawn_threshold_close = self._dawn_config.brightness_threshold
            dawn_height = self._dawn_config.shutter_max_height
            dawn_angle = self._dawn_config.shutter_max_angle
            if dawn_brightness is not None and dawn_threshold_close is not None and dawn_brightness < dawn_threshold_close:
                if self._is_timer_finished():
                    if dawn_height is not None and dawn_angle is not None:
                        await self._position_shutter(
                            float(dawn_height),
                            float(dawn_angle),
                            shadow_position=False,
                            stop_timer=True,
                        )
                        self.logger.debug(
                            "State %s (%s): Timer finished, moving to dawn position (%s%%, %s%%) and state %s",
                            ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING,
                            ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING.name,
                            dawn_height,
                            dawn_angle,
                            ShutterState.DAWN_FULL_CLOSED,
                        )
                        return ShutterState.DAWN_FULL_CLOSED
                    self.logger.warning(
                        "State %s (%s): Dawn height or angle not configured, staying at %s",
                        ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING,
                        ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING.name,
                        ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING,
                    )
                    return ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING
                self.logger.debug(
                    "State %s (%s): Waiting for timer (brightness low enough)",
                    ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING,
                    ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING.name,
                )
                return ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING
            self.logger.debug(
                "State %s (%s): Brightness (%s) not below threshold (%s), moving to %s and stopping timer",
                ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING,
                ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING.name,
                dawn_brightness,
                dawn_threshold_close,
                ShutterState.DAWN_NEUTRAL,
            )
            self._cancel_timer()
            return ShutterState.DAWN_NEUTRAL
        neutral_height = self._facade_config.neutral_pos_height
        neutral_angle = self._facade_config.neutral_pos_angle
        if neutral_height is not None and neutral_angle is not None:
            await self._position_shutter(
                float(neutral_height),
                float(neutral_angle),
                shadow_position=False,
                stop_timer=True,  # Stop Timer
            )
            self.logger.debug(
                "State %s (%s): Dawn mode disabled, moving to neutral position (%s%%, %s%%) and state %s",
                ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING,
                ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING.name,
                neutral_height,
                neutral_angle,
                ShutterState.NEUTRAL,
            )
            return ShutterState.NEUTRAL
        self.logger.warning(
            "State %s (%s): Neutral height or angle not configured, transitioning to %s",
            ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING,
            ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING.name,
            ShutterState.NEUTRAL,
        )
        return ShutterState.NEUTRAL

        self.logger.debug(
            "State %s (%s): Staying at previous position", ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING, ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING.name
        )
        return ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING

    # End of state handling
    # #######################################################################

    async def _is_shadow_control_enabled(self) -> bool:
        """Check if shadow handling is activated."""
        return self._shadow_config.enabled

    async def _is_dawn_control_enabled(self) -> bool:
        """Check if dawn handling is activated."""
        return self._dawn_config.enabled

    def _get_static_value(self, key: str, default: Any, expected_type: type, log_warning: bool = True) -> Any:
        """Get static value from options with type conversion and default handling."""
        value = self._options.get(key)
        if value is None:
            if log_warning:
                self.logger.debug("Static key '%s' not found in options. Using default: %s", key, default)
            return default
        try:
            if expected_type is bool:  # For boolean selectors (if any static boolean values existed)
                return bool(value)
            return expected_type(value)
        except (ValueError, TypeError):
            if log_warning:
                self.logger.warning(
                    "Static value for key '%s' ('%s') cannot be converted to %s. Using default: %s", key, value, expected_type, default
                )
            return default

    def _get_entity_state_value(self, key: str, default: Any, expected_type: type, log_warning: bool = True) -> Any:
        """Extract dynamic value from an entity state."""
        # Type conversion and default will be handled
        entity_id = self._options.get(key)  # This will be the string entity_id or None

        if entity_id is None or not isinstance(entity_id, str) or entity_id == "":
            # if log_warning:
            #     self.logger.debug("No valid entity_id configured for key '%s' ('%s'). Using default: %s", key, entity_id, default)
            return default

        state = self.hass.states.get(entity_id)

        if state is None or state.state in ["unavailable", "unknown", "none"]:  # 'none' can happen for input_number if not set
            if log_warning:
                self.logger.debug("Entity '%s' for key '%s' is unavailable or unknown. Using default: %s", entity_id, key, default)
            return default

        try:
            if expected_type is bool:
                return state.state == STATE_ON
            if expected_type is int:
                return int(float(state.state))  # Handle cases where state might be "10.0"
            if expected_type is float:
                return float(state.state)
            # For other types, direct conversion might be risky or need specific handling
            return expected_type(state.state)
        except (ValueError, TypeError):
            if log_warning:
                self.logger.warning(
                    "State of entity '%s' for key '%s' ('%s') cannot be converted to %s. Using default: %s",
                    entity_id,
                    key,
                    state.state,
                    expected_type,
                    default,
                )
            return default

    def _get_enum_value(self, key: str, enum_class: type, default_enum_member: Enum, log_warning: bool = True) -> Enum:
        """Get enum member from string value stored in options."""
        value_str = self._options.get(key)

        if value_str is None or not isinstance(value_str, str) or value_str == "":
            if log_warning:
                self.logger.debug("Enum key '%s' not found or empty in options. Using default: %s", key, default_enum_member.name)
            return default_enum_member

        try:
            # Assuming the stored string matches the enum member's name (e.g., "NO_RESTRICTION" or "no_restriction")
            # Convert to upper case to match enum member names
            return enum_class[value_str.upper()]
        except KeyError:
            if log_warning:
                self.logger.warning(
                    "Value '%s' for enum key '%s' is not a valid %s member. Using default: %s",
                    value_str,
                    key,
                    enum_class.__name__,
                    default_enum_member.name,
                )
            return default_enum_member

    def _convert_shutter_angle_percent_to_degrees(self, angle_percent: float) -> float:
        """Convert percent to degrees."""
        # 0% = 0 degrees (Slats open)
        # 100% = 90 degrees (Slats closed)
        # Could be higher than 90° depending on shutter type.
        min_slat_angle = self._facade_config.slat_min_angle
        angle_offset = self._facade_config.slat_angle_offset

        if min_slat_angle is None or angle_offset is None:
            self.logger.warning(
                "_convert_shutter_angle_percent_to_degrees: min_slat_angle (%s) or angle_offset (%s) is None. Using default values (0, 0)",
                min_slat_angle,
                angle_offset,
            )
            min_slat_angle = 0.0
            angle_offset = 0.0

        calculated_degrees = angle_percent * 0.9  # Convert 0-100% into 0-90 degrees

        # Handle angle offset and minimal shutter slat angle
        calculated_degrees += angle_offset
        calculated_degrees = max(min_slat_angle, calculated_degrees)

        self.logger.debug(
            "Angle of %s%% equates to %s° (min_slat_angle=%s, angle_offset=%s)", angle_percent, calculated_degrees, min_slat_angle, angle_offset
        )

        return calculated_degrees

    def _should_output_be_updated(self, config_value: MovementRestricted, new_value: float, previous_value: float | None) -> float:
        """Perform output update check."""
        # Check if the output should be updated, depending on given MovementRestricted configuration
        # New value will be returned if:
        # - config_value is 'ONLY_DOWN' and new value is higher than previous value or
        # - config_value is 'ONLY_UP' and new value is lower than previous value or
        # - config_value is 'NO_RESTRICTION' oder everything else.
        # All other cases will return the previous value.
        if previous_value is None:
            # Return None if there's no previous value (like on the initial run)
            # self.logger.debug(
            #     "_should_output_be_updated: previous_value is None. Returning new value (%s)", new_value)
            return new_value

        # Check if the value was changed at all
        # by using a small tolerance to prevent redundant movements.
        if abs(new_value - previous_value) < 0.001:
            # self.logger.debug(
            #     "_should_output_be_updated: new_value (%s) is nearly identical to previous_value (%s). Returning previous_value",
            #     new_value, previous_value)
            return previous_value

        # self.logger.debug(
        #     "_should_output_be_updated: config_value=%s, new_value=%s, previous_value=%s", config_value.name,
        #     new_value, previous_value)

        if config_value == MovementRestricted.ONLY_CLOSE:
            if new_value > previous_value:
                # self.logger.debug(
                #     "_should_output_be_updated: ONLY_DOWN -> new_value (%s) > previous_value (%s). Returning new_value",
                #     new_value, previous_value)
                return new_value
            # self.logger.debug(
            #     "_should_output_be_updated: ONLY_DOWN -> new_value (%s) <= previous_value (%s). Returning previous_value",
            #     new_value, previous_value)
            return previous_value
        if config_value == MovementRestricted.ONLY_OPEN:
            if new_value < previous_value:
                # self.logger.debug(
                #     "_should_output_be_updated: ONLY_UP -> new_value (%s) < previous_value (%s). Returning new_value",
                #     new_value, previous_value)
                return new_value
            # self.logger.debug(
            #     "_should_output_be_updated: ONLY_UP -> new_value (%s) >= previous_value (%s). Returning previous_value",
            #     new_value, previous_value)
            return previous_value
        if config_value == MovementRestricted.NO_RESTRICTION:
            # self.logger.debug(
            #     "_should_output_be_updated: NO_RESTRICTION -> Returning new_value (%s)", new_value)
            return new_value
        # self.logger.warning(
        #     "_should_output_be_updated: Unknown value '%s'. Returning new_value (%s)", config_value.name, new_value)
        return new_value

    async def _start_timer(self, delay_seconds: float) -> None:
        """Start new timer."""
        self._cancel_timer()

        if delay_seconds <= 0:
            self.logger.debug("Timer delay is <= 0 (%ss). Trigger immediate recalculation", delay_seconds)
            await self._async_calculate_and_apply_cover_position(None)
            # At immediate recalculation, there is no new timer
            self.next_modification_timestamp = None
            return

        # Save start time and duration
        current_utc_time = datetime.now(UTC)
        self._timer_start_time = datetime.now(UTC)
        self._timer_duration_seconds = delay_seconds

        self.next_modification_timestamp = current_utc_time + timedelta(seconds=delay_seconds)
        self.logger.info("Starting timer for %ss, next modification scheduled for: %s", delay_seconds, self.next_modification_timestamp)

        # Save callback handle from async_call_later to enable timer canceling
        self._timer = async_call_later(self.hass, delay_seconds, self._async_timer_callback)

        self._update_extra_state_attributes()

    def _cancel_timer(self) -> None:
        """Cancel running timer."""
        if self._timer:
            self.logger.info("Canceling timer")
            self._timer()
            self._timer = None

        # Reset timer tracking variables
        self._timer_start_time = None
        self._timer_duration_seconds = None
        self.next_modification_timestamp = None

    async def _async_timer_callback(self, now) -> None:
        """Trigger position calculation."""
        self.logger.info("Timer finished, triggering recalculation")
        # Reset vars, as timer is finished
        self._timer = None
        self._timer_start_time = None
        self._timer_duration_seconds = None
        await self._async_calculate_and_apply_cover_position(None)

    def get_remaining_timer_seconds(self) -> float | None:
        """Return remaining time of running timer or None if no timer is running."""
        if self._timer and self._timer_start_time and self._timer_duration_seconds is not None:
            elapsed_time = (datetime.now(UTC) - self._timer_start_time).total_seconds()
            remaining_time = self._timer_duration_seconds - elapsed_time
            return max(0.0, remaining_time)  # Only positive values
        return None

    def _is_timer_finished(self) -> bool:
        """Check if a timer is running."""
        return self._timer is None

    def _calculate_lock_state(self) -> LockState:
        """Calculate the current lock state."""
        if self._dynamic_config.lock_integration_with_position:
            return LockState.LOCKED_MANUALLY_WITH_FORCED_POSITION
        if self._dynamic_config.lock_integration:
            return LockState.LOCKED_MANUALLY
        return LockState.UNLOCKED


# Helper for dynamic log output
def _format_config_object_for_logging(obj, prefix: str = "") -> str:
    """Format the public attributes of a given configuration object into one string."""
    if not obj:
        return f"{prefix}None"

    parts = []
    # `vars(obj)` returns a dictionary of __dict__ attributes of a given object
    for attr, value in vars(obj).items():
        # Skip 'private' attributes, which start with an underscore
        if not attr.startswith("_"):
            parts.append(f"{attr}={value}")

    if not parts:
        return f"{prefix}No attributes to log found."

    return f"{prefix}{', '.join(parts)}"
