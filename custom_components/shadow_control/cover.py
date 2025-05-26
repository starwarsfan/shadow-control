"""Platform for Shadow Control integration."""

from __future__ import annotations

import logging
import math
from typing import Any, Awaitable, Callable, Optional

import voluptuous as vol
from datetime import datetime, timedelta, timezone
from homeassistant.components.cover import CoverEntity, CoverEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, STATE_ON, STATE_OFF, STATE_UNAVAILABLE, STATE_UNKNOWN 
from homeassistant.core import Event, HomeAssistant, callback, State, CALLBACK_TYPE
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import callback, async_call_later, async_track_state_change_event
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    DOMAIN,
    DEFAULT_NAME,

    # === Dynamische Eingänge (Test-Helfer) ===
    CONF_BRIGHTNESS_ENTITY_ID,
    CONF_BRIGHTNESS_DAWN_ENTITY_ID,
    CONF_SUN_ELEVATION_ENTITY_ID,
    CONF_SUN_AZIMUTH_ENTITY_ID,
    CONF_SHUTTER_CURRENT_HEIGHT_ENTITY_ID,
    CONF_SHUTTER_CURRENT_ANGLE_ENTITY_ID,
    CONF_LOCK_INTEGRATION_ENTITY_ID,
    CONF_LOCK_INTEGRATION_WITH_POSITION_ENTITY_ID,
    CONF_LOCK_HEIGHT_ENTITY_ID,
    CONF_LOCK_ANGLE_ENTITY_ID,
    CONF_MODIFICATION_TOLERANCE_HEIGHT_ENTITY_ID,
    CONF_MODIFICATION_TOLERANCE_ANGLE_ENTITY_ID,

    # === Allgemeine Einstellungen (Test-Helfer) ===
    CONF_AZIMUTH_FACADE_ENTITY_ID,
    CONF_OFFSET_SUN_IN_ENTITY_ID,
    CONF_OFFSET_SUN_OUT_ENTITY_ID,
    CONF_ELEVATION_SUN_MIN_ENTITY_ID,
    CONF_ELEVATION_SUN_MAX_ENTITY_ID,
    CONF_SLAT_WIDTH_ENTITY_ID,
    CONF_SLAT_DISTANCE_ENTITY_ID,
    CONF_ANGLE_OFFSET_ENTITY_ID,
    CONF_MIN_SLAT_ANGLE_ENTITY_ID,
    CONF_STEPPING_HEIGHT_ENTITY_ID,
    CONF_STEPPING_ANGLE_ENTITY_ID,
    CONF_SHUTTER_TYPE_ENTITY_ID,
    CONF_LIGHT_BAR_WIDTH_ENTITY_ID,
    CONF_SHUTTER_HEIGHT_ENTITY_ID,
    CONF_NEUTRAL_POS_HEIGHT_ENTITY_ID,
    CONF_NEUTRAL_POS_ANGLE_ENTITY_ID,
    CONF_MOVEMENT_RESTRICTION_HEIGHT_ENTITY_ID,
    CONF_MOVEMENT_RESTRICTION_ANGLE_ENTITY_ID,
    CONF_UPDATE_LOCK_OUTPUT_ENTITY_ID,

    # === Beschattungseinstellungen (Test-Helfer) ===
    CONF_SHADOW_CONTROL_ENABLED_ENTITY_ID,
    CONF_SHADOW_BRIGHTNESS_LEVEL_ENTITY_ID,
    CONF_SHADOW_AFTER_SECONDS_ENTITY_ID,
    CONF_SHADOW_MAX_HEIGHT_ENTITY_ID,
    CONF_SHADOW_MAX_ANGLE_ENTITY_ID,
    CONF_SHADOW_LOOK_THROUGH_SECONDS_ENTITY_ID,
    CONF_SHADOW_OPEN_SECONDS_ENTITY_ID,
    CONF_SHADOW_LOOK_THROUGH_ANGLE_ENTITY_ID,
    CONF_AFTER_SHADOW_HEIGHT_ENTITY_ID,
    CONF_AFTER_SHADOW_ANGLE_ENTITY_ID,

    # === Dämmerungseinstellungen (Test-Helfer) ===
    CONF_DAWN_CONTROL_ENABLED_ENTITY_ID,
    CONF_DAWN_BRIGHTNESS_LEVEL_ENTITY_ID,
    CONF_DAWN_AFTER_SECONDS_ENTITY_ID,
    CONF_DAWN_MAX_HEIGHT_ENTITY_ID,
    CONF_DAWN_MAX_ANGLE_ENTITY_ID,
    CONF_DAWN_LOOK_THROUGH_SECONDS_ENTITY_ID,
    CONF_DAWN_OPEN_SECONDS_ENTITY_ID,
    CONF_DAWN_LOOK_THROUGH_ANGLE_ENTITY_ID,
    CONF_AFTER_DAWN_HEIGHT_ENTITY_ID,
    CONF_AFTER_DAWN_ANGLE_ENTITY_ID,

    # Ausgang
    CONF_TARGET_COVER_ENTITY_ID,

    # Enumerations
    ShutterState,
    LockState,
    MovementRestricted,
)

DEFAULT_NAME = "Shadow Control"

_LOGGER = logging.getLogger(__name__)

