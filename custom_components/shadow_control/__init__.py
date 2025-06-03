"""Integration for Shadow Control."""
import datetime
import logging
import math

import voluptuous as vol
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Callable, Awaitable, Mapping

from homeassistant.components.cover import CoverEntityFeature
from homeassistant.components.sensor import SensorEntity # Für die Basisklasse Sensor
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_SUPPORTED_FEATURES,
    STATE_ON, STATE_OFF,
    EVENT_HOMEASSISTANT_STARTED
)
from homeassistant.core import HomeAssistant, callback, Event, State
from homeassistant.helpers import discovery
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity import DeviceInfo # Für Gerätedefinitionen (optional, aber gut)
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_change, async_call_later
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import ( # Für die Benachrichtigung von Sensoren über Updates
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

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
    SC_CONF_COVERS,
    SC_CONF_NAME,
    TARGET_COVER_ENTITY_ID
)

_LOGGER = logging.getLogger(__name__)

SINGLE_COVER_CONFIG_SCHEMA = vol.Schema({
    vol.Required(SC_CONF_NAME): str, # Freundlicher Name für dieses spezifische Cover
    vol.Required(TARGET_COVER_ENTITY_ID): str,

    # === Dynamische Eingänge (Mapped directly to your existing input_number/input_boolean entities) ===
    vol.Required(SCDynamicInput.BRIGHTNESS_ENTITY.value): str,
    vol.Required(SCDynamicInput.BRIGHTNESS_DAWN_ENTITY.value): str,
    vol.Required(SCDynamicInput.SUN_ELEVATION_ENTITY.value): str,
    vol.Required(SCDynamicInput.SUN_AZIMUTH_ENTITY.value): str,
    # HINWEIS: shutter_current_height/angle würde man normalerweise direkt vom Cover bekommen.
    # Hier bleiben sie als input_number für Ihre Testzwecke.
    vol.Required(SCDynamicInput.SHUTTER_CURRENT_HEIGHT_ENTITY.value): str,
    vol.Required(SCDynamicInput.SHUTTER_CURRENT_ANGLE_ENTITY.value): str,
    vol.Required(SCDynamicInput.LOCK_INTEGRATION_ENTITY.value): str,
    vol.Required(SCDynamicInput.LOCK_INTEGRATION_WITH_POSITION_ENTITY.value): str,
    vol.Required(SCDynamicInput.LOCK_HEIGHT_ENTITY.value): str,
    vol.Required(SCDynamicInput.LOCK_ANGLE_ENTITY.value): str,
    vol.Required(SCDynamicInput.MOVEMENT_RESTRICTION_HEIGHT_ENTITY.value): str, # input_select
    vol.Required(SCDynamicInput.MOVEMENT_RESTRICTION_ANGLE_ENTITY.value): str, # input_select

    # === Allgemeine Einstellungen (Mapped to your existing input_number/input_select entities) ===
    vol.Required(SCFacadeConfig.AZIMUTH_STATIC.value): str,
    vol.Required(SCFacadeConfig.OFFSET_SUN_IN_STATIC.value): str,
    vol.Required(SCFacadeConfig.OFFSET_SUN_OUT_STATIC.value): str,
    vol.Required(SCFacadeConfig.ELEVATION_SUN_MIN_STATIC.value): str,
    vol.Required(SCFacadeConfig.ELEVATION_SUN_MAX_STATIC.value): str,
    vol.Required(SCFacadeConfig.SLAT_WIDTH_STATIC.value): str,
    vol.Required(SCFacadeConfig.SLAT_DISTANCE_STATIC.value): str,
    vol.Required(SCFacadeConfig.SLAT_ANGLE_OFFSET_STATIC.value): str,
    vol.Required(SCFacadeConfig.SLAT_MIN_ANGLE_STATIC.value): str,
    vol.Required(SCFacadeConfig.SHUTTER_STEPPING_HEIGHT_STATIC.value): str,
    vol.Required(SCFacadeConfig.SHUTTER_STEPPING_ANGLE_STATIC.value): str,
    vol.Required(SCFacadeConfig.SHUTTER_TYPE_STATIC.value): str, # input_select
    vol.Required(SCFacadeConfig.LIGHT_STRIP_WIDTH_STATIC.value): str,
    vol.Required(SCFacadeConfig.SHUTTER_HEIGHT_STATIC.value): str,
    vol.Required(SCFacadeConfig.NEUTRAL_POS_HEIGHT_STATIC.value): str,
    vol.Required(SCFacadeConfig.NEUTRAL_POS_ANGLE_STATIC.value): str,
    vol.Required(SCFacadeConfig.MODIFICATION_TOLERANCE_HEIGHT_STATIC.value): str,
    vol.Required(SCFacadeConfig.MODIFICATION_TOLERANCE_ANGLE_STATIC.value): str,

    # === Beschattungseinstellungen ===
    vol.Required(SCShadowInput.CONTROL_ENABLED_ENTITY.value): str, # input boolean
    vol.Required(SCShadowInput.BRIGHTNESS_THRESHOLD_ENTITY.value): str,
    vol.Required(SCShadowInput.AFTER_SECONDS_ENTITY.value): str,
    vol.Required(SCShadowInput.SHUTTER_MAX_HEIGHT_ENTITY.value): str,
    vol.Required(SCShadowInput.SHUTTER_MAX_ANGLE_ENTITY.value): str,
    vol.Required(SCShadowInput.SHUTTER_LOOK_THROUGH_SECONDS_ENTITY.value): str,
    vol.Required(SCShadowInput.SHUTTER_LOOK_THROUGH_ANGLE_ENTITY.value): str,
    vol.Required(SCShadowInput.SHUTTER_OPEN_SECONDS_ENTITY.value): str,
    vol.Required(SCShadowInput.HEIGHT_AFTER_SUN_ENTITY.value): str,
    vol.Required(SCShadowInput.ANGLE_AFTER_SUN_ENTITY.value): str,

    # === Dämmerungseinstellungen ===
    vol.Required(SCDawnInput.CONTROL_ENABLED_ENTITY.value): str, # input boolean
    vol.Required(SCDawnInput.BRIGHTNESS_THRESHOLD_ENTITY.value): str,
    vol.Required(SCDawnInput.AFTER_SECONDS_ENTITY.value): str,
    vol.Required(SCDawnInput.SHUTTER_MAX_HEIGHT_ENTITY.value): str,
    vol.Required(SCDawnInput.SHUTTER_MAX_ANGLE_ENTITY.value): str,
    vol.Required(SCDawnInput.SHUTTER_LOOK_THROUGH_SECONDS_ENTITY.value): str,
    vol.Required(SCDawnInput.SHUTTER_LOOK_THROUGH_ANGLE_ENTITY.value): str,
    vol.Required(SCDawnInput.SHUTTER_OPEN_SECONDS_ENTITY.value): str,
    vol.Required(SCDawnInput.HEIGHT_AFTER_DAWN_ENTITY.value): str,
    vol.Required(SCDawnInput.ANGLE_AFTER_DAWN_ENTITY.value): str,
})

# --- Schema für ein einzelnes Cover innerhalb der 'covers' Liste ---

