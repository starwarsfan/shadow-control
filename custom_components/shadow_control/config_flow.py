"""Config flow for Shadow Control integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import selector

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
    CONF_DAWN_THRESHOLD_OPEN,
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
    CONF_SHADOW_THRESHOLD_OPEN,
    CONF_SHUTTER_ANGLE_STEPPING,
    CONF_SHUTTER_HEIGHT_STEPPING,
    CONF_SHUTTER_OVERALL_HEIGHT,
    CONF_SHUTTER_SLAT_DISTANCE,
    CONF_SHUTTER_SLAT_WIDTH,
    CONF_SHUTTER_TYPE,
    CONF_UPDATE_LOCKSTATE_OUTPUT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): str,  # Name der Beschattungssteuerung
        vol.Optional(CONF_COVER): selector(
            {"entity": {"domain": "cover"}}
        ),  # Auswahl der Cover-Entität
        vol.Required(CONF_BRIGHTNESS): str,  # Helligkeit (Lux)
        vol.Optional(CONF_BRIGHTNESS_DAWN): str,  # Helligkeit Dämmerung (Lux)
        vol.Required(CONF_SUN_ELEVATION, default="sun.sun"): str,  # Elevation (°)
        vol.Required(CONF_SUN_AZIMUT, default="sun.sun"): str,  # Azimut (°)
        vol.Optional(CONF_HEIGHT): str,  # Höhe Ist-Wert (%)
        vol.Optional(CONF_ANGLE): str,  # Winkel Ist-Wert (%)
        vol.Optional(CONF_LOCK, default=False): bool,  # Bausteinsperre (0/1)
        vol.Optional(
            CONF_LOCK_WITH_FORCED_POSITION, default=False
        ): bool,  # Bausteinsperre mit Zwangsposition (0/1)
        vol.Optional(CONF_MODIFICATION_RANGE_HEIGHT, default=10): vol.Coerce(
            int
        ),  # Toleranzbereich für externe Höhenänderungen
        vol.Optional(CONF_MODIFICATION_RANGE_ANGLE, default=10): vol.Coerce(
            int
        ),  # Toleranzbereich für externe Winkeländerungen
        vol.Optional(CONF_DEBUG_ENABLED, default=False): bool,
    }
)

STEP_CONFIG_SCHEMA_GENERAL_SETTINGS = vol.Schema(
    {
        vol.Required(CONF_FACADE_AZIMUTH, default=180): vol.Coerce(
            int
        ),  # Fassadenwinkel (°)
        vol.Required(CONF_FACADE_OFFSET_START, default=-90): vol.Coerce(
            int
        ),  # OffsetEintritt (°)
        vol.Required(CONF_FACADE_OFFSET_END, default=90): vol.Coerce(
            int
        ),  # OffsetAustritt (°)
        vol.Required(CONF_ELEVATION_MIN, default=0): vol.Coerce(
            int
        ),  # Min Elevation (°)
        vol.Required(CONF_ELEVATION_MAX, default=90): vol.Coerce(
            int
        ),  # Max Elevation (°)
        vol.Required(CONF_SHUTTER_SLAT_WIDTH, default=80): vol.Coerce(
            int
        ),  # Lamellenbreite (mm)
        vol.Required(CONF_SHUTTER_SLAT_DISTANCE, default=40): vol.Coerce(
            int
        ),  # Lamellenabstand (mm)
        vol.Required(CONF_ANGLE_OFFSET, default=0): vol.Coerce(
            int
        ),  # Winkel-Offset (%)
        vol.Required(CONF_MIN_SHUTTER_ANGLE, default=0): vol.Coerce(
            int
        ),  # Min. Lamellenwinkel (%)
        vol.Required(CONF_SHUTTER_ANGLE_STEPPING, default=5): vol.Coerce(
            int
        ),  # Winkel-Schrittweite (%)
        vol.Required(CONF_SHUTTER_TYPE, default=0): vol.In(
            [0, 1]
        ),  # Typ bzw. Schwenkbereich (0/1)
        vol.Required(CONF_NON_SHADOW_RANGE, default=0): vol.Coerce(
            int
        ),  # Lichtstreifen (mm)
        vol.Required(CONF_SHUTTER_OVERALL_HEIGHT, default=2000): vol.Coerce(
            int
        ),  # Gesamthoehe (mm)
        vol.Required(CONF_HEIGHT_NEUTRAL, default=0): vol.Coerce(
            int
        ),  # Hoehe in Status NEUTRAL (%)
        vol.Required(CONF_ANGLE_NEUTRAL, default=0): vol.Coerce(
            int
        ),  # Winkel in Status NEUTRAL (%)
        vol.Required(CONF_SHUTTER_HEIGHT_STEPPING, default=5): vol.Coerce(
            int
        ),  # Hoehen-Schrittweite (%)
        vol.Optional(CONF_FIX_MOVEMENT_DIRECTION_HEIGHT, default="none"): vol.In(
            ["none", "up", "down"]
        ),  # Bewegung Hoehe einschraenken (none/up/down)
        vol.Optional(CONF_FIX_MOVEMENT_DIRECTION_ANGLE, default="none"): vol.In(
            ["none", "up", "down"]
        ),  # Bewegung Winkel einschraenken (none/up/down)
        vol.Required(CONF_UPDATE_LOCKSTATE_OUTPUT, default="always"): vol.In(
            ["always", "only_on_external_modification", "only_on_manual_lock"]
        ),  # Update Sperrausgang
    }
)

# Definieren Sie hier STEP_CONFIG_SHADOW_SETTINGS und STEP_CONFIG_DAWN_SETTINGS entsprechend den PHP-Konstanten
STEP_CONFIG_SHADOW_SETTINGS = vol.Schema(
    {
        # Hier die Felder für die Schatteneinstellungen
        vol.Required(CONF_SHADOW_THRESHOLD_CLOSE, default=50): vol.Coerce(int),
        vol.Required(CONF_SHADOW_THRESHOLD_OPEN, default=30): vol.Coerce(int),
        vol.Required(CONF_SHADOW_CLOSE_DELAY, default=5): vol.Coerce(int),
        vol.Required(CONF_SHADOW_OPEN_SLAT_DELAY, default=2): vol.Coerce(int),
        vol.Required(CONF_SHADOW_OPEN_SHUTTER_DELAY, default=10): vol.Coerce(int),
        vol.Required(CONF_SHADOW_MAX_HEIGHT, default=80): vol.Coerce(int),
        vol.Required(CONF_SHADOW_MAX_ANGLE, default=90): vol.Coerce(int),
        vol.Required(CONF_SHADOW_HANDLING_ACTIVATION): str,
        vol.Required(CONF_HEIGHT_AFTER_SHADOW, default=0): vol.Coerce(int),
        vol.Required(CONF_ANGLE_AFTER_SHADOW, default=50): vol.Coerce(int),
    }
)

STEP_CONFIG_DAWN_SETTINGS = vol.Schema(
    {
        # Hier die Felder für die Dämmerungseinstellungen
        vol.Required(CONF_DAWN_THRESHOLD_CLOSE, default=20): vol.Coerce(int),
        vol.Required(CONF_DAWN_THRESHOLD_OPEN, default=60): vol.Coerce(int),
        vol.Required(CONF_DAWN_CLOSE_DELAY, default=10): vol.Coerce(int),
        vol.Required(CONF_DAWN_OPEN_SLAT_DELAY, default=3): vol.Coerce(int),
        vol.Required(CONF_DAWN_OPEN_SHUTTER_DELAY, default=15): vol.Coerce(int),
        vol.Required(CONF_DAWN_HANDLING_ACTIVATION): str,
        vol.Required(CONF_HEIGHT_AFTER_DAWN, default=0): vol.Coerce(int),
        vol.Required(CONF_ANGLE_AFTER_DAWN, default=50): vol.Coerce(int),
    }
)

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Shadow Control."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        _LOGGER.debug(f"async_step_user aufgerufen mit user_input: {user_input}")
        errors: dict[str, str] = {}
        if user_input is not None:
            _LOGGER.debug(f"Benutzereingabe erhalten: {user_input}")
            self.user_input = user_input  # Speichern der ersten Eingaben
            return await self.async_step_general_settings()  # Zum nächsten Schritt

        _LOGGER.debug("Zeige Benutzerformular an")
        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_general_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the general settings step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            final_config = {**self.user_input, **user_input}
            # Hier würden Sie zum nächsten Schritt (STEP_CONFIG_SHADOW_SETTINGS) übergehen
            self.advanced_config = user_input
            return await self.async_step_shadow_settings()
            # return self.async_create_entry(title=final_config[CONF_NAME], data=final_config)

        return self.async_show_form(
            step_id="general_settings",
            data_schema=STEP_CONFIG_SCHEMA_GENERAL_SETTINGS,
            errors=errors,
        )

    async def async_step_shadow_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the shadow settings step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            final_config = {**self.user_input, **self.advanced_config, **user_input}
            # Hier würden Sie zum nächsten Schritt (STEP_CONFIG_DAWN_SETTINGS) übergehen
            self.shadow_config = user_input
            return await self.async_step_dawn_settings()
            # return self.async_create_entry(title=final_config[CONF_NAME], data=final_config)

        return self.async_show_form(
            step_id="shadow_settings",
            data_schema=STEP_CONFIG_SHADOW_SETTINGS,
            errors=errors,
        )

    async def async_step_dawn_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the dawn settings step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            final_config = {**self.user_input, **self.advanced_config, **self.shadow_config, **user_input}
            return self.async_create_entry(title=final_config[CONF_NAME], data=final_config)

        return self.async_show_form(
            step_id="dawn_settings",
            data_schema=STEP_CONFIG_DAWN_SETTINGS,
            errors=errors,
        )
