"""Platform for Shadow Control integration."""

from __future__ import annotations

import logging
import math  # Stellen Sie sicher, dass math importiert ist
from typing import Optional

import voluptuous as vol
from homeassistant.components.cover import CoverEntity, CoverEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, STATE_UNAVAILABLE, STATE_UNKNOWN 
from homeassistant.core import HomeAssistant, callback, State
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change, async_track_state_change_event
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import (
    CONF_ANGLE_AFTER_DAWN,
    CONF_ANGLE_AFTER_SHADOW,
    CONF_ANGLE,
    CONF_ANGLE_NEUTRAL,
    CONF_ANGLE_OFFSET,
    CONF_SUN_AZIMUT,
    CONF_BRIGHTNESS_DAWN,
    CONF_BRIGHTNESS,
    CONF_COVER,
    CONF_DAWN_CLOSE_DELAY,
    CONF_DAWN_HANDLING_ACTIVATION,
    CONF_DAWN_OPEN_SHUTTER_DELAY,
    CONF_DAWN_OPEN_SLAT_DELAY,
    CONF_DAWN_THRESHOLD_CLOSE,
    CONF_DEBUG_ENABLED,
    CONF_SUN_ELEVATION,
    CONF_ELEVATION_MAX,
    CONF_ELEVATION_MIN,
    CONF_FACADE_AZIMUTH,
    CONF_FACADE_OFFSET_END,
    CONF_FACADE_OFFSET_START,
    CONF_FIX_MOVEMENT_DIRECTION_ANGLE,
    CONF_FIX_MOVEMENT_DIRECTION_HEIGHT,
    CONF_HEIGHT_AFTER_DAWN,
    CONF_HEIGHT_AFTER_SHADOW,
    CONF_HEIGHT,
    CONF_HEIGHT_NEUTRAL,
    CONF_LOCK,
    CONF_LOCK_WITH_FORCED_POSITION,
    CONF_MIN_SHUTTER_ANGLE,
    CONF_MODIFICATION_RANGE_ANGLE,
    CONF_MODIFICATION_RANGE_HEIGHT,
    CONF_NON_SHADOW_RANGE,
    CONF_SHADOW_CLOSE_DELAY,
    CONF_SHADOW_HANDLING_ACTIVATION,
    CONF_SHADOW_MAX_ANGLE,
    CONF_SHADOW_MAX_HEIGHT,
    CONF_SHADOW_OPEN_SHUTTER_DELAY,
    CONF_SHADOW_OPEN_SLAT_DELAY,
    CONF_SHADOW_THRESHOLD_CLOSE,
    CONF_SHUTTER_ANGLE_STEPPING,
    CONF_SHUTTER_HEIGHT_STEPPING,
    CONF_SHUTTER_OVERALL_HEIGHT,
    CONF_SHUTTER_SLAT_DISTANCE,
    CONF_SHUTTER_SLAT_WIDTH,
    CONF_SHUTTER_TYPE,
    CONF_UPDATE_LOCKSTATE_OUTPUT,
    DOMAIN,
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
    cover_entity_id = config.get("cover")
    # ... (hier könnten Sie die anderen Konfigurationsparameter lesen,
    #      aber da wir sie fest verdrahtet haben, ist das jetzt optional)

    # Hier erstellen wir eine Instanz Ihrer ShadowControl-Klasse.
    # Die 'config' enthält alle Parameter, die Sie in der configuration.yaml
    # unter 'shadow_control:' definiert haben.
    # Wir übergeben 'config' direkt an den Konstruktor.
    async_add_entities([ShadowControl(hass, config)])

class ShadowControl(CoverEntity): # Vorerst ohne CoordinatorEntity, um es einfach zu halten
    """Representation of a Shadow Control cover."""

    _attr_has_entity_name = True

    def __init__(
            self,
            hass: HomeAssistant,
            config: ConfigType, # Empfängt die gesamte Konfiguration
    ) -> None:
        """Initialize the Shadow Control cover."""
        self.hass = hass # Speichern der hass Instanz
        self._name = config.get(CONF_NAME, DEFAULT_NAME)

        _LOGGER.debug(f"Initializing Shadow Control: {self._name}")

        # Feste Verdrahtung der Entitäts-IDs für die Entwicklung
        # Diese Werte werden jetzt direkt hier gesetzt und nicht mehr aus 'config' gelesen,
        # es sei denn, Sie möchten das später wieder ändern.
        # Die 'config'-Parameter sind aber weiterhin verfügbar, falls Sie sie doch nutzen wollen.

        # === Dynamische Eingänge (Test-Helfer) ===
        self._brightness_entity_id = "input_number.d01_brightness"
        self._brightness_dawn_entity_id = "input_number.d02_brightness_dawn"
        self._sun_elevation_entity_id = "input_number.d03_sun_elevation"
        self._sun_azimuth_entity_id = "input_number.d04_sun_azimuth"
        self._shutter_current_height_entity_id = "input_number.d05_shutter_current_height" # Ist-Wert Höhe
        self._shutter_current_angle_entity_id = "input_number.d06_shutter_current_angle"   # Ist-Wert Winkel
        self._lock_integration_entity_id = "input_select.d07_lock_integration"
        self._lock_integration_with_position_entity_id = "input_select.d08_lock_integration_with_position"
        self._lock_height_entity_id = "input_number.d09_lock_height"
        self._lock_angle_entity_id = "input_number.d10_lock_angle"
        self._modification_tolerance_height_entity_id = "input_number.d11_modification_tolerance_height"
        self._modification_tolerance_angle_entity_id = "input_number.d12_modification_tolerance_angle"

        # === Allgemeine Einstellungen (Test-Helfer) ===
        self._azimuth_facade_entity_id = "input_number.g01_azimuth_facade"
        self._offset_sun_in_entity_id = "input_number.g02_offset_sun_in"
        self._offset_sun_out_entity_id = "input_number.g03_offset_sun_out"
        self._elevation_sun_min_entity_id = "input_number.g04_elevation_sun_min"
        self._elevation_sun_max_entity_id = "input_number.g05_elevation_sun_max"
        self._slat_width_entity_id = "input_number.g06_slat_with" # Korrigiert von g06_slat_with zu g06_slat_width (wahrscheinlicher Tippfehler im Helfernamen)
        self._slat_distance_entity_id = "input_number.g07_slat_distance"
        self._angle_offset_entity_id = "input_number.g08_angle_offset"
        self._min_slat_angle_entity_id = "input_number.g09_min_slat_angle"
        self._stepping_height_entity_id = "input_number.g10_stepping_height" # war g10_stepping_height
        self._stepping_angle_entity_id = "input_number.g11_stepping_angle" # war g11_stepping_angle
        self._shutter_type_entity_id = "input_select.g12_shutter_type"
        self._light_bar_width_entity_id = "input_number.g13_light_bar_width"
        self._shutter_height_entity_id = "input_number.g14_shutter_height"
        self._neutral_pos_height_entity_id = "input_number.g15_neutral_pos_height"
        self._neutral_pos_angle_entity_id = "input_number.g16_neutral_pos_angle" # Name im Helfer ggf. g16?
        self._movement_restriction_height_entity_id = "input_select.g17_movement_restriction_height"
        self._movement_restriction_angle_entity_id = "input_select.g18_movement_restriction_angle"
        self._update_lock_output_entity_id = "input_select.g19_update_lock_output"

        # === Beschattungseinstellungen (Test-Helfer) ===
        self._shadow_control_enabled_entity_id = "input_select.s01_shadow_control_enabled"
        self._shadow_brightness_level_entity_id = "input_number.s02_shadow_brightness_level"
        self._shadow_after_seconds_entity_id = "input_number.s03_shadow_after_seconds"
        self._shadow_max_height_entity_id = "input_number.s04_shadow_max_height"
        self._shadow_max_angle_entity_id = "input_number.s05_shadow_max_angle"
        self._shadow_look_through_seconds_entity_id = "input_number.s06_shadow_look_through_seconds"
        self._shadow_open_seconds_entity_id = "input_number.s07_shadow_open_seconds"
        self._shadow_look_through_angle_entity_id = "input_number.s08_shadow_look_through_angle"
        self._after_shadow_height_entity_id = "input_number.s09_after_shadow_height"
        self._after_shadow_angle_entity_id = "input_number.s10_after_shadow_angle"

        # === Dämmerungseinstellungen (Test-Helfer) ===
        self._dawn_control_enabled_entity_id = "input_select.sd01_dawn_control_enabled"
        self._dawn_brightness_level_entity_id = "input_number.sd02_dawn_brightness_level"
        self._dawn_after_seconds_entity_id = "input_number.sd03_dawn_after_seconds"
        self._dawn_max_height_entity_id = "input_number.sd04_dawn_max_height"
        self._dawn_max_angle_entity_id = "input_number.sd05_dawn_max_angle"
        self._dawn_look_through_seconds_entity_id = "input_number.sd06_dawn_look_through_seconds" # Name im Helfer ggf. sd06?
        self._dawn_open_seconds_entity_id = "input_number.sd07_dawn_open_seconds"
        self._dawn_look_through_angle_entity_id = "input_number.sd08_dawn_look_through_angle"
        self._after_dawn_height_entity_id = "input_number.sd09_after_dawn_height"
        self._after_dawn_angle_entity_id = "input_number.sd10_after_dawn_angle"

        # Die zu steuernde Cover-Entität (Ihr Template-Cover)
        # Diese sollte weiterhin aus der YAML-Konfiguration kommen, da sie essenziell ist.
        self._target_cover_entity_id = config.get("cover") # Aus configuration.yaml

        # Logging der (fest verdrahteten) Entitäts-IDs
        _LOGGER.debug(f"--- {self._name}: Initialized with fixed Entity IDs ---")
        _LOGGER.debug(f"Target Cover Entity ID: {self._target_cover_entity_id}")
        _LOGGER.debug(f"Brightness Entity ID: {self._brightness_entity_id}")
        _LOGGER.debug(f"Sun Elevation Entity ID: {self._sun_elevation_entity_id}")
        _LOGGER.debug(f"Facade Azimuth Entity ID: {self._azimuth_facade_entity_id}")
        # Fügen Sie hier weitere _LOGGER.debug-Zeilen für alle anderen _entity_id-Variablen hinzu

        # Initialwerte für Position und Neigung (optional, falls benötigt)
        self._current_position: int | None = None
        self._current_tilt_position: int | None = None

        # Hier können Sie auch direkt die Werte der Helfer beim Start loggen,
        # aber es ist besser, das in async_added_to_hass oder async_update zu tun,
        # da die Zustände dort zuverlässiger verfügbar sind.

    async def _log_current_input_values(self) -> None:
        """Logs the current values of all input entities."""
        _LOGGER.debug(f"--- {self._name}: Current Input Values ---")
        try:
            # Dynamische Eingänge
            _LOGGER.debug(f"Brightness: {self._get_state_value(self._brightness_entity_id)}")
            _LOGGER.debug(f"Brightness Dawn: {self._get_state_value(self._brightness_dawn_entity_id)}")
            _LOGGER.debug(f"Sun Elevation: {self._get_state_value(self._sun_elevation_entity_id)}")
            _LOGGER.debug(f"Sun Azimuth: {self._get_state_value(self._sun_azimuth_entity_id)}")
            _LOGGER.debug(f"Shutter Current Height: {self._get_state_value(self._shutter_current_height_entity_id)}")
            _LOGGER.debug(f"Shutter Current Angle: {self._get_state_value(self._shutter_current_angle_entity_id)}")
            _LOGGER.debug(f"Lock Integration: {self._get_state_value(self._lock_integration_entity_id)}")
            _LOGGER.debug(f"Lock Integration w. Position: {self._get_state_value(self._lock_integration_with_position_entity_id)}")
            _LOGGER.debug(f"Lock Height: {self._get_state_value(self._lock_height_entity_id)}")
            _LOGGER.debug(f"Lock Angle: {self._get_state_value(self._lock_angle_entity_id)}")
            _LOGGER.debug(f"Tolerance Height: {self._get_state_value(self._modification_tolerance_height_entity_id)}")
            _LOGGER.debug(f"Tolerance Angle: {self._get_state_value(self._modification_tolerance_angle_entity_id)}")

            # Allgemeine Einstellungen
            _LOGGER.debug(f"Facade Azimuth: {self._get_state_value(self._azimuth_facade_entity_id)}")
            _LOGGER.debug(f"Offset Sun In: {self._get_state_value(self._offset_sun_in_entity_id)}")
            # ... Fügen Sie hier Logs für ALLE anderen Gxx, Sxx, SDxx Helfer hinzu ...
            # Beispiel für einen weiteren allgemeinen Parameter:
            _LOGGER.debug(f"Slat Width: {self._get_state_value(self._slat_width_entity_id)}")
            # (usw. für alle anderen)

        except Exception as e:
            _LOGGER.error(f"Error logging input values: {e}")

    def _get_state_value(self, entity_id: str | None) -> str | None:
        """Helper to get the state of an entity."""
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if state:
            return state.state
        return None

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

    # Optional: Methoden für Tilt, falls unterstützt
    # async def async_set_cover_tilt_position(self, **kwargs: any) -> None:
    #     tilt_position = kwargs[ATTR_TILT_POSITION]
    #     _LOGGER.info(f"{self._name}: Setting cover tilt to {tilt_position}")
    #     # Rufen Sie hier Ihr Skript für die Neigung auf
    #     self.async_write_ha_state()

    async def async_update(self) -> None:
        """Fetch new state data for the cover. (Hier implementieren Sie Ihre Logik)"""
        _LOGGER.debug(f"{self._name}: Updating state...")
        await self._log_current_input_values() # Loggt die aktuellen Werte bei jedem Update

        # === Beispielhafte Logik (Platzhalter) ===
        # Hier würden Sie die Werte Ihrer Sensoren und Helfer auslesen
        # und basierend darauf entscheiden, ob und wie das Cover bewegt werden soll.

        # Beispiel: Werte auslesen
        try:
            current_brightness_state = self.hass.states.get(self._brightness_entity_id)
            current_sun_elevation_state = self.hass.states.get(self._sun_elevation_entity_id)
            facade_azimuth_state = self.hass.states.get(self._azimuth_facade_entity_id)
            shadow_control_enabled_state = self.hass.states.get(self._shadow_control_enabled_entity_id)

            if not all([current_brightness_state, current_sun_elevation_state, facade_azimuth_state, shadow_control_enabled_state]):
                _LOGGER.warning(f"{self._name}: One or more input entities are not available.")
                return

            current_brightness = float(current_brightness_state.state)
            current_sun_elevation = float(current_sun_elevation_state.state)
            facade_azimuth = float(facade_azimuth_state.state)
            is_shadow_control_enabled = shadow_control_enabled_state.state == "enabled" # Annahme für input_select

            _LOGGER.debug(
                f"{self._name}: "
                f"Brightness={current_brightness}, "
                f"Elevation={current_sun_elevation}, "
                f"FacadeAzimuth={facade_azimuth}, "
                f"ShadowCtrlEnabled={is_shadow_control_enabled}"
            )

            # Ihre komplexe Logik hier...
            # if is_shadow_control_enabled and current_brightness > 50000 and current_sun_elevation > 20:
            #     _LOGGER.info(f"{self._name}: Conditions met for closing cover.")
            #     # await self.async_set_cover_position(position=10) # Beispiel: Schließen auf 10%
            # else:
            #     _LOGGER.info(f"{self._name}: Conditions not met for closing cover.")
            #     # await self.async_set_cover_position(position=90) # Beispiel: Öffnen auf 90%

        except ValueError as e:
            _LOGGER.error(f"{self._name}: Error converting sensor value to float: {e}")
        except Exception as e:
            _LOGGER.error(f"{self._name}: Unexpected error during update: {e}")

        # Am Ende jedes Updates den Zustand schreiben, falls er sich geändert haben könnte
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

    async def async_setup(self):
        """Set up the Shadow Control by listening to sensor states."""
        async def sensor_state_listener(entity_id, old_state, new_state):
            """Handle state changes of the tracked sensors."""
            if new_state is None:
                return
            self._perform_computation = True
            await self.async_update_ha_state(True)  # Force an immediate update

        # Listen for state changes of the elevation entity
        async_track_state_change_event(
            self.hass, self._sun_elevation_entity_id, sensor_state_listener
        )

        # Listen for state changes of the azimuth entity
        async_track_state_change_event(
            self.hass, self._sun_azimuth_entity_id, sensor_state_listener
        )

        # Listen for state changes of the brightness entity
        async_track_state_change_event(
            self.hass, self._brightness_entity_id, sensor_state_listener
        )

        # Listen for state changes of the dawn brightness entity (if configured)
        if self._brightness_dawn_entity_id:
            async_track_state_change_event(
                self.hass, self._brightness_dawn_entity_id, sensor_state_listener
            )

        # Listen for state changes of the shadow handling activation entity
        async_track_state_change_event(
            self.hass, self._shadow_handling_activation_entity_id, sensor_state_listener
        )

        # Listen for state changes of the dawn handling activation entity
        async_track_state_change_event(
            self.hass, self._dawn_handling_activation_entity_id, sensor_state_listener
        )

        # Listen for state changes of the cover entity (to track its current position)
        if self._controlled_cover_entity_id:
            async def cover_state_listener(entity_id, old_state, new_state):
                """Handle state changes of the controlled cover entity."""
                if new_state and "current_cover_position" in new_state.attributes:
                    self._target_position = new_state.attributes["current_cover_position"]
                    self._is_closed = (self._target_position == 0)
                    self.async_schedule_update_ha_state()

            async_track_state_change_event(
                self.hass, self._controlled_cover_entity_id, cover_state_listener
            )

        # Optionally listen for lock entity state changes
        if self._lock_angle_entity_id:
            async def lock_state_listener(entity_id, old_state, new_state):
                """Handle state changes of the lock entity."""
                if new_state and new_state.state in ("locked", "unlocked"):
                    self._is_locked = (new_state.state == "locked")
                    self.async_schedule_update_ha_state()

            async_track_state_change_event(
                self.hass, self._lock_angle_entity_id, lock_state_listener
            )

        # Optionally listen for lock with forced position entity state changes
        # (Implement similar logic as for _lock_angle_entity_id if needed)

        # No direct control here, the ShadowControlledCover handles commands
        pass

    async def async_set_cover_tilt(self, **kwargs: any) -> None:
        """Set the tilt of the cover."""
        if (tilt := kwargs.get("tilt")) is not None:
            _LOGGER.debug(f"Set cover tilt to {tilt}")
            self._target_tilt = tilt
            await self._perform_state_handling()

    async def async_added_to_hass(self) -> None:
        """Subscribe to sensor events."""
        await super().async_added_to_hass()
        async_track_state_change_event(
            self.hass,
            [
                self._sun_elevation_entity_id,
                self._sun_azimuth_entity_id,
                self._brightness_entity_id,
                self._brightness_dawn_entity_id,
                self._lock_angle_entity_id,
                self._lock_forced_entity_id,
                self._height_entity_id,
                self._angle_entity_id,
                self._shadow_handling_activation_entity_id,
                self._dawn_handling_activation_entity_id,
            ],
            self._async_sensor_changed,
        )
        # Initial run finished
        self._initial_lbs_run_finished = True
        self._debug(True, "Initial LBS run finished")
        await self._perform_state_handling()

    @callback
    async def _async_sensor_changed(self, entity_id, old_state, new_state):
        """Handle sensor state changes."""
        if new_state is None:
            return
        self._debug(True, f"Sensor {entity_id} changed to {new_state.state}")
        await self._perform_state_handling()

    async def _perform_state_handling(self):
        """Handle the state machine and trigger actions."""
        new_state = await self._calculate_state()
        if new_state != self._current_shutter_state:
            self._debug(
                True, f"State changed from {self._current_shutter_state} to {new_state}"
            )
            self._current_shutter_state = new_state
            # Potentially trigger another state calculation if needed
            await self._perform_state_handling()
        else:
            self._debug(True, f"Current state: {self._current_shutter_state}")
            # Perform actions based on the current state
            method_name = f"_handle_state_{self._current_shutter_state.lower()}"
            if hasattr(self, method_name):
                next_state = await getattr(self, method_name)()
                if next_state and next_state != self._current_shutter_state:
                    self._debug(
                        True, f"State handling requested transition to {next_state}"
                    )
                    self._current_shutter_state = next_state
                    await self._perform_state_handling()

    async def _calculate_state(self) -> str:
        """Determine the current state based on sensor values and conditions."""
        self._debug(True, "=== Calculating shutter state... ===")
        current_state = self._current_shutter_state
        new_state = self.STATE_NEUTRAL

        if (
            await self._is_shadow_handling_activated() and not await self._is_in_sun()
        ) or (
            await self._is_dawn_handling_activated() and await self._is_dawn_active()
        ):
            new_state = await self._get_appropriate_closed_state(current_state)
        elif await self._is_in_sun() and await self._is_shadow_handling_activated():
            new_state = await self._get_appropriate_sun_state(current_state)
        elif (
            await self._is_dawn_handling_activated()
            and not await self._is_dawn_active()
        ):
            new_state = await self._get_appropriate_dawn_open_state(current_state)
        else:
            new_state = self.STATE_NEUTRAL

        self._debug(
            True, f"=== Calculated new state: {new_state} (was: {current_state}) ==="
        )
        return new_state

    async def _get_appropriate_closed_state(self, current_state: str) -> str:
        """Determine the appropriate closed state (shadow or dawn)."""
        if await self._is_shadow_handling_activated() and not await self._is_in_sun():
            return self.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING
        elif await self._is_dawn_handling_activated() and await self._is_dawn_active():
            return self.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING
        return self.STATE_NEUTRAL

    async def _get_appropriate_sun_state(self, current_state: str) -> str:
        """Determine the appropriate state when the sun is shining."""
        # Placeholder logic - needs more detailed implementation
        return self.STATE_SHADOW_OPEN_SLATS_TIMER_RUNNING

    async def _get_appropriate_dawn_open_state(self, current_state: str) -> str:
        """Determine the appropriate state after dawn."""
        return self.STATE_DAWN_OPEN_SHUTTER_TIMER_RUNNING

    async def _is_shadow_handling_activated(self) -> bool:
        """Check if shadow handling is activated."""
        state = self.hass.states.get(self._shadow_handling_activation_entity_id)
        return state.state.lower() == "on" if state else False

    async def _is_dawn_handling_activated(self) -> bool:
        """Check if dawn handling is activated."""
        state = self.hass.states.get(self._dawn_handling_activation_entity_id)
        return state.state.lower() == "on" if state else False

    async def _is_lbs_locked(self) -> bool:
        """Check if the cover is locked."""
        state = self.hass.states.get(self._lock_angle_entity_id)
        return state.state.lower() == "locked" if state else False

    async def _is_lbs_forced_locked(self) -> bool:
        """Check if the cover is forced locked."""
        state = self.hass.states.get(self._lock_forced_entity_id)
        return state.state.lower() == "locked" if state else False

    async def _is_lbs_locked_in_either_way(self) -> bool:
        """Check if the cover is locked in any way."""
        return await self._is_lbs_locked() or await self._is_lbs_forced_locked()

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
        self._debug(
            True,
            f"Timer started for {delay} seconds. Finish time: {self._timer_finish_time}",
        )

    async def _is_timer_finished(self) -> bool:
        """Check if the current time is after the timer finish time."""
        return self.hass.loop.time() >= self._timer_finish_time

    async def _stop_timer(self) -> None:
        """Stop the active timer."""
        self._timer_finish_time = 0
        self._debug(True, "Timer stopped.")

    async def _calculate_shutter_height(self) -> float | None:
        """Calculate the target shutter height based on current conditions."""
        elevation = await self._get_input_value("elevation")
        elevation_min = await self._get_input_value("elevation_min")
        elevation_max = await self._get_input_value("elevation_max")
        shadow_max_height = await self._get_input_value("shadow_max_height")

        if (
            elevation is None
            or elevation_min is None
            or elevation_max is None
            or shadow_max_height is None
        ):
            return None

        # Placeholder for actual calculation logic
        effective_elevation = elevation  # For now, use raw elevation
        height_percent = (
            100
            - ((effective_elevation - elevation_min) / (elevation_max - elevation_min))
            * shadow_max_height
        )
        return max(0.0, min(100.0, height_percent))

    async def _calculate_shutter_angle(self) -> float | None:
        """Calculate the target shutter angle based on current conditions."""
        azimuth = await self._get_input_value("azimuth")
        facade_angle = await self._get_input_value("facade_angle")
        facade_offset_start = await self._get_input_value("facade_offset_start")
        facade_offset_end = await self._get_input_value("facade_offset_end")
        angle_offset = await self._get_input_value("angle_offset")
        min_shutter_angle = await self._get_input_value("min_shutter_angle")
        shadow_max_angle = await self._get_input_value("shadow_max_angle")

        if (
            azimuth is None
            or facade_angle is None
            or facade_offset_start is None
            or facade_offset_end is None
            or angle_offset is None
            or min_shutter_angle is None
            or shadow_max_angle is None
        ):
            return None

        relative_azimuth = (azimuth - facade_angle + 360) % 360
        if facade_offset_start <= relative_azimuth <= (360 + facade_offset_end) % 360:
            angle_percent = min_shutter_angle + (
                (relative_azimuth - facade_offset_start)
                / (
                    facade_offset_end - facade_offset_start + 360
                    if facade_offset_end < facade_offset_start
                    else facade_offset_end - facade_offset_start
                )
            ) * (shadow_max_angle - min_shutter_angle)
            return max(0.0, min(100.0, angle_percent))
        return float(self._angle_neutral)  # Default to neutral if not in facade range

    async def _position_shutter(
        self,
        height_percent: float | None,
        angle_percent: float | None,
        direction: int,
        force: bool,
        stop_timer: bool = False,
    ) -> None:
        """Write computed values to the outputs and update member variables."""
        self._debug(
            True,
            f"positionShutter(...), Werte für Höhe/Winkel: {height_percent}%/{angle_percent}%, Richtung: {direction}, Force: {force}, Stop Timer: {stop_timer}",
        )
        if (
            self._initial_lbs_run_finished
            and not await self._is_lbs_locked_in_either_way()
        ):
            # Hier die Logik von LB_LBSID_positionShutter implementieren,
            # inklusive _send_by_change und Berücksichtigung der Bewegungsrichtung
            if height_percent is not None:
                self._target_position = (
                    int(
                        round(height_percent / self._shutter_height_stepping)
                        * self._shutter_height_stepping
                    )
                    if self._shutter_height_stepping > 0
                    else int(round(height_percent))
                )
                await self._send_by_change("position", self._target_position)
            if angle_percent is not None:
                self._target_tilt = (
                    int(
                        round(angle_percent / self._shutter_angle_stepping)
                        * self._shutter_angle_stepping
                    )
                    if self._shutter_angle_stepping > 0
                    else int(round(angle_percent))
                )
                await self._send_by_change("tilt", self._target_tilt)

        if stop_timer:
            await self._stop_timer()

    async def _send_by_change(self, attribute: str, value: any) -> None:
        """Send the value only if it has changed."""
        current_value = getattr(self, f"_current_{attribute}", None)
        if current_value != value:
            self._debug(
                True,
                f"Attribute '{attribute}' changed from '{current_value}' to '{value}', updating...",
            )
            setattr(self, f"_current_{attribute}", value)
            self.async_write_ha_state()

    async def _is_in_sun(self) -> bool:
        """Prüft, ob die Sonne im relevanten Azimut- und Elevationsbereich ist."""
        elevation = await self._get_input_value("elevation")
        elevation_min = await self._get_input_value("elevation_min")
        elevation_max = await self._get_input_value("elevation_max")

        if elevation is None or elevation_min is None or elevation_max is None:
            return False

        is_elevation_in_range = elevation_min <= elevation <= elevation_max
        self._debug(
            True,
            f"Prüfe Sonneneinfall: Azimut im Bereich: {self._sun_illuminates_facade}, Elevation im Bereich: {is_elevation_in_range}",
        )
        return self._sun_illuminates_facade and is_elevation_in_range

    async def _check_if_facade_is_in_sun(self) -> None:
        """Calculate if the given facade is illuminated by the sun."""
        self._debug(True, "=== Checking if facade is in sun... ===")

        azimuth = await self._get_input_value("azimuth")
        facade_angle = await self._get_input_value("facade_angle")
        facade_offset_start = await self._get_input_value("facade_offset_start")
        facade_offset_end = await self._get_input_value("facade_offset_end")
        min_elevation = await self._get_input_value("elevation_min")
        max_elevation = await self._get_input_value("elevation_max")
        current_elevation = await self._get_input_value("elevation")

        if (
            azimuth is None
            or facade_angle is None
            or facade_offset_start is None
            or facade_offset_end is None
            or min_elevation is None
            or max_elevation is None
            or current_elevation is None
        ):
            self._debug(
                False,
                "Nicht alle erforderlichen Sonnen- oder Fassadendaten verfügbar für die Prüfung des Sonneneinfalls.",
            )
            return

        sun_entry_angle = facade_angle - abs(facade_offset_start)
        sun_exit_angle = facade_angle + abs(facade_offset_end)
        if sun_entry_angle < 0:
            sun_entry_angle = 360 - abs(sun_entry_angle)
        if sun_exit_angle >= 360:
            sun_exit_angle %= 360

        sun_exit_angle_calc = sun_exit_angle - sun_entry_angle
        if sun_exit_angle_calc < 0:
            sun_exit_angle_calc += 360
        azimuth_calc = azimuth - sun_entry_angle
        if azimuth_calc < 0:
            azimuth_calc += 360

        is_azimuth_in_range = 0 <= azimuth_calc <= sun_exit_angle_calc
        message = f"=== Finished facade check, real azimuth {azimuth}° and facade at {facade_angle}° -> "
        if is_azimuth_in_range:
            message += f"IN SUN (from {sun_entry_angle}° to {sun_exit_angle}°)"
            self._sun_illuminates_facade = True
            await self._send_by_change("sun_at_facade_azimuth", True)
            effective_elevation = await self._calculate_effective_elevation()
        else:
            message += f"NOT IN SUN (shadow side, at sun from {sun_entry_angle}° to {sun_exit_angle}°)"
            self._sun_illuminates_facade = False
            await self._send_by_change("sun_at_facade_azimuth", False)
            effective_elevation = None

        await self._send_by_change("effective_elevation", effective_elevation)

        message += f", effective elevation {effective_elevation}° for given elevation of {current_elevation}°"
        is_elevation_in_range = False
        if isinstance(
            effective_elevation, (int, float)
        ) and await self._get_input_value(
            "elevation_min"
        ) <= effective_elevation <= await self._get_input_value("elevation_max"):
            message += f"° -> in min-max-range ({await self._get_input_value('elevation_min')}-{await self._get_input_value('elevation_max')})"
            self._is_between_min_max_elevation = True
            is_elevation_in_range = True
            await self._send_by_change("sun_at_facade_elevation", True)
        else:
            message += f"° -> NOT in min-max-range ({await self._get_input_value('elevation_min')}-{await self._get_input_value('elevation_max')})"
            self._is_between_min_max_elevation = False
            await self._send_by_change("sun_at_facade_elevation", False)
        self._debug(True, message + " ===")

        # Setze _is_in_sun basierend auf beiden Bedingungen
        # self._is_in_sun = is_azimuth_in_range and is_elevation_in_range # Wird nun in _calculate_state gemacht

    async def _is_dawn_active(self) -> bool:
        """Check if the current brightness is below the dawn threshold."""
        brightness_dawn = await self._get_input_value("brightness_dawn")
        dawn_threshold_close = await self._get_input_value("dawn_threshold_close")
        return (
            brightness_dawn is not None
            and dawn_threshold_close is not None
            and brightness_dawn < dawn_threshold_close
        )

    async def _calculate_effective_elevation(self) -> float | None:
        """Berechnet die effektive Elevation der Sonne relativ zur Fassade."""
        elevation = await self._get_input_value("elevation")
        azimuth = await self._get_input_value("azimuth")
        facade_angle = await self._get_input_value("facade_angle")

        if elevation is None or azimuth is None or facade_angle is None:
            self._debug(
                False,
                "Kann effektive Elevation nicht berechnen: Nicht alle erforderlichen Eingabewerte sind verfügbar.",
            )
            return None

        try:
            elevation = float(elevation)
            azimuth = float(azimuth)
            facade_angle = float(facade_angle)

            virtual_depth = math.cos(math.radians(abs(azimuth - facade_angle)))
            virtual_height = math.tan(math.radians(elevation))

            # Vermeide Division durch Null, falls virtual_depth sehr klein ist
            if abs(virtual_depth) < 1e-9:
                effective_elevation = 90.0 if virtual_height > 0 else -90.0
            else:
                effective_elevation = math.degrees(
                    math.atan(virtual_height / virtual_depth)
                )

            self._debug(
                True,
                f"Virtuelle Tiefe und Höhe der Sonnenposition in 90° zur Fassade: {virtual_depth}, {virtual_height}, effektive Elevation: {effective_elevation}",
            )
            return effective_elevation
        except ValueError:
            self._debug(
                False,
                "Kann effektive Elevation nicht berechnen: Ungültige numerische Eingabewerte.",
            )
            return None
        except ZeroDivisionError:
            self._debug(
                False, "Kann effektive Elevation nicht berechnen: Division durch Null."
            )
            return None

    async def _handle_state_neutral(self) -> str:
        """Implementierung der Logik für den Zustand NEUTRAL."""
        if await self._is_lbs_locked_in_either_way():
            self._debug(
                True, f"Zustand {self.STATE_NEUTRAL}: LBS ist gesperrt, keine Aktion."
            )
            return self.STATE_NEUTRAL

        if await self._is_in_sun() and await self._is_shadow_handling_activated():
            current_brightness = await self._get_input_value("brightness")
            shadow_threshold_close = await self._get_input_value(
                "shadow_threshold_close"
            )
            shadow_close_delay = await self._get_input_value("shadow_close_delay")
            if (
                current_brightness is not None
                and shadow_threshold_close is not None
                and current_brightness > shadow_threshold_close
                and shadow_close_delay is not None
            ):
                self._debug(
                    True,
                    f"Zustand {self.STATE_NEUTRAL}: Helligkeit ({current_brightness}) über Schatten-Schwellwert ({shadow_threshold_close}), starte Timer für {self.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING} ({shadow_close_delay}s)",
                )
                await self._start_timer(shadow_close_delay)
                return self.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING

        if await self._is_dawn_handling_activated():
            dawn_brightness = await self._get_input_value("brightness_dawn")
            dawn_threshold_close = await self._get_input_value("dawn_threshold_close")
            dawn_close_delay = await self._get_input_value("dawn_close_delay")
            if (
                dawn_brightness is not None
                and dawn_threshold_close is not None
                and dawn_brightness < dawn_threshold_close
                and dawn_close_delay is not None
            ):
                self._debug(
                    True,
                    f"Zustand {self.STATE_NEUTRAL}: Dämmerungsbehandlung aktiv und Helligkeit ({dawn_brightness}) unter Dämmerungs-Schwellwert ({dawn_threshold_close}), starte Timer für {self.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING} ({dawn_close_delay}s)",
                )
                await self._start_timer(dawn_close_delay)
                return self.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING

        neutral_height = await self._get_input_value("height_neutral")
        neutral_angle = await self._get_input_value("angle_neutral")
        if neutral_height is not None and neutral_angle is not None:
            await self._position_shutter(
                float(neutral_height),
                float(neutral_angle),
                0,  # Richtung: Neutral
                force=True,
                stop_timer=False,
            )
            self._debug(
                True,
                f"Zustand {self.STATE_NEUTRAL}: Bewege Behang in Neutralposition ({neutral_height}%, {neutral_angle}%).",
            )
        return self.STATE_NEUTRAL

    async def _handle_state_shadow_full_close_timer_running(self) -> str:
        """Implementierung der Logik für den Zustand SHADOW_FULL_CLOSE_TIMER_RUNNING."""
        if await self._is_lbs_locked_in_either_way():
            self._debug(
                True,
                f"Zustand {self.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING}: LBS ist gesperrt, keine Aktion.",
            )
            return self.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING

        if await self._is_in_sun() and await self._is_shadow_handling_activated():
            current_brightness = await self._get_input_value("brightness")
            shadow_threshold_close = await self._get_input_value(
                "shadow_threshold_close"
            )
            if (
                current_brightness is not None
                and shadow_threshold_close is not None
                and current_brightness > shadow_threshold_close
            ):
                if await self._is_timer_finished():
                    target_height = await self._calculate_shutter_height()
                    target_angle = await self._calculate_shutter_angle()
                    if target_height is not None and target_angle is not None:
                        await self._position_shutter(
                            target_height,
                            target_angle,
                            -1,  # Richtung: Schliessen/Abwärts
                            force=False,
                            stop_timer=True,
                        )
                        self._debug(
                            True,
                            f"Zustand {self.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING}: Timer abgelaufen, Helligkeit hoch genug, fahre in Vollschatten ({target_height}%, {target_angle}%) und gehe zu {self.STATE_SHADOW_FULL_CLOSED}",
                        )
                        return self.STATE_SHADOW_FULL_CLOSED
                    else:
                        self._debug(
                            False,
                            f"Zustand {self.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING}: Fehler beim Berechnen der Schattenhöhe oder des Winkels, bleibe in {self.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING}",
                        )
                        return self.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING
                else:
                    self._debug(
                        True,
                        f"Zustand {self.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING}: Warte auf Timer (Helligkeit hoch genug)...",
                    )
                    return self.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING
            else:
                self._debug(
                    True,
                    f"Zustand {self.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING}: Helligkeit ({current_brightness}) nicht höher als Schwellwert ({shadow_threshold_close}), gehe zu {self.STATE_SHADOW_NEUTRAL}",
                )
                await self._stop_timer()
                return self.STATE_SHADOW_NEUTRAL
        else:
            neutral_height = await self._get_input_value("height_neutral")
            neutral_angle = await self._get_input_value("angle_neutral")
            if neutral_height is not None and neutral_angle is not None:
                await self._position_shutter(
                    float(neutral_height),
                    float(neutral_angle),
                    0,  # Richtung: Neutral
                    force=True,  # Force
                    stop_timer=True,  # Stop Timer
                )
                self._debug(
                    True,
                    f"Zustand {self.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING}: Nicht in Sonne oder Schattenmodus deaktiviert, fahre in Neutralposition ({neutral_height}%, {neutral_angle}%) und gehe zu {self.STATE_NEUTRAL}",
                )
                return self.STATE_NEUTRAL
            else:
                self._debug(
                    False,
                    f"Zustand {self.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING}: Neutrale Höhe oder Winkel nicht konfiguriert, gehe zu {self.STATE_NEUTRAL}",
                )
                return self.STATE_NEUTRAL

        # Entsprechung zu LB_LBSID_positionShutterWithPreviousValues
        self._debug(
            True,
            f"Zustand {self.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING}: Beibehalte vorherige Position.",
        )
        return self.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING

    async def _handle_state_shadow_full_closed(self) -> str:
        """Implementierung der Logik für den Zustand SHADOW_FULL_CLOSED."""
        if await self._is_lbs_locked_in_either_way():
            self._debug(
                True,
                f"Zustand {self.STATE_SHADOW_FULL_CLOSED}: LBS ist gesperrt, keine Aktion.",
            )
            return self.STATE_SHADOW_FULL_CLOSED

        if await self._is_in_sun() and await self._is_shadow_handling_activated():
            current_brightness = await self._get_input_value("brightness")
            shadow_threshold_close = await self._get_input_value(
                "shadow_threshold_close"
            )
            shadow_open_slat_delay = await self._get_input_value(
                "shadow_open_slat_delay"
            )
            if (
                current_brightness is not None
                and shadow_threshold_close is not None
                and shadow_open_slat_delay is not None
                and current_brightness < shadow_threshold_close
            ):
                self._debug(
                    True,
                    f"Zustand {self.STATE_SHADOW_FULL_CLOSED}: Helligkeit ({current_brightness}) unter Schwellwert ({shadow_threshold_close}), starte Timer für {self.STATE_SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING} ({shadow_open_slat_delay}s)",
                )
                await self._start_timer(shadow_open_slat_delay)
                return self.STATE_SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING
            else:
                self._debug(
                    True,
                    f"Zustand {self.STATE_SHADOW_FULL_CLOSED}: Helligkeit nicht unter Schwellwert, Neuberechnung der Schattenposition.",
                )
                target_height = await self._calculate_shutter_height()
                target_angle = await self._calculate_shutter_angle()
                if target_height is not None and target_angle is not None:
                    await self._position_shutter(
                        target_height,
                        target_angle,
                        1,  # Richtung: Öffnen/Aufwärts (für Anpassung innerhalb des Schattenmodus)
                        force=True,
                        stop_timer=False,
                    )
                return self.STATE_SHADOW_FULL_CLOSED
        else:
            neutral_height = await self._get_input_value("height_neutral")
            neutral_angle = await self._get_input_value("angle_neutral")
            if neutral_height is not None and neutral_angle is not None:
                await self._position_shutter(
                    float(neutral_height),
                    float(neutral_angle),
                    0,  # Richtung: Neutral
                    force=True,
                    stop_timer=True,  # Stop Timer
                )
                self._debug(
                    True,
                    f"Zustand {self.STATE_SHADOW_FULL_CLOSED}: Nicht in Sonne oder Schattenmodus deaktiviert, fahre in Neutralposition ({neutral_height}%, {neutral_angle}%) und gehe zu {self.STATE_NEUTRAL}",
                )
                return self.STATE_NEUTRAL
            else:
                self._debug(
                    False,
                    f"Zustand {self.STATE_SHADOW_FULL_CLOSED}: Neutrale Höhe oder Winkel nicht konfiguriert, gehe zu {self.STATE_NEUTRAL}",
                )
                return self.STATE_NEUTRAL

        # Entsprechung zu LB_LBSID_positionShutterWithPreviousValues
        self._debug(
            True,
            f"Zustand {self.STATE_SHADOW_FULL_CLOSED}: Beibehalte vorherige Position.",
        )
        return self.STATE_SHADOW_FULL_CLOSED

    async def _handle_state_shadow_open_shutter_timer_running(self) -> str:
        """Implementierung der Logik für den Zustand SHADOW_OPEN_SHUTTER_TIMER_RUNNING."""
        if await self._is_lbs_locked_in_either_way():
            self._debug(
                True,
                f"Zustand {self.STATE_SHADOW_OPEN_SHUTTER_TIMER_RUNNING}: LBS ist gesperrt, keine Aktion.",
            )
            return self.STATE_SHADOW_OPEN_SHUTTER_TIMER_RUNNING

        if await self._is_timer_finished():
            shadow_open_height = await self._get_input_value("height_after_shadow")
            shadow_open_angle = await self._get_input_value("angle_after_shadow")
            if shadow_open_height is not None and shadow_open_angle is not None:
                await self._position_shutter(
                    float(shadow_open_height),
                    float(shadow_open_angle),
                    1,  # Richtung: Öffnen/Aufwärts
                    force=False,
                    stop_timer=True,
                )
                self._debug(
                    True,
                    f"Zustand {self.STATE_SHADOW_OPEN_SHUTTER_TIMER_RUNNING}: Timer abgelaufen, fahre in Schatten-Offen Position ({shadow_open_height}%, {shadow_open_angle}%) und gehe zu {self.STATE_SHADOW_PARTIALLY_OPEN}",
                )
                return self.STATE_SHADOW_PARTIALLY_OPEN
            else:
                self._debug(
                    False,
                    f"Zustand {self.STATE_SHADOW_OPEN_SHUTTER_TIMER_RUNNING}: Höhe oder Winkel für Schatten-Offen nicht konfiguriert, gehe zu {self.STATE_NEUTRAL}",
                )
                return self.STATE_NEUTRAL
        else:
            self._debug(
                True,
                f"Zustand {self.STATE_SHADOW_OPEN_SHUTTER_TIMER_RUNNING}: Warte auf Timer...",
            )
            return self.STATE_SHADOW_OPEN_SHUTTER_TIMER_RUNNING

    async def _handle_state_shadow_partially_open(self) -> str:
        """Implementierung der Logik für den Zustand SHADOW_PARTIALLY_OPEN."""
        if await self._is_lbs_locked_in_either_way():
            self._debug(
                True,
                f"Zustand {self.STATE_SHADOW_PARTIALLY_OPEN}: LBS ist gesperrt, keine Aktion.",
            )
            return self.STATE_SHADOW_PARTIALLY_OPEN

        if await self._is_in_sun() and await self._is_shadow_handling_activated():
            shadow_open_slat_delay = await self._get_input_value(
                "shadow_open_slat_delay"
            )
            await self._start_timer(shadow_open_slat_delay)
            self._debug(
                True,
                f"Zustand {self.STATE_SHADOW_PARTIALLY_OPEN}: Sonne scheint immer noch, starte Timer ({shadow_open_slat_delay}s) zum Öffnen der Lamellen und gehe zu {self.STATE_SHADOW_OPEN_SLATS_TIMER_RUNNING}",
            )
            return self.STATE_SHADOW_OPEN_SLATS_TIMER_RUNNING
        elif (
            not await self._is_in_sun()
            or not await self._is_shadow_handling_activated()
        ):
            self._debug(
                True,
                f"Zustand {self.STATE_SHADOW_PARTIALLY_OPEN}: Sonne weg oder Schattenmodus deaktiviert, gehe zu {self.STATE_NEUTRAL}",
            )
            return self.STATE_NEUTRAL
        else:
            self._debug(
                True,
                f"Zustand {self.STATE_SHADOW_PARTIALLY_OPEN}: Warte weiterhin auf Sonneneinstrahlung...",
            )
            return self.STATE_SHADOW_PARTIALLY_OPEN

    async def _handle_state_shadow_open_slats_timer_running(self) -> str:
        """Implementierung der Logik für den Zustand SHADOW_OPEN_SLATS_TIMER_RUNNING (mit Sperrzustandsprüfung)."""
        if await self._is_lbs_locked_in_either_way():
            self._debug(
                True,
                f"Zustand {self.STATE_SHADOW_OPEN_SLATS_TIMER_RUNNING}: LBS ist gesperrt, keine Aktion.",
            )
            return self.STATE_SHADOW_OPEN_SLATS_TIMER_RUNNING

        if await self._is_timer_finished():
            neutral_angle = await self._get_input_value("angle_neutral")
            if neutral_angle is not None:
                await self._position_shutter(
                    None,  # Höhe beibehalten
                    float(neutral_angle),
                    1,  # Richtung: Öffnen/Aufwärts
                    force=False,
                    stop_timer=True,
                )
                self._debug(
                    True,
                    f"Zustand {self.STATE_SHADOW_OPEN_SLATS_TIMER_RUNNING}: Timer abgelaufen, öffne Lamellen auf Neutralwinkel und gehe zu {self.STATE_SHADOW_PARTIALLY_OPEN}",
                )
                return self.STATE_SHADOW_PARTIALLY_OPEN
            else:
                self._debug(
                    False,
                    f"Zustand {self.STATE_SHADOW_OPEN_SLATS_TIMER_RUNNING}: Neutraler Winkel nicht konfiguriert, gehe zu {self.STATE_NEUTRAL}",
                )
                return self.STATE_NEUTRAL
        else:
            self._debug(
                True,
                f"Zustand {self.STATE_SHADOW_OPEN_SLATS_TIMER_RUNNING}: Warte auf Timer...",
            )
            return self.STATE_SHADOW_OPEN_SLATS_TIMER_RUNNING

    async def _handle_state_dawn_full_close_timer_running(self) -> str:
        """Implementierung der Logik für den Zustand DAWN_FULL_CLOSE_TIMER_RUNNING."""
        if await self._is_lbs_locked_in_either_way():
            self._debug(
                True,
                f"Zustand {self.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING}: LBS ist gesperrt, keine Aktion.",
            )
            return self.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING

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
                            0,  # Richtung: Neutral
                            force=True,
                            stop_timer=True,
                        )
                        self._debug(
                            True,
                            f"Zustand {self.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING}: Timer abgelaufen, fahre in volle Dämmerungsposition ({dawn_height}%, {dawn_angle}%) und gehe zu {self.STATE_DAWN_FULL_CLOSED}",
                        )
                        return self.STATE_DAWN_FULL_CLOSED
                    else:
                        self._debug(
                            False,
                            f"Zustand {self.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING}: Dämmerungshöhe oder -winkel nicht konfiguriert, bleibe in {self.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING}",
                        )
                        return self.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING
                else:
                    self._debug(
                        True,
                        f"Zustand {self.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING}: Warte auf Timer (Helligkeit niedrig genug)...",
                    )
                    return self.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING
            else:
                self._debug(
                    True,
                    f"Zustand {self.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING}: Helligkeit ({dawn_brightness}) nicht unter Schwellwert ({dawn_threshold_close}), gehe zu {self.STATE_DAWN_NEUTRAL} und stoppe Timer.",
                )
                await self._stop_timer()
                return self.STATE_DAWN_NEUTRAL
        else:
            neutral_height = await self._get_input_value("height_neutral")
            neutral_angle = await self._get_input_value("angle_neutral")
            if neutral_height is not None and neutral_angle is not None:
                await self._position_shutter(
                    float(neutral_height),
                    float(neutral_angle),
                    0,  # Richtung: Neutral
                    force=True,
                    stop_timer=True,  # Stop Timer
                )
                self._debug(
                    True,
                    f"Zustand {self.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING}: Dämmerungsbehandlung deaktiviert, fahre in Neutralposition ({neutral_height}%, {neutral_angle}%) und gehe zu {self.STATE_NEUTRAL}",
                )
                return self.STATE_NEUTRAL
            else:
                self._debug(
                    False,
                    f"Zustand {self.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING}: Neutrale Höhe oder Winkel nicht konfiguriert, gehe zu {self.STATE_NEUTRAL}",
                )
                return self.STATE_NEUTRAL

        # Entsprechung zu LB_LBSID_positionShutterWithPreviousValues
        self._debug(
            True,
            f"Zustand {self.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING}: Beibehalte vorherige Position.",
        )
        return self.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING

    async def _handle_state_dawn_full_closed(self) -> str:
        """Implementierung der Logik für den Zustand DAWN_FULL_CLOSED."""
        if await self._is_lbs_locked_in_either_way():
            self._debug(
                True,
                f"Zustand {self.STATE_DAWN_FULL_CLOSED}: LBS ist gesperrt, keine Aktion.",
            )
            return self.STATE_DAWN_FULL_CLOSED

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
                self._debug(
                    True,
                    f"Zustand {self.STATE_DAWN_FULL_CLOSED}: Dämmerungshelligkeit ({dawn_brightness}) über Schwellwert ({dawn_threshold_close}), starte Timer für {self.STATE_DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING} ({dawn_open_slat_delay}s)",
                )
                await self._start_timer(dawn_open_slat_delay)
                return self.STATE_DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING
            elif dawn_height is not None and dawn_angle is not None:
                await self._position_shutter(
                    float(dawn_height),
                    float(dawn_angle),
                    0,  # Richtung: Neutral
                    force=True,
                    stop_timer=False,
                )
                self._debug(
                    True,
                    f"Zustand {self.STATE_DAWN_FULL_CLOSED}: Dämmerungshelligkeit nicht über Schwellwert, fahre in Dämmerungsposition ({dawn_height}%, {dawn_angle}%).",
                )
                return self.STATE_DAWN_FULL_CLOSED
            else:
                self._debug(
                    False,
                    f"Zustand {self.STATE_DAWN_FULL_CLOSED}: Dämmerungshöhe oder -winkel nicht konfiguriert, bleibe in {self.STATE_DAWN_FULL_CLOSED}",
                )
                return self.STATE_DAWN_FULL_CLOSED
        else:
            neutral_height = await self._get_input_value("height_neutral")
            neutral_angle = await self._get_input_value("angle_neutral")
            if neutral_height is not None and neutral_angle is not None:
                await self._position_shutter(
                    float(neutral_height),
                    float(neutral_angle),
                    0,  # Richtung: Neutral
                    force=True,
                    stop_timer=True,  # Stop Timer
                )
                self._debug(
                    True,
                    f"Zustand {self.STATE_DAWN_FULL_CLOSED}: Dämmerungsbehandlung deaktiviert, fahre in Neutralposition ({neutral_height}%, {neutral_angle}%) und gehe zu {self.STATE_NEUTRAL}",
                )
                return self.STATE_NEUTRAL
            else:
                self._debug(
                    False,
                    f"Zustand {self.STATE_DAWN_FULL_CLOSED}: Neutrale Höhe oder Winkel nicht konfiguriert, gehe zu {self.STATE_NEUTRAL}",
                )
                return self.STATE_NEUTRAL

        # Entsprechung zu LB_LBSID_positionShutterWithPreviousValues
        self._debug(
            True,
            f"Zustand {self.STATE_DAWN_FULL_CLOSED}: Beibehalte vorherige Position.",
        )
        return self.STATE_DAWN_FULL_CLOSED

    async def _handle_state_dawn_open_shutter_timer_running(self) -> str:
        """Implementierung der Logik für den Zustand DAWN_OPEN_SHUTTER_TIMER_RUNNING."""
        if await self._is_lbs_locked_in_either_way():
            self._debug(
                True,
                f"Zustand {self.STATE_DAWN_OPEN_SHUTTER_TIMER_RUNNING}: LBS ist gesperrt, keine Aktion.",
            )
            return self.STATE_DAWN_OPEN_SHUTTER_TIMER_RUNNING

        if await self._is_timer_finished():
            dawn_open_height = await self._get_input_value("height_after_dawn")
            dawn_open_angle = await self._get_input_value("angle_after_dawn")
            if dawn_open_height is not None and dawn_open_angle is not None:
                await self._position_shutter(
                    float(dawn_open_height),
                    float(dawn_open_angle),
                    1,  # Richtung: Öffnen/Aufwärts
                    force=False,
                    stop_timer=True,
                )
                self._debug(
                    True,
                    f"Zustand {self.STATE_DAWN_OPEN_SHUTTER_TIMER_RUNNING}: Timer abgelaufen, fahre in Dämmerungs-Offen Position ({dawn_open_height}%, {dawn_open_angle}%) und gehe zu {self.STATE_DAWN_PARTIALLY_OPEN}",
                )
                return self.STATE_DAWN_PARTIALLY_OPEN
            else:
                self._debug(
                    False,
                    f"Zustand {self.STATE_DAWN_OPEN_SHUTTER_TIMER_RUNNING}: Höhe oder Winkel für Dämmerungs-Offen nicht konfiguriert, gehe zu {self.STATE_NEUTRAL}",
                )
                return self.STATE_NEUTRAL
        else:
            self._debug(
                True,
                f"Zustand {self.STATE_DAWN_OPEN_SHUTTER_TIMER_RUNNING}: Warte auf Timer...",
            )
            return self.STATE_DAWN_OPEN_SHUTTER_TIMER_RUNNING

    async def _handle_state_dawn_partially_open(self) -> str:
        """Implementierung der Logik für den Zustand DAWN_PARTIALLY_OPEN."""
        if await self._is_lbs_locked_in_either_way():
            self._debug(
                True,
                f"Zustand {self.STATE_DAWN_PARTIALLY_OPEN}: LBS ist gesperrt, keine Aktion.",
            )
            return self.STATE_DAWN_PARTIALLY_OPEN

        if await self._is_dawn_handling_activated() and await self._is_dawn_active():
            dawn_open_slat_delay = await self._get_input_value("dawn_open_slat_delay")
            await self._start_timer(dawn_open_slat_delay)
            self._debug(
                True,
                f"Zustand {self.STATE_DAWN_PARTIALLY_OPEN}: Dämmerung aktiv, starte Timer ({dawn_open_slat_delay}s) zum Öffnen der Lamellen und gehe zu {self.STATE_DAWN_OPEN_SLATS_TIMER_RUNNING}",
            )
            return self.STATE_DAWN_OPEN_SLATS_TIMER_RUNNING
        elif (
            not await self._is_dawn_handling_activated()
            or not await self._is_dawn_active()
        ):
            self._debug(
                True,
                f"Zustand {self.STATE_DAWN_PARTIALLY_OPEN}: Dämmerungsmodus deaktiviert oder Dämmerung vorbei, gehe zu {self.STATE_NEUTRAL}",
            )
            return self.STATE_NEUTRAL
        else:
            self._debug(
                True,
                f"Zustand {self.STATE_DAWN_PARTIALLY_OPEN}: Warte weiterhin auf Ende der Dämmerung...",
            )
            return self.STATE_DAWN_PARTIALLY_OPEN

    async def _handle_state_dawn_open_slats_timer_running(self) -> str:
        """Implementierung der Logik für den Zustand DAWN_OPEN_SLATS_TIMER_RUNNING."""
        if await self._is_lbs_locked_in_either_way():
            self._debug(
                True,
                f"Zustand {self.STATE_DAWN_OPEN_SLATS_TIMER_RUNNING}: LBS ist gesperrt, keine Aktion.",
            )
            return self.STATE_DAWN_OPEN_SLATS_TIMER_RUNNING

        if await self._is_timer_finished():
            neutral_angle = await self._get_input_value("angle_neutral")
            if neutral_angle is not None:
                await self._position_shutter(
                    None,  # Höhe beibehalten
                    float(neutral_angle),
                    1,  # Richtung: Öffnen/Aufwärts
                    force=False,
                    stop_timer=True,
                )
                self._debug(
                    True,
                    f"Zustand {self.STATE_DAWN_OPEN_SLATS_TIMER_RUNNING}: Timer abgelaufen, öffne Lamellen auf Neutralwinkel und gehe zu {self.STATE_DAWN_PARTIALLY_OPEN}",
                )
                return self.STATE_DAWN_PARTIALLY_OPEN
            else:
                self._debug(
                    False,
                    f"Zustand {self.STATE_DAWN_OPEN_SLATS_TIMER_RUNNING}: Neutraler Winkel nicht konfiguriert, gehe zu {self.STATE_NEUTRAL}",
                )
                return self.STATE_NEUTRAL
        else:
            self._debug(
                True,
                f"Zustand {self.STATE_DAWN_OPEN_SLATS_TIMER_RUNNING}: Warte auf Timer...",
            )
            return self.STATE_DAWN_OPEN_SLATS_TIMER_RUNNING

    async def _handle_state_shadow_horizontal_neutral_timer_running(self) -> str:
        """Implementierung der Logik für den Zustand SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING."""
        if await self._is_lbs_locked_in_either_way():
            self._debug(
                True,
                f"Zustand {self.STATE_SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: LBS ist gesperrt, keine Aktion.",
            )
            return self.STATE_SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING

        if await self._is_in_sun() and await self._is_shadow_handling_activated():
            current_brightness = await self._get_input_value("brightness")
            shadow_threshold_close = await self._get_input_value(
                "shadow_threshold_close"
            )
            shadow_open_slat_angle = await self._get_input_value(
                "shadow_open_slat_angle"
            )
            if (
                current_brightness is not None
                and shadow_threshold_close is not None
                and current_brightness > shadow_threshold_close
            ):
                self._debug(
                    True,
                    f"Zustand {self.STATE_SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Helligkeit ({current_brightness}) wieder über Schwellwert ({shadow_threshold_close}), gehe zu {self.STATE_SHADOW_FULL_CLOSED} und stoppe Timer.",
                )
                await self._stop_timer()
                return self.STATE_SHADOW_FULL_CLOSED
            else:
                if await self._is_timer_finished():
                    target_height = await self._calculate_shutter_height()
                    if target_height is not None and shadow_open_slat_angle is not None:
                        await self._position_shutter(
                            target_height,
                            float(shadow_open_slat_angle),
                            0,  # Richtung: Neutral (da nur Winkel der Lamellen geändert wird)
                            force=True,
                            stop_timer=True,
                        )
                        self._debug(
                            True,
                            f"Zustand {self.STATE_SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Timer abgelaufen, fahre auf Höhe {target_height}% mit neutralen Lamellen ({shadow_open_slat_angle}°) und gehe zu {self.STATE_SHADOW_HORIZONTAL_NEUTRAL}",
                        )
                        return self.STATE_SHADOW_HORIZONTAL_NEUTRAL
                    else:
                        self._debug(
                            False,
                            f"Zustand {self.STATE_SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Fehler beim Berechnen der Höhe oder Winkel für offene Lamellen nicht konfiguriert, bleibe in {self.STATE_SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING}",
                        )
                        return self.STATE_SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING
                else:
                    self._debug(
                        True,
                        f"Zustand {self.STATE_SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Warte auf Timer (Helligkeit nicht hoch genug)...",
                    )
                    return self.STATE_SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING
        else:
            neutral_height = await self._get_input_value("height_neutral")
            neutral_angle = await self._get_input_value("angle_neutral")
            if neutral_height is not None and neutral_angle is not None:
                await self._position_shutter(
                    float(neutral_height),
                    float(neutral_angle),
                    0,  # Richtung: Neutral
                    force=True,
                    stop_timer=True,  # Stop Timer
                )
                self._debug(
                    True,
                    f"Zustand {self.STATE_SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Nicht in Sonne oder Schattenmodus deaktiviert, fahre in Neutralposition ({neutral_height}%, {neutral_angle}%) und gehe zu {self.STATE_NEUTRAL}",
                )
                return self.STATE_NEUTRAL
            else:
                self._debug(
                    False,
                    f"Zustand {self.STATE_SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Neutrale Höhe oder Winkel nicht konfiguriert, gehe zu {self.STATE_NEUTRAL}",
                )
                return self.STATE_NEUTRAL

        # Entsprechung zu LB_LBSID_positionShutterWithPreviousValues
        self._debug(
            True,
            f"Zustand {self.STATE_SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Beibehalte vorherige Position.",
        )
        return self.STATE_SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING

    async def _handle_state_shadow_horizontal_neutral(self) -> str:
        """Implementierung der Logik für den Zustand SHADOW_HORIZONTAL_NEUTRAL."""
        if await self._is_lbs_locked_in_either_way():
            self._debug(
                True,
                f"Zustand {self.STATE_SHADOW_HORIZONTAL_NEUTRAL}: LBS ist gesperrt, keine Aktion.",
            )
            return self.STATE_SHADOW_HORIZONTAL_NEUTRAL

        if await self._is_in_sun() and await self._is_shadow_handling_activated():
            current_brightness = await self._get_input_value("brightness")
            shadow_threshold_close = await self._get_input_value(
                "shadow_threshold_close"
            )
            shadow_open_shutter_delay = await self._get_input_value(
                "shadow_open_shutter_delay"
            )
            if (
                current_brightness is not None
                and shadow_threshold_close is not None
                and current_brightness > shadow_threshold_close
            ):
                target_height = await self._calculate_shutter_height()
                target_angle = await self._calculate_shutter_angle()
                if target_height is not None and target_angle is not None:
                    await self._position_shutter(
                        target_height,
                        target_angle,
                        1,  # Richtung: Öffnen/Aufwärts (für volle Schattenposition)
                        force=True,
                        stop_timer=False,
                    )
                    self._debug(
                        True,
                        f"Zustand {self.STATE_SHADOW_HORIZONTAL_NEUTRAL}: Helligkeit ({current_brightness}) über Schwellwert ({shadow_threshold_close}), fahre in Vollschatten ({target_height}%, {target_angle}%) und gehe zu {self.STATE_SHADOW_FULL_CLOSED}",
                    )
                    return self.STATE_SHADOW_FULL_CLOSED
                else:
                    self._debug(
                        False,
                        f"Zustand {self.STATE_SHADOW_HORIZONTAL_NEUTRAL}: Fehler beim Berechnen der Schattenhöhe oder des Winkels, bleibe in {self.STATE_SHADOW_HORIZONTAL_NEUTRAL}",
                    )
                    return self.STATE_SHADOW_HORIZONTAL_NEUTRAL
            elif shadow_open_shutter_delay is not None:
                self._debug(
                    True,
                    f"Zustand {self.STATE_SHADOW_HORIZONTAL_NEUTRAL}: Helligkeit nicht über Schwellwert, starte Timer für {self.STATE_SHADOW_NEUTRAL_TIMER_RUNNING} ({shadow_open_shutter_delay}s)",
                )
                await self._start_timer(shadow_open_shutter_delay)
                return self.STATE_SHADOW_NEUTRAL_TIMER_RUNNING
            else:
                self._debug(
                    False,
                    f"Zustand {self.STATE_SHADOW_HORIZONTAL_NEUTRAL}: Helligkeit nicht über Schwellwert und 'shadow_open_shutter_delay' nicht konfiguriert, bleibe in {self.STATE_SHADOW_HORIZONTAL_NEUTRAL}",
                )
                return self.STATE_SHADOW_HORIZONTAL_NEUTRAL
        else:
            neutral_height = await self._get_input_value("height_neutral")
            neutral_angle = await self._get_input_value("angle_neutral")
            if neutral_height is not None and neutral_angle is not None:
                await self._position_shutter(
                    float(neutral_height),
                    float(neutral_angle),
                    0,  # Richtung: Neutral
                    force=True,
                    stop_timer=True,  # Stop Timer (falls ein Timer aktiv war)
                )
                self._debug(
                    True,
                    f"Zustand {self.STATE_SHADOW_HORIZONTAL_NEUTRAL}: Nicht in Sonne oder Schattenmodus deaktiviert, fahre in Neutralposition ({neutral_height}%, {neutral_angle}%) und gehe zu {self.STATE_NEUTRAL}",
                )
                return self.STATE_NEUTRAL
            else:
                self._debug(
                    False,
                    f"Zustand {self.STATE_SHADOW_HORIZONTAL_NEUTRAL}: Neutrale Höhe oder Winkel nicht konfiguriert, gehe zu {self.STATE_NEUTRAL}",
                )
                return self.STATE_NEUTRAL

        # Entsprechung zu LB_LBSID_positionShutterWithPreviousValues
        self._debug(
            True,
            f"Zustand {self.STATE_SHADOW_HORIZONTAL_NEUTRAL}: Beibehalte vorherige Position.",
        )
        return self.STATE_SHADOW_HORIZONTAL_NEUTRAL

    async def _handle_state_shadow_neutral_timer_running(self) -> str:
        """Implementierung der Logik für den Zustand SHADOW_NEUTRAL_TIMER_RUNNING."""
        if await self._is_lbs_locked_in_either_way():
            self._debug(
                True,
                f"Zustand {self.STATE_SHADOW_NEUTRAL_TIMER_RUNNING}: LBS ist gesperrt, keine Aktion.",
            )
            return self.STATE_SHADOW_NEUTRAL_TIMER_RUNNING

        if await self._is_in_sun() and await self._is_shadow_handling_activated():
            current_brightness = await self._get_input_value("brightness")
            shadow_threshold_close = await self._get_input_value(
                "shadow_threshold_close"
            )
            height_after_shadow = await self._get_input_value("height_after_shadow")
            angle_after_shadow = await self._get_input_value("angle_after_shadow")
            if (
                current_brightness is not None
                and shadow_threshold_close is not None
                and current_brightness > shadow_threshold_close
            ):
                self._debug(
                    True,
                    f"Zustand {self.STATE_SHADOW_NEUTRAL_TIMER_RUNNING}: Helligkeit ({current_brightness}) wieder über Schwellwert ({shadow_threshold_close}), gehe zu {self.STATE_SHADOW_FULL_CLOSED} und stoppe Timer.",
                )
                await self._stop_timer()
                return self.STATE_SHADOW_FULL_CLOSED
            else:
                if await self._is_timer_finished():
                    if (
                        height_after_shadow is not None
                        and angle_after_shadow is not None
                    ):
                        await self._position_shutter(
                            float(height_after_shadow),
                            float(angle_after_shadow),
                            0,  # Richtung: Neutral
                            force=True,
                            stop_timer=True,
                        )
                        self._debug(
                            True,
                            f"Zustand {self.STATE_SHADOW_NEUTRAL_TIMER_RUNNING}: Timer abgelaufen, fahre in Position nach Schatten ({height_after_shadow}%, {angle_after_shadow}°) und gehe zu {self.STATE_SHADOW_NEUTRAL}",
                        )
                        return self.STATE_SHADOW_NEUTRAL
                    else:
                        self._debug(
                            False,
                            f"Zustand {self.STATE_SHADOW_NEUTRAL_TIMER_RUNNING}: Höhe oder Winkel nach Schatten nicht konfiguriert, bleibe in {self.STATE_SHADOW_NEUTRAL_TIMER_RUNNING}",
                        )
                        return self.STATE_SHADOW_NEUTRAL_TIMER_RUNNING
                else:
                    self._debug(
                        True,
                        f"Zustand {self.STATE_SHADOW_NEUTRAL_TIMER_RUNNING}: Warte auf Timer (Helligkeit nicht hoch genug)...",
                    )
                    return self.STATE_SHADOW_NEUTRAL_TIMER_RUNNING
        else:
            neutral_height = await self._get_input_value("height_neutral")
            neutral_angle = await self._get_input_value("angle_neutral")
            if neutral_height is not None and neutral_angle is not None:
                await self._position_shutter(
                    float(neutral_height),
                    float(neutral_angle),
                    0,  # Richtung: Neutral
                    force=True,
                    stop_timer=True,  # Stop Timer
                )
                self._debug(
                    True,
                    f"Zustand {self.STATE_SHADOW_NEUTRAL_TIMER_RUNNING}: Nicht in Sonne oder Schattenmodus deaktiviert, fahre in Neutralposition ({neutral_height}%, {neutral_angle}%) und gehe zu {self.STATE_NEUTRAL}",
                )
                return self.STATE_NEUTRAL
            else:
                self._debug(
                    False,
                    f"Zustand {self.STATE_SHADOW_NEUTRAL_TIMER_RUNNING}: Neutrale Höhe oder Winkel nicht konfiguriert, gehe zu {self.STATE_NEUTRAL}",
                )
                return self.STATE_NEUTRAL

        # Entsprechung zu LB_LBSID_positionShutterWithPreviousValues
        self._debug(
            True,
            f"Zustand {self.STATE_SHADOW_NEUTRAL_TIMER_RUNNING}: Beibehalte vorherige Position.",
        )
        return self.STATE_SHADOW_NEUTRAL_TIMER_RUNNING

    async def _handle_state_shadow_neutral(self) -> str:
        """Implementierung der Logik für den Zustand SHADOW_NEUTRAL."""
        if await self._is_lbs_locked_in_either_way():
            self._debug(
                True,
                f"Zustand {self.STATE_SHADOW_NEUTRAL}: LBS ist gesperrt, keine Aktion.",
            )
            return self.STATE_SHADOW_NEUTRAL

        if await self._is_in_sun() and await self._is_shadow_handling_activated():
            current_brightness = await self._get_input_value("brightness")
            shadow_threshold_close = await self._get_input_value(
                "shadow_threshold_close"
            )
            dawn_handling_active = await self._is_dawn_handling_activated()
            dawn_brightness = await self._get_input_value("brightness_dawn")
            dawn_threshold_close = await self._get_input_value("dawn_threshold_close")
            shadow_close_delay = await self._get_input_value("shadow_close_delay")
            dawn_close_delay = await self._get_input_value("dawn_close_delay")
            height_after_shadow = await self._get_input_value("height_after_shadow")
            angle_after_shadow = await self._get_input_value("angle_after_shadow")

            if (
                current_brightness is not None
                and shadow_threshold_close is not None
                and current_brightness > shadow_threshold_close
                and shadow_close_delay is not None
            ):
                self._debug(
                    True,
                    f"Zustand {self.STATE_SHADOW_NEUTRAL}: Helligkeit ({current_brightness}) über Schatten-Schwellwert ({shadow_threshold_close}), starte Timer für {self.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING} ({shadow_close_delay}s)",
                )
                await self._start_timer(shadow_close_delay)
                return self.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING
            elif (
                dawn_handling_active
                and dawn_brightness is not None
                and dawn_threshold_close is not None
                and dawn_brightness < dawn_threshold_close
                and dawn_close_delay is not None
            ):
                self._debug(
                    True,
                    f"Zustand {self.STATE_SHADOW_NEUTRAL}: Dämmerungsbehandlung aktiv und Helligkeit ({dawn_brightness}) unter Dämmerungs-Schwellwert ({dawn_threshold_close}), starte Timer für {self.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING} ({dawn_close_delay}s)",
                )
                await self._start_timer(dawn_close_delay)
                return self.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING
            elif height_after_shadow is not None and angle_after_shadow is not None:
                await self._position_shutter(
                    float(height_after_shadow),
                    float(angle_after_shadow),
                    0,  # Richtung: Neutral
                    force=True,
                    stop_timer=False,
                )
                self._debug(
                    True,
                    f"Zustand {self.STATE_SHADOW_NEUTRAL}: Bewege Behang in Position nach Schatten ({height_after_shadow}%, {angle_after_shadow}%).",
                )
                return self.STATE_SHADOW_NEUTRAL
            else:
                self._debug(
                    False,
                    f"Zustand {self.STATE_SHADOW_NEUTRAL}: Höhe oder Winkel nach Schatten nicht konfiguriert, bleibe in {self.STATE_SHADOW_NEUTRAL}",
                )
                return self.STATE_SHADOW_NEUTRAL

        if await self._is_dawn_handling_activated():
            dawn_brightness = await self._get_input_value("brightness_dawn")
            dawn_threshold_close = await self._get_input_value("dawn_threshold_close")
            dawn_close_delay = await self._get_input_value("dawn_close_delay")
            if (
                dawn_brightness is not None
                and dawn_threshold_close is not None
                and dawn_brightness < dawn_threshold_close
                and dawn_close_delay is not None
            ):
                self._debug(
                    True,
                    f"Zustand {self.STATE_SHADOW_NEUTRAL}: Dämmerungsbehandlung aktiv und Helligkeit ({dawn_brightness}) unter Dämmerungs-Schwellwert ({dawn_threshold_close}), starte Timer für {self.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING} ({dawn_close_delay}s)",
                )
                await self._start_timer(dawn_close_delay)
                return self.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING

        neutral_height = await self._get_input_value("height_neutral")
        neutral_angle = await self._get_input_value("angle_neutral")
        if neutral_height is not None and neutral_angle is not None:
            await self._position_shutter(
                float(neutral_height),
                float(neutral_angle),
                0,  # Richtung: Neutral
                force=True,
                stop_timer=True,  # Stop Timer (falls ein Timer aktiv war)
            )
            self._debug(
                True,
                f"Zustand {self.STATE_SHADOW_NEUTRAL}: Nicht in Sonne oder Schattenmodus deaktiviert und Dämmerung nicht aktiv, fahre in Neutralposition ({neutral_height}%, {neutral_angle}%) und gehe zu {self.STATE_NEUTRAL}",
            )
            return self.STATE_NEUTRAL
        else:
            self._debug(
                False,
                f"Zustand {self.STATE_SHADOW_NEUTRAL}: Neutrale Höhe oder Winkel nicht konfiguriert, gehe zu {self.STATE_NEUTRAL}",
            )
            return self.STATE_NEUTRAL

    async def _handle_state_dawn_neutral(self) -> str:
        """Implementierung der Logik für den Zustand DAWN_NEUTRAL."""
        if await self._is_lbs_locked_in_either_way():
            self._debug(
                True,
                f"Zustand {self.STATE_DAWN_NEUTRAL}: LBS ist gesperrt, keine Aktion.",
            )
            return self.STATE_DAWN_NEUTRAL

        dawn_handling_active = await self._is_dawn_handling_activated()
        dawn_brightness = await self._get_input_value("brightness_dawn")
        dawn_threshold_close = await self._get_input_value("dawn_threshold_close")
        dawn_close_delay = await self._get_input_value("dawn_close_delay")
        is_in_sun = await self._is_in_sun()
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
                self._debug(
                    True,
                    f"Zustand {self.STATE_DAWN_NEUTRAL}: Dämmerungsbehandlung aktiv und Helligkeit ({dawn_brightness}) unter Dämmerungs-Schwellwert ({dawn_threshold_close}), starte Timer für {self.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING} ({dawn_close_delay}s)",
                )
                await self._start_timer(dawn_close_delay)
                return self.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING
            elif (
                is_in_sun
                and shadow_handling_active
                and current_brightness is not None
                and shadow_threshold_close is not None
                and current_brightness > shadow_threshold_close
                and shadow_close_delay is not None
            ):
                self._debug(
                    True,
                    f"Zustand {self.STATE_DAWN_NEUTRAL}: Sonne scheint, Schattenbehandlung aktiv und Helligkeit ({current_brightness}) über Schatten-Schwellwert ({shadow_threshold_close}), starte Timer für {self.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING} ({shadow_close_delay}s)",
                )
                await self._start_timer(shadow_close_delay)
                return self.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING
            elif height_after_dawn is not None and angle_after_dawn is not None:
                await self._position_shutter(
                    float(height_after_dawn),
                    float(angle_after_dawn),
                    0,  # Richtung: Neutral
                    force=True,
                    stop_timer=False,
                )
                self._debug(
                    True,
                    f"Zustand {self.STATE_DAWN_NEUTRAL}: Bewege Behang in Position nach Dämmerung ({height_after_dawn}%, {angle_after_dawn}%).",
                )
                return self.STATE_DAWN_NEUTRAL
            else:
                self._debug(
                    False,
                    f"Zustand {self.STATE_DAWN_NEUTRAL}: Höhe oder Winkel nach Dämmerung nicht konfiguriert, bleibe in {self.STATE_DAWN_NEUTRAL}",
                )
                return self.STATE_DAWN_NEUTRAL

        if (
            is_in_sun
            and shadow_handling_active
            and current_brightness is not None
            and shadow_threshold_close is not None
            and current_brightness > shadow_threshold_close
            and shadow_close_delay is not None
        ):
            self._debug(
                True,
                f"Zustand {self.STATE_DAWN_NEUTRAL}: Sonne scheint, Schattenbehandlung aktiv und Helligkeit ({current_brightness}) über Schatten-Schwellwert ({shadow_threshold_close}), starte Timer für {self.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING} ({shadow_close_delay}s)",
            )
            await self._start_timer(shadow_close_delay)
            return self.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING

        if neutral_height is not None and neutral_angle is not None:
            await self._position_shutter(
                float(neutral_height),
                float(neutral_angle),
                0,  # Richtung: Neutral
                force=True,
                stop_timer=True,  # Stop Timer (falls ein Timer aktiv war)
            )
            self._debug(
                True,
                f"Zustand {self.STATE_DAWN_NEUTRAL}: Dämmerungsbehandlung deaktiviert oder nicht die Bedingungen für Schatten, fahre in Neutralposition ({neutral_height}%, {neutral_angle}%).",
            )
            return self.STATE_NEUTRAL
        else:
            self._debug(
                False,
                f"Zustand {self.STATE_DAWN_NEUTRAL}: Neutrale Höhe oder Winkel nicht konfiguriert, gehe zu {self.STATE_NEUTRAL}",
            )
            return self.STATE_NEUTRAL

    async def _handle_state_dawn_neutral_timer_running(self) -> str:
        """Implementierung der Logik für den Zustand DAWN_NEUTRAL_TIMER_RUNNING."""
        if await self._is_lbs_locked_in_either_way():
            self._debug(
                True,
                f"Zustand {self.STATE_DAWN_NEUTRAL_TIMER_RUNNING}: LBS ist gesperrt, keine Aktion.",
            )
            return self.STATE_DAWN_NEUTRAL_TIMER_RUNNING

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
                self._debug(
                    True,
                    f"Zustand {self.STATE_DAWN_NEUTRAL_TIMER_RUNNING}: Dämmerungshelligkeit ({dawn_brightness}) wieder unter Schwellwert ({dawn_threshold_close}), gehe zu {self.STATE_DAWN_FULL_CLOSED} und stoppe Timer.",
                )
                await self._stop_timer()
                return self.STATE_DAWN_FULL_CLOSED
            else:
                if await self._is_timer_finished():
                    if dawn_height is not None and dawn_open_slat_angle is not None:
                        await self._position_shutter(
                            float(dawn_height),
                            float(dawn_open_slat_angle),
                            0,  # Richtung: Neutral
                            force=True,
                            stop_timer=True,
                        )
                        self._debug(
                            True,
                            f"Zustand {self.STATE_DAWN_NEUTRAL_TIMER_RUNNING}: Timer abgelaufen, fahre auf Dämmerungshöhe ({dawn_height}%) mit geöffneten Lamellen ({dawn_open_slat_angle}°) und gehe zu {self.STATE_DAWN_NEUTRAL}",
                        )
                        return self.STATE_DAWN_NEUTRAL
                    else:
                        self._debug(
                            False,
                            f"Zustand {self.STATE_DAWN_NEUTRAL_TIMER_RUNNING}: Dämmerungshöhe oder Winkel für offene Lamellen nicht konfiguriert, bleibe in {self.STATE_DAWN_NEUTRAL_TIMER_RUNNING}",
                        )
                        return self.STATE_DAWN_NEUTRAL_TIMER_RUNNING
                else:
                    self._debug(
                        True,
                        f"Zustand {self.STATE_DAWN_NEUTRAL_TIMER_RUNNING}: Warte auf Timer (Helligkeit nicht niedrig genug)...",
                    )
                    return self.STATE_DAWN_NEUTRAL_TIMER_RUNNING
        else:
            neutral_height = await self._get_input_value("height_neutral")
            neutral_angle = await self._get_input_value("angle_neutral")
            if neutral_height is not None and neutral_angle is not None:
                await self._position_shutter(
                    float(neutral_height),
                    float(neutral_angle),
                    0,  # Richtung: Neutral
                    force=True,
                    stop_timer=True,  # Stop Timer
                )
                self._debug(
                    True,
                    f"Zustand {self.STATE_DAWN_NEUTRAL_TIMER_RUNNING}: Dämmerungsbehandlung deaktiviert, fahre in Neutralposition ({neutral_height}%, {neutral_angle}%) und gehe zu {self.STATE_NEUTRAL}",
                )
                return self.STATE_NEUTRAL
            else:
                self._debug(
                    False,
                    f"Zustand {self.STATE_DAWN_NEUTRAL_TIMER_RUNNING}: Neutrale Höhe oder Winkel nicht konfiguriert, gehe zu {self.STATE_NEUTRAL}",
                )
                return self.STATE_NEUTRAL

        # Entsprechung zu LB_LBSID_positionShutterWithPreviousValues
        self._debug(
            True,
            f"Zustand {self.STATE_DAWN_NEUTRAL_TIMER_RUNNING}: Beibehalte vorherige Position.",
        )
        return self.STATE_DAWN_NEUTRAL_TIMER_RUNNING

    async def _handle_state_dawn_horizontal_neutral(self) -> str:
        """Implementierung der Logik für den Zustand DAWN_HORIZONTAL_NEUTRAL."""
        if await self._is_lbs_locked_in_either_way():
            self._debug(
                True,
                f"Zustand {self.STATE_DAWN_HORIZONTAL_NEUTRAL}: LBS ist gesperrt, keine Aktion.",
            )
            return self.STATE_DAWN_HORIZONTAL_NEUTRAL

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
                    0,  # Richtung: Neutral
                    force=False,
                    stop_timer=False,
                )
                self._debug(
                    True,
                    f"Zustand {self.STATE_DAWN_HORIZONTAL_NEUTRAL}: Dämmerungshelligkeit ({dawn_brightness}) unter Schwellwert ({dawn_threshold_close}), fahre auf Dämmerungshöhe ({dawn_height}%) mit geöffneten Lamellen ({dawn_open_slat_angle}°) und gehe zu {self.STATE_DAWN_FULL_CLOSED}",
                )
                return self.STATE_DAWN_FULL_CLOSED
            elif dawn_open_shutter_delay is not None:
                self._debug(
                    True,
                    f"Zustand {self.STATE_DAWN_HORIZONTAL_NEUTRAL}: Dämmerungshelligkeit nicht unter Schwellwert, starte Timer für {self.STATE_DAWN_NEUTRAL_TIMER_RUNNING} ({dawn_open_shutter_delay}s)",
                )
                await self._start_timer(dawn_open_shutter_delay)
                return self.STATE_DAWN_NEUTRAL_TIMER_RUNNING
            else:
                self._debug(
                    False,
                    f"Zustand {self.STATE_DAWN_HORIZONTAL_NEUTRAL}: Dämmerungshelligkeit nicht unter Schwellwert und 'dawn_open_shutter_delay' nicht konfiguriert, bleibe in {self.STATE_DAWN_HORIZONTAL_NEUTRAL}",
                )
                return self.STATE_DAWN_HORIZONTAL_NEUTRAL
        else:
            neutral_height = await self._get_input_value("height_neutral")
            neutral_angle = await self._get_input_value("angle_neutral")
            if neutral_height is not None and neutral_angle is not None:
                await self._position_shutter(
                    float(neutral_height),
                    float(neutral_angle),
                    0,  # Richtung: Neutral
                    force=True,
                    stop_timer=True,
                )
                self._debug(
                    True,
                    f"Zustand {self.STATE_DAWN_HORIZONTAL_NEUTRAL}: Dämmerungsbehandlung deaktiviert, fahre in Neutralposition ({neutral_height}%, {neutral_angle}%) und gehe zu {self.STATE_NEUTRAL}",
                )
                return self.STATE_NEUTRAL
            else:
                self._debug(
                    False,
                    f"Zustand {self.STATE_DAWN_HORIZONTAL_NEUTRAL}: Neutrale Höhe oder Winkel nicht konfiguriert, gehe zu {self.STATE_NEUTRAL}",
                )
                return self.STATE_NEUTRAL

        # Entsprechung zu LB_LBSID_positionShutterWithPreviousValues
        self._debug(
            True,
            f"Zustand {self.STATE_DAWN_HORIZONTAL_NEUTRAL}: Beibehalte vorherige Position.",
        )
        return self.STATE_DAWN_HORIZONTAL_NEUTRAL

    async def _handle_state_dawn_horizontal_neutral_timer_running(self) -> str:
        """Implementierung der Logik für den Zustand DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING."""
        if await self._is_lbs_locked_in_either_way():
            self._debug(
                True,
                f"Zustand {self.STATE_DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: LBS ist gesperrt, keine Aktion.",
            )
            return self.STATE_DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING

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
                self._debug(
                    True,
                    f"Zustand {self.STATE_DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Dämmerungshelligkeit ({dawn_brightness}) wieder unter Schwellwert ({dawn_threshold_close}), gehe zu {self.STATE_DAWN_FULL_CLOSED} und stoppe Timer.",
                )
                await self._stop_timer()
                return self.STATE_DAWN_FULL_CLOSED
            else:
                if await self._is_timer_finished():
                    if dawn_height is not None and dawn_open_slat_angle is not None:
                        await self._position_shutter(
                            float(dawn_height),
                            float(dawn_open_slat_angle),
                            0,  # Richtung: Neutral
                            force=False,
                            stop_timer=True,
                        )
                        self._debug(
                            True,
                            f"Zustand {self.STATE_DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Timer abgelaufen, fahre auf Dämmerungshöhe ({dawn_height}%) mit geöffneten Lamellen ({dawn_open_slat_angle}°) und gehe zu {self.STATE_DAWN_HORIZONTAL_NEUTRAL}",
                        )
                        return self.STATE_DAWN_HORIZONTAL_NEUTRAL
                    else:
                        self._debug(
                            False,
                            f"Zustand {self.STATE_DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Dämmerungshöhe oder Winkel für offene Lamellen nicht konfiguriert, bleibe in {self.STATE_DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING}",
                        )
                        return self.STATE_DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING
                else:
                    self._debug(
                        True,
                        f"Zustand {self.STATE_DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Warte auf Timer (Helligkeit nicht niedrig genug)...",
                    )
                    return self.STATE_DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING
        else:
            neutral_height = await self._get_input_value("height_neutral")
            neutral_angle = await self._get_input_value("angle_neutral")
            if neutral_height is not None and neutral_angle is not None:
                await self._position_shutter(
                    float(neutral_height),
                    float(neutral_angle),
                    0,  # Richtung: Neutral
                    force=True,
                    stop_timer=True,  # Stop Timer
                )
                self._debug(
                    True,
                    f"Zustand {self.STATE_DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Dämmerungsbehandlung deaktiviert, fahre in Neutralposition ({neutral_height}%, {neutral_angle}%) und gehe zu {self.STATE_NEUTRAL}",
                )
                return self.STATE_NEUTRAL
            else:
                self._debug(
                    False,
                    f"Zustand {self.STATE_DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Neutrale Höhe oder Winkel nicht konfiguriert, gehe zu {self.STATE_NEUTRAL}",
                )
                return self.STATE_NEUTRAL

        # Entsprechung zu LB_LBSID_positionShutterWithPreviousValues
        self._debug(
            True,
            f"Zustand {self.STATE_DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Beibehalte vorherige Position.",
        )
        return self.STATE_DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING

    async def _update_sun_state(self):
        """Berechnet, ob die Fassade von der Sonne beleuchtet wird und ob die Elevation im gültigen Bereich liegt."""
        self._debug(True, "=== Überprüfe, ob Fassade in der Sonne ist... ===")

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
            self._debug(
                False,
                "Kann Sonnenstatus nicht überprüfen: Nicht alle erforderlichen Eingabewerte sind verfügbar.",
            )
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

        self._debug(True, message + " ===")

        # Speichere die Ergebnisse in internen Zustandsvariablen
        self._internal_is_in_sun = is_in_sun
        self._internal_is_between_min_max_elevation = is_between_min_max_elevation
        self._internal_effective_elevation = effective_elevation

    async def _get_internal_state(self, state_name: str) -> bool | str | None:
        """Gibt den Wert einer internen Zustandsvariable zurück."""
        state_map = {
            "is_in_sun": self._internal_is_in_sun,
            "is_between_min_max_elevation": self._internal_is_between_min_max_elevation,
            "effective_elevation": self._internal_effective_elevation,
        }
        return state_map.get(state_name)

    _debug_enabled: bool = True  # Standardmäßig Debug-Ausgaben aktivieren

    def _debug(self, enabled: bool, message: str):
        """Gibt eine Debug-Nachricht aus, wenn die Debug-Ausgabe aktiviert ist."""
        if self._debug_enabled and enabled:
            print(f"DEBUG (ShadowControl): {message}")
        elif not enabled:
            print(f"DEBUG (ShadowControl) (forced): {message}")

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
                self._debug(
                    True,
                    f"Home Assistant: Setze Zustand von '{entity_id}' auf '{state}' mit Attributen '{attributes}'.",
                )
            else:
                self._debug(
                    True,
                    f"Home Assistant: Zustand von '{entity_id}' ist bereits '{state}' (und Attribute sind gleich), überspringe Aktualisierung.",
                )
        else:
            self._debug(False, "Home Assistant API-Instanz nicht verfügbar.")

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
