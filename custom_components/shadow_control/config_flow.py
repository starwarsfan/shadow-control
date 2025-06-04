import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from voluptuous import Any

from .const import DOMAIN, SCFacadeConfig, \
    SCDynamicInput, TARGET_COVER_ENTITY_ID, SC_CONF_NAME, \
    SCShadowInput, SCDawnInput  # Annahme: DOMAIN ist in const.py definiert

_LOGGER = logging.getLogger(__name__)

# --- STEP 1: Name, cover entity  ---
STEP_GENERAL_DATA_SCHEMA = vol.Schema({
    vol.Required(SC_CONF_NAME): selector.TextSelector(
        selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
    ),
    vol.Required(TARGET_COVER_ENTITY_ID): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="cover")
    ),
})

# --- STEP 2: General settings (facade, cover type, ...) ---
STEP_FACADE_SETTINGS_SCHEMA = vol.Schema({
    vol.Required(SCFacadeConfig.AZIMUTH_STATIC.value, default=180): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=359, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Required(SCFacadeConfig.OFFSET_SUN_IN_STATIC.value, default=-90): selector.NumberSelector(
        selector.NumberSelectorConfig(min=-90, max=0, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Required(SCFacadeConfig.OFFSET_SUN_OUT_STATIC.value, default=90): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=90, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Required(SCFacadeConfig.ELEVATION_SUN_MIN_STATIC.value, default=0): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=90, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Required(SCFacadeConfig.ELEVATION_SUN_MAX_STATIC.value, default=90): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=90, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Required(SCFacadeConfig.SLAT_WIDTH_STATIC.value, default=95): selector.NumberSelector(
        selector.NumberSelectorConfig(min=20, max=150, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Required(SCFacadeConfig.SLAT_DISTANCE_STATIC.value, default=67): selector.NumberSelector(
        selector.NumberSelectorConfig(min=20, max=150, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Required(SCFacadeConfig.SLAT_ANGLE_OFFSET_STATIC.value): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=10, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Required(SCFacadeConfig.SLAT_MIN_ANGLE_STATIC.value, default=0): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=90, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Required(SCFacadeConfig.SHUTTER_STEPPING_HEIGHT_STATIC.value, default=10): selector.NumberSelector(
        selector.NumberSelectorConfig(min=1, max=20, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Required(SCFacadeConfig.SHUTTER_STEPPING_ANGLE_STATIC.value, default=10): selector.NumberSelector(
        selector.NumberSelectorConfig(min=1, max=20, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Required(SCFacadeConfig.SHUTTER_TYPE_STATIC.value, default="mode1"): selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=[
                "mode1",
                "mode2"
            ],
            translation_key="facade_shutter_type"
        )
    ),
    vol.Optional(SCFacadeConfig.LIGHT_STRIP_WIDTH_STATIC.value): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=2000, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional(SCFacadeConfig.SHUTTER_HEIGHT_STATIC.value): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=3000, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional(SCFacadeConfig.NEUTRAL_POS_HEIGHT_STATIC.value, default=0): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional(SCFacadeConfig.NEUTRAL_POS_ANGLE_STATIC.value, default=0): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional(SCFacadeConfig.MODIFICATION_TOLERANCE_HEIGHT_STATIC.value, default=0): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=20, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional(SCFacadeConfig.MODIFICATION_TOLERANCE_ANGLE_STATIC.value, default=0): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=20, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
})

# --- STEP 3: Dynamic settings ---
STEP_DYNAMIC_INPUTS_SCHEMA = vol.Schema({
    vol.Required(SCDynamicInput.BRIGHTNESS_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["sensor", "input_number"])
    ),
    vol.Optional(SCDynamicInput.BRIGHTNESS_DAWN_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["sensor", "input_number"])
    ),
    vol.Required(SCDynamicInput.SUN_ELEVATION_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["sensor", "input_number"])
    ),
    vol.Required(SCDynamicInput.SUN_AZIMUTH_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["sensor", "input_number"])
    ),
    vol.Optional(SCDynamicInput.SHUTTER_CURRENT_HEIGHT_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["sensor", "input_number"])
    ),
    vol.Optional(SCDynamicInput.SHUTTER_CURRENT_ANGLE_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["sensor", "input_number"])
    ),
    vol.Optional(SCDynamicInput.LOCK_INTEGRATION_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="input_boolean")
    ),
    vol.Optional(SCDynamicInput.LOCK_INTEGRATION_WITH_POSITION_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="input_boolean")
    ),
    vol.Optional(SCDynamicInput.LOCK_HEIGHT_ENTITY.value): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional(SCDynamicInput.LOCK_ANGLE_ENTITY.value): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional(SCDynamicInput.MOVEMENT_RESTRICTION_HEIGHT_ENTITY.value, default="no_restriction"): selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=[
                "no_restriction",
                "only_close",
                "only_open",
            ],
            translation_key="facade_movement_restriction"
        )
    ),
    vol.Optional(SCDynamicInput.MOVEMENT_RESTRICTION_ANGLE_ENTITY.value, default="no_restriction"): selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=[
                "no_restriction",
                "only_close",
                "only_open",
            ],
            translation_key="facade_movement_restriction"
        )
    ),
})

# --- STEP 4: Shadow settings ---
STEP_SHADOW_SETTINGS_SCHEMA = vol.Schema({
    vol.Required(SCShadowInput.CONTROL_ENABLED_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="input_boolean")
    ),
    # -----------------------------------------------------------------------
    vol.Optional(SCShadowInput.BRIGHTNESS_THRESHOLD_STATIC.value): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=300000, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional(SCShadowInput.BRIGHTNESS_THRESHOLD_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["sensor", "input_number"])
    ),
    # -----------------------------------------------------------------------
    vol.Optional(SCShadowInput.AFTER_SECONDS_STATIC.value): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional(SCShadowInput.AFTER_SECONDS_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["sensor", "input_number"])
    ),
    # -----------------------------------------------------------------------
    vol.Optional(SCShadowInput.SHUTTER_MAX_HEIGHT_STATIC.value, default=100): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
    ),
    vol.Optional(SCShadowInput.SHUTTER_MAX_HEIGHT_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["sensor", "input_number"])
    ),
    # -----------------------------------------------------------------------
    vol.Optional(SCShadowInput.SHUTTER_MAX_ANGLE_STATIC.value, default=100): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
    ),
    vol.Optional(SCShadowInput.SHUTTER_MAX_ANGLE_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["sensor", "input_number"])
    ),
    # -----------------------------------------------------------------------
    vol.Optional(SCShadowInput.SHUTTER_LOOK_THROUGH_SECONDS_STATIC.value): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional(SCShadowInput.SHUTTER_LOOK_THROUGH_SECONDS_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["sensor", "input_number"])
    ),
    # -----------------------------------------------------------------------
    vol.Optional(SCShadowInput.SHUTTER_OPEN_SECONDS_STATIC.value): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional(SCShadowInput.SHUTTER_OPEN_SECONDS_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["sensor", "input_number"])
    ),
    # -----------------------------------------------------------------------
    vol.Optional(SCShadowInput.SHUTTER_LOOK_THROUGH_ANGLE_STATIC.value, default=0): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
    ),
    vol.Optional(SCShadowInput.SHUTTER_LOOK_THROUGH_ANGLE_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["sensor", "input_number"])
    ),
    # -----------------------------------------------------------------------
    vol.Optional(SCShadowInput.HEIGHT_AFTER_SUN_STATIC.value, default=0): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
    ),
    vol.Optional(SCShadowInput.HEIGHT_AFTER_SUN_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["sensor", "input_number"])
    ),
    # -----------------------------------------------------------------------
    vol.Optional(SCShadowInput.ANGLE_AFTER_SUN_STATIC.value, default=0): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
    ),
    vol.Optional(SCShadowInput.ANGLE_AFTER_SUN_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["sensor", "input_number"])
    ),
})