# --- Haupt-Konfigurationsschema für die gesamte Integration ---
CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                # Die 'covers' Liste enthält ein oder mehrere Cover,
                # jedes konfiguriert nach SINGLE_COVER_CONFIG_SCHEMA
                vol.Required("covers"): vol.All(
                    vol.Coerce(list), # Stellen Sie sicher, dass es eine Liste ist
                    [SINGLE_COVER_CONFIG_SCHEMA], # Jedes Element muss dem Schema entsprechen
                    vol.Length(min=1) # Mindestens ein Cover muss konfiguriert sein
                ),
            }
        )
    },
    extra=vol.ALLOW_EXTRA, # Erlaubt weitere unbekannte Top-Level Keys in configuration.yaml
)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Shadow Control integration."""
    _LOGGER.debug(f"[{DOMAIN}] async_setup called.")

    if DOMAIN not in config:
        _LOGGER.warning(f"[{DOMAIN}] No configuration found for {DOMAIN}.")
        return False

    domain_config = config[DOMAIN]
    managers_list = []

    if SC_CONF_COVERS in domain_config and isinstance(domain_config[SC_CONF_COVERS], list):
        for cover_config in domain_config[SC_CONF_COVERS]:
            _LOGGER.debug(f"[{DOMAIN}] Setting up manager for cover: {cover_config['name']}")
            manager = ShadowControlManager(hass, cover_config) # Hier muss ShadowControlManager verfügbar sein
            managers_list.append(manager)
            manager.register_listeners()
    else:
        _LOGGER.warning(f"[{DOMAIN}] No '{SC_CONF_COVERS}' section found or it's not a list in the configuration. No covers will be managed.")
        # Decide if this should return False (fatal) or True (proceed without covers)
        # For now, let's assume it should continue if no covers are defined, but warn.

    # Speichern Sie die Liste der Manager in hass.data. Dies ist entscheidend!
    # sensor.py wird über hass.data auf diese Manager zugreifen.
    hass.data.setdefault(DOMAIN, {})[DOMAIN_DATA_MANAGERS] = managers_list

    # JETZT laden wir die 'sensor'-Plattform Ihrer Integration.
    # Dies wird dazu führen, dass die `async_setup_platform`-Funktion in Ihrer `sensor.py` aufgerufen wird.
    # Wir übergeben die `domain_config[COVERS]` als `discovery_info` an `sensor.py`,
    # falls sensor.py spezifische Konfigurationsdetails für die Sensoren benötigt.
    # Der letzte Parameter (`config`) ist der vollständige Home Assistant Konfigurations-Dict.
    hass.async_create_task(
        discovery.async_load_platform(
            hass,              # Das fehlende 'hass' Objekt am Anfang
            "sensor",          # Die Plattform, die geladen werden soll (sensor.py)
            DOMAIN,            # Die Domain Ihrer Integration (shadow_control)
            {SC_CONF_COVERS: domain_config[SC_CONF_COVERS]}, # Die Konfiguration für sensor.py (discovery_info)
            config             # Der vollständige Home Assistant Konfigurations-Dict (hass_config)
        )
    )

    # --------------------------------------------------------------------------
    # Die _async_hass_started_all_managers Funktion bleibt eine INNERE Funktion
    # --------------------------------------------------------------------------
    async def _async_hass_started_all_managers(event: Event) -> None:
        """Called when Home Assistant has finished starting up."""
        _LOGGER.debug(f"[{DOMAIN}] Home Assistant started event received. Triggering initial run for all managers.")

        if DOMAIN in hass.data and DOMAIN_DATA_MANAGERS in hass.data[DOMAIN]:
            for manager in hass.data[DOMAIN][DOMAIN_DATA_MANAGERS]:
                await manager._async_handle_input_change(None)
        else:
            _LOGGER.warning(f"[{DOMAIN}] No managers found in hass.data during Home Assistant startup event.")

    # Registrieren Sie den Listener für das Home Assistant Started Event
    hass.bus.async_listen_once(
        EVENT_HOMEASSISTANT_STARTED,
        _async_hass_started_all_managers
    )

    _LOGGER.info(f" [{DOMAIN}] Integration 'Shadow Control' successfully set up. Configured {len(managers_list)} covers.")
    return True

class ShadowControlManager:
    """Manages the Shadow Control logic for a single cover."""

    def __init__(
            self,
            hass: HomeAssistant,
            config: Dict[str, Any], # Jetzt bekommt der Manager die komplette Konfig für SEIN Cover
    ) -> None:
        self.hass = hass
        self._config = config
        self._name = config[SC_CONF_NAME]
        self._target_cover_entity = config[TARGET_COVER_ENTITY_ID]

        # === Dynamische Eingänge (Test-Helfer) ===
        self._brightness_entity = config.get(SCDynamicInput.BRIGHTNESS_ENTITY.value)
        self._brightness_dawn_entity = config.get(SCDynamicInput.BRIGHTNESS_DAWN_ENTITY.value)
        self._sun_elevation_entity = config.get(SCDynamicInput.SUN_ELEVATION_ENTITY.value)
        self._sun_azimuth_entity = config.get(SCDynamicInput.SUN_AZIMUTH_ENTITY.value)
        self._shutter_current_height_entity = config.get(SCDynamicInput.SHUTTER_CURRENT_HEIGHT_ENTITY.value)
        self._shutter_current_angle_entity = config.get(SCDynamicInput.SHUTTER_CURRENT_ANGLE_ENTITY.value)
        self._lock_integration_entity = config.get(SCDynamicInput.LOCK_INTEGRATION_ENTITY.value)
        self._lock_integration_with_position_entity = config.get(SCDynamicInput.LOCK_INTEGRATION_WITH_POSITION_ENTITY.value)
        self._lock_height_entity = config.get(SCDynamicInput.LOCK_HEIGHT_ENTITY.value)
        self._lock_angle_entity = config.get(SCDynamicInput.LOCK_ANGLE_ENTITY.value)
        self._movement_restriction_height_entity = config.get(SCDynamicInput.MOVEMENT_RESTRICTION_HEIGHT_ENTITY.value)
        self._movement_restriction_angle_entity = config.get(SCDynamicInput.MOVEMENT_RESTRICTION_ANGLE_ENTITY.value)

        # === Allgemeine Einstellungen (Test-Helfer) ===
        self._facade_azimuth_entity = config.get(SCFacadeConfig.AZIMUTH_STATIC.value)
        self._facade_offset_sun_in_entity = config.get(SCFacadeConfig.OFFSET_SUN_IN_STATIC.value)
        self._facade_offset_sun_out_entity = config.get(SCFacadeConfig.OFFSET_SUN_OUT_STATIC.value)
        self._facade_elevation_sun_min_entity = config.get(SCFacadeConfig.ELEVATION_SUN_MIN_STATIC.value)
        self._facade_elevation_sun_max_entity = config.get(SCFacadeConfig.ELEVATION_SUN_MAX_STATIC.value)
        self._facade_slat_width_entity = config.get(SCFacadeConfig.SLAT_WIDTH_STATIC.value)
        self._facade_slat_distance_entity = config.get(SCFacadeConfig.SLAT_DISTANCE_STATIC.value)
        self._facade_slat_angle_offset_entity = config.get(SCFacadeConfig.SLAT_ANGLE_OFFSET_STATIC.value)
        self._facade_slat_min_angle_entity = config.get(SCFacadeConfig.SLAT_MIN_ANGLE_STATIC.value)
        self._facade_shutter_stepping_height_entity = config.get(SCFacadeConfig.SHUTTER_STEPPING_HEIGHT_STATIC.value)
        self._facade_shutter_stepping_angle_entity = config.get(SCFacadeConfig.SHUTTER_STEPPING_ANGLE_STATIC.value)
        self._facade_shutter_type_entity = config.get(SCFacadeConfig.SHUTTER_TYPE_STATIC.value)
        self._facade_light_strip_width_entity = config.get(SCFacadeConfig.LIGHT_STRIP_WIDTH_STATIC.value)
        self._facade_shutter_height_entity = config.get(SCFacadeConfig.SHUTTER_HEIGHT_STATIC.value)
        self._facade_neutral_pos_height_entity = config.get(SCFacadeConfig.NEUTRAL_POS_HEIGHT_STATIC.value)
        self._facade_neutral_pos_angle_entity = config.get(SCFacadeConfig.NEUTRAL_POS_ANGLE_STATIC.value)
        self._modification_tolerance_height_entity = config.get(SCFacadeConfig.MODIFICATION_TOLERANCE_HEIGHT_STATIC.value)
        self._modification_tolerance_angle_entity = config.get(SCFacadeConfig.MODIFICATION_TOLERANCE_ANGLE_STATIC.value)

        # === Beschattungseinstellungen (Test-Helfer) ===
        self._shadow_control_enabled_entity = config.get(SCShadowInput.CONTROL_ENABLED_ENTITY.value)
        self._shadow_brightness_threshold_entity = config.get(SCShadowInput.BRIGHTNESS_THRESHOLD_ENTITY.value)
        self._shadow_after_seconds_entity = config.get(SCShadowInput.AFTER_SECONDS_ENTITY.value)
        self._shadow_shutter_max_height_entity = config.get(SCShadowInput.SHUTTER_MAX_HEIGHT_ENTITY.value)
        self._shadow_shutter_max_angle_entity = config.get(SCShadowInput.SHUTTER_MAX_ANGLE_ENTITY.value)
        self._shadow_shutter_look_through_seconds_entity = config.get(SCShadowInput.SHUTTER_LOOK_THROUGH_SECONDS_ENTITY.value)
        self._shadow_shutter_open_seconds_entity = config.get(SCShadowInput.SHUTTER_OPEN_SECONDS_ENTITY.value)
        self._shadow_shutter_look_through_angle_entity = config.get(SCShadowInput.SHUTTER_LOOK_THROUGH_ANGLE_ENTITY.value)
        self._shadow_height_after_sun_entity = config.get(SCShadowInput.HEIGHT_AFTER_SUN_ENTITY.value)
        self._shadow_angle_after_sun_entity = config.get(SCShadowInput.ANGLE_AFTER_SUN_ENTITY.value)

        # === Dämmerungseinstellungen (Test-Helfer) ===
        self._dawn_control_enabled_entity = config.get(SCDawnInput.CONTROL_ENABLED_ENTITY.value)
        self._dawn_brightness_threshold_entity = config.get(SCDawnInput.BRIGHTNESS_THRESHOLD_ENTITY.value)
        self._dawn_after_seconds_entity = config.get(SCDawnInput.AFTER_SECONDS_ENTITY.value)
        self._dawn_shutter_max_height_entity = config.get(SCDawnInput.SHUTTER_MAX_HEIGHT_ENTITY.value)
        self._dawn_shutter_max_angle_entity = config.get(SCDawnInput.SHUTTER_MAX_ANGLE_ENTITY.value)
        self._dawn_shutter_look_through_seconds_entity = config.get(SCDawnInput.SHUTTER_LOOK_THROUGH_SECONDS_ENTITY.value)
        self._dawn_shutter_open_seconds_entity = config.get(SCDawnInput.SHUTTER_OPEN_SECONDS_ENTITY.value)
        self._dawn_shutter_look_through_angle_entity = config.get(SCDawnInput.SHUTTER_LOOK_THROUGH_ANGLE_ENTITY.value)
        self._dawn_height_after_dawn_entity = config.get(SCDawnInput.HEIGHT_AFTER_DAWN_ENTITY.value)
        self._dawn_angle_after_dawn_entity = config.get(SCDawnInput.ANGLE_AFTER_DAWN_ENTITY.value)

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

        # Interne Variablen
        self._enforce_position_update: bool = False

        # Interne persistente Variablen
        # Werden beim Start aus den persistenten Attributen gelesen.
        self._current_shutter_state: ShutterState = ShutterState.NEUTRAL # Standardwert setzen
        self._current_lock_state: LockState = LockState.UNLOCKED # Standardwert setzen
        self._calculated_shutter_height: float = 0.0
        self._calculated_shutter_angle: float = 0.0
        self._calculated_shutter_angle_degrees: float | None = None
        self._effective_elevation: float | None = None
        self._previous_shutter_height: float | None = None
        self._previous_shutter_angle: float | None = None
        self._is_initial_run: bool = True # Flag für den initialen Lauf
        self._is_producing_shadow: bool = False # Neuer interner Zustand für ProduceShadow
        self._next_modification_timestamp: datetime | None = None

        self._listeners: list[Callable[[], None]] = [] # Liste zum Speichern der Listener
        self._recalculation_timer: Callable[[], None] | None = None # Zum Speichern des Callbacks für den geplanten Timer

        _LOGGER.debug(f"{self._name}: Manager initialized for target: {self._target_cover_entity}.")

    def register_listeners(self) -> None:
        """Register listeners for relevant state changes for this specific cover."""
        _LOGGER.debug(f"{self._name}: Registering listeners")

        # Liste aller Entitäten, auf deren Änderungen dieser Manager reagieren soll
        # Dies sind die Entitäten aus Ihrer config, deren Zustand die Logik beeinflusst
        relevant_entities = [
            self._brightness_entity,
            self._brightness_dawn_entity,
            self._sun_elevation_entity,
            self._sun_azimuth_entity,
            self._lock_integration_entity,
            self._lock_integration_with_position_entity,
            self._shadow_control_enabled_entity,
            self._dawn_control_enabled_entity
        ]

        # Filtern Sie None-Werte heraus (falls ein optionaler Parameter nicht gesetzt ist,
        # oder wenn Sie versehentlich einen Platzhalter eingefügt haben, der None ist)
        unique_relevant_entities = list(set(eid for eid in relevant_entities if eid))

        self._listeners.append(
            async_track_state_change_event(
                self.hass,
                unique_relevant_entities,
                self._async_handle_input_change, # EINE zentrale Methode für alle Änderungen
            )
        )

        # Optional: Wenn Sie eine zeitbasierte Aktualisierung für jedes Cover möchten
        # self._listeners.append(
        #     async_track_time_change(self.hass, self._async_handle_input_change,
        #                             minute=None, second=0)
        # )

        _LOGGER.debug(f"{self._name}: All relevant state listeners registered")


    async def async_hass_started(self, event: Event) -> None:
        """Handle Home Assistant start event for this specific manager."""
        _LOGGER.info(f" {self._name}: Home Assistant has started. Initializing Shadow Control")
        # Hier können Sie den initialen Zustand abrufen und die erste Berechnung ausführen

        # Initialberechnung beim Start
        await self._async_calculate_and_apply_cover_position(None)

    def _update_input_values(self) -> None:
        """
        Aktualisiert alle relevanten Eingangs- und Konfigurationswerte
        aus Home Assistant und speichert sie in Instanzvariablen.
        """
        _LOGGER.debug(f"{self._name}: Updating all input values")

        # === Dynamische Eingänge (Sensor-Werte) ===
        self._brightness = self._get_entity_numeric_state(self._brightness_entity, float)
        self._brightness_dawn = self._get_entity_numeric_state(self._brightness_dawn_entity, float)
        self._sun_elevation = self._get_entity_numeric_state(self._sun_elevation_entity, float)
        self._sun_azimuth = self._get_entity_numeric_state(self._sun_azimuth_entity, float)
        self._shutter_current_height = self._get_entity_numeric_state(self._shutter_current_height_entity, float)
        self._shutter_current_angle = self._get_entity_numeric_state(self._shutter_current_angle_entity, float)
        self._lock_integration = self._get_entity_boolean_state(self._lock_integration_entity)
        self._lock_integration_with_position = self._get_entity_boolean_state(self._lock_integration_with_position_entity)
        self._lock_height = self._get_entity_numeric_state(self._lock_height_entity, float)
        self._lock_angle = self._get_entity_numeric_state(self._lock_angle_entity, float)
        self._modification_tolerance_height = self._get_entity_numeric_state(self._modification_tolerance_height_entity, float)
        self._modification_tolerance_angle = self._get_entity_numeric_state(self._modification_tolerance_angle_entity, float)

        # === Allgemeine Einstellungen ===
        self._azimuth_facade = self._get_entity_numeric_state(self._facade_azimuth_entity, float)
        self._offset_sun_in = self._get_entity_numeric_state(self._facade_offset_sun_in_entity, float)
        self._offset_sun_out = self._get_entity_numeric_state(self._facade_offset_sun_out_entity, float)
        self._elevation_sun_min = self._get_entity_numeric_state(self._facade_elevation_sun_min_entity, float)
        self._elevation_sun_max = self._get_entity_numeric_state(self._facade_elevation_sun_max_entity, float)
        self._slat_width = self._get_entity_numeric_state(self._facade_slat_width_entity, float)
        self._slat_distance = self._get_entity_numeric_state(self._facade_slat_distance_entity, float)
        self._angle_offset = self._get_entity_numeric_state(self._facade_slat_angle_offset_entity, float)
        self._min_slat_angle = self._get_entity_numeric_state(self._facade_slat_min_angle_entity, float)
        self._stepping_height = self._get_entity_numeric_state(self._facade_shutter_stepping_height_entity, float)
        self._stepping_angle = self._get_entity_numeric_state(self._facade_shutter_stepping_angle_entity, float)
        self._shutter_type = self._get_entity_string_state(self._facade_shutter_type_entity)
        self._light_bar_width = self._get_entity_numeric_state(self._facade_light_strip_width_entity, float)
        self._shutter_height = self._get_entity_numeric_state(self._facade_shutter_height_entity, float)
        self._neutral_pos_height = self._get_entity_numeric_state(self._facade_neutral_pos_height_entity, float)
        self._neutral_pos_angle = self._get_entity_numeric_state(self._facade_neutral_pos_angle_entity, float)

        # -------------------------------------------
        # Movement restriction to enumeration mapping
        #self._movement_restriction_height = self._get_entity_string_state(self._movement_restriction_height_entity)
        height_restriction_entity = self._config.get(SCDynamicInput.MOVEMENT_RESTRICTION_HEIGHT_ENTITY.value)
        if height_restriction_entity:
            state_obj = self.hass.states.get(height_restriction_entity)
            if state_obj and state_obj.state:
                # Suchen Sie den Enum-Member, dessen Wert (value) dem input_select String entspricht
                for restriction_type in MovementRestricted:
                    if restriction_type.value == state_obj.state:
                        self._movement_restriction_height = restriction_type
                        _LOGGER.debug(f"{self._name}: Movement restriction for height set ({self._movement_restriction_height.name}, value: {state_obj.state})")
                        break
                else: # Wenn die Schleife ohne break beendet wird (Wert nicht gefunden)
                    _LOGGER.warning(f"{self._name}: Unknown option for {height_restriction_entity}: '{state_obj.state}'. Using NO_RESTRICTION.")
                    self._movement_restriction_height = MovementRestricted.NO_RESTRICTION
            else:
                _LOGGER.warning(f"{self._name}: Value of {height_restriction_entity} not available or empty. Using NO_RESTRICTION.")
                self._movement_restriction_height = MovementRestricted.NO_RESTRICTION
        else:
            _LOGGER.warning(f"{self._name}: Configuration of '{SCDynamicInput.MOVEMENT_RESTRICTION_HEIGHT_ENTITY.value}' missing. Using NO_RESTRICTION.")
            self._movement_restriction_height = MovementRestricted.NO_RESTRICTION
        #self._movement_restriction_angle = self._get_entity_string_state(self._movement_restriction_angle_entity)
        angle_restriction_entity = self._config.get(SCDynamicInput.MOVEMENT_RESTRICTION_ANGLE_ENTITY.value)
        if angle_restriction_entity:
            state_obj = self.hass.states.get(angle_restriction_entity)
            if state_obj and state_obj.state:
                for restriction_type in MovementRestricted:
                    if restriction_type.value == state_obj.state:
                        self._movement_restriction_angle = restriction_type
                        _LOGGER.debug(f"{self._name}: Movement restriction for angle set {self._movement_restriction_angle.name}, value: {state_obj.state})")
                        break
                else:
                    _LOGGER.warning(f"{self._name}: Unknown option for {angle_restriction_entity}: '{state_obj.state}'. Using NO_RESTRICTION.")
                    self._movement_restriction_angle = MovementRestricted.NO_RESTRICTION
            else:
                _LOGGER.warning(f"{self._name}: Value of {angle_restriction_entity} not available or empty. Using NO_RESTRICTION.")
                self._movement_restriction_angle = MovementRestricted.NO_RESTRICTION
        else:
            _LOGGER.warning(f"{self._name}: Configuration of '{SCDynamicInput.MOVEMENT_RESTRICTION_ANGLE_ENTITY.value}' missing. Using NO_RESTRICTION.")
            self._movement_restriction_angle = MovementRestricted.NO_RESTRICTION

        # === Beschattungseinstellungen ===
        self._shadow_control_enabled = self._get_entity_boolean_state(self._shadow_control_enabled_entity)
        self._shadow_brightness_level = self._get_entity_numeric_state(self._shadow_brightness_threshold_entity, float)
        self._shadow_after_seconds = self._get_entity_numeric_state(self._shadow_after_seconds_entity, float)
        self._shadow_max_height = self._get_entity_numeric_state(self._shadow_shutter_max_height_entity, float)
        self._shadow_max_angle = self._get_entity_numeric_state(self._shadow_shutter_max_angle_entity, float)
        self._shadow_look_through_seconds = self._get_entity_numeric_state(self._shadow_shutter_look_through_seconds_entity, float)
        self._shadow_open_seconds = self._get_entity_numeric_state(self._shadow_shutter_open_seconds_entity, float)
        self._shadow_look_through_angle = self._get_entity_numeric_state(self._shadow_shutter_look_through_angle_entity, float)
        self._after_shadow_height = self._get_entity_numeric_state(self._shadow_height_after_sun_entity, float)
        self._after_shadow_angle = self._get_entity_numeric_state(self._shadow_angle_after_sun_entity, float)

        # === Dämmerungseinstellungen ===
        self._dawn_control_enabled = self._get_entity_boolean_state(self._dawn_control_enabled_entity)
        self._dawn_brightness_level = self._get_entity_numeric_state(self._dawn_brightness_threshold_entity, float)
        self._dawn_after_seconds = self._get_entity_numeric_state(self._dawn_after_seconds_entity, float)
        self._dawn_max_height = self._get_entity_numeric_state(self._dawn_shutter_max_height_entity, float)
        self._dawn_max_angle = self._get_entity_numeric_state(self._dawn_shutter_max_angle_entity, float)
        self._dawn_look_through_seconds = self._get_entity_numeric_state(self._dawn_shutter_look_through_seconds_entity, float)
        self._dawn_open_seconds = self._get_entity_numeric_state(self._dawn_shutter_open_seconds_entity, float)
        self._dawn_look_through_angle = self._get_entity_numeric_state(self._dawn_shutter_look_through_angle_entity, float)
        self._after_dawn_height = self._get_entity_numeric_state(self._dawn_height_after_dawn_entity, float)
        self._after_dawn_angle = self._get_entity_numeric_state(self._dawn_angle_after_dawn_entity, float)

        _LOGGER.debug(
            f"{self._name}: Updated values (part of): "
            f"Brightness={self._brightness}, "
            f"Elevation={self._sun_elevation}, "
            f"ShadowEnabled={self._shadow_control_enabled}"
        )

        # === Priorisierung des internen LockState ===
        # Wenn LOCK_INTEGRATION_WITH_POSITION_ENTITY (höchste Priorität) "on" ist
        if self._lock_integration_with_position:
            self._current_lock_state = LockState.LOCKED_MANUALLY_WITH_FORCED_POSITION
            _LOGGER.debug(f"{self._name}: LockState set to LOCKSTATE__LOCKED_MANUALLY_WITH_FORCED_POSITION due to '{self._lock_integration_with_position_entity}' being ON.")
        # Wenn LOCK_INTEGRATION_ENTITY "on" ist (und die höhere Priorität nicht greift)
        elif self._lock_integration:
            self._current_lock_state = LockState.LOCKED_MANUALLY
            _LOGGER.debug(f"{self._name}: LockState set to LOCKSTATE__LOCKED_MANUALLY due to '{self._lock_integration_entity}' being ON.")
        # Ansonsten bleibt es UNLOCKED (oder ein anderer Standardwert, den Sie festgelegt haben)

        # Optional: Weitere LockStates wie LOCKSTATE__LOCKED_BY_EXTERNAL_MODIFICATION
        # elif self._is_external_modification_detected: # Pseudo-Variable
        #    self._current_lock_state = LockState.LOCKSTATE__LOCKED_BY_EXTERNAL_MODIFICATION
        #    _LOGGER.debug(f"{self._name}: LockState set to LOCKSTATE__LOCKED_BY_EXTERNAL_MODIFICATION.")

        else:
            # Standardmässig ist der Zustand ungesperrt
            self._current_lock_state = LockState.UNLOCKED
            _LOGGER.debug(f"{self._name}: LockState set to LOCKSTATE__UNLOCKED due to '{self._lock_integration_entity}' and '{self._lock_integration_with_position_entity}' being OFF.")


    @callback
    async def _async_handle_input_change(self, event: Event | None) -> None:
        """Handle changes to any relevant input entity for this specific cover."""
        _LOGGER.debug(f"{self._name}: Input change detected. Event: {event}")

        await self._async_calculate_and_apply_cover_position(event)

    async def _async_calculate_and_apply_cover_position(self, event: Event | None) -> None:
        """
        Calculate and apply the new cover and tilt position for this specific cover.
        This is where your main Shadow Control logic resides.
        """
        _LOGGER.debug(f"{self._name}: =====================================================================")
        _LOGGER.debug(f"{self._name}: Calculating and applying cover positions")

        self._update_input_values()

        shadow_handling_was_disabled = False
        dawn_handling_was_disabled = False
        
        if event: # Prüfen, ob es sich um ein tatsächliches Event handelt (nicht None, wie beim Initial-Run)
            event_type = event.event_type
            event_data = event.data

            if event_type == "state_changed":
                entity = event_data.get("entity")
                old_state: State | None = event_data.get("old_state")
                new_state: State | None = event_data.get("new_state")

                _LOGGER.debug(f"{self._name}: State change for entity: {entity}")
                _LOGGER.debug(f"{self._name}:   Old state: {old_state.state if old_state else 'None'}")
                _LOGGER.debug(f"{self._name}:   New state: {new_state.state if new_state else 'None'}")

                # Hier können Sie spezifische Logik hinzufügen, basierend auf der entity
                if entity == self._shadow_control_enabled_entity:
                    _LOGGER.debug(f"{self._name}: Shadow control enable changed to {new_state.state}")
                    shadow_handling_was_disabled = new_state.state == "off"
                elif entity == self._dawn_control_enabled_entity:
                    _LOGGER.debug(f"{self._name}: Dawn control enable changed to {new_state.state}")
                    dawn_handling_was_disabled = new_state.state == "off"
                elif entity == self._lock_integration_entity:
                    if new_state.state == "off" and not self._lock_integration_with_position:
                        _LOGGER.debug(f"{self._name}: Simple lock was disabled and lock with position is already disabled, enforcing position update")
                        self._enforce_position_update = True
                elif entity == self._lock_integration_with_position_entity:
                    if new_state.state == "off" and not self._lock_integration:
                        _LOGGER.debug(f"{self._name}: Lock with position was disabled and simple lock already disabled, enforcing position update")
                        self._enforce_position_update = True
            elif event_type == "time_changed":
                _LOGGER.debug(f"{self._name}: Time changed event received")
            else:
                _LOGGER.debug(f"{self._name}: Unhandled event type: {event_type}")
        else:
            _LOGGER.debug(f"{self._name}: No specific event data (likely initial run or manual trigger)")

        self._check_if_position_changed_externally(self._shutter_current_height, self._shutter_current_angle)
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
        _LOGGER.debug(f"{self._name}: Checking if facade is in sun")

        # Die Werte wurden bereits in _update_input_values als float abgerufen.
        sun_current_azimuth = self._sun_azimuth
        sun_current_elevation = self._sun_elevation
        facade_azimuth = self._azimuth_facade
        facade_offset_start = self._offset_sun_in
        facade_offset_end = self._offset_sun_out
        min_elevation = self._elevation_sun_min
        max_elevation = self._elevation_sun_max

        if (
                sun_current_azimuth is None
                or sun_current_elevation is None
                or facade_azimuth is None
                or facade_offset_start is None
                or facade_offset_end is None
                or min_elevation is None
                or max_elevation is None
        ):
            _LOGGER.debug(f"{self._name}: Not all required values available to compute sun state of facade")
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

        message = f"{self._name}: Finished facade check:\n -> real azimuth {sun_current_azimuth}° and facade at {facade_azimuth}° -> "
        _sun_between_offsets = False
        if 0 <= azimuth_calc <= sun_exit_angle_calc:
            message += f"IN SUN (from {sun_entry_angle}° to {sun_exit_angle}°)"
            _sun_between_offsets = True
            self._effective_elevation = await self._calculate_effective_elevation()
        else:
            message += f"NOT IN SUN (shadow side, at sun from {sun_entry_angle}° to {sun_exit_angle}°)"
            self._effective_elevation = None

        message += f"\n -> effective elevation {self._effective_elevation}° for given elevation of {sun_current_elevation}°"
        _is_elevation_in_range = False
        if min_elevation < self._effective_elevation < max_elevation:
            message += f" -> in min-max-range ({min_elevation}°-{max_elevation}°)"
            self._sun_between_min_max = True
            _is_elevation_in_range = True
        else:
            message += f" -> NOT in min-max-range ({min_elevation}°-{max_elevation}°)"
            self._sun_between_min_max = False
        _LOGGER.debug(f"{message}")

        return _sun_between_offsets and _is_elevation_in_range

    def _get_current_brightness(self) -> float:
        return self._brightness

    def _get_current_dawn_brightness(self) -> float:
        if self._brightness_dawn is not None and self._brightness_dawn >= 0:
            return self._brightness_dawn
        return self._brightness

    async def _calculate_effective_elevation(self) -> float | None:
        """Berechnet die effektive Elevation der Sonne relativ zur Fassade."""

        # Die Werte wurden bereits in _update_input_values als float abgerufen.
        sun_current_azimuth = self._sun_azimuth
        sun_current_elevation = self._sun_elevation
        facade_azimuth = self._azimuth_facade

        if sun_current_azimuth is None or sun_current_elevation is None or facade_azimuth is None:
            _LOGGER.debug(f"{self._name}: Unable to compute effective elevation, not all required values available")
            return None

        _LOGGER.debug(f"{self._name}: Current sun position (a:e): {sun_current_azimuth}°:{sun_current_elevation}°, facade: {facade_azimuth}°")

        try:
            virtual_depth = math.cos(math.radians(abs(sun_current_azimuth - facade_azimuth)))
            virtual_height = math.tan(math.radians(sun_current_elevation))

            # Vermeide Division durch Null, falls virtual_depth sehr klein ist
            if abs(virtual_depth) < 1e-9:
                effective_elevation = 90.0 if virtual_height > 0 else -90.0
            else:
                effective_elevation = math.degrees(math.atan(virtual_height / virtual_depth))

            _LOGGER.debug(f"{self._name}: Virtual deep and height of the sun against the facade: {virtual_depth}, {virtual_height}, effektive Elevation: {effective_elevation}")
            return effective_elevation
        except ValueError:
            _LOGGER.debug(f"{self._name}: Unable to compute effective elevation: Invalid input values")
            return None
        except ZeroDivisionError:
            _LOGGER.debug(f"{self._name}: Unable to compute effective elevation: Division by zero")
            return None

    # =======================================================================
    # Persistente Werte
    def _update_extra_state_attributes(self) -> None:
        """Helper to update the extra_state_attributes dictionary."""
        self._attr_extra_state_attributes = {
            "current_shutter_state": self._current_shutter_state,
            "calculated_shutter_height": self._calculated_shutter_height,
            "calculated_shutter_angle": self._calculated_shutter_angle,
            "calculated_shutter_angle_degrees": self._calculated_shutter_angle_degrees,
            "current_lock_state": self._current_lock_state,
            "next_modification_timestamp": self._next_modification_timestamp.isoformat() if self._next_modification_timestamp else None,
        }

    async def _shadow_handling_was_disabled(self) -> None:
        match self._current_shutter_state:
            case ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING | \
                 ShutterState.SHADOW_FULL_CLOSED | \
                 ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING | \
                 ShutterState.SHADOW_HORIZONTAL_NEUTRAL | \
                 ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING | \
                 ShutterState.SHADOW_NEUTRAL:
                _LOGGER.debug(f"{self._name}: Shadow handling was disabled, position shutter at neutral height")
                self._cancel_recalculation_timer()
                self._current_shutter_state = ShutterState.NEUTRAL
                self._update_extra_state_attributes()  # Attribute nach Zustandswechsel aktualisieren
            case ShutterState.NEUTRAL:
                _LOGGER.debug(f"{self._name}: Shadow handling was disabled, but shutter already at neutral height. Nothing to do")
            case _:
                _LOGGER.debug(f"{self._name}: Shadow handling was disabled but currently within a dawn state. Nothing to do")

    async def _dawn_handling_was_disabled(self) -> None:
        match self._current_shutter_state:
            case ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING | \
                 ShutterState.DAWN_FULL_CLOSED | \
                 ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING | \
                 ShutterState.DAWN_HORIZONTAL_NEUTRAL | \
                 ShutterState.DAWN_NEUTRAL_TIMER_RUNNING | \
                 ShutterState.DAWN_NEUTRAL:
                _LOGGER.debug(f"{self._name}: Dawn handling was disabled, position shutter at neutral height")
                self._cancel_recalculation_timer()
                self._current_shutter_state = ShutterState.NEUTRAL
                self._update_extra_state_attributes()  # Attribute nach Zustandswechsel aktualisieren
            case ShutterState.NEUTRAL:
                _LOGGER.debug(f"{self._name}: Dawn handling was disabled, but shutter already at neutral height. Nothing to do")
            case _:
                _LOGGER.debug(f"{self._name}: Dawn handling was disabled but currently within a shadow state. Nothing to do")

    async def _process_shutter_state(self) -> None:
        """
        Verarbeitet den aktuellen Behangzustand und ruft die entsprechende Handler-Funktion auf.
        Die Handler-Funktionen müssen den neuen ShutterState zurückgeben.
        """
        _LOGGER.debug(f"{self._name}: Current shutter state (before processing): {self._current_shutter_state.name} ({self._current_shutter_state.value})")

        handler_func = self._state_handlers.get(self._current_shutter_state)
        new_shutter_state: ShutterState

        if handler_func:
            new_shutter_state = await handler_func()
            if new_shutter_state is not None and new_shutter_state != self._current_shutter_state:
                _LOGGER.debug(
                    f"{self._name}: State change from {self._current_shutter_state.name} to {new_shutter_state.name}")
                self._current_shutter_state = new_shutter_state
                self._update_extra_state_attributes()  # Attribute nach Zustandswechsel aktualisieren
                _LOGGER.debug(f"{self._name}: Checking if there might be another change required")
                await self._process_shutter_state()
        else:
            _LOGGER.debug(
                f"{self._name}: No specific handler for current state or locked. Current lock state: {self._current_lock_state.name}")
            self._cancel_recalculation_timer()
            self._update_extra_state_attributes()  # Auch hier Attribute aktualisieren, falls sich durch Sperrung etwas ändert

        _LOGGER.debug(f"{self._name}: New shutter state after processing: {self._current_shutter_state.name} ({self._current_shutter_state.value})")

    def _check_if_position_changed_externally(self, current_height, current_angle):
        #_LOGGER.debug(f"{self._name}: Checking if position changed externally. Current height: {current_height}, Current angle: {current_angle}")
        _LOGGER.debug(f"{self._name}: Check for external shutter modification -> TBD")
        pass

    async def _position_shutter(
            self,
            shutter_height_percent: float,
            shutter_angle_percent: float,
            shadow_position: bool,
            stop_timer: bool
    ) -> None:
        """Helper to send commands to the target cover."""
        _LOGGER.debug(
            f"{self._name}: Starting _position_shutter with target height {shutter_height_percent:.2f}% "
            f"and angle {shutter_angle_percent:.2f}% (is_initial_run: {self._is_initial_run}, "
            f"lock_state: {self._current_lock_state.name})"
        )

        # Always handle timer cancellation if required, regardless of initial run or lock state
        if stop_timer:
            _LOGGER.debug(f"{self._name}: Canceling timer.")
            self._cancel_recalculation_timer()

        # --- Phase 1: Update internal states that should always reflect the calculation ---
        # These are the *calculated target* values.
        self._calculated_shutter_height = shutter_height_percent
        self._calculated_shutter_angle = shutter_angle_percent
        self._calculated_shutter_angle_degrees = self._convert_shutter_angle_percent_to_degrees(
            shutter_angle_percent)

        # --- Phase 2: Handle initial run special logic ---
        if self._is_initial_run:
            _LOGGER.info(
                f"{self._name}: Initial run of integration. Setting internal states. No physical output update.")
            # Only set internal previous values for the *next* run's send-by-change logic.
            # These are now set to the *initial target* values.
            self._previous_shutter_height = shutter_height_percent
            self._previous_shutter_angle = shutter_angle_percent
            self._is_initial_run = False  # Initial run completed

            self._update_extra_state_attributes()
            return  # Exit here, as no physical output should happen on initial run

        # --- Phase 3: Check for Lock State BEFORE applying stepping/should_output_be_updated and sending commands ---
        # This ensures that calculations still happen, but outputs are skipped.
        is_locked = (self._current_lock_state != LockState.UNLOCKED)
        if is_locked:
            _LOGGER.info(
                f"{self._name}: Integration is locked ({self._current_lock_state.name}). "
                f"Calculations are running, but physical outputs are skipped."
            )
            # Update internal _previous values here to reflect that if it *were* unlocked,
            # it would have moved to these calculated positions.
            # This prepares for a smooth transition when unlocked.
            self._previous_shutter_height = shutter_height_percent
            self._previous_shutter_angle = shutter_angle_percent
            self._update_extra_state_attributes()
            return  # Exit here, no physical output while locked

        # --- Phase 4: Apply stepping and output restriction logic (only if not initial run AND not locked) ---
        entity = self._target_cover_entity
        current_cover_state: State | None = self.hass.states.get(entity)

        if not current_cover_state:
            _LOGGER.warning(f"{self._name}: Target cover entity '{entity}' not found. Cannot send commands.")
            return

        supported_features = current_cover_state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)

        # Hier die korrekten Dienstnamen verwenden
        has_pos_service = self.hass.services.has_service("cover", "set_cover_position")
        has_tilt_service = self.hass.services.has_service("cover", "set_cover_tilt_position")

        _LOGGER.debug(f"{self._name}: Services availability ({entity}): set_cover_position={has_pos_service}, set_cover_tilt_position={has_tilt_service}")

        async_dispatcher_send(
            self.hass,
            f"{DOMAIN}_update_{self._name.lower().replace(' ', '_')}"
        )

        # Height Handling
        height_to_set_percent = self._handle_shutter_height_stepping(shutter_height_percent)
        height_to_set_percent = self._should_output_be_updated(
            config_value=self._movement_restriction_height,
            new_value=height_to_set_percent,
            previous_value=self._previous_shutter_height
        )

        # Angle Handling - Crucial for "send angle if height changed" logic
        # We need the value of _previous_shutter_height *before* it's updated for height.
        # So, compare the *calculated* `shutter_height_percent` with what was previously *stored*.
        height_calculated_different_from_previous = (
                -0.001 < abs(shutter_height_percent - self._previous_shutter_height) > 0.001) if self._previous_shutter_height is not None else True

        angle_to_set_percent = self._should_output_be_updated(
            config_value=self._movement_restriction_angle,
            new_value=shutter_angle_percent,
            previous_value=self._previous_shutter_angle
        )

        # --- Phase 5: Send commands if values actually changed (only if not initial run AND not locked) ---
        send_height_command = -0.001 < abs(height_to_set_percent - self._previous_shutter_height) > 0.001 if self._previous_shutter_height is not None else True

        # Send angle command if angle changed OR if height changed significantly
        send_angle_command = (-0.001 < abs(angle_to_set_percent - self._previous_shutter_angle) > 0.001 if self._previous_shutter_angle is not None else True) or height_calculated_different_from_previous

        if self._enforce_position_update:
            _LOGGER.debug(f"{self._name}: Enforcing position update")
            send_height_command = True
            send_angle_command = True

        # Height positioning
        if send_height_command or self._enforce_position_update:
            if (supported_features & CoverEntityFeature.SET_POSITION) and has_pos_service:
                _LOGGER.info(f" {self._name}: Setting position to {shutter_height_percent:.1f}% (current: {self._previous_shutter_height}).")
                try:
                    await self.hass.services.async_call(
                        "cover",
                        "set_cover_position",
                        {"entity": entity, "position": 100 - shutter_height_percent},
                        blocking=False
                    )
                except Exception as e:
                    _LOGGER.error(f"{self._name}: Failed to set position: {e}")
                self._previous_shutter_height = shutter_height_percent
            else:
                _LOGGER.debug(f"{self._name}: Skipping position set. Supported: {supported_features & CoverEntityFeature.SET_POSITION}, Service Found: {has_pos_service}.")
        else:
            _LOGGER.debug(
                f"{self._name}: Height '{height_to_set_percent:.2f}%' not sent, value was the same or restricted.")

        # Angle positioning
        if send_angle_command or self._enforce_position_update:
            if (supported_features & CoverEntityFeature.SET_TILT_POSITION) and has_tilt_service:
                _LOGGER.info(f" {self._name}: Setting tilt position to {shutter_angle_percent:.1f}% (current: {self._previous_shutter_angle}).")
                try:
                    await self.hass.services.async_call(
                        "cover",
                        "set_cover_tilt_position",
                        {"entity_id": entity, "tilt_position": 100 - shutter_angle_percent},
                        blocking=False
                    )
                except Exception as e:
                    _LOGGER.error(f"{self._name}: Failed to set tilt position: {e}")
                self._previous_shutter_angle = shutter_angle_percent
            else:
                _LOGGER.debug(f"{self._name}: Skipping tilt set. Supported: {supported_features & CoverEntityFeature.SET_TILT_POSITION}, Service Found: {has_tilt_service}.")
        else:
            _LOGGER.debug(
                f"{self._name}: Angle '{angle_to_set_percent:.2f}%' not sent, value was the same or restricted.")

        # Always update HA state at the end to reflect the latest internal calculated values and attributes
        self._update_extra_state_attributes()

        _LOGGER.debug(f"{self._name}: _position_shutter finished.")

    async def async_unload(self) -> bool:
        """Clean up when the integration is unloaded."""
        _LOGGER.debug(f"{self._name}: Unloading Shadow Control")
        for listener in self._listeners:
            listener() # Remove event listener
        return True

    def _calculate_shutter_height(self) -> float:
        """
        Berechnet die Zielhöhe des Rolladens basierend auf Sonnenstand und
        Konfiguration für den Beschattungsbereich.
        Gibt die berechnete Höhe in Prozent (0-100) zurück.
        """
        _LOGGER.debug(f"{self._name}: Starting calculation of shutter height")

        width_of_light_strip = self._light_bar_width
        shadow_max_height_percent = self._shadow_max_height
        elevation = self._sun_elevation
        shutter_overall_height = self._shutter_height

        shutter_height_to_set_percent = shadow_max_height_percent

        if (
                width_of_light_strip is None
                or elevation is None
                or shutter_overall_height is None
                or shadow_max_height_percent is None  # Muss auch None-geprüft werden
        ):
            _LOGGER.warning(
                f"{self._name}: Not all required values for calcualation of shutter height available! "
                f"width_of_light_strip={width_of_light_strip}, elevation={elevation}, "
                f"shutter_overall_height={shutter_overall_height}, "
                f"shadow_max_height_percent={shadow_max_height_percent}. "
                f"Using initial default value of {shutter_height_to_set_percent}%")
            return shutter_height_to_set_percent  # Oder ein anderer Standard/Fehlerwert

        if width_of_light_strip != 0:
            # PHP's deg2rad entspricht math.radians
            # PHP's tan entspricht math.tan
            shutter_height_from_bottom_raw = width_of_light_strip * math.tan(
                math.radians(elevation))

            # PHP's round ist in der Regel kaufmännisch runden (0.5 aufrunden).
            # Python's round() rundet zur nächsten geraden Zahl bei .5 (banker's rounding).
            # Für kaufmännisches Runden müsste man math.floor(x + 0.5) verwenden oder Decimal.
            # Für Rolladenpositionen ist der Unterschied meist unerheblich, daher bleiben wir bei round().
            shutter_height_to_set = round(shutter_height_from_bottom_raw)

            # PHP: 100 - round($shutterHeightToSet * 100 / $shutterOverallHeight);
            new_shutter_height = 100 - round((shutter_height_to_set * 100) / shutter_overall_height)

            if new_shutter_height < shadow_max_height_percent:
                shutter_height_to_set_percent = new_shutter_height
                _LOGGER.debug(
                    f"{self._name}: Elevation: {elevation}°, Height: {shutter_overall_height}, "
                    f"Light strip width: {width_of_light_strip}, "
                    f"Resulting shutter height: {shutter_height_to_set} ({shutter_height_to_set_percent}%). "
                    f"Is smaller than max height")
            else:
                _LOGGER.debug(
                    f"{self._name}: Elevation: {elevation}°, Height: {shutter_overall_height}, "
                    f"Light strip width: {width_of_light_strip}, "
                    f"Resulting shutter height ({new_shutter_height}%) is bigger or equal than given max height ({shadow_max_height_percent}%). "
                    f"Using max height")
        else:
            _LOGGER.debug(
                f"{self._name}: width_of_light_strip is 0. No height calculation required. "
                f"Using default height {shutter_height_to_set_percent}%.")

        return self._handle_shutter_height_stepping(shutter_height_to_set_percent)

    def _handle_shutter_height_stepping(self, calculated_height_percent: float) -> float:
        """
        Passt die Rollladenhöhe an die konfigurierte minimale Schrittweite an.
        Entspricht der PHP-Funktion LB_LBSID_handleShutterHeightStepping.
        """
        shutter_stepping_percent = self._stepping_height

        if shutter_stepping_percent is None:
            _LOGGER.warning(
                f"{self._name}: 'self._stepping_height' is None. Using 0 (no stepping).")
            shutter_stepping_percent = 0.0  # Standardwert, wenn nicht konfiguriert

        # Only apply stepping if the stepping value is not zero and height is not already a multiple
        if shutter_stepping_percent != 0:
            remainder = calculated_height_percent % shutter_stepping_percent
            if remainder != 0:
                # The PHP logic seems to round up to the next full step.
                # Example: 10% stepping, current height 23%. remainder = 3.
                # 23 + 10 - 3 = 30. (Rounds up to the next full step).
                adjusted_height = calculated_height_percent + shutter_stepping_percent - remainder
                _LOGGER.debug(
                    f"{self._name}: Adjusting shutter height from {calculated_height_percent:.2f}% "
                    f"to {adjusted_height:.2f}% (stepping: {shutter_stepping_percent:.2f}%)."
                )
                return adjusted_height

        _LOGGER.debug(
            f"{self._name}: Shutter height {calculated_height_percent:.2f}% "
            f"fits stepping or stepping is 0. No adjustment."
        )
        return calculated_height_percent

    def _calculate_shutter_angle(self) -> float:
        """
        Berechnet den Zielwinkel der Lamellen, um Sonneneinstrahlung zu verhindern.
        Gibt den berechneten Winkel in Prozent (0-100) zurück.
        """
        _LOGGER.debug(f"{self._name}: Starting calculation of shutter angle")

        elevation = self._sun_elevation
        azimuth = self._sun_azimuth  # For logging
        given_shutter_slat_width = self._slat_width
        shutter_slat_distance = self._slat_distance
        shutter_angle_offset = self._angle_offset
        min_shutter_angle_percent = self._min_slat_angle
        max_shutter_angle_percent = self._shadow_max_angle
        shutter_type_str = self._shutter_type  # String "90_degree_slats" or "180_degree_slats"

        # Der effektive Elevationswinkel kommt aus der Instanzvariable, die von _check_if_facade_is_in_sun gesetzt wird
        effective_elevation = self._effective_elevation

        if (
                elevation is None or azimuth is None
                or given_shutter_slat_width is None or shutter_slat_distance is None
                or shutter_angle_offset is None or min_shutter_angle_percent is None
                or max_shutter_angle_percent is None or shutter_type_str is None
                or effective_elevation is None
        ):
            _LOGGER.warning(
                f"{self._name}: Not all required values for angle calculation available. "
                f"elevation={elevation}, azimuth={azimuth}, "
                f"slat_width={given_shutter_slat_width}, slat_distance={shutter_slat_distance}, "
                f"angle_offset={shutter_angle_offset}, min_angle={min_shutter_angle_percent}, "
                f"max_angle={max_shutter_angle_percent}, shutter_type={shutter_type_str}, "
                f"effective_elevation={effective_elevation}. Returning 0.0")
            return 0.0  # Standardwert bei fehlenden Daten

        # ==============================
        # Math based on oblique triangle

        # $alpha is the opposite angle of shutter slat width, so this is the difference
        # effectiveElevation and vertical
        alpha_deg = 90 - effective_elevation
        alpha_rad = math.radians(alpha_deg)

        # $beta is the opposit angle of shutter slat distance
        asin_arg = (math.sin(alpha_rad) * shutter_slat_distance) / given_shutter_slat_width

        if not (-1 <= asin_arg <= 1):
            _LOGGER.warning(
                f"{self._name}: Argument for asin() out of valid range ({-1 <= asin_arg <= 1}). "
                f"Current value: {asin_arg}. Unable to compute angle, returning 0.0")
            return 0.0

        beta_rad = math.asin(asin_arg)
        beta_deg = math.degrees(beta_rad)

        # $gamma is the angle between vertical and shutter slat
        gamma_deg = 180 - alpha_deg - beta_deg

        # $shutterAnglePercent is the difference between horizontal and shutter slat,
        # so this is the result of the calculation
        shutter_angle_degrees = round(90 - gamma_deg)

        _LOGGER.debug(f"{self._name}: Elevation/azimuth: {elevation}°/{azimuth}°, "
                      f"resulting effective elevation and shutter angle: "
                      f"{effective_elevation}°/{shutter_angle_degrees}° (without stepping and offset)")

        shutter_angle_percent: float
        if shutter_type_str == "90_degree_slats":
            shutter_angle_percent = shutter_angle_degrees / 0.9
        elif shutter_type_str == "180_degree_slats":
            shutter_angle_percent = shutter_angle_degrees / 1.8 + 50
        else:
            _LOGGER.warning(
                f"{self._name}: Unknown shutter type '{shutter_type_str}'. Using default (90°)")
            shutter_angle_percent = shutter_angle_degrees / 0.9  # Standardverhalten

        # Sicherstellen, dass der Winkel nicht negativ wird
        if shutter_angle_percent < 0:
            shutter_angle_percent = 0.0

        # Runden vor dem Stepping, wie im PHP-Code
        shutter_angle_percent_rounded_for_stepping = round(shutter_angle_percent)

        shutter_angle_percent_with_stepping = self._handle_shutter_angle_stepping(
            shutter_angle_percent_rounded_for_stepping)

        shutter_angle_percent_with_stepping += shutter_angle_offset

        if shutter_angle_percent_with_stepping < min_shutter_angle_percent:
            final_shutter_angle_percent = min_shutter_angle_percent
            _LOGGER.debug(
                f"{self._name}: Limiting angle to min: {min_shutter_angle_percent}%")
        elif shutter_angle_percent_with_stepping > max_shutter_angle_percent:
            final_shutter_angle_percent = max_shutter_angle_percent
            _LOGGER.debug(
                f"{self._name}: Limiting angle to max: {max_shutter_angle_percent}%")
        else:
            final_shutter_angle_percent = shutter_angle_percent_with_stepping

        # Endgültiges Runden des finalen Winkels
        final_shutter_angle_percent = round(final_shutter_angle_percent)

        _LOGGER.debug(
            f"{self._name}: Resulting shutter angle with offset and stepping: {final_shutter_angle_percent}%")
        return float(final_shutter_angle_percent)  # Sicherstellen, dass es ein Float zurückgibt

    def _handle_shutter_angle_stepping(self, calculated_angle_percent: float) -> float:
        """
        Passt den berechneten Lamellenwinkel an das vorgegebene Stepping an.
        """
        _LOGGER.debug(
            f"{self._name}: Computing shutter angle stepping for {calculated_angle_percent}%")

        shutter_stepping_percent = self._stepping_angle

        if shutter_stepping_percent is None:
            _LOGGER.warning(
                f"{self._name}: 'stepping_angle' is None. Stepping can't be computed, returning initial angle {calculated_angle_percent}%")
            return calculated_angle_percent

        # Die PHP-Logik in Python:
        # if ($shutterSteppingPercent != 0 && ($shutterAnglePercent % $shutterSteppingPercent) != 0) {
        #    $shutterAnglePercent = $shutterAnglePercent + $shutterSteppingPercent - ($shutterAnglePercent % $shutterSteppingPercent);
        # }

        if shutter_stepping_percent != 0:
            remainder = calculated_angle_percent % shutter_stepping_percent
            if remainder != 0:
                adjusted_angle = calculated_angle_percent + shutter_stepping_percent - remainder
                _LOGGER.debug(
                    f"{self._name}: Applied stepping of {calculated_angle_percent}% to resulting {adjusted_angle}%. Stepping width: {shutter_stepping_percent}%.")
                return adjusted_angle

        _LOGGER.debug(
            f"{self._name}: No stepping necessary or stepping value is 0. Returning initial angle {calculated_angle_percent}%")
        return calculated_angle_percent

    # #######################################################################
    # State handling starting here
    #
    # =======================================================================
    # State SHADOW_FULL_CLOSE_TIMER_RUNNING
    async def _handle_state_shadow_full_close_timer_running(self) -> ShutterState:
        _LOGGER.debug(f"{self._name}: Handle SHADOW_FULL_CLOSE_TIMER_RUNNING")
        if await self._check_if_facade_is_in_sun() and await self._is_shadow_control_enabled():
            current_brightness = self._brightness
            shadow_threshold_close = self._shadow_brightness_level
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
                        _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING} ({ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING.name}): Timer finished, brightness above threshold, moving to shadow position ({target_height}%, {target_angle}%). Next state: {ShutterState.SHADOW_FULL_CLOSED}")
                        return ShutterState.SHADOW_FULL_CLOSED
                    else:
                        _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING} ({ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING.name}): Error within calculation of height a/o angle, staying at {ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING}")
                        return ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING
                else:
                    _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING} ({ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING.name}): Waiting for timer (Brightness big enough)")
                    return ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING
            else:
                _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING} ({ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING.name}): Brightness ({current_brightness}) not above threshold ({shadow_threshold_close}), transitioning to {ShutterState.SHADOW_NEUTRAL}")
                self._cancel_recalculation_timer()
                return ShutterState.SHADOW_NEUTRAL
        else:
            neutral_height = self._neutral_pos_height
            neutral_angle = self._neutral_pos_angle
            if neutral_height is not None and neutral_angle is not None:
                await self._position_shutter(
                    float(neutral_height),
                    float(neutral_angle),
                    shadow_position=False,
                    stop_timer=True,  # Stop Timer
                )
                _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING} ({ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING.name}): Not in the sun or shadow mode disabled, transitioning to ({neutral_height}%, {neutral_angle}%) with state {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL
            else:
                _LOGGER.warning(f"{self._name}: State {ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING} ({ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING.name}): Neutral height or angle not configured, transitioning to {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL

        # Entsprechung zu LB_LBSID_positionShutterWithPreviousValues
        _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING} ({ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING.name}): Staying at previous position.")
        return ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING

    # =======================================================================
    # State SHADOW_FULL_CLOSED
    async def _handle_state_shadow_full_closed(self) -> ShutterState:
        _LOGGER.debug(f"{self._name}: Handle SHADOW_FULL_CLOSED")
        if await self._check_if_facade_is_in_sun() and await self._is_shadow_control_enabled():
            current_brightness = self._get_current_brightness()
            shadow_threshold_close = self._shadow_brightness_level
            shadow_open_slat_delay = self._shadow_look_through_seconds
            if (
                    current_brightness is not None
                    and shadow_threshold_close is not None
                    and shadow_open_slat_delay is not None
                    and current_brightness < shadow_threshold_close
            ):
                _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_FULL_CLOSED} ({ShutterState.SHADOW_FULL_CLOSED.name}): Brightness ({current_brightness}) below threshold ({shadow_threshold_close}), starting timer for {ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING} ({shadow_open_slat_delay}s)")
                await self._start_recalculation_timer(shadow_open_slat_delay)
                return ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING
            else:
                _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_FULL_CLOSED} ({ShutterState.SHADOW_FULL_CLOSED.name}): Brightness not below threshold, recalculating shadow position")
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
            neutral_height = self._neutral_pos_height
            neutral_angle = self._neutral_pos_angle
            if neutral_height is not None and neutral_angle is not None:
                await self._position_shutter(
                    float(neutral_height),
                    float(neutral_angle),
                    shadow_position=False,
                    stop_timer=True,  # Stop Timer
                )
                _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_FULL_CLOSED} ({ShutterState.SHADOW_FULL_CLOSED.name}): Not in sun or shadow mode deactivated, moving to neutral position ({neutral_height}%, {neutral_angle}%) und state {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL
            else:
                _LOGGER.warning(f"{self._name}: State {ShutterState.SHADOW_FULL_CLOSED} ({ShutterState.SHADOW_FULL_CLOSED.name}): Neutral height or angle not configured, moving to state {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL

        # Entsprechung zu LB_LBSID_positionShutterWithPreviousValues
        _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_FULL_CLOSED} ({ShutterState.SHADOW_FULL_CLOSED.name}): Staying at previous position")
        return ShutterState.SHADOW_FULL_CLOSED

    # =======================================================================
    # State SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING
    async def _handle_state_shadow_horizontal_neutral_timer_running(self) -> ShutterState:
        _LOGGER.debug(f"{self._name}: Handle SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING")
        if await self._check_if_facade_is_in_sun() and await self._is_shadow_control_enabled():
            current_brightness = self._get_current_brightness()
            shadow_threshold_close = self._shadow_brightness_level
            shadow_open_slat_angle = self._shadow_look_through_angle
            if (
                    current_brightness is not None
                    and shadow_threshold_close is not None
                    and shadow_open_slat_angle is not None
                    and current_brightness > shadow_threshold_close
            ):
                _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING} ({ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING.name}): Brightness ({current_brightness}) again above threshold ({shadow_threshold_close}), transitioning to {ShutterState.SHADOW_FULL_CLOSED} and stopping timer")
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
                        _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING} ({ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING.name}): Timer finished, moving to height {target_height}% with neutral slats ({shadow_open_slat_angle}°) and state {ShutterState.SHADOW_HORIZONTAL_NEUTRAL}")
                        return ShutterState.SHADOW_HORIZONTAL_NEUTRAL
                    else:
                        _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING} ({ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING.name}): Error during calculation of height and angle for open slats, staying at {ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING}")
                        return ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING
                else:
                    _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING} ({ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING.name}): Waiting for timer (brightness not high enough)")
                    return ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING
        else:
            neutral_height = self._neutral_pos_height
            neutral_angle = self._neutral_pos_angle
            if neutral_height is not None and neutral_angle is not None:
                await self._position_shutter(
                    float(neutral_height),
                    float(neutral_angle),
                    shadow_position=False,
                    stop_timer=True,  # Stop Timer
                )
                _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING} ({ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING.name}): Not in the sun or shadow mode disabled, moving to neutral position ({neutral_height}%, {neutral_angle}%) and state {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL
            else:
                _LOGGER.warning(f"{self._name}: State {ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING} ({ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING.name}): Neutral height or angle not configured, transitioning to {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL

        # Entsprechung zu LB_LBSID_positionShutterWithPreviousValues
        _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING} ({ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING.name}): Staying at previous position")
        return ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING

    # =======================================================================
    # State SHADOW_HORIZONTAL_NEUTRAL
    async def _handle_state_shadow_horizontal_neutral(self) -> ShutterState:
        _LOGGER.debug(f"{self._name}: Handle SHADOW_HORIZONTAL_NEUTRAL")
        if await self._check_if_facade_is_in_sun() and await self._is_shadow_control_enabled():
            current_brightness = self._get_current_brightness()
            shadow_threshold_close = self._shadow_brightness_level
            shadow_open_shutter_delay = self._shadow_open_seconds
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
                    _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_HORIZONTAL_NEUTRAL} ({ShutterState.SHADOW_HORIZONTAL_NEUTRAL.name}): Brightness ({current_brightness}) above threshold ({shadow_threshold_close}), moving to shadow position ({target_height}%, {target_angle}%) and state {ShutterState.SHADOW_FULL_CLOSED}")
                    return ShutterState.SHADOW_FULL_CLOSED
                else:
                    _LOGGER.warning(f"{self._name}: State {ShutterState.SHADOW_HORIZONTAL_NEUTRAL} ({ShutterState.SHADOW_HORIZONTAL_NEUTRAL.name}): Error at calculating height or angle, staying at {ShutterState.SHADOW_HORIZONTAL_NEUTRAL}")
                    return ShutterState.SHADOW_HORIZONTAL_NEUTRAL
            elif shadow_open_shutter_delay is not None:
                _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_HORIZONTAL_NEUTRAL} ({ShutterState.SHADOW_HORIZONTAL_NEUTRAL.name}): Brightness not above threshold, starting timer for {ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING} ({shadow_open_shutter_delay}s)")
                await self._start_recalculation_timer(shadow_open_shutter_delay)
                return ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING
            else:
                _LOGGER.warning(f"{self._name}: State {ShutterState.SHADOW_HORIZONTAL_NEUTRAL} ({ShutterState.SHADOW_HORIZONTAL_NEUTRAL.name}): Brightness not above threshold and 'shadow_open_shutter_delay' not configured, staying at {ShutterState.SHADOW_HORIZONTAL_NEUTRAL}")
                return ShutterState.SHADOW_HORIZONTAL_NEUTRAL
        else:
            neutral_height = self._neutral_pos_height
            neutral_angle = self._neutral_pos_angle
            if neutral_height is not None and neutral_angle is not None:
                await self._position_shutter(
                    float(neutral_height),
                    float(neutral_angle),
                    shadow_position=False,
                    stop_timer=True,  # Stop Timer (falls ein Timer aktiv war)
                )
                _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_HORIZONTAL_NEUTRAL} ({ShutterState.SHADOW_HORIZONTAL_NEUTRAL.name}): Not in sun or shadow mode disabled, moving to neutral position ({neutral_height}%, {neutral_angle}%) and state {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL
            else:
                _LOGGER.warning(f"{self._name}: State {ShutterState.SHADOW_HORIZONTAL_NEUTRAL} ({ShutterState.SHADOW_HORIZONTAL_NEUTRAL.name}): Neutral height or angle not configured, transitioning to {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL

        # Entsprechung zu LB_LBSID_positionShutterWithPreviousValues
        _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_HORIZONTAL_NEUTRAL} ({ShutterState.SHADOW_HORIZONTAL_NEUTRAL.name}): Staying at previous position")
        return ShutterState.SHADOW_HORIZONTAL_NEUTRAL

    # =======================================================================
    # State SHADOW_NEUTRAL_TIMER_RUNNING
    async def _handle_state_shadow_neutral_timer_running(self) -> ShutterState:
        _LOGGER.debug(f"{self._name}: Handle SHADOW_NEUTRAL_TIMER_RUNNING")
        if await self._check_if_facade_is_in_sun() and await self._is_shadow_control_enabled():
            current_brightness = self._get_current_brightness()
            shadow_threshold_close = self._shadow_brightness_level
            height_after_shadow = self._after_shadow_height
            angle_after_shadow = self._after_shadow_angle
            if (
                    current_brightness is not None
                    and shadow_threshold_close is not None
                    and current_brightness > shadow_threshold_close
            ):
                _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING} ({ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING.name}): Brightness ({current_brightness}) again above threshold ({shadow_threshold_close}), state {ShutterState.SHADOW_FULL_CLOSED} and stopping timer")
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
                        _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING} ({ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING.name}): Timer finished, moving to after-shadow position ({height_after_shadow}%, {angle_after_shadow}°) and state {ShutterState.SHADOW_NEUTRAL}")
                        return ShutterState.SHADOW_NEUTRAL
                    else:
                        _LOGGER.warning(f"{self._name}: State {ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING} ({ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING.name}): Height or angle after shadow not configured, staying at {ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING}")
                        return ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING
                else:
                    _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING} ({ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING.name}): Waiting for timer (brightness not high enough)")
                    return ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING
        else:
            neutral_height = self._neutral_pos_height
            neutral_angle = self._neutral_pos_angle
            if neutral_height is not None and neutral_angle is not None:
                await self._position_shutter(
                    float(neutral_height),
                    float(neutral_angle),
                    shadow_position=False,
                    stop_timer=True,  # Stop Timer
                )
                _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING} ({ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING.name}): Not in sun or shadow mode disabled, moving to neutral position ({neutral_height}%, {neutral_angle}%) and state {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL
            else:
                _LOGGER.warning(f"{self._name}: State {ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING} ({ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING.name}): Neutral height or angle not configured, transitioning to {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL

        # Entsprechung zu LB_LBSID_positionShutterWithPreviousValues
        _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING} ({ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING.name}): Staying at previous position")
        return ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING

    # =======================================================================
    # State SHADOW_NEUTRAL
    async def _handle_state_shadow_neutral(self) -> ShutterState:
        _LOGGER.debug(f"{self._name}: Handle SHADOW_NEUTRAL")
        if await self._check_if_facade_is_in_sun() and await self._is_shadow_control_enabled():
            current_brightness = self._get_current_brightness()
            shadow_threshold_close = self._shadow_brightness_level
            dawn_handling_active = self._dawn_control_enabled
            dawn_brightness = self._get_current_dawn_brightness()
            dawn_threshold_close = self._dawn_brightness_level
            shadow_close_delay = self._shadow_after_seconds
            dawn_close_delay = self._dawn_after_seconds
            height_after_shadow = self._after_shadow_height
            angle_after_shadow = self._after_shadow_angle

            if (
                    current_brightness is not None
                    and shadow_threshold_close is not None
                    and current_brightness > shadow_threshold_close
                    and shadow_close_delay is not None
            ):
                _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_NEUTRAL} ({ShutterState.SHADOW_NEUTRAL.name}): Brightness ({current_brightness}) above threshold ({shadow_threshold_close}), starting timer for {ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING} ({shadow_close_delay}s)")
                await self._start_recalculation_timer(shadow_close_delay)
                return ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING
            elif (
                    dawn_handling_active
                    and dawn_brightness is not None
                    and dawn_threshold_close is not None
                    and dawn_brightness < dawn_threshold_close
                    and dawn_close_delay is not None
            ):
                _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_NEUTRAL} ({ShutterState.SHADOW_NEUTRAL.name}): Dawn handling active and dawn-brighness ({dawn_brightness}) below threshold ({dawn_threshold_close}), starting timer for {ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING} ({dawn_close_delay}s)")
                await self._start_recalculation_timer(dawn_close_delay)
                return ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING
            elif height_after_shadow is not None and angle_after_shadow is not None:
                await self._position_shutter(
                    float(height_after_shadow),
                    float(angle_after_shadow),
                    shadow_position=False,
                    stop_timer=True,
                )
                _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_NEUTRAL} ({ShutterState.SHADOW_NEUTRAL.name}): Moving to after-shadow position ({height_after_shadow}%, {angle_after_shadow}%)")
                return ShutterState.SHADOW_NEUTRAL
            else:
                _LOGGER.warning(f"{self._name}: State {ShutterState.SHADOW_NEUTRAL} ({ShutterState.SHADOW_NEUTRAL.name}): Height or angle after shadow not configured, staying at {ShutterState.SHADOW_NEUTRAL}")
                return ShutterState.SHADOW_NEUTRAL

        if await self._is_dawn_control_enabled():
            dawn_brightness = self._get_current_dawn_brightness()
            dawn_threshold_close = self._dawn_brightness_level
            dawn_close_delay = self._dawn_after_seconds
            if (
                    dawn_brightness is not None
                    and dawn_threshold_close is not None
                    and dawn_brightness < dawn_threshold_close
                    and dawn_close_delay is not None
            ):
                _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_NEUTRAL.name} ({ShutterState.SHADOW_NEUTRAL.name.name}): Dawn mode active and brightness ({dawn_brightness}) below threshold ({dawn_threshold_close}), starting timer for {ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING} ({dawn_close_delay}s)")
                await self._start_recalculation_timer(dawn_close_delay)
                return ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING

        neutral_height = self._neutral_pos_height
        neutral_angle = self._neutral_pos_angle
        if neutral_height is not None and neutral_angle is not None:
            await self._position_shutter(
                float(neutral_height),
                float(neutral_angle),
                shadow_position=False,
                stop_timer=True,  # Stop Timer (falls ein Timer aktiv war)
            )
            _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_NEUTRAL} ({ShutterState.SHADOW_NEUTRAL.name}): Not in sun or shadow mode disabled or dawn mode not active, moving to neutral position ({neutral_height}%, {neutral_angle}%) and state {ShutterState.NEUTRAL}")
            return ShutterState.NEUTRAL
        else:
            _LOGGER.warning(f"{self._name}: State {ShutterState.SHADOW_NEUTRAL} ({ShutterState.SHADOW_NEUTRAL.name}): Neutral height or angle not configured, transitioning to {ShutterState.NEUTRAL}")
            return ShutterState.NEUTRAL

    # =======================================================================
    # State NEUTRAL
    async def _handle_state_neutral(self) -> ShutterState:
        _LOGGER.debug(f"{self._name}: Handle NEUTRAL")
        if await self._check_if_facade_is_in_sun() and await self._is_shadow_control_enabled():
            _LOGGER.debug(f"{self._name}: self._check_if_facade_is_in_sun and self._is_shadow_handling_activated")
            current_brightness = self._get_current_brightness()
            shadow_threshold_close = self._shadow_brightness_level
            shadow_close_delay = self._shadow_after_seconds
            if (
                    current_brightness is not None
                    and shadow_threshold_close is not None
                    and current_brightness > shadow_threshold_close
                    and shadow_close_delay is not None
            ):
                _LOGGER.debug(f"{self._name}: State {ShutterState.NEUTRAL} ({ShutterState.NEUTRAL.name}): Brightness ({current_brightness}) above dawn threshold ({shadow_threshold_close}), starting timer for {ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING} ({shadow_close_delay}s)")
                await self._start_recalculation_timer(shadow_close_delay)
                return ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING

        if await self._is_dawn_control_enabled():
            dawn_brightness = self._get_current_dawn_brightness()
            dawn_threshold_close = self._dawn_brightness_level
            dawn_close_delay = self._dawn_after_seconds
            if (
                    dawn_brightness is not None
                    and dawn_threshold_close is not None
                    and dawn_brightness < dawn_threshold_close
                    and dawn_close_delay is not None
            ):
                _LOGGER.debug(f"{self._name}: State {ShutterState.NEUTRAL} ({ShutterState.NEUTRAL.name}): Dawn mode active and brightness ({dawn_brightness}) below dawn threshold ({dawn_threshold_close}), starting timer for {ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING} ({dawn_close_delay}s)")
                await self._start_recalculation_timer(dawn_close_delay)
                return ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING

        neutral_height = self._neutral_pos_height
        neutral_angle = self._neutral_pos_angle
        if neutral_height is not None and neutral_angle is not None:
            await self._position_shutter(
                float(neutral_height),
                float(neutral_angle),
                shadow_position=False,
                stop_timer=True,
            )
            _LOGGER.debug(f"{self._name}: State {ShutterState.NEUTRAL} ({ShutterState.NEUTRAL.name}): Moving shutter to neutral position ({neutral_height}%, {neutral_angle}%).")
        return ShutterState.NEUTRAL

    # =======================================================================
    # State DAWN_NEUTRAL
    async def _handle_state_dawn_neutral(self) -> ShutterState:
        _LOGGER.debug(f"{self._name}: Handle DAWN_NEUTRAL")
        current_brightness = self._get_current_brightness()

        shadow_handling_active = await self._is_shadow_control_enabled()
        shadow_threshold_close = self._shadow_brightness_level
        shadow_close_delay = self._shadow_after_seconds

        dawn_handling_active = await self._is_dawn_control_enabled()
        dawn_brightness = self._get_current_dawn_brightness()
        dawn_threshold_close = self._dawn_brightness_level
        dawn_close_delay = self._dawn_after_seconds
        height_after_dawn = self._after_dawn_height
        angle_after_dawn = self._after_dawn_angle

        is_in_sun = await self._check_if_facade_is_in_sun()
        neutral_height = self._neutral_pos_height
        neutral_angle = self._neutral_pos_angle

        if dawn_handling_active:
            if (
                    dawn_brightness is not None
                    and dawn_threshold_close is not None
                    and dawn_brightness < dawn_threshold_close
                    and dawn_close_delay is not None
            ):
                _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_NEUTRAL} ({ShutterState.DAWN_NEUTRAL.name}): Dawn mode active and brightness ({dawn_brightness}) below dawn threshold ({dawn_threshold_close}), starting timer for {ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING} ({dawn_close_delay}s)")
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
                _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_NEUTRAL} ({ShutterState.DAWN_NEUTRAL.name}): Within sun, shadow mode active and brightness ({current_brightness}) above shadow threshold ({shadow_threshold_close}), starting timer for {ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING} ({shadow_close_delay}s)")
                await self._start_recalculation_timer(shadow_close_delay)
                return ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING
            elif height_after_dawn is not None and angle_after_dawn is not None:
                await self._position_shutter(
                    float(height_after_dawn),
                    float(angle_after_dawn),
                    shadow_position=False,
                    stop_timer=True,
                )
                _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_NEUTRAL} ({ShutterState.DAWN_NEUTRAL.name}): Moving shutter to after-dawn position ({height_after_dawn}%, {angle_after_dawn}%).")
                return ShutterState.DAWN_NEUTRAL
            else:
                _LOGGER.warning(f"{self._name}: State {ShutterState.DAWN_NEUTRAL} ({ShutterState.DAWN_NEUTRAL.name}): Height or angle after dawn not configured, staying at {ShutterState.DAWN_NEUTRAL}")
                return ShutterState.DAWN_NEUTRAL

        if (
                is_in_sun
                and shadow_handling_active
                and current_brightness is not None
                and shadow_threshold_close is not None
                and current_brightness > shadow_threshold_close
                and shadow_close_delay is not None
        ):
            _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_NEUTRAL} ({ShutterState.DAWN_NEUTRAL.name}): Within sun, shadow mode active and brightness ({current_brightness}) above shadow threshold ({shadow_threshold_close}), starting timer for {ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING} ({shadow_close_delay}s)")
            await self._start_recalculation_timer(shadow_close_delay)
            return ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING

        if neutral_height is not None and neutral_angle is not None:
            await self._position_shutter(
                float(neutral_height),
                float(neutral_angle),
                shadow_position=False,
                stop_timer=True,
            )
            _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_NEUTRAL} ({ShutterState.DAWN_NEUTRAL.name}): Dawn mode disabled or requirements for shadow not given, moving to neutral position ({neutral_height}%, {neutral_angle}%)")
            return ShutterState.NEUTRAL
        else:
            _LOGGER.warning(f"{self._name}: State {ShutterState.DAWN_NEUTRAL} ({ShutterState.DAWN_NEUTRAL.name}): Neutral height or angle not configured, transitioning to {ShutterState.NEUTRAL}")
            return ShutterState.NEUTRAL

    # =======================================================================
    # State DAWN_NEUTRAL_TIMER_RUNNING
    async def _handle_state_dawn_neutral_timer_running(self) -> ShutterState:
        _LOGGER.debug(f"{self._name}: Handle DAWN_NEUTRAL_TIMER_RUNNING")
        if await self._is_dawn_control_enabled():
            dawn_brightness = self._get_current_dawn_brightness()
            dawn_threshold_close = self._dawn_brightness_level
            dawn_height = self._dawn_max_height
            dawn_open_slat_angle = self._dawn_look_through_angle

            if (
                    dawn_brightness is not None
                    and dawn_threshold_close is not None
                    and dawn_brightness < dawn_threshold_close
            ):
                _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_NEUTRAL_TIMER_RUNNING} ({ShutterState.DAWN_NEUTRAL_TIMER_RUNNING.name}): Dawn brightness ({dawn_brightness}) again below threshold ({dawn_threshold_close}), moving to {ShutterState.DAWN_FULL_CLOSED} and stopping timer")
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
                        _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_NEUTRAL_TIMER_RUNNING} ({ShutterState.DAWN_NEUTRAL_TIMER_RUNNING.name}): Timer finished, moving to dawn height ({dawn_height}%) with open slats ({dawn_open_slat_angle}°) and state {ShutterState.DAWN_NEUTRAL}")
                        return ShutterState.DAWN_NEUTRAL
                    else:
                        _LOGGER.warning(f"{self._name}: State {ShutterState.DAWN_NEUTRAL_TIMER_RUNNING} ({ShutterState.DAWN_NEUTRAL_TIMER_RUNNING.name}): Dawn height or angle for open slats not configured, staying at {ShutterState.DAWN_NEUTRAL_TIMER_RUNNING}")
                        return ShutterState.DAWN_NEUTRAL_TIMER_RUNNING
                else:
                    _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_NEUTRAL_TIMER_RUNNING} ({ShutterState.DAWN_NEUTRAL_TIMER_RUNNING.name}): Waiting for timer (brightness not low enough)")
                    return ShutterState.DAWN_NEUTRAL_TIMER_RUNNING
        else:
            neutral_height = self._neutral_pos_height
            neutral_angle = self._neutral_pos_angle
            if neutral_height is not None and neutral_angle is not None:
                await self._position_shutter(
                    float(neutral_height),
                    float(neutral_angle),
                    shadow_position=False,
                    stop_timer=True,  # Stop Timer
                )
                _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_NEUTRAL_TIMER_RUNNING} ({ShutterState.DAWN_NEUTRAL_TIMER_RUNNING.name}): Dawn mode disabled, moving to neutral position ({neutral_height}%, {neutral_angle}%) and state {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL
            else:
                _LOGGER.warning(f"{self._name}: State {ShutterState.DAWN_NEUTRAL_TIMER_RUNNING} ({ShutterState.DAWN_NEUTRAL_TIMER_RUNNING.name}): Neutral height or angle not configured, transitioning to {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL

        # Entsprechung zu LB_LBSID_positionShutterWithPreviousValues
        _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_NEUTRAL_TIMER_RUNNING} ({ShutterState.DAWN_NEUTRAL_TIMER_RUNNING.name}): Staying at previous position")
        return ShutterState.DAWN_NEUTRAL_TIMER_RUNNING

    # =======================================================================
    # State DAWN_HORIZONTAL_NEUTRAL
    async def _handle_state_dawn_horizontal_neutral(self) -> ShutterState:
        _LOGGER.debug(f"{self._name}: Handle DAWN_HORIZONTAL_NEUTRAL")
        if await self._is_dawn_control_enabled():
            dawn_brightness = self._get_current_dawn_brightness()
            dawn_threshold_close = self._dawn_brightness_level
            dawn_height = self._dawn_max_height
            dawn_open_slat_angle = self._dawn_look_through_angle
            dawn_open_shutter_delay = self._dawn_open_seconds

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
                _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_HORIZONTAL_NEUTRAL} ({ShutterState.DAWN_HORIZONTAL_NEUTRAL.name}): Dawn brightness ({dawn_brightness}) below threshold ({dawn_threshold_close}), moving to dawn height ({dawn_height}%) with open slats ({dawn_open_slat_angle}°) and state {ShutterState.DAWN_FULL_CLOSED}")
                return ShutterState.DAWN_FULL_CLOSED
            elif dawn_open_shutter_delay is not None:
                _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_HORIZONTAL_NEUTRAL} ({ShutterState.DAWN_HORIZONTAL_NEUTRAL.name}): Dawn brightness not below threshold, starting timer for {ShutterState.DAWN_NEUTRAL_TIMER_RUNNING} ({dawn_open_shutter_delay}s)")
                await self._start_recalculation_timer(dawn_open_shutter_delay)
                return ShutterState.DAWN_NEUTRAL_TIMER_RUNNING
            else:
                _LOGGER.warning(f"{self._name}: State {ShutterState.DAWN_HORIZONTAL_NEUTRAL} ({ShutterState.DAWN_HORIZONTAL_NEUTRAL.name}): Dawn brightness not below threshold and 'dawn_open_shutter_delay' not configured, staying at {ShutterState.DAWN_HORIZONTAL_NEUTRAL}")
                return ShutterState.DAWN_HORIZONTAL_NEUTRAL
        else:
            neutral_height = self._neutral_pos_height
            neutral_angle = self._neutral_pos_angle
            if neutral_height is not None and neutral_angle is not None:
                await self._position_shutter(
                    float(neutral_height),
                    float(neutral_angle),
                    shadow_position=False,
                    stop_timer=True,
                )
                _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_HORIZONTAL_NEUTRAL} ({ShutterState.DAWN_HORIZONTAL_NEUTRAL.name}): Dawn mode disabled, moving to neutral position ({neutral_height}%, {neutral_angle}%) and state {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL
            else:
                _LOGGER.warning(f"{self._name}: State {ShutterState.DAWN_HORIZONTAL_NEUTRAL} ({ShutterState.DAWN_HORIZONTAL_NEUTRAL.name}): Neutral height or angle not configured, transitioning to {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL

        # Entsprechung zu LB_LBSID_positionShutterWithPreviousValues
        _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_HORIZONTAL_NEUTRAL} ({ShutterState.DAWN_HORIZONTAL_NEUTRAL.name}): Staying at previous position")
        return ShutterState.DAWN_HORIZONTAL_NEUTRAL

    # =======================================================================
    # State DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING
    async def _handle_state_dawn_horizontal_neutral_timer_running(self) -> ShutterState:
        _LOGGER.debug(f"{self._name}: Handle DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING")
        if await self._is_dawn_control_enabled():
            dawn_brightness = self._get_current_dawn_brightness()
            dawn_threshold_close = self._dawn_brightness_level
            dawn_height = self._dawn_max_height
            dawn_open_slat_angle = self._dawn_look_through_angle
            if (
                    dawn_brightness is not None
                    and dawn_threshold_close is not None
                    and dawn_brightness < dawn_threshold_close
            ):
                _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING} ({ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING.name}): Dawn brightness ({dawn_brightness}) again below threshold ({dawn_threshold_close}), moving to {ShutterState.DAWN_FULL_CLOSED} and stopping timer")
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
                        _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING} ({ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING.name}): Timer finished, moving to dawn height ({dawn_height}%) with open slats ({dawn_open_slat_angle}°) and state {ShutterState.DAWN_HORIZONTAL_NEUTRAL}")
                        return ShutterState.DAWN_HORIZONTAL_NEUTRAL
                    else:
                        _LOGGER.warning(f"{self._name}: State {ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING} ({ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING.name}): Dawn height or angle for open slats not configured, staying at {ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING}")
                        return ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING
                else:
                    _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING} ({ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING.name}): Waiting for timer (brightness not low enough)")
                    return ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING
        else:
            neutral_height = self._neutral_pos_height
            neutral_angle = self._neutral_pos_angle
            if neutral_height is not None and neutral_angle is not None:
                await self._position_shutter(
                    float(neutral_height),
                    float(neutral_angle),
                    shadow_position=False,
                    stop_timer=True,  # Stop Timer
                )
                _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING} ({ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING.name}): Dawn mode disabled, moving to neutral position ({neutral_height}%, {neutral_angle}%) and state {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL
            else:
                _LOGGER.warning(f"{self._name}: State {ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING} ({ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING.name}): Neutral height or angle not configured, transitioning to {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL

        # Entsprechung zu LB_LBSID_positionShutterWithPreviousValues
        _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING} ({ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING.name}): Staying at previous position")
        return ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING

    # =======================================================================
    # State DAWN_FULL_CLOSED
    async def _handle_state_dawn_full_closed(self) -> ShutterState:
        _LOGGER.debug(f"{self._name}: Handle DAWN_FULL_CLOSED")
        if await self._is_dawn_control_enabled():
            dawn_brightness = self._get_current_dawn_brightness()
            dawn_threshold_close = self._dawn_brightness_level
            dawn_height = self._dawn_max_height
            dawn_open_slat_delay = self._dawn_look_through_seconds
            dawn_angle = self._dawn_max_angle
            if (
                    dawn_brightness is not None
                    and dawn_threshold_close is not None
                    and dawn_brightness > dawn_threshold_close
                    and dawn_open_slat_delay is not None
            ):
                _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_FULL_CLOSED} ({ShutterState.DAWN_FULL_CLOSED.name}): Dawn brightness ({dawn_brightness}) above threshold ({dawn_threshold_close}), starting timer for {ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING} ({dawn_open_slat_delay}s)")
                await self._start_recalculation_timer(dawn_open_slat_delay)
                return ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING
            elif dawn_height is not None and dawn_angle is not None:
                await self._position_shutter(
                    float(dawn_height),
                    float(dawn_angle),
                    shadow_position=False,
                    stop_timer=True,
                )
                _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_FULL_CLOSED} ({ShutterState.DAWN_FULL_CLOSED.name}): Dawn brightness not above threshold, moving to dawn position ({dawn_height}%, {dawn_angle}%)")
                return ShutterState.DAWN_FULL_CLOSED
            else:
                _LOGGER.warning(f"{self._name}: State {ShutterState.DAWN_FULL_CLOSED} ({ShutterState.DAWN_FULL_CLOSED.name}): Dawn height or angle not configured, staying at {ShutterState.DAWN_FULL_CLOSED}")
                return ShutterState.DAWN_FULL_CLOSED
        else:
            neutral_height = self._neutral_pos_height
            neutral_angle = self._neutral_pos_angle
            if neutral_height is not None and neutral_angle is not None:
                await self._position_shutter(
                    float(neutral_height),
                    float(neutral_angle),
                    shadow_position=False,
                    stop_timer=True,  # Stop Timer
                )
                _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_FULL_CLOSED} ({ShutterState.DAWN_FULL_CLOSED.name}): Dawn handling disabled, moving to neutral position ({neutral_height}%, {neutral_angle}%) and state {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL
            else:
                _LOGGER.warning(f"{self._name}: State {ShutterState.DAWN_FULL_CLOSED} ({ShutterState.DAWN_FULL_CLOSED.name}): Neutral height or angle not configured, transitioning to {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL

        # Entsprechung zu LB_LBSID_positionShutterWithPreviousValues
        _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_FULL_CLOSED} ({ShutterState.DAWN_FULL_CLOSED.name}): Staying at previous position")
        return ShutterState.DAWN_FULL_CLOSED

    # =======================================================================
    # State DAWN_FULL_CLOSE_TIMER_RUNNING
    async def _handle_state_dawn_full_close_timer_running(self) -> ShutterState:
        _LOGGER.debug(f"{self._name}: Handle DAWN_FULL_CLOSE_TIMER_RUNNING")
        if await self._is_dawn_control_enabled():
            dawn_brightness = self._get_current_dawn_brightness()
            dawn_threshold_close = self._dawn_brightness_level
            dawn_height = self._dawn_max_height
            dawn_angle = self._dawn_max_angle
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
                        _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING} ({ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING.name}): Timer finished, moving to dawn position ({dawn_height}%, {dawn_angle}%) and state {ShutterState.DAWN_FULL_CLOSED}")
                        return ShutterState.DAWN_FULL_CLOSED
                    else:
                        _LOGGER.warning(f"{self._name}: State {ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING} ({ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING.name}): Dawn height or angle not configured, staying at {ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING}")
                        return ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING
                else:
                    _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING} ({ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING.name}): Waiting for timer (brightness low enough)")
                    return ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING
            else:
                _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING} ({ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING.name}): Brightness ({dawn_brightness}) not below threshold ({dawn_threshold_close}), moving to {ShutterState.DAWN_NEUTRAL} and stopping timer")
                self._cancel_recalculation_timer()
                return ShutterState.DAWN_NEUTRAL
        else:
            neutral_height = self._neutral_pos_height
            neutral_angle = self._neutral_pos_angle
            if neutral_height is not None and neutral_angle is not None:
                await self._position_shutter(
                    float(neutral_height),
                    float(neutral_angle),
                    shadow_position=False,
                    stop_timer=True,  # Stop Timer
                )
                _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING} ({ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING.name}): Dawn mode disabled, moving to neutral position ({neutral_height}%, {neutral_angle}%) and state {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL
            else:
                _LOGGER.warning(f"{self._name}: State {ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING} ({ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING.name}): Neutral height or angle not configured, transitioning to {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL

        # Entsprechung zu LB_LBSID_positionShutterWithPreviousValues
        _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING} ({ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING.name}): Staying at previous position")
        return ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING

    # End of state handling
    # #######################################################################

    async def _is_shadow_control_enabled(self) -> bool:
        """Check if shadow handling is activated."""
        return self._shadow_control_enabled

    async def _is_dawn_control_enabled(self) -> bool:
        """Check if dawn handling is activated."""
        return self._dawn_control_enabled

    # =======================================================================
    # Entity state helper functions
    def _get_state_value(self, entity_id: str | None) -> str | None:
        """Helper to get the state of an entity."""
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if state:
            return state.state
        return None

    def _get_entity_numeric_state(self, entity_id: str | None, target_type: type, default_value: Any = None) -> Any:
        """
        Gibt den numerischen Zustand einer Entität zurück oder einen Standardwert,
        wenn die Entität nicht existiert, ihr Zustand nicht verfügbar ist oder nicht konvertiert werden kann.
        """
        if not entity_id: # <-- WICHTIG: Prüfung auf None/leeren String
            _LOGGER.warning(f"{self._name}: Missing entity id for numeric value (None/Empty). Using default {default_value}")
            return default_value

        state_obj = self.hass.states.get(entity_id)
        if not state_obj or state_obj.state in ['unknown', 'unavailable', 'none', None]:
            _LOGGER.debug(f"{self._name}: State of '{entity_id}' not available or invalid ('{state_obj.state if state_obj else 'None'}'). Using default {default_value}")
            return default_value
        try:
            return target_type(state_obj.state)
        except (ValueError, TypeError):
            _LOGGER.warning(f"{self._name}: Unable to convert '{state_obj.state}' of '{entity_id}' into {target_type.__name__}. Using default {default_value}")
            return default_value

    def _get_entity_boolean_state(self, entity_id: str | None, default_value: bool = False) -> bool:
        """
        Gibt den booleschen Zustand einer Entität zurück oder einen Standardwert,
        wenn die Entität nicht existiert, ihr Zustand nicht verfügbar ist oder nicht konvertiert werden kann.
        """
        if not entity_id: # <-- WICHTIG: Prüfung auf None/leeren String
            _LOGGER.warning(f"{self._name}: Missing entity id for boolean value (None/Empty). Using default {default_value}")
            return default_value

        state_obj = self.hass.states.get(entity_id)
        if not state_obj or state_obj.state in ['unknown', 'unavailable', 'none', None]:
            _LOGGER.debug(f"{self._name}: State of '{entity_id}' not available or invalid ('{state_obj.state if state_obj else 'None'}'). Using default {default_value}")
            return default_value
        return state_obj.state.lower() == 'on' # HA States sind oft 'on'/'off' Strings

    def _get_entity_string_state(self, entity_id: str | None, default_value: str | None = None) -> str | None:
        """
        Gibt den String-Zustand einer Entität zurück oder einen Standardwert,
        wenn die Entität nicht existiert oder ihr Zustand nicht verfügbar ist.
        """
        if not entity_id: # <-- WICHTIG: Prüfung auf None/leeren String
            _LOGGER.warning(f"{self._name}: Missing entity id for string value (None/Empty). Using default {default_value}")
            return default_value

        state_obj = self.hass.states.get(entity_id)
        if not state_obj or state_obj.state in ['unknown', 'unavailable', 'none', None]:
            _LOGGER.debug(f"{self._name}: State of '{entity_id}' not available or invalid ('{state_obj.state if state_obj else 'None'}'). Using default {default_value}")
            return default_value
        return str(state_obj.state)

    def _convert_shutter_angle_percent_to_degrees(self, angle_percent: float) -> float:
        """
        Konvertiert den Jalousienwinkel von Prozent (0-100) in Grad.
        0% = 0 Grad (Lamellen offen)
        100% = 90 Grad (Lamellen geschlossen)
        Kann auch auf mehr als 90 Grad gehen, wenn im Enum entsprechend definiert.
        """
        # Stellen Sie sicher, dass _facade_slat_min_angle_entity und _facade_slat_angle_offset_entity
        # in __init__ korrekt initialisiert sind und über _get_entity_numeric_state gelesen werden.

        min_slat_angle = self._min_slat_angle  # Dieser Wert sollte jetzt über _update_input_values gesetzt sein
        angle_offset = self._angle_offset  # Dieser Wert sollte jetzt über _update_input_values gesetzt sein

        # Sicherheitsprüfung für None-Werte, falls _update_input_values noch nicht durchlief oder Fehler hatte
        if min_slat_angle is None or angle_offset is None:
            _LOGGER.warning(
                f"{self._name}: _convert_shutter_angle_percent_to_degrees: min_slat_angle ({min_slat_angle}) or angle_offset ({angle_offset}) is None. Using default values (0, 0)")
            min_slat_angle = 0.0
            angle_offset = 0.0

        # Die Umrechnungsformel
        # Annahme: 0% ist offen (min_slat_angle) und 100% ist geschlossen (90 Grad + offset)
        # Ihre KNX-Doku oder LBS-Logik kann hier abweichen.
        # Wenn 0% = 0 Grad und 100% = 90 Grad Standard ist, dann ist es einfach angle_percent * 0.9.
        # Wenn 0% auf min_slat_angle mappt und 100% auf (90 + angle_offset) Grad:

        # Beispiel basierend auf typischer 0-100% zu 0-90° Konvertierung für Lamellen:
        # 0% = Lamellen horizontal (oft 0 Grad)
        # 100% = Lamellen vertikal (oft 90 Grad)

        # Wenn Sie eine variable 'max_angle' haben oder Ihre Logik anders ist, passen Sie dies an.
        # Basierend auf der PHP-LBS, wo 100% = 90 Grad ist (plus Offset/MinSlatAngle)
        # Beispiel: Wenn 0% = min_slat_angle und 100% = (90 + angle_offset)
        # angle_range = (90 + angle_offset) - min_slat_angle
        # return min_slat_angle + (angle_percent / 100.0) * angle_range

        # Für eine einfachere 0-100% zu 0-90° (oder 0-max_angle) mapping:
        # Gehen wir davon aus, dass 100% einem Winkel von (90 + angle_offset) Grad entspricht
        # und 0% dem min_slat_angle.

        # PHP-Beispiel aus dem LBS-Code (angenommen):
        # Angle in degrees = $shutterAnglePercent * 0.9; // 0-90 Grad
        # Angle in degrees = $angleInDegrees + $offset; // Plus Offset
        # Angle in degrees = max($minSlatAngle, $angleInDegrees); // Minimum Lamellenwinkel

        # Basierend auf der typischen KNX-Welt, wo 0% Lamellen offen sind, 100% Lamellen geschlossen (90 Grad)
        # und dann noch ein Min-Winkel und Offset hinzukommt:

        calculated_degrees = angle_percent * 0.9  # Konvertiert 0-100% in 0-90 Grad

        # Anwenden des Winkels-Offsets und des Minimum-Lamellenwinkels
        # Die Reihenfolge dieser Operationen ist wichtig und hängt von der Logik Ihrer originalen LBS ab.
        # Typischerweise wird der Offset addiert und dann ein Minimum angewendet.
        calculated_degrees += angle_offset
        calculated_degrees = max(min_slat_angle, calculated_degrees)

        _LOGGER.debug(
            f"{self._name}: Angle of {angle_percent}% equates to {calculated_degrees}° (min_slat_angle={min_slat_angle}, angle_offset={angle_offset})")

        return calculated_degrees

    def _should_output_be_updated(self, config_value: MovementRestricted, new_value: float,
                                  previous_value: float | None) -> float:
        """
        Abhängig vom übergebenen Konfigurationswert, gibt den vorherigen oder den neuen Wert zurück.
        Neuer Wert wird zurückgegeben, wenn:
        - config_value ist 'ONLY_DOWN' und neuer Wert ist größer als vorheriger Wert oder
        - config_value ist 'ONLY_UP' und neuer Wert ist kleiner als vorheriger Ausgabewert oder
        - config_value ist 'NO_RESTRICTION' oder etwas anderes.
        Alle anderen Fälle geben den vorherigen Wert zurück.

        Entspricht der PHP-Funktion LB_LBSID_shouldOutputBeUpdated.
        """
        # Annahme: LB_LBSID_INTERNAL__doUpdatePositionOutputs ist in Python über
        # die Zustandsmaschine und die _current_lock_state Logik abgedeckt.
        # Hier geht es nur um die reine Bewegungsbeschränkung.

        # Falls previous_value noch None ist (z.B. beim Initiallauf),
        # sollte der new_value immer zurückgegeben werden, da es noch keinen "previous" gibt.
        if previous_value is None:
            # _LOGGER.debug(
            #     f"{self._name}: _should_output_be_updated: previous_value is None. Returning new value ({new_value})")
            return new_value

        # Überprüfen Sie, ob sich der Wert überhaupt geändert hat,
        # bevor Sie die komplexere Logik anwenden.
        # Eine kleine Toleranz kann hier sinnvoll sein, um unnötige Bewegungen zu vermeiden.
        # Home Assistant filtert oft schon, aber eine explizite Prüfung ist gut.
        if abs(new_value - previous_value) < 0.001:  # Kleine Toleranz für Floating Point Vergleiche
            # _LOGGER.debug(
            #     f"{self._name}: _should_output_be_updated: new_value ({new_value}) is nearly identical to previous_value ({previous_value}). Returning previous_value")
            return previous_value

        # _LOGGER.debug(
        #     f"{self._name}: _should_output_be_updated: config_value={config_value.name}, new_value={new_value}, previous_value={previous_value}")

        if config_value == MovementRestricted.ONLY_CLOSE:
            if new_value > previous_value:
                # _LOGGER.debug(
                #     f"{self._name}: _should_output_be_updated: ONLY_DOWN -> new_value ({new_value}) > previous_value ({previous_value}). Returning new_value")
                return new_value
            else:
                # _LOGGER.debug(
                #     f"{self._name}: _should_output_be_updated: ONLY_DOWN -> new_value ({new_value}) <= previous_value ({previous_value}). Returning previous_value")
                return previous_value
        elif config_value == MovementRestricted.ONLY_OPEN:
            if new_value < previous_value:
                # _LOGGER.debug(
                #     f"{self._name}: _should_output_be_updated: ONLY_UP -> new_value ({new_value}) < previous_value ({previous_value}). Returning new_value")
                return new_value
            else:
                # _LOGGER.debug(
                #     f"{self._name}: _should_output_be_updated: ONLY_UP -> new_value ({new_value}) >= previous_value ({previous_value}). Returning previous_value")
                return previous_value
        elif config_value == MovementRestricted.NO_RESTRICTION:
            # _LOGGER.debug(
            #     f"{self._name}: _should_output_be_updated: NO_RESTRICTION -> Returning new_value ({new_value})")
            return new_value
        else:
            # Für alle anderen (unbekannten) config_values, geben wir den previous_value zurück
            # oder den new_value, je nachdem, wie Sie die "default" in PHP interpretieren.
            # Die PHP "default" ist "return $newValue;", also lassen wir das auch hier so.
            # _LOGGER.warning(
            #     f"{self._name}: _should_output_be_updated: Unknown value '{config_value.name}'. Returning new_value ({new_value})")
            return new_value

    async def _start_recalculation_timer(self, delay_seconds: float) -> None:
        """
        Startet einen Timer, der nach 'delay_seconds' eine Neuberechnung auslöst.
        Bestehende Timer werden vorher abgebrochen.
        """
        self._cancel_recalculation_timer()  # Immer erst den alten Timer abbrechen

        if delay_seconds <= 0:
            _LOGGER.debug(
                f"{self._name}: Timer delay is <= 0 ({delay_seconds}s). Trigger immediate recalculation")
            await self._async_calculate_and_apply_cover_position(None)
            # Wenn sofortige Neuberechnung, gibt es keinen zukünftigen Timer.
            self._next_modification_timestamp = None
            return

        _LOGGER.debug(f"{self._name}: Starting recalculation timer for {delay_seconds}s")

        # Save start time and duration
        current_utc_time = datetime.now(timezone.utc)
        self._recalculation_timer_start_time = datetime.now(timezone.utc)
        self._recalculation_timer_duration_seconds = delay_seconds

        self._next_modification_timestamp = current_utc_time + timedelta(seconds=delay_seconds)
        _LOGGER.debug(f"{self._name}: Next modification scheduled for: {self._next_modification_timestamp}")

        # Save callback handle from async_call_later to enable timer canceling
        self._recalculation_timer = async_call_later(
            self.hass,
            delay_seconds,
            self._async_timer_callback
        )

        self._update_extra_state_attributes()

    def _cancel_recalculation_timer(self) -> None:
        """Bricht einen laufenden Neuberechnungs-Timer ab."""
        if self._recalculation_timer:
            _LOGGER.debug(f"{self._name}: Canceling recalculation timer")
            self._recalculation_timer()  # Aufruf des Handles bricht den Timer ab
            self._recalculation_timer = None

        # Reset timer tracking variables
        self._recalculation_timer_start_time = None
        self._recalculation_timer_duration_seconds = None
        self._next_modification_timestamp = None

    async def _async_timer_callback(self, now) -> None:
        """
        Dieser Callback wird vom Home Assistant Scheduler aufgerufen, wenn der Timer abläuft.
        'now' ist das aktuelle Zeitpunkt-Objekt, das von async_call_later übergeben wird.
        """
        _LOGGER.debug(f"{self._name}: Recalculation timer finished, triggering recalculation")
        # Variablen zurücksetzen, da der Timer abgelaufen ist
        self._recalculation_timer = None
        self._recalculation_timer_start_time = None
        self._recalculation_timer_duration_seconds = None
        await self._async_calculate_and_apply_cover_position(None)

    def get_remaining_timer_seconds(self) -> float | None:
        """
        Gibt die verbleibende Zeit des Timers in Sekunden zurück, oder None, wenn kein Timer läuft.
        """
        if self._recalculation_timer and self._recalculation_timer_start_time and self._recalculation_timer_duration_seconds is not None:
            elapsed_time = (datetime.now(timezone.utc) - self._recalculation_timer_start_time).total_seconds()
            remaining_time = self._recalculation_timer_duration_seconds - elapsed_time
            return max(0.0, remaining_time) # Stelle sicher, dass es nicht negativ ist
        return None

    def _is_timer_finished(self) -> bool:
        """
        Prüft, ob ein Neuberechnungs-Timer aktiv ist.
        """
        return self._recalculation_timer is None
