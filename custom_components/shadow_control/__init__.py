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
    vol.Required("brightness_entity_id"): str,
    vol.Required("brightness_dawn_entity_id"): str,
    vol.Required("sun_elevation_entity_id"): str,
    vol.Required("sun_azimuth_entity_id"): str,
    # HINWEIS: shutter_current_height/angle würde man normalerweise direkt vom Cover bekommen.
    # Hier bleiben sie als input_number für Ihre Testzwecke.
    vol.Required("shutter_current_height_entity_id"): str,
    vol.Required("shutter_current_angle_entity_id"): str,
    vol.Required("lock_integration_entity_id"): str,
    vol.Required("lock_integration_with_position_entity_id"): str,
    vol.Required("lock_height_entity_id"): str,
    vol.Required("lock_angle_entity_id"): str,
    vol.Required("modification_tolerance_height_entity_id"): str,
    vol.Required("modification_tolerance_angle_entity_id"): str,

    # === Allgemeine Einstellungen (Mapped to your existing input_number/input_select entities) ===
    vol.Required("facade_azimuth_entity_id"): str,
    vol.Required("facade_offset_sun_in_entity_id"): str,
    vol.Required("facade_offset_sun_out_entity_id"): str,
    vol.Required("facade_elevation_sun_min_entity_id"): str,
    vol.Required("facade_elevation_sun_max_entity_id"): str,
    vol.Required("facade_slat_width_entity_id"): str,
    vol.Required("facade_slat_distance_entity_id"): str,
    vol.Required("facade_slat_angle_offset_entity_id"): str,
    vol.Required("facade_slat_min_angle_entity_id"): str,
    vol.Required("facade_shutter_stepping_height_entity_id"): str,
    vol.Required("facade_shutter_stepping_angle_entity_id"): str,
    vol.Required("facade_shutter_type_entity_id"): str, # input_select
    vol.Required("facade_light_strip_width_entity_id"): str,
    vol.Required("facade_shutter_height_entity_id"): str,
    vol.Required("facade_neutral_pos_height_entity_id"): str,
    vol.Required("facade_neutral_pos_angle_entity_id"): str,
    vol.Required("facade_movement_restriction_height_entity_id"): str, # input_select
    vol.Required("facade_movement_restriction_angle_entity_id"): str, # input_select
    vol.Required("facade_update_lock_output_entity_id"): str, # input_select

    # === Beschattungseinstellungen ===
    vol.Required("shadow_control_enabled_entity_id"): str, # input_boolean
    vol.Required("shadow_brightness_threshold_entity_id"): str,
    vol.Required("shadow_after_seconds_entity_id"): str,
    vol.Required("shadow_shutter_max_height_entity_id"): str,
    vol.Required("shadow_shutter_max_angle_entity_id"): str,
    vol.Required("shadow_shutter_look_through_seconds_entity_id"): str,
    vol.Required("shadow_shutter_look_through_angle_entity_id"): str,
    vol.Required("shadow_shutter_open_seconds_entity_id"): str,
    vol.Required("shadow_height_after_sun_entity_id"): str,
    vol.Required("shadow_angle_after_sun_entity_id"): str,

    # === Dämmerungseinstellungen ===
    vol.Required("dawn_control_enabled_entity_id"): str, # input_boolean
    vol.Required("dawn_brightness_threshold_entity_id"): str,
    vol.Required("dawn_after_seconds_entity_id"): str,
    vol.Required("dawn_shutter_max_height_entity_id"): str,
    vol.Required("dawn_shutter_max_angle_entity_id"): str,
    vol.Required("dawn_shutter_look_through_seconds_entity_id"): str,
    vol.Required("dawn_shutter_look_through_angle_entity_id"): str,
    vol.Required("dawn_shutter_open_seconds_entity_id"): str,
    vol.Required("dawn_height_after_dawn_entity_id"): str,
    vol.Required("dawn_angle_after_dawn_entity_id"): str,
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

        # Entitäten-IDs aus der Konfiguration extrahieren
        # Dies ist nur eine Auswahl, Sie müssen alle Ihre 40+ IDs hier zuweisen
        self._brightness_entity_id = config["brightness_entity_id"]
        self._sun_elevation_entity_id = config["sun_elevation_entity_id"]
        self._sun_azimuth_entity_id = config["sun_azimuth_entity_id"]
        self._shadow_control_enabled_entity_id = config["shadow_control_enabled_entity_id"]
        # ... und so weiter für ALLE Ihre D- und G- und S- und SD-Parameter ...

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
            self._sun_elevation_entity_id,
            self._sun_azimuth_entity_id,
            self._shadow_control_enabled_entity_id,
            # Fügen Sie hier ALLE anderen Entitäten-IDs ein, die Sie oben zugewiesen haben,
            # und die Zustandsänderungen auslösen sollen!
            # z.B. self._lock_integration_entity_id, self._threshold_temperature_entity_id, etc.
        ]

        # Filtern Sie None-Werte heraus, falls ein optionaler Parameter nicht gesetzt ist
        relevant_entity_ids = [eid for eid in relevant_entity_ids if eid]

        self._listeners.append(
            async_track_state_change_event(
                self.hass,
                relevant_entity_ids,
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

        # Erste Berechnung starten
        await self._async_calculate_and_apply_cover_position(None)


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

        # 2. Ihre komplexe Shadow Control Logik hier implementieren
        # Basierend auf current_brightness, current_elevation, current_azimuth
        # und all den anderen Parametern aus self._config

        desired_height = 100 # Standard: Offen
        desired_angle = 50 # Standard: Mitte

        # Beispiel-Logik:
        # Hier würden Sie Ihre Algorithmen einfügen, die die optimalen
        # Höhen- und Lamellenpositionen berechnen.
        # Zugriff auf Konfigurationswerte z.B.: self._config["facade_azimuth_entity_id"]

        # TODO: Implementieren Sie hier Ihre vollständige Shadow Control Logik
        # (Dies ist nur ein Platzhalter)
        if current_brightness > float(self.hass.states.get(self._config["shadow_brightness_threshold_entity_id"]).state):
            _LOGGER.debug(f"[{DOMAIN}] High brightness ({current_brightness}) for '{self._name}'. Activating shading logic.")
            # Beispiel: Abhängig von der Sonnenhöhe
            if current_elevation > float(self.hass.states.get(self._config["facade_elevation_sun_min_entity_id"]).state):
                desired_height = float(self.hass.states.get(self._config["shadow_shutter_max_height_entity_id"]).state)
                # Lamellenwinkel berechnen (z.B. basierend auf elevation, facade_azimuth, slat_width/distance)
                # Für den Moment ein Platzhalter:
                desired_angle = float(self.hass.states.get(self._config["shadow_shutter_max_angle_entity_id"]).state)
            else:
                desired_height = 100 # Sonne zu tief, Fenster lieber offen
                desired_angle = 50
        else:
            _LOGGER.debug(f"[{DOMAIN}] Low brightness ({current_brightness}) for '{self._name}'. Opening covers.")
            desired_height = 100
            desired_angle = 50

        # Überprüfen Sie hier auch die "Lock"-Parameter
        # if self.hass.states.get(self._lock_integration_entity_id).state == STATE_ON:
        #     _LOGGER.info(f"[{DOMAIN}] Integration is locked for '{self._name}'. Skipping control.")
        #     return


        # 3. Positionen an das Cover senden
        await self._send_cover_commands(desired_height, desired_angle)


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