# --- STEP 5: Dawn settings ---
STEP_DAWN_SETTINGS_SCHEMA = vol.Schema({
    vol.Required(SCDawnInput.CONTROL_ENABLED_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="input_boolean")
    ),
    # -----------------------------------------------------------------------
    vol.Optional(SCDawnInput.BRIGHTNESS_THRESHOLD_STATIC.value): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=10000, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional(SCDawnInput.BRIGHTNESS_THRESHOLD_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["sensor", "input_number"])
    ),
    # -----------------------------------------------------------------------
    vol.Optional(SCDawnInput.AFTER_SECONDS_STATIC.value): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional(SCDawnInput.AFTER_SECONDS_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["sensor", "input_number"])
    ),
    # -----------------------------------------------------------------------
    vol.Optional(SCDawnInput.SHUTTER_MAX_HEIGHT_STATIC.value, default=100): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
    ),
    vol.Optional(SCDawnInput.SHUTTER_MAX_HEIGHT_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["sensor", "input_number"])
    ),
    # -----------------------------------------------------------------------
    vol.Optional(SCDawnInput.SHUTTER_MAX_ANGLE_STATIC.value, default=100): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
    ),
    vol.Optional(SCDawnInput.SHUTTER_MAX_ANGLE_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["sensor", "input_number"])
    ),
    # -----------------------------------------------------------------------
    vol.Optional(SCDawnInput.SHUTTER_LOOK_THROUGH_SECONDS_STATIC.value): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional(SCDawnInput.SHUTTER_LOOK_THROUGH_SECONDS_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["sensor", "input_number"])
    ),
    # -----------------------------------------------------------------------
    vol.Optional(SCDawnInput.SHUTTER_OPEN_SECONDS_STATIC.value): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional(SCDawnInput.SHUTTER_OPEN_SECONDS_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["sensor", "input_number"])
    ),
    # -----------------------------------------------------------------------
    vol.Optional(SCDawnInput.SHUTTER_LOOK_THROUGH_ANGLE_STATIC.value, default=0): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
    ),
    vol.Optional(SCDawnInput.SHUTTER_LOOK_THROUGH_ANGLE_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["sensor", "input_number"])
    ),
    # -----------------------------------------------------------------------
    vol.Optional(SCDawnInput.HEIGHT_AFTER_DAWN_STATIC.value, default=0): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
    ),
    vol.Optional(SCDawnInput.HEIGHT_AFTER_DAWN_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["sensor", "input_number"])
    ),
    # -----------------------------------------------------------------------
    vol.Optional(SCDawnInput.ANGLE_AFTER_DAWN_STATIC.value, default=0): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
    ),
    vol.Optional(SCDawnInput.ANGLE_AFTER_DAWN_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["sensor", "input_number"])
    ),
})


class ShadowControlConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Shadow Control."""

    VERSION = 1

    # Used to store data in between the config flow steps
    _data = {}

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial setup step (Step 1: General Settings - Name, Target Cover)."""
        errors = {}

        if user_input is not None:
            target_cover_entity_id = user_input.get(TARGET_COVER_ENTITY_ID)

            # Use unique id to prevent multiple usage of the same cover
            await self.async_set_unique_id(target_cover_entity_id)
            self._abort_if_unique_id_configured()

            self._data.update(user_input)

            # Next ConfigFlow page
            return await self.async_step_facade_settings()

        # Show form of 1st config step
        return self.async_show_form(
            step_id="user",
            data_schema=STEP_GENERAL_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_facade_settings(self, user_input=None) -> FlowResult:
        """Handle the facade and related settings (Step 2)."""
        errors = {}

        if user_input is not None:
            self._data.update(user_input)

            # Next ConfigFlow page
            return await self.async_step_dynamic_inputs()

        # Show form of 2nd config step
        return self.async_show_form(
            step_id="facade_settings",
            data_schema=self.add_suggested_values_to_schema(
                STEP_FACADE_SETTINGS_SCHEMA,
                self._data # Vorausfüllen mit bereits bekannten Werten, falls Benutzer zurückgeht
            ),
            errors=errors,
        )

    async def async_step_dynamic_inputs(self, user_input=None) -> FlowResult:
        """Handle dynamic input (test helpers) settings (Step 3)."""
        errors = {}

        if user_input is not None:
            self._data.update(user_input)

            # Next ConfigFlow page
            return await self.async_step_shadow_settings()

        # Show form of 3rd config step
        return self.async_show_form(
            step_id="dynamic_inputs",
            data_schema=self.add_suggested_values_to_schema(
                STEP_DYNAMIC_INPUTS_SCHEMA,
                self._data # Vorausfüllen mit bereits bekannten Werten
            ),
            errors=errors,
        )

    async def async_step_shadow_settings(self, user_input=None) -> FlowResult:
        """Handle shadow control settings (Step 4)."""
        errors = {}

        # Initialisiere alle Daten, die an das Schema übergeben werden sollen,
        # mit den bereits bekannten Werten aus self._data
        # Dies ist der Basiswert, der dann von user_input überschrieben wird
        suggested_values = self._data.copy()

        if user_input is not None:
            # Führe die aktuellen Benutzereingaben mit den bereits bekannten Werten zusammen.
            # user_input überschreibt dabei alle gleichen Schlüssel in suggested_values.
            suggested_values.update(user_input)

            # Validierungen für "entweder/oder" Paare
            # Helligkeitsschwelle
            brightness_static = user_input.get(SCShadowInput.BRIGHTNESS_THRESHOLD_STATIC.value)
            brightness_entity = user_input.get(SCShadowInput.BRIGHTNESS_THRESHOLD_ENTITY.value)
            if brightness_static is None and brightness_entity is None:
                errors[SCShadowInput.BRIGHTNESS_THRESHOLD_STATIC.value] = "shadow_brightness_threshold_missing"

            # Nach X Sekunden
            after_seconds_static = user_input.get(SCShadowInput.AFTER_SECONDS_STATIC.value)
            after_seconds_entity = user_input.get(SCShadowInput.AFTER_SECONDS_ENTITY.value)
            if after_seconds_static is None and after_seconds_entity is None:
                errors[SCShadowInput.AFTER_SECONDS_STATIC.value] = "shadow_after_seconds_missing"

            # SHUTTER_MAX_HEIGHT
            shutter_height_static =  user_input.get(SCShadowInput.SHUTTER_MAX_HEIGHT_STATIC.value)
            shutter_height_entity = user_input.get(SCShadowInput.SHUTTER_MAX_HEIGHT_ENTITY.value)
            if shutter_height_static is None and shutter_height_entity is None:
                errors[SCShadowInput.SHUTTER_MAX_HEIGHT_STATIC.value] = "shadow_shutter_max_height_missing"

            # SHUTTER_MAX_ANGLE
            shutter_angle_static = user_input.get(SCShadowInput.SHUTTER_MAX_ANGLE_STATIC.value)
            shutter_angle_entity = user_input.get(SCShadowInput.SHUTTER_MAX_ANGLE_ENTITY.value)
            if shutter_angle_static is None and shutter_angle_entity is None:
                errors[SCShadowInput.SHUTTER_MAX_ANGLE_STATIC.value] = "shadow_shutter_max_angle_missing"

            # SHUTTER_LOOK_THROUGH_SECONDS
            look_through_seconds_static = user_input.get(SCShadowInput.SHUTTER_LOOK_THROUGH_SECONDS_STATIC.value)
            look_through_seconds_entity = user_input.get(SCShadowInput.SHUTTER_LOOK_THROUGH_SECONDS_ENTITY.value)
            if look_through_seconds_static is None and look_through_seconds_entity is None:
                errors[SCShadowInput.SHUTTER_LOOK_THROUGH_SECONDS_STATIC.value] = "shadow_look_through_seconds_missing"

            # SHUTTER_OPEN_SECONDS
            open_seconds_static = user_input.get(SCShadowInput.SHUTTER_OPEN_SECONDS_STATIC.value)
            open_seconds_entity = user_input.get(SCShadowInput.SHUTTER_OPEN_SECONDS_ENTITY.value)
            if open_seconds_static is None and open_seconds_entity is None:
                errors[SCShadowInput.SHUTTER_OPEN_SECONDS_STATIC.value] = "shadow_open_seconds_missing"

            # SHUTTER_LOOK_THROUGH_ANGLE
            look_through_angle_static = user_input.get(SCShadowInput.SHUTTER_LOOK_THROUGH_ANGLE_STATIC.value)
            look_through_angle_entity =  user_input.get(SCShadowInput.SHUTTER_LOOK_THROUGH_ANGLE_ENTITY.value)
            if look_through_angle_static is None and look_through_angle_entity is None:
                errors[SCShadowInput.SHUTTER_LOOK_THROUGH_ANGLE_STATIC.value] = "shadow_look_through_angle_missing"

            # HEIGHT_AFTER_SUN
            height_after_sun_static = user_input.get(SCShadowInput.HEIGHT_AFTER_SUN_STATIC.value)
            height_after_sun_entity = user_input.get(SCShadowInput.HEIGHT_AFTER_SUN_ENTITY.value)
            if height_after_sun_static is None and height_after_sun_entity is None:
                errors[SCShadowInput.HEIGHT_AFTER_SUN_STATIC.value] = "shadow_height_after_sun_missing"

            # ANGLE_AFTER_SUN
            angle_after_sun_static = user_input.get(SCShadowInput.ANGLE_AFTER_SUN_STATIC.value)
            angle_after_sun_entity =  user_input.get(SCShadowInput.ANGLE_AFTER_SUN_ENTITY.value)
            if angle_after_sun_static is None and angle_after_sun_entity is None:
                errors[SCShadowInput.ANGLE_AFTER_SUN_STATIC.value] = "shadow_angle_after_sun_missing"


            if not errors: # Nur wenn keine Fehler, dann aktualisieren und weiter
                self._data.update(user_input)
                return await self.async_step_dawn_settings()

        # Show form of 4th config step
        return self.async_show_form(
            step_id="shadow_settings",
            data_schema=self.add_suggested_values_to_schema(
                STEP_SHADOW_SETTINGS_SCHEMA,
                suggested_values # Vorausfüllen mit bereits bekannten Werten
            ),
            errors=errors,
        )

    async def async_step_dawn_settings(self, user_input=None) -> FlowResult:
        """Handle dawn control settings (Step 5 - Final)."""
        errors = {}

        # Initialisiere alle Daten, die an das Schema übergeben werden sollen,
        # mit den bereits bekannten Werten aus self._data
        # Dies ist der Basiswert, der dann von user_input überschrieben wird
        suggested_values = self._data.copy()

        if user_input is not None:
            # Führe die aktuellen Benutzereingaben mit den bereits bekannten Werten zusammen.
            # user_input überschreibt dabei alle gleichen Schlüssel in suggested_values.
            suggested_values.update(user_input)

            # Validierung für BRIGHTNESS_THRESHOLD (Dawn)
            brightness_static = user_input.get(SCDawnInput.BRIGHTNESS_THRESHOLD_STATIC.value)
            brightness_entity = user_input.get(SCDawnInput.BRIGHTNESS_THRESHOLD_ENTITY.value)
            if brightness_static is None and brightness_entity is None:
                errors[SCDawnInput.BRIGHTNESS_THRESHOLD_STATIC.value] = "dawn_brightness_threshold_missing"

            # Validierung für AFTER_SECONDS (Dawn)
            after_seconds_static = user_input.get(SCDawnInput.AFTER_SECONDS_STATIC.value)
            after_seconds_entity = user_input.get(SCDawnInput.AFTER_SECONDS_ENTITY.value)
            if after_seconds_static is None and after_seconds_entity is None:
                errors[SCDawnInput.AFTER_SECONDS_STATIC.value] = "dawn_after_seconds_missing"

            # SHUTTER_MAX_HEIGHT (Dawn)
            shutter_height_static =  user_input.get(SCDawnInput.SHUTTER_MAX_HEIGHT_STATIC.value)
            shutter_height_entity = user_input.get(SCDawnInput.SHUTTER_MAX_HEIGHT_ENTITY.value)
            if shutter_height_static is None and shutter_height_entity is None:
                errors[SCDawnInput.SHUTTER_MAX_HEIGHT_STATIC.value] = "dawn_shutter_max_height_missing"

            # SHUTTER_MAX_ANGLE (Dawn)
            shutter_angle_static = user_input.get(SCDawnInput.SHUTTER_MAX_ANGLE_STATIC.value)
            shutter_angle_entity =  user_input.get(SCDawnInput.SHUTTER_MAX_ANGLE_ENTITY.value)
            if shutter_angle_static is None and shutter_angle_entity is None:
                errors[SCDawnInput.SHUTTER_MAX_ANGLE_STATIC.value] = "dawn_shutter_max_angle_missing"

            # SHUTTER_LOOK_THROUGH_SECONDS (Dawn)
            look_through_seconds_static = user_input.get(SCDawnInput.SHUTTER_LOOK_THROUGH_SECONDS_STATIC.value)
            look_through_seconds_entity = user_input.get(SCDawnInput.SHUTTER_LOOK_THROUGH_SECONDS_ENTITY.value)
            if look_through_seconds_static is None and look_through_seconds_entity is None:
                errors[SCDawnInput.SHUTTER_LOOK_THROUGH_SECONDS_STATIC.value] = "dawn_look_through_seconds_missing"

            # SHUTTER_OPEN_SECONDS (Dawn)
            open_seconds_static = user_input.get(SCDawnInput.SHUTTER_OPEN_SECONDS_STATIC.value)
            open_seconds_entity =  user_input.get(SCDawnInput.SHUTTER_OPEN_SECONDS_ENTITY.value)
            if open_seconds_static is None and open_seconds_entity is None:
                errors[SCDawnInput.SHUTTER_OPEN_SECONDS_STATIC.value] = "dawn_open_seconds_missing"

            # SHUTTER_LOOK_THROUGH_ANGLE (Dawn)
            look_through_angle_static = user_input.get(SCDawnInput.SHUTTER_LOOK_THROUGH_ANGLE_STATIC.value)
            look_through_angle_entity = user_input.get(SCDawnInput.SHUTTER_LOOK_THROUGH_ANGLE_ENTITY.value)
            if look_through_angle_static is None and look_through_angle_entity is None:
                errors[SCDawnInput.SHUTTER_LOOK_THROUGH_ANGLE_STATIC.value] = "dawn_look_through_angle_missing"

            # HEIGHT_AFTER_DAWN (Dawn)
            height_after_sun_static =  user_input.get(SCDawnInput.HEIGHT_AFTER_DAWN_STATIC.value)
            height_after_sun_entity = user_input.get(SCDawnInput.HEIGHT_AFTER_DAWN_ENTITY.value)
            if height_after_sun_static is None and height_after_sun_entity is None:
                errors[SCDawnInput.HEIGHT_AFTER_DAWN_STATIC.value] = "dawn_height_after_dawn_missing"

            # ANGLE_AFTER_DAWN (Dawn)
            angle_after_sun_static = user_input.get(SCDawnInput.ANGLE_AFTER_DAWN_STATIC.value)
            angle_after_sun_entity = user_input.get(SCDawnInput.ANGLE_AFTER_DAWN_ENTITY.value)
            if angle_after_sun_static is None and angle_after_sun_entity is None:
                errors[SCDawnInput.ANGLE_AFTER_DAWN_STATIC.value] = "dawn_angle_after_dawn_missing"

            if not errors: # Nur wenn keine Fehler, dann aktualisieren und weiter
                self._data.update(user_input)
                return self.async_create_entry(
                    title=self._data.get(SC_CONF_NAME, DOMAIN),
                    data=self._data
                )

        # Show form of 5th config step
        return self.async_show_form(
            step_id="dawn_settings",
            data_schema=self.add_suggested_values_to_schema(
                STEP_DAWN_SETTINGS_SCHEMA,
                suggested_values # Vorausfüllen mit bereits bekannten Werten
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return ShadowControlOptionsFlowHandler(config_entry)

class ShadowControlOptionsFlowHandler(config_entries.OptionsFlow):
    """Handles options flow for the component."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        self._data = dict(config_entry.data) # optional: create a mutable copy if you intend to modify it
        self._options = dict(config_entry.options) # optional: create a mutable copy

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the options flow for editing an existing entry."""
        errors = {}

        # Fall 1: Benutzer hat das Formular abgeschickt (user_input ist nicht None)
        if user_input is not None:
            # Speichere die aktualisierten Optionen in der ConfigEntry.
            # `data` im async_create_entry des OptionsFlowHandlers wird in `options` des ConfigEntry gespeichert.
            # Alternativ und sauberer ist es, self.hass.config_entries.async_update_entry direkt zu nutzen.
            # Ich habe den async_update_entry Teil von ganz unten hierher verschoben, da er hier hingehört.
            self.hass.config_entries.async_update_entry(
                self.config_entry, options=user_input
            )

            # Lade die Integration neu, damit sie die neuen Optionen verwendet.
            self.hass.async_create_task(
                self.hass.config_entries.async_reload(self.config_entry.entry_id)
            )

            # Beende den Options-Flow
            # Es wird kein zusätzliches data{} benötigt, da die Optionen bereits aktualisiert wurden.
            return self.async_create_entry(title="") # Kein data={}) ist hier korrekt.


        # Fall 2: Formular wird initial angezeigt oder es gab Fehler im letzten Submit (user_input ist None)

        # Definiere dein Schema für die Optionen
        # HINWEIS: Du musst nun ALLE vol.Required/Optional Felder
        # mit den Default-Werten aus self.config_entry.options oder self.config_entry.data versehen.
        OPTIONS_SCHEMA = vol.Schema({
            # STEP_FACADE_SETTINGS_SCHEMA
            vol.Required(
                SCFacadeConfig.AZIMUTH_STATIC.value,
                default=self.config_entry.options.get(
                    SCFacadeConfig.AZIMUTH_STATIC.value,
                    self.config_entry.data.get(SCFacadeConfig.AZIMUTH_STATIC.value, 180)
                )
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=359, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Required(
                SCFacadeConfig.OFFSET_SUN_IN_STATIC.value,
                default=self.config_entry.options.get(
                    SCFacadeConfig.OFFSET_SUN_IN_STATIC.value,
                    self.config_entry.data.get(SCFacadeConfig.OFFSET_SUN_IN_STATIC.value, -90)
                )
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=-90, max=0, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Required(
                SCFacadeConfig.OFFSET_SUN_OUT_STATIC.value,
                default=self.config_entry.options.get(
                    SCFacadeConfig.OFFSET_SUN_OUT_STATIC.value,
                    self.config_entry.data.get(SCFacadeConfig.OFFSET_SUN_OUT_STATIC.value, 90)
                )
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=90, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Required(
                SCFacadeConfig.ELEVATION_SUN_MIN_STATIC.value,
                default=self.config_entry.options.get(
                    SCFacadeConfig.ELEVATION_SUN_MIN_STATIC.value,
                    self.config_entry.data.get(SCFacadeConfig.ELEVATION_SUN_MIN_STATIC.value, 0)
                )
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=90, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Required(
                SCFacadeConfig.ELEVATION_SUN_MAX_STATIC.value,
                default=self.config_entry.options.get(
                    SCFacadeConfig.ELEVATION_SUN_MAX_STATIC.value,
                    self.config_entry.data.get(SCFacadeConfig.ELEVATION_SUN_MAX_STATIC.value, 90)
                )
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=90, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Required(
                SCFacadeConfig.SLAT_WIDTH_STATIC.value,
                default=self.config_entry.options.get(
                    SCFacadeConfig.SLAT_WIDTH_STATIC.value,
                    self.config_entry.data.get(SCFacadeConfig.SLAT_WIDTH_STATIC.value, 95)
                )
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=20, max=150, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Required(
                SCFacadeConfig.SLAT_DISTANCE_STATIC.value,
                default=self.config_entry.options.get(
                    SCFacadeConfig.SLAT_DISTANCE_STATIC.value,
                    self.config_entry.data.get(SCFacadeConfig.SLAT_DISTANCE_STATIC.value, 67)
                )
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=20, max=150, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Required(
                SCFacadeConfig.SLAT_ANGLE_OFFSET_STATIC.value,
                # Für diesen Wert gab es keinen initialen Default in deiner Liste,
                # daher musst du einen passenden initialen Default-Wert festlegen,
                # falls er weder in options noch in data gefunden wird.
                # Hier ein Beispielwert von 0.
                default=self.config_entry.options.get(
                    SCFacadeConfig.SLAT_ANGLE_OFFSET_STATIC.value,
                    self.config_entry.data.get(SCFacadeConfig.SLAT_ANGLE_OFFSET_STATIC.value, 0) # Wichtig: Initialer Default muss hier rein!
                )
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=10, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Required(
                SCFacadeConfig.SLAT_MIN_ANGLE_STATIC.value,
                default=self.config_entry.options.get(
                    SCFacadeConfig.SLAT_MIN_ANGLE_STATIC.value,
                    self.config_entry.data.get(SCFacadeConfig.SLAT_MIN_ANGLE_STATIC.value, 0)
                )
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=90, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Required(
                SCFacadeConfig.SHUTTER_STEPPING_HEIGHT_STATIC.value,
                default=self.config_entry.options.get(
                    SCFacadeConfig.SHUTTER_STEPPING_HEIGHT_STATIC.value,
                    self.config_entry.data.get(SCFacadeConfig.SHUTTER_STEPPING_HEIGHT_STATIC.value, 10)
                )
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=1, max=20, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Required(
                SCFacadeConfig.SHUTTER_STEPPING_ANGLE_STATIC.value,
                default=self.config_entry.options.get(
                    SCFacadeConfig.SHUTTER_STEPPING_ANGLE_STATIC.value,
                    self.config_entry.data.get(SCFacadeConfig.SHUTTER_STEPPING_ANGLE_STATIC.value, 10)
                )
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=1, max=20, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Required(
                SCFacadeConfig.SHUTTER_TYPE_STATIC.value,
                default=self.config_entry.options.get(
                    SCFacadeConfig.SHUTTER_TYPE_STATIC.value,
                    self.config_entry.data.get(SCFacadeConfig.SHUTTER_TYPE_STATIC.value, "mode1") # Der ursprüngliche Default-Wert
                )
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        "mode1",
                        "mode2"
                    ],
                    translation_key="facade_shutter_type"
                )
            ),
            vol.Optional(
                SCFacadeConfig.LIGHT_STRIP_WIDTH_STATIC.value,
                # Da kein initialer Default angegeben war, nutzen wir 0 als Fallback für Zahlen.
                default=self.config_entry.options.get(
                    SCFacadeConfig.LIGHT_STRIP_WIDTH_STATIC.value,
                    self.config_entry.data.get(SCFacadeConfig.LIGHT_STRIP_WIDTH_STATIC.value, "")
                )
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=2000, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(
                SCFacadeConfig.SHUTTER_HEIGHT_STATIC.value,
                # Kein initialer Default, also 0 als Fallback.
                default=self.config_entry.options.get(
                    SCFacadeConfig.SHUTTER_HEIGHT_STATIC.value,
                    self.config_entry.data.get(SCFacadeConfig.SHUTTER_HEIGHT_STATIC.value, "")
                )
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=3000, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(
                SCFacadeConfig.NEUTRAL_POS_HEIGHT_STATIC.value,
                default=self.config_entry.options.get(
                    SCFacadeConfig.NEUTRAL_POS_HEIGHT_STATIC.value,
                    self.config_entry.data.get(SCFacadeConfig.NEUTRAL_POS_HEIGHT_STATIC.value, "")
                )
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(
                SCFacadeConfig.NEUTRAL_POS_ANGLE_STATIC.value,
                default=self.config_entry.options.get(
                    SCFacadeConfig.NEUTRAL_POS_ANGLE_STATIC.value,
                    self.config_entry.data.get(SCFacadeConfig.NEUTRAL_POS_ANGLE_STATIC.value, "")
                )
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(
                SCFacadeConfig.MODIFICATION_TOLERANCE_HEIGHT_STATIC.value,
                default=self.config_entry.options.get(
                    SCFacadeConfig.MODIFICATION_TOLERANCE_HEIGHT_STATIC.value,
                    self.config_entry.data.get(SCFacadeConfig.MODIFICATION_TOLERANCE_HEIGHT_STATIC.value, "")
                )
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=20, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(
                SCFacadeConfig.MODIFICATION_TOLERANCE_ANGLE_STATIC.value,
                default=self.config_entry.options.get(
                    SCFacadeConfig.MODIFICATION_TOLERANCE_ANGLE_STATIC.value,
                    self.config_entry.data.get(SCFacadeConfig.MODIFICATION_TOLERANCE_ANGLE_STATIC.value, "")
                )
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=20, step=1, mode=selector.NumberSelectorMode.BOX)
            ),

            # STEP_DYNAMIC_INPUTS_SCHEMA
            vol.Required(
                SCDynamicInput.BRIGHTNESS_ENTITY.value,
                default=self.config_entry.options.get(
                    SCDynamicInput.BRIGHTNESS_ENTITY.value,
                    self.config_entry.data.get(SCDynamicInput.BRIGHTNESS_ENTITY.value, "no_entity_selected")
                )
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number"])
            ),
            vol.Optional(
                SCDynamicInput.BRIGHTNESS_DAWN_ENTITY.value,
                default=self.config_entry.options.get(
                    SCDynamicInput.BRIGHTNESS_DAWN_ENTITY.value,
                    self.config_entry.data.get(SCDynamicInput.BRIGHTNESS_DAWN_ENTITY.value, "")
                )
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number"])
            ),
            vol.Required(
                SCDynamicInput.SUN_ELEVATION_ENTITY.value,
                default=self.config_entry.options.get(
                    SCDynamicInput.SUN_ELEVATION_ENTITY.value,
                    self.config_entry.data.get(SCDynamicInput.SUN_ELEVATION_ENTITY.value, "no_entity_selected")
                )
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number"])
            ),
            vol.Required(
                SCDynamicInput.SUN_AZIMUTH_ENTITY.value,
                default=self.config_entry.options.get(
                    SCDynamicInput.SUN_AZIMUTH_ENTITY.value,
                    self.config_entry.data.get(SCDynamicInput.SUN_AZIMUTH_ENTITY.value, "no_entity_selected")
                )
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number"])
            ),
            vol.Optional(
                SCDynamicInput.SHUTTER_CURRENT_HEIGHT_ENTITY.value,
                default=self.config_entry.options.get(
                    SCDynamicInput.SHUTTER_CURRENT_HEIGHT_ENTITY.value,
                    self.config_entry.data.get(SCDynamicInput.SHUTTER_CURRENT_HEIGHT_ENTITY.value, "")
                )
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number"])
            ),
            vol.Optional(
                SCDynamicInput.SHUTTER_CURRENT_ANGLE_ENTITY.value,
                default=self.config_entry.options.get(
                    SCDynamicInput.SHUTTER_CURRENT_ANGLE_ENTITY.value,
                    self.config_entry.data.get(SCDynamicInput.SHUTTER_CURRENT_ANGLE_ENTITY.value, "")
                )
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number"])
            ),
            vol.Optional(
                SCDynamicInput.LOCK_INTEGRATION_ENTITY.value,
                # For input_boolean, "no_entity_selected" is a good default if not set.
                default=self.config_entry.options.get(
                    SCDynamicInput.LOCK_INTEGRATION_ENTITY.value,
                    self.config_entry.data.get(SCDynamicInput.LOCK_INTEGRATION_ENTITY.value, "")
                )
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="input_boolean")
            ),
            vol.Optional(
                SCDynamicInput.LOCK_INTEGRATION_WITH_POSITION_ENTITY.value,
                # For input_boolean, "no_entity_selected" is a good default if not set.
                default=self.config_entry.options.get(
                    SCDynamicInput.LOCK_INTEGRATION_WITH_POSITION_ENTITY.value,
                    self.config_entry.data.get(SCDynamicInput.LOCK_INTEGRATION_WITH_POSITION_ENTITY.value, "")
                )
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="input_boolean")
            ),
            vol.Optional(
                SCDynamicInput.LOCK_HEIGHT_ENTITY.value,
                # Default to 0 if not set, or another sensible initial value.
                default=self.config_entry.options.get(
                    SCDynamicInput.LOCK_HEIGHT_ENTITY.value,
                    self.config_entry.data.get(SCDynamicInput.LOCK_HEIGHT_ENTITY.value, 0)
                )
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(
                SCDynamicInput.LOCK_ANGLE_ENTITY.value,
                # Default to 0 if not set, or another sensible initial value.
                default=self.config_entry.options.get(
                    SCDynamicInput.LOCK_ANGLE_ENTITY.value,
                    self.config_entry.data.get(SCDynamicInput.LOCK_ANGLE_ENTITY.value, 0)
                )
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(
                SCDynamicInput.MOVEMENT_RESTRICTION_HEIGHT_ENTITY.value,
                default=self.config_entry.options.get(
                    SCDynamicInput.MOVEMENT_RESTRICTION_HEIGHT_ENTITY.value,
                    self.config_entry.data.get(SCDynamicInput.MOVEMENT_RESTRICTION_HEIGHT_ENTITY.value, "no_restriction")
                )
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        "no_restriction",
                        "only_close",
                        "only_open",
                    ],
                    translation_key="facade_movement_restriction"
                )
            ),
            vol.Optional(
                SCDynamicInput.MOVEMENT_RESTRICTION_ANGLE_ENTITY.value,
                default=self.config_entry.options.get(
                    SCDynamicInput.MOVEMENT_RESTRICTION_ANGLE_ENTITY.value,
                    self.config_entry.data.get(SCDynamicInput.MOVEMENT_RESTRICTION_ANGLE_ENTITY.value, "")
                )
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        "no_restriction",
                        "only_close",
                        "only_open",
                    ],
                    translation_key="facade_movement_restriction"
                )
            ),

            # ===============================================================
            # STEP_SHADOW_SETTINGS_SCHEMA
            # -----------------------------------------------------------------------
            vol.Required(
                SCShadowInput.CONTROL_ENABLED_ENTITY.value,
                default=self.config_entry.options.get(
                    SCShadowInput.CONTROL_ENABLED_ENTITY.value,
                    self.config_entry.data.get(SCShadowInput.CONTROL_ENABLED_ENTITY.value, "no_entity_selected") # 'input_boolean' ist auch ein Entity Selector
                )
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="input_boolean")
            ),
            # -----------------------------------------------------------------------
            vol.Required(
                SCShadowInput.BRIGHTNESS_THRESHOLD_STATIC.value,
                default=self.config_entry.options.get(
                    SCShadowInput.BRIGHTNESS_THRESHOLD_STATIC.value,
                    self.config_entry.data.get(SCShadowInput.BRIGHTNESS_THRESHOLD_STATIC.value, 0) # Oder ein anderer passender Standardwert
                )
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=300000, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(
                SCShadowInput.BRIGHTNESS_THRESHOLD_ENTITY.value,
                default=self.config_entry.options.get(
                    SCShadowInput.BRIGHTNESS_THRESHOLD_ENTITY.value,
                    self.config_entry.data.get(SCShadowInput.BRIGHTNESS_THRESHOLD_ENTITY.value, "")
                )
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number"])
            ),
            # -----------------------------------------------------------------------
            vol.Required(
                SCShadowInput.AFTER_SECONDS_STATIC.value,
                default=self.config_entry.options.get(
                    SCShadowInput.AFTER_SECONDS_STATIC.value,
                    self.config_entry.data.get(SCShadowInput.AFTER_SECONDS_STATIC.value, 0) # Oder ein anderer passender Standardwert
                )
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(
                SCShadowInput.AFTER_SECONDS_ENTITY.value,
                default=self.config_entry.options.get(
                    SCShadowInput.AFTER_SECONDS_ENTITY.value,
                    self.config_entry.data.get(SCShadowInput.AFTER_SECONDS_ENTITY.value, "")
                )
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number"])
            ),
            # -----------------------------------------------------------------------
            vol.Optional(
                SCShadowInput.SHUTTER_MAX_HEIGHT_STATIC.value,
                default=self.config_entry.options.get(
                    SCShadowInput.SHUTTER_MAX_HEIGHT_STATIC.value,
                    self.config_entry.data.get(SCShadowInput.SHUTTER_MAX_HEIGHT_STATIC.value, "")
                )
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
            ),
            vol.Optional(
                SCShadowInput.SHUTTER_MAX_HEIGHT_ENTITY.value,
                default=self.config_entry.options.get(
                    SCShadowInput.SHUTTER_MAX_HEIGHT_ENTITY.value,
                    self.config_entry.data.get(SCShadowInput.SHUTTER_MAX_HEIGHT_ENTITY.value, "")
                )
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number"])
            ),
            # -----------------------------------------------------------------------
            vol.Optional(
                SCShadowInput.SHUTTER_MAX_ANGLE_STATIC.value,
                default=self.config_entry.options.get(
                    SCShadowInput.SHUTTER_MAX_ANGLE_STATIC.value,
                    self.config_entry.data.get(SCShadowInput.SHUTTER_MAX_ANGLE_STATIC.value, "")
                )
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
            ),
            vol.Optional(
                SCShadowInput.SHUTTER_MAX_ANGLE_ENTITY.value,
                default=self.config_entry.options.get(
                    SCShadowInput.SHUTTER_MAX_ANGLE_ENTITY.value,
                    self.config_entry.data.get(SCShadowInput.SHUTTER_MAX_ANGLE_ENTITY.value, "")
                )
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number"])
            ),
            # -----------------------------------------------------------------------
            vol.Required(
                SCShadowInput.SHUTTER_LOOK_THROUGH_SECONDS_STATIC.value,
                default=self.config_entry.options.get(
                    SCShadowInput.SHUTTER_LOOK_THROUGH_SECONDS_STATIC.value,
                    self.config_entry.data.get(SCShadowInput.SHUTTER_LOOK_THROUGH_SECONDS_STATIC.value, 0)
                )
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(
                SCShadowInput.SHUTTER_LOOK_THROUGH_SECONDS_ENTITY.value,
                default=self.config_entry.options.get(
                    SCShadowInput.SHUTTER_LOOK_THROUGH_SECONDS_ENTITY.value,
                    self.config_entry.data.get(SCShadowInput.SHUTTER_LOOK_THROUGH_SECONDS_ENTITY.value, "")
                )
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number"])
            ),
            # -----------------------------------------------------------------------
            vol.Required(
                SCShadowInput.SHUTTER_OPEN_SECONDS_STATIC.value,
                default=self.config_entry.options.get(
                    SCShadowInput.SHUTTER_OPEN_SECONDS_STATIC.value,
                    self.config_entry.data.get(SCShadowInput.SHUTTER_OPEN_SECONDS_STATIC.value, 0)
                )
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(
                SCShadowInput.SHUTTER_OPEN_SECONDS_ENTITY.value,
                default=self.config_entry.options.get(
                    SCShadowInput.SHUTTER_OPEN_SECONDS_ENTITY.value,
                    self.config_entry.data.get(SCShadowInput.SHUTTER_OPEN_SECONDS_ENTITY.value, "")
                )
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number"])
            ),
            # -----------------------------------------------------------------------
            vol.Optional(
                SCShadowInput.SHUTTER_LOOK_THROUGH_ANGLE_STATIC.value,
                default=self.config_entry.options.get(
                    SCShadowInput.SHUTTER_LOOK_THROUGH_ANGLE_STATIC.value,
                    self.config_entry.data.get(SCShadowInput.SHUTTER_LOOK_THROUGH_ANGLE_STATIC.value, "")
                )
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
            ),
            vol.Optional(
                SCShadowInput.SHUTTER_LOOK_THROUGH_ANGLE_ENTITY.value,
                default=self.config_entry.options.get(
                    SCShadowInput.SHUTTER_LOOK_THROUGH_ANGLE_ENTITY.value,
                    self.config_entry.data.get(SCShadowInput.SHUTTER_LOOK_THROUGH_ANGLE_ENTITY.value, "")
                )
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number"])
            ),
            # -----------------------------------------------------------------------
            vol.Optional(
                SCShadowInput.HEIGHT_AFTER_SUN_STATIC.value,
                default=self.config_entry.options.get(
                    SCShadowInput.HEIGHT_AFTER_SUN_STATIC.value,
                    self.config_entry.data.get(SCShadowInput.HEIGHT_AFTER_SUN_STATIC.value, "")
                )
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
            ),
            vol.Optional(
                SCShadowInput.HEIGHT_AFTER_SUN_ENTITY.value,
                default=self.config_entry.options.get(
                    SCShadowInput.HEIGHT_AFTER_SUN_ENTITY.value,
                    self.config_entry.data.get(SCShadowInput.HEIGHT_AFTER_SUN_ENTITY.value, "")
                )
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number"])
            ),
            # -----------------------------------------------------------------------
            vol.Optional(
                SCShadowInput.ANGLE_AFTER_SUN_STATIC.value,
                default=self.config_entry.options.get(
                    SCShadowInput.ANGLE_AFTER_SUN_STATIC.value,
                    self.config_entry.data.get(SCShadowInput.ANGLE_AFTER_SUN_STATIC.value, "")
                )
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
            ),
            vol.Optional(
                SCShadowInput.ANGLE_AFTER_SUN_ENTITY.value,
                default=self.config_entry.options.get(
                    SCShadowInput.ANGLE_AFTER_SUN_ENTITY.value,
                    self.config_entry.data.get(SCShadowInput.ANGLE_AFTER_SUN_ENTITY.value, "")
                )
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number"])
            ),

            # ===============================================================
            # STEP_DAWN_SETTINGS_SCHEMA
            vol.Required(
                SCDawnInput.CONTROL_ENABLED_ENTITY.value,
                default=self.config_entry.options.get(
                    SCDawnInput.CONTROL_ENABLED_ENTITY.value,
                    self.config_entry.data.get(SCDawnInput.CONTROL_ENABLED_ENTITY.value, "no_entity_selected")
                )
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="input_boolean")
            ),
            # -----------------------------------------------------------------------
            vol.Required(
                SCDawnInput.BRIGHTNESS_THRESHOLD_STATIC.value,
                default=self.config_entry.options.get(
                    SCDawnInput.BRIGHTNESS_THRESHOLD_STATIC.value,
                    self.config_entry.data.get(SCDawnInput.BRIGHTNESS_THRESHOLD_STATIC.value, 0) # Beispiel-Default, anpassen falls nötig
                )
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=10000, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(
                SCDawnInput.BRIGHTNESS_THRESHOLD_ENTITY.value,
                default=self.config_entry.options.get(
                    SCDawnInput.BRIGHTNESS_THRESHOLD_ENTITY.value,
                    self.config_entry.data.get(SCDawnInput.BRIGHTNESS_THRESHOLD_ENTITY.value, "")
                )
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number"])
            ),
            # -----------------------------------------------------------------------
            vol.Required(
                SCDawnInput.AFTER_SECONDS_STATIC.value,
                default=self.config_entry.options.get(
                    SCDawnInput.AFTER_SECONDS_STATIC.value,
                    self.config_entry.data.get(SCDawnInput.AFTER_SECONDS_STATIC.value, 0) # Beispiel-Default, anpassen falls nötig
                )
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(
                SCDawnInput.AFTER_SECONDS_ENTITY.value,
                default=self.config_entry.options.get(
                    SCDawnInput.AFTER_SECONDS_ENTITY.value,
                    self.config_entry.data.get(SCDawnInput.AFTER_SECONDS_ENTITY.value, "")
                )
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number"])
            ),
            # -----------------------------------------------------------------------
            vol.Optional(
                SCDawnInput.SHUTTER_MAX_HEIGHT_STATIC.value,
                default=self.config_entry.options.get(
                    SCDawnInput.SHUTTER_MAX_HEIGHT_STATIC.value,
                    self.config_entry.data.get(SCDawnInput.SHUTTER_MAX_HEIGHT_STATIC.value, "")
                )
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
            ),
            vol.Optional(
                SCDawnInput.SHUTTER_MAX_HEIGHT_ENTITY.value,
                default=self.config_entry.options.get(
                    SCDawnInput.SHUTTER_MAX_HEIGHT_ENTITY.value,
                    self.config_entry.data.get(SCDawnInput.SHUTTER_MAX_HEIGHT_ENTITY.value, "")
                )
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number"])
            ),
            # -----------------------------------------------------------------------
            vol.Optional(
                SCDawnInput.SHUTTER_MAX_ANGLE_STATIC.value,
                default=self.config_entry.options.get(
                    SCDawnInput.SHUTTER_MAX_ANGLE_STATIC.value,
                    self.config_entry.data.get(SCDawnInput.SHUTTER_MAX_ANGLE_STATIC.value, "")
                )
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
            ),
            vol.Optional(
                SCDawnInput.SHUTTER_MAX_ANGLE_ENTITY.value,
                default=self.config_entry.options.get(
                    SCDawnInput.SHUTTER_MAX_ANGLE_ENTITY.value,
                    self.config_entry.data.get(SCDawnInput.SHUTTER_MAX_ANGLE_ENTITY.value, "")
                )
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number"])
            ),
            # -----------------------------------------------------------------------
            vol.Required(
                SCDawnInput.SHUTTER_LOOK_THROUGH_SECONDS_STATIC.value,
                default=self.config_entry.options.get(
                    SCDawnInput.SHUTTER_LOOK_THROUGH_SECONDS_STATIC.value,
                    self.config_entry.data.get(SCDawnInput.SHUTTER_LOOK_THROUGH_SECONDS_STATIC.value, 0)
                )
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(
                SCDawnInput.SHUTTER_LOOK_THROUGH_SECONDS_ENTITY.value,
                default=self.config_entry.options.get(
                    SCDawnInput.SHUTTER_LOOK_THROUGH_SECONDS_ENTITY.value,
                    self.config_entry.data.get(SCDawnInput.SHUTTER_LOOK_THROUGH_SECONDS_ENTITY.value, "")
                )
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number"])
            ),
            # -----------------------------------------------------------------------
            vol.Required(
                SCDawnInput.SHUTTER_OPEN_SECONDS_STATIC.value,
                default=self.config_entry.options.get(
                    SCDawnInput.SHUTTER_OPEN_SECONDS_STATIC.value,
                    self.config_entry.data.get(SCDawnInput.SHUTTER_OPEN_SECONDS_STATIC.value, 0)
                )
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(
                SCDawnInput.SHUTTER_OPEN_SECONDS_ENTITY.value,
                default=self.config_entry.options.get(
                    SCDawnInput.SHUTTER_OPEN_SECONDS_ENTITY.value,
                    self.config_entry.data.get(SCDawnInput.SHUTTER_OPEN_SECONDS_ENTITY.value, "")
                )
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number"])
            ),
            # -----------------------------------------------------------------------
            vol.Optional(
                SCDawnInput.SHUTTER_LOOK_THROUGH_ANGLE_STATIC.value,
                default=self.config_entry.options.get(
                    SCDawnInput.SHUTTER_LOOK_THROUGH_ANGLE_STATIC.value,
                    self.config_entry.data.get(SCDawnInput.SHUTTER_LOOK_THROUGH_ANGLE_STATIC.value, "")
                )
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
            ),
            vol.Optional(
                SCDawnInput.SHUTTER_LOOK_THROUGH_ANGLE_ENTITY.value,
                default=self.config_entry.options.get(
                    SCDawnInput.SHUTTER_LOOK_THROUGH_ANGLE_ENTITY.value,
                    self.config_entry.data.get(SCDawnInput.SHUTTER_LOOK_THROUGH_ANGLE_ENTITY.value, "")
                )
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number"])
            ),
            # -----------------------------------------------------------------------
            vol.Optional(
                SCDawnInput.HEIGHT_AFTER_DAWN_STATIC.value,
                default=self.config_entry.options.get(
                    SCDawnInput.HEIGHT_AFTER_DAWN_STATIC.value,
                    self.config_entry.data.get(SCDawnInput.HEIGHT_AFTER_DAWN_STATIC.value, "")
                )
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
            ),
            vol.Optional(
                SCDawnInput.HEIGHT_AFTER_DAWN_ENTITY.value,
                default=self.config_entry.options.get(
                    SCDawnInput.HEIGHT_AFTER_DAWN_ENTITY.value,
                    self.config_entry.data.get(SCDawnInput.HEIGHT_AFTER_DAWN_ENTITY.value, "")
                )
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number"])
            ),
            # -----------------------------------------------------------------------
            vol.Optional(
                SCDawnInput.ANGLE_AFTER_DAWN_STATIC.value,
                default=self.config_entry.options.get(
                    SCDawnInput.ANGLE_AFTER_DAWN_STATIC.value,
                    self.config_entry.data.get(SCDawnInput.ANGLE_AFTER_DAWN_STATIC.value, "")
                )
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
            ),
            vol.Optional(
                SCDawnInput.ANGLE_AFTER_DAWN_ENTITY.value,
                default=self.config_entry.options.get(
                    SCDawnInput.ANGLE_AFTER_DAWN_ENTITY.value,
                    self.config_entry.data.get(SCDawnInput.ANGLE_AFTER_DAWN_ENTITY.value, "")
                )
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number"])
            ),
        })

        # Zeige das Formular an
        # Wenn user_input beim letzten Mal Fehler hatte, verwende diesen Input
        # Ansonsten, wenn user_input None ist, wird add_suggested_values_to_schema
        # die Werte aus self.config_entry.options nehmen (oder self.config_entry.data, falls options leer sind)
        # und die defaults im Schema als Fallback nutzen.
        return self.async_show_form(
            step_id="init", # Oder "options", je nachdem was du lieber hast.
            data_schema=self.add_suggested_values_to_schema(
                OPTIONS_SCHEMA,
                user_input or self.config_entry.options or self.config_entry.data # Hier können wir die Quellen für suggested_values kombinieren
            ),
            errors=errors,
        )
