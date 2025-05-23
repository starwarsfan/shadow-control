"""Platform for Shadow Control integration."""

from __future__ import annotations

import logging
import math
from typing import Any, Callable, Optional

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
        self._movement_restriction_height: str | None = None
        self._movement_restriction_angle: str | None = None
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

        # Interne persistente Variablen
        # Werden beim Start aus den persistenten Attributen gelesen.
        self._current_shutter_state: float | None = None

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
                    # Konvertieren Sie den Wert zu int, falls er als String gespeichert wurde.
                    self._current_shutter_state = int(initial_state_value)
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

        # Optional: Initialberechnung beim Start, falls Sie async_update entfernen
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
            # Fügen Sie hier alle internen Statusvariablen hinzu, die persistent sein sollen
        }

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
        # Sonnenstand und Helligkeit
        current_sun_elevation = self._get_entity_numeric_state(self._sun_elevation_entity_id, float)
        current_sun_azimuth = self._get_entity_numeric_state(self._sun_azimuth_entity_id, float)
        current_brightness = self._get_entity_numeric_state(self._brightness_entity_id, float)
        current_brightness_dawn = self._get_entity_numeric_state(self._brightness_dawn_entity_id, float)

        # Aktuelle Behang-Position
        current_height = self._get_entity_numeric_state(self._shutter_current_height_entity_id, float)
        current_angle = self._get_entity_numeric_state(self._shutter_current_angle_entity_id, float)

        # 2. Beschattungslogik ausführen
        _LOGGER.debug(f"{self._name}: Brightness={current_brightness}, Elevation={current_sun_elevation}, etc. - Performing calculation.")

        self._check_if_position_changed_externally(current_height, current_angle)
        await self._handle_lock_state()
        await self._check_if_facade_is_in_sun()

        # 3. Jalousie steuern (async_set_cover_position, async_set_cover_tilt_position)
        # await self.async_set_cover_position(new_position)
        # await self.async_set_cover_tilt_position(new_tilt_position)
        # ...

        # 4. Update the dictionary holding the attributes
        self._update_extra_state_attributes()
        # 5. Tell Home Assistant to save the updated state (and attributes)
        self.async_write_ha_state()

    def _check_if_position_changed_externally(self, current_height, current_angle):
        #_LOGGER.debug(f"{self._name}: Checking if position changed externally. Current height: {current_height}, Current angle: {current_angle}")
        _LOGGER.debug(f"{self._name}: Check for external shutter modification -> TBD")
        pass

    async def _handle_lock_state(self):
        if await self._is_locked():
            _LOGGER.debug(f"{self._name} is locked. Do not change the position.")
        elif await self._is_forced_locked():
            _LOGGER.debug(f"{self._name} is forced locked. Do not change the position.")
        # elif await self._is_modified_externally():
        #     _LOGGER.debug(f"{self._name} is modified externally. Do not change the position.")
        else:
            _LOGGER.debug(f"{self._name} is not locked. Change the position.")
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

    # Optional: Methoden für Tilt, falls unterstützt
    # async def async_set_cover_tilt_position(self, **kwargs: any) -> None:
    #     tilt_position = kwargs[ATTR_TILT_POSITION]
    #     _LOGGER.info(f"{self._name}: Setting cover tilt to {tilt_position}")
    #     # Rufen Sie hier Ihr Skript für die Neigung auf
    #     self.async_write_ha_state()

    @property
    def unique_id(self) -> str | None:
        """Return the unique ID of the cover."""
        return f"shadow_control_{self._name.lower().replace(' ', '_')}"

    @property
    def current_cover_tilt(self) -> int | None:
        """Return the current tilt of the cover."""
        # Hier den aktuellen Neigungswinkel abrufen oder aus dem Zustand ableiten
        return None  # Placeholder

    async def async_set_cover_tilt(self, **kwargs: any) -> None:
        """Set the tilt of the cover."""
        if (tilt := kwargs.get("tilt")) is not None:
            _LOGGER.debug(f"Set cover tilt to {tilt}")
            self._target_tilt = tilt
            await self._perform_state_handling()

    async def _perform_state_handling(self):
        """Handle the state machine and trigger actions."""
        new_state = await self._calculate_state()
        if new_state != self._current_shutter_state:
            _LOGGER.debug(f"State changed from {self._current_shutter_state} to {new_state}")
            self._current_shutter_state = new_state
            # Potentially trigger another state calculation if needed
            await self._perform_state_handling()
        else:
            _LOGGER.debug(f"Current state: {self._current_shutter_state}")
            # Perform actions based on the current state
            method_name = f"_handle_state_{self._current_shutter_state.lower()}"
            if hasattr(self, method_name):
                next_state = await getattr(self, method_name)()
                if next_state and next_state != self._current_shutter_state:
                    _LOGGER.debug(f"State handling requested transition to {next_state}")
                    self._current_shutter_state = next_state
                    await self._perform_state_handling()

    async def _calculate_state(self) -> str:
        """Determine the current state based on sensor values and conditions."""
        _LOGGER.debug(f"=== Calculating shutter state... ===")
        current_state = self._current_shutter_state
        new_state = self.STATE_NEUTRAL

        if (
            await self._is_shadow_handling_activated() and not await self._check_if_facade_is_in_sun()
        ) or (
            await self._is_dawn_handling_activated() and await self._is_dawn_active()
        ):
            new_state = await self._get_appropriate_closed_state(current_state)
        elif await self._check_if_facade_is_in_sun() and await self._is_shadow_handling_activated():
            new_state = await self._get_appropriate_sun_state(current_state)
        elif (
            await self._is_dawn_handling_activated()
            and not await self._is_dawn_active()
        ):
            new_state = await self._get_appropriate_dawn_open_state(current_state)
        else:
            new_state = self.STATE_NEUTRAL

        _LOGGER.debug(f"=== Calculated new state: {new_state} (was: {current_state}) ===")
        return new_state

    async def _get_appropriate_closed_state(self, current_state: str) -> str:
        """Determine the appropriate closed state (shadow or dawn)."""
        if await self._is_shadow_handling_activated() and not await self._check_if_facade_is_in_sun():
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

    async def _is_locked(self) -> LockState:
        """Check if the integration is locked."""
        lock_state_obj = self.hass.states.get(self._lock_integration_entity_id)
        if lock_state_obj: # Prüfen, ob das State-Objekt existiert
            if lock_state_obj.state == STATE_ON: # Vergleichen mit der Konstante STATE_ON
                is_locked = LockState.LOCKSTATE__LOCKED_MANUALLY
            elif lock_state_obj.state == STATE_OFF: # Vergleichen mit der Konstante STATE_OFF
                is_locked = LockState.LOCKSTATE__UNLOCKED
            else: # Fallback für den Fall, dass der Zustand weder 'on' noch 'off' ist (z.B. 'unavailable', 'unknown')
                _LOGGER.warning(f"Unexpected state for {self._lock_integration_entity_id}: {lock_state_obj.state}. Assuming unlocked.")
                is_locked = LockState.LOCKSTATE__UNLOCKED
        else: # Fallback, wenn das State-Objekt nicht gefunden wird
            _LOGGER.warning(f"Entity {self._lock_integration_entity_id} not found. Assuming unlocked.")
            is_locked = LockState.LOCKSTATE__UNLOCKED
        return is_locked

    async def _is_forced_locked(self) -> LockState:
        """Check if integration locked with a forced position."""
        lock_state_obj = self.hass.states.get(self._lock_integration_with_position_entity_id)
        if lock_state_obj: # Prüfen, ob das State-Objekt existiert
            if lock_state_obj.state == STATE_ON: # Vergleichen mit der Konstante STATE_ON
                is_locked = LockState.LOCKSTATE__LOCKED_MANUALLY_WITH_FORCED_POSITION
            elif lock_state_obj.state == STATE_OFF: # Vergleichen mit der Konstante STATE_OFF
                is_locked = LockState.LOCKSTATE__UNLOCKED
            else: # Fallback für den Fall, dass der Zustand weder 'on' noch 'off' ist (z.B. 'unavailable', 'unknown')
                _LOGGER.warning(f"Unexpected state for {self._lock_integration_entity_id}: {lock_state_obj.state}. Assuming unlocked.")
                is_locked = LockState.LOCKSTATE__UNLOCKED
        else: # Fallback, wenn das State-Objekt nicht gefunden wird
            _LOGGER.warning(f"Entity {self._lock_integration_entity_id} not found. Assuming unlocked.")
            is_locked = LockState.LOCKSTATE__UNLOCKED
        return is_locked

    async def _is_lbs_locked_in_either_way(self) -> bool:
        """Check if the cover is locked in any way."""
        return await self._is_locked() == LockState.LOCKSTATE__UNLOCKED and await self._is_forced_locked() == LockState.LOCKSTATE__UNLOCKED

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
        _LOGGER.debug(f"positionShutter(...), Werte für Höhe/Winkel: {height_percent}%/{angle_percent}%, Richtung: {direction}, Force: {force}, Stop Timer: {stop_timer}")
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
            _LOGGER.debug(f"Attribute '{attribute}' changed from '{current_value}' to '{value}', updating...")
            setattr(self, f"_current_{attribute}", value)
            self.async_write_ha_state()

    async def _check_if_facade_is_in_sun(self) -> None:
        """Calculate if the sun illuminates the given facade."""
        _LOGGER.debug(f"=== Checking if facade is in sun... ===")

        sun_current_azimuth = self._get_entity_numeric_state(self._sun_azimuth_entity_id, int)
        sun_current_elevation = self._get_entity_numeric_state(self._sun_elevation_entity_id, int)
        facade_azimuth = self._get_entity_numeric_state(self._azimuth_facade_entity_id, int)
        facade_offset_start = self._get_entity_numeric_state(self._offset_sun_in_entity_id, int)
        facade_offset_end = self._get_entity_numeric_state(self._offset_sun_out_entity_id, int)
        min_elevation = self._get_entity_numeric_state(self._elevation_sun_min_entity_id, int)
        max_elevation = self._get_entity_numeric_state(self._elevation_sun_max_entity_id, int)

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
            await self._send_by_change("sun_at_facade_azimuth", True)
            effective_elevation = await self._calculate_effective_elevation()
        else:
            message += f"NOT IN SUN (shadow side, at sun from {sun_entry_angle}° to {sun_exit_angle}°)"
            self._sun_between_offsets = False
            await self._send_by_change("sun_at_facade_azimuth", False)
            effective_elevation = None

        #await self._send_by_change("effective_elevation", effective_elevation)

        message += f"\n -> effective elevation {effective_elevation}° for given elevation of {sun_current_elevation}°"
        is_elevation_in_range = False
        if effective_elevation > min_elevation and effective_elevation < max_elevation:
            message += f" -> in min-max-range ({min_elevation}°-{max_elevation}°)"
            self._sun_between_min_max = True
            is_elevation_in_range = True
            await self._send_by_change("sun_at_facade_elevation", True)
        else:
            message += f" -> NOT in min-max-range ({min_elevation}°-{max_elevation}°)"
            self._sun_between_min_max = False
            await self._send_by_change("sun_at_facade_elevation", False)
        _LOGGER.debug(f"{message} ===")

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
        sun_current_azimuth = self._get_entity_numeric_state(self._sun_azimuth_entity_id, int)
        sun_current_elevation = self._get_entity_numeric_state(self._sun_elevation_entity_id, int)
        facade_azimuth = self._get_entity_numeric_state(self._azimuth_facade_entity_id, int)

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
    async def _handle_state_shadow_full_close_timer_running(self) -> str:
        if await self._is_lbs_locked_in_either_way():
            _LOGGER.debug(f"Zustand {self.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING}: LBS ist gesperrt, keine Aktion.")
            return self.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING

        if await self._check_if_facade_is_in_sun() and await self._is_shadow_handling_activated():
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
                        _LOGGER.debug(f"Zustand {self.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING}: Timer abgelaufen, Helligkeit hoch genug, fahre in Vollschatten ({target_height}%, {target_angle}%) und gehe zu {self.STATE_SHADOW_FULL_CLOSED}")
                        return self.STATE_SHADOW_FULL_CLOSED
                    else:
                        _LOGGER.debug(f"Zustand {self.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING}: Fehler beim Berechnen der Schattenhöhe oder des Winkels, bleibe in {self.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING}")
                        return self.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING
                else:
                    _LOGGER.debug(f"Zustand {self.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING}: Warte auf Timer (Helligkeit hoch genug)...")
                    return self.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING
            else:
                _LOGGER.debug(f"Zustand {self.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING}: Helligkeit ({current_brightness}) nicht höher als Schwellwert ({shadow_threshold_close}), gehe zu {self.STATE_SHADOW_NEUTRAL}")
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
                _LOGGER.debug(f"Zustand {self.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING}: Nicht in Sonne oder Schattenmodus deaktiviert, fahre in Neutralposition ({neutral_height}%, {neutral_angle}%) und gehe zu {self.STATE_NEUTRAL}")
                return self.STATE_NEUTRAL
            else:
                _LOGGER.debug(f"Zustand {self.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING}: Neutrale Höhe oder Winkel nicht konfiguriert, gehe zu {self.STATE_NEUTRAL}")
                return self.STATE_NEUTRAL

        # Entsprechung zu LB_LBSID_positionShutterWithPreviousValues
        _LOGGER.debug(f"Zustand {self.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING}: Beibehalte vorherige Position.")
        return self.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING

    # =======================================================================
    # State SHADOW_FULL_CLOSED
    async def _handle_state_shadow_full_closed(self) -> str:
        if await self._is_lbs_locked_in_either_way():
            _LOGGER.debug(f"Zustand {self.STATE_SHADOW_FULL_CLOSED}: LBS ist gesperrt, keine Aktion.")
            return self.STATE_SHADOW_FULL_CLOSED

        if await self._check_if_facade_is_in_sun() and await self._is_shadow_handling_activated():
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
                _LOGGER.debug(f"Zustand {self.STATE_SHADOW_FULL_CLOSED}: Helligkeit ({current_brightness}) unter Schwellwert ({shadow_threshold_close}), starte Timer für {self.STATE_SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING} ({shadow_open_slat_delay}s)")
                await self._start_timer(shadow_open_slat_delay)
                return self.STATE_SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING
            else:
                _LOGGER.debug(f"Zustand {self.STATE_SHADOW_FULL_CLOSED}: Helligkeit nicht unter Schwellwert, Neuberechnung der Schattenposition.")
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
                _LOGGER.debug(f"Zustand {self.STATE_SHADOW_FULL_CLOSED}: Nicht in Sonne oder Schattenmodus deaktiviert, fahre in Neutralposition ({neutral_height}%, {neutral_angle}%) und gehe zu {self.STATE_NEUTRAL}")
                return self.STATE_NEUTRAL
            else:
                _LOGGER.debug(f"Zustand {self.STATE_SHADOW_FULL_CLOSED}: Neutrale Höhe oder Winkel nicht konfiguriert, gehe zu {self.STATE_NEUTRAL}")
                return self.STATE_NEUTRAL

        # Entsprechung zu LB_LBSID_positionShutterWithPreviousValues
        _LOGGER.debug(f"Zustand {self.STATE_SHADOW_FULL_CLOSED}: Beibehalte vorherige Position.")
        return self.STATE_SHADOW_FULL_CLOSED

    # =======================================================================
    # State SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING
    async def _handle_state_shadow_horizontal_neutral_timer_running(self) -> str:
        if await self._is_lbs_locked_in_either_way():
            _LOGGER.debug(f"Zustand {self.STATE_SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: LBS ist gesperrt, keine Aktion.")
            return self.STATE_SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING

        if await self._check_if_facade_is_in_sun() and await self._is_shadow_handling_activated():
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
                _LOGGER.debug(f"Zustand {self.STATE_SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Helligkeit ({current_brightness}) wieder über Schwellwert ({shadow_threshold_close}), gehe zu {self.STATE_SHADOW_FULL_CLOSED} und stoppe Timer.")
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
                        _LOGGER.debug(f"Zustand {self.STATE_SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Timer abgelaufen, fahre auf Höhe {target_height}% mit neutralen Lamellen ({shadow_open_slat_angle}°) und gehe zu {self.STATE_SHADOW_HORIZONTAL_NEUTRAL}")
                        return self.STATE_SHADOW_HORIZONTAL_NEUTRAL
                    else:
                        _LOGGER.debug(f"Zustand {self.STATE_SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Fehler beim Berechnen der Höhe oder Winkel für offene Lamellen nicht konfiguriert, bleibe in {self.STATE_SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING}")
                        return self.STATE_SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING
                else:
                    _LOGGER.debug(f"Zustand {self.STATE_SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Warte auf Timer (Helligkeit nicht hoch genug)...")
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
                _LOGGER.debug(f"Zustand {self.STATE_SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Nicht in Sonne oder Schattenmodus deaktiviert, fahre in Neutralposition ({neutral_height}%, {neutral_angle}%) und gehe zu {self.STATE_NEUTRAL}")
                return self.STATE_NEUTRAL
            else:
                _LOGGER.debug(f"Zustand {self.STATE_SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Neutrale Höhe oder Winkel nicht konfiguriert, gehe zu {self.STATE_NEUTRAL}")
                return self.STATE_NEUTRAL

        # Entsprechung zu LB_LBSID_positionShutterWithPreviousValues
        _LOGGER.debug(f"Zustand {self.STATE_SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Beibehalte vorherige Position.")
        return self.STATE_SHADOW_HORIZONTAL_NEUTRAL_TIMER_RUNNING

    # =======================================================================
    # State SHADOW_HORIZONTAL_NEUTRAL
    async def _handle_state_shadow_horizontal_neutral(self) -> str:
        if await self._is_lbs_locked_in_either_way():
            _LOGGER.debug(f"Zustand {self.STATE_SHADOW_HORIZONTAL_NEUTRAL}: LBS ist gesperrt, keine Aktion.")
            return self.STATE_SHADOW_HORIZONTAL_NEUTRAL

        if await self._check_if_facade_is_in_sun() and await self._is_shadow_handling_activated():
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
                    _LOGGER.debug(f"Zustand {self.STATE_SHADOW_HORIZONTAL_NEUTRAL}: Helligkeit ({current_brightness}) über Schwellwert ({shadow_threshold_close}), fahre in Vollschatten ({target_height}%, {target_angle}%) und gehe zu {self.STATE_SHADOW_FULL_CLOSED}")
                    return self.STATE_SHADOW_FULL_CLOSED
                else:
                    _LOGGER.debug(f"Zustand {self.STATE_SHADOW_HORIZONTAL_NEUTRAL}: Fehler beim Berechnen der Schattenhöhe oder des Winkels, bleibe in {self.STATE_SHADOW_HORIZONTAL_NEUTRAL}")
                    return self.STATE_SHADOW_HORIZONTAL_NEUTRAL
            elif shadow_open_shutter_delay is not None:
                _LOGGER.debug(f"Zustand {self.STATE_SHADOW_HORIZONTAL_NEUTRAL}: Helligkeit nicht über Schwellwert, starte Timer für {self.STATE_SHADOW_NEUTRAL_TIMER_RUNNING} ({shadow_open_shutter_delay}s)")
                await self._start_timer(shadow_open_shutter_delay)
                return self.STATE_SHADOW_NEUTRAL_TIMER_RUNNING
            else:
                _LOGGER.debug(f"Zustand {self.STATE_SHADOW_HORIZONTAL_NEUTRAL}: Helligkeit nicht über Schwellwert und 'shadow_open_shutter_delay' nicht konfiguriert, bleibe in {self.STATE_SHADOW_HORIZONTAL_NEUTRAL}")
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
                _LOGGER.debug(f"Zustand {self.STATE_SHADOW_HORIZONTAL_NEUTRAL}: Nicht in Sonne oder Schattenmodus deaktiviert, fahre in Neutralposition ({neutral_height}%, {neutral_angle}%) und gehe zu {self.STATE_NEUTRAL}")
                return self.STATE_NEUTRAL
            else:
                _LOGGER.debug(f"Zustand {self.STATE_SHADOW_HORIZONTAL_NEUTRAL}: Neutrale Höhe oder Winkel nicht konfiguriert, gehe zu {self.STATE_NEUTRAL}")
                return self.STATE_NEUTRAL

        # Entsprechung zu LB_LBSID_positionShutterWithPreviousValues
        _LOGGER.debug(f"Zustand {self.STATE_SHADOW_HORIZONTAL_NEUTRAL}: Beibehalte vorherige Position.")
        return self.STATE_SHADOW_HORIZONTAL_NEUTRAL

    # =======================================================================
    # State SHADOW_NEUTRAL_TIMER_RUNNING
    async def _handle_state_shadow_neutral_timer_running(self) -> str:
        if await self._is_lbs_locked_in_either_way():
            _LOGGER.debug(f"Zustand {self.STATE_SHADOW_NEUTRAL_TIMER_RUNNING}: LBS ist gesperrt, keine Aktion.")
            return self.STATE_SHADOW_NEUTRAL_TIMER_RUNNING

        if await self._check_if_facade_is_in_sun() and await self._is_shadow_handling_activated():
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
                _LOGGER.debug(f"Zustand {self.STATE_SHADOW_NEUTRAL_TIMER_RUNNING}: Helligkeit ({current_brightness}) wieder über Schwellwert ({shadow_threshold_close}), gehe zu {self.STATE_SHADOW_FULL_CLOSED} und stoppe Timer.")
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
                        _LOGGER.debug(f"Zustand {self.STATE_SHADOW_NEUTRAL_TIMER_RUNNING}: Timer abgelaufen, fahre in Position nach Schatten ({height_after_shadow}%, {angle_after_shadow}°) und gehe zu {self.STATE_SHADOW_NEUTRAL}")
                        return self.STATE_SHADOW_NEUTRAL
                    else:
                        _LOGGER.debug(f"Zustand {self.STATE_SHADOW_NEUTRAL_TIMER_RUNNING}: Höhe oder Winkel nach Schatten nicht konfiguriert, bleibe in {self.STATE_SHADOW_NEUTRAL_TIMER_RUNNING}")
                        return self.STATE_SHADOW_NEUTRAL_TIMER_RUNNING
                else:
                    _LOGGER.debug(f"Zustand {self.STATE_SHADOW_NEUTRAL_TIMER_RUNNING}: Warte auf Timer (Helligkeit nicht hoch genug)...")
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
                _LOGGER.debug(f"Zustand {self.STATE_SHADOW_NEUTRAL_TIMER_RUNNING}: Nicht in Sonne oder Schattenmodus deaktiviert, fahre in Neutralposition ({neutral_height}%, {neutral_angle}%) und gehe zu {self.STATE_NEUTRAL}")
                return self.STATE_NEUTRAL
            else:
                _LOGGER.debug(f"Zustand {self.STATE_SHADOW_NEUTRAL_TIMER_RUNNING}: Neutrale Höhe oder Winkel nicht konfiguriert, gehe zu {self.STATE_NEUTRAL}")
                return self.STATE_NEUTRAL

        # Entsprechung zu LB_LBSID_positionShutterWithPreviousValues
        _LOGGER.debug(f"Zustand {self.STATE_SHADOW_NEUTRAL_TIMER_RUNNING}: Beibehalte vorherige Position.")
        return self.STATE_SHADOW_NEUTRAL_TIMER_RUNNING

    # =======================================================================
    # State SHADOW_NEUTRAL
    async def _handle_state_shadow_neutral(self) -> str:
        if await self._is_lbs_locked_in_either_way():
            _LOGGER.debug(f"Zustand {self.STATE_SHADOW_NEUTRAL}: LBS ist gesperrt, keine Aktion.")
            return self.STATE_SHADOW_NEUTRAL

        if await self._check_if_facade_is_in_sun() and await self._is_shadow_handling_activated():
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
                _LOGGER.debug(f"Zustand {self.STATE_SHADOW_NEUTRAL}: Helligkeit ({current_brightness}) über Schatten-Schwellwert ({shadow_threshold_close}), starte Timer für {self.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING} ({shadow_close_delay}s)")
                await self._start_timer(shadow_close_delay)
                return self.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING
            elif (
                    dawn_handling_active
                    and dawn_brightness is not None
                    and dawn_threshold_close is not None
                    and dawn_brightness < dawn_threshold_close
                    and dawn_close_delay is not None
            ):
                _LOGGER.debug(f"Zustand {self.STATE_SHADOW_NEUTRAL}: Dämmerungsbehandlung aktiv und Helligkeit ({dawn_brightness}) unter Dämmerungs-Schwellwert ({dawn_threshold_close}), starte Timer für {self.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING} ({dawn_close_delay}s)")
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
                _LOGGER.debug(f"Zustand {self.STATE_SHADOW_NEUTRAL}: Bewege Behang in Position nach Schatten ({height_after_shadow}%, {angle_after_shadow}%).")
                return self.STATE_SHADOW_NEUTRAL
            else:
                _LOGGER.debug(f"Zustand {self.STATE_SHADOW_NEUTRAL}: Höhe oder Winkel nach Schatten nicht konfiguriert, bleibe in {self.STATE_SHADOW_NEUTRAL}")
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
                _LOGGER.debug(f"Zustand {self.STATE_SHADOW_NEUTRAL}: Dämmerungsbehandlung aktiv und Helligkeit ({dawn_brightness}) unter Dämmerungs-Schwellwert ({dawn_threshold_close}), starte Timer für {self.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING} ({dawn_close_delay}s)")
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
            _LOGGER.debug(f"Zustand {self.STATE_SHADOW_NEUTRAL}: Nicht in Sonne oder Schattenmodus deaktiviert und Dämmerung nicht aktiv, fahre in Neutralposition ({neutral_height}%, {neutral_angle}%) und gehe zu {self.STATE_NEUTRAL}")
            return self.STATE_NEUTRAL
        else:
            _LOGGER.debug(f"Zustand {self.STATE_SHADOW_NEUTRAL}: Neutrale Höhe oder Winkel nicht konfiguriert, gehe zu {self.STATE_NEUTRAL}")
            return self.STATE_NEUTRAL

    # =======================================================================
    # State NEUTRAL
    async def _handle_state_neutral(self) -> str:
        if await self._is_lbs_locked_in_either_way():
            _LOGGER.debug(f"Zustand {self.STATE_NEUTRAL}: LBS ist gesperrt, keine Aktion."
            )
            return self.STATE_NEUTRAL

        if await self._check_if_facade_is_in_sun() and await self._is_shadow_handling_activated():
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
                _LOGGER.debug(f"Zustand {self.STATE_NEUTRAL}: Helligkeit ({current_brightness}) über Schatten-Schwellwert ({shadow_threshold_close}), starte Timer für {self.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING} ({shadow_close_delay}s)")
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
                _LOGGER.debug(f"Zustand {self.STATE_NEUTRAL}: Dämmerungsbehandlung aktiv und Helligkeit ({dawn_brightness}) unter Dämmerungs-Schwellwert ({dawn_threshold_close}), starte Timer für {self.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING} ({dawn_close_delay}s)")
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
            _LOGGER.debug(f"Zustand {self.STATE_NEUTRAL}: Bewege Behang in Neutralposition ({neutral_height}%, {neutral_angle}%).")
        return self.STATE_NEUTRAL

    # =======================================================================
    # State DAWN_NEUTRAL
    async def _handle_state_dawn_neutral(self) -> str:
        if await self._is_lbs_locked_in_either_way():
            _LOGGER.debug(f"Zustand {self.STATE_DAWN_NEUTRAL}: LBS ist gesperrt, keine Aktion.")
            return self.STATE_DAWN_NEUTRAL

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
                return self.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING
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
                return self.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING
            elif height_after_dawn is not None and angle_after_dawn is not None:
                await self._position_shutter(
                    float(height_after_dawn),
                    float(angle_after_dawn),
                    0,  # Richtung: Neutral
                    force=True,
                    stop_timer=False,
                )
                _LOGGER.debug(f"Zustand {self.STATE_DAWN_NEUTRAL}: Bewege Behang in Position nach Dämmerung ({height_after_dawn}%, {angle_after_dawn}%).")
                return self.STATE_DAWN_NEUTRAL
            else:
                _LOGGER.debug(f"Zustand {self.STATE_DAWN_NEUTRAL}: Höhe oder Winkel nach Dämmerung nicht konfiguriert, bleibe in {self.STATE_DAWN_NEUTRAL}")
                return self.STATE_DAWN_NEUTRAL

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
            return self.STATE_SHADOW_FULL_CLOSE_TIMER_RUNNING

        if neutral_height is not None and neutral_angle is not None:
            await self._position_shutter(
                float(neutral_height),
                float(neutral_angle),
                0,  # Richtung: Neutral
                force=True,
                stop_timer=True,  # Stop Timer (falls ein Timer aktiv war)
            )
            _LOGGER.debug(f"Zustand {self.STATE_DAWN_NEUTRAL}: Dämmerungsbehandlung deaktiviert oder nicht die Bedingungen für Schatten, fahre in Neutralposition ({neutral_height}%, {neutral_angle}%).")
            return self.STATE_NEUTRAL
        else:
            _LOGGER.debug(f"Zustand {self.STATE_DAWN_NEUTRAL}: Neutrale Höhe oder Winkel nicht konfiguriert, gehe zu {self.STATE_NEUTRAL}")
            return self.STATE_NEUTRAL

    # =======================================================================
    # State DAWN_NEUTRAL_TIMER_RUNNING
    async def _handle_state_dawn_neutral_timer_running(self) -> str:
        if await self._is_lbs_locked_in_either_way():
            _LOGGER.debug(f"Zustand {self.STATE_DAWN_NEUTRAL_TIMER_RUNNING}: LBS ist gesperrt, keine Aktion.")
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
                _LOGGER.debug(f"Zustand {self.STATE_DAWN_NEUTRAL_TIMER_RUNNING}: Dämmerungshelligkeit ({dawn_brightness}) wieder unter Schwellwert ({dawn_threshold_close}), gehe zu {self.STATE_DAWN_FULL_CLOSED} und stoppe Timer.")
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
                        _LOGGER.debug(f"Zustand {self.STATE_DAWN_NEUTRAL_TIMER_RUNNING}: Timer abgelaufen, fahre auf Dämmerungshöhe ({dawn_height}%) mit geöffneten Lamellen ({dawn_open_slat_angle}°) und gehe zu {self.STATE_DAWN_NEUTRAL}")
                        return self.STATE_DAWN_NEUTRAL
                    else:
                        _LOGGER.debug(f"Zustand {self.STATE_DAWN_NEUTRAL_TIMER_RUNNING}: Dämmerungshöhe oder Winkel für offene Lamellen nicht konfiguriert, bleibe in {self.STATE_DAWN_NEUTRAL_TIMER_RUNNING}")
                        return self.STATE_DAWN_NEUTRAL_TIMER_RUNNING
                else:
                    _LOGGER.debug(f"Zustand {self.STATE_DAWN_NEUTRAL_TIMER_RUNNING}: Warte auf Timer (Helligkeit nicht niedrig genug)...")
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
                _LOGGER.debug(f"Zustand {self.STATE_DAWN_NEUTRAL_TIMER_RUNNING}: Dämmerungsbehandlung deaktiviert, fahre in Neutralposition ({neutral_height}%, {neutral_angle}%) und gehe zu {self.STATE_NEUTRAL}")
                return self.STATE_NEUTRAL
            else:
                _LOGGER.debug(f"Zustand {self.STATE_DAWN_NEUTRAL_TIMER_RUNNING}: Neutrale Höhe oder Winkel nicht konfiguriert, gehe zu {self.STATE_NEUTRAL}")
                return self.STATE_NEUTRAL

        # Entsprechung zu LB_LBSID_positionShutterWithPreviousValues
        _LOGGER.debug(f"Zustand {self.STATE_DAWN_NEUTRAL_TIMER_RUNNING}: Beibehalte vorherige Position.")
        return self.STATE_DAWN_NEUTRAL_TIMER_RUNNING

    # =======================================================================
    # State DAWN_HORIZONTAL_NEUTRAL
    async def _handle_state_dawn_horizontal_neutral(self) -> str:
        if await self._is_lbs_locked_in_either_way():
            _LOGGER.debug(f"Zustand {self.STATE_DAWN_HORIZONTAL_NEUTRAL}: LBS ist gesperrt, keine Aktion.")
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
                _LOGGER.debug(f"Zustand {self.STATE_DAWN_HORIZONTAL_NEUTRAL}: Dämmerungshelligkeit ({dawn_brightness}) unter Schwellwert ({dawn_threshold_close}), fahre auf Dämmerungshöhe ({dawn_height}%) mit geöffneten Lamellen ({dawn_open_slat_angle}°) und gehe zu {self.STATE_DAWN_FULL_CLOSED}")
                return self.STATE_DAWN_FULL_CLOSED
            elif dawn_open_shutter_delay is not None:
                _LOGGER.debug(f"Zustand {self.STATE_DAWN_HORIZONTAL_NEUTRAL}: Dämmerungshelligkeit nicht unter Schwellwert, starte Timer für {self.STATE_DAWN_NEUTRAL_TIMER_RUNNING} ({dawn_open_shutter_delay}s)")
                await self._start_timer(dawn_open_shutter_delay)
                return self.STATE_DAWN_NEUTRAL_TIMER_RUNNING
            else:
                _LOGGER.debug(f"Zustand {self.STATE_DAWN_HORIZONTAL_NEUTRAL}: Dämmerungshelligkeit nicht unter Schwellwert und 'dawn_open_shutter_delay' nicht konfiguriert, bleibe in {self.STATE_DAWN_HORIZONTAL_NEUTRAL}")
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
                _LOGGER.debug(f"Zustand {self.STATE_DAWN_HORIZONTAL_NEUTRAL}: Dämmerungsbehandlung deaktiviert, fahre in Neutralposition ({neutral_height}%, {neutral_angle}%) und gehe zu {self.STATE_NEUTRAL}")
                return self.STATE_NEUTRAL
            else:
                _LOGGER.debug(f"Zustand {self.STATE_DAWN_HORIZONTAL_NEUTRAL}: Neutrale Höhe oder Winkel nicht konfiguriert, gehe zu {self.STATE_NEUTRAL}")
                return self.STATE_NEUTRAL

        # Entsprechung zu LB_LBSID_positionShutterWithPreviousValues
        _LOGGER.debug(f"Zustand {self.STATE_DAWN_HORIZONTAL_NEUTRAL}: Beibehalte vorherige Position.")
        return self.STATE_DAWN_HORIZONTAL_NEUTRAL

    # =======================================================================
    # State DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING
    async def _handle_state_dawn_horizontal_neutral_timer_running(self) -> str:
        if await self._is_lbs_locked_in_either_way():
            _LOGGER.debug(f"Zustand {self.STATE_DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: LBS ist gesperrt, keine Aktion.")
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
                _LOGGER.debug(f"Zustand {self.STATE_DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Dämmerungshelligkeit ({dawn_brightness}) wieder unter Schwellwert ({dawn_threshold_close}), gehe zu {self.STATE_DAWN_FULL_CLOSED} und stoppe Timer.")
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
                        _LOGGER.debug(f"Zustand {self.STATE_DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Timer abgelaufen, fahre auf Dämmerungshöhe ({dawn_height}%) mit geöffneten Lamellen ({dawn_open_slat_angle}°) und gehe zu {self.STATE_DAWN_HORIZONTAL_NEUTRAL}")
                        return self.STATE_DAWN_HORIZONTAL_NEUTRAL
                    else:
                        _LOGGER.debug(f"Zustand {self.STATE_DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Dämmerungshöhe oder Winkel für offene Lamellen nicht konfiguriert, bleibe in {self.STATE_DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING}")
                        return self.STATE_DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING
                else:
                    _LOGGER.debug(f"Zustand {self.STATE_DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Warte auf Timer (Helligkeit nicht niedrig genug)...")
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
                _LOGGER.debug(f"Zustand {self.STATE_DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Dämmerungsbehandlung deaktiviert, fahre in Neutralposition ({neutral_height}%, {neutral_angle}%) und gehe zu {self.STATE_NEUTRAL}")
                return self.STATE_NEUTRAL
            else:
                _LOGGER.debug(f"Zustand {self.STATE_DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Neutrale Höhe oder Winkel nicht konfiguriert, gehe zu {self.STATE_NEUTRAL}")
                return self.STATE_NEUTRAL

        # Entsprechung zu LB_LBSID_positionShutterWithPreviousValues
        _LOGGER.debug(f"Zustand {self.STATE_DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING}: Beibehalte vorherige Position.")
        return self.STATE_DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING

    # =======================================================================
    # State DAWN_FULL_CLOSED
    async def _handle_state_dawn_full_closed(self) -> str:
        if await self._is_lbs_locked_in_either_way():
            _LOGGER.debug(f"Zustand {self.STATE_DAWN_FULL_CLOSED}: LBS ist gesperrt, keine Aktion.")
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
                _LOGGER.debug(f"Zustand {self.STATE_DAWN_FULL_CLOSED}: Dämmerungshelligkeit ({dawn_brightness}) über Schwellwert ({dawn_threshold_close}), starte Timer für {self.STATE_DAWN_HORIZONTAL_NEUTRAL_TIMER_RUNNING} ({dawn_open_slat_delay}s)")
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
                _LOGGER.debug(f"Zustand {self.STATE_DAWN_FULL_CLOSED}: Dämmerungshelligkeit nicht über Schwellwert, fahre in Dämmerungsposition ({dawn_height}%, {dawn_angle}%).")
                return self.STATE_DAWN_FULL_CLOSED
            else:
                _LOGGER.debug(f"Zustand {self.STATE_DAWN_FULL_CLOSED}: Dämmerungshöhe oder -winkel nicht konfiguriert, bleibe in {self.STATE_DAWN_FULL_CLOSED}")
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
                _LOGGER.debug(f"Zustand {self.STATE_DAWN_FULL_CLOSED}: Dämmerungsbehandlung deaktiviert, fahre in Neutralposition ({neutral_height}%, {neutral_angle}%) und gehe zu {self.STATE_NEUTRAL}")
                return self.STATE_NEUTRAL
            else:
                _LOGGER.debug(f"Zustand {self.STATE_DAWN_FULL_CLOSED}: Neutrale Höhe oder Winkel nicht konfiguriert, gehe zu {self.STATE_NEUTRAL}")
                return self.STATE_NEUTRAL

        # Entsprechung zu LB_LBSID_positionShutterWithPreviousValues
        _LOGGER.debug(f"Zustand {self.STATE_DAWN_FULL_CLOSED}: Beibehalte vorherige Position.")
        return self.STATE_DAWN_FULL_CLOSED

    # =======================================================================
    # State DAWN_FULL_CLOSE_TIMER_RUNNING
    async def _handle_state_dawn_full_close_timer_running(self) -> str:
        if await self._is_lbs_locked_in_either_way():
            _LOGGER.debug(f"Zustand {self.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING}: LBS ist gesperrt, keine Aktion.")
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
                        _LOGGER.debug(f"Zustand {self.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING}: Timer abgelaufen, fahre in volle Dämmerungsposition ({dawn_height}%, {dawn_angle}%) und gehe zu {self.STATE_DAWN_FULL_CLOSED}")
                        return self.STATE_DAWN_FULL_CLOSED
                    else:
                        _LOGGER.debug(f"Zustand {self.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING}: Dämmerungshöhe oder -winkel nicht konfiguriert, bleibe in {self.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING}")
                        return self.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING
                else:
                    _LOGGER.debug(f"Zustand {self.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING}: Warte auf Timer (Helligkeit niedrig genug)...")
                    return self.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING
            else:
                _LOGGER.debug(f"Zustand {self.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING}: Helligkeit ({dawn_brightness}) nicht unter Schwellwert ({dawn_threshold_close}), gehe zu {self.STATE_DAWN_NEUTRAL} und stoppe Timer.")
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
                _LOGGER.debug(f"Zustand {self.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING}: Dämmerungsbehandlung deaktiviert, fahre in Neutralposition ({neutral_height}%, {neutral_angle}%) und gehe zu {self.STATE_NEUTRAL}")
                return self.STATE_NEUTRAL
            else:
                _LOGGER.debug(f"Zustand {self.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING}: Neutrale Höhe oder Winkel nicht konfiguriert, gehe zu {self.STATE_NEUTRAL}")
                return self.STATE_NEUTRAL

        # Entsprechung zu LB_LBSID_positionShutterWithPreviousValues
        _LOGGER.debug(f"Zustand {self.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING}: Beibehalte vorherige Position.")
        return self.STATE_DAWN_FULL_CLOSE_TIMER_RUNNING

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
