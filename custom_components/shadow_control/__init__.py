"""Integration for Shadow Control."""
import datetime
import logging
import math
import re
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Optional, Callable, Awaitable

from homeassistant.components.cover import CoverEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_SUPPORTED_FEATURES,
    STATE_ON, EVENT_HOMEASSISTANT_STARTED
)
from homeassistant.core import HomeAssistant, callback, Event, State
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_state_change_event, async_call_later
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN,
    DOMAIN_DATA_MANAGERS,
    LockState,
    MovementRestricted,
    SCFacadeConfig,
    SCDynamicInput,
    SCShadowInput,
    SCDawnInput,
    ShutterState,
    ShutterType,
    SC_CONF_COVERS,
    SC_CONF_NAME,
    TARGET_COVER_ENTITY_ID,
    DEBUG_ENABLED
)

_GLOBAL_DOMAIN_LOGGER = logging.getLogger(DOMAIN)
_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]

# Setup entry point, which is called at every start of Home Assistant.
# Not specific for config entries.
async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """
    Set up the Shadow Control integration.
    """
    _LOGGER.debug(f"[{DOMAIN}] async_setup called.")

    # Placeholder for all data of this integration within 'hass.data'.
    # Will be used to store things like the ShadowControlManager instances.
    # hass.data[DOMAIN_DATA_MANAGERS] will be a dictionary to map ConfigEntry IDs to manager instances.
    hass.data.setdefault(DOMAIN_DATA_MANAGERS, {})

    _LOGGER.info(f"[{DOMAIN}] Integration 'Shadow Control' base setup complete.")
    return True

# Entry point for setup using ConfigEntry (via ConfigFlow)
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """
    Set up Shadow Control from a config entry.
    """
    _LOGGER.debug(f"[{DOMAIN}] Setting up Shadow Control from config entry: {entry.entry_id}: data={entry.data}, options={entry.options}")

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
    sanitized_instance_name = re.sub(r'\s+', '_', instance_name).lower()
    sanitized_instance_name = re.sub(r'[^a-z0-9_]', '', sanitized_instance_name)

    # Prevent empty name if there were only special characters used
    if not sanitized_instance_name:
        _LOGGER.warning(f"Sanitized logger instance name would be empty, using entry_id as fallback for: '{instance_name}'")
        sanitized_instance_name = entry.entry_id

    instance_logger_name = f"{DOMAIN}.{sanitized_instance_name}"
    instance_specific_logger = logging.getLogger(instance_logger_name)

    if entry.options.get(DEBUG_ENABLED, False):
        instance_specific_logger.setLevel(logging.DEBUG)
        instance_specific_logger.debug(f"Debug log for instance '{instance_name}' activated.")
    else:
        instance_specific_logger.setLevel(logging.INFO)
        instance_specific_logger.debug(f"Debug log for instance '{instance_name}' disabled.")

    # The manager can't work without a configuration.
    if not config_data:
        _LOGGER.error(f"[{manager_name}] Config data (entry.data + entry.options) is empty for entry {entry.entry_id} during setup/reload. This means no configuration could be loaded.")
        return False

    # The cover to handle with this integration
    target_cover_entity_id = config_data.get(TARGET_COVER_ENTITY_ID)

    if not manager_name:
        _LOGGER.error(f"[{DOMAIN}] No manager name found (entry.title was empty) for entry {entry.entry_id}. This should not happen and indicates a deeper problem.")
        return False

    if not target_cover_entity_id:
        _LOGGER.error(f"[{manager_name}] No target cover entity ID found in config for entry {entry.entry_id}.")
        return False

    # Hand over the combined configuration dictionary to the ShadowControlManager
    manager = ShadowControlManager(
        hass,
        config_data,
        entry.entry_id,
        instance_specific_logger
    )

    # Store manager within 'hass.data' to let sensors and other components access it.
    if DOMAIN_DATA_MANAGERS not in hass.data:
        hass.data[DOMAIN_DATA_MANAGERS] = {}
    hass.data[DOMAIN_DATA_MANAGERS][entry.entry_id] = manager
    _LOGGER.debug(f"[{manager_name}] Shadow Control manager stored for entry {entry.entry_id} in {DOMAIN_DATA_MANAGERS}.")

    # Initial start of the manager
    await manager.async_start()

    # Load platforms (like sensors)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Add listeners for update of input values and integration trigger
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    _LOGGER.info(f"[{DOMAIN}] Integration '{manager_name}' successfully set up from config entry.")
    return True

# Entry point to unload a ConfigEntry
async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """
    Unload a config entry.
    """
    _LOGGER.debug(f"[{DOMAIN}] Unloading Shadow Control integration for entry: {entry.entry_id}")

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Stop manager instance
        manager: "ShadowControlManager" = hass.data[DOMAIN_DATA_MANAGERS].pop(entry.entry_id, None)
        if manager:
            await manager.async_stop()

        _LOGGER.info(f"[{DOMAIN}] Shadow Control integration for entry {entry.entry_id} successfully unloaded.")
    else:
        _LOGGER.error(f"[{DOMAIN}] Failed to unload platforms for entry {entry.entry_id}.")

    return unload_ok

async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """
    Handle options update.
    Will be called if the user modifies the configuration using the OptionsFlow.
    """
    _LOGGER.debug(f"[{DOMAIN}] Options update listener triggered for entry {entry.entry_id}.")
    await hass.config_entries.async_reload(entry.entry_id)

