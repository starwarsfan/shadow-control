"""Integration for Shadow Control."""
import datetime
import logging
import math

import voluptuous as vol
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Callable, Awaitable

from homeassistant.core import HomeAssistant, callback, Event, State
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_change
from homeassistant.const import (
    ATTR_SUPPORTED_FEATURES,
    STATE_ON, STATE_OFF,
    EVENT_HOMEASSISTANT_STARTED
)
from homeassistant.components.cover import CoverEntityFeature

from .const import SCDynamicInput, SCConfigurationInput, SCShadowInput, SCDawnInput, \
    MovementRestricted, LockState, ShutterState

_LOGGER = logging.getLogger(__name__)

DOMAIN = "shadow_control"
SINGLE_COVER_CONFIG_SCHEMA = vol.Schema({
    vol.Required("name"): str, # Freundlicher Name für dieses spezifische Cover
    vol.Required("target_cover_entity_id"): str,

    # === Dynamische Eingänge (Mapped directly to your existing input_number/input_boolean entities) ===
    vol.Required(SCDynamicInput.CONF_BRIGHTNESS_ENTITY_ID.value): str,
    vol.Required(SCDynamicInput.CONF_BRIGHTNESS_DAWN_ENTITY_ID.value): str,
    vol.Required(SCDynamicInput.CONF_SUN_ELEVATION_ENTITY_ID.value): str,
    vol.Required(SCDynamicInput.CONF_SUN_AZIMUTH_ENTITY_ID.value): str,
    # HINWEIS: shutter_current_height/angle würde man normalerweise direkt vom Cover bekommen.
    # Hier bleiben sie als input_number für Ihre Testzwecke.
    vol.Required(SCDynamicInput.CONF_SHUTTER_CURRENT_HEIGHT_ENTITY_ID.value): str,
    vol.Required(SCDynamicInput.CONF_SHUTTER_CURRENT_ANGLE_ENTITY_ID.value): str,
    vol.Required(SCDynamicInput.CONF_LOCK_INTEGRATION_ENTITY_ID.value): str,
    vol.Required(SCDynamicInput.CONF_LOCK_INTEGRATION_WITH_POSITION_ENTITY_ID.value): str,
    vol.Required(SCDynamicInput.CONF_LOCK_HEIGHT_ENTITY_ID.value): str,
    vol.Required(SCDynamicInput.CONF_LOCK_ANGLE_ENTITY_ID.value): str,
    vol.Required(SCDynamicInput.CONF_MODIFICATION_TOLERANCE_HEIGHT_ENTITY_ID.value): str,
    vol.Required(SCDynamicInput.CONF_MODIFICATION_TOLERANCE_ANGLE_ENTITY_ID.value): str,

    # === Allgemeine Einstellungen (Mapped to your existing input_number/input_select entities) ===
    vol.Required(SCConfigurationInput.CONF_FACADE_AZIMUTH_ENTITY_ID.value): str,
    vol.Required(SCConfigurationInput.CONF_FACADE_OFFSET_SUN_IN_ENTITY_ID.value): str,
    vol.Required(SCConfigurationInput.CONF_FACADE_OFFSET_SUN_OUT_ENTITY_ID.value): str,
    vol.Required(SCConfigurationInput.CONF_FACADE_ELEVATION_SUN_MIN_ENTITY_ID.value): str,
    vol.Required(SCConfigurationInput.CONF_FACADE_ELEVATION_SUN_MAX_ENTITY_ID.value): str,
    vol.Required(SCConfigurationInput.CONF_FACADE_SLAT_WIDTH_ENTITY_ID.value): str,
    vol.Required(SCConfigurationInput.CONF_FACADE_SLAT_DISTANCE_ENTITY_ID.value): str,
    vol.Required(SCConfigurationInput.CONF_FACADE_SLAT_ANGLE_OFFSET_ENTITY_ID.value): str,
    vol.Required(SCConfigurationInput.CONF_FACADE_SLAT_MIN_ANGLE_ENTITY_ID.value): str,
    vol.Required(SCConfigurationInput.CONF_FACADE_SHUTTER_STEPPING_HEIGHT_ENTITY_ID.value): str,
    vol.Required(SCConfigurationInput.CONF_FACADE_SHUTTER_STEPPING_ANGLE_ENTITY_ID.value): str,
    vol.Required(SCConfigurationInput.CONF_FACADE_SHUTTER_TYPE_ENTITY_ID.value): str, # input_select
    vol.Required(SCConfigurationInput.CONF_FACADE_LIGHT_STRIP_WIDTH_ENTITY_ID.value): str,
    vol.Required(SCConfigurationInput.CONF_FACADE_SHUTTER_HEIGHT_ENTITY_ID.value): str,
    vol.Required(SCConfigurationInput.CONF_FACADE_NEUTRAL_POS_HEIGHT_ENTITY_ID.value): str,
    vol.Required(SCConfigurationInput.CONF_FACADE_NEUTRAL_POS_ANGLE_ENTITY_ID.value): str,
    vol.Required(SCConfigurationInput.CONF_FACADE_MOVEMENT_RESTRICTION_HEIGHT_ENTITY_ID.value): str, # input_select
    vol.Required(SCConfigurationInput.CONF_FACADE_MOVEMENT_RESTRICTION_ANGLE_ENTITY_ID.value): str, # input_select
    vol.Required(SCConfigurationInput.CONF_FACADE_UPDATE_LOCK_OUTPUT_ENTITY_ID.value): str, # input_select

    # === Beschattungseinstellungen ===
    vol.Required(SCShadowInput.CONF_SHADOW_CONTROL_ENABLED_ENTITY_ID.value): str, # input boolean
    vol.Required(SCShadowInput.CONF_SHADOW_BRIGHTNESS_THRESHOLD_ENTITY_ID.value): str,
    vol.Required(SCShadowInput.CONF_SHADOW_AFTER_SECONDS_ENTITY_ID.value): str,
    vol.Required(SCShadowInput.CONF_SHADOW_SHUTTER_MAX_HEIGHT_ENTITY_ID.value): str,
    vol.Required(SCShadowInput.CONF_SHADOW_SHUTTER_MAX_ANGLE_ENTITY_ID.value): str,
    vol.Required(SCShadowInput.CONF_SHADOW_SHUTTER_LOOK_THROUGH_SECONDS_ENTITY_ID.value): str,
    vol.Required(SCShadowInput.CONF_SHADOW_SHUTTER_LOOK_THROUGH_ANGLE_ENTITY_ID.value): str,
    vol.Required(SCShadowInput.CONF_SHADOW_SHUTTER_OPEN_SECONDS_ENTITY_ID.value): str,
    vol.Required(SCShadowInput.CONF_SHADOW_HEIGHT_AFTER_SUN_ENTITY_ID.value): str,
    vol.Required(SCShadowInput.CONF_SHADOW_ANGLE_AFTER_SUN_ENTITY_ID.value): str,

    # === Dämmerungseinstellungen ===
    vol.Required(SCDawnInput.CONF_DAWN_CONTROL_ENABLED_ENTITY_ID.value): str, # input boolean
    vol.Required(SCDawnInput.CONF_DAWN_BRIGHTNESS_THRESHOLD_ENTITY_ID.value): str,
    vol.Required(SCDawnInput.CONF_DAWN_AFTER_SECONDS_ENTITY_ID.value): str,
    vol.Required(SCDawnInput.CONF_DAWN_SHUTTER_MAX_HEIGHT_ENTITY_ID.value): str,
    vol.Required(SCDawnInput.CONF_DAWN_SHUTTER_MAX_ANGLE_ENTITY_ID.value): str,
    vol.Required(SCDawnInput.CONF_DAWN_SHUTTER_LOOK_THROUGH_SECONDS_ENTITY_ID.value): str,
    vol.Required(SCDawnInput.CONF_DAWN_SHUTTER_LOOK_THROUGH_ANGLE_ENTITY_ID.value): str,
    vol.Required(SCDawnInput.CONF_DAWN_SHUTTER_OPEN_SECONDS_ENTITY_ID.value): str,
    vol.Required(SCDawnInput.CONF_DAWN_HEIGHT_AFTER_DAWN_ENTITY_ID.value): str,
    vol.Required(SCDawnInput.CONF_DAWN_ANGLE_AFTER_DAWN_ENTITY_ID.value): str,
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

    # Holen Sie sich die Konfiguration für Shadow Control
    conf = config[DOMAIN]

    # Die 'covers' Liste aus der Konfiguration
    covers_config = conf["covers"]

    hass.data.setdefault(DOMAIN, {}) # Initialisiert den Datenbereich für die Integration

    # Für jedes konfigurierte Cover einen eigenen Manager erstellen
    # Das ist der Schlüssel für die Skalierbarkeit und Trennung der Logik pro Cover
    for cover_conf in covers_config:
        cover_name = cover_conf["name"]
        _LOGGER.debug(f"[{DOMAIN}] Setting up manager for cover: {cover_name}")

        manager = ShadowControlManager(
            hass,
            cover_conf # Übergeben Sie die gesamte Konfiguration dieses Covers an den Manager
        )

        # Speichern Sie den Manager unter dem Namen des Covers (oder der target_cover_entity_id)
        # So können Sie später darauf zugreifen, falls nötig
        hass.data[DOMAIN][cover_name] = manager

        # Registriere Listener für alle relevanten Entitäten DIESES Covers
        manager.register_listeners()

    # WICHTIG: Listener für EVENT_HOMEASSISTANT_STARTED NACHDEM alle Manager initialisiert sind
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _async_hass_started_all_managers)

    _LOGGER.info(f"[{DOMAIN}] Integration 'Shadow Control' successfully set up. Configured {len(covers_config)} covers.")
    return True

# Callback, der alle Manager nach dem HA-Start benachrichtigt
async def _async_hass_started_all_managers(event: Event) -> None:
    """Call async_hass_started on all configured managers."""
    hass = event.hass # Greifen Sie auf die HomeAssistant-Instanz zu
    _LOGGER.debug(f"[{DOMAIN}] EVENT_HOMEASSISTANT_STARTED received. Notifying all managers.")
    for manager_name, manager_instance in hass.data[DOMAIN].items():
        if isinstance(manager_instance, ShadowControlManager): # Sicherstellen, dass es ein Manager ist
            await manager_instance.async_hass_started(event)
        else:
            _LOGGER.warning(f"[{DOMAIN}] Found unexpected item in hass.data[{DOMAIN}]: {manager_name}")

class ShadowControlManager:
    """Manages the Shadow Control logic for a single cover."""

    def __init__(
            self,
            hass: HomeAssistant,
            config: Dict[str, Any], # Jetzt bekommt der Manager die komplette Konfig für SEIN Cover
    ) -> None:
        self.hass = hass
        self._config = config
        self._name = config["name"] # Freundlicher Name
        self._target_cover_entity_id = config["target_cover_entity_id"]

        # === Dynamische Eingänge (Test-Helfer) ===
        self._brightness_entity_id = config.get(SCDynamicInput.CONF_BRIGHTNESS_ENTITY_ID.value)
        self._brightness_dawn_entity_id = config.get(SCDynamicInput.CONF_BRIGHTNESS_DAWN_ENTITY_ID.value)
        self._sun_elevation_entity_id = config.get(SCDynamicInput.CONF_SUN_ELEVATION_ENTITY_ID.value)
        self._sun_azimuth_entity_id = config.get(SCDynamicInput.CONF_SUN_AZIMUTH_ENTITY_ID.value)
        self._shutter_current_height_entity_id = config.get(SCDynamicInput.CONF_SHUTTER_CURRENT_HEIGHT_ENTITY_ID.value)
        self._shutter_current_angle_entity_id = config.get(SCDynamicInput.CONF_SHUTTER_CURRENT_ANGLE_ENTITY_ID.value)
        self._lock_integration_entity_id = config.get(SCDynamicInput.CONF_LOCK_INTEGRATION_ENTITY_ID.value)
        self._lock_integration_with_position_entity_id = config.get(SCDynamicInput.CONF_LOCK_INTEGRATION_WITH_POSITION_ENTITY_ID.value)
        self._lock_height_entity_id = config.get(SCDynamicInput.CONF_LOCK_HEIGHT_ENTITY_ID.value)
        self._lock_angle_entity_id = config.get(SCDynamicInput.CONF_LOCK_ANGLE_ENTITY_ID.value)
        self._modification_tolerance_height_entity_id = config.get(SCDynamicInput.CONF_MODIFICATION_TOLERANCE_HEIGHT_ENTITY_ID.value)
        self._modification_tolerance_angle_entity_id = config.get(SCDynamicInput.CONF_MODIFICATION_TOLERANCE_ANGLE_ENTITY_ID.value)

        # === Allgemeine Einstellungen (Test-Helfer) ===
        self._facade_azimuth_entity_id = config.get(SCConfigurationInput.CONF_FACADE_AZIMUTH_ENTITY_ID.value)
        self._facade_offset_sun_in_entity_id = config.get(SCConfigurationInput.CONF_FACADE_OFFSET_SUN_IN_ENTITY_ID.value)
        self._facade_offset_sun_out_entity_id = config.get(SCConfigurationInput.CONF_FACADE_OFFSET_SUN_OUT_ENTITY_ID.value)
        self._facade_elevation_sun_min_entity_id = config.get(SCConfigurationInput.CONF_FACADE_ELEVATION_SUN_MIN_ENTITY_ID.value)
        self._facade_elevation_sun_max_entity_id = config.get(SCConfigurationInput.CONF_FACADE_ELEVATION_SUN_MAX_ENTITY_ID.value)
        self._facade_slat_width_entity_id = config.get(SCConfigurationInput.CONF_FACADE_SLAT_WIDTH_ENTITY_ID.value)
        self._facade_slat_distance_entity_id = config.get(SCConfigurationInput.CONF_FACADE_SLAT_DISTANCE_ENTITY_ID.value)
        self._facade_slat_angle_offset_entity_id = config.get(SCConfigurationInput.CONF_FACADE_SLAT_ANGLE_OFFSET_ENTITY_ID.value)
        self._facade_slat_min_angle_entity_id = config.get(SCConfigurationInput.CONF_FACADE_SLAT_MIN_ANGLE_ENTITY_ID.value)
        self._facade_shutter_stepping_height_entity_id = config.get(SCConfigurationInput.CONF_FACADE_SHUTTER_STEPPING_HEIGHT_ENTITY_ID.value)
        self._facade_shutter_stepping_angle_entity_id = config.get(SCConfigurationInput.CONF_FACADE_SHUTTER_STEPPING_ANGLE_ENTITY_ID.value)
        self._facade_shutter_type_entity_id = config.get(SCConfigurationInput.CONF_FACADE_SHUTTER_TYPE_ENTITY_ID.value)
        self._facade_light_strip_width_entity_id = config.get(SCConfigurationInput.CONF_FACADE_LIGHT_STRIP_WIDTH_ENTITY_ID.value)
        self._facade_shutter_height_entity_id = config.get(SCConfigurationInput.CONF_FACADE_SHUTTER_HEIGHT_ENTITY_ID.value)
        self._facade_neutral_pos_height_entity_id = config.get(SCConfigurationInput.CONF_FACADE_NEUTRAL_POS_HEIGHT_ENTITY_ID.value)
        self._facade_neutral_pos_angle_entity_id = config.get(SCConfigurationInput.CONF_FACADE_NEUTRAL_POS_ANGLE_ENTITY_ID.value)
        self._facade_movement_restriction_height_entity_id = config.get(SCConfigurationInput.CONF_FACADE_MOVEMENT_RESTRICTION_HEIGHT_ENTITY_ID.value)
        self._facade_movement_restriction_angle_entity_id = config.get(SCConfigurationInput.CONF_FACADE_MOVEMENT_RESTRICTION_ANGLE_ENTITY_ID.value)
        self._facade_update_lock_output_entity_id = config.get(SCConfigurationInput.CONF_FACADE_UPDATE_LOCK_OUTPUT_ENTITY_ID.value)

        # === Beschattungseinstellungen (Test-Helfer) ===
        self._shadow_control_enabled_entity_id = config.get(SCShadowInput.CONF_SHADOW_CONTROL_ENABLED_ENTITY_ID.value)
        self._shadow_brightness_threshold_entity_id = config.get(SCShadowInput.CONF_SHADOW_BRIGHTNESS_THRESHOLD_ENTITY_ID.value)
        self._shadow_after_seconds_entity_id = config.get(SCShadowInput.CONF_SHADOW_AFTER_SECONDS_ENTITY_ID.value)
        self._shadow_shutter_max_height_entity_id = config.get(SCShadowInput.CONF_SHADOW_SHUTTER_MAX_HEIGHT_ENTITY_ID.value)
        self._shadow_shutter_max_angle_entity_id = config.get(SCShadowInput.CONF_SHADOW_SHUTTER_MAX_ANGLE_ENTITY_ID.value)
        self._shadow_shutter_look_through_seconds_entity_id = config.get(SCShadowInput.CONF_SHADOW_SHUTTER_LOOK_THROUGH_SECONDS_ENTITY_ID.value)
        self._shadow_shutter_open_seconds_entity_id = config.get(SCShadowInput.CONF_SHADOW_SHUTTER_OPEN_SECONDS_ENTITY_ID.value)
        self._shadow_shutter_look_through_angle_entity_id = config.get(SCShadowInput.CONF_SHADOW_SHUTTER_LOOK_THROUGH_ANGLE_ENTITY_ID.value)
        self._shadow_height_after_sun_entity_id = config.get(SCShadowInput.CONF_SHADOW_HEIGHT_AFTER_SUN_ENTITY_ID.value)
        self._shadow_angle_after_sun_entity_id = config.get(SCShadowInput.CONF_SHADOW_ANGLE_AFTER_SUN_ENTITY_ID.value)

        # === Dämmerungseinstellungen (Test-Helfer) ===
        self._dawn_control_enabled_entity_id = config.get(SCDawnInput.CONF_DAWN_CONTROL_ENABLED_ENTITY_ID.value)
        self._dawn_brightness_threshold_entity_id = config.get(SCDawnInput.CONF_DAWN_BRIGHTNESS_THRESHOLD_ENTITY_ID.value)
        self._dawn_after_seconds_entity_id = config.get(SCDawnInput.CONF_DAWN_AFTER_SECONDS_ENTITY_ID.value)
        self._dawn_shutter_max_height_entity_id = config.get(SCDawnInput.CONF_DAWN_SHUTTER_MAX_HEIGHT_ENTITY_ID.value)
        self._dawn_shutter_max_angle_entity_id = config.get(SCDawnInput.CONF_DAWN_SHUTTER_MAX_ANGLE_ENTITY_ID.value)
        self._dawn_shutter_look_through_seconds_entity_id = config.get(SCDawnInput.CONF_DAWN_SHUTTER_LOOK_THROUGH_SECONDS_ENTITY_ID.value)
        self._dawn_shutter_open_seconds_entity_id = config.get(SCDawnInput.CONF_DAWN_SHUTTER_OPEN_SECONDS_ENTITY_ID.value)
        self._dawn_shutter_look_through_angle_entity_id = config.get(SCDawnInput.CONF_DAWN_SHUTTER_LOOK_THROUGH_ANGLE_ENTITY_ID.value)
        self._dawn_height_after_dawn_entity_id = config.get(SCDawnInput.CONF_DAWN_HEIGHT_AFTER_DAWN_ENTITY_ID.value)
        self._dawn_angle_after_dawn_entity_id = config.get(SCDawnInput.CONF_DAWN_ANGLE_AFTER_DAWN_ENTITY_ID.value)

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

        self._listeners = []
        self._auto_mode_active = False # Initialer Zustand

        _LOGGER.debug(f"[{DOMAIN}] Manager for '{self._name}' initialized for target: {self._target_cover_entity_id}.")

    def register_listeners(self) -> None:
        """Register listeners for relevant state changes for this specific cover."""
        _LOGGER.debug(f"[{DOMAIN}] Registering listeners for '{self._name}'.")

        # Liste aller Entitäten, auf deren Änderungen dieser Manager reagieren soll
        # Dies sind die Entitäten aus Ihrer config, deren Zustand die Logik beeinflusst
        relevant_entity_ids = [
            self._brightness_entity_id,
            self._brightness_dawn_entity_id,
            self._sun_elevation_entity_id,
            self._sun_azimuth_entity_id,
            self._lock_integration_entity_id,
            self._lock_integration_with_position_entity_id,
            self._shadow_control_enabled_entity_id,
            self._dawn_control_enabled_entity_id
        ]

        # Filtern Sie None-Werte heraus (falls ein optionaler Parameter nicht gesetzt ist,
        # oder wenn Sie versehentlich einen Platzhalter eingefügt haben, der None ist)
        unique_relevant_entity_ids = list(set(eid for eid in relevant_entity_ids if eid))

        self._listeners.append(
            async_track_state_change_event(
                self.hass,
                unique_relevant_entity_ids,
                self._async_handle_input_change, # EINE zentrale Methode für alle Änderungen
            )
        )

        # Optional: Wenn Sie eine zeitbasierte Aktualisierung für jedes Cover möchten
        # self._listeners.append(
        #     async_track_time_change(self.hass, self._async_handle_input_change,
        #                             minute=None, second=0)
        # )

        _LOGGER.debug(f"[{DOMAIN}] All relevant state listeners registered for '{self._name}'.")


    async def async_hass_started(self, event: Event) -> None:
        """Handle Home Assistant start event for this specific manager."""
        _LOGGER.info(f"[{DOMAIN}] Home Assistant has started. Initializing Shadow Control for '{self._name}'.")
        # Hier können Sie den initialen Zustand abrufen und die erste Berechnung ausführen
        # Auto-Modus-Status aktualisieren
        auto_mode_state = self.hass.states.get(self._shadow_control_enabled_entity_id)
        self._auto_mode_active = (auto_mode_state and auto_mode_state.state == STATE_ON)
        _LOGGER.debug(f"[{DOMAIN}] Initial auto mode for '{self._name}': {self._auto_mode_active}")

        # Initialberechnung beim Start
        await self._async_calculate_and_apply_cover_position(None)

    def _update_input_values(self) -> None:
        """
        Aktualisiert alle relevanten Eingangs- und Konfigurationswerte
        aus Home Assistant und speichert sie in Instanzvariablen.
        """
        _LOGGER.debug(f"{self._name}: Updating all input values")

        # === Dynamische Eingänge (Sensor-Werte) ===
        self._brightness = self._get_entity_numeric_state(self._brightness_entity_id, float)
        self._brightness_dawn = self._get_entity_numeric_state(self._brightness_dawn_entity_id, float)
        self._sun_elevation = self._get_entity_numeric_state(self._sun_elevation_entity_id, float)
        self._sun_azimuth = self._get_entity_numeric_state(self._sun_azimuth_entity_id, float)
        self._shutter_current_height = self._get_entity_numeric_state(self._shutter_current_height_entity_id, float)
        self._shutter_current_angle = self._get_entity_numeric_state(self._shutter_current_angle_entity_id, float)
        self._lock_integration = self._get_entity_boolean_state(self._lock_integration_entity_id)
        self._lock_integration_with_position = self._get_entity_boolean_state(self._lock_integration_with_position_entity_id)
        self._lock_height = self._get_entity_numeric_state(self._lock_height_entity_id, float)
        self._lock_angle = self._get_entity_numeric_state(self._lock_angle_entity_id, float)
        self._modification_tolerance_height = self._get_entity_numeric_state(self._modification_tolerance_height_entity_id, float)
        self._modification_tolerance_angle = self._get_entity_numeric_state(self._modification_tolerance_angle_entity_id, float)

        # === Allgemeine Einstellungen ===
        self._azimuth_facade = self._get_entity_numeric_state(self._facade_azimuth_entity_id, float)
        self._offset_sun_in = self._get_entity_numeric_state(self._facade_offset_sun_in_entity_id, float)
        self._offset_sun_out = self._get_entity_numeric_state(self._facade_offset_sun_out_entity_id, float)
        self._elevation_sun_min = self._get_entity_numeric_state(self._facade_elevation_sun_min_entity_id, float)
        self._elevation_sun_max = self._get_entity_numeric_state(self._facade_elevation_sun_max_entity_id, float)
        self._slat_width = self._get_entity_numeric_state(self._facade_slat_width_entity_id, float)
        self._slat_distance = self._get_entity_numeric_state(self._facade_slat_distance_entity_id, float)
        self._angle_offset = self._get_entity_numeric_state(self._facade_slat_angle_offset_entity_id, float)
        self._min_slat_angle = self._get_entity_numeric_state(self._facade_slat_min_angle_entity_id, float)
        self._stepping_height = self._get_entity_numeric_state(self._facade_shutter_stepping_height_entity_id, float)
        self._stepping_angle = self._get_entity_numeric_state(self._facade_shutter_stepping_angle_entity_id, float)
        self._shutter_type = self._get_entity_string_state(self._facade_shutter_type_entity_id)
        self._light_bar_width = self._get_entity_numeric_state(self._facade_light_strip_width_entity_id, float)
        self._shutter_height = self._get_entity_numeric_state(self._facade_shutter_height_entity_id, float)
        self._neutral_pos_height = self._get_entity_numeric_state(self._facade_neutral_pos_height_entity_id, float)
        self._neutral_pos_angle = self._get_entity_numeric_state(self._facade_neutral_pos_angle_entity_id, float)

        # -------------------------------------------
        # Movement restriction to enumeration mapping
        #self._movement_restriction_height = self._get_entity_string_state(self._facade_movement_restriction_height_entity_id)
        height_restriction_entity_id = self._config.get(SCConfigurationInput.CONF_FACADE_MOVEMENT_RESTRICTION_HEIGHT_ENTITY_ID.value)
        if height_restriction_entity_id:
            state_obj = self.hass.states.get(height_restriction_entity_id)
            if state_obj and state_obj.state:
                # Suchen Sie den Enum-Member, dessen Wert (value) dem input_select String entspricht
                for restriction_type in MovementRestricted:
                    if restriction_type.value == state_obj.state:
                        self._movement_restriction_height = restriction_type
                        _LOGGER.debug(f"{self._name}: Movement restriction for height set ({self._movement_restriction_height.name}, value: {state_obj.state})")
                        break
                else: # Wenn die Schleife ohne break beendet wird (Wert nicht gefunden)
                    _LOGGER.warning(f"{self._name}: Unknown option for {height_restriction_entity_id}: '{state_obj.state}'. Using NO_RESTRICTION.")
                    self._movement_restriction_height = MovementRestricted.NO_RESTRICTION
            else:
                _LOGGER.warning(f"{self._name}: Value of {height_restriction_entity_id} not available or empty. Using NO_RESTRICTION.")
                self._movement_restriction_height = MovementRestricted.NO_RESTRICTION
        else:
            _LOGGER.warning(f"{self._name}: Configuration of '{SCConfigurationInput.CONF_FACADE_MOVEMENT_RESTRICTION_HEIGHT_ENTITY_ID.value}' missing. Using NO_RESTRICTION.")
            self._movement_restriction_height = MovementRestricted.NO_RESTRICTION
        #self._movement_restriction_angle = self._get_entity_string_state(self._facade_movement_restriction_angle_entity_id)
        angle_restriction_entity_id = self._config.get(SCConfigurationInput.CONF_FACADE_MOVEMENT_RESTRICTION_ANGLE_ENTITY_ID.value)
        if angle_restriction_entity_id:
            state_obj = self.hass.states.get(angle_restriction_entity_id)
            if state_obj and state_obj.state:
                for restriction_type in MovementRestricted:
                    if restriction_type.value == state_obj.state:
                        self._movement_restriction_angle = restriction_type
                        _LOGGER.debug(f"{self._name}: Movement restriction for angle set {self._movement_restriction_angle.name}, value: {state_obj.state})")
                        break
                else:
                    _LOGGER.warning(f"{self._name}: Unknown option for {angle_restriction_entity_id}: '{state_obj.state}'. Using NO_RESTRICTION.")
                    self._movement_restriction_angle = MovementRestricted.NO_RESTRICTION
            else:
                _LOGGER.warning(f"{self._name}: Value of {angle_restriction_entity_id} not available or empty. Using NO_RESTRICTION.")
                self._movement_restriction_angle = MovementRestricted.NO_RESTRICTION
        else:
            _LOGGER.warning(f"{self._name}: Configuration of '{SCConfigurationInput.CONF_FACADE_MOVEMENT_RESTRICTION_ANGLE_ENTITY_ID.value}' missing. Using NO_RESTRICTION.")
            self._movement_restriction_angle = MovementRestricted.NO_RESTRICTION

        self._update_lock_output = self._get_entity_string_state(self._facade_update_lock_output_entity_id)

        # === Beschattungseinstellungen ===
        self._shadow_control_enabled = self._get_entity_boolean_state(self._shadow_control_enabled_entity_id)
        self._shadow_brightness_level = self._get_entity_numeric_state(self._shadow_brightness_threshold_entity_id, float)
        self._shadow_after_seconds = self._get_entity_numeric_state(self._shadow_after_seconds_entity_id, float)
        self._shadow_max_height = self._get_entity_numeric_state(self._shadow_shutter_max_height_entity_id, float)
        self._shadow_max_angle = self._get_entity_numeric_state(self._shadow_shutter_max_angle_entity_id, float)
        self._shadow_look_through_seconds = self._get_entity_numeric_state(self._shadow_shutter_look_through_seconds_entity_id, float)
        self._shadow_open_seconds = self._get_entity_numeric_state(self._shadow_shutter_open_seconds_entity_id, float)
        self._shadow_look_through_angle = self._get_entity_numeric_state(self._shadow_shutter_look_through_angle_entity_id, float)
        self._after_shadow_height = self._get_entity_numeric_state(self._shadow_height_after_sun_entity_id, float)
        self._after_shadow_angle = self._get_entity_numeric_state(self._shadow_angle_after_sun_entity_id, float)

        # === Dämmerungseinstellungen ===
        self._dawn_control_enabled = self._get_entity_boolean_state(self._dawn_control_enabled_entity_id)
        self._dawn_brightness_level = self._get_entity_numeric_state(self._dawn_brightness_threshold_entity_id, float)
        self._dawn_after_seconds = self._get_entity_numeric_state(self._dawn_after_seconds_entity_id, float)
        self._dawn_max_height = self._get_entity_numeric_state(self._dawn_shutter_max_height_entity_id, float)
        self._dawn_max_angle = self._get_entity_numeric_state(self._dawn_shutter_max_angle_entity_id, float)
        self._dawn_look_through_seconds = self._get_entity_numeric_state(self._dawn_shutter_look_through_seconds_entity_id, float)
        self._dawn_open_seconds = self._get_entity_numeric_state(self._dawn_shutter_open_seconds_entity_id, float)
        self._dawn_look_through_angle = self._get_entity_numeric_state(self._dawn_shutter_look_through_angle_entity_id, float)
        self._after_dawn_height = self._get_entity_numeric_state(self._dawn_height_after_dawn_entity_id, float)
        self._after_dawn_angle = self._get_entity_numeric_state(self._dawn_angle_after_dawn_entity_id, float)

        _LOGGER.debug(
            f"{self._name}: Updated values (part of): "
            f"Brightness={self._brightness}, "
            f"Elevation={self._sun_elevation}, "
            f"ShadowEnabled={self._shadow_control_enabled}"
        )

        # === Priorisierung des internen LockState ===
        # Wenn CONF_LOCK_INTEGRATION_WITH_POSITION_ENTITY_ID (höchste Priorität) "on" ist
        if self._lock_integration_with_position:
            self._current_lock_state = LockState.LOCKED_MANUALLY_WITH_FORCED_POSITION
            _LOGGER.debug(f"{self._name}: LockState set to LOCKSTATE__LOCKED_MANUALLY_WITH_FORCED_POSITION due to '{self._lock_integration_with_position_entity_id}' being ON.")
        # Wenn CONF_LOCK_INTEGRATION_ENTITY_ID "on" ist (und die höhere Priorität nicht greift)
        elif self._lock_integration:
            self._current_lock_state = LockState.LOCKED_MANUALLY
            _LOGGER.debug(f"{self._name}: LockState set to LOCKSTATE__LOCKED_MANUALLY due to '{self._lock_integration_entity_id}' being ON.")
        # Ansonsten bleibt es UNLOCKED (oder ein anderer Standardwert, den Sie festgelegt haben)

        # Optional: Weitere LockStates wie LOCKSTATE__LOCKED_BY_EXTERNAL_MODIFICATION
        # elif self._is_external_modification_detected: # Pseudo-Variable
        #    self._current_lock_state = LockState.LOCKSTATE__LOCKED_BY_EXTERNAL_MODIFICATION
        #    _LOGGER.debug(f"{self._name}: LockState set to LOCKSTATE__LOCKED_BY_EXTERNAL_MODIFICATION.")

        else:
            # Standardmässig ist der Zustand ungesperrt
            self._current_lock_state = LockState.UNLOCKED
            _LOGGER.debug(f"{self._name}: LockState set to LOCKSTATE__UNLOCKED due to '{self._lock_integration_entity_id}' and '{self._lock_integration_with_position_entity_id}' being OFF.")


    @callback
    async def _async_handle_input_change(self, event: Event | None) -> None:
        """Handle changes to any relevant input entity for this specific cover."""
        _LOGGER.debug(f"[{DOMAIN}] Input change detected for '{self._name}'. Event: {event}")

        # Wenn der Auslöser der Shadow Control Enabled Schalter ist, den Modus aktualisieren
        if event and event.data.get("entity_id") == self._shadow_control_enabled_entity_id:
            new_state = event.data.get("new_state")
            if new_state:
                self._auto_mode_active = (new_state.state == STATE_ON)
                _LOGGER.info(f"[{DOMAIN}] Auto mode for '{self._name}' switched to: {self._auto_mode_active}")

        # Unabhängig vom Auslöser, immer die Berechnung starten,
        # wenn der Auto-Modus aktiv ist
        if self._auto_mode_active:
            await self._async_calculate_and_apply_cover_position(event)
        else:
            _LOGGER.debug(f"[{DOMAIN}] Auto mode for '{self._name}' is not active. Skipping calculation.")

    @callback
    async def _async_calculate_and_apply_cover_position(self, event: Event | None) -> None:
        """
        Calculate and apply the new cover and tilt position for this specific cover.
        This is where your main Shadow Control logic resides.
        """
        _LOGGER.debug(f"[{DOMAIN}] Calculating and applying cover positions for '{self._name}'.")

        self._update_input_values()

        # 1. Alle benötigten Eingabedaten abrufen
        # Beispiel: Sonnenstand und Helligkeit
        brightness_state = self.hass.states.get(self._brightness_entity_id)
        sun_elevation_state = self.hass.states.get(self._sun_elevation_entity_id)
        sun_azimuth_state = self.hass.states.get(self._sun_azimuth_entity_id)

        # Prüfen, ob alle benötigten Sensoren verfügbar sind und gültige Werte haben
        if not brightness_state or brightness_state.state in ['unavailable', 'unknown'] or \
                not sun_elevation_state or sun_elevation_state.state in ['unavailable', 'unknown'] or \
                not sun_azimuth_state or sun_azimuth_state.state in ['unavailable', 'unknown']:
            _LOGGER.warning(f"[{DOMAIN}] Missing or invalid input data for '{self._name}'. Skipping calculation.")
            return

        # Werte in den richtigen Typ umwandeln
        try:
            current_brightness = float(brightness_state.state)
            current_elevation = float(sun_elevation_state.state)
            current_azimuth = float(sun_azimuth_state.state)
        except ValueError as e:
            _LOGGER.error(f"[{DOMAIN}] Invalid state value for sensor for '{self._name}': {e}. Skipping calculation.")
            return

        self._check_if_position_changed_externally(self._shutter_current_height, self._shutter_current_angle)
        await self._check_if_facade_is_in_sun()

        await self._process_shutter_state()

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
                self.async_schedule_update_ha_state()  # UI-Update anfordern
        else:
            _LOGGER.debug(
                f"{self._name}: No specific handler for current state or locked. Current lock state: {self._current_lock_state.name}")
            self._cancel_recalculation_timer()
            self._update_extra_state_attributes()  # Auch hier Attribute aktualisieren, falls sich durch Sperrung etwas ändert
            self.async_schedule_update_ha_state()  # UI-Update anfordern

        _LOGGER.debug(f"{self._name}: New shutter state after processing: {self._current_shutter_state.name} ({self._current_shutter_state.value})")

    def _check_if_position_changed_externally(self, current_height, current_angle):
        #_LOGGER.debug(f"{self._name}: Checking if position changed externally. Current height: {current_height}, Current angle: {current_angle}")
        _LOGGER.debug(f"{self._name}: Check for external shutter modification -> TBD")
        pass


    async def _send_cover_commands(self, desired_height: float, desired_tilt_position: float) -> None:
        """Helper to send commands to the target cover."""
        entity_id = self._target_cover_entity_id
        current_cover_state: State | None = self.hass.states.get(entity_id)

        if not current_cover_state:
            _LOGGER.warning(f"[{DOMAIN}] Target cover entity '{entity_id}' not found. Cannot send commands.")
            return

        supported_features = current_cover_state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)

        # Hier die korrekten Dienstnamen verwenden
        has_pos_service = self.hass.services.has_service("cover", "set_cover_position")
        has_tilt_service = self.hass.services.has_service("cover", "set_cover_tilt_position")

        _LOGGER.debug(f"[{DOMAIN}] Services availability for '{self._name}' ({entity_id}): set_cover_position={has_pos_service}, set_cover_tilt_position={has_tilt_service}")

        # Aktuelle Positionen für Optimierung abrufen
        current_pos = current_cover_state.attributes.get('current_position')
        current_tilt = current_cover_state.attributes.get('current_tilt_position')

        # Toleranzen aus Konfiguration verwenden
        # tolerance_height = float(self.hass.states.get(self._config["modification_tolerance_height_entity_id"]).state)
        # tolerance_angle = float(self.hass.states.get(self._config["modification_tolerance_angle_entity_id"]).state)
        # Für den Moment fixe Toleranzen, bis Sie die Entitätenwerte lesen
        tolerance_height = 0.5
        tolerance_angle = 0.5


        # Höhen-Befehl senden
        if (supported_features & CoverEntityFeature.SET_POSITION) and has_pos_service:
            if current_pos is None or abs(current_pos - desired_height) > tolerance_height:
                _LOGGER.info(f"[{DOMAIN}] Setting '{self._name}' ({entity_id}) position to {desired_height:.1f}% (current: {current_pos}).")
                try:
                    await self.hass.services.async_call(
                        "cover",
                        "set_cover_position", # Korrekter Dienstname
                        {"entity_id": entity_id, "position": desired_height},
                        blocking=False
                    )
                except Exception as e:
                    _LOGGER.error(f"[{DOMAIN}] Failed to set position for '{self._name}' ({entity_id}): {e}")
            else:
                _LOGGER.debug(f"[{DOMAIN}] Position for '{self._name}' ({entity_id}) already at {desired_height:.1f}% (current: {current_pos}).")
        else:
            _LOGGER.debug(f"[{DOMAIN}] Skipping position set for '{self._name}' ({entity_id}). Supported: {supported_features & CoverEntityFeature.SET_POSITION}, Service Found: {has_pos_service}.")


        # Winkel-Befehl senden
        if (supported_features & CoverEntityFeature.SET_TILT_POSITION) and has_tilt_service:
            if current_tilt is None or abs(current_tilt - desired_tilt_position) > tolerance_angle:
                _LOGGER.info(f"[{DOMAIN}] Setting '{self._name}' ({entity_id}) tilt position to {desired_tilt_position:.1f}% (current: {current_tilt}).")
                try:
                    await self.hass.services.async_call(
                        "cover",
                        "set_cover_tilt_position", # Korrekter Dienstname
                        {"entity_id": entity_id, "tilt_position": desired_tilt_position},
                        blocking=False
                    )
                except Exception as e:
                    _LOGGER.error(f"[{DOMAIN}] Failed to set tilt position for '{self._name}' ({entity_id}): {e}")
            else:
                _LOGGER.debug(f"[{DOMAIN}] Tilt position for '{self._name}' ({entity_id}) already at {desired_tilt_position:.1f}% (current: {current_tilt}).")
        else:
            _LOGGER.debug(f"[{DOMAIN}] Skipping tilt set for '{self._name}' ({entity_id}). Supported: {supported_features & CoverEntityFeature.SET_TILT_POSITION}, Service Found: {has_tilt_service}.")


    async def async_unload(self) -> bool:
        """Clean up when the integration is unloaded."""
        _LOGGER.debug(f"[{DOMAIN}] Unloading Shadow Control for '{self._name}'.")
        for listener in self._listeners:
            listener() # Remove event listener
        return True
