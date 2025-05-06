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
    CONF_ANGLE_ENTITY,
    CONF_ANGLE_NEUTRAL,
    CONF_ANGLE_OFFSET,
    CONF_AZIMUT_ENTITY,
    CONF_BRIGHTNESS_DAWN_ENTITY,
    CONF_BRIGHTNESS_ENTITY,
    CONF_COVER_ENTITY,
    CONF_DAWN_CLOSE_DELAY,
    CONF_DAWN_HANDLING_ACTIVATION_ENTITY,
    CONF_DAWN_OPEN_SHUTTER_DELAY,
    CONF_DAWN_OPEN_SLAT_DELAY,
    CONF_DAWN_THRESHOLD_CLOSE,
    CONF_DAWN_THRESHOLD_OPEN,
    CONF_DEBUG_ENABLED,
    CONF_ELEVATION_ENTITY,
    CONF_ELEVATION_MAX,
    CONF_ELEVATION_MIN,
    CONF_FACADE_ANGLE,
    CONF_FACADE_OFFSET_END,
    CONF_FACADE_OFFSET_START,
    CONF_FIX_MOVEMENT_DIRECTION_ANGLE,
    CONF_FIX_MOVEMENT_DIRECTION_HEIGHT,
    CONF_HEIGHT_AFTER_DAWN,
    CONF_HEIGHT_AFTER_SHADOW,
    CONF_HEIGHT_ENTITY,
    CONF_HEIGHT_NEUTRAL,
    CONF_LOCK_ENTITY,
    CONF_LOCK_WITH_FORCED_POSITION_ENTITY,
    CONF_MIN_SHUTTER_ANGLE,
    CONF_MODIFICATION_RANGE_ANGLE,
    CONF_MODIFICATION_RANGE_HEIGHT,
    CONF_NON_SHADOW_RANGE,
    CONF_SHADOW_CLOSE_DELAY,
    CONF_SHADOW_HANDLING_ACTIVATION_ENTITY,
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
        vol.Required(CONF_NAME): str,
        vol.Optional(CONF_COVER_ENTITY): selector({"entity": {"domain": "cover"}}),
        vol.Required(CONF_ELEVATION_ENTITY): str,
        vol.Required(CONF_AZIMUT_ENTITY): str,
        vol.Required(CONF_BRIGHTNESS_ENTITY): str,
        vol.Optional(CONF_BRIGHTNESS_DAWN_ENTITY): str,
        vol.Optional(CONF_LOCK_ENTITY): str,
        vol.Optional(CONF_LOCK_WITH_FORCED_POSITION_ENTITY): str,
        vol.Optional(CONF_HEIGHT_ENTITY): str,
        vol.Optional(CONF_ANGLE_ENTITY): str,
        vol.Required(CONF_HEIGHT_NEUTRAL, default=0): vol.Coerce(int),
        vol.Required(CONF_ANGLE_NEUTRAL, default=50): vol.Coerce(int),
        vol.Required(CONF_HEIGHT_AFTER_SHADOW, default=0): vol.Coerce(int),
        vol.Required(CONF_ANGLE_AFTER_SHADOW, default=50): vol.Coerce(int),
        vol.Required(CONF_HEIGHT_AFTER_DAWN, default=0): vol.Coerce(int),
        vol.Required(CONF_ANGLE_AFTER_DAWN, default=50): vol.Coerce(int),
        vol.Required(CONF_FACADE_ANGLE, default=180): vol.Coerce(int),
        vol.Required(CONF_FACADE_OFFSET_START, default=-30): vol.Coerce(int),
        vol.Required(CONF_FACADE_OFFSET_END, default=30): vol.Coerce(int),
        vol.Required(CONF_NON_SHADOW_RANGE, default=50): vol.Coerce(int),
        vol.Required(CONF_SHUTTER_OVERALL_HEIGHT): vol.Coerce(int),
        vol.Required(CONF_SHUTTER_SLAT_WIDTH): vol.Coerce(int),
        vol.Required(CONF_SHUTTER_SLAT_DISTANCE): vol.Coerce(int),
        vol.Required(CONF_ANGLE_OFFSET, default=0): vol.Coerce(int),
        vol.Required(CONF_MIN_SHUTTER_ANGLE, default=0): vol.Coerce(int),
        vol.Required(CONF_SHADOW_MAX_ANGLE, default=90): vol.Coerce(int),
        vol.Optional(CONF_FIX_MOVEMENT_DIRECTION_HEIGHT, default="none"): vol.In(
            ["none", "up", "down"]
        ),
        vol.Optional(CONF_FIX_MOVEMENT_DIRECTION_ANGLE, default="none"): vol.In(
            ["none", "up", "down"]
        ),
        vol.Required(CONF_MODIFICATION_RANGE_HEIGHT, default=10): vol.Coerce(int),
        vol.Required(CONF_MODIFICATION_RANGE_ANGLE, default=10): vol.Coerce(int),
        vol.Required(CONF_SHADOW_MAX_HEIGHT, default=80): vol.Coerce(int),
        vol.Required(CONF_SHUTTER_TYPE, default=0): vol.In([0, 1]), # 0 für 90°, 1 für 180°
        vol.Required(CONF_SHUTTER_ANGLE_STEPPING, default=5): vol.Coerce(int),
        vol.Required(CONF_SHUTTER_HEIGHT_STEPPING, default=10): vol.Coerce(int),
        vol.Required(CONF_ELEVATION_MIN, default=10): vol.Coerce(int),
        vol.Required(CONF_ELEVATION_MAX, default=80): vol.Coerce(int),
        vol.Required(CONF_SHADOW_HANDLING_ACTIVATION_ENTITY): str,
        vol.Required(CONF_DAWN_HANDLING_ACTIVATION_ENTITY): str,
        vol.Required(CONF_SHADOW_THRESHOLD_CLOSE, default=50): vol.Coerce(int),
        vol.Required(CONF_DAWN_THRESHOLD_CLOSE, default=20): vol.Coerce(int),
        vol.Required(CONF_SHADOW_CLOSE_DELAY, default=5): vol.Coerce(int),
        vol.Required(CONF_SHADOW_OPEN_SLAT_DELAY, default=2): vol.Coerce(int),
        vol.Required(CONF_SHADOW_OPEN_SHUTTER_DELAY, default=10): vol.Coerce(int),
        vol.Required(CONF_DAWN_CLOSE_DELAY, default=10): vol.Coerce(int),
        vol.Required(CONF_DAWN_OPEN_SLAT_DELAY, default=3): vol.Coerce(int),
        vol.Required(CONF_DAWN_OPEN_SHUTTER_DELAY, default=15): vol.Coerce(int),
        vol.Required(CONF_UPDATE_LOCKSTATE_OUTPUT, default="always"): vol.In(
            ["always", "only_on_external_modification", "only_on_manual_lock"]
        ),
        vol.Optional(CONF_DEBUG_ENABLED, default=False): bool,
        vol.Required(CONF_SHADOW_THRESHOLD_OPEN, default=30): vol.Coerce(int),
        vol.Required(CONF_DAWN_THRESHOLD_OPEN, default=60): vol.Coerce(int),
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
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        _LOGGER.debug("Zeige Benutzerformular an")
        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