class SCDynamicInputConfiguration:
    def __init__(self):
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
    def __init__(self):
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
    def __init__(self):
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
    def __init__(self):
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
    """
    Manages the Shadow Control logic for a single cover.
    """

    def __init__(
            self,
            hass: HomeAssistant,
            config: dict[str, Any],
            entry_id: str,
            instance_logger: logging.Logger
    ):
        self.hass = hass
        self._config = config
        self._entry_id = entry_id
        self.logger = instance_logger

        self._name = config[SC_CONF_NAME]
        self._target_cover_entity_id = config[TARGET_COVER_ENTITY_ID]

        # Check if critical values are missing, even if this might be done within async_setup_entry
        if not self._name:
            self.logger.warning(f"Manager init: Manager name is missing in config for entry {entry_id}. Using fallback.")
            self._name = f"Unnamed Shadow Control ({entry_id})"
        if not self._target_cover_entity_id:
            self.logger.error(f"Manager init: Target cover entity ID is missing in config for entry {entry_id}. This is critical.")
            raise ValueError(f"Target cover entity ID missing for entry {entry_id}")

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
        self._dynamic_config.lock_height = config.get(SCDynamicInput.LOCK_HEIGHT_ENTITY.value)
        self._dynamic_config.lock_angle = config.get(SCDynamicInput.LOCK_ANGLE_ENTITY.value)
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
        self._current_shutter_state: ShutterState = ShutterState.NEUTRAL
        self._current_lock_state: LockState = LockState.UNLOCKED
        self._calculated_shutter_height: float = 0.0
        self._calculated_shutter_angle: float = 0.0
        self._calculated_shutter_angle_degrees: float | None = None
        self._effective_elevation: float | None = None
        self._previous_shutter_height: float | None = None
        self._previous_shutter_angle: float | None = None
        self._is_initial_run: bool = True # Flag for initial integration run
        self._is_producing_shadow: bool = False
        self._next_modification_timestamp: datetime | None = None

        self._last_known_height: float | None = None
        self._last_known_angle: float | None = None
        self._is_external_modification_detected: bool = False
        self._external_modification_timestamp: datetime | None = None

        self._recalculation_timer_start_time: datetime | None = None
        self._recalculation_timer_duration_seconds: float | None = None

        self._listeners: list[Callable[[], None]] = []
        self._recalculation_timer: Callable[[], None] | None = None

        self.logger.debug(f"Manager initialized for target: {self._target_cover_entity_id}.")

    async def async_start(self) -> None:
        """
        Start ShadowControlManager:
        - Register listeners
        - Trigger initial calculation
        Will be called after instantiation of the manager.
        """
        self.logger.debug(f"Starting manager lifecycle...")
        self._async_register_listeners()
        await self._async_calculate_and_apply_cover_position(None)
        self.logger.debug(f"Manager lifecycle started.")

    def _async_register_listeners(self) -> None:
        """
        Register listener for state changes of relevant entities.
        """
        self.logger.debug(f"Registering listeners...")

        # If integration is re-loaded (e.g. by OptionsFlow), Home Assistant is already running.
        # In this case, call logic of _async_home_assistant_started directly.
        if not self.hass.is_running:
            self.logger.debug(f"Home Assistant not yet running, registering startup listener.")
            self.hass.bus.async_listen_once(
                EVENT_HOMEASSISTANT_STARTED, self._async_home_assistant_started
            )
        else:
            self.logger.debug(f"Home Assistant already running, executing startup logic directly.")
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
            SCDawnInput.CONTROL_ENABLED_ENTITY,
        ]:
            # False positive "Expected type 'str' (matched generic type '_KT'), got '() -> Any | () -> Any | () -> Any' instead"
            entity_id = self._config.get(conf_key_enum.value)
            if entity_id:
                tracked_inputs.append(entity_id)

        # Handle movement restriction entities separately as they have a 'no_restriction' value
        if self._config.get(SCDynamicInput.MOVEMENT_RESTRICTION_HEIGHT_ENTITY.value) and \
                self._config[SCDynamicInput.MOVEMENT_RESTRICTION_HEIGHT_ENTITY.value] != "no_restriction":
            tracked_inputs.append(self._config[SCDynamicInput.MOVEMENT_RESTRICTION_HEIGHT_ENTITY.value])
        if self._config.get(SCDynamicInput.MOVEMENT_RESTRICTION_ANGLE_ENTITY.value) and \
                self._config[SCDynamicInput.MOVEMENT_RESTRICTION_ANGLE_ENTITY.value] != "no_restriction":
            tracked_inputs.append(self._config[SCDynamicInput.MOVEMENT_RESTRICTION_ANGLE_ENTITY.value])

        if tracked_inputs:
            self.logger.debug(f"Tracking input entities: {tracked_inputs}")
            self._unsub_callbacks.append(
                async_track_state_change_event(
                    self.hass, tracked_inputs, self._async_state_change_listener
                )
            )

        # Listener of state changes at the handled cover entity to register external changes.
        # Important to recognize manual modification!
        if self._target_cover_entity_id:
            self.logger.debug(f"Tracking target cover entity: {self._target_cover_entity_id}")
            self._unsub_callbacks.append(
                async_track_state_change_event(
                    self.hass,
                    self._target_cover_entity_id,
                    self._async_target_cover_entity_state_change_listener
                )
            )

        self.logger.debug(f"Listeners registered.")

    async def _async_state_change_listener(self, event: Event) -> None:
        """
        Callback for state changes of monitored entities.
        """
        entity_id = event.data.get("entity_id")
        old_state = event.data.get("old_state")
        new_state = event.data.get("new_state")

        self.logger.debug(
            f"State change detected for {entity_id}. "
            f"Old state: {old_state.state if old_state else 'None'}, "
            f"New state: {new_state.state if new_state else 'None'}."
        )

        # Check if state really was changed
        if old_state is None or new_state is None or old_state.state != new_state.state:
            self.logger.debug(f"Input entity '{entity_id}' changed. Triggering recalculation.")
            await self._async_calculate_and_apply_cover_position(None)
        else:
            self.logger.debug(f"State change for {entity_id} detected, but value did not change. No recalculation triggered.")

    async def _async_target_cover_entity_state_change_listener(self, event: Event) -> None:
        """
        Callback for state changes of handled cover entity.
        """
        entity_id = event.data.get("entity_id")
        old_state: Optional[State] = event.data.get("old_state")
        new_state: Optional[State] = event.data.get("new_state")

        self.logger.debug(
            f"Target cover state change detected for {entity_id}. "
            f"Old state: {old_state.state if old_state else 'None'}, "
            f"New state: {new_state.state if new_state else 'None'}."
        )

        # Check if state really was changed
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
            if self._next_modification_timestamp and (
                    (datetime.now(timezone.utc) - self._next_modification_timestamp).total_seconds() < 5 # Less than 5 seconds since last change
            ):
                self.logger.debug(f"Cover state change detected, but appears to be self-initiated. Skipping lock state update.")
                self._next_modification_timestamp = None # Reset for next external change
                return

            self.logger.debug(f"External change detected on target cover '{entity_id}'. (Updating lock state not implemented yet)")

            # TODO: Implement logic for LockState handling e.g. manager.update_lock_state(LockState.LOCKED_BY_EXTERNAL_MODIFICATION)

            pass

        else:
            self.logger.debug(f"Target cover state change detected, but height/angle did not change or no external modification.")

    def unregister_listeners(self) -> None:
        """
        Unregister all listeners for this manager.
        """
        self.logger.debug(f"Unregistering listeners")
        for unsub_func in self._listeners:
            unsub_func()
        self._listeners = []

    async def _async_home_assistant_started(self, event: Event) -> None:
        """
        Callback for start of Home Assistant.
        """
        self.logger.debug(f"Home Assistant started event received. Performing initial calculation.")
        await self._async_calculate_and_apply_cover_position(None)

    async def async_stop(self) -> None:
        """
        Stop ShadowControlManager:
        - Remove listeners
        - Stop timer
        """
        self.logger.debug(f"Stopping manager lifecycle...")
        if self._recalculation_timer:
            self._recalculation_timer()
            self._recalculation_timer = None
            self.logger.debug(f"Recalculation timer cancelled.")

        for unsub_callback in self._unsub_callbacks:
            unsub_callback()
        self._unsub_callbacks.clear()
        self.logger.debug(f"Listeners unregistered.")

        self.logger.debug(f"Manager lifecycle stopped.")

    async def _update_input_values(self, event: Event | None = None) -> None:
        """
        Update all relevant input values from configuration or Home Assistant states.
        """
        # self.logger.debug(f"Updating all input values")

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
            self.logger.warning(f"Invalid shutter type '{shutter_type_str}' configured. Using default 'mode1'.")
            self._facade_config.shutter_type = ShutterType.MODE1

        self._facade_config.light_strip_width = self._get_static_value(SCFacadeConfig.LIGHT_STRIP_WIDTH_STATIC.value, 0.0, float)
        self._facade_config.shutter_height = self._get_static_value(SCFacadeConfig.SHUTTER_HEIGHT_STATIC.value, 1000.0, float)
        self._facade_config.neutral_pos_height = self._get_static_value(SCFacadeConfig.NEUTRAL_POS_HEIGHT_STATIC.value, 0.0, float)
        self._facade_config.neutral_pos_angle = self._get_static_value(SCFacadeConfig.NEUTRAL_POS_ANGLE_STATIC.value, 0.0, float)
        self._facade_config.modification_tolerance_height = self._get_static_value(SCFacadeConfig.MODIFICATION_TOLERANCE_HEIGHT_STATIC.value, 0.0, float)
        self._facade_config.modification_tolerance_angle = self._get_static_value(SCFacadeConfig.MODIFICATION_TOLERANCE_ANGLE_STATIC.value, 0.0, float)

        # Dynamic Inputs (entity states or static values)
        self._dynamic_config.brightness = self._get_entity_state_value(SCDynamicInput.BRIGHTNESS_ENTITY.value, 0.0, float)
        self._dynamic_config.brightness_dawn = self._get_entity_state_value(SCDynamicInput.BRIGHTNESS_DAWN_ENTITY.value, -1.0, float)
        self._dynamic_config.sun_elevation = self._get_entity_state_value(SCDynamicInput.SUN_ELEVATION_ENTITY.value, 0.0, float)
        self._dynamic_config.sun_azimuth = self._get_entity_state_value(SCDynamicInput.SUN_AZIMUTH_ENTITY.value, 0.0, float)
        self._dynamic_config.shutter_current_height = self._get_entity_state_value(SCDynamicInput.SHUTTER_CURRENT_HEIGHT_ENTITY.value, -1.0, float)
        self._dynamic_config.shutter_current_angle = self._get_entity_state_value(SCDynamicInput.SHUTTER_CURRENT_ANGLE_ENTITY.value, -1.0, float)

        self._dynamic_config.lock_integration = self._get_entity_state_value(SCDynamicInput.LOCK_INTEGRATION_ENTITY.value, False, bool)
        self._dynamic_config.lock_integration_with_position = self._get_entity_state_value(SCDynamicInput.LOCK_INTEGRATION_WITH_POSITION_ENTITY.value, False, bool)
        self._current_lock_state = self._calculate_lock_state()

        # Here, lock_height_entity and lock_angle_entity can be static defaults (0.0) or actual entity IDs.
        # Check if the stored value is an entity ID (string) or a static number.
        lock_height_config_value = self._options.get(SCDynamicInput.LOCK_HEIGHT_ENTITY.value)
        if isinstance(lock_height_config_value, (int, float)):
            self._dynamic_config.lock_height = lock_height_config_value
        else: # Assume it's an entity ID if not a number
            self._dynamic_config.lock_height = self._get_entity_state_value(SCDynamicInput.LOCK_HEIGHT_ENTITY.value, 0.0, float)

        lock_angle_config_value = self._options.get(SCDynamicInput.LOCK_ANGLE_ENTITY.value)
        if isinstance(lock_angle_config_value, (int, float)):
            self._dynamic_config.lock_angle = lock_angle_config_value
        else: # Assume it's an entity ID if not a number
            self._dynamic_config.lock_angle = self._get_entity_state_value(SCDynamicInput.LOCK_ANGLE_ENTITY.value, 0.0, float)

        # Movement restrictions (Enum values)
        self._dynamic_config.movement_restriction_height = self._get_enum_value(
            SCDynamicInput.MOVEMENT_RESTRICTION_HEIGHT_ENTITY.value,
            MovementRestricted,
            MovementRestricted.NO_RESTRICTION
        )
        self._dynamic_config.movement_restriction_angle = self._get_enum_value(
            SCDynamicInput.MOVEMENT_RESTRICTION_ANGLE_ENTITY.value,
            MovementRestricted,
            MovementRestricted.NO_RESTRICTION
        )

        self._enforce_position_update = self._get_entity_state_value(SCDynamicInput.ENFORCE_POSITIONING_ENTITY.value, False, bool)

        # Shadow Control Inputs
        shadow_control_enabled_static = self._get_static_value(SCShadowInput.CONTROL_ENABLED_STATIC.value, True, bool, log_warning=False)
        self._shadow_config.enabled = self._get_entity_state_value(SCShadowInput.CONTROL_ENABLED_ENTITY.value, shadow_control_enabled_static, bool)

        # Shadow Brightness Threshold
        shadow_brightness_threshold_static = self._get_static_value(SCShadowInput.BRIGHTNESS_THRESHOLD_STATIC.value, 50000.0, float, log_warning=False)
        self._shadow_config.brightness_threshold = self._get_entity_state_value(SCShadowInput.BRIGHTNESS_THRESHOLD_ENTITY.value, shadow_brightness_threshold_static, float)

        # Shadow After Seconds
        shadow_after_seconds_static = self._get_static_value(SCShadowInput.AFTER_SECONDS_STATIC.value, 15.0, float, log_warning=False)
        self._shadow_config.after_seconds = self._get_entity_state_value(SCShadowInput.AFTER_SECONDS_ENTITY.value, shadow_after_seconds_static, float)

        # Shadow Shutter Max Height
        shadow_shutter_max_height_static = self._get_static_value(SCShadowInput.SHUTTER_MAX_HEIGHT_STATIC.value, 100.0, float, log_warning=False)
        self._shadow_config.shutter_max_height = self._get_entity_state_value(SCShadowInput.SHUTTER_MAX_HEIGHT_ENTITY.value, shadow_shutter_max_height_static, float)

        # Shadow Shutter Max Angle
        shadow_shutter_max_angle_static = self._get_static_value(SCShadowInput.SHUTTER_MAX_ANGLE_STATIC.value, 100.0, float, log_warning=False)
        self._shadow_config.shutter_max_angle = self._get_entity_state_value(SCShadowInput.SHUTTER_MAX_ANGLE_ENTITY.value, shadow_shutter_max_angle_static, float)

        # Shadow Shutter Look Through Seconds
        shadow_shutter_look_through_seconds_static = self._get_static_value(SCShadowInput.SHUTTER_LOOK_THROUGH_SECONDS_STATIC.value, 15.0, float, log_warning=False)
        self._shadow_config.shutter_look_through_seconds = self._get_entity_state_value(SCShadowInput.SHUTTER_LOOK_THROUGH_SECONDS_ENTITY.value, shadow_shutter_look_through_seconds_static, float)

        # Shadow Shutter Open Seconds
        shadow_shutter_open_seconds_static = self._get_static_value(SCShadowInput.SHUTTER_OPEN_SECONDS_STATIC.value, 15.0, float, log_warning=False)
        self._shadow_config.shutter_open_seconds = self._get_entity_state_value(SCShadowInput.SHUTTER_OPEN_SECONDS_ENTITY.value, shadow_shutter_open_seconds_static, float)

        # Shadow Shutter Look Through Angle
        shadow_shutter_look_through_angle_static = self._get_static_value(SCShadowInput.SHUTTER_LOOK_THROUGH_ANGLE_STATIC.value, 0.0, float, log_warning=False)
        self._shadow_config.shutter_look_through_angle = self._get_entity_state_value(SCShadowInput.SHUTTER_LOOK_THROUGH_ANGLE_ENTITY.value, shadow_shutter_look_through_angle_static, float)

        # Shadow Height After Sun
        shadow_height_after_sun_static = self._get_static_value(SCShadowInput.HEIGHT_AFTER_SUN_STATIC.value, 0.0, float, log_warning=False)
        self._shadow_config.height_after_sun = self._get_entity_state_value(SCShadowInput.HEIGHT_AFTER_SUN_ENTITY.value, shadow_height_after_sun_static, float)

        # Shadow Angle After Sun
        shadow_angle_after_sun_static = self._get_static_value(SCShadowInput.ANGLE_AFTER_SUN_STATIC.value, 0.0, float, log_warning=False)
        self._shadow_config.angle_after_sun = self._get_entity_state_value(SCShadowInput.ANGLE_AFTER_SUN_ENTITY.value, shadow_angle_after_sun_static, float)


        # Dawn Control Inputs
        dawn_control_enabled_static = self._get_static_value(SCDawnInput.CONTROL_ENABLED_STATIC.value, True, bool, log_warning=False)
        self._dawn_config.enabled = self._get_entity_state_value(SCDawnInput.CONTROL_ENABLED_ENTITY.value, dawn_control_enabled_static, bool)

        # Dawn Brightness Threshold
        dawn_brightness_threshold_static = self._get_static_value(SCDawnInput.BRIGHTNESS_THRESHOLD_STATIC.value, 500.0, float, log_warning=False)
        self._dawn_config.brightness_threshold = self._get_entity_state_value(SCDawnInput.BRIGHTNESS_THRESHOLD_ENTITY.value, dawn_brightness_threshold_static, float)

        # Dawn After Seconds
        dawn_after_seconds_static = self._get_static_value(SCDawnInput.AFTER_SECONDS_STATIC.value, 15.0, float, log_warning=False)
        self._dawn_config.after_seconds = self._get_entity_state_value(SCDawnInput.AFTER_SECONDS_ENTITY.value, dawn_after_seconds_static, float)

        # Dawn Shutter Max Height
        dawn_shutter_max_height_static = self._get_static_value(SCDawnInput.SHUTTER_MAX_HEIGHT_STATIC.value, 100.0, float, log_warning=False)
        self._dawn_config.shutter_max_height = self._get_entity_state_value(SCDawnInput.SHUTTER_MAX_HEIGHT_ENTITY.value, dawn_shutter_max_height_static, float)

        # Dawn Shutter Max Angle
        dawn_shutter_max_angle_static = self._get_static_value(SCDawnInput.SHUTTER_MAX_ANGLE_STATIC.value, 100.0, float, log_warning=False)
        self._dawn_config.shutter_max_angle = self._get_entity_state_value(SCDawnInput.SHUTTER_MAX_ANGLE_ENTITY.value, dawn_shutter_max_angle_static, float)

        # Dawn Shutter Look Through Seconds
        dawn_shutter_look_through_seconds_static = self._get_static_value(SCDawnInput.SHUTTER_LOOK_THROUGH_SECONDS_STATIC.value, 15.0, float, log_warning=False)
        self._dawn_config.shutter_look_through_seconds = self._get_entity_state_value(SCDawnInput.SHUTTER_LOOK_THROUGH_SECONDS_ENTITY.value, dawn_shutter_look_through_seconds_static, float)

        # Dawn Shutter Open Seconds
        dawn_shutter_open_seconds_static = self._get_static_value(SCDawnInput.SHUTTER_OPEN_SECONDS_STATIC.value, 15.0, float, log_warning=False)
        self._dawn_config.shutter_open_seconds = self._get_entity_state_value(SCDawnInput.SHUTTER_OPEN_SECONDS_ENTITY.value, dawn_shutter_open_seconds_static, float)

        # Dawn Shutter Look Through Angle
        dawn_shutter_look_through_angle_static = self._get_static_value(SCDawnInput.SHUTTER_LOOK_THROUGH_ANGLE_STATIC.value, 0.0, float, log_warning=False)
        self._dawn_config.shutter_look_through_angle = self._get_entity_state_value(SCDawnInput.SHUTTER_LOOK_THROUGH_ANGLE_ENTITY.value, dawn_shutter_look_through_angle_static, float)

        # Dawn Height After Dawn
        dawn_height_after_dawn_static = self._get_static_value(SCDawnInput.HEIGHT_AFTER_DAWN_STATIC.value, 0.0, float, log_warning=False)
        self._dawn_config.height_after_dawn = self._get_entity_state_value(SCDawnInput.HEIGHT_AFTER_DAWN_ENTITY.value, dawn_height_after_dawn_static, float)

        # Dawn Angle After Dawn
        dawn_angle_after_dawn_static = self._get_static_value(SCDawnInput.ANGLE_AFTER_DAWN_STATIC.value, 0.0, float, log_warning=False)
        self._dawn_config.angle_after_dawn = self._get_entity_state_value(SCDawnInput.ANGLE_AFTER_DAWN_ENTITY.value, dawn_angle_after_dawn_static, float)

        self.logger.debug(f"Updated input values:\n"
                      f"{_format_config_object_for_logging(self._facade_config, ' -> Facade config: ')},\n"
                      f"{_format_config_object_for_logging(self._dynamic_config, ' -> Dynamic config: ')},\n"
                      f"{_format_config_object_for_logging(self._shadow_config, ' -> Shadow config: ')},\n"
                      f"{_format_config_object_for_logging(self._dawn_config, ' -> Dawn config: ')}"
                      )

    @callback
    async def _async_handle_input_change(self, event: Event | None) -> None:
        """
        Handle changes to any relevant input entity for this specific cover.
        """
        self.logger.debug(f"Input change detected. Event: {event}")

        await self._async_calculate_and_apply_cover_position(event)

    async def _async_calculate_and_apply_cover_position(self, event: Event | None) -> None:
        """
        Calculate and apply the new cover and tilt position for this specific cover.
        This is where your main Shadow Control logic resides.
        """
        self.logger.debug(f"=====================================================================")
        self.logger.debug(f"Calculating and applying cover positions")

        await self._update_input_values()

        shadow_handling_was_disabled = False
        dawn_handling_was_disabled = False
        
        if event: # Check for real event (not None like at the initial run)
            event_type = event.event_type
            event_data = event.data

            if event_type == "state_changed":
                entity = event_data.get("entity")
                old_state: State | None = event_data.get("old_state")
                new_state: State | None = event_data.get("new_state")

                self.logger.debug(f"State change for entity: {entity}")
                self.logger.debug(f"  Old state: {old_state.state if old_state else 'None'}")
                self.logger.debug(f"  New state: {new_state.state if new_state else 'None'}")

                if entity == SCShadowInput.CONTROL_ENABLED_ENTITY:
                    self.logger.debug(f"Shadow control enable changed to {new_state.state}")
                    shadow_handling_was_disabled = new_state.state == "off"
                elif entity == SCShadowInput.CONTROL_ENABLED_ENTITY:
                    self.logger.debug(f"Dawn control enable changed to {new_state.state}")
                    dawn_handling_was_disabled = new_state.state == "off"
                elif entity == SCDynamicInput.LOCK_INTEGRATION_ENTITY:
                    if new_state.state == "off" and not self._dynamic_config.lock_integration_with_position:
                        self.logger.debug(f"Simple lock was disabled and lock with position is already disabled, enforcing position update")
                        self._enforce_position_update = True
                elif entity == SCDynamicInput.LOCK_INTEGRATION_WITH_POSITION_ENTITY:
                    if new_state.state == "off" and not self._dynamic_config.lock_integration:
                        self.logger.debug(f"Lock with position was disabled and simple lock already disabled, enforcing position update")
                        self._enforce_position_update = True
                    else:
                        self.logger.debug(f"Lock with position enabled, enforcing position update")
                        self._enforce_position_update = True
                elif entity == SCDynamicInput.ENFORCE_POSITIONING_ENTITY:
                    if new_state.state == "on":
                        self.logger.debug(f"Enforced positioning triggered")
                        self._enforce_position_update = True
            elif event_type == "time_changed":
                self.logger.debug(f"Time changed event received")
            else:
                self.logger.debug(f"Unhandled event type: {event_type}")
        else:
            self.logger.debug(f"No specific event data (likely initial run or manual trigger)")

        self._check_if_position_changed_externally(self._dynamic_config.shutter_current_height, self._dynamic_config.shutter_current_angle)
        await self._check_if_facade_is_in_sun()

        if shadow_handling_was_disabled:
            await self._shadow_handling_was_disabled()
        elif dawn_handling_was_disabled:
            await self._dawn_handling_was_disabled()
        else:
            await self._process_shutter_state()

        self._enforce_position_update = False

    async def _check_if_facade_is_in_sun(self) -> bool:
        """
        Calculate if the sun illuminates the given facade.
        """
        self.logger.debug(f"Checking if facade is in sun")

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
            self.logger.debug(f"Not all required values available to compute sun state of facade")
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
        self.logger.debug(f"sun_entry_angle: {sun_entry_angle}, sun_exit_angle: {sun_exit_angle}, sun_exit_angle_calc: {sun_exit_angle_calc}, azimuth_calc: {azimuth_calc}")

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
        self.logger.debug(f"{message}")

        return _sun_between_offsets and _is_elevation_in_range

    def _get_current_brightness(self) -> float:
        return self._dynamic_config.brightness

    def _get_current_dawn_brightness(self) -> float:
        if self._dynamic_config.brightness_dawn is not None and self._dynamic_config.brightness_dawn >= 0:
            return self._dynamic_config.brightness_dawn
        return self._dynamic_config.brightness

    async def _calculate_effective_elevation(self) -> float | None:
        """
        Calculate effective elevation in relation to the facade.
        """

        sun_current_azimuth = self._dynamic_config.sun_azimuth
        sun_current_elevation = self._dynamic_config.sun_elevation
        facade_azimuth = self._facade_config.azimuth

        if sun_current_azimuth is None or sun_current_elevation is None or facade_azimuth is None:
            self.logger.debug(f"Unable to compute effective elevation, not all required values available")
            return None

        self.logger.debug(f"Current sun position (a:e): {sun_current_azimuth}°:{sun_current_elevation}°, facade: {facade_azimuth}°")

        try:
            virtual_depth = math.cos(math.radians(abs(sun_current_azimuth - facade_azimuth)))
            virtual_height = math.tan(math.radians(sun_current_elevation))

            # Prevent division by zero if virtual_depth if very small
            if abs(virtual_depth) < 1e-9:
                effective_elevation = 90.0 if virtual_height > 0 else -90.0
            else:
                effective_elevation = math.degrees(math.atan(virtual_height / virtual_depth))

            self.logger.debug(f"Virtual deep and height of the sun against the facade: {virtual_depth}, {virtual_height}, effektive Elevation: {effective_elevation}")
            return effective_elevation
        except ValueError:
            self.logger.debug(f"Unable to compute effective elevation: Invalid input values")
            return None
        except ZeroDivisionError:
            self.logger.debug(f"Unable to compute effective elevation: Division by zero")
            return None

    # Persistent values
    def _update_extra_state_attributes(self) -> None:
        """
        Helper to update the extra_state_attributes dictionary.
        """
        self._attr_extra_state_attributes = {
            "current_shutter_state": self._current_shutter_state,
            "calculated_shutter_height": self._calculated_shutter_height,
            "calculated_shutter_angle": self._calculated_shutter_angle,
            "calculated_shutter_angle_degrees": self._calculated_shutter_angle_degrees,
            "current_lock_state": self._current_lock_state,
            "next_modification_timestamp": self._next_modification_timestamp,
        }

    async def _shadow_handling_was_disabled(self) -> None:
        # False positive warning "This code is unreachable"
        match self._current_shutter_state:
            case ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING | \
                 ShutterState.SHADOW_FULL_CLOSED | \
                 ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING | \
                 ShutterState.SHADOW_HORIZONTAL_NEUTRAL | \
                 ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING | \
                 ShutterState.SHADOW_NEUTRAL:
                self.logger.debug(f"Shadow handling was disabled, position shutter at neutral height")
                self._cancel_recalculation_timer()
                self._current_shutter_state = ShutterState.NEUTRAL
                self._update_extra_state_attributes()
            case ShutterState.NEUTRAL:
                self.logger.debug(f"Shadow handling was disabled, but shutter already at neutral height. Nothing to do")
            case _:
                self.logger.debug(f"Shadow handling was disabled but currently within a dawn state. Nothing to do")

    async def _dawn_handling_was_disabled(self) -> None:
        # False positive warning "This code is unreachable"
        match self._current_shutter_state:
            case ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING | \
                 ShutterState.DAWN_FULL_CLOSED | \
                 ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING | \
                 ShutterState.DAWN_HORIZONTAL_NEUTRAL | \
                 ShutterState.DAWN_NEUTRAL_TIMER_RUNNING | \
                 ShutterState.DAWN_NEUTRAL:
                self.logger.debug(f"Dawn handling was disabled, position shutter at neutral height")
                self._cancel_recalculation_timer()
                self._current_shutter_state = ShutterState.NEUTRAL
                self._update_extra_state_attributes()
            case ShutterState.NEUTRAL:
                self.logger.debug(f"Dawn handling was disabled, but shutter already at neutral height. Nothing to do")
            case _:
                self.logger.debug(f"Dawn handling was disabled but currently within a shadow state. Nothing to do")

    async def _process_shutter_state(self) -> None:
        """
        Process current shutter state and call corresponding handler functions.
        Handler functions must return the new shutter state.
        """
        self.logger.debug(f"Current shutter state (before processing): {self._current_shutter_state.name} ({self._current_shutter_state.value})")

        handler_func = self._state_handlers.get(self._current_shutter_state)
        new_shutter_state: ShutterState

        if handler_func:
            new_shutter_state = await handler_func()
            if new_shutter_state is not None and new_shutter_state != self._current_shutter_state:
                self.logger.debug(
                    f"State change from {self._current_shutter_state.name} to {new_shutter_state.name}")
                self._current_shutter_state = new_shutter_state
                self._update_extra_state_attributes()
                self.logger.debug(f"Checking if there might be another change required")
                await self._process_shutter_state()
        else:
            self.logger.debug(
                f"No specific handler for current state or locked. Current lock state: {self._current_lock_state.name}")
            self._cancel_recalculation_timer()
            self._update_extra_state_attributes()

        self.logger.debug(f"New shutter state after processing: {self._current_shutter_state.name} ({self._current_shutter_state.value})")

    def _check_if_position_changed_externally(self, current_height, current_angle):
        # Replace functionality with _async_target_cover_entity_state_change_listener
        #self.logger.debug(f"Check for external shutter modification -> TBD")
        pass

    async def _position_shutter(
            self,
            shutter_height_percent: float,
            shutter_angle_percent: float,
            shadow_position: bool,
            stop_timer: bool
    ) -> None:
        """
        Helper to send commands to the cover, which is maintained by this ShadowControlManager instance.
        """
        self.logger.debug(
            f"Starting _position_shutter with target height {shutter_height_percent:.2f}% "
            f"and angle {shutter_angle_percent:.2f}% (is_initial_run: {self._is_initial_run}, "
            f"lock_state: {self._current_lock_state.name})"
        )

        # Always handle timer cancellation if required, regardless of initial run or lock state
        if stop_timer:
            self.logger.debug(f"Canceling timer.")
            self._cancel_recalculation_timer()

        # --- Phase 1: Update internal states that should always reflect the calculation ---
        # These are the *calculated target* values.
        self._calculated_shutter_height = shutter_height_percent
        self._calculated_shutter_angle = shutter_angle_percent
        self._calculated_shutter_angle_degrees = self._convert_shutter_angle_percent_to_degrees(
            shutter_angle_percent)

        # --- Phase 2: Handle initial run special logic ---
        if self._is_initial_run:
            self.logger.info(f"Initial run of integration. Setting internal states. No physical output update.")
            # Only set internal previous values for the *next* run's send-by-change logic.
            # These are now set to the *initial target* values.
            self._previous_shutter_height = shutter_height_percent
            self._previous_shutter_angle = shutter_angle_percent
            self._is_initial_run = False  # Initial run completed

            self._update_extra_state_attributes()
            return  # Exit here, as no physical output should happen on the initial run

        # --- Phase 3: Check for Lock State BEFORE applying stepping/should_output_be_updated and sending commands ---
        # This ensures that calculations still happen, but outputs are skipped.
        is_locked = (self._current_lock_state != LockState.UNLOCKED)
        if is_locked:
            self.logger.info(
                f"Integration is locked ({self._current_lock_state.name}). "
                f"Calculations are running, but physical outputs are skipped."
            )
            # Update internal _previous values here to reflect that if it *were* unlocked,
            # it would have moved to these calculated positions.
            # This prepares for a smooth transition when unlocked.
            self._previous_shutter_height = shutter_height_percent
            self._previous_shutter_angle = shutter_angle_percent

            # if self._enforce_position_update:
            #     entity_id = self._target_cover_entity_id
            #     current_cover_state: State | None = self.hass.states.get(entity_id)
            #
            #     if not current_cover_state:
            #         self.logger.warning(f"Target cover entity '{entity_id}' not found. Cannot send commands.")
            #     else:
            #         shutter_height_percent = self._lock_height_entity_id
            #         shutter_angle_percent = self._lock_angle_entity_id
            #         self.logger.info(f"Integration set to locked with forced position, setting position to {shutter_height_percent:.1f}%/{shutter_angle_percent:.1f}%")
            #         try:
            #             await self.hass.services.async_call(
            #                 "cover",
            #                 "set_cover_position",
            #                 {"entity_id": entity_id, "position": 100 - shutter_height_percent},
            #                 blocking=False
            #             )
            #         except Exception as e:
            #             self.logger.error(f"Failed to set position: {e}")
            #         try:
            #             await self.hass.services.async_call(
            #                 "cover",
            #                 "set_cover_tilt_position",
            #                 {"entity_id": entity_id, "tilt_position": 100 - shutter_angle_percent},
            #                 blocking=False
            #             )
            #         except Exception as e:
            #             self.logger.error(f"Failed to set tilt position: {e}")
            # else:
            #     self.logger.info(
            #         f"Integration is locked ({self._current_lock_state.name}). "
            #         f"Calculations are running, but physical outputs are skipped."
            #     )

            self._update_extra_state_attributes()
            return  # Exit here, nothing else to do

        # --- Phase 4: Apply stepping and output restriction logic (only if not initial run AND not locked) ---
        # Computation is done with the first configured shutter
        entity = self._target_cover_entity_id[0]
        current_cover_state: State | None = self.hass.states.get(entity)

        if not current_cover_state:
            self.logger.warning(f"Target cover entity '{entity}' not found. Cannot send commands.")
            return

        supported_features = current_cover_state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)

        has_pos_service = self.hass.services.has_service("cover", "set_cover_position")
        has_tilt_service = self.hass.services.has_service("cover", "set_cover_tilt_position")

        self.logger.debug(f"Services availability ({entity}): set_cover_position={has_pos_service}, set_cover_tilt_position={has_tilt_service}")

        async_dispatcher_send(
            self.hass,
            f"{DOMAIN}_update_{self._name.lower().replace(' ', '_')}"
        )

        # Height Handling
        height_to_set_percent = self._handle_shutter_height_stepping(shutter_height_percent)
        height_to_set_percent = self._should_output_be_updated(
            config_value=self._dynamic_config.movement_restriction_height,
            new_value=height_to_set_percent,
            previous_value=self._previous_shutter_height
        )

        # Angle Handling - Crucial for "send angle if height changed" logic
        # We need the value of _previous_shutter_height *before* it's updated for height.
        # So, compare the *calculated* `shutter_height_percent` with what was previously *stored*.
        height_calculated_different_from_previous = (
                -0.001 < abs(shutter_height_percent - self._previous_shutter_height) > 0.001) if self._previous_shutter_height is not None else True

        angle_to_set_percent = self._should_output_be_updated(
            config_value=self._dynamic_config.movement_restriction_angle,
            new_value=shutter_angle_percent,
            previous_value=self._previous_shutter_angle
        )

        # --- Phase 5: Send commands if values actually changed (only if not initial run AND not locked) ---
        send_height_command = -0.001 < abs(height_to_set_percent - self._previous_shutter_height) > 0.001 if self._previous_shutter_height is not None else True

        # Send angle command if the angle changed OR if height changed significantly
        send_angle_command = (-0.001 < abs(angle_to_set_percent - self._previous_shutter_angle) > 0.001 if self._previous_shutter_angle is not None else True) or height_calculated_different_from_previous

        if self._enforce_position_update:
            self.logger.debug(f"Enforcing position update")
            send_height_command = True
            send_angle_command = True

        # Position all configured shutters
        for entity in self._target_cover_entity_id:
            current_cover_state: State | None = self.hass.states.get(entity)

            if not current_cover_state:
                self.logger.warning(f"Target cover entity '{entity}' not found. Cannot send commands.")
                continue

            # Height positioning
            if send_height_command or self._enforce_position_update:
                if (supported_features & CoverEntityFeature.SET_POSITION) and has_pos_service:
                    self.logger.info(f"Setting position to {shutter_height_percent:.1f}% (current: {self._previous_shutter_height}).")
                    try:
                        await self.hass.services.async_call(
                            "cover",
                            "set_cover_position",
                            {"entity_id": entity, "position": 100 - shutter_height_percent},
                            blocking=False
                        )
                    except Exception as e:
                        self.logger.error(f"Failed to set position: {e}")
                    self._previous_shutter_height = shutter_height_percent
                else:
                    self.logger.debug(f"Skipping position set. Supported: {supported_features & CoverEntityFeature.SET_POSITION}, Service Found: {has_pos_service}.")
            else:
                self.logger.debug(
                    f"Height '{height_to_set_percent:.2f}%' not sent, value was the same or restricted.")

            # Angle positioning
            if send_angle_command or self._enforce_position_update:
                if (supported_features & CoverEntityFeature.SET_TILT_POSITION) and has_tilt_service:
                    self.logger.info(f"Setting tilt position to {shutter_angle_percent:.1f}% (current: {self._previous_shutter_angle}).")
                    try:
                        await self.hass.services.async_call(
                            "cover",
                            "set_cover_tilt_position",
                            {"entity_id": entity, "tilt_position": 100 - shutter_angle_percent},
                            blocking=False
                        )
                    except Exception as e:
                        self.logger.error(f"Failed to set tilt position: {e}")
                    self._previous_shutter_angle = shutter_angle_percent
                else:
                    self.logger.debug(f"Skipping tilt set. Supported: {supported_features & CoverEntityFeature.SET_TILT_POSITION}, Service Found: {has_tilt_service}.")
            else:
                self.logger.debug(
                    f"Angle '{angle_to_set_percent:.2f}%' not sent, value was the same or restricted.")

        # Always update HA state at the end to reflect the latest internal calculated values and attributes
        self._update_extra_state_attributes()

        self.logger.debug(f"_position_shutter finished.")

    def _calculate_shutter_height(self) -> float:
        """
        Calculate shutter height based on sun position and shadow area configuration.
        Returns height in percent (0-100).
        """
        self.logger.debug(f"Starting calculation of shutter height")

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
                f"Not all required values for calcualation of shutter height available! "
                f"width_of_light_strip={width_of_light_strip}, elevation={elevation}, "
                f"shutter_overall_height={shutter_overall_height}, "
                f"shadow_max_height_percent={shadow_max_height_percent}. "
                f"Using initial default value of {shutter_height_to_set_percent}%")
            return shutter_height_to_set_percent

        if width_of_light_strip != 0:
            # PHP's deg2rad equates to math.radians
            # PHP's tan equates math.tan
            shutter_height_from_bottom_raw = width_of_light_strip * math.tan(
                math.radians(elevation))

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
                    f"Elevation: {elevation}°, Height: {shutter_overall_height}, "
                    f"Light strip width: {width_of_light_strip}, "
                    f"Resulting shutter height: {shutter_height_to_set} ({shutter_height_to_set_percent}%). "
                    f"Is smaller than max height")
            else:
                self.logger.debug(
                    f"Elevation: {elevation}°, Height: {shutter_overall_height}, "
                    f"Light strip width: {width_of_light_strip}, "
                    f"Resulting shutter height ({new_shutter_height}%) is bigger or equal than given max height ({shadow_max_height_percent}%). "
                    f"Using max height")
        else:
            self.logger.debug(
                f"width_of_light_strip is 0. No height calculation required. "
                f"Using default height {shutter_height_to_set_percent}%.")

        return self._handle_shutter_height_stepping(shutter_height_to_set_percent)

    def _handle_shutter_height_stepping(self, calculated_height_percent: float) -> float:
        """
        Modify shutter height according to configured minimal stepping.
        """
        shutter_stepping_percent = self._facade_config.shutter_stepping_height

        if shutter_stepping_percent is None:
            self.logger.warning(
                f"'shutter_stepping_angle' is None. Stepping can't be computed, returning initial angle {calculated_height_percent}%")
            return calculated_height_percent

        # Only apply stepping if the stepping value is not zero and height is not yet a multiple of the stepping
        if shutter_stepping_percent != 0:
            remainder = calculated_height_percent % shutter_stepping_percent
            if remainder != 0:
                # Example: 10% stepping, current height 23%. remainder = 3.
                # 23 + 10 - 3 = 30. (Rounds up to the next full step).
                adjusted_height = calculated_height_percent + shutter_stepping_percent - remainder
                self.logger.debug(
                    f"Adjusting shutter height from {calculated_height_percent:.2f}% "
                    f"to {adjusted_height:.2f}% (stepping: {shutter_stepping_percent:.2f}%)."
                )
                return adjusted_height

        self.logger.debug(
            f"Shutter height {calculated_height_percent:.2f}% "
            f"fits stepping or stepping is 0. No adjustment."
        )
        return calculated_height_percent

    def _calculate_shutter_angle(self) -> float:
        """
        Berechnet den Zielwinkel der Lamellen, um Sonneneinstrahlung zu verhindern.
        Gibt den berechneten Winkel in Prozent (0-100) zurück.
        Calculate shutter slat angle to prevent sun light within the room.
        Returns angle in percent (0-100).
        """
        self.logger.debug(f"Starting calculation of shutter angle")

        elevation = self._dynamic_config.sun_elevation
        azimuth = self._dynamic_config.sun_azimuth  # For logging
        given_shutter_slat_width = self._facade_config.slat_width
        shutter_slat_distance = self._facade_config.slat_distance
        shutter_angle_offset = self._facade_config.slat_angle_offset
        min_shutter_angle_percent = self._facade_config.slat_min_angle
        max_shutter_angle_percent = self._shadow_config.shutter_max_angle
        shutter_type = self._facade_config.shutter_type  # String "90_degree_slats" or "180_degree_slats"

        # Der effektive Elevationswinkel kommt aus der Instanzvariable, die von _check_if_facade_is_in_sun gesetzt wird
        effective_elevation = self._effective_elevation

        if (
                elevation is None or azimuth is None
                or given_shutter_slat_width is None or shutter_slat_distance is None
                or shutter_angle_offset is None or min_shutter_angle_percent is None
                or max_shutter_angle_percent is None or shutter_type is None
                or effective_elevation is None
        ):
            self.logger.warning(
                f"Not all required values for angle calculation available. "
                f"elevation={elevation}, azimuth={azimuth}, "
                f"slat_width={given_shutter_slat_width}, slat_distance={shutter_slat_distance}, "
                f"angle_offset={shutter_angle_offset}, min_angle={min_shutter_angle_percent}, "
                f"max_angle={max_shutter_angle_percent}, shutter_type={shutter_type}, "
                f"effective_elevation={effective_elevation}. Returning 0.0")
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
                f"Argument for asin() out of valid range ({-1 <= asin_arg <= 1}). "
                f"Current value: {asin_arg}. Unable to compute angle, returning 0.0")
            return 0.0

        beta_rad = math.asin(asin_arg)
        beta_deg = math.degrees(beta_rad)

        # $gamma is the angle between vertical and shutter slat
        gamma_deg = 180 - alpha_deg - beta_deg

        # $shutterAnglePercent is the difference between horizontal and shutter slat,
        # so this is the result of the calculation
        shutter_angle_degrees = round(90 - gamma_deg)

        self.logger.debug(f"Elevation/azimuth: {elevation}°/{azimuth}°, "
                      f"resulting effective elevation and shutter angle: "
                      f"{effective_elevation}°/{shutter_angle_degrees}° (without stepping and offset)")

        shutter_angle_percent: float
        if shutter_type == ShutterType.MODE1:
            shutter_angle_percent = shutter_angle_degrees / 0.9
        elif shutter_type == ShutterType.MODE2:
            shutter_angle_percent = shutter_angle_degrees / 1.8 + 50
        else:
            self.logger.warning(
                f"Unknown shutter type '{shutter_type}'. Using default (mode1, 90°)")
            shutter_angle_percent = shutter_angle_degrees / 0.9  # Standardverhalten

        # Make sure, the angle will not be lower than 0
        if shutter_angle_percent < 0:
            shutter_angle_percent = 0.0

        # Round before stepping
        shutter_angle_percent_rounded_for_stepping = round(shutter_angle_percent)

        shutter_angle_percent_with_stepping = self._handle_shutter_angle_stepping(
            shutter_angle_percent_rounded_for_stepping)

        shutter_angle_percent_with_stepping += shutter_angle_offset

        if shutter_angle_percent_with_stepping < min_shutter_angle_percent:
            final_shutter_angle_percent = min_shutter_angle_percent
            self.logger.debug(
                f"Limiting angle to min: {min_shutter_angle_percent}%")
        elif shutter_angle_percent_with_stepping > max_shutter_angle_percent:
            final_shutter_angle_percent = max_shutter_angle_percent
            self.logger.debug(
                f"Limiting angle to max: {max_shutter_angle_percent}%")
        else:
            final_shutter_angle_percent = shutter_angle_percent_with_stepping

        # Round final angle
        final_shutter_angle_percent = round(final_shutter_angle_percent)

        self.logger.debug(
            f"Resulting shutter angle with offset and stepping: {final_shutter_angle_percent}%")
        return float(final_shutter_angle_percent)

    def _handle_shutter_angle_stepping(self, calculated_angle_percent: float) -> float:
        """
        Modify shutter angle according to configured minimal stepping.
        """
        self.logger.debug(
            f"Computing shutter angle stepping for {calculated_angle_percent}%")

        shutter_stepping_percent = self._facade_config.shutter_stepping_angle

        if shutter_stepping_percent is None:
            self.logger.warning(
                f"'shutter_stepping_angle' is None. Stepping can't be computed, returning initial angle {calculated_angle_percent}%")
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
                    f"Adjusting shutter height from {calculated_angle_percent:.2f}% "
                    f"to {adjusted_angle:.2f}% (stepping: {shutter_stepping_percent:.2f}%)."
                )
                return adjusted_angle

        self.logger.debug(
            f"Shutter height {calculated_angle_percent:.2f}% "
            f"fits stepping or stepping is 0. No adjustment."
        )
        return calculated_angle_percent

    # #######################################################################
    # State handling starts here
    #
    # =======================================================================
    # State SHADOW_FULL_CLOSE_TIMER_RUNNING
    async def _handle_state_shadow_full_close_timer_running(self) -> ShutterState:
        self.logger.debug(f"Handle SHADOW_FULL_CLOSE_TIMER_RUNNING")
        if await self._check_if_facade_is_in_sun() and await self._is_shadow_control_enabled():
            current_brightness = self._dynamic_config.brightness
            shadow_threshold_close = self._shadow_config.brightness_threshold
            if (
                    current_brightness is not None
                    and shadow_threshold_close is not None
                    and current_brightness > shadow_threshold_close
            ):
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
                        self.logger.debug(f"State {ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING} ({ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING.name}): Timer finished, brightness above threshold, moving to shadow position ({target_height}%, {target_angle}%). Next state: {ShutterState.SHADOW_FULL_CLOSED}")
                        return ShutterState.SHADOW_FULL_CLOSED
                    else:
                        self.logger.debug(f"State {ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING} ({ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING.name}): Error within calculation of height a/o angle, staying at {ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING}")
                        return ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING
                else:
                    self.logger.debug(f"State {ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING} ({ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING.name}): Waiting for timer (Brightness big enough)")
                    return ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING
            else:
                self.logger.debug(f"State {ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING} ({ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING.name}): Brightness ({current_brightness}) not above threshold ({shadow_threshold_close}), transitioning to {ShutterState.SHADOW_NEUTRAL}")
                self._cancel_recalculation_timer()
                return ShutterState.SHADOW_NEUTRAL
        else:
            neutral_height = self._facade_config.neutral_pos_height
            neutral_angle = self._facade_config.neutral_pos_angle
            if neutral_height is not None and neutral_angle is not None:
                await self._position_shutter(
                    float(neutral_height),
                    float(neutral_angle),
                    shadow_position=False,
                    stop_timer=True,  # Stop Timer
                )
                self.logger.debug(f"State {ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING} ({ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING.name}): Not in the sun or shadow mode disabled, transitioning to ({neutral_height}%, {neutral_angle}%) with state {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL
            else:
                self.logger.warning(f"State {ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING} ({ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING.name}): Neutral height or angle not configured, transitioning to {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL

        self.logger.debug(f"State {ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING} ({ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING.name}): Staying at previous position.")
        return ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING

    # =======================================================================
    # State SHADOW_FULL_CLOSED
    async def _handle_state_shadow_full_closed(self) -> ShutterState:
        self.logger.debug(f"Handle SHADOW_FULL_CLOSED")
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
                self.logger.debug(f"State {ShutterState.SHADOW_FULL_CLOSED} ({ShutterState.SHADOW_FULL_CLOSED.name}): Brightness ({current_brightness}) below threshold ({shadow_threshold_close}), starting timer for {ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING} ({shadow_open_slat_delay}s)")
                await self._start_recalculation_timer(shadow_open_slat_delay)
                return ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING
            else:
                self.logger.debug(f"State {ShutterState.SHADOW_FULL_CLOSED} ({ShutterState.SHADOW_FULL_CLOSED.name}): Brightness not below threshold, recalculating shadow position")
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
        else:
            neutral_height = self._facade_config.neutral_pos_height
            neutral_angle = self._facade_config.neutral_pos_angle
            if neutral_height is not None and neutral_angle is not None:
                await self._position_shutter(
                    float(neutral_height),
                    float(neutral_angle),
                    shadow_position=False,
                    stop_timer=True,  # Stop Timer
                )
                self.logger.debug(f"State {ShutterState.SHADOW_FULL_CLOSED} ({ShutterState.SHADOW_FULL_CLOSED.name}): Not in sun or shadow mode deactivated, moving to neutral position ({neutral_height}%, {neutral_angle}%) und state {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL
            else:
                self.logger.warning(f"State {ShutterState.SHADOW_FULL_CLOSED} ({ShutterState.SHADOW_FULL_CLOSED.name}): Neutral height or angle not configured, moving to state {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL

        self.logger.debug(f"State {ShutterState.SHADOW_FULL_CLOSED} ({ShutterState.SHADOW_FULL_CLOSED.name}): Staying at previous position")
        return ShutterState.SHADOW_FULL_CLOSED

    # =======================================================================
    # State SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING
    async def _handle_state_shadow_horizontal_neutral_timer_running(self) -> ShutterState:
        self.logger.debug(f"Handle SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING")
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
                self.logger.debug(f"State {ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING} ({ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING.name}): Brightness ({current_brightness}) again above threshold ({shadow_threshold_close}), transitioning to {ShutterState.SHADOW_FULL_CLOSED} and stopping timer")
                self._cancel_recalculation_timer()
                return ShutterState.SHADOW_FULL_CLOSED
            else:
                if self._is_timer_finished():
                    target_height = self._calculate_shutter_height()
                    if target_height is not None and shadow_open_slat_angle is not None:
                        await self._position_shutter(
                            target_height,
                            float(shadow_open_slat_angle),
                            shadow_position=False,
                            stop_timer=True,
                        )
                        self.logger.debug(f"State {ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING} ({ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING.name}): Timer finished, moving to height {target_height}% with neutral slats ({shadow_open_slat_angle}°) and state {ShutterState.SHADOW_HORIZONTAL_NEUTRAL}")
                        return ShutterState.SHADOW_HORIZONTAL_NEUTRAL
                    else:
                        self.logger.debug(f"State {ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING} ({ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING.name}): Error during calculation of height and angle for open slats, staying at {ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING}")
                        return ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING
                else:
                    self.logger.debug(f"State {ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING} ({ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING.name}): Waiting for timer (brightness not high enough)")
                    return ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING
        else:
            neutral_height = self._facade_config.neutral_pos_height
            neutral_angle = self._facade_config.neutral_pos_angle
            if neutral_height is not None and neutral_angle is not None:
                await self._position_shutter(
                    float(neutral_height),
                    float(neutral_angle),
                    shadow_position=False,
                    stop_timer=True,  # Stop Timer
                )
                self.logger.debug(f"State {ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING} ({ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING.name}): Not in the sun or shadow mode disabled, moving to neutral position ({neutral_height}%, {neutral_angle}%) and state {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL
            else:
                self.logger.warning(f"State {ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING} ({ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING.name}): Neutral height or angle not configured, transitioning to {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL

        self.logger.debug(f"State {ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING} ({ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING.name}): Staying at previous position")
        return ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING

    # =======================================================================
    # State SHADOW_HORIZONTAL_NEUTRAL
    async def _handle_state_shadow_horizontal_neutral(self) -> ShutterState:
        self.logger.debug(f"Handle SHADOW_HORIZONTAL_NEUTRAL")
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
                    self.logger.debug(f"State {ShutterState.SHADOW_HORIZONTAL_NEUTRAL} ({ShutterState.SHADOW_HORIZONTAL_NEUTRAL.name}): Brightness ({current_brightness}) above threshold ({shadow_threshold_close}), moving to shadow position ({target_height}%, {target_angle}%) and state {ShutterState.SHADOW_FULL_CLOSED}")
                    return ShutterState.SHADOW_FULL_CLOSED
                else:
                    self.logger.warning(f"State {ShutterState.SHADOW_HORIZONTAL_NEUTRAL} ({ShutterState.SHADOW_HORIZONTAL_NEUTRAL.name}): Error at calculating height or angle, staying at {ShutterState.SHADOW_HORIZONTAL_NEUTRAL}")
                    return ShutterState.SHADOW_HORIZONTAL_NEUTRAL
            elif shadow_open_shutter_delay is not None:
                self.logger.debug(f"State {ShutterState.SHADOW_HORIZONTAL_NEUTRAL} ({ShutterState.SHADOW_HORIZONTAL_NEUTRAL.name}): Brightness not above threshold, starting timer for {ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING} ({shadow_open_shutter_delay}s)")
                await self._start_recalculation_timer(shadow_open_shutter_delay)
                return ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING
            else:
                self.logger.warning(f"State {ShutterState.SHADOW_HORIZONTAL_NEUTRAL} ({ShutterState.SHADOW_HORIZONTAL_NEUTRAL.name}): Brightness not above threshold and 'shadow_open_shutter_delay' not configured, staying at {ShutterState.SHADOW_HORIZONTAL_NEUTRAL}")
                return ShutterState.SHADOW_HORIZONTAL_NEUTRAL
        else:
            neutral_height = self._facade_config.neutral_pos_height
            neutral_angle = self._facade_config.neutral_pos_angle
            if neutral_height is not None and neutral_angle is not None:
                await self._position_shutter(
                    float(neutral_height),
                    float(neutral_angle),
                    shadow_position=False,
                    stop_timer=True,  # Stop Timer (falls ein Timer aktiv war)
                )
                self.logger.debug(f"State {ShutterState.SHADOW_HORIZONTAL_NEUTRAL} ({ShutterState.SHADOW_HORIZONTAL_NEUTRAL.name}): Not in sun or shadow mode disabled, moving to neutral position ({neutral_height}%, {neutral_angle}%) and state {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL
            else:
                self.logger.warning(f"State {ShutterState.SHADOW_HORIZONTAL_NEUTRAL} ({ShutterState.SHADOW_HORIZONTAL_NEUTRAL.name}): Neutral height or angle not configured, transitioning to {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL

        self.logger.debug(f"State {ShutterState.SHADOW_HORIZONTAL_NEUTRAL} ({ShutterState.SHADOW_HORIZONTAL_NEUTRAL.name}): Staying at previous position")
        return ShutterState.SHADOW_HORIZONTAL_NEUTRAL

    # =======================================================================
    # State SHADOW_NEUTRAL_TIMER_RUNNING
    async def _handle_state_shadow_neutral_timer_running(self) -> ShutterState:
        self.logger.debug(f"Handle SHADOW_NEUTRAL_TIMER_RUNNING")
        if await self._check_if_facade_is_in_sun() and await self._is_shadow_control_enabled():
            current_brightness = self._get_current_brightness()
            shadow_threshold_close = self._shadow_config.brightness_threshold
            height_after_shadow = self._shadow_config.height_after_sun
            angle_after_shadow = self._shadow_config.angle_after_sun
            if (
                    current_brightness is not None
                    and shadow_threshold_close is not None
                    and current_brightness > shadow_threshold_close
            ):
                self.logger.debug(f"State {ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING} ({ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING.name}): Brightness ({current_brightness}) again above threshold ({shadow_threshold_close}), state {ShutterState.SHADOW_FULL_CLOSED} and stopping timer")
                self._cancel_recalculation_timer()
                return ShutterState.SHADOW_FULL_CLOSED
            else:
                if self._is_timer_finished():
                    if (
                            height_after_shadow is not None
                            and angle_after_shadow is not None
                    ):
                        await self._position_shutter(
                            float(height_after_shadow),
                            float(angle_after_shadow),
                            shadow_position=False,
                            stop_timer=True,
                        )
                        self.logger.debug(f"State {ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING} ({ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING.name}): Timer finished, moving to after-shadow position ({height_after_shadow}%, {angle_after_shadow}°) and state {ShutterState.SHADOW_NEUTRAL}")
                        return ShutterState.SHADOW_NEUTRAL
                    else:
                        self.logger.warning(f"State {ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING} ({ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING.name}): Height or angle after shadow not configured, staying at {ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING}")
                        return ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING
                else:
                    self.logger.debug(f"State {ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING} ({ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING.name}): Waiting for timer (brightness not high enough)")
                    return ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING
        else:
            neutral_height = self._facade_config.neutral_pos_height
            neutral_angle = self._facade_config.neutral_pos_angle
            if neutral_height is not None and neutral_angle is not None:
                await self._position_shutter(
                    float(neutral_height),
                    float(neutral_angle),
                    shadow_position=False,
                    stop_timer=True,  # Stop Timer
                )
                self.logger.debug(f"State {ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING} ({ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING.name}): Not in sun or shadow mode disabled, moving to neutral position ({neutral_height}%, {neutral_angle}%) and state {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL
            else:
                self.logger.warning(f"State {ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING} ({ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING.name}): Neutral height or angle not configured, transitioning to {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL

        self.logger.debug(f"State {ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING} ({ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING.name}): Staying at previous position")
        return ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING

    # =======================================================================
    # State SHADOW_NEUTRAL
    async def _handle_state_shadow_neutral(self) -> ShutterState:
        self.logger.debug(f"Handle SHADOW_NEUTRAL")
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
                self.logger.debug(f"State {ShutterState.SHADOW_NEUTRAL} ({ShutterState.SHADOW_NEUTRAL.name}): Brightness ({current_brightness}) above threshold ({shadow_threshold_close}), starting timer for {ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING} ({shadow_close_delay}s)")
                await self._start_recalculation_timer(shadow_close_delay)
                return ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING
            elif (
                    dawn_handling_active
                    and dawn_brightness is not None
                    and dawn_threshold_close is not None
                    and dawn_brightness < dawn_threshold_close
                    and dawn_close_delay is not None
            ):
                self.logger.debug(f"State {ShutterState.SHADOW_NEUTRAL} ({ShutterState.SHADOW_NEUTRAL.name}): Dawn handling active and dawn-brighness ({dawn_brightness}) below threshold ({dawn_threshold_close}), starting timer for {ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING} ({dawn_close_delay}s)")
                await self._start_recalculation_timer(dawn_close_delay)
                return ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING
            elif height_after_shadow is not None and angle_after_shadow is not None:
                await self._position_shutter(
                    float(height_after_shadow),
                    float(angle_after_shadow),
                    shadow_position=False,
                    stop_timer=True,
                )
                self.logger.debug(f"State {ShutterState.SHADOW_NEUTRAL} ({ShutterState.SHADOW_NEUTRAL.name}): Moving to after-shadow position ({height_after_shadow}%, {angle_after_shadow}%)")
                return ShutterState.SHADOW_NEUTRAL
            else:
                self.logger.warning(f"State {ShutterState.SHADOW_NEUTRAL} ({ShutterState.SHADOW_NEUTRAL.name}): Height or angle after shadow not configured, staying at {ShutterState.SHADOW_NEUTRAL}")
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
                self.logger.debug(f"State {ShutterState.SHADOW_NEUTRAL.name} ({ShutterState.SHADOW_NEUTRAL.name.name}): Dawn mode active and brightness ({dawn_brightness}) below threshold ({dawn_threshold_close}), starting timer for {ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING} ({dawn_close_delay}s)")
                await self._start_recalculation_timer(dawn_close_delay)
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
            self.logger.debug(f"State {ShutterState.SHADOW_NEUTRAL} ({ShutterState.SHADOW_NEUTRAL.name}): Not in sun or shadow mode disabled or dawn mode not active, moving to neutral position ({neutral_height}%, {neutral_angle}%) and state {ShutterState.NEUTRAL}")
            return ShutterState.NEUTRAL
        else:
            self.logger.warning(f"State {ShutterState.SHADOW_NEUTRAL} ({ShutterState.SHADOW_NEUTRAL.name}): Neutral height or angle not configured, transitioning to {ShutterState.NEUTRAL}")
            return ShutterState.NEUTRAL

    # =======================================================================
    # State NEUTRAL
    async def _handle_state_neutral(self) -> ShutterState:
        self.logger.debug(f"Handle NEUTRAL")
        if await self._check_if_facade_is_in_sun() and await self._is_shadow_control_enabled():
            self.logger.debug(f"self._check_if_facade_is_in_sun and self._is_shadow_handling_activated")
            current_brightness = self._get_current_brightness()
            shadow_threshold_close = self._shadow_config.brightness_threshold
            shadow_close_delay = self._shadow_config.after_seconds
            if (
                    current_brightness is not None
                    and shadow_threshold_close is not None
                    and current_brightness > shadow_threshold_close
                    and shadow_close_delay is not None
            ):
                self.logger.debug(f"State {ShutterState.NEUTRAL} ({ShutterState.NEUTRAL.name}): Brightness ({current_brightness}) above dawn threshold ({shadow_threshold_close}), starting timer for {ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING} ({shadow_close_delay}s)")
                await self._start_recalculation_timer(shadow_close_delay)
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
                self.logger.debug(f"State {ShutterState.NEUTRAL} ({ShutterState.NEUTRAL.name}): Dawn mode active and brightness ({dawn_brightness}) below dawn threshold ({dawn_threshold_close}), starting timer for {ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING} ({dawn_close_delay}s)")
                await self._start_recalculation_timer(dawn_close_delay)
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
            self.logger.debug(f"State {ShutterState.NEUTRAL} ({ShutterState.NEUTRAL.name}): Moving shutter to neutral position ({neutral_height}%, {neutral_angle}%).")
        return ShutterState.NEUTRAL

    # =======================================================================
    # State DAWN_NEUTRAL
    async def _handle_state_dawn_neutral(self) -> ShutterState:
        self.logger.debug(f"Handle DAWN_NEUTRAL")
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
                self.logger.debug(f"State {ShutterState.DAWN_NEUTRAL} ({ShutterState.DAWN_NEUTRAL.name}): Dawn mode active and brightness ({dawn_brightness}) below dawn threshold ({dawn_threshold_close}), starting timer for {ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING} ({dawn_close_delay}s)")
                await self._start_recalculation_timer(dawn_close_delay)
                return ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING
            elif (
                    is_in_sun
                    and shadow_handling_active
                    and current_brightness is not None
                    and shadow_threshold_close is not None
                    and current_brightness > shadow_threshold_close
                    and shadow_close_delay is not None
            ):
                self.logger.debug(f"State {ShutterState.DAWN_NEUTRAL} ({ShutterState.DAWN_NEUTRAL.name}): Within sun, shadow mode active and brightness ({current_brightness}) above shadow threshold ({shadow_threshold_close}), starting timer for {ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING} ({shadow_close_delay}s)")
                await self._start_recalculation_timer(shadow_close_delay)
                return ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING
            elif height_after_dawn is not None and angle_after_dawn is not None:
                await self._position_shutter(
                    float(height_after_dawn),
                    float(angle_after_dawn),
                    shadow_position=False,
                    stop_timer=True,
                )
                self.logger.debug(f"State {ShutterState.DAWN_NEUTRAL} ({ShutterState.DAWN_NEUTRAL.name}): Moving shutter to after-dawn position ({height_after_dawn}%, {angle_after_dawn}%).")
                return ShutterState.DAWN_NEUTRAL
            else:
                self.logger.warning(f"State {ShutterState.DAWN_NEUTRAL} ({ShutterState.DAWN_NEUTRAL.name}): Height or angle after dawn not configured, staying at {ShutterState.DAWN_NEUTRAL}")
                return ShutterState.DAWN_NEUTRAL

        if (
                is_in_sun
                and shadow_handling_active
                and current_brightness is not None
                and shadow_threshold_close is not None
                and current_brightness > shadow_threshold_close
                and shadow_close_delay is not None
        ):
            self.logger.debug(f"State {ShutterState.DAWN_NEUTRAL} ({ShutterState.DAWN_NEUTRAL.name}): Within sun, shadow mode active and brightness ({current_brightness}) above shadow threshold ({shadow_threshold_close}), starting timer for {ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING} ({shadow_close_delay}s)")
            await self._start_recalculation_timer(shadow_close_delay)
            return ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING

        if neutral_height is not None and neutral_angle is not None:
            await self._position_shutter(
                float(neutral_height),
                float(neutral_angle),
                shadow_position=False,
                stop_timer=True,
            )
            self.logger.debug(f"State {ShutterState.DAWN_NEUTRAL} ({ShutterState.DAWN_NEUTRAL.name}): Dawn mode disabled or requirements for shadow not given, moving to neutral position ({neutral_height}%, {neutral_angle}%)")
            return ShutterState.NEUTRAL
        else:
            self.logger.warning(f"State {ShutterState.DAWN_NEUTRAL} ({ShutterState.DAWN_NEUTRAL.name}): Neutral height or angle not configured, transitioning to {ShutterState.NEUTRAL}")
            return ShutterState.NEUTRAL

    # =======================================================================
    # State DAWN_NEUTRAL_TIMER_RUNNING
    async def _handle_state_dawn_neutral_timer_running(self) -> ShutterState:
        self.logger.debug(f"Handle DAWN_NEUTRAL_TIMER_RUNNING")
        if await self._is_dawn_control_enabled():
            dawn_brightness = self._get_current_dawn_brightness()
            dawn_threshold_close = self._dawn_config.brightness_threshold
            dawn_height = self._dawn_config.shutter_max_height
            dawn_open_slat_angle = self._dawn_config.shutter_look_through_angle

            if (
                    dawn_brightness is not None
                    and dawn_threshold_close is not None
                    and dawn_brightness < dawn_threshold_close
            ):
                self.logger.debug(f"State {ShutterState.DAWN_NEUTRAL_TIMER_RUNNING} ({ShutterState.DAWN_NEUTRAL_TIMER_RUNNING.name}): Dawn brightness ({dawn_brightness}) again below threshold ({dawn_threshold_close}), moving to {ShutterState.DAWN_FULL_CLOSED} and stopping timer")
                self._cancel_recalculation_timer()
                return ShutterState.DAWN_FULL_CLOSED
            else:
                if self._is_timer_finished():
                    if dawn_height is not None and dawn_open_slat_angle is not None:
                        await self._position_shutter(
                            float(dawn_height),
                            float(dawn_open_slat_angle),
                            shadow_position=False,
                            stop_timer=True,
                        )
                        self.logger.debug(f"State {ShutterState.DAWN_NEUTRAL_TIMER_RUNNING} ({ShutterState.DAWN_NEUTRAL_TIMER_RUNNING.name}): Timer finished, moving to dawn height ({dawn_height}%) with open slats ({dawn_open_slat_angle}°) and state {ShutterState.DAWN_NEUTRAL}")
                        return ShutterState.DAWN_NEUTRAL
                    else:
                        self.logger.warning(f"State {ShutterState.DAWN_NEUTRAL_TIMER_RUNNING} ({ShutterState.DAWN_NEUTRAL_TIMER_RUNNING.name}): Dawn height or angle for open slats not configured, staying at {ShutterState.DAWN_NEUTRAL_TIMER_RUNNING}")
                        return ShutterState.DAWN_NEUTRAL_TIMER_RUNNING
                else:
                    self.logger.debug(f"State {ShutterState.DAWN_NEUTRAL_TIMER_RUNNING} ({ShutterState.DAWN_NEUTRAL_TIMER_RUNNING.name}): Waiting for timer (brightness not low enough)")
                    return ShutterState.DAWN_NEUTRAL_TIMER_RUNNING
        else:
            neutral_height = self._facade_config.neutral_pos_height
            neutral_angle = self._facade_config.neutral_pos_angle
            if neutral_height is not None and neutral_angle is not None:
                await self._position_shutter(
                    float(neutral_height),
                    float(neutral_angle),
                    shadow_position=False,
                    stop_timer=True,  # Stop Timer
                )
                self.logger.debug(f"State {ShutterState.DAWN_NEUTRAL_TIMER_RUNNING} ({ShutterState.DAWN_NEUTRAL_TIMER_RUNNING.name}): Dawn mode disabled, moving to neutral position ({neutral_height}%, {neutral_angle}%) and state {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL
            else:
                self.logger.warning(f"State {ShutterState.DAWN_NEUTRAL_TIMER_RUNNING} ({ShutterState.DAWN_NEUTRAL_TIMER_RUNNING.name}): Neutral height or angle not configured, transitioning to {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL

        self.logger.debug(f"State {ShutterState.DAWN_NEUTRAL_TIMER_RUNNING} ({ShutterState.DAWN_NEUTRAL_TIMER_RUNNING.name}): Staying at previous position")
        return ShutterState.DAWN_NEUTRAL_TIMER_RUNNING

    # =======================================================================
    # State DAWN_HORIZONTAL_NEUTRAL
    async def _handle_state_dawn_horizontal_neutral(self) -> ShutterState:
        self.logger.debug(f"Handle DAWN_HORIZONTAL_NEUTRAL")
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
                self.logger.debug(f"State {ShutterState.DAWN_HORIZONTAL_NEUTRAL} ({ShutterState.DAWN_HORIZONTAL_NEUTRAL.name}): Dawn brightness ({dawn_brightness}) below threshold ({dawn_threshold_close}), moving to dawn height ({dawn_height}%) with open slats ({dawn_open_slat_angle}°) and state {ShutterState.DAWN_FULL_CLOSED}")
                return ShutterState.DAWN_FULL_CLOSED
            elif dawn_open_shutter_delay is not None:
                self.logger.debug(f"State {ShutterState.DAWN_HORIZONTAL_NEUTRAL} ({ShutterState.DAWN_HORIZONTAL_NEUTRAL.name}): Dawn brightness not below threshold, starting timer for {ShutterState.DAWN_NEUTRAL_TIMER_RUNNING} ({dawn_open_shutter_delay}s)")
                await self._start_recalculation_timer(dawn_open_shutter_delay)
                return ShutterState.DAWN_NEUTRAL_TIMER_RUNNING
            else:
                self.logger.warning(f"State {ShutterState.DAWN_HORIZONTAL_NEUTRAL} ({ShutterState.DAWN_HORIZONTAL_NEUTRAL.name}): Dawn brightness not below threshold and 'dawn_open_shutter_delay' not configured, staying at {ShutterState.DAWN_HORIZONTAL_NEUTRAL}")
                return ShutterState.DAWN_HORIZONTAL_NEUTRAL
        else:
            neutral_height = self._facade_config.neutral_pos_height
            neutral_angle = self._facade_config.neutral_pos_angle
            if neutral_height is not None and neutral_angle is not None:
                await self._position_shutter(
                    float(neutral_height),
                    float(neutral_angle),
                    shadow_position=False,
                    stop_timer=True,
                )
                self.logger.debug(f"State {ShutterState.DAWN_HORIZONTAL_NEUTRAL} ({ShutterState.DAWN_HORIZONTAL_NEUTRAL.name}): Dawn mode disabled, moving to neutral position ({neutral_height}%, {neutral_angle}%) and state {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL
            else:
                self.logger.warning(f"State {ShutterState.DAWN_HORIZONTAL_NEUTRAL} ({ShutterState.DAWN_HORIZONTAL_NEUTRAL.name}): Neutral height or angle not configured, transitioning to {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL

        self.logger.debug(f"State {ShutterState.DAWN_HORIZONTAL_NEUTRAL} ({ShutterState.DAWN_HORIZONTAL_NEUTRAL.name}): Staying at previous position")
        return ShutterState.DAWN_HORIZONTAL_NEUTRAL

    # =======================================================================
    # State DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING
    async def _handle_state_dawn_horizontal_neutral_timer_running(self) -> ShutterState:
        self.logger.debug(f"Handle DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING")
        if await self._is_dawn_control_enabled():
            dawn_brightness = self._get_current_dawn_brightness()
            dawn_threshold_close = self._dawn_config.brightness_threshold
            dawn_height = self._dawn_config.shutter_max_height
            dawn_open_slat_angle = self._dawn_config.shutter_look_through_angle
            if (
                    dawn_brightness is not None
                    and dawn_threshold_close is not None
                    and dawn_brightness < dawn_threshold_close
            ):
                self.logger.debug(f"State {ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING} ({ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING.name}): Dawn brightness ({dawn_brightness}) again below threshold ({dawn_threshold_close}), moving to {ShutterState.DAWN_FULL_CLOSED} and stopping timer")
                self._cancel_recalculation_timer()
                return ShutterState.DAWN_FULL_CLOSED
            else:
                if self._is_timer_finished():
                    if dawn_height is not None and dawn_open_slat_angle is not None:
                        await self._position_shutter(
                            float(dawn_height),
                            float(dawn_open_slat_angle),
                            shadow_position=False,
                            stop_timer=False,
                        )
                        self.logger.debug(f"State {ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING} ({ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING.name}): Timer finished, moving to dawn height ({dawn_height}%) with open slats ({dawn_open_slat_angle}°) and state {ShutterState.DAWN_HORIZONTAL_NEUTRAL}")
                        return ShutterState.DAWN_HORIZONTAL_NEUTRAL
                    else:
                        self.logger.warning(f"State {ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING} ({ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING.name}): Dawn height or angle for open slats not configured, staying at {ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING}")
                        return ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING
                else:
                    self.logger.debug(f"State {ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING} ({ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING.name}): Waiting for timer (brightness not low enough)")
                    return ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING
        else:
            neutral_height = self._facade_config.neutral_pos_height
            neutral_angle = self._facade_config.neutral_pos_angle
            if neutral_height is not None and neutral_angle is not None:
                await self._position_shutter(
                    float(neutral_height),
                    float(neutral_angle),
                    shadow_position=False,
                    stop_timer=True,  # Stop Timer
                )
                self.logger.debug(f"State {ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING} ({ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING.name}): Dawn mode disabled, moving to neutral position ({neutral_height}%, {neutral_angle}%) and state {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL
            else:
                self.logger.warning(f"State {ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING} ({ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING.name}): Neutral height or angle not configured, transitioning to {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL

        self.logger.debug(f"State {ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING} ({ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING.name}): Staying at previous position")
        return ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING

    # =======================================================================
    # State DAWN_FULL_CLOSED
    async def _handle_state_dawn_full_closed(self) -> ShutterState:
        self.logger.debug(f"Handle DAWN_FULL_CLOSED")
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
                self.logger.debug(f"State {ShutterState.DAWN_FULL_CLOSED} ({ShutterState.DAWN_FULL_CLOSED.name}): Dawn brightness ({dawn_brightness}) above threshold ({dawn_threshold_close}), starting timer for {ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING} ({dawn_open_slat_delay}s)")
                await self._start_recalculation_timer(dawn_open_slat_delay)
                return ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING
            elif dawn_height is not None and dawn_angle is not None:
                await self._position_shutter(
                    float(dawn_height),
                    float(dawn_angle),
                    shadow_position=False,
                    stop_timer=True,
                )
                self.logger.debug(f"State {ShutterState.DAWN_FULL_CLOSED} ({ShutterState.DAWN_FULL_CLOSED.name}): Dawn brightness not above threshold, moving to dawn position ({dawn_height}%, {dawn_angle}%)")
                return ShutterState.DAWN_FULL_CLOSED
            else:
                self.logger.warning(f"State {ShutterState.DAWN_FULL_CLOSED} ({ShutterState.DAWN_FULL_CLOSED.name}): Dawn height or angle not configured, staying at {ShutterState.DAWN_FULL_CLOSED}")
                return ShutterState.DAWN_FULL_CLOSED
        else:
            neutral_height = self._facade_config.neutral_pos_height
            neutral_angle = self._facade_config.neutral_pos_angle
            if neutral_height is not None and neutral_angle is not None:
                await self._position_shutter(
                    float(neutral_height),
                    float(neutral_angle),
                    shadow_position=False,
                    stop_timer=True,  # Stop Timer
                )
                self.logger.debug(f"State {ShutterState.DAWN_FULL_CLOSED} ({ShutterState.DAWN_FULL_CLOSED.name}): Dawn handling disabled, moving to neutral position ({neutral_height}%, {neutral_angle}%) and state {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL
            else:
                self.logger.warning(f"State {ShutterState.DAWN_FULL_CLOSED} ({ShutterState.DAWN_FULL_CLOSED.name}): Neutral height or angle not configured, transitioning to {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL

        self.logger.debug(f"State {ShutterState.DAWN_FULL_CLOSED} ({ShutterState.DAWN_FULL_CLOSED.name}): Staying at previous position")
        return ShutterState.DAWN_FULL_CLOSED

    # =======================================================================
    # State DAWN_FULL_CLOSE_TIMER_RUNNING
    async def _handle_state_dawn_full_close_timer_running(self) -> ShutterState:
        self.logger.debug(f"Handle DAWN_FULL_CLOSE_TIMER_RUNNING")
        if await self._is_dawn_control_enabled():
            dawn_brightness = self._get_current_dawn_brightness()
            dawn_threshold_close = self._dawn_config.brightness_threshold
            dawn_height = self._dawn_config.shutter_max_height
            dawn_angle = self._dawn_config.shutter_max_angle
            if (
                    dawn_brightness is not None
                    and dawn_threshold_close is not None
                    and dawn_brightness < dawn_threshold_close
            ):
                if self._is_timer_finished():
                    if dawn_height is not None and dawn_angle is not None:
                        await self._position_shutter(
                            float(dawn_height),
                            float(dawn_angle),
                            shadow_position=False,
                            stop_timer=True,
                        )
                        self.logger.debug(f"State {ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING} ({ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING.name}): Timer finished, moving to dawn position ({dawn_height}%, {dawn_angle}%) and state {ShutterState.DAWN_FULL_CLOSED}")
                        return ShutterState.DAWN_FULL_CLOSED
                    else:
                        self.logger.warning(f"State {ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING} ({ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING.name}): Dawn height or angle not configured, staying at {ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING}")
                        return ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING
                else:
                    self.logger.debug(f"State {ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING} ({ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING.name}): Waiting for timer (brightness low enough)")
                    return ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING
            else:
                self.logger.debug(f"State {ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING} ({ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING.name}): Brightness ({dawn_brightness}) not below threshold ({dawn_threshold_close}), moving to {ShutterState.DAWN_NEUTRAL} and stopping timer")
                self._cancel_recalculation_timer()
                return ShutterState.DAWN_NEUTRAL
        else:
            neutral_height = self._facade_config.neutral_pos_height
            neutral_angle = self._facade_config.neutral_pos_angle
            if neutral_height is not None and neutral_angle is not None:
                await self._position_shutter(
                    float(neutral_height),
                    float(neutral_angle),
                    shadow_position=False,
                    stop_timer=True,  # Stop Timer
                )
                self.logger.debug(f"State {ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING} ({ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING.name}): Dawn mode disabled, moving to neutral position ({neutral_height}%, {neutral_angle}%) and state {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL
            else:
                self.logger.warning(f"State {ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING} ({ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING.name}): Neutral height or angle not configured, transitioning to {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL

        self.logger.debug(f"State {ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING} ({ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING.name}): Staying at previous position")
        return ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING

    # End of state handling
    # #######################################################################

    async def _is_shadow_control_enabled(self) -> bool:
        """
        Check if shadow handling is activated.
        """
        return self._shadow_config.enabled

    async def _is_dawn_control_enabled(self) -> bool:
        """
        Check if dawn handling is activated.
        """
        return self._dawn_config.enabled

    def _get_static_value(self, key: str, default: Any, expected_type: type, log_warning: bool = True) -> Any:
        """
        Gets a static value directly from options, with type conversion and default.
        """
        value = self._options.get(key)
        if value is None:
            if log_warning:
                self.logger.debug(f"Static key '{key}' not found in options. Using default: {default}")
            return default
        try:
            if expected_type == bool: # For boolean selectors (if any static boolean values existed)
                return bool(value)
            return expected_type(value)
        except (ValueError, TypeError):
            if log_warning:
                self.logger.warning(f"Static value for key '{key}' ('{value}') cannot be converted to {expected_type}. Using default: {default}")
            return default

    def _get_entity_state_value(self, key: str, default: Any, expected_type: type, log_warning: bool = True) -> Any:
        """
        Gets a dynamic value from an entity state, with type conversion and default.
        """
        entity_id = self._options.get(key) # This will be the string entity_id or None

        if entity_id is None or not isinstance(entity_id, str) or entity_id == '':
            # if log_warning:
            #     self.logger.debug(f"No valid entity_id configured for key '{key}' ('{entity_id}'). Using default: {default}")
            return default

        state = self.hass.states.get(entity_id)

        if state is None or state.state in ['unavailable', 'unknown', 'none']: # 'none' can happen for input_number if not set
            if log_warning:
                self.logger.debug(f"Entity '{entity_id}' for key '{key}' is unavailable or unknown. Using default: {default}")
            return default

        try:
            if expected_type == bool:
                return state.state == STATE_ON
            elif expected_type == int:
                return int(float(state.state)) # Handle cases where state might be "10.0"
            elif expected_type == float:
                return float(state.state)
            # For other types, direct conversion might be risky or need specific handling
            return expected_type(state.state)
        except (ValueError, TypeError):
            if log_warning:
                self.logger.warning(f"State of entity '{entity_id}' for key '{key}' ('{state.state}') cannot be converted to {expected_type}. Using default: {default}")
            return default

    def _get_enum_value(self, key: str, enum_class: type, default_enum_member: Enum, log_warning: bool = True) -> Enum:
        """
        Gets an enum member from a string value stored in options.
        """
        value_str = self._options.get(key)

        if value_str is None or not isinstance(value_str, str) or value_str == '':
            if log_warning:
                self.logger.debug(f"Enum key '{key}' not found or empty in options. Using default: {default_enum_member.name}")
            return default_enum_member

        try:
            # Assuming the stored string matches the enum member's name (e.g., "NO_RESTRICTION" or "no_restriction")
            # Convert to upper case to match enum member names
            return enum_class[value_str.upper()]
        except KeyError:
            if log_warning:
                self.logger.warning(f"Value '{value_str}' for enum key '{key}' is not a valid {enum_class.__name__} member. Using default: {default_enum_member.name}")
            return default_enum_member

    def _convert_shutter_angle_percent_to_degrees(self, angle_percent: float) -> float:
        """
        Convert shutter slat angle from percent to degrees.
        0% = 0 degrees (Slats open)
        100% = 90 degrees (Slats closed)
        Could be higher than 90° depending on shutter type.
        """
        min_slat_angle = self._facade_config.slat_min_angle
        angle_offset = self._facade_config.slat_angle_offset

        if min_slat_angle is None or angle_offset is None:
            self.logger.warning(
                f"_convert_shutter_angle_percent_to_degrees: min_slat_angle ({min_slat_angle}) or angle_offset ({angle_offset}) is None. Using default values (0, 0)")
            min_slat_angle = 0.0
            angle_offset = 0.0

        calculated_degrees = angle_percent * 0.9  # Convert 0-100% into 0-90 degrees

        # Handle angle offset and minimal shutter slat angle
        calculated_degrees += angle_offset
        calculated_degrees = max(min_slat_angle, calculated_degrees)

        self.logger.debug(
            f"Angle of {angle_percent}% equates to {calculated_degrees}° (min_slat_angle={min_slat_angle}, angle_offset={angle_offset})")

        return calculated_degrees

    def _should_output_be_updated(self, config_value: MovementRestricted, new_value: float,
                                  previous_value: float | None) -> float:
        """
        Check if the output should be updated, depending on given MovementRestricted configuration
        New value will be returned if:
        - config_value is 'ONLY_DOWN' and new value is higher than previous value or
        - config_value is 'ONLY_UP' and new value is lower than previous value or
        - config_value is 'NO_RESTRICTION' oder everything else.
        All other cases will return the previous value.
        """
        if previous_value is None:
            # Return None if there's no previous value (like on the initial run)
            # self.logger.debug(
            #     f"_should_output_be_updated: previous_value is None. Returning new value ({new_value})")
            return new_value

        # Check if the value was changed at all
        # by using a small tolerance to prevent redundant movements.
        if abs(new_value - previous_value) < 0.001:
            # self.logger.debug(
            #     f"_should_output_be_updated: new_value ({new_value}) is nearly identical to previous_value ({previous_value}). Returning previous_value")
            return previous_value

        # self.logger.debug(
        #     f"_should_output_be_updated: config_value={config_value.name}, new_value={new_value}, previous_value={previous_value}")

        if config_value == MovementRestricted.ONLY_CLOSE:
            if new_value > previous_value:
                # self.logger.debug(
                #     f"_should_output_be_updated: ONLY_DOWN -> new_value ({new_value}) > previous_value ({previous_value}). Returning new_value")
                return new_value
            else:
                # self.logger.debug(
                #     f"_should_output_be_updated: ONLY_DOWN -> new_value ({new_value}) <= previous_value ({previous_value}). Returning previous_value")
                return previous_value
        elif config_value == MovementRestricted.ONLY_OPEN:
            if new_value < previous_value:
                # self.logger.debug(
                #     f"_should_output_be_updated: ONLY_UP -> new_value ({new_value}) < previous_value ({previous_value}). Returning new_value")
                return new_value
            else:
                # self.logger.debug(
                #     f"_should_output_be_updated: ONLY_UP -> new_value ({new_value}) >= previous_value ({previous_value}). Returning previous_value")
                return previous_value
        elif config_value == MovementRestricted.NO_RESTRICTION:
            # self.logger.debug(
            #     f"_should_output_be_updated: NO_RESTRICTION -> Returning new_value ({new_value})")
            return new_value
        else:
            # self.logger.warning(
            #     f"_should_output_be_updated: Unknown value '{config_value.name}'. Returning new_value ({new_value})")
            return new_value

    async def _start_recalculation_timer(self, delay_seconds: float) -> None:
        """
        Start timer, which triggers a recalculation after 'delay_seconds'.
        Existing timers will be stopped before.
        """
        self._cancel_recalculation_timer()

        if delay_seconds <= 0:
            self.logger.debug(
                f"Timer delay is <= 0 ({delay_seconds}s). Trigger immediate recalculation")
            await self._async_calculate_and_apply_cover_position(None)
            # At immediate recalculation, there is no new timer
            self._next_modification_timestamp = None
            return

        self.logger.debug(f"Starting recalculation timer for {delay_seconds}s")

        # Save start time and duration
        current_utc_time = datetime.now(timezone.utc)
        self._recalculation_timer_start_time = datetime.now(timezone.utc)
        self._recalculation_timer_duration_seconds = delay_seconds

        self._next_modification_timestamp = current_utc_time + timedelta(seconds=delay_seconds)
        self.logger.debug(f"Next modification scheduled for: {self._next_modification_timestamp}")

        # Save callback handle from async_call_later to enable timer canceling
        self._recalculation_timer = async_call_later(
            self.hass,
            delay_seconds,
            self._async_timer_callback
        )

        self._update_extra_state_attributes()

    def _cancel_recalculation_timer(self) -> None:
        """
        Cancel running timer.
        """
        if self._recalculation_timer:
            self.logger.info(f"Canceling recalculation timer")
            self._recalculation_timer()
            self._recalculation_timer = None

        # Reset timer tracking variables
        self._recalculation_timer_start_time = None
        self._recalculation_timer_duration_seconds = None
        self._next_modification_timestamp = None

    async def _async_timer_callback(self, now) -> None:
        """
        Callback which will be called by the Home Assistant scheduler, if timer is running out.
        Parameter 'now' is the object with the current point in time, which will be returned by async_call_later.
        """
        self.logger.debug(f"Recalculation timer finished, triggering recalculation")
        # Reset vars, as timer is finished
        self._recalculation_timer = None
        self._recalculation_timer_start_time = None
        self._recalculation_timer_duration_seconds = None
        await self._async_calculate_and_apply_cover_position(None)

    def get_remaining_timer_seconds(self) -> float | None:
        """
        Return remaining time of running timer or None if no timer is running.
        """
        if self._recalculation_timer and self._recalculation_timer_start_time and self._recalculation_timer_duration_seconds is not None:
            elapsed_time = (datetime.now(timezone.utc) - self._recalculation_timer_start_time).total_seconds()
            remaining_time = self._recalculation_timer_duration_seconds - elapsed_time
            return max(0.0, remaining_time) # Only positive values
        return None

    def _is_timer_finished(self) -> bool:
        """
        Check if a recalculation timer is running.
        """
        return self._recalculation_timer is None

    def _calculate_lock_state(self) -> LockState:
        """
        Calculate the current lock state based on SCDynamicInput booleans.
        lock_integration_with_position has precedence over lock_integration.
        """
        if self._dynamic_config.lock_integration_with_position:
            return LockState.LOCKED_MANUALLY_WITH_FORCED_POSITION
        elif self._dynamic_config.lock_integration:
            return LockState.LOCKED_MANUALLY
        else:
            return LockState.UNLOCKED

# Helper for dynamic log output
def _format_config_object_for_logging(obj, prefix: str = "") -> str:
    """
    Format the public attributes of a given configuration object into one string
    """
    if not obj:
        return f"{prefix}None"

    parts = []
    # `vars(obj)` returns a dictionary of __dict__ attributes of a given object
    for attr, value in vars(obj).items():
        # Skip 'private' attributes, which start with an underscore
        if not attr.startswith('_'):
            parts.append(f"{attr}={value}")

    if not parts:
        return f"{prefix}No attributes to log found."

    return f"{prefix}{', '.join(parts)}"