# Diese Funktion wird von Home Assistant aufgerufen, wenn die Plattform
# über die configuration.yaml eingerichtet wird.
async def async_setup_platform(
        hass: HomeAssistant,
        config: ConfigType, # Die Konfiguration aus der configuration.yaml
        async_add_entities: AddEntitiesCallback,
        discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Shadow Control platform from YAML."""
    _LOGGER.info(f"Setting up Shadow Control platform from YAML")
    _LOGGER.debug(f"Configuration from YAML: {config}")

    name = config.get(CONF_NAME, DEFAULT_NAME)
    target_cover_entity_id = config.get(CONF_TARGET_COVER_ENTITY_ID)

    if not target_cover_entity_id:
        _LOGGER.error(f"[{name}]: Missing required configuration key '{CONF_TARGET_COVER_ENTITY_ID}'")
        return # Wichtig: Hier sollte kein False zurückgegeben werden, Home Assistant erwartet nichts
               # nach dem Logging des Fehlers und Beenden der Funktion.

    # Hier erstellen wir eine Instanz Ihrer ShadowControl-Klasse.
    # Die 'config' enthält alle Parameter, die Sie in der configuration.yaml
    # unter 'shadow_control:' definiert haben.
    # Wir übergeben 'config' direkt an den Konstruktor.
    async_add_entities([ShadowControl(hass, config, target_cover_entity_id)])

class ShadowControl(CoverEntity, RestoreEntity):
    """Representation of a Shadow Control cover."""

    _attr_has_entity_name = True

    def __init__(
            self,
            hass: HomeAssistant,
            config: ConfigType, # Empfängt die gesamte Konfiguration
            target_cover_entity_id: str, # ID der zu steuernde Entität
    ) -> None:
        """Initialize the Shadow Control cover."""
        super().__init__() # Call base class constructor

        self.hass = hass # Speichern der hass Instanz
        self._name = config.get(CONF_NAME, DEFAULT_NAME)
        self._config = config

        _LOGGER.debug(f"{self._name}: Initializing Shadow Control")

        # Entity ID with which the integration will be visible within HA
        self._attr_unique_id = f"shadow_control_{self._name.lower().replace(' ', '_')}"
        self.entity_id = f"cover.{self._attr_unique_id}" # Wichtig, um die Entität eindeutig zu machen

        self._target_cover_entity_id = target_cover_entity_id

        self._attr_extra_state_attributes: dict[str, Any] = {}

        # === Dynamische Eingänge (Test-Helfer) ===
        self._brightness_entity_id = config.get(CONF_BRIGHTNESS_ENTITY_ID)
        self._brightness_dawn_entity_id = config.get(CONF_BRIGHTNESS_DAWN_ENTITY_ID)
        self._sun_elevation_entity_id = config.get(CONF_SUN_ELEVATION_ENTITY_ID)
        self._sun_azimuth_entity_id = config.get(CONF_SUN_AZIMUTH_ENTITY_ID)
        self._shutter_current_height_entity_id = config.get(CONF_SHUTTER_CURRENT_HEIGHT_ENTITY_ID)
        self._shutter_current_angle_entity_id = config.get(CONF_SHUTTER_CURRENT_ANGLE_ENTITY_ID)
        self._lock_integration_entity_id = config.get(CONF_LOCK_INTEGRATION_ENTITY_ID)
        self._lock_integration_with_position_entity_id = config.get(CONF_LOCK_INTEGRATION_WITH_POSITION_ENTITY_ID)
        self._lock_height_entity_id = config.get(CONF_LOCK_HEIGHT_ENTITY_ID)
        self._lock_angle_entity_id = config.get(CONF_LOCK_ANGLE_ENTITY_ID)
        self._modification_tolerance_height_entity_id = config.get(CONF_MODIFICATION_TOLERANCE_HEIGHT_ENTITY_ID)
        self._modification_tolerance_angle_entity_id = config.get(CONF_MODIFICATION_TOLERANCE_ANGLE_ENTITY_ID)

        # === Allgemeine Einstellungen (Test-Helfer) ===
        self._azimuth_facade_entity_id = config.get(CONF_AZIMUTH_FACADE_ENTITY_ID)
        self._offset_sun_in_entity_id = config.get(CONF_OFFSET_SUN_IN_ENTITY_ID)
        self._offset_sun_out_entity_id = config.get(CONF_OFFSET_SUN_OUT_ENTITY_ID)
        self._elevation_sun_min_entity_id = config.get(CONF_ELEVATION_SUN_MIN_ENTITY_ID)
        self._elevation_sun_max_entity_id = config.get(CONF_ELEVATION_SUN_MAX_ENTITY_ID)
        self._slat_width_entity_id = config.get(CONF_SLAT_WIDTH_ENTITY_ID)
        self._slat_distance_entity_id = config.get(CONF_SLAT_DISTANCE_ENTITY_ID)
        self._angle_offset_entity_id = config.get(CONF_ANGLE_OFFSET_ENTITY_ID)
        self._min_slat_angle_entity_id = config.get(CONF_MIN_SLAT_ANGLE_ENTITY_ID)
        self._stepping_height_entity_id = config.get(CONF_STEPPING_HEIGHT_ENTITY_ID)
        self._stepping_angle_entity_id = config.get(CONF_STEPPING_ANGLE_ENTITY_ID)
        self._shutter_type_entity_id = config.get(CONF_SHUTTER_TYPE_ENTITY_ID)
        self._light_bar_width_entity_id = config.get(CONF_LIGHT_BAR_WIDTH_ENTITY_ID)
        self._shutter_height_entity_id = config.get(CONF_SHUTTER_HEIGHT_ENTITY_ID)
        self._neutral_pos_height_entity_id = config.get(CONF_NEUTRAL_POS_HEIGHT_ENTITY_ID)
        self._neutral_pos_angle_entity_id = config.get(CONF_NEUTRAL_POS_ANGLE_ENTITY_ID)
        self._movement_restriction_height_entity_id = config.get(CONF_MOVEMENT_RESTRICTION_HEIGHT_ENTITY_ID)
        self._movement_restriction_angle_entity_id = config.get(CONF_MOVEMENT_RESTRICTION_ANGLE_ENTITY_ID)
        self._update_lock_output_entity_id = config.get(CONF_UPDATE_LOCK_OUTPUT_ENTITY_ID)

        # === Beschattungseinstellungen (Test-Helfer) ===
        self._shadow_control_enabled_entity_id = config.get(CONF_SHADOW_CONTROL_ENABLED_ENTITY_ID)
        self._shadow_brightness_level_entity_id = config.get(CONF_SHADOW_BRIGHTNESS_LEVEL_ENTITY_ID)
        self._shadow_after_seconds_entity_id = config.get(CONF_SHADOW_AFTER_SECONDS_ENTITY_ID)
        self._shadow_max_height_entity_id = config.get(CONF_SHADOW_MAX_HEIGHT_ENTITY_ID)
        self._shadow_max_angle_entity_id = config.get(CONF_SHADOW_MAX_ANGLE_ENTITY_ID)
        self._shadow_look_through_seconds_entity_id = config.get(CONF_SHADOW_LOOK_THROUGH_SECONDS_ENTITY_ID)
        self._shadow_open_seconds_entity_id = config.get(CONF_SHADOW_OPEN_SECONDS_ENTITY_ID)
        self._shadow_look_through_angle_entity_id = config.get(CONF_SHADOW_LOOK_THROUGH_ANGLE_ENTITY_ID)
        self._after_shadow_height_entity_id = config.get(CONF_AFTER_SHADOW_HEIGHT_ENTITY_ID)
        self._after_shadow_angle_entity_id = config.get(CONF_AFTER_SHADOW_ANGLE_ENTITY_ID)

        # === Dämmerungseinstellungen (Test-Helfer) ===
        self._dawn_control_enabled_entity_id = config.get(CONF_DAWN_CONTROL_ENABLED_ENTITY_ID)
        self._dawn_brightness_level_entity_id = config.get(CONF_DAWN_BRIGHTNESS_LEVEL_ENTITY_ID)
        self._dawn_after_seconds_entity_id = config.get(CONF_DAWN_AFTER_SECONDS_ENTITY_ID)
        self._dawn_max_height_entity_id = config.get(CONF_DAWN_MAX_HEIGHT_ENTITY_ID)
        self._dawn_max_angle_entity_id = config.get(CONF_DAWN_MAX_ANGLE_ENTITY_ID)
        self._dawn_look_through_seconds_entity_id = config.get(CONF_DAWN_LOOK_THROUGH_SECONDS_ENTITY_ID)
        self._dawn_open_seconds_entity_id = config.get(CONF_DAWN_OPEN_SECONDS_ENTITY_ID)
        self._dawn_look_through_angle_entity_id = config.get(CONF_DAWN_LOOK_THROUGH_ANGLE_ENTITY_ID)
        self._after_dawn_height_entity_id = config.get(CONF_AFTER_DAWN_HEIGHT_ENTITY_ID)
        self._after_dawn_angle_entity_id = config.get(CONF_AFTER_DAWN_ANGLE_ENTITY_ID)

        # Aktuelle Werte der Eingänge resp. deren Entitäten
        # === Dynamische Eingänge (Test-Helfer) ===
        self._brightness: float | None = None
        self._brightness_dawn: float | None = None
        self._sun_elevation: float | None = None
        self._sun_azimuth: float | None = None
        self._shutter_current_height: float | None = None
        self._shutter_current_angle: float | None = None
        self._lock_integration: bool | None = None
        self._lock_integration_with_position: bool | None = None
        self._lock_height: float | None = None
        self._lock_angle: float | None = None
        self._modification_tolerance_height: float | None = None
        self._modification_tolerance_angle: float | None = None

        # === Allgemeine Einstellungen (Test-Helfer) ===
        self._azimuth_facade: float | None = None
        self._offset_sun_in: float | None = None
        self._offset_sun_out: float | None = None
        self._elevation_sun_min: float | None = None
        self._elevation_sun_max: float | None = None
        self._slat_width: float | None = None
        self._slat_distance: float | None = None
        self._angle_offset: float | None = None
        self._min_slat_angle: float | None = None
        self._stepping_height: float | None = None
        self._stepping_angle: float | None = None
        self._shutter_type: str | None = None
        self._light_bar_width: float | None = None
        self._shutter_height: float | None = None
        self._neutral_pos_height: float | None = None
        self._neutral_pos_angle: float | None = None
        self._movement_restriction_height: MovementRestricted = MovementRestricted.NO_RESTRICTION
        self._movement_restriction_angle: MovementRestricted = MovementRestricted.NO_RESTRICTION
        self._update_lock_output: str | None = None

        # === Beschattungseinstellungen (Test-Helfer) ===
        self._shadow_control_enabled: bool | None = None
        self._shadow_brightness_level: float | None = None
        self._shadow_after_seconds: float | None = None
        self._shadow_max_height: float | None = None
        self._shadow_max_angle: float | None = None
        self._shadow_look_through_seconds: float | None = None
        self._shadow_open_seconds: float | None = None
        self._shadow_look_through_angle: float | None = None
        self._after_shadow_height: float | None = None
        self._after_shadow_angle: float | None = None

        # === Dämmerungseinstellungen (Test-Helfer) ===
        self._dawn_control_enabled: bool | None = None
        self._dawn_brightness_level: float | None = None
        self._dawn_after_seconds: float | None = None
        self._dawn_max_height: float | None = None
        self._dawn_max_angle: float | None = None
        self._dawn_look_through_seconds: float | None = None
        self._dawn_open_seconds: float | None = None
        self._dawn_look_through_angle: float | None = None
        self._after_dawn_height: float | None = None
        self._after_dawn_angle: float | None = None

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
        self._effective_elevation: float | None = None
        self._previous_shutter_height: float | None = None
        self._previous_shutter_angle: float | None = None
        self._is_initial_run: bool = True # Flag für den initialen Lauf
        self._is_producing_shadow: bool = False # Neuer interner Zustand für ProduceShadow

        # Für den "output" der Gradzahl
        self._calculated_angle_degrees: float | None = None

        self._listeners: list[Callable[[], None]] = [] # Liste zum Speichern der Listener
        self._recalculation_timer: Callable[[], None] | None = None # Zum Speichern des Callbacks für den geplanten Timer

        _LOGGER.debug(f"{self._name}: Integration initialization finished")

    # =======================================================================
    # Listener registrieren, welche die Integration triggern
    async def async_added_to_hass(self) -> None:
        """Run when this Entity has been added to Home Assistant."""
        await super().async_added_to_hass()

        _LOGGER.debug(f"{self._name}: async_added_to_hass called. Registering listeners.")

        # === 1. Lade den zuletzt gespeicherten Status der Entität ===
        _LOGGER.debug(f"{self._name}: Attempting to retrieve last state...")
        last_state = await self.async_get_last_state()

        if last_state:
            _LOGGER.debug(f"{self._name}: Successfully retrieved last state.")
            # last_state.attributes.get gibt None zurück, wenn das Attribut nicht existiert
            initial_state_value = last_state.attributes.get("current_shutter_state")

            if initial_state_value is not None:
                try:
                    self._current_shutter_state = ShutterState(int(initial_state_value))
                    _LOGGER.debug(f"{self._name}: Restored _current_shutter_state to {self._current_shutter_state}")
                except (ValueError, TypeError):
                    _LOGGER.warning(f"{self._name}: Could not convert last state '{initial_state_value}' to int. Using STATE_NEUTRAL.")
                    self._current_shutter_state = ShutterState.NEUTRAL
            else:
                self._current_shutter_state = ShutterState.NEUTRAL
                _LOGGER.debug(f"{self._name}: 'current_shutter_state' not found in last state. Initializing to {self._current_shutter_state}")
        else:
            self._current_shutter_state = ShutterState.NEUTRAL
            _LOGGER.debug(f"{self._name}: No last state found. Initializing _current_shutter_state to {self._current_shutter_state}")

        # Aktualisiere die Attribute und speichere den Zustand sofort, falls er wiederhergestellt wurde
        self._update_extra_state_attributes()
        self.async_write_ha_state()

        # Registrieren Sie Listener für Ihre Trigger-Entitäten
        # Alle Entity-IDs kommen jetzt aus den Instanzvariablen, die aus der Konfiguration gefüllt wurden.
        trigger_entities = [
            self._brightness_entity_id,
            self._brightness_dawn_entity_id,
            self._sun_elevation_entity_id,
            self._sun_azimuth_entity_id,
            self._lock_integration_entity_id,
            self._lock_integration_with_position_entity_id,
            self._shadow_control_enabled_entity_id,
            self._dawn_control_enabled_entity_id
        ]

        # Filtern Sie None-Werte heraus, falls optional konfigurierte Entitäten nicht vorhanden sind.
        # Dies verhindert Fehler, wenn ein entity_id in der Konfiguration weggelassen wird.
        valid_trigger_entities = [entity_id for entity_id in trigger_entities if entity_id is not None]

        if valid_trigger_entities:
            self._listeners.append(
                async_track_state_change_event(
                    self.hass,
                    valid_trigger_entities,
                    self._async_trigger_recalculation,  # Ihre Callback-Funktion
                )
            )
            _LOGGER.debug(f"{self._name}: Registered listeners for input changes on: {valid_trigger_entities}")
        else:
            _LOGGER.warning(f"{self._name}: No valid trigger entities configured. Recalculation will only happen on initial load")

        self._update_input_values()

        # Initialberechnung beim Start
        await self._async_trigger_recalculation(None)

    # =======================================================================
    # Registrierte Listener entfernen
    async def async_will_remove_from_hass(self) -> None:
        """Run when this Entity will be removed from Home Assistant."""
        await super().async_will_remove_from_hass()
        _LOGGER.debug(f"{self._name}: async_will_remove_from_hass called. Removing listeners.")
        for remove_listener in self._listeners:
            remove_listener()
        self._listeners = []

    # =======================================================================
    # Persistente Werte
    def _update_extra_state_attributes(self) -> None:
        """Helper to update the extra_state_attributes dictionary."""
        self._attr_extra_state_attributes = {
            "current_shutter_state": self._current_shutter_state,
            "calculated_shutter_height": self._calculated_shutter_height,
            "calculated_shutter_angle": self._calculated_shutter_angle,
        }

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
        self._azimuth_facade = self._get_entity_numeric_state(self._azimuth_facade_entity_id, float)
        self._offset_sun_in = self._get_entity_numeric_state(self._offset_sun_in_entity_id, float)
        self._offset_sun_out = self._get_entity_numeric_state(self._offset_sun_out_entity_id, float)
        self._elevation_sun_min = self._get_entity_numeric_state(self._elevation_sun_min_entity_id, float)
        self._elevation_sun_max = self._get_entity_numeric_state(self._elevation_sun_max_entity_id, float)
        self._slat_width = self._get_entity_numeric_state(self._slat_width_entity_id, float)
        self._slat_distance = self._get_entity_numeric_state(self._slat_distance_entity_id, float)
        self._angle_offset = self._get_entity_numeric_state(self._angle_offset_entity_id, float)
        self._min_slat_angle = self._get_entity_numeric_state(self._min_slat_angle_entity_id, float)
        self._stepping_height = self._get_entity_numeric_state(self._stepping_height_entity_id, float)
        self._stepping_angle = self._get_entity_numeric_state(self._stepping_angle_entity_id, float)
        self._shutter_type = self._get_entity_string_state(self._shutter_type_entity_id)
        self._light_bar_width = self._get_entity_numeric_state(self._light_bar_width_entity_id, float)
        self._shutter_height = self._get_entity_numeric_state(self._shutter_height_entity_id, float)
        self._neutral_pos_height = self._get_entity_numeric_state(self._neutral_pos_height_entity_id, float)
        self._neutral_pos_angle = self._get_entity_numeric_state(self._neutral_pos_angle_entity_id, float)

        # -------------------------------------------
        # Movement restriction to enumeration mapping
        #self._movement_restriction_height = self._get_entity_string_state(self._movement_restriction_height_entity_id)
        height_restriction_entity_id = self._config.get(CONF_MOVEMENT_RESTRICTION_HEIGHT_ENTITY_ID)
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
            _LOGGER.warning(f"{self._name}: Configuration of '{CONF_MOVEMENT_RESTRICTION_HEIGHT_ENTITY_ID}' missing. Using NO_RESTRICTION.")
            self._movement_restriction_height = MovementRestricted.NO_RESTRICTION
        #self._movement_restriction_angle = self._get_entity_string_state(self._movement_restriction_angle_entity_id)
        angle_restriction_entity_id = self._config.get(CONF_MOVEMENT_RESTRICTION_ANGLE_ENTITY_ID)
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
            _LOGGER.warning(f"{self._name}: Configuration of '{CONF_MOVEMENT_RESTRICTION_ANGLE_ENTITY_ID}' missing. Using NO_RESTRICTION.")
            self._movement_restriction_angle = MovementRestricted.NO_RESTRICTION

        self._update_lock_output = self._get_entity_string_state(self._update_lock_output_entity_id)

        # === Beschattungseinstellungen ===
        self._shadow_control_enabled = self._get_entity_boolean_state(self._shadow_control_enabled_entity_id)
        self._shadow_brightness_level = self._get_entity_numeric_state(self._shadow_brightness_level_entity_id, float)
        self._shadow_after_seconds = self._get_entity_numeric_state(self._shadow_after_seconds_entity_id, float)
        self._shadow_max_height = self._get_entity_numeric_state(self._shadow_max_height_entity_id, float)
        self._shadow_max_angle = self._get_entity_numeric_state(self._shadow_max_angle_entity_id, float)
        self._shadow_look_through_seconds = self._get_entity_numeric_state(self._shadow_look_through_seconds_entity_id, float)
        self._shadow_open_seconds = self._get_entity_numeric_state(self._shadow_open_seconds_entity_id, float)
        self._shadow_look_through_angle = self._get_entity_numeric_state(self._shadow_look_through_angle_entity_id, float)
        self._after_shadow_height = self._get_entity_numeric_state(self._after_shadow_height_entity_id, float)
        self._after_shadow_angle = self._get_entity_numeric_state(self._after_shadow_angle_entity_id, float)

        # === Dämmerungseinstellungen ===
        self._dawn_control_enabled = self._get_entity_boolean_state(self._dawn_control_enabled_entity_id)
        self._dawn_brightness_level = self._get_entity_numeric_state(self._dawn_brightness_level_entity_id, float)
        self._dawn_after_seconds = self._get_entity_numeric_state(self._dawn_after_seconds_entity_id, float)
        self._dawn_max_height = self._get_entity_numeric_state(self._dawn_max_height_entity_id, float)
        self._dawn_max_angle = self._get_entity_numeric_state(self._dawn_max_angle_entity_id, float)
        self._dawn_look_through_seconds = self._get_entity_numeric_state(self._dawn_look_through_seconds_entity_id, float)
        self._dawn_open_seconds = self._get_entity_numeric_state(self._dawn_open_seconds_entity_id, float)
        self._dawn_look_through_angle = self._get_entity_numeric_state(self._dawn_look_through_angle_entity_id, float)
        self._after_dawn_height = self._get_entity_numeric_state(self._after_dawn_height_entity_id, float)
        self._after_dawn_angle = self._get_entity_numeric_state(self._after_dawn_angle_entity_id, float)

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


    # =======================================================================
    # Beschattung neu berechnen
    async def _async_trigger_recalculation(
            self, event: Event | None
    ) -> None:
        """Callback for state changes of trigger entities."""
        if event:
            entity_id = event.data.get("entity_id")
            old_state = event.data.get("old_state")
            new_state = event.data.get("new_state")
            _LOGGER.debug(f"{self._name}: Trigger entity {entity_id} state changed from\n  {old_state}\nto\n  {new_state} --> Recalculating...")
        else:
            _LOGGER.debug(f"{self._name}: Initial trigger recalculation (no event).")

        # === Hier beginnt Ihre gesamte Beschattungslogik ===
        # 1. Alle benötigten Werte abrufen (auch die Nicht-Trigger-Werte, die den letzten Stand behalten)
        self._update_input_values()

        # 2. Beschattungslogik ausführen
        self._check_if_position_changed_externally(self._shutter_current_height, self._shutter_current_angle)
        await self._check_if_facade_is_in_sun()

        await self._process_shutter_state()

        # 4. Update the dictionary holding the attributes
        self._update_extra_state_attributes()
        # 5. Tell Home Assistant to save the updated state (and attributes)
        self.async_write_ha_state()

    async def _process_shutter_state(self) -> None:
        """
        Verarbeitet den aktuellen Behangzustand und ruft die entsprechende Handler-Funktion auf.
        Die Handler-Funktionen müssen den neuen ShutterState zurückgeben.
        """
        _LOGGER.debug(f"{self._name}: Current shutter state (before processing): {self._current_shutter_state.name} ({self._current_shutter_state.value})")

        handler_func = self._state_handlers.get(self._current_shutter_state)
        new_shutter_state: ShutterState

        if handler_func:
            # Rufe die entsprechende Handler-Methode auf
            new_shutter_state = await handler_func()
        else:
            # Standardfall: Wenn der Zustand nicht im Dictionary gefunden wird
            _LOGGER.warning(f"{self._name}: Shutter within undefined state ({self._current_shutter_state}). Using NEUTRAL ({ShutterState.NEUTRAL.value}).")
            new_shutter_state = await self._handle_state_neutral() # Ruft den Handler für NEUTRAL auf

        # Aktualisiere den internen Behangzustand
        self._current_shutter_state = new_shutter_state
        _LOGGER.debug(f"{self._name}: New shutter state after processing: {self._current_shutter_state.name} ({self._current_shutter_state.value})")

    def _check_if_position_changed_externally(self, current_height, current_angle):
        #_LOGGER.debug(f"{self._name}: Checking if position changed externally. Current height: {current_height}, Current angle: {current_angle}")
        _LOGGER.debug(f"{self._name}: Check for external shutter modification -> TBD")
        pass

    @callback
    async def _handle_sensor_change(self, event) -> None:
        """Handle changes in sensor states."""
        _LOGGER.debug(f"{self._name}: Sensor change detected: {event.data.get('entity_id')}")
        await self.async_update_ha_state(True) # Fordert ein Update der Entität an

    # --- CoverEntity Properties ---
    @property
    def name(self) -> str:
        """Return the name of the cover."""
        return self._name

    @property
    def supported_features(self) -> CoverEntityFeature:
        """Flag supported features."""
        features = (
                CoverEntityFeature.OPEN
                | CoverEntityFeature.CLOSE
                | CoverEntityFeature.STOP
                | CoverEntityFeature.SET_POSITION
        )
        # Optional: Fügen Sie Tilt hinzu, wenn Ihr Test-Cover und Ihre Logik es unterstützen
        # features |= CoverEntityFeature.SET_TILT_POSITION
        return features

    @property
    def current_cover_position(self) -> int | None:
        """Return current position of cover. 0 is closed, 100 is open."""
        # Hier lesen Sie den Wert Ihres Test-Höhen-Helfers
        height_state = self.hass.states.get(self._shutter_current_height_entity_id)
        if height_state and height_state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            try:
                return int(float(height_state.state))
            except ValueError:
                _LOGGER.warning(f"{self._name}: Could not parse position from {self._shutter_current_height_entity_id}: {height_state.state}")
        return None

    @property
    def current_cover_tilt_position(self) -> int | None:
        """Return current tilt position of cover. 0 is closed, 100 is open."""
        # Hier lesen Sie den Wert Ihres Test-Winkel-Helfers
        angle_state = self.hass.states.get(self._shutter_current_angle_entity_id)
        if angle_state and angle_state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            try:
                return int(float(angle_state.state))
            except ValueError:
                _LOGGER.warning(f"{self._name}: Could not parse tilt position from {self._shutter_current_angle_entity_id}: {angle_state.state}")
        return None

    @property
    def is_closed(self) -> bool | None:
        """Return if the cover is closed or not."""
        if self.current_cover_position is None:
            return None
        return self.current_cover_position == 0

    @property
    def is_opening(self) -> bool:
        """Return if the cover is opening or not."""
        return False # Für ein Template-Cover meist False, es sei denn, Sie simulieren dies

    @property
    def is_closing(self) -> bool:
        """Return if the cover is closing or not."""
        return False # Für ein Template-Cover meist False, es sei denn, Sie simulieren dies

    # --- CoverEntity Methods ---
    async def async_open_cover(self, **kwargs: any) -> None:
        """Open the cover."""
        _LOGGER.info(f"{self._name}: Opening cover (calling script)")
        await self.hass.services.async_call(
            "script",
            "test_cover_open", # Ihr Test-Skript
            blocking=True,
        )
        # Optional: Den Helfer für die aktuelle Position aktualisieren (falls nicht durch das Skript erledigt)
        # self.hass.states.async_set(self._shutter_current_height_entity_id, 100)
        self.async_write_ha_state()

    async def async_close_cover(self, **kwargs: any) -> None:
        """Close the cover."""
        _LOGGER.info(f"{self._name}: Closing cover (calling script)")
        await self.hass.services.async_call(
            "script",
            "test_cover_close", # Ihr Test-Skript
            blocking=True,
        )
        # self.hass.states.async_set(self._shutter_current_height_entity_id, 0)
        self.async_write_ha_state()

    async def async_set_cover_position(self, **kwargs: any) -> None:
        """Move the cover to a specific position."""
        position = kwargs[ATTR_POSITION]
        _LOGGER.info(f"{self._name}: Setting cover position to {position} (calling script)")
        await self.hass.services.async_call(
            "script",
            "test_cover_set_position", # Ihr Test-Skript
            service_data={"position": position},
            blocking=True,
        )
        # Simuliert, dass das Skript den Ist-Wert-Helfer aktualisiert
        # In der Realität würde das Skript oder das echte Cover den Zustand ändern.
        # Für Testzwecke können Sie den input_number hier direkt setzen.
        # await self.hass.services.async_call(
        #     "input_number",
        #     "set_value",
        #     {"entity_id": self._shutter_current_height_entity_id, "value": position},
        # )
        self.async_write_ha_state()


    async def async_stop_cover(self, **kwargs: any) -> None:
        """Stop the cover."""
        _LOGGER.info(f"{self._name}: Stopping cover (calling script)")
        await self.hass.services.async_call(
            "script",
            "test_cover_stop", # Ihr Test-Skript
            blocking=True,
        )
        self.async_write_ha_state()

    @property
    def unique_id(self) -> str | None:
        """Return the unique ID of the cover."""
        return f"shadow_control_{self._name.lower().replace(' ', '_')}"

    @property
    def current_cover_tilt(self) -> int | None:
        """Return the current tilt of the cover."""
        # Hier den aktuellen Neigungswinkel abrufen oder aus dem Zustand ableiten
        return None  # Placeholder

    async def _is_shadow_handling_activated(self) -> bool:
        """Check if shadow handling is activated."""
        return self._shadow_control_enabled

    async def _is_dawn_handling_activated(self) -> bool:
        """Check if dawn handling is activated."""
        return self._dawn_control_enabled

    async def _is_lbs_locked_in_either_way(self) -> bool:
        """Check if the cover is locked in any way."""
        return not self._current_lock_state == LockState.UNLOCKED

    async def _get_input_value(self, config_key: str) -> any:
        """Get the value of a configured input entity or setting."""
        if config_key.endswith("_entity"):
            entity_id_key = f"_{config_key}"
            if hasattr(self, entity_id_key):
                entity_id = getattr(self, entity_id_key)
                state = self.hass.states.get(entity_id)
                return (
                    float(state.state)
                    if state and state.state not in ["unavailable", "unknown"]
                    else None
                )
            return None
        else:
            attribute_key = f"_{config_key.lower()}"
            return (
                getattr(self, attribute_key) if hasattr(self, attribute_key) else None
            )

    async def _start_recalculation_timer(self, delay_seconds: float) -> None:
        """
        Startet einen Timer, der nach 'delay_seconds' eine Neuberechnung auslöst.
        Bestehende Timer werden vorher abgebrochen.
        """
        self._cancel_recalculation_timer()  # Immer erst den alten Timer abbrechen

        if delay_seconds <= 0:
            _LOGGER.debug(
                f"{self._name}: Timer delay is <= 0 ({delay_seconds}s). Trigger immediate recalculation")
            await self._async_trigger_recalculation(None)
            return

        _LOGGER.debug(f"{self._name}: Starting recalculation timer for {delay_seconds}s")

        # Save start time and duration
        self._recalculation_timer_start_time = datetime.now(timezone.utc)
        self._recalculation_timer_duration_seconds = delay_seconds

        # Save callback handle from async_call_later to enable timer canceling
        self._recalculation_timer = async_call_later(
            self.hass,
            delay_seconds,
            self._async_timer_callback
        )

    def _cancel_recalculation_timer(self) -> None:
        """Bricht einen laufenden Neuberechnungs-Timer ab."""
        if self._recalculation_timer:
            _LOGGER.debug(f"{self._name}: Canceling recalculation timer")
            self._recalculation_timer()  # Aufruf des Handles bricht den Timer ab
            self._recalculation_timer = None

        # Reset timer tracking variables
        self._recalculation_timer_start_time = None
        self._recalculation_timer_duration_seconds = None

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
        await self._async_trigger_recalculation(None)  # Oder ein spezifisches Event triggern

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
        shutter_stepping_percent = self._shutter_height_stepping_percent

        if shutter_stepping_percent is None:
            _LOGGER.warning(
                f"{self._name}: 'shutter_height_stepping_percent' is None. Using 0 (no stepping).")
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

    async def _position_shutter(
            self,
            shutter_height_percent: float,
            shutter_angle_percent: float,
            shadow_position: bool,
            stop_timer: bool
    ) -> None:
        """
        Sendet die berechneten Höhen- und Winkelwerte an die KNX-Cover-Entität.
        Aktualisiert interne Zustände und publiziert den Binary Sensor für 'Beschattung aktiv'.
        """
        _LOGGER.debug(
            f"{self._name}: Starting _position_shutter with height {shutter_height_percent}% and angle {shutter_angle_percent}%")

        # Prüfung auf den initialen Lauf
        if self._is_initial_run:
            _LOGGER.debug(
                f"{self._name}: Initialer run of integration, only internal computing, no update of outputs")
            # Wir aktualisieren die internen Previous-Werte, damit beim NÄCHSTEN Lauf
            # die sendByChange-ähnliche Logik funktioniert.
            self._previous_shutter_height = shutter_height_percent
            self._previous_shutter_angle = shutter_angle_percent
            self._is_initial_run = False
            self._is_producing_shadow = shadow_position  # Auch den initialen Zustand setzen
            self._calculated_angle_degrees = self._convert_shutter_angle_percent_to_degrees(
                shutter_angle_percent)

            # Publizieren des initialen Beschattungszustands, da es sich um einen initialen Lauf handelt
            binary_sensor_entity_id = f"input_boolean.{self._name.lower().replace(' ', '_')}_shadow_active"
            await self.hass.services.async_call(
                "input_boolean",
                "turn_on" if shadow_position else "turn_off",
                {"entity_id": binary_sensor_entity_id},
                blocking=False
            )
            # Hier ist es wichtig, dass die _update_extra_state_attributes auch nach dem initialen Lauf aufgerufen wird
            self.async_write_ha_state()  # Erzeugt ein State-Update, um Attribute zu aktualisieren
            return

        # Prüfung, ob die Steuerung gesperrt ist
        if self._current_lock_state != LockState.UNLOCKED:
            _LOGGER.debug(
                f"{self._name}: Integration is locked ({self._current_lock_state.name}), no update of outputs")
            return

        # === ProduceShadow als Binary Sensor steuern ===
        # Dies ist der Part für LB_LBSID_sendByChange(LB_LBSID_OUTPUT_ProduceShadow, $shadowPosition);
        # Nur senden, wenn sich der Zustand ändert
        if self._is_producing_shadow != shadow_position:
            binary_sensor_entity_id = f"input_boolean.{self._name.lower().replace(' ', '_')}_shadow_active"
            _LOGGER.debug(
                f"{self._name}: Updating binary sensor '{binary_sensor_entity_id}' to {shadow_position}.")
            await self.hass.services.async_call(
                "input_boolean",
                "turn_on" if shadow_position else "turn_off",
                {"entity_id": binary_sensor_entity_id},
                blocking=False
            )
            self._is_producing_shadow = shadow_position  # Internen Zustand aktualisieren

        # --- Höhen-Handling ---
        height_to_set_percent = self._should_output_be_updated(
            config_value=self._movement_restriction_height,  # Korrekte Instanzvariable
            new_value=shutter_height_percent,
            previous_value=self._previous_shutter_height
        )

        # Senden des Höhenbefehls nur, wenn sich der Wert ändert oder eine erzwungene Aktualisierung nötig ist
        if height_to_set_percent != self._previous_shutter_height:
            _LOGGER.debug(
                f"{self._name}: Sending height of {height_to_set_percent}% to {self._target_cover_entity_id}.")
            await self.hass.services.async_call(
                "cover",
                "set_position",
                {"entity_id": self._target_cover_entity_id, "position": height_to_set_percent},
                blocking=False
            )
        else:
            _LOGGER.debug(
                f"{self._name}: Height '{height_to_set_percent}%' not sent, value was the same than before or has another restriction")

        self._previous_shutter_height = shutter_height_percent  # Immer mit dem NEUEN *berechneten* Wert aktualisieren

        # --- Winkel-Handling ---
        angle_to_set_percent = self._should_output_be_updated(
            config_value=self._movement_restriction_angle,  # Korrekte Instanzvariable
            new_value=shutter_angle_percent,
            previous_value=self._previous_shutter_angle
        )

        # Logik für "if height has changed, update angle anyway"
        # PHP: if ($previousHeight != $shutterHeightPercent)
        # In Python: Wir vergleichen den vorherigen, *ungefilterten* Wert mit dem neuen, *ungefilterten* Wert.
        # Der Vergleich muss mit dem Wert von *vor* dem aktuellen _position_shutter-Aufruf erfolgen
        # Dafür nutzen wir den original shutter_height_percent und den alten self._previous_shutter_height
        # ABER: Die Logik ist jetzt so, dass _previous_shutter_height *bereits* auf den neuen Wert gesetzt wurde.
        # Daher muss man vorsichtig sein oder den alten Wert separat speichern.
        # Einfacher ist es, den Vergleich VOR der Zuweisung zu self._previous_shutter_height zu machen.
        # Da ich den Code oben jetzt so angepasst habe, dass self._previous_shutter_height nach dem Höhenbefehl aktualisiert wird,
        # verwende ich hier den *lokalen* Wert `height_to_set_percent` für den Vergleich,
        # oder alternativ müsste ein `_old_shutter_height_before_this_run` Parameter übergeben werden.
        # Für die PHP-Logik bedeutet "$previousHeight" den Wert, der *vor* dem Aufruf von positionShutter aktuell war.
        # Den aktuellen `self._previous_shutter_height` nach der Aktualisierung der Höhe zu verwenden, ist nicht korrekt für den Vergleich.

        # Korrektur der PHP-Logik "if ($previousHeight != $shutterHeightPercent)"
        # um sicherzustellen, dass die Bedingung sich auf die tatsächliche Änderung der Höhe
        # *durch DIESEN Lauf der Berechnung* bezieht, nicht auf den internen self._previous_shutter_height
        # der bereits aktualisiert wurde.

        # Um die PHP-Logik genau nachzubilden, benötigen wir den Wert, der *vor diesem Aufruf*
        # der Funktion self._previous_shutter_height hatte.
        # Da wir self._previous_shutter_height bereits mit dem neuen Wert aktualisiert haben,
        # müssen wir den ursprünglichen "previous_shutter_height" (der aus der Instanzvariablen kam)
        # in der _should_output_be_updated Methode nutzen.
        # Der hier relevante Vergleich ist der von `shutter_height_percent` (berechneter neuer Wert)
        # mit dem, was `self._previous_shutter_height` *zu Beginn dieses Funktionsaufrufs* war.
        # Da `self._previous_shutter_height` *nach* dem Höhenbefehl aktualisiert wird, ist der Vergleich hier schwierig.

        # Eine einfachere Lösung ist, den Winkelbefehl immer zu senden, wenn sich der berechnete Winkel ändert,
        # ODER wenn sich die Höhe geändert hat (im Sinne von `shutter_height_percent != self._previous_shutter_height_at_start_of_call`).
        # Da wir keinen "shutter_height_percent_at_start_of_call" haben,
        # und die PHP-Logik im Kern sagt "wenn der *Höhen-Zielwert* sich geändert hat,
        # sende den Winkel-Zielwert auch, um den Aktor zu triggern",
        # können wir die Logik auf die tatsächlich von Home Assistant gesendeten Werte beziehen.

        # Alternative Interpretation der PHP-Logik (einfacher in Python):
        # Sende den Tilt-Befehl, WENN:
        # 1. Der neu berechnete Winkel (nach _should_output_be_updated) sich vom *zuletzt gesendeten Winkel* unterscheidet, ODER
        # 2. Der neu berechnete Höhe (nach _should_output_be_updated) sich vom *zuletzt gesendeten Höhe* unterscheidet.
        # Dies ist das Robusteste, da Home Assistant normalerweise nur aktualisiert, wenn sich der Wert ändert.
        # Das bedeutet, der Befehl wird gesendet, wenn `angle_to_set_percent` ungleich `self._previous_shutter_angle` ist,
        # ODER wenn `height_to_set_percent` ungleich `self._previous_shutter_height` ist (beides VOR der Aktualisierung von _previous_).

        # PHP-Code: if ($previousHeight != $shutterHeightPercent)
        # Dies bedeutet: Wenn der *berechnete* (ungefilterte) Wert von height_percent ungleich des *zuletzt wirklich gesendeten* Werts ist.
        # `self._previous_shutter_height` speichert den *ungefilterten* Wert, der *zuletzt berechnet* wurde.
        # Wir müssen also `shutter_height_percent` mit dem Wert von `self._previous_shutter_height` *vor der Aktualisierung* der Höhe vergleichen.

        # Da wir self._previous_shutter_height *nach* dem Höhenbefehl aktualisieren,
        # MÜSSEN wir hier einen temporären Wert nutzen:
        height_was_different_before_height_update = (
                    self._previous_shutter_height != shutter_height_percent)

        # Sende Winkelbefehl, wenn der Wert sich ändert ODER wenn sich die Höhe geändert hat.
        if angle_to_set_percent != self._previous_shutter_angle or height_was_different_before_height_update:
            _LOGGER.debug(
                f"{self._name}: Sending angle {angle_to_set_percent}% to {self._target_cover_entity_id}. "
                f"Angle update: {angle_to_set_percent != self._previous_shutter_angle}. Height update: {height_was_different_before_height_update}")
            await self.hass.services.async_call(
                "cover",
                "set_tilt_position",
                {"entity_id": self._target_cover_entity_id, "tilt_position": angle_to_set_percent},
                blocking=False
            )
        else:
            _LOGGER.debug(
                f"{self._name}: Angle '{angle_to_set_percent}%' not sent, value was the same than before or has another restriction")

        self._previous_shutter_angle = shutter_angle_percent  # Immer mit dem NEUEN *berechneten* Wert aktualisieren

        # --- Neuen Sensor für Winkel in Grad publizieren ---
        self._calculated_angle_degrees = self._convert_shutter_angle_percent_to_degrees(
            angle_to_set_percent)
        # Wichtig: HA-Zustand aktualisieren, damit Attribute (inkl. calculated_angle_degrees) publiziert werden
        self.async_write_ha_state()

        # === Timer stoppen ===
        if stop_timer:
            _LOGGER.debug(f"{self._name}: Canceling timer")
            self._cancel_recalculation_timer()

        _LOGGER.debug(
            f"{self._name}: _position_shutter for height {shutter_height_percent}% and angle {shutter_angle_percent}% finished")

    # ... (Ihre _should_output_be_updated, _convert_shutter_angle_percent_to_degrees und _cancel_all_shadow_timers) ...
    # Denken Sie daran, dass _update_input_values auch in der Klasse sein muss.

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

    async def _is_dawn_active(self) -> bool:
        """Check if the current brightness is below the dawn threshold."""
        brightness_dawn = self._brightness_dawn
        dawn_threshold_close = self._dawn_brightness_level
        return (
            brightness_dawn is not None
            and dawn_threshold_close is not None
            and brightness_dawn < dawn_threshold_close
        )

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

    # #######################################################################
    # State handling starting here
    # 
    # =======================================================================
    # State SHADOW_FULL_CLOSE_TIMER_RUNNING
    async def _handle_state_shadow_full_close_timer_running(self) -> ShutterState:
        _LOGGER.debug(f"{self._name}: Handle SHADOW_FULL_CLOSE_TIMER_RUNNING")
        if await self._is_lbs_locked_in_either_way():
            _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING}: Integration locked, no action performed")
            return ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING

        if await self._check_if_facade_is_in_sun() and await self._is_shadow_handling_activated():
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
                        _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING}: Timer finished, brightness above threshold, moving to shadow position ({target_height}%, {target_angle}%). Next state: {ShutterState.SHADOW_FULL_CLOSED}")
                        return ShutterState.SHADOW_FULL_CLOSED
                    else:
                        _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING}: Error within calculation of height a/o angle, staying at {ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING}")
                        return ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING
                else:
                    _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING}: Waiting for timer (Brightness big enough)")
                    return ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING
            else:
                _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING}: Brightness ({current_brightness}) not above threshold ({shadow_threshold_close}), transitioning to {ShutterState.SHADOW_NEUTRAL}")
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
                _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING}: Not in the sun or shadow mode disabled, transitioning to ({neutral_height}%, {neutral_angle}%) with state {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL
            else:
                _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING}: Neutral height or angle not configured, transitioning to {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL

        # Entsprechung zu LB_LBSID_positionShutterWithPreviousValues
        _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING}: Staying at previous position.")
        return ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING

    # =======================================================================
    # State SHADOW_FULL_CLOSED
    async def _handle_state_shadow_full_closed(self) -> ShutterState:
        _LOGGER.debug(f"{self._name}: Handle SHADOW_FULL_CLOSED")
        if await self._is_lbs_locked_in_either_way():
            _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_FULL_CLOSED}: Integration locked, no action performed")
            return ShutterState.SHADOW_FULL_CLOSED

        if await self._check_if_facade_is_in_sun() and await self._is_shadow_handling_activated():
            current_brightness = self._brightness
            shadow_threshold_close = self._shadow_brightness_level
            shadow_open_slat_delay = self._shadow_look_through_seconds
            if (
                    current_brightness is not None
                    and shadow_threshold_close is not None
                    and shadow_open_slat_delay is not None
                    and current_brightness < shadow_threshold_close
            ):
                _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_FULL_CLOSED}: Brightness ({current_brightness}) below threshold ({shadow_threshold_close}), starting timer for {ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING} ({shadow_open_slat_delay}s)")
                await self._start_recalculation_timer(shadow_open_slat_delay)
                return ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING
            else:
                _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_FULL_CLOSED}: Brightness not below threshold, recalculating shadow position")
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
                _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_FULL_CLOSED}: Not in sun or shadow mode deactivated, moving to neutral position ({neutral_height}%, {neutral_angle}%) und state {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL
            else:
                _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_FULL_CLOSED}: Neutral height or angle not configured, moving to state {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL

        # Entsprechung zu LB_LBSID_positionShutterWithPreviousValues
        _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_FULL_CLOSED}: Staying at previous position")
        return ShutterState.SHADOW_FULL_CLOSED

    # =======================================================================
    # State SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING
    async def _handle_state_shadow_horizontal_neutral_timer_running(self) -> ShutterState:
        _LOGGER.debug(f"{self._name}: Handle SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING")
        if await self._is_lbs_locked_in_either_way():
            _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Integration locked, no action performed")
            return ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING

        if await self._check_if_facade_is_in_sun() and await self._is_shadow_handling_activated():
            current_brightness = self._brightness
            shadow_threshold_close = self._shadow_brightness_level
            shadow_open_slat_angle = self._shadow_look_through_angle
            if (
                    current_brightness is not None
                    and shadow_threshold_close is not None
                    and shadow_open_slat_angle is not None
                    and current_brightness > shadow_threshold_close
            ):
                _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Brightness ({current_brightness}) again above threshold ({shadow_threshold_close}), transitioning to {ShutterState.SHADOW_FULL_CLOSED} and stopping timer")
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
                        _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Timer finished, moving to height {target_height}% with neutral slats ({shadow_open_slat_angle}°) and state {ShutterState.SHADOW_HORIZONTAL_NEUTRAL}")
                        return ShutterState.SHADOW_HORIZONTAL_NEUTRAL
                    else:
                        _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Error during calculation of height and angle for open slats, staying at {ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING}")
                        return ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING
                else:
                    _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Waiting for timer (brightness not high enough)")
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
                _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Not in the sun or shadow mode disabled, moving to neutral position ({neutral_height}%, {neutral_angle}%) and state {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL
            else:
                _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Neutral height or angle not configured, transitioning to {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL

        # Entsprechung zu LB_LBSID_positionShutterWithPreviousValues
        _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Staying at previous position")
        return ShutterState.SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING

    # =======================================================================
    # State SHADOW_HORIZONTAL_NEUTRAL
    async def _handle_state_shadow_horizontal_neutral(self) -> ShutterState:
        _LOGGER.debug(f"{self._name}: Handle SHADOW_HORIZONTAL_NEUTRAL")
        if await self._is_lbs_locked_in_either_way():
            _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_HORIZONTAL_NEUTRAL}: Integration locked, no action performed")
            return ShutterState.SHADOW_HORIZONTAL_NEUTRAL

        if await self._check_if_facade_is_in_sun() and await self._is_shadow_handling_activated():
            current_brightness = self._brightness
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
                        stop_timer=False,
                    )
                    _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_HORIZONTAL_NEUTRAL}: Brightness ({current_brightness}) above threshold ({shadow_threshold_close}), moving to shadow position ({target_height}%, {target_angle}%) and state {ShutterState.SHADOW_FULL_CLOSED}")
                    return ShutterState.SHADOW_FULL_CLOSED
                else:
                    _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_HORIZONTAL_NEUTRAL}: Error at calculating height or angle, staying at {ShutterState.SHADOW_HORIZONTAL_NEUTRAL}")
                    return ShutterState.SHADOW_HORIZONTAL_NEUTRAL
            elif shadow_open_shutter_delay is not None:
                _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_HORIZONTAL_NEUTRAL}: Brightness not above threshold, starting timer for {ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING} ({shadow_open_shutter_delay}s)")
                await self._start_recalculation_timer(shadow_open_shutter_delay)
                return ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING
            else:
                _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_HORIZONTAL_NEUTRAL}: Brightness not above threshold and 'shadow_open_shutter_delay' not configured, staying at {ShutterState.SHADOW_HORIZONTAL_NEUTRAL}")
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
                _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_HORIZONTAL_NEUTRAL}: Not in sun or shadow mode disabled, moving to neutral position ({neutral_height}%, {neutral_angle}%) and state {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL
            else:
                _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_HORIZONTAL_NEUTRAL}: Neutral height or angle not configured, transitioning to {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL

        # Entsprechung zu LB_LBSID_positionShutterWithPreviousValues
        _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_HORIZONTAL_NEUTRAL}: Staying at previous position")
        return ShutterState.SHADOW_HORIZONTAL_NEUTRAL

    # =======================================================================
    # State SHADOW_NEUTRAL_TIMER_RUNNING
    async def _handle_state_shadow_neutral_timer_running(self) -> ShutterState:
        _LOGGER.debug(f"{self._name}: Handle SHADOW_NEUTRAL_TIMER_RUNNING")
        if await self._is_lbs_locked_in_either_way():
            _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING}: Integration locked, no action performed")
            return ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING

        if await self._check_if_facade_is_in_sun() and await self._is_shadow_handling_activated():
            current_brightness = self._brightness
            shadow_threshold_close = self._shadow_brightness_level
            height_after_shadow = self._after_shadow_height
            angle_after_shadow = self._after_shadow_angle
            if (
                    current_brightness is not None
                    and shadow_threshold_close is not None
                    and current_brightness > shadow_threshold_close
            ):
                _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING}: Brightness ({current_brightness}) again above threshold ({shadow_threshold_close}), state {ShutterState.SHADOW_FULL_CLOSED} and stopping timer")
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
                        _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING}: Timer finished, moving to after-shadow position ({height_after_shadow}%, {angle_after_shadow}°) and state {ShutterState.SHADOW_NEUTRAL}")
                        return ShutterState.SHADOW_NEUTRAL
                    else:
                        _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING}: Height or angle after shadow not configured, staying at {ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING}")
                        return ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING
                else:
                    _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING}: Waiting for timer (brightness not high enough)")
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
                _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING}: Not in sun or shadow mode disabled, moving to neutral position ({neutral_height}%, {neutral_angle}%) and state {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL
            else:
                _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING}: Neutral height or angle not configured, transitioning to {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL

        # Entsprechung zu LB_LBSID_positionShutterWithPreviousValues
        _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING}: Staying at previous position")
        return ShutterState.SHADOW_NEUTRAL_TIMER_RUNNING

    # =======================================================================
    # State SHADOW_NEUTRAL
    async def _handle_state_shadow_neutral(self) -> ShutterState:
        _LOGGER.debug(f"{self._name}: Handle SHADOW_NEUTRAL")
        if await self._is_lbs_locked_in_either_way():
            _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_NEUTRAL}: Integration locked, no action performed")
            return ShutterState.SHADOW_NEUTRAL

        if await self._check_if_facade_is_in_sun() and await self._is_shadow_handling_activated():
            current_brightness = self._brightness
            shadow_threshold_close = self._shadow_brightness_level
            dawn_handling_active = self._dawn_control_enabled
            dawn_brightness = self._brightness_dawn
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
                _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_NEUTRAL}: Brightness ({current_brightness}) above threshold ({shadow_threshold_close}), starting timer for {ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING} ({shadow_close_delay}s)")
                await self._start_recalculation_timer(shadow_close_delay)
                return ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING
            elif (
                    dawn_handling_active
                    and dawn_brightness is not None
                    and dawn_threshold_close is not None
                    and dawn_brightness < dawn_threshold_close
                    and dawn_close_delay is not None
            ):
                _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_NEUTRAL}: Dawn handling active and dawn-brighness ({dawn_brightness}) below threshold ({dawn_threshold_close}), starting timer for {ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING} ({dawn_close_delay}s)")
                await self._start_recalculation_timer(dawn_close_delay)
                return ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING
            elif height_after_shadow is not None and angle_after_shadow is not None:
                await self._position_shutter(
                    float(height_after_shadow),
                    float(angle_after_shadow),
                    shadow_position=False,
                    stop_timer=False,
                )
                _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_NEUTRAL}: Moving to after-shadow position ({height_after_shadow}%, {angle_after_shadow}%)")
                return ShutterState.SHADOW_NEUTRAL
            else:
                _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_NEUTRAL}: Height or angle after shadow not configured, staying at {ShutterState.SHADOW_NEUTRAL}")
                return ShutterState.SHADOW_NEUTRAL

        if await self._is_dawn_handling_activated():
            dawn_brightness = self._brightness_dawn
            dawn_threshold_close = self._dawn_brightness_level
            dawn_close_delay = self._dawn_after_seconds
            if (
                    dawn_brightness is not None
                    and dawn_threshold_close is not None
                    and dawn_brightness < dawn_threshold_close
                    and dawn_close_delay is not None
            ):
                _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_NEUTRAL}: Dawn mode active and brightness ({dawn_brightness}) below threshold ({dawn_threshold_close}), starting timer for {ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING} ({dawn_close_delay}s)")
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
            _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_NEUTRAL}: Not in sun or shadow mode disabled or dawn mode not active, moving to neutral position ({neutral_height}%, {neutral_angle}%) and state {ShutterState.NEUTRAL}")
            return ShutterState.NEUTRAL
        else:
            _LOGGER.debug(f"{self._name}: State {ShutterState.SHADOW_NEUTRAL}: Neutral height or angle not configured, transitioning to {ShutterState.NEUTRAL}")
            return ShutterState.NEUTRAL

    # =======================================================================
    # State NEUTRAL
    async def _handle_state_neutral(self) -> ShutterState:
        _LOGGER.debug(f"{self._name}: Handle NEUTRAL")
        if await self._is_lbs_locked_in_either_way():
            _LOGGER.debug(f"{self._name}: State {ShutterState.NEUTRAL}: Integration locked, no action performed"
            )
            return ShutterState.NEUTRAL

        if await self._check_if_facade_is_in_sun() and await self._is_shadow_handling_activated():
            _LOGGER.debug(f"{self._name}: self._check_if_facade_is_in_sun and self._is_shadow_handling_activated")
            current_brightness = self._brightness
            shadow_threshold_close = self._shadow_brightness_level
            shadow_close_delay = self._shadow_after_seconds
            if (
                current_brightness is not None
                and shadow_threshold_close is not None
                and current_brightness > shadow_threshold_close
                and shadow_close_delay is not None
            ):
                _LOGGER.debug(f"{self._name}: State {ShutterState.NEUTRAL}: Brightness ({current_brightness}) above dawn threshold ({shadow_threshold_close}), starting timer for {ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING} ({shadow_close_delay}s)")
                await self._start_recalculation_timer(shadow_close_delay)
                return ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING

        if await self._is_dawn_handling_activated():
            dawn_brightness = self._brightness_dawn
            dawn_threshold_close = self._dawn_brightness_level
            dawn_close_delay = self._dawn_after_seconds
            if (
                dawn_brightness is not None
                and dawn_threshold_close is not None
                and dawn_brightness < dawn_threshold_close
                and dawn_close_delay is not None
            ):
                _LOGGER.debug(f"{self._name}: State {ShutterState.NEUTRAL}: Dawn mode active and brightness ({dawn_brightness}) below dawn threshold ({dawn_threshold_close}), starting timer for {ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING} ({dawn_close_delay}s)")
                await self._start_recalculation_timer(dawn_close_delay)
                return ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING

        neutral_height = self._neutral_pos_height
        neutral_angle = self._neutral_pos_angle
        if neutral_height is not None and neutral_angle is not None:
            await self._position_shutter(
                float(neutral_height),
                float(neutral_angle),
                shadow_position=False,
                stop_timer=False,
            )
            _LOGGER.debug(f"{self._name}: State {ShutterState.NEUTRAL}: Moving shutter to neutral position ({neutral_height}%, {neutral_angle}%).")
        return ShutterState.NEUTRAL

    # =======================================================================
    # State DAWN_NEUTRAL
    async def _handle_state_dawn_neutral(self) -> ShutterState:
        _LOGGER.debug(f"{self._name}: Handle DAWN_NEUTRAL")
        if await self._is_lbs_locked_in_either_way():
            _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_NEUTRAL}: Integration locked, no action performed")
            return ShutterState.DAWN_NEUTRAL

        current_brightness = self._brightness

        shadow_handling_active = self._is_shadow_handling_activated()
        shadow_threshold_close = self._shadow_brightness_level
        shadow_close_delay = self._shadow_after_seconds

        dawn_handling_active = self._is_dawn_handling_activated()
        dawn_brightness = self._brightness_dawn
        dawn_threshold_close = self._dawn_brightness_level
        dawn_close_delay = self._dawn_after_seconds
        height_after_dawn = self._after_dawn_height
        angle_after_dawn = self._after_dawn_angle

        is_in_sun = self._check_if_facade_is_in_sun()
        neutral_height = self._neutral_pos_height
        neutral_angle = self._neutral_pos_angle

        if dawn_handling_active:
            if (
                    dawn_brightness is not None
                    and dawn_threshold_close is not None
                    and dawn_brightness < dawn_threshold_close
                    and dawn_close_delay is not None
            ):
                _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_NEUTRAL}: Dawn mode active and brightness ({dawn_brightness}) below dawn threshold ({dawn_threshold_close}), starting timer for {ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING} ({dawn_close_delay}s)")
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
                _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_NEUTRAL}: Within sun, shadow mode active and brightness ({current_brightness}) above shadow threshold ({shadow_threshold_close}), starting timer for {ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING} ({shadow_close_delay}s)")
                await self._start_recalculation_timer(shadow_close_delay)
                return ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING
            elif height_after_dawn is not None and angle_after_dawn is not None:
                await self._position_shutter(
                    float(height_after_dawn),
                    float(angle_after_dawn),
                    shadow_position=False,
                    stop_timer=False,
                )
                _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_NEUTRAL}: Moving shutter to after-dawn position ({height_after_dawn}%, {angle_after_dawn}%).")
                return ShutterState.DAWN_NEUTRAL
            else:
                _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_NEUTRAL}: Height or angle after dawn not configured, staying at {ShutterState.DAWN_NEUTRAL}")
                return ShutterState.DAWN_NEUTRAL

        if (
                is_in_sun
                and shadow_handling_active
                and current_brightness is not None
                and shadow_threshold_close is not None
                and current_brightness > shadow_threshold_close
                and shadow_close_delay is not None
        ):
            _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_NEUTRAL}: Within sun, shadow mode active and brightness ({current_brightness}) above shadow threshold ({shadow_threshold_close}), starting timer for {ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING} ({shadow_close_delay}s)")
            await self._start_recalculation_timer(shadow_close_delay)
            return ShutterState.SHADOW_FULL_CLOSE_TIMER_RUNNING

        if neutral_height is not None and neutral_angle is not None:
            await self._position_shutter(
                float(neutral_height),
                float(neutral_angle),
                shadow_position=False,
                stop_timer=True,  # Stop Timer (falls ein Timer aktiv war)
            )
            _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_NEUTRAL}: Dawn mode disabled or requirements for shadow not given, moving to neutral position ({neutral_height}%, {neutral_angle}%)")
            return ShutterState.NEUTRAL
        else:
            _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_NEUTRAL}: Neutral height or angle not configured, transitioning to {ShutterState.NEUTRAL}")
            return ShutterState.NEUTRAL

    # =======================================================================
    # State DAWN_NEUTRAL_TIMER_RUNNING
    async def _handle_state_dawn_neutral_timer_running(self) -> ShutterState:
        _LOGGER.debug(f"{self._name}: Handle DAWN_NEUTRAL_TIMER_RUNNING")
        if await self._is_lbs_locked_in_either_way():
            _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_NEUTRAL_TIMER_RUNNING}: Integration locked, no action performed")
            return ShutterState.DAWN_NEUTRAL_TIMER_RUNNING

        if await self._is_dawn_handling_activated():
            dawn_brightness = self._brightness_dawn
            dawn_threshold_close = self._dawn_brightness_level
            dawn_height = self._dawn_max_height
            dawn_open_slat_angle = self._dawn_look_through_angle

            if (
                    dawn_brightness is not None
                    and dawn_threshold_close is not None
                    and dawn_brightness < dawn_threshold_close
            ):
                _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_NEUTRAL_TIMER_RUNNING}: Dawn brightness ({dawn_brightness}) again below threshold ({dawn_threshold_close}), moving to {ShutterState.DAWN_FULL_CLOSED} and stopping timer")
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
                        _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_NEUTRAL_TIMER_RUNNING}: Timer finished, moving to dawn height ({dawn_height}%) with open slats ({dawn_open_slat_angle}°) and state {ShutterState.DAWN_NEUTRAL}")
                        return ShutterState.DAWN_NEUTRAL
                    else:
                        _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_NEUTRAL_TIMER_RUNNING}: Dawn height or angle for open slats not configured, staying at {ShutterState.DAWN_NEUTRAL_TIMER_RUNNING}")
                        return ShutterState.DAWN_NEUTRAL_TIMER_RUNNING
                else:
                    _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_NEUTRAL_TIMER_RUNNING}: Waiting for timer (brightness not low enough)")
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
                _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_NEUTRAL_TIMER_RUNNING}: Dawn mode disabled, moving to neutral position ({neutral_height}%, {neutral_angle}%) and state {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL
            else:
                _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_NEUTRAL_TIMER_RUNNING}: Neutral height or angle not configured, transitioning to {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL

        # Entsprechung zu LB_LBSID_positionShutterWithPreviousValues
        _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_NEUTRAL_TIMER_RUNNING}: Staying at previous position")
        return ShutterState.DAWN_NEUTRAL_TIMER_RUNNING

    # =======================================================================
    # State DAWN_HORIZONTAL_NEUTRAL
    async def _handle_state_dawn_horizontal_neutral(self) -> ShutterState:
        _LOGGER.debug(f"{self._name}: Handle DAWN_HORIZONTAL_NEUTRAL")
        if await self._is_lbs_locked_in_either_way():
            _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_HORIZONTAL_NEUTRAL}: Integration locked, no action performed")
            return ShutterState.DAWN_HORIZONTAL_NEUTRAL

        if await self._is_dawn_handling_activated():
            dawn_brightness = self._brightness_dawn
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
                _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_HORIZONTAL_NEUTRAL}: Dawn brightness ({dawn_brightness}) below threshold ({dawn_threshold_close}), moving to dawn height ({dawn_height}%) with open slats ({dawn_open_slat_angle}°) and state {ShutterState.DAWN_FULL_CLOSED}")
                return ShutterState.DAWN_FULL_CLOSED
            elif dawn_open_shutter_delay is not None:
                _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_HORIZONTAL_NEUTRAL}: Dawn brightness not below threshold, starting timer for {ShutterState.DAWN_NEUTRAL_TIMER_RUNNING} ({dawn_open_shutter_delay}s)")
                await self._start_recalculation_timer(dawn_open_shutter_delay)
                return ShutterState.DAWN_NEUTRAL_TIMER_RUNNING
            else:
                _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_HORIZONTAL_NEUTRAL}: Dawn brightness not below threshold and 'dawn_open_shutter_delay' not configured, staying at {ShutterState.DAWN_HORIZONTAL_NEUTRAL}")
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
                _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_HORIZONTAL_NEUTRAL}: Dawn mode disabled, moving to neutral position ({neutral_height}%, {neutral_angle}%) and state {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL
            else:
                _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_HORIZONTAL_NEUTRAL}: Neutral height or angle not configured, transitioning to {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL

        # Entsprechung zu LB_LBSID_positionShutterWithPreviousValues
        _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_HORIZONTAL_NEUTRAL}: Staying at previous position")
        return ShutterState.DAWN_HORIZONTAL_NEUTRAL

    # =======================================================================
    # State DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING
    async def _handle_state_dawn_horizontal_neutral_timer_running(self) -> ShutterState:
        _LOGGER.debug(f"{self._name}: Handle DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING")
        if await self._is_lbs_locked_in_either_way():
            _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Integration locked, no action performed")
            return ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING

        if await self._is_dawn_handling_activated():
            dawn_brightness = self._brightness_dawn
            dawn_threshold_close = self._dawn_brightness_level
            dawn_height = self._dawn_max_height
            dawn_open_slat_angle = self._dawn_look_through_angle
            if (
                    dawn_brightness is not None
                    and dawn_threshold_close is not None
                    and dawn_brightness < dawn_threshold_close
            ):
                _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Dawn brightness ({dawn_brightness}) again below threshold ({dawn_threshold_close}), moving to {ShutterState.DAWN_FULL_CLOSED} and stopping timer")
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
                        _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Timer finished, moving to dawn height ({dawn_height}%) with open slats ({dawn_open_slat_angle}°) and state {ShutterState.DAWN_HORIZONTAL_NEUTRAL}")
                        return ShutterState.DAWN_HORIZONTAL_NEUTRAL
                    else:
                        _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Dawn height or angle for open slats not configured, staying at {ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING}")
                        return ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING
                else:
                    _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Waiting for timer (brightness not low enough)")
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
                _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Dawn mode disabled, moving to neutral position ({neutral_height}%, {neutral_angle}%) and state {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL
            else:
                _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Neutral height or angle not configured, transitioning to {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL

        # Entsprechung zu LB_LBSID_positionShutterWithPreviousValues
        _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Staying at previous position")
        return ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING

    # =======================================================================
    # State DAWN_FULL_CLOSED
    async def _handle_state_dawn_full_closed(self) -> ShutterState:
        _LOGGER.debug(f"{self._name}: Handle DAWN_FULL_CLOSED")
        if await self._is_lbs_locked_in_either_way():
            _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_FULL_CLOSED}: Integration locked, no action performed")
            return ShutterState.DAWN_FULL_CLOSED

        if await self._is_dawn_handling_activated():
            dawn_brightness = self._brightness_dawn
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
                _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_FULL_CLOSED}: Dawn brightness ({dawn_brightness}) above threshold ({dawn_threshold_close}), starting timer for {ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING} ({dawn_open_slat_delay}s)")
                await self._start_recalculation_timer(dawn_open_slat_delay)
                return ShutterState.DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING
            elif dawn_height is not None and dawn_angle is not None:
                await self._position_shutter(
                    float(dawn_height),
                    float(dawn_angle),
                    shadow_position=False,
                    stop_timer=False,
                )
                _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_FULL_CLOSED}: Dawn brightness not above threshold, moving to dawn position ({dawn_height}%, {dawn_angle}%)")
                return ShutterState.DAWN_FULL_CLOSED
            else:
                _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_FULL_CLOSED}: Dawn height or angle not configured, staying at {ShutterState.DAWN_FULL_CLOSED}")
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
                _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_FULL_CLOSED}: Dawn handling disabled, moving to neutral position ({neutral_height}%, {neutral_angle}%) and state {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL
            else:
                _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_FULL_CLOSED}: Neutral height or angle not configured, transitioning to {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL

        # Entsprechung zu LB_LBSID_positionShutterWithPreviousValues
        _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_FULL_CLOSED}: Staying at previous position")
        return ShutterState.DAWN_FULL_CLOSED

    # =======================================================================
    # State DAWN_FULL_CLOSE_TIMER_RUNNING
    async def _handle_state_dawn_full_close_timer_running(self) -> ShutterState:
        _LOGGER.debug(f"{self._name}: Handle DAWN_FULL_CLOSE_TIMER_RUNNING")
        if await self._is_lbs_locked_in_either_way():
            _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING}: Integration locked, no action performed")
            return ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING

        if await self._is_dawn_handling_activated():
            dawn_brightness = self._brightness_dawn
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
                        _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING}: Timer finished, moving to dawn position ({dawn_height}%, {dawn_angle}%) and state {ShutterState.DAWN_FULL_CLOSED}")
                        return ShutterState.DAWN_FULL_CLOSED
                    else:
                        _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING}: Dawn height or angle not configured, staying at {ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING}")
                        return ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING
                else:
                    _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING}: Waiting for timer (brightness low enough)")
                    return ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING
            else:
                _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING}: Brightness ({dawn_brightness}) not below threshold ({dawn_threshold_close}), moving to {ShutterState.DAWN_NEUTRAL} and stopping timer")
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
                _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING}: Dawn mode disabled, moving to neutral position ({neutral_height}%, {neutral_angle}%) and state {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL
            else:
                _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING}: Neutral height or angle not configured, transitioning to {ShutterState.NEUTRAL}")
                return ShutterState.NEUTRAL

        # Entsprechung zu LB_LBSID_positionShutterWithPreviousValues
        _LOGGER.debug(f"{self._name}: State {ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING}: Staying at previous position")
        return ShutterState.DAWN_FULL_CLOSE_TIMER_RUNNING

    # End of state handling
    # #######################################################################

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
        # Stellen Sie sicher, dass _min_slat_angle_entity_id und _angle_offset_entity_id
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
            _LOGGER.debug(
                f"{self._name}: _should_output_be_updated: previous_value is None. Returning new value ({new_value})")
            return new_value

        # Überprüfen Sie, ob sich der Wert überhaupt geändert hat,
        # bevor Sie die komplexere Logik anwenden.
        # Eine kleine Toleranz kann hier sinnvoll sein, um unnötige Bewegungen zu vermeiden.
        # Home Assistant filtert oft schon, aber eine explizite Prüfung ist gut.
        if abs(new_value - previous_value) < 0.001:  # Kleine Toleranz für Floating Point Vergleiche
            _LOGGER.debug(
                f"{self._name}: _should_output_be_updated: new_value ({new_value}) is nearly identical to previous_value ({previous_value}). Returning previous_value")
            return previous_value

        _LOGGER.debug(
            f"{self._name}: _should_output_be_updated: config_value={config_value.name}, new_value={new_value}, previous_value={previous_value}")

        if config_value == MovementRestricted.ONLY_CLOSE:
            if new_value > previous_value:
                _LOGGER.debug(
                    f"{self._name}: _should_output_be_updated: ONLY_DOWN -> new_value ({new_value}) > previous_value ({previous_value}). Returning new_value")
                return new_value
            else:
                _LOGGER.debug(
                    f"{self._name}: _should_output_be_updated: ONLY_DOWN -> new_value ({new_value}) <= previous_value ({previous_value}). Returning previous_value")
                return previous_value
        elif config_value == MovementRestricted.ONLY_OPEN:
            if new_value < previous_value:
                _LOGGER.debug(
                    f"{self._name}: _should_output_be_updated: ONLY_UP -> new_value ({new_value}) < previous_value ({previous_value}). Returning new_value")
                return new_value
            else:
                _LOGGER.debug(
                    f"{self._name}: _should_output_be_updated: ONLY_UP -> new_value ({new_value}) >= previous_value ({previous_value}). Returning previous_value")
                return previous_value
        elif config_value == MovementRestricted.NO_RESTRICTION:
            _LOGGER.debug(
                f"{self._name}: _should_output_be_updated: NO_RESTRICTION -> Returning new_value ({new_value})")
            return new_value
        else:
            # Für alle anderen (unbekannten) config_values, geben wir den previous_value zurück
            # oder den new_value, je nachdem, wie Sie die "default" in PHP interpretieren.
            # Die PHP "default" ist "return $newValue;", also lassen wir das auch hier so.
            _LOGGER.warning(
                f"{self._name}: _should_output_be_updated: Unknown value '{config_value.name}'. Returning new_value ({new_value})")
            return new_value
