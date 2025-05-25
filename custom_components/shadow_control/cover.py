"""Platform for Shadow Control integration."""

from __future__ import annotations

import logging
import math
from typing import Any, Awaitable, Callable, Optional

import voluptuous as vol
from homeassistant.components.cover import CoverEntity, CoverEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, STATE_ON, STATE_OFF, STATE_UNAVAILABLE, STATE_UNKNOWN 
from homeassistant.core import Event, HomeAssistant, callback, State
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event
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
    _LOGGER.info("Setting up Shadow Control platform from YAML - WIRD AUSGEFÜHRT!") # <--- HINZUGEFÜGT
    _LOGGER.debug(f"Configuration from YAML: {config}") # Zur Überprüfung der Konfigurationsdaten

    name = config.get(CONF_NAME, DEFAULT_NAME)
    target_cover_entity_id = config.get(CONF_TARGET_COVER_ENTITY_ID)

    if not target_cover_entity_id:
        _LOGGER.error(f"[{name}] Missing required configuration key '{CONF_TARGET_COVER_ENTITY_ID}'")
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

    # Initialisiere _attr_extra_state_attributes hier, damit es immer ein Dictionary ist
    # und Home Assistant es als persistierbares Attribut erkennt.
    _attr_extra_state_attributes: dict[str, Any] = {}

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

        _LOGGER.debug(f"Initializing Shadow Control: {self._name}")

        # Die Entity ID, unter der diese Entität in HA erscheinen wird
        self._attr_unique_id = f"shadow_control_{self._name.lower().replace(' ', '_')}"
        self.entity_id = f"cover.{self._attr_unique_id}" # Wichtig, um die Entität eindeutig zu machen

        # Entity ID des zu steuernden Behangs
        self._target_cover_entity_id = target_cover_entity_id

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

        # Logging der (fest verdrahteten) Entitäts-IDs
        _LOGGER.debug(f"--- Integration '{self._name}' initialized with fixed Entity IDs ---")

        # Define dictionary with all state handlers
        self._state_handlers: dict[ShutterState, Callable[[], Awaitable[ShutterState]]] = {
            ShutterState.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING: self._handle_state_shadow_full_close_timer_running,
            ShutterState.STATE_SHADOW_FULL_CLOSED: self._handle_state_shadow_full_closed,
            ShutterState.STATE_SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING: self._handle_state_shadow_horizontal_neutral_timer_running,
            ShutterState.STATE_SHADOW_HORIZONTAL_NEUTRAL: self._handle_state_shadow_horizontal_neutral,
            ShutterState.STATE_SHADOW_NEUTRAL_TIMER_RUNNING: self._handle_state_shadow_neutral_timer_running,
            ShutterState.STATE_SHADOW_NEUTRAL: self._handle_state_shadow_neutral,
            ShutterState.STATE_NEUTRAL: self._handle_state_neutral,
            ShutterState.STATE_DAWN_NEUTRAL: self._handle_state_dawn_neutral,
            ShutterState.STATE_DAWN_NEUTRAL_TIMER_RUNNING: self._handle_state_dawn_neutral_timer_running,
            ShutterState.STATE_DAWN_HORIZONTAL_NEUTRAL: self._handle_state_dawn_horizontal_neutral,
            ShutterState.STATE_DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING: self._handle_state_dawn_horizontal_neutral_timer_running,
            ShutterState.STATE_DAWN_FULL_CLOSED: self._handle_state_dawn_full_closed,
            ShutterState.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING: self._handle_state_dawn_full_close_timer_running,
        }

        # Interne persistente Variablen
        # Werden beim Start aus den persistenten Attributen gelesen.
        self._current_shutter_state: ShutterState = ShutterState.STATE_NEUTRAL # Standardwert setzen
        self._current_lock_state: LockState = LockState.LOCKSTATE__UNLOCKED # Standardwert setzen
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
                    self._current_shutter_state = ShutterState.STATE_NEUTRAL
            else:
                self._current_shutter_state = ShutterState.STATE_NEUTRAL
                _LOGGER.debug(f"{self._name}: 'current_shutter_state' not found in last state. Initializing to {self._current_shutter_state}")
        else:
            self._current_shutter_state = ShutterState.STATE_NEUTRAL
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
            _LOGGER.warning(f"{self._name}: No valid trigger entities configured. Recalculation will only happen on initial load.")

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
        _LOGGER.debug(f"{self._name}: Aktualisiere alle Eingangswerte.")

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
                        _LOGGER.debug(f"{self._name}: Bewegungsbeschränkung Höhe gesetzt auf: {self._movement_restriction_height.name} (Value: {state_obj.state})")
                        break
                else: # Wenn die Schleife ohne break beendet wird (Wert nicht gefunden)
                    _LOGGER.warning(f"{self._name}: Unbekannte Option für {height_restriction_entity_id}: '{state_obj.state}'. Setze auf NO_RESTRICTION.")
                    self._movement_restriction_height = MovementRestricted.NO_RESTRICTION
            else:
                _LOGGER.warning(f"{self._name}: Zustand für {height_restriction_entity_id} nicht verfügbar oder leer. Setze auf NO_RESTRICTION.")
                self._movement_restriction_height = MovementRestricted.NO_RESTRICTION
        else:
            _LOGGER.warning(f"{self._name}: Konfiguration für '{CONF_MOVEMENT_RESTRICTION_HEIGHT_ENTITY_ID}' fehlt. Setze auf NO_RESTRICTION.")
            self._movement_restriction_height = MovementRestricted.NO_RESTRICTION
        #self._movement_restriction_angle = self._get_entity_string_state(self._movement_restriction_angle_entity_id)
        angle_restriction_entity_id = self._config.get(CONF_MOVEMENT_RESTRICTION_ANGLE_ENTITY_ID)
        if angle_restriction_entity_id:
            state_obj = self.hass.states.get(angle_restriction_entity_id)
            if state_obj and state_obj.state:
                for restriction_type in MovementRestricted:
                    if restriction_type.value == state_obj.state:
                        self._movement_restriction_angle = restriction_type
                        _LOGGER.debug(f"{self._name}: Bewegungsbeschränkung Winkel gesetzt auf: {self._movement_restriction_angle.name} (Value: {state_obj.state})")
                        break
                else:
                    _LOGGER.warning(f"{self._name}: Unbekannte Option für {angle_restriction_entity_id}: '{state_obj.state}'. Setze auf NO_RESTRICTION.")
                    self._movement_restriction_angle = MovementRestricted.NO_RESTRICTION
            else:
                _LOGGER.warning(f"{self._name}: Zustand für {angle_restriction_entity_id} nicht verfügbar oder leer. Setze auf NO_RESTRICTION.")
                self._movement_restriction_angle = MovementRestricted.NO_RESTRICTION
        else:
            _LOGGER.warning(f"{self._name}: Konfiguration für '{CONF_MOVEMENT_RESTRICTION_ANGLE_ENTITY_ID}' fehlt. Setze auf NO_RESTRICTION.")
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

        # Optional: Logging der aktualisierten Werte zur Fehlersuche
        _LOGGER.debug(
            f"{self._name}: Aktualisierte Werte (Auszug): "
            f"Brightness={self._brightness}, "
            f"Elevation={self._sun_elevation}, "
            f"ShadowEnabled={self._shadow_control_enabled}"
            # ... weitere Werte nach Bedarf ...
        )

        # === Priorisierung des internen LockState ===
        # Wenn CONF_LOCK_INTEGRATION_WITH_POSITION_ENTITY_ID (höchste Priorität) "on" ist
        if self._lock_integration_with_position:
            self._current_lock_state = LockState.LOCKSTATE__LOCKED_MANUALLY_WITH_FORCED_POSITION
            _LOGGER.debug(f"{self._name}: LockState set to LOCKSTATE__LOCKED_MANUALLY_WITH_FORCED_POSITION due to '{self._lock_integration_with_position_entity_id}' being ON.")
        # Wenn CONF_LOCK_INTEGRATION_ENTITY_ID "on" ist (und die höhere Priorität nicht greift)
        elif self._lock_integration:
            self._current_lock_state = LockState.LOCKSTATE__LOCKED_MANUALLY
            _LOGGER.debug(f"{self._name}: LockState set to LOCKSTATE__LOCKED_MANUALLY due to '{self._lock_integration_entity_id}' being ON.")
        # Ansonsten bleibt es UNLOCKED (oder ein anderer Standardwert, den Sie festgelegt haben)

        # Optional: Weitere LockStates wie LOCKSTATE__LOCKED_BY_EXTERNAL_MODIFICATION
        # elif self._is_external_modification_detected: # Pseudo-Variable
        #    self._current_lock_state = LockState.LOCKSTATE__LOCKED_BY_EXTERNAL_MODIFICATION
        #    _LOGGER.debug(f"{self._name}: LockState set to LOCKSTATE__LOCKED_BY_EXTERNAL_MODIFICATION.")

        else:
            # Standardmässig ist der Zustand ungesperrt
            self._current_lock_state = LockState.LOCKSTATE__UNLOCKED
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
        _LOGGER.debug(f"{self._name}: Aktueller Behangzustand vor der Verarbeitung: {self._current_shutter_state.name} ({self._current_shutter_state.value})")

        handler_func = self._state_handlers.get(self._current_shutter_state)
        new_shutter_state: ShutterState

        if handler_func:
            # Rufe die entsprechende Handler-Methode auf
            new_shutter_state = await handler_func()
        else:
            # Standardfall: Wenn der Zustand nicht im Dictionary gefunden wird
            _LOGGER.warning(f"{self._name}: Shutter ist in einem undefinierten Zustand ({self._current_shutter_state}). Setze auf NEUTRAL ({ShutterState.STATE_NEUTRAL.value}).")
            new_shutter_state = await self._handle_state_neutral() # Ruft den Handler für NEUTRAL auf

        # Aktualisiere den internen Behangzustand
        self._current_shutter_state = new_shutter_state
        _LOGGER.debug(f"{self._name}: Neuer Behangzustand nach der Verarbeitung: {self._current_shutter_state.name} ({self._current_shutter_state.value})")

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
                _LOGGER.warning(f"Could not parse position from {self._shutter_current_height_entity_id}: {height_state.state}")
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
                _LOGGER.warning(f"Could not parse tilt position from {self._shutter_current_angle_entity_id}: {angle_state.state}")
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
        return not self._current_lock_state == LockState.LOCKSTATE__UNLOCKED

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

    async def _start_timer(self, delay: float) -> None:
        """Start a timer that finishes after the given delay in seconds."""
        self._timer_finish_time = self.hass.loop.time() + delay
        _LOGGER.debug(f"Timer started for {delay} seconds. Finish time: {self._timer_finish_time}")

    async def _is_timer_finished(self) -> bool:
        """Check if the current time is after the timer finish time."""
        return self.hass.loop.time() >= self._timer_finish_time

    async def _stop_timer(self) -> None:
        """Stop the active timer."""
        self._timer_finish_time = 0
        _LOGGER.debug("Timer stopped.")

    def _calculate_shutter_height(self) -> float:
        """
        Berechnet die Zielhöhe des Rolladens basierend auf Sonnenstand und
        Konfiguration für den Beschattungsbereich.
        Gibt die berechnete Höhe in Prozent (0-100) zurück.
        """
        _LOGGER.debug(f"{self._name}: Starte Berechnung der Rolladenhöhe.")

        width_of_light_strip = self._light_bar_width
        shadow_max_height_percent = self._shadow_max_height
        elevation = self._sun_elevation
        shutter_overall_height = self._shutter_height

        # Initialer Rückgabewert, falls Berechnung nicht möglich ist oder Bedingungen nicht erfüllt sind
        # Hier wird der Standardwert shadow_max_height_percent gesetzt
        shutter_height_to_set_percent = shadow_max_height_percent

        # Prüfen auf None-Werte, bevor mit Berechnungen begonnen wird
        if (
                width_of_light_strip is None
                or elevation is None
                or shutter_overall_height is None
                or shadow_max_height_percent is None  # Muss auch None-geprüft werden
        ):
            _LOGGER.warning(
                f"{self._name}: Nicht alle erforderlichen Werte für die Höhenberechnung verfügbar. "
                f"width_of_light_strip={width_of_light_strip}, elevation={elevation}, "
                f"shutter_overall_height={shutter_overall_height}, "
                f"shadow_max_height_percent={shadow_max_height_percent}. "
                f"Gebe initialen Standardwert von {shutter_height_to_set_percent}% zurück.")
            # Rückgabe des Standardwerts oder eines Fehlerwerts, je nach gewünschtem Verhalten
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
                    f"{self._name}: Elevation: {elevation}°, Fensterhöhe: {shutter_overall_height}, "
                    f"Lichtstreifenbreite: {width_of_light_strip}, "
                    f"resultierende Rolladenhöhe (von unten): {shutter_height_to_set} (entspricht {shutter_height_to_set_percent}% von oben). "
                    f"Ist kleiner als max. Höhe.")
            else:
                _LOGGER.debug(
                    f"{self._name}: Elevation: {elevation}°, Fensterhöhe: {shutter_overall_height}, "
                    f"Lichtstreifenbreite: {width_of_light_strip}, "
                    f"resultierende Rolladenhöhe ({new_shutter_height}%) ist größer oder gleich als gegebene max. Höhe ({shadow_max_height_percent}%). "
                    f"Verwende gegebene max. Höhe.")
                # shutter_height_to_set_percent behält seinen initialen Wert von shadow_max_height_percent
        else:
            _LOGGER.debug(
                f"{self._name}: width_of_light_strip ist 0. Keine Höhenberechnung notwendig. "
                f"Verwende Standardwert für Rolladenhöhe: {shutter_height_to_set_percent}%.")

        # Der Aufruf zu LB_LBSID_handleShutterHeightStepping($E, $shutterHeightToSetPercent)
        # wird hier durch einen Aufruf der entsprechenden Python-Methode ersetzt.
        # Nehmen wir an, diese Methode heißt _handle_shutter_height_stepping
        return self._handle_shutter_height_stepping(shutter_height_to_set_percent)

    # Sie müssen dann die Methode _handle_shutter_height_stepping implementieren:
    def _handle_shutter_height_stepping(self, calculated_height_percent: float) -> float:
        """
        Passt die berechnete Rolladenhöhe an das vorgegebene Stepping an.
        Dies ist eine Platzhalterfunktion. Implementieren Sie die tatsächliche Logik hier.
        """
        _LOGGER.debug(
            f"{self._name}: Bearbeite Rolladenhöhe Stepping für {calculated_height_percent}%.")
        # Hier würde die Logik für das Stepping stattfinden, z.B.:
        # stepping = self._stepping_height # Annahme, dass dies eine Instanzvariable ist
        # if stepping and stepping > 0:
        #    return round(calculated_height_percent / stepping) * stepping
        return calculated_height_percent  # Vorerst einfach den Wert zurückgeben

    def _calculate_shutter_angle(self) -> float:
        """
        Berechnet den Zielwinkel der Lamellen, um Sonneneinstrahlung zu verhindern.
        Gibt den berechneten Winkel in Prozent (0-100) zurück.
        """
        _LOGGER.debug(f"{self._name}: Starte Berechnung des Rolladenwinkels.")

        # Entsprechende Instanzvariablen aus _update_input_values
        elevation = self._sun_elevation
        azimuth = self._sun_azimuth  # Für Logging verwendet
        given_shutter_slat_width = self._slat_width
        shutter_slat_distance = self._slat_distance
        shutter_angle_offset = self._angle_offset
        min_shutter_angle_percent = self._min_slat_angle
        max_shutter_angle_percent = self._shadow_max_angle
        shutter_type_str = self._shutter_type  # String wie "90_degree_slats" oder "180_degree_slats"

        # Der effektive Elevationswinkel kommt aus der Instanzvariable, die von _check_if_facade_is_in_sun gesetzt wird
        effective_elevation = self._effective_elevation

        # --- Prüfen auf None-Werte ---
        if (
                elevation is None or azimuth is None
                or given_shutter_slat_width is None or shutter_slat_distance is None
                or shutter_angle_offset is None or min_shutter_angle_percent is None
                or max_shutter_angle_percent is None or shutter_type_str is None
                or effective_elevation is None
        ):
            _LOGGER.warning(
                f"{self._name}: Nicht alle erforderlichen Werte für die Winkelberechnung verfügbar. "
                f"elevation={elevation}, azimuth={azimuth}, "
                f"slat_width={given_shutter_slat_width}, slat_distance={shutter_slat_distance}, "
                f"angle_offset={shutter_angle_offset}, min_angle={min_shutter_angle_percent}, "
                f"max_angle={max_shutter_angle_percent}, shutter_type={shutter_type_str}, "
                f"effective_elevation={effective_elevation}. Gebe 0.0 zurück.")
            return 0.0  # Standardwert bei fehlenden Daten

        # --- Mathematische Berechnungen basierend auf dem schiefen Dreieck ---

        # $alpha is the opposit angle of shutter slat width, so this is the difference
        # between $GLOBALS["LB_LBSID_INTERNAL__effectiveElevation"] and vertical
        alpha_deg = 90 - effective_elevation
        alpha_rad = math.radians(alpha_deg)

        # $beta is the opposit angle of shutter slat distance
        asin_arg = (math.sin(alpha_rad) * shutter_slat_distance) / given_shutter_slat_width

        # Schutz vor domain error für asin() wenn Argument > 1 oder < -1
        if not (-1 <= asin_arg <= 1):
            _LOGGER.warning(
                f"{self._name}: Argument für asin() ausserhalb des gültigen Bereichs ({-1 <= asin_arg <= 1}). "
                f"Aktueller Wert: {asin_arg}. Kann Winkel nicht berechnen. Gebe 0.0 zurück.")
            return 0.0

        beta_rad = math.asin(asin_arg)
        beta_deg = math.degrees(beta_rad)

        # $gamma is the angle between vertical and shutter slat
        gamma_deg = 180 - alpha_deg - beta_deg

        # $shutterAnglePercent is the difference between horizontal and shutter slat,
        # so this is the result of the calculation
        shutter_angle_degrees = round(90 - gamma_deg)

        _LOGGER.debug(f"{self._name}: Elevation/Azimut: {elevation}°/{azimuth}°, "
                      f"resultierende effektive Elevation und Rollladenwinkel: "
                      f"{effective_elevation}°/{shutter_angle_degrees}° (ohne Stepping und Offset)")

        # --- Anpassung basierend auf Rollladentyp (90° oder 180° Lamellen) ---
        shutter_angle_percent: float
        if shutter_type_str == "90_degree_slats":
            shutter_angle_percent = shutter_angle_degrees / 0.9
        elif shutter_type_str == "180_degree_slats":
            shutter_angle_percent = shutter_angle_degrees / 1.8 + 50
        else:
            _LOGGER.warning(
                f"{self._name}: Unbekannter Rollladentyp '{shutter_type_str}'. Verwende Standard (90°).")
            shutter_angle_percent = shutter_angle_degrees / 0.9  # Standardverhalten

        # Sicherstellen, dass der Winkel nicht negativ wird
        if shutter_angle_percent < 0:
            shutter_angle_percent = 0.0

        # Runden vor dem Stepping, wie im PHP-Code
        shutter_angle_percent_rounded_for_stepping = round(shutter_angle_percent)

        # --- Anwendung des Winkel-Steppings ---
        # Diese Methode (_handle_shutter_angle_stepping) muss noch implementiert werden
        shutter_angle_percent_with_stepping = self._handle_shutter_angle_stepping(
            shutter_angle_percent_rounded_for_stepping)

        # --- Hinzufügen des konfigurierten Offsets ---
        shutter_angle_percent_with_stepping += shutter_angle_offset

        # --- Begrenzung des Winkels auf Min/Max-Werte ---
        if shutter_angle_percent_with_stepping < min_shutter_angle_percent:
            final_shutter_angle_percent = min_shutter_angle_percent
            _LOGGER.debug(
                f"{self._name}: Begrenze Winkel auf Minimum: {min_shutter_angle_percent}%")
        elif shutter_angle_percent_with_stepping > max_shutter_angle_percent:
            final_shutter_angle_percent = max_shutter_angle_percent
            _LOGGER.debug(
                f"{self._name}: Begrenze Winkel auf Maximum: {max_shutter_angle_percent}%")
        else:
            final_shutter_angle_percent = shutter_angle_percent_with_stepping

        # Endgültiges Runden des finalen Winkels
        final_shutter_angle_percent = round(final_shutter_angle_percent)

        _LOGGER.debug(
            f"{self._name}: Resultierender Rollladenwinkel mit Offset und Stepping: {final_shutter_angle_percent}%")
        return float(final_shutter_angle_percent)  # Sicherstellen, dass es ein Float zurückgibt

    def _handle_shutter_angle_stepping(self, calculated_angle_percent: float) -> float:
        """
        Passt den berechneten Lamellenwinkel an das vorgegebene Stepping an.
        """
        _LOGGER.debug(
            f"{self._name}: Bearbeite Lamellenwinkel Stepping für {calculated_angle_percent}%.")

        # Entsprechende Instanzvariable für die Schrittweite
        # Stellen Sie sicher, dass self._stepping_angle in _update_input_values gefüllt wird!
        shutter_stepping_percent = self._stepping_angle

        # Prüfen auf None-Werte für die Schrittweite
        if shutter_stepping_percent is None:
            _LOGGER.warning(
                f"{self._name}: 'stepping_angle' ist None. Stepping kann nicht angewendet werden. Gebe ursprünglichen Winkel {calculated_angle_percent}% zurück.")
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
                    f"{self._name}: Angewendetes Stepping: von {calculated_angle_percent}% auf {adjusted_angle}%. Schrittweite: {shutter_stepping_percent}%.")
                return adjusted_angle

        # Wenn kein Stepping angewendet werden muss oder shutter_stepping_percent 0 ist
        _LOGGER.debug(
            f"{self._name}: Kein Stepping nötig oder Stepping ist 0. Gebe ursprünglichen Winkel {calculated_angle_percent}% zurück.")
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
            f"{self._name}: Starte _position_shutter mit Höhe: {shutter_height_percent}%, Winkel: {shutter_angle_percent}%.")

        # Prüfung auf den initialen Lauf
        if self._is_initial_run:
            _LOGGER.debug(
                f"{self._name}: Initialer Lauf der LBS, aktualisiere Ausgänge nicht direkt (nur interne Variablen).")
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
        if self._current_lock_state != LockState.LOCKSTATE__UNLOCKED:
            _LOGGER.debug(
                f"{self._name}: LBS gesperrt ({self._current_lock_state.name}), aktualisiere Ausgänge nicht.")
            return

        # === ProduceShadow als Binary Sensor steuern ===
        # Dies ist der Part für LB_LBSID_sendByChange(LB_LBSID_OUTPUT_ProduceShadow, $shadowPosition);
        # Nur senden, wenn sich der Zustand ändert
        if self._is_producing_shadow != shadow_position:
            binary_sensor_entity_id = f"input_boolean.{self._name.lower().replace(' ', '_')}_shadow_active"
            _LOGGER.debug(
                f"{self._name}: Aktualisiere Binary Sensor '{binary_sensor_entity_id}' auf {shadow_position}.")
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
                f"{self._name}: Sende Höhenbefehl: {height_to_set_percent}% an {self._target_cover_entity_id}.")
            await self.hass.services.async_call(
                "cover",
                "set_position",
                {"entity_id": self._target_cover_entity_id, "position": height_to_set_percent},
                blocking=False
            )
        else:
            _LOGGER.debug(
                f"{self._name}: Höhenbefehl '{height_to_set_percent}%' nicht gesendet, da Wert sich nicht geändert hat oder durch Beschränkung gefiltert wurde.")

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
                f"{self._name}: Sende Winkelbefehl: {angle_to_set_percent}% an {self._target_cover_entity_id}. "
                f"Winkeländerung: {angle_to_set_percent != self._previous_shutter_angle}. Höhenänderung: {height_was_different_before_height_update}")
            await self.hass.services.async_call(
                "cover",
                "set_tilt_position",
                {"entity_id": self._target_cover_entity_id, "tilt_position": angle_to_set_percent},
                blocking=False
            )
        else:
            _LOGGER.debug(
                f"{self._name}: Winkelbefehl '{angle_to_set_percent}%' nicht gesendet, da Wert sich nicht geändert hat oder durch Beschränkung gefiltert wurde und Höhe sich nicht geändert hat.")

        self._previous_shutter_angle = shutter_angle_percent  # Immer mit dem NEUEN *berechneten* Wert aktualisieren

        # --- Neuen Sensor für Winkel in Grad publizieren ---
        self._calculated_angle_degrees = self._convert_shutter_angle_percent_to_degrees(
            angle_to_set_percent)
        # Wichtig: HA-Zustand aktualisieren, damit Attribute (inkl. calculated_angle_degrees) publiziert werden
        self.async_write_ha_state()

        # === Timer stoppen ===
        if stop_timer:
            _LOGGER.debug(f"{self._name}: Stop Timer wurde angefordert (Platzhalter).")
            await self._stop_timer()

        _LOGGER.debug(
            f"{self._name}: _position_shutter für Höhe {shutter_height_percent}% und Winkel {shutter_angle_percent}% abgeschlossen.")

    # ... (Ihre _should_output_be_updated, _convert_shutter_angle_percent_to_degrees und _cancel_all_shadow_timers) ...
    # Denken Sie daran, dass _update_input_values auch in der Klasse sein muss.

    async def _check_if_facade_is_in_sun(self) -> None:
        """Calculate if the sun illuminates the given facade."""
        _LOGGER.debug(f"=== Checking if facade is in sun... ===")

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
            _LOGGER.debug(f"Nicht alle erforderlichen Sonnen- oder Fassadendaten verfügbar für die Prüfung des Sonneneinfalls.")
            self._effective_elevation = None
            return

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

        is_azimuth_in_range = 0 <= azimuth_calc <= sun_exit_angle_calc
        message = f"=== Finished facade check:\n -> real azimuth {sun_current_azimuth}° and facade at {facade_azimuth}° -> "
        if is_azimuth_in_range:
            message += f"IN SUN (from {sun_entry_angle}° to {sun_exit_angle}°)"
            self._sun_between_offsets = True
            self._effective_elevation = await self._calculate_effective_elevation()
        else:
            message += f"NOT IN SUN (shadow side, at sun from {sun_entry_angle}° to {sun_exit_angle}°)"
            self._sun_between_offsets = False
            self._effective_elevation = None

        message += f"\n -> effective elevation {self._effective_elevation}° for given elevation of {sun_current_elevation}°"
        is_elevation_in_range = False
        if min_elevation < self._effective_elevation < max_elevation:
            message += f" -> in min-max-range ({min_elevation}°-{max_elevation}°)"
            self._sun_between_min_max = True
            is_elevation_in_range = True
        else:
            message += f" -> NOT in min-max-range ({min_elevation}°-{max_elevation}°)"
            self._sun_between_min_max = False
        _LOGGER.debug(f"{message} ===")

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
            _LOGGER.debug(f"Kann effektive Elevation nicht berechnen: Nicht alle erforderlichen Eingabewerte sind verfügbar.")
            return None

        _LOGGER.debug(f"Current sun position (a:e): {sun_current_azimuth}°:{sun_current_elevation}°, facade: {facade_azimuth}°")

        try:
            virtual_depth = math.cos(math.radians(abs(sun_current_azimuth - facade_azimuth)))
            virtual_height = math.tan(math.radians(sun_current_elevation))

            # Vermeide Division durch Null, falls virtual_depth sehr klein ist
            if abs(virtual_depth) < 1e-9:
                effective_elevation = 90.0 if virtual_height > 0 else -90.0
            else:
                effective_elevation = math.degrees(math.atan(virtual_height / virtual_depth))

            _LOGGER.debug(f"Virtuelle Tiefe und Höhe der Sonnenposition in 90° zur Fassade: {virtual_depth}, {virtual_height}, effektive Elevation: {effective_elevation}")
            return effective_elevation
        except ValueError:
            _LOGGER.debug(f"Kann effektive Elevation nicht berechnen: Ungültige numerische Eingabewerte.")
            return None
        except ZeroDivisionError:
            _LOGGER.debug(f"Kann effektive Elevation nicht berechnen: Division durch Null.")
            return None

    # #######################################################################
    # State handling starting here
    # 
    # =======================================================================
    # State SHADOW_FULL_CLOSE_TIMER_RUNNING
    async def _handle_state_shadow_full_close_timer_running(self) -> ShutterState:
        if await self._is_lbs_locked_in_either_way():
            _LOGGER.debug(f"Zustand {self.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING}: LBS ist gesperrt, keine Aktion.")
            return ShutterState.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING

        if await self._check_if_facade_is_in_sun() and await self._is_shadow_handling_activated():
            current_brightness = self._brightness
            shadow_threshold_close = self._shadow_brightness_level
            if (
                    current_brightness is not None
                    and shadow_threshold_close is not None
                    and current_brightness > shadow_threshold_close
            ):
                if await self._is_timer_finished():
                    target_height = self._calculate_shutter_height()
                    target_angle = self._calculate_shutter_angle()
                    if target_height is not None and target_angle is not None:
                        await self._position_shutter(
                            target_height,
                            target_angle,
                            shadow_position=True,
                            stop_timer=True,
                        )
                        _LOGGER.debug(f"Zustand {self.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING}: Timer abgelaufen, Helligkeit hoch genug, fahre in Vollschatten ({target_height}%, {target_angle}%) und gehe zu {self.STATE_SHADOW_FULL_CLOSED}")
                        return ShutterState.STATE_SHADOW_FULL_CLOSED
                    else:
                        _LOGGER.debug(f"Zustand {self.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING}: Fehler beim Berechnen der Schattenhöhe oder des Winkels, bleibe in {self.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING}")
                        return ShutterState.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING
                else:
                    _LOGGER.debug(f"Zustand {self.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING}: Warte auf Timer (Helligkeit hoch genug)...")
                    return ShutterState.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING
            else:
                _LOGGER.debug(f"Zustand {self.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING}: Helligkeit ({current_brightness}) nicht höher als Schwellwert ({shadow_threshold_close}), gehe zu {self.STATE_SHADOW_NEUTRAL}")
                await self._stop_timer()
                return ShutterState.STATE_SHADOW_NEUTRAL
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
                _LOGGER.debug(f"Zustand {self.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING}: Nicht in Sonne oder Schattenmodus deaktiviert, fahre in Neutralposition ({neutral_height}%, {neutral_angle}%) und gehe zu {self.STATE_NEUTRAL}")
                return ShutterState.STATE_NEUTRAL
            else:
                _LOGGER.debug(f"Zustand {self.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING}: Neutrale Höhe oder Winkel nicht konfiguriert, gehe zu {self.STATE_NEUTRAL}")
                return ShutterState.STATE_NEUTRAL

        # Entsprechung zu LB_LBSID_positionShutterWithPreviousValues
        _LOGGER.debug(f"Zustand {self.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING}: Beibehalte vorherige Position.")
        return ShutterState.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING

    # =======================================================================
    # State SHADOW_FULL_CLOSED
    async def _handle_state_shadow_full_closed(self) -> ShutterState:
        if await self._is_lbs_locked_in_either_way():
            _LOGGER.debug(f"Zustand {self.STATE_SHADOW_FULL_CLOSED}: LBS ist gesperrt, keine Aktion.")
            return ShutterState.STATE_SHADOW_FULL_CLOSED

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
                _LOGGER.debug(f"Zustand {self.STATE_SHADOW_FULL_CLOSED}: Helligkeit ({current_brightness}) unter Schwellwert ({shadow_threshold_close}), starte Timer für {self.STATE_SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING} ({shadow_open_slat_delay}s)")
                await self._start_timer(shadow_open_slat_delay)
                return ShutterState.STATE_SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING
            else:
                _LOGGER.debug(f"Zustand {self.STATE_SHADOW_FULL_CLOSED}: Helligkeit nicht unter Schwellwert, Neuberechnung der Schattenposition.")
                target_height = self._calculate_shutter_height()
                target_angle = self._calculate_shutter_angle()
                if target_height is not None and target_angle is not None:
                    await self._position_shutter(
                        target_height,
                        target_angle,
                        shadow_position=True,
                        stop_timer=False,
                    )
                return ShutterState.STATE_SHADOW_FULL_CLOSED
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
                _LOGGER.debug(f"Zustand {self.STATE_SHADOW_FULL_CLOSED}: Nicht in Sonne oder Schattenmodus deaktiviert, fahre in Neutralposition ({neutral_height}%, {neutral_angle}%) und gehe zu {self.STATE_NEUTRAL}")
                return ShutterState.STATE_NEUTRAL
            else:
                _LOGGER.debug(f"Zustand {self.STATE_SHADOW_FULL_CLOSED}: Neutrale Höhe oder Winkel nicht konfiguriert, gehe zu {self.STATE_NEUTRAL}")
                return ShutterState.STATE_NEUTRAL

        # Entsprechung zu LB_LBSID_positionShutterWithPreviousValues
        _LOGGER.debug(f"Zustand {self.STATE_SHADOW_FULL_CLOSED}: Beibehalte vorherige Position.")
        return ShutterState.STATE_SHADOW_FULL_CLOSED

    # =======================================================================
    # State SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING
    async def _handle_state_shadow_horizontal_neutral_timer_running(self) -> ShutterState:
        if await self._is_lbs_locked_in_either_way():
            _LOGGER.debug(f"Zustand {self.STATE_SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: LBS ist gesperrt, keine Aktion.")
            return ShutterState.STATE_SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING

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
                _LOGGER.debug(f"Zustand {self.STATE_SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Helligkeit ({current_brightness}) wieder über Schwellwert ({shadow_threshold_close}), gehe zu {self.STATE_SHADOW_FULL_CLOSED} und stoppe Timer.")
                await self._stop_timer()
                return ShutterState.STATE_SHADOW_FULL_CLOSED
            else:
                if await self._is_timer_finished():
                    target_height = await self._calculate_shutter_height()
                    if target_height is not None and shadow_open_slat_angle is not None:
                        await self._position_shutter(
                            target_height,
                            float(shadow_open_slat_angle),
                            shadow_position=False,
                            stop_timer=True,
                        )
                        _LOGGER.debug(f"Zustand {self.STATE_SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Timer abgelaufen, fahre auf Höhe {target_height}% mit neutralen Lamellen ({shadow_open_slat_angle}°) und gehe zu {self.STATE_SHADOW_HORIZONTAL_NEUTRAL}")
                        return ShutterState.STATE_SHADOW_HORIZONTAL_NEUTRAL
                    else:
                        _LOGGER.debug(f"Zustand {self.STATE_SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Fehler beim Berechnen der Höhe oder Winkel für offene Lamellen nicht konfiguriert, bleibe in {self.STATE_SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING}")
                        return ShutterState.STATE_SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING
                else:
                    _LOGGER.debug(f"Zustand {self.STATE_SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Warte auf Timer (Helligkeit nicht hoch genug)...")
                    return ShutterState.STATE_SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING
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
                _LOGGER.debug(f"Zustand {self.STATE_SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Nicht in Sonne oder Schattenmodus deaktiviert, fahre in Neutralposition ({neutral_height}%, {neutral_angle}%) und gehe zu {self.STATE_NEUTRAL}")
                return ShutterState.STATE_NEUTRAL
            else:
                _LOGGER.debug(f"Zustand {self.STATE_SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Neutrale Höhe oder Winkel nicht konfiguriert, gehe zu {self.STATE_NEUTRAL}")
                return ShutterState.STATE_NEUTRAL

        # Entsprechung zu LB_LBSID_positionShutterWithPreviousValues
        _LOGGER.debug(f"Zustand {self.STATE_SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Beibehalte vorherige Position.")
        return ShutterState.STATE_SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING

    # =======================================================================
    # State SHADOW_HORIZONTAL_NEUTRAL
    async def _handle_state_shadow_horizontal_neutral(self) -> ShutterState:
        if await self._is_lbs_locked_in_either_way():
            _LOGGER.debug(f"Zustand {self.STATE_SHADOW_HORIZONTAL_NEUTRAL}: LBS ist gesperrt, keine Aktion.")
            return ShutterState.STATE_SHADOW_HORIZONTAL_NEUTRAL

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
                    _LOGGER.debug(f"Zustand {self.STATE_SHADOW_HORIZONTAL_NEUTRAL}: Helligkeit ({current_brightness}) über Schwellwert ({shadow_threshold_close}), fahre in Vollschatten ({target_height}%, {target_angle}%) und gehe zu {self.STATE_SHADOW_FULL_CLOSED}")
                    return ShutterState.STATE_SHADOW_FULL_CLOSED
                else:
                    _LOGGER.debug(f"Zustand {self.STATE_SHADOW_HORIZONTAL_NEUTRAL}: Fehler beim Berechnen der Schattenhöhe oder des Winkels, bleibe in {self.STATE_SHADOW_HORIZONTAL_NEUTRAL}")
                    return ShutterState.STATE_SHADOW_HORIZONTAL_NEUTRAL
            elif shadow_open_shutter_delay is not None:
                _LOGGER.debug(f"Zustand {self.STATE_SHADOW_HORIZONTAL_NEUTRAL}: Helligkeit nicht über Schwellwert, starte Timer für {self.STATE_SHADOW_NEUTRAL_TIMER_RUNNING} ({shadow_open_shutter_delay}s)")
                await self._start_timer(shadow_open_shutter_delay)
                return ShutterState.STATE_SHADOW_NEUTRAL_TIMER_RUNNING
            else:
                _LOGGER.debug(f"Zustand {self.STATE_SHADOW_HORIZONTAL_NEUTRAL}: Helligkeit nicht über Schwellwert und 'shadow_open_shutter_delay' nicht konfiguriert, bleibe in {self.STATE_SHADOW_HORIZONTAL_NEUTRAL}")
                return ShutterState.STATE_SHADOW_HORIZONTAL_NEUTRAL
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
                _LOGGER.debug(f"Zustand {self.STATE_SHADOW_HORIZONTAL_NEUTRAL}: Nicht in Sonne oder Schattenmodus deaktiviert, fahre in Neutralposition ({neutral_height}%, {neutral_angle}%) und gehe zu {self.STATE_NEUTRAL}")
                return ShutterState.STATE_NEUTRAL
            else:
                _LOGGER.debug(f"Zustand {self.STATE_SHADOW_HORIZONTAL_NEUTRAL}: Neutrale Höhe oder Winkel nicht konfiguriert, gehe zu {self.STATE_NEUTRAL}")
                return ShutterState.STATE_NEUTRAL

        # Entsprechung zu LB_LBSID_positionShutterWithPreviousValues
        _LOGGER.debug(f"Zustand {self.STATE_SHADOW_HORIZONTAL_NEUTRAL}: Beibehalte vorherige Position.")
        return ShutterState.STATE_SHADOW_HORIZONTAL_NEUTRAL

    # =======================================================================
    # State SHADOW_NEUTRAL_TIMER_RUNNING
    async def _handle_state_shadow_neutral_timer_running(self) -> ShutterState:
        if await self._is_lbs_locked_in_either_way():
            _LOGGER.debug(f"Zustand {self.STATE_SHADOW_NEUTRAL_TIMER_RUNNING}: LBS ist gesperrt, keine Aktion.")
            return ShutterState.STATE_SHADOW_NEUTRAL_TIMER_RUNNING

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
                _LOGGER.debug(f"Zustand {self.STATE_SHADOW_NEUTRAL_TIMER_RUNNING}: Helligkeit ({current_brightness}) wieder über Schwellwert ({shadow_threshold_close}), gehe zu {self.STATE_SHADOW_FULL_CLOSED} und stoppe Timer.")
                await self._stop_timer()
                return ShutterState.STATE_SHADOW_FULL_CLOSED
            else:
                if await self._is_timer_finished():
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
                        _LOGGER.debug(f"Zustand {self.STATE_SHADOW_NEUTRAL_TIMER_RUNNING}: Timer abgelaufen, fahre in Position nach Schatten ({height_after_shadow}%, {angle_after_shadow}°) und gehe zu {self.STATE_SHADOW_NEUTRAL}")
                        return ShutterState.STATE_SHADOW_NEUTRAL
                    else:
                        _LOGGER.debug(f"Zustand {self.STATE_SHADOW_NEUTRAL_TIMER_RUNNING}: Höhe oder Winkel nach Schatten nicht konfiguriert, bleibe in {self.STATE_SHADOW_NEUTRAL_TIMER_RUNNING}")
                        return ShutterState.STATE_SHADOW_NEUTRAL_TIMER_RUNNING
                else:
                    _LOGGER.debug(f"Zustand {self.STATE_SHADOW_NEUTRAL_TIMER_RUNNING}: Warte auf Timer (Helligkeit nicht hoch genug)...")
                    return ShutterState.STATE_SHADOW_NEUTRAL_TIMER_RUNNING
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
                _LOGGER.debug(f"Zustand {self.STATE_SHADOW_NEUTRAL_TIMER_RUNNING}: Nicht in Sonne oder Schattenmodus deaktiviert, fahre in Neutralposition ({neutral_height}%, {neutral_angle}%) und gehe zu {self.STATE_NEUTRAL}")
                return ShutterState.STATE_NEUTRAL
            else:
                _LOGGER.debug(f"Zustand {self.STATE_SHADOW_NEUTRAL_TIMER_RUNNING}: Neutrale Höhe oder Winkel nicht konfiguriert, gehe zu {self.STATE_NEUTRAL}")
                return ShutterState.STATE_NEUTRAL

        # Entsprechung zu LB_LBSID_positionShutterWithPreviousValues
        _LOGGER.debug(f"Zustand {self.STATE_SHADOW_NEUTRAL_TIMER_RUNNING}: Beibehalte vorherige Position.")
        return ShutterState.STATE_SHADOW_NEUTRAL_TIMER_RUNNING

    # =======================================================================
    # State SHADOW_NEUTRAL
    async def _handle_state_shadow_neutral(self) -> ShutterState:
        if await self._is_lbs_locked_in_either_way():
            _LOGGER.debug(f"Zustand {self.STATE_SHADOW_NEUTRAL}: LBS ist gesperrt, keine Aktion.")
            return ShutterState.STATE_SHADOW_NEUTRAL

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
                _LOGGER.debug(f"Zustand {self.STATE_SHADOW_NEUTRAL}: Helligkeit ({current_brightness}) über Schatten-Schwellwert ({shadow_threshold_close}), starte Timer für {self.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING} ({shadow_close_delay}s)")
                await self._start_timer(shadow_close_delay)
                return ShutterState.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING
            elif (
                    dawn_handling_active
                    and dawn_brightness is not None
                    and dawn_threshold_close is not None
                    and dawn_brightness < dawn_threshold_close
                    and dawn_close_delay is not None
            ):
                _LOGGER.debug(f"Zustand {self.STATE_SHADOW_NEUTRAL}: Dämmerungsbehandlung aktiv und Helligkeit ({dawn_brightness}) unter Dämmerungs-Schwellwert ({dawn_threshold_close}), starte Timer für {self.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING} ({dawn_close_delay}s)")
                await self._start_timer(dawn_close_delay)
                return ShutterState.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING
            elif height_after_shadow is not None and angle_after_shadow is not None:
                await self._position_shutter(
                    float(height_after_shadow),
                    float(angle_after_shadow),
                    shadow_position=False,
                    stop_timer=False,
                )
                _LOGGER.debug(f"Zustand {self.STATE_SHADOW_NEUTRAL}: Bewege Behang in Position nach Schatten ({height_after_shadow}%, {angle_after_shadow}%).")
                return ShutterState.STATE_SHADOW_NEUTRAL
            else:
                _LOGGER.debug(f"Zustand {self.STATE_SHADOW_NEUTRAL}: Höhe oder Winkel nach Schatten nicht konfiguriert, bleibe in {self.STATE_SHADOW_NEUTRAL}")
                return ShutterState.STATE_SHADOW_NEUTRAL

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
                _LOGGER.debug(f"Zustand {self.STATE_SHADOW_NEUTRAL}: Dämmerungsbehandlung aktiv und Helligkeit ({dawn_brightness}) unter Dämmerungs-Schwellwert ({dawn_threshold_close}), starte Timer für {self.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING} ({dawn_close_delay}s)")
                await self._start_timer(dawn_close_delay)
                return ShutterState.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING

        neutral_height = self._neutral_pos_height
        neutral_angle = self._neutral_pos_angle
        if neutral_height is not None and neutral_angle is not None:
            await self._position_shutter(
                float(neutral_height),
                float(neutral_angle),
                shadow_position=False,
                stop_timer=True,  # Stop Timer (falls ein Timer aktiv war)
            )
            _LOGGER.debug(f"Zustand {self.STATE_SHADOW_NEUTRAL}: Nicht in Sonne oder Schattenmodus deaktiviert und Dämmerung nicht aktiv, fahre in Neutralposition ({neutral_height}%, {neutral_angle}%) und gehe zu {self.STATE_NEUTRAL}")
            return ShutterState.STATE_NEUTRAL
        else:
            _LOGGER.debug(f"Zustand {self.STATE_SHADOW_NEUTRAL}: Neutrale Höhe oder Winkel nicht konfiguriert, gehe zu {self.STATE_NEUTRAL}")
            return ShutterState.STATE_NEUTRAL

    # =======================================================================
    # State NEUTRAL
    async def _handle_state_neutral(self) -> ShutterState:
        if await self._is_lbs_locked_in_either_way():
            _LOGGER.debug(f"Zustand {self.STATE_NEUTRAL}: LBS ist gesperrt, keine Aktion."
            )
            return ShutterState.STATE_NEUTRAL

        if await self._check_if_facade_is_in_sun() and await self._is_shadow_handling_activated():
            current_brightness = self._brightness
            shadow_threshold_close = self._shadow_brightness_level
            shadow_close_delay = self._shadow_after_seconds
            if (
                current_brightness is not None
                and shadow_threshold_close is not None
                and current_brightness > shadow_threshold_close
                and shadow_close_delay is not None
            ):
                _LOGGER.debug(f"Zustand {self.STATE_NEUTRAL}: Helligkeit ({current_brightness}) über Schatten-Schwellwert ({shadow_threshold_close}), starte Timer für {self.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING} ({shadow_close_delay}s)")
                await self._start_timer(shadow_close_delay)
                return ShutterState.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING

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
                _LOGGER.debug(f"Zustand {self.STATE_NEUTRAL}: Dämmerungsbehandlung aktiv und Helligkeit ({dawn_brightness}) unter Dämmerungs-Schwellwert ({dawn_threshold_close}), starte Timer für {self.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING} ({dawn_close_delay}s)")
                await self._start_timer(dawn_close_delay)
                return ShutterState.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING

        neutral_height = self._neutral_pos_height
        neutral_angle = self._neutral_pos_angle
        if neutral_height is not None and neutral_angle is not None:
            await self._position_shutter(
                float(neutral_height),
                float(neutral_angle),
                shadow_position=False,
                stop_timer=False,
            )
            _LOGGER.debug(f"Zustand {self.STATE_NEUTRAL}: Bewege Behang in Neutralposition ({neutral_height}%, {neutral_angle}%).")
        return ShutterState.STATE_NEUTRAL

    # =======================================================================
    # State DAWN_NEUTRAL
    async def _handle_state_dawn_neutral(self) -> ShutterState:
        if await self._is_lbs_locked_in_either_way():
            _LOGGER.debug(f"Zustand {self.STATE_DAWN_NEUTRAL}: LBS ist gesperrt, keine Aktion.")
            return ShutterState.STATE_DAWN_NEUTRAL

        dawn_handling_active = await self._is_dawn_handling_activated()
        dawn_brightness = await self._get_input_value("brightness_dawn")
        dawn_threshold_close = await self._get_input_value("dawn_threshold_close")
        dawn_close_delay = await self._get_input_value("dawn_close_delay")
        is_in_sun = await self._check_if_facade_is_in_sun()
        shadow_handling_active = await self._is_shadow_handling_activated()
        current_brightness = await self._get_input_value("brightness")
        shadow_threshold_close = await self._get_input_value("shadow_threshold_close")
        shadow_close_delay = await self._get_input_value("shadow_close_delay")
        height_after_dawn = await self._get_input_value("height_after_dawn")
        angle_after_dawn = await self._get_input_value("angle_after_dawn")
        neutral_height = await self._get_input_value("height_neutral")
        neutral_angle = await self._get_input_value("angle_neutral")

        if dawn_handling_active:
            if (
                    dawn_brightness is not None
                    and dawn_threshold_close is not None
                    and dawn_brightness < dawn_threshold_close
                    and dawn_close_delay is not None
            ):
                _LOGGER.debug(f"Zustand {self.STATE_DAWN_NEUTRAL}: Dämmerungsbehandlung aktiv und Helligkeit ({dawn_brightness}) unter Dämmerungs-Schwellwert ({dawn_threshold_close}), starte Timer für {self.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING} ({dawn_close_delay}s)")
                await self._start_timer(dawn_close_delay)
                return ShutterState.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING
            elif (
                    is_in_sun
                    and shadow_handling_active
                    and current_brightness is not None
                    and shadow_threshold_close is not None
                    and current_brightness > shadow_threshold_close
                    and shadow_close_delay is not None
            ):
                _LOGGER.debug(f"Zustand {self.STATE_DAWN_NEUTRAL}: Sonne scheint, Schattenbehandlung aktiv und Helligkeit ({current_brightness}) über Schatten-Schwellwert ({shadow_threshold_close}), starte Timer für {self.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING} ({shadow_close_delay}s)")
                await self._start_timer(shadow_close_delay)
                return ShutterState.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING
            elif height_after_dawn is not None and angle_after_dawn is not None:
                await self._position_shutter(
                    float(height_after_dawn),
                    float(angle_after_dawn),
                    shadow_position=False,
                    stop_timer=False,
                )
                _LOGGER.debug(f"Zustand {self.STATE_DAWN_NEUTRAL}: Bewege Behang in Position nach Dämmerung ({height_after_dawn}%, {angle_after_dawn}%).")
                return ShutterState.STATE_DAWN_NEUTRAL
            else:
                _LOGGER.debug(f"Zustand {self.STATE_DAWN_NEUTRAL}: Höhe oder Winkel nach Dämmerung nicht konfiguriert, bleibe in {self.STATE_DAWN_NEUTRAL}")
                return ShutterState.STATE_DAWN_NEUTRAL

        if (
                is_in_sun
                and shadow_handling_active
                and current_brightness is not None
                and shadow_threshold_close is not None
                and current_brightness > shadow_threshold_close
                and shadow_close_delay is not None
        ):
            _LOGGER.debug(f"Zustand {self.STATE_DAWN_NEUTRAL}: Sonne scheint, Schattenbehandlung aktiv und Helligkeit ({current_brightness}) über Schatten-Schwellwert ({shadow_threshold_close}), starte Timer für {self.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING} ({shadow_close_delay}s)")
            await self._start_timer(shadow_close_delay)
            return ShutterState.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING

        if neutral_height is not None and neutral_angle is not None:
            await self._position_shutter(
                float(neutral_height),
                float(neutral_angle),
                shadow_position=False,
                stop_timer=True,  # Stop Timer (falls ein Timer aktiv war)
            )
            _LOGGER.debug(f"Zustand {self.STATE_DAWN_NEUTRAL}: Dämmerungsbehandlung deaktiviert oder nicht die Bedingungen für Schatten, fahre in Neutralposition ({neutral_height}%, {neutral_angle}%).")
            return ShutterState.STATE_NEUTRAL
        else:
            _LOGGER.debug(f"Zustand {self.STATE_DAWN_NEUTRAL}: Neutrale Höhe oder Winkel nicht konfiguriert, gehe zu {self.STATE_NEUTRAL}")
            return ShutterState.STATE_NEUTRAL

    # =======================================================================
    # State DAWN_NEUTRAL_TIMER_RUNNING
    async def _handle_state_dawn_neutral_timer_running(self) -> ShutterState:
        if await self._is_lbs_locked_in_either_way():
            _LOGGER.debug(f"Zustand {self.STATE_DAWN_NEUTRAL_TIMER_RUNNING}: LBS ist gesperrt, keine Aktion.")
            return ShutterState.STATE_DAWN_NEUTRAL_TIMER_RUNNING

        if await self._is_dawn_handling_activated():
            dawn_brightness = await self._get_input_value("brightness_dawn")
            dawn_threshold_close = await self._get_input_value("dawn_threshold_close")
            dawn_height = await self._get_input_value("dawn_height")
            dawn_open_slat_angle = await self._get_input_value("dawn_open_slat_angle")

            if (
                    dawn_brightness is not None
                    and dawn_threshold_close is not None
                    and dawn_brightness < dawn_threshold_close
            ):
                _LOGGER.debug(f"Zustand {self.STATE_DAWN_NEUTRAL_TIMER_RUNNING}: Dämmerungshelligkeit ({dawn_brightness}) wieder unter Schwellwert ({dawn_threshold_close}), gehe zu {self.STATE_DAWN_FULL_CLOSED} und stoppe Timer.")
                await self._stop_timer()
                return ShutterState.STATE_DAWN_FULL_CLOSED
            else:
                if await self._is_timer_finished():
                    if dawn_height is not None and dawn_open_slat_angle is not None:
                        await self._position_shutter(
                            float(dawn_height),
                            float(dawn_open_slat_angle),
                            shadow_position=False,
                            stop_timer=True,
                        )
                        _LOGGER.debug(f"Zustand {self.STATE_DAWN_NEUTRAL_TIMER_RUNNING}: Timer abgelaufen, fahre auf Dämmerungshöhe ({dawn_height}%) mit geöffneten Lamellen ({dawn_open_slat_angle}°) und gehe zu {self.STATE_DAWN_NEUTRAL}")
                        return ShutterState.STATE_DAWN_NEUTRAL
                    else:
                        _LOGGER.debug(f"Zustand {self.STATE_DAWN_NEUTRAL_TIMER_RUNNING}: Dämmerungshöhe oder Winkel für offene Lamellen nicht konfiguriert, bleibe in {self.STATE_DAWN_NEUTRAL_TIMER_RUNNING}")
                        return ShutterState.STATE_DAWN_NEUTRAL_TIMER_RUNNING
                else:
                    _LOGGER.debug(f"Zustand {self.STATE_DAWN_NEUTRAL_TIMER_RUNNING}: Warte auf Timer (Helligkeit nicht niedrig genug)...")
                    return ShutterState.STATE_DAWN_NEUTRAL_TIMER_RUNNING
        else:
            neutral_height = await self._get_input_value("height_neutral")
            neutral_angle = await self._get_input_value("angle_neutral")
            if neutral_height is not None and neutral_angle is not None:
                await self._position_shutter(
                    float(neutral_height),
                    float(neutral_angle),
                    shadow_position=False,
                    stop_timer=True,  # Stop Timer
                )
                _LOGGER.debug(f"Zustand {self.STATE_DAWN_NEUTRAL_TIMER_RUNNING}: Dämmerungsbehandlung deaktiviert, fahre in Neutralposition ({neutral_height}%, {neutral_angle}%) und gehe zu {self.STATE_NEUTRAL}")
                return ShutterState.STATE_NEUTRAL
            else:
                _LOGGER.debug(f"Zustand {self.STATE_DAWN_NEUTRAL_TIMER_RUNNING}: Neutrale Höhe oder Winkel nicht konfiguriert, gehe zu {self.STATE_NEUTRAL}")
                return ShutterState.STATE_NEUTRAL

        # Entsprechung zu LB_LBSID_positionShutterWithPreviousValues
        _LOGGER.debug(f"Zustand {self.STATE_DAWN_NEUTRAL_TIMER_RUNNING}: Beibehalte vorherige Position.")
        return ShutterState.STATE_DAWN_NEUTRAL_TIMER_RUNNING

    # =======================================================================
    # State DAWN_HORIZONTAL_NEUTRAL
    async def _handle_state_dawn_horizontal_neutral(self) -> ShutterState:
        if await self._is_lbs_locked_in_either_way():
            _LOGGER.debug(f"Zustand {self.STATE_DAWN_HORIZONTAL_NEUTRAL}: LBS ist gesperrt, keine Aktion.")
            return ShutterState.STATE_DAWN_HORIZONTAL_NEUTRAL

        if await self._is_dawn_handling_activated():
            dawn_brightness = await self._get_input_value("brightness_dawn")
            dawn_threshold_close = await self._get_input_value("dawn_threshold_close")
            dawn_height = await self._get_input_value("dawn_height")
            dawn_open_slat_angle = await self._get_input_value("dawn_open_slat_angle")
            dawn_open_shutter_delay = await self._get_input_value(
                "dawn_open_shutter_delay"
            )

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
                _LOGGER.debug(f"Zustand {self.STATE_DAWN_HORIZONTAL_NEUTRAL}: Dämmerungshelligkeit ({dawn_brightness}) unter Schwellwert ({dawn_threshold_close}), fahre auf Dämmerungshöhe ({dawn_height}%) mit geöffneten Lamellen ({dawn_open_slat_angle}°) und gehe zu {self.STATE_DAWN_FULL_CLOSED}")
                return ShutterState.STATE_DAWN_FULL_CLOSED
            elif dawn_open_shutter_delay is not None:
                _LOGGER.debug(f"Zustand {self.STATE_DAWN_HORIZONTAL_NEUTRAL}: Dämmerungshelligkeit nicht unter Schwellwert, starte Timer für {self.STATE_DAWN_NEUTRAL_TIMER_RUNNING} ({dawn_open_shutter_delay}s)")
                await self._start_timer(dawn_open_shutter_delay)
                return ShutterState.STATE_DAWN_NEUTRAL_TIMER_RUNNING
            else:
                _LOGGER.debug(f"Zustand {self.STATE_DAWN_HORIZONTAL_NEUTRAL}: Dämmerungshelligkeit nicht unter Schwellwert und 'dawn_open_shutter_delay' nicht konfiguriert, bleibe in {self.STATE_DAWN_HORIZONTAL_NEUTRAL}")
                return ShutterState.STATE_DAWN_HORIZONTAL_NEUTRAL
        else:
            neutral_height = await self._get_input_value("height_neutral")
            neutral_angle = await self._get_input_value("angle_neutral")
            if neutral_height is not None and neutral_angle is not None:
                await self._position_shutter(
                    float(neutral_height),
                    float(neutral_angle),
                    shadow_position=False,
                    stop_timer=True,
                )
                _LOGGER.debug(f"Zustand {self.STATE_DAWN_HORIZONTAL_NEUTRAL}: Dämmerungsbehandlung deaktiviert, fahre in Neutralposition ({neutral_height}%, {neutral_angle}%) und gehe zu {self.STATE_NEUTRAL}")
                return ShutterState.STATE_NEUTRAL
            else:
                _LOGGER.debug(f"Zustand {self.STATE_DAWN_HORIZONTAL_NEUTRAL}: Neutrale Höhe oder Winkel nicht konfiguriert, gehe zu {self.STATE_NEUTRAL}")
                return ShutterState.STATE_NEUTRAL

        # Entsprechung zu LB_LBSID_positionShutterWithPreviousValues
        _LOGGER.debug(f"Zustand {self.STATE_DAWN_HORIZONTAL_NEUTRAL}: Beibehalte vorherige Position.")
        return ShutterState.STATE_DAWN_HORIZONTAL_NEUTRAL

    # =======================================================================
    # State DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING
    async def _handle_state_dawn_horizontal_neutral_timer_running(self) -> ShutterState:
        if await self._is_lbs_locked_in_either_way():
            _LOGGER.debug(f"Zustand {self.STATE_DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: LBS ist gesperrt, keine Aktion.")
            return ShutterState.STATE_DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING

        if await self._is_dawn_handling_activated():
            dawn_brightness = await self._get_input_value("brightness_dawn")
            dawn_threshold_close = await self._get_input_value("dawn_threshold_close")
            dawn_height = await self._get_input_value("dawn_height")
            dawn_open_slat_angle = await self._get_input_value("dawn_open_slat_angle")

            if (
                    dawn_brightness is not None
                    and dawn_threshold_close is not None
                    and dawn_brightness < dawn_threshold_close
            ):
                _LOGGER.debug(f"Zustand {self.STATE_DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Dämmerungshelligkeit ({dawn_brightness}) wieder unter Schwellwert ({dawn_threshold_close}), gehe zu {self.STATE_DAWN_FULL_CLOSED} und stoppe Timer.")
                await self._stop_timer()
                return ShutterState.STATE_DAWN_FULL_CLOSED
            else:
                if await self._is_timer_finished():
                    if dawn_height is not None and dawn_open_slat_angle is not None:
                        await self._position_shutter(
                            float(dawn_height),
                            float(dawn_open_slat_angle),
                            shadow_position=False,
                            stop_timer=True,
                        )
                        _LOGGER.debug(f"Zustand {self.STATE_DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Timer abgelaufen, fahre auf Dämmerungshöhe ({dawn_height}%) mit geöffneten Lamellen ({dawn_open_slat_angle}°) und gehe zu {self.STATE_DAWN_HORIZONTAL_NEUTRAL}")
                        return ShutterState.STATE_DAWN_HORIZONTAL_NEUTRAL
                    else:
                        _LOGGER.debug(f"Zustand {self.STATE_DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Dämmerungshöhe oder Winkel für offene Lamellen nicht konfiguriert, bleibe in {self.STATE_DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING}")
                        return ShutterState.STATE_DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING
                else:
                    _LOGGER.debug(f"Zustand {self.STATE_DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Warte auf Timer (Helligkeit nicht niedrig genug)...")
                    return ShutterState.STATE_DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING
        else:
            neutral_height = await self._get_input_value("height_neutral")
            neutral_angle = await self._get_input_value("angle_neutral")
            if neutral_height is not None and neutral_angle is not None:
                await self._position_shutter(
                    float(neutral_height),
                    float(neutral_angle),
                    shadow_position=False,
                    stop_timer=True,  # Stop Timer
                )
                _LOGGER.debug(f"Zustand {self.STATE_DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Dämmerungsbehandlung deaktiviert, fahre in Neutralposition ({neutral_height}%, {neutral_angle}%) und gehe zu {self.STATE_NEUTRAL}")
                return ShutterState.STATE_NEUTRAL
            else:
                _LOGGER.debug(f"Zustand {self.STATE_DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Neutrale Höhe oder Winkel nicht konfiguriert, gehe zu {self.STATE_NEUTRAL}")
                return ShutterState.STATE_NEUTRAL

        # Entsprechung zu LB_LBSID_positionShutterWithPreviousValues
        _LOGGER.debug(f"Zustand {self.STATE_DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Beibehalte vorherige Position.")
        return ShutterState.STATE_DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING

    # =======================================================================
    # State DAWN_FULL_CLOSED
    async def _handle_state_dawn_full_closed(self) -> ShutterState:
        if await self._is_lbs_locked_in_either_way():
            _LOGGER.debug(f"Zustand {self.STATE_DAWN_FULL_CLOSED}: LBS ist gesperrt, keine Aktion.")
            return ShutterState.STATE_DAWN_FULL_CLOSED

        if await self._is_dawn_handling_activated():
            dawn_brightness = await self._get_input_value("brightness_dawn")
            dawn_threshold_close = await self._get_input_value("dawn_threshold_close")
            dawn_open_slat_delay = await self._get_input_value("dawn_open_slat_delay")
            dawn_height = await self._get_input_value("dawn_height")
            dawn_angle = await self._get_input_value("dawn_angle")

            if (
                    dawn_brightness is not None
                    and dawn_threshold_close is not None
                    and dawn_brightness > dawn_threshold_close
                    and dawn_open_slat_delay is not None
            ):
                _LOGGER.debug(f"Zustand {self.STATE_DAWN_FULL_CLOSED}: Dämmerungshelligkeit ({dawn_brightness}) über Schwellwert ({dawn_threshold_close}), starte Timer für {self.STATE_DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING} ({dawn_open_slat_delay}s)")
                await self._start_timer(dawn_open_slat_delay)
                return ShutterState.STATE_DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING
            elif dawn_height is not None and dawn_angle is not None:
                await self._position_shutter(
                    float(dawn_height),
                    float(dawn_angle),
                    shadow_position=False,
                    stop_timer=False,
                )
                _LOGGER.debug(f"Zustand {self.STATE_DAWN_FULL_CLOSED}: Dämmerungshelligkeit nicht über Schwellwert, fahre in Dämmerungsposition ({dawn_height}%, {dawn_angle}%).")
                return ShutterState.STATE_DAWN_FULL_CLOSED
            else:
                _LOGGER.debug(f"Zustand {self.STATE_DAWN_FULL_CLOSED}: Dämmerungshöhe oder -winkel nicht konfiguriert, bleibe in {self.STATE_DAWN_FULL_CLOSED}")
                return ShutterState.STATE_DAWN_FULL_CLOSED
        else:
            neutral_height = await self._get_input_value("height_neutral")
            neutral_angle = await self._get_input_value("angle_neutral")
            if neutral_height is not None and neutral_angle is not None:
                await self._position_shutter(
                    float(neutral_height),
                    float(neutral_angle),
                    shadow_position=False,
                    stop_timer=True,  # Stop Timer
                )
                _LOGGER.debug(f"Zustand {self.STATE_DAWN_FULL_CLOSED}: Dämmerungsbehandlung deaktiviert, fahre in Neutralposition ({neutral_height}%, {neutral_angle}%) und gehe zu {self.STATE_NEUTRAL}")
                return ShutterState.STATE_NEUTRAL
            else:
                _LOGGER.debug(f"Zustand {self.STATE_DAWN_FULL_CLOSED}: Neutrale Höhe oder Winkel nicht konfiguriert, gehe zu {self.STATE_NEUTRAL}")
                return ShutterState.STATE_NEUTRAL

        # Entsprechung zu LB_LBSID_positionShutterWithPreviousValues
        _LOGGER.debug(f"Zustand {self.STATE_DAWN_FULL_CLOSED}: Beibehalte vorherige Position.")
        return ShutterState.STATE_DAWN_FULL_CLOSED

    # =======================================================================
    # State DAWN_FULL_CLOSE_TIMER_RUNNING
    async def _handle_state_dawn_full_close_timer_running(self) -> ShutterState:
        if await self._is_lbs_locked_in_either_way():
            _LOGGER.debug(f"Zustand {self.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING}: LBS ist gesperrt, keine Aktion.")
            return ShutterState.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING

        if await self._is_dawn_handling_activated():
            dawn_brightness = await self._get_input_value("brightness_dawn")
            dawn_threshold_close = await self._get_input_value("dawn_threshold_close")
            dawn_height = await self._get_input_value("dawn_height")
            dawn_angle = await self._get_input_value("dawn_angle")

            if (
                    dawn_brightness is not None
                    and dawn_threshold_close is not None
                    and dawn_brightness < dawn_threshold_close
            ):
                if await self._is_timer_finished():
                    if dawn_height is not None and dawn_angle is not None:
                        await self._position_shutter(
                            float(dawn_height),
                            float(dawn_angle),
                            shadow_position=False,
                            stop_timer=True,
                        )
                        _LOGGER.debug(f"Zustand {self.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING}: Timer abgelaufen, fahre in volle Dämmerungsposition ({dawn_height}%, {dawn_angle}%) und gehe zu {self.STATE_DAWN_FULL_CLOSED}")
                        return ShutterState.STATE_DAWN_FULL_CLOSED
                    else:
                        _LOGGER.debug(f"Zustand {self.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING}: Dämmerungshöhe oder -winkel nicht konfiguriert, bleibe in {self.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING}")
                        return ShutterState.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING
                else:
                    _LOGGER.debug(f"Zustand {self.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING}: Warte auf Timer (Helligkeit niedrig genug)...")
                    return ShutterState.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING
            else:
                _LOGGER.debug(f"Zustand {self.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING}: Helligkeit ({dawn_brightness}) nicht unter Schwellwert ({dawn_threshold_close}), gehe zu {self.STATE_DAWN_NEUTRAL} und stoppe Timer.")
                await self._stop_timer()
                return ShutterState.STATE_DAWN_NEUTRAL
        else:
            neutral_height = await self._get_input_value("height_neutral")
            neutral_angle = await self._get_input_value("angle_neutral")
            if neutral_height is not None and neutral_angle is not None:
                await self._position_shutter(
                    float(neutral_height),
                    float(neutral_angle),
                    shadow_position=False,
                    stop_timer=True,  # Stop Timer
                )
                _LOGGER.debug(f"Zustand {self.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING}: Dämmerungsbehandlung deaktiviert, fahre in Neutralposition ({neutral_height}%, {neutral_angle}%) und gehe zu {self.STATE_NEUTRAL}")
                return ShutterState.STATE_NEUTRAL
            else:
                _LOGGER.debug(f"Zustand {self.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING}: Neutrale Höhe oder Winkel nicht konfiguriert, gehe zu {self.STATE_NEUTRAL}")
                return ShutterState.STATE_NEUTRAL

        # Entsprechung zu LB_LBSID_positionShutterWithPreviousValues
        _LOGGER.debug(f"Zustand {self.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING}: Beibehalte vorherige Position.")
        return ShutterState.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING

    # End of state handling
    # #######################################################################

    async def _update_sun_state(self):
        """Berechnet, ob die Fassade von der Sonne beleuchtet wird und ob die Elevation im gültigen Bereich liegt."""
        _LOGGER.debug(f"=== Überprüfe, ob Fassade in der Sonne ist... ===")

        azimuth = await self._get_input_value("azimuth")
        facade_angle = await self._get_input_value("facade_angle")
        facade_offset_start = await self._get_input_value("facade_offset_start")
        facade_offset_end = await self._get_input_value("facade_offset_end")
        min_elevation = await self._get_input_value("elevation_min")
        max_elevation = await self._get_input_value("elevation_max")
        elevation = await self._get_input_value("elevation")

        if (
            azimuth is None
            or facade_angle is None
            or facade_offset_start is None
            or facade_offset_end is None
            or min_elevation is None
            or max_elevation is None
            or elevation is None
        ):
            _LOGGER.debug(f"Kann Sonnenstatus nicht überprüfen: Nicht alle erforderlichen Eingabewerte sind verfügbar.")
            return

        azimuth = float(azimuth)
        facade_angle = float(facade_angle)
        facade_offset_start = float(facade_offset_start)
        facade_offset_end = float(facade_offset_end)
        min_elevation = float(min_elevation)
        max_elevation = float(max_elevation)
        elevation = float(elevation)

        # Berechne Eintritts- und Austrittswinkel der Sonne
        sun_entry_angle = facade_angle - abs(facade_offset_start)
        sun_exit_angle = facade_angle + abs(facade_offset_end)

        if sun_entry_angle < 0:
            # Winkel kann nicht negativ sein, korrigiere den Wert
            sun_entry_angle = 360 - abs(sun_entry_angle)
        if sun_exit_angle >= 360:
            # Winkel kann nicht höher als 360° sein, korrigiere den Wert
            sun_exit_angle %= 360

        # Rotiere das System, sodass der Eintrittswinkel bei 0° beginnt
        sun_exit_angle_calc = sun_exit_angle - sun_entry_angle
        if sun_exit_angle_calc < 0:
            sun_exit_angle_calc += 360
        azimuth_calc = azimuth - sun_entry_angle
        if azimuth_calc < 0:
            azimuth_calc += 360

        message = f"=== Fassadenprüfung beendet, realer Azimut {azimuth}° und Fassade bei {facade_angle}° -> "
        is_in_sun = False
        effective_elevation = "n/a"

        if 0 <= azimuth_calc <= sun_exit_angle_calc:
            message += f"IN DER SONNE (von {sun_entry_angle}° bis {sun_exit_angle}°)"
            is_in_sun = True
            await self._set_sun_at_facade_azimuth(1)
            effective_elevation_result = (
                await self._calculate_effective_elevation()
            )  # Implementierung folgt
            if effective_elevation_result is not None:
                effective_elevation = effective_elevation_result
        else:
            message += f"NICHT IN DER SONNE (Schattenseite, Sonne von {sun_entry_angle}° bis {sun_exit_angle}°)"
            is_in_sun = False
            await self._set_sun_at_facade_azimuth(0)

        await self._set_effective_elevation(effective_elevation)

        message += f", effektive Elevation {effective_elevation}° für gegebene Elevation von {elevation}°"
        is_between_min_max_elevation = False
        if (
            effective_elevation != "n/a"
            and min_elevation <= float(effective_elevation) <= max_elevation
        ):
            message += f"° -> im Min-Max-Bereich ({min_elevation}-{max_elevation})"
            is_between_min_max_elevation = True
            await self._set_sun_at_facade_elevation(1)
        else:
            message += (
                f"° -> NICHT im Min-Max-Bereich ({min_elevation}-{max_elevation})"
            )
            is_between_min_max_elevation = False
            await self._set_sun_at_facade_elevation(0)

        _LOGGER.debug(f"{message} ===")

        # Speichere die Ergebnisse in internen Zustandsvariablen
        self._internal_is_in_sun = is_in_sun
        self._internal_sun_between_min_max = is_between_min_max_elevation
        self._internal_effective_elevation = effective_elevation

    async def _get_internal_state(self, state_name: str) -> bool | str | None:
        """Gibt den Wert einer internen Zustandsvariable zurück."""
        state_map = {
            "is_in_sun": self._internal_is_in_sun,
            "is_between_min_max_elevation": self._internal_sun_between_min_max,
            "effective_elevation": self._internal_effective_elevation,
        }
        return state_map.get(state_name)

    _debug_enabled: bool = True  # Standardmäßig Debug-Ausgaben aktivieren

    async def _set_sun_at_facade_azimuth(self, value: int):
        entity_id = await self._get_home_assistant_entity_id("sun_at_facade_azimuth")
        if entity_id:
            await self._set_ha_state(
                entity_id, str(value), {"output_name": "sun_at_facade_azimuth"}
            )

    async def _set_sun_at_facade_elevation(self, value: bool):
        entity_id = await self._get_home_assistant_entity_id("sun_at_facade_elevation")
        if entity_id:
            await self._set_ha_state(
                entity_id,
                "on" if value else "off",
                {"output_name": "sun_at_facade_elevation"},
            )

    async def _set_effective_elevation(self, value: float | str):
        entity_id = await self._get_home_assistant_entity_id("effective_elevation")
        if entity_id:
            await self._set_ha_state(
                entity_id, str(value), {"output_name": "effective_elevation"}
            )

    async def _set_ha_state(
        self, entity_id: str, state: str, attributes: dict | None = None
    ):
        """Hilfsmethode zum Setzen des Zustands einer Home Assistant Entität."""
        if self.hass:
            current_state = self.hass.states.get(entity_id)
            if (
                current_state is None
                or current_state.state != state
                or (attributes and current_state.attributes != attributes)
            ):
                self.hass.states.async_set(entity_id, state, attributes)
                _LOGGER.debug(f"Home Assistant: Setze Zustand von '{entity_id}' auf '{state}' mit Attributen '{attributes}'.")
            else:
                _LOGGER.debug(f"Home Assistant: Zustand von '{entity_id}' ist bereits '{state}' (und Attribute sind gleich), überspringe Aktualisierung.")
        else:
            _LOGGER.debug(f"Home Assistant API-Instanz nicht verfügbar.")

    async def _get_home_assistant_entity_id(self, output_name: str) -> Optional[str]:
        """Holt die Home Assistant Entitäts-ID für den gegebenen Ausgangsnamen aus der Konfiguration."""
        # ... Ihre Logik zum Laden der Zuordnung
        ha_mapping = await self._load_home_assistant_mapping()
        return ha_mapping.get(output_name)

    async def _load_home_assistant_mapping(self) -> dict[str, str]:
        # ... Ihre Implementierung zum Laden der Zuordnung
        return {
            "sun_at_facade_azimuth": "sensor.shadow_control_sun_azimuth",
            "effective_elevation": "sensor.shadow_control_effective_elevation",
            "sun_at_facade_elevation": "binary_sensor.shadow_control_sun_elevation",
            # ... weitere Zuordnungen
        }


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

    # --- Hilfsfunktionen zum Abrufen von Entitätszuständen ---
    def _get_entity_numeric_state(self, entity_id: str | None, value_type: type) -> Any | None:
        """Helper to get a numeric state, converting to the specified type."""
        if entity_id is None:
            return None

        state = self.hass.states.get(entity_id)
        if state is None or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            _LOGGER.debug(f"{self._name}: State for {entity_id} is unknown or unavailable.")
            return None

        try:
            # Konvertieren Sie den Zustandswert in den gewünschten Typ
            return value_type(state.state)
        except (ValueError, TypeError):
            _LOGGER.warning(f"{self._name}: Could not convert state '{state.state}' for {entity_id} to {value_type.__name__}.")
            return None

    def _get_entity_boolean_state(self, entity_id: str | None) -> bool | None:
        """Helper to get a boolean state (on/off)."""
        if entity_id is None:
            return None

        state = self.hass.states.get(entity_id)
        if state is None or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            _LOGGER.debug(f"{self._name}: State for {entity_id} is unknown or unavailable (boolean).")
            return None

        if state.state == STATE_ON:
            return True
        elif state.state == STATE_OFF:
            return False
        else:
            _LOGGER.warning(f"{self._name}: Unexpected state '{state.state}' for boolean entity {entity_id}.")
            return None

    def _get_entity_string_state(self, entity_id: str | None) -> str | None:
        """Helper to get a string state."""
        if entity_id is None:
            return None

        state = self.hass.states.get(entity_id)
        if state is None or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            _LOGGER.debug(f"{self._name}: State for {entity_id} is unknown or unavailable (string).")
            return None

        return state.state