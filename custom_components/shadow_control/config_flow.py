import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import DOMAIN, SCFacadeConfig, \
    SCDynamicInput, TARGET_COVER_ENTITY, SC_CONF_NAME, \
    SCShadowInput, SCDawnInput  # Annahme: DOMAIN ist in const.py definiert

_LOGGER = logging.getLogger(__name__)

# --- STEP 1: Name, cover entity  ---
STEP_GENERAL_DATA_SCHEMA = vol.Schema({
    vol.Required(SC_CONF_NAME): selector.TextSelector(
        selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
    ),
    vol.Required(TARGET_COVER_ENTITY): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="cover")
    ),
})

# --- STEP 2: General settings (facade, cover type, ...) ---
STEP_FACADE_SETTINGS_SCHEMA = vol.Schema({
    vol.Required(SCFacadeConfig.AZIMUTH_STATIC.value): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=359, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Required(SCFacadeConfig.OFFSET_SUN_IN_STATIC.value): selector.NumberSelector(
        selector.NumberSelectorConfig(min=-90, max=0, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Required(SCFacadeConfig.OFFSET_SUN_OUT_STATIC.value): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=90, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Required(SCFacadeConfig.ELEVATION_SUN_MIN_STATIC.value): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=90, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Required(SCFacadeConfig.ELEVATION_SUN_MAX_STATIC.value): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=90, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Required(SCFacadeConfig.SLAT_WIDTH_STATIC.value): selector.NumberSelector(
        selector.NumberSelectorConfig(min=20, max=150, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Required(SCFacadeConfig.SLAT_DISTANCE_STATIC.value): selector.NumberSelector(
        selector.NumberSelectorConfig(min=19, max=150, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Required(SCFacadeConfig.SLAT_ANGLE_OFFSET_STATIC.value): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=10, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Required(SCFacadeConfig.SLAT_MIN_ANGLE_STATIC.value): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=90, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Required(SCFacadeConfig.SHUTTER_STEPPING_HEIGHT_STATIC.value): selector.NumberSelector(
        selector.NumberSelectorConfig(min=1, max=20, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Required(SCFacadeConfig.SHUTTER_STEPPING_ANGLE_STATIC.value): selector.NumberSelector(
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
    vol.Optional(SCFacadeConfig.NEUTRAL_POS_HEIGHT_STATIC.value): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional(SCFacadeConfig.NEUTRAL_POS_ANGLE_STATIC.value): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional(SCFacadeConfig.MODIFICATION_TOLERANCE_HEIGHT_STATIC.value): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=20, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional(SCFacadeConfig.MODIFICATION_TOLERANCE_ANGLE_STATIC.value): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=20, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
})

# --- STEP 3: Dynamic settings ---
STEP_DYNAMIC_INPUTS_SCHEMA = vol.Schema({
    vol.Required(SCDynamicInput.BRIGHTNESS_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="sensor", device_class="illuminance")
    ),
    vol.Optional(SCDynamicInput.BRIGHTNESS_DAWN_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="sensor", device_class="illuminance")
    ),
    vol.Required(SCDynamicInput.SUN_ELEVATION_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="sensor")
    ),
    vol.Required(SCDynamicInput.SUN_AZIMUTH_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="sensor")
    ),
    vol.Optional(SCDynamicInput.SHUTTER_CURRENT_HEIGHT_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="sensor")
    ),
    vol.Optional(SCDynamicInput.SHUTTER_CURRENT_ANGLE_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="sensor")
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
    #
    vol.Required(SCShadowInput.BRIGHTNESS_THRESHOLD_STATIC.value): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=300000, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional(SCShadowInput.BRIGHTNESS_THRESHOLD_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="sensor")
    ),
    #
    vol.Required(SCShadowInput.AFTER_SECONDS_STATIC.value): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional(SCShadowInput.AFTER_SECONDS_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="sensor")
    ),
    #
    vol.Optional(SCShadowInput.SHUTTER_MAX_HEIGHT_STATIC.value): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
    ),
    vol.Optional(SCShadowInput.SHUTTER_MAX_HEIGHT_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="sensor")
    ),
    #
    vol.Optional(SCShadowInput.SHUTTER_MAX_ANGLE_STATIC.value): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
    ),
    vol.Optional(SCShadowInput.SHUTTER_MAX_ANGLE_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="sensor")
    ),
    #
    vol.Required(SCShadowInput.SHUTTER_LOOK_THROUGH_SECONDS_STATIC.value): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional(SCShadowInput.SHUTTER_LOOK_THROUGH_SECONDS_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="sensor")
    ),
    #
    vol.Required(SCShadowInput.SHUTTER_OPEN_SECONDS_STATIC.value): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional(SCShadowInput.SHUTTER_OPEN_SECONDS_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="sensor")
    ),
    #
    vol.Optional(SCShadowInput.SHUTTER_LOOK_THROUGH_ANGLE_STATIC.value): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
    ),
    vol.Optional(SCShadowInput.SHUTTER_LOOK_THROUGH_ANGLE_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="sensor")
    ),
    #
    vol.Optional(SCShadowInput.HEIGHT_AFTER_SUN_STATIC.value): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
    ),
    vol.Optional(SCShadowInput.HEIGHT_AFTER_SUN_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="sensor")
    ),
    #
    vol.Optional(SCShadowInput.ANGLE_AFTER_SUN_STATIC.value): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
    ),
    vol.Optional(SCShadowInput.ANGLE_AFTER_SUN_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="sensor")
    ),
})

# --- STEP 5: Dawn settings ---
STEP_DAWN_SETTINGS_SCHEMA = vol.Schema({
    vol.Required(SCDawnInput.CONTROL_ENABLED_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="input_boolean")
    ),
    #
    vol.Required(SCDawnInput.BRIGHTNESS_THRESHOLD_STATIC.value): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=10000, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional(SCDawnInput.BRIGHTNESS_THRESHOLD_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="sensor")
    ),
    #
    vol.Required(SCDawnInput.AFTER_SECONDS_STATIC.value): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional(SCDawnInput.AFTER_SECONDS_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="sensor")
    ),
    #
    vol.Optional(SCDawnInput.SHUTTER_MAX_HEIGHT_STATIC.value): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
    ),
    vol.Optional(SCDawnInput.SHUTTER_MAX_HEIGHT_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="sensor")
    ),
    #
    vol.Optional(SCDawnInput.SHUTTER_MAX_ANGLE_STATIC.value): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
    ),
    vol.Optional(SCDawnInput.SHUTTER_MAX_ANGLE_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="sensor")
    ),
    #
    vol.Required(SCDawnInput.SHUTTER_LOOK_THROUGH_SECONDS_STATIC.value): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional(SCDawnInput.SHUTTER_LOOK_THROUGH_SECONDS_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="sensor")
    ),
    #
    vol.Required(SCDawnInput.SHUTTER_OPEN_SECONDS_STATIC.value): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional(SCDawnInput.SHUTTER_OPEN_SECONDS_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="sensor")
    ),
    #
    vol.Optional(SCDawnInput.SHUTTER_LOOK_THROUGH_ANGLE_STATIC.value): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
    ),
    vol.Optional(SCDawnInput.SHUTTER_LOOK_THROUGH_ANGLE_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="sensor")
    ),
    #
    vol.Optional(SCDawnInput.HEIGHT_AFTER_STATIC.value): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
    ),
    vol.Optional(SCDawnInput.HEIGHT_AFTER_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="sensor")
    ),
    #
    vol.Optional(SCDawnInput.ANGLE_AFTER_STATIC.value): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
    ),
    vol.Optional(SCDawnInput.ANGLE_AFTER_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="sensor")
    ),
})


class ShadowControlConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Shadow Control."""

    VERSION = 1
    DOMAIN = DOMAIN

    # Used to store data in between the config flow steps
    _data = {}

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial setup step (Step 1: General Settings - Name, Target Cover)."""
        errors = {}

        if user_input is not None:
            target_cover_entity = user_input.get("target_cover_entity")

            # Use unique id to prevent multiple usage of the same cover
            await self.async_set_unique_id(target_cover_entity)
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

        if user_input is not None:
            self._data.update(user_input)

            # Next ConfigFlow page
            return await self.async_step_dawn_settings()

        # Show form of 4th config step
        return self.async_show_form(
            step_id="shadow_settings",
            data_schema=self.add_suggested_values_to_schema(
                STEP_SHADOW_SETTINGS_SCHEMA,
                self._data # Vorausfüllen mit bereits bekannten Werten
            ),
            errors=errors,
        )

    async def async_step_dawn_settings(self, user_input=None) -> FlowResult:
        """Handle dawn control settings (Step 5 - Final)."""
        errors = {}

        if user_input is not None:
            self._data.update(user_input)

            # All data collected, create config entry
            return self.async_create_entry(
                title=self._data.get("name", DOMAIN),
                data=self._data
            )

        # Show form of 5th config step
        return self.async_show_form(
            step_id="dawn_settings",
            data_schema=self.add_suggested_values_to_schema(
                STEP_DAWN_SETTINGS_SCHEMA,
                self._data # Vorausfüllen mit bereits bekannten Werten
            ),
            errors=errors,
        )

    # --- OPTIONS FLOW (Modification of existing configuration) ---
    # Used if "Options" button at the integration card was clicked.
    async def async_step_options(self, user_input=None) -> FlowResult:
        """Handle the options flow for editing an existing entry."""
        errors = {}

        # Combined schema for options flow
        # Should contain all fields which the user should be able to modify.
        OPTIONS_COMBINED_SCHEMA = vol.Schema({
            # Without 'name' and '' because these fields define the unique id.

            # STEP_FACADE_SETTINGS_SCHEMA
            vol.Required(SCFacadeConfig.AZIMUTH_STATIC.value): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=359, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Required(SCFacadeConfig.OFFSET_SUN_IN_STATIC.value): selector.NumberSelector(
                selector.NumberSelectorConfig(min=-90, max=0, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Required(SCFacadeConfig.OFFSET_SUN_OUT_STATIC.value): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=90, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Required(SCFacadeConfig.ELEVATION_SUN_MIN_STATIC.value): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=90, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Required(SCFacadeConfig.ELEVATION_SUN_MAX_STATIC.value): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=90, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Required(SCFacadeConfig.SLAT_WIDTH_STATIC.value): selector.NumberSelector(
                selector.NumberSelectorConfig(min=20, max=150, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Required(SCFacadeConfig.SLAT_DISTANCE_STATIC.value): selector.NumberSelector(
                selector.NumberSelectorConfig(min=19, max=150, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Required(SCFacadeConfig.SLAT_ANGLE_OFFSET_STATIC.value): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=10, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Required(SCFacadeConfig.SLAT_MIN_ANGLE_STATIC.value): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=90, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Required(SCFacadeConfig.SHUTTER_STEPPING_HEIGHT_STATIC.value): selector.NumberSelector(
                selector.NumberSelectorConfig(min=1, max=20, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Required(SCFacadeConfig.SHUTTER_STEPPING_ANGLE_STATIC.value): selector.NumberSelector(
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
            vol.Optional(SCFacadeConfig.NEUTRAL_POS_HEIGHT_STATIC.value): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(SCFacadeConfig.NEUTRAL_POS_ANGLE_STATIC.value): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(SCFacadeConfig.MODIFICATION_TOLERANCE_HEIGHT_STATIC.value): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=20, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(SCFacadeConfig.MODIFICATION_TOLERANCE_ANGLE_STATIC.value): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=20, step=1, mode=selector.NumberSelectorMode.BOX)
            ),

            # STEP_DYNAMIC_INPUTS_SCHEMA
            vol.Required(SCDynamicInput.BRIGHTNESS_ENTITY.value): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="illuminance")
            ),
            vol.Optional(SCDynamicInput.BRIGHTNESS_DAWN_ENTITY.value): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="illuminance")
            ),
            vol.Required(SCDynamicInput.SUN_ELEVATION_ENTITY.value): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Required(SCDynamicInput.SUN_AZIMUTH_ENTITY.value): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(SCDynamicInput.SHUTTER_CURRENT_HEIGHT_ENTITY.value): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(SCDynamicInput.SHUTTER_CURRENT_ANGLE_ENTITY.value): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
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

            # ===============================================================
            # STEP_SHADOW_SETTINGS_SCHEMA
            #
            vol.Required(SCShadowInput.CONTROL_ENABLED_ENTITY.value): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="input_boolean")
            ),
            #
            vol.Required(SCShadowInput.BRIGHTNESS_THRESHOLD_STATIC.value): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=300000, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(SCShadowInput.BRIGHTNESS_THRESHOLD_ENTITY.value): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            #
            vol.Required(SCShadowInput.AFTER_SECONDS_STATIC.value): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(SCShadowInput.AFTER_SECONDS_ENTITY.value): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            #
            vol.Optional(SCShadowInput.SHUTTER_MAX_HEIGHT_STATIC.value): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
            ),
            vol.Optional(SCShadowInput.SHUTTER_MAX_HEIGHT_ENTITY.value): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            #
            vol.Optional(SCShadowInput.SHUTTER_MAX_ANGLE_STATIC.value): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
            ),
            vol.Optional(SCShadowInput.SHUTTER_MAX_ANGLE_ENTITY.value): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            #
            vol.Required(SCShadowInput.SHUTTER_LOOK_THROUGH_SECONDS_STATIC.value): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(SCShadowInput.SHUTTER_LOOK_THROUGH_SECONDS_ENTITY.value): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            #
            vol.Required(SCShadowInput.SHUTTER_OPEN_SECONDS_STATIC.value): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(SCShadowInput.SHUTTER_OPEN_SECONDS_ENTITY.value): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            #
            vol.Optional(SCShadowInput.SHUTTER_LOOK_THROUGH_ANGLE_STATIC.value): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
            ),
            vol.Optional(SCShadowInput.SHUTTER_LOOK_THROUGH_ANGLE_ENTITY.value): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            #
            vol.Optional(SCShadowInput.HEIGHT_AFTER_SUN_STATIC.value): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
            ),
            vol.Optional(SCShadowInput.HEIGHT_AFTER_SUN_ENTITY.value): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            #
            vol.Optional(SCShadowInput.ANGLE_AFTER_SUN_STATIC.value): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
            ),
            vol.Optional(SCShadowInput.ANGLE_AFTER_SUN_ENTITY.value): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),

            # ===============================================================
            # STEP_DAWN_SETTINGS_SCHEMA
            vol.Required(SCDawnInput.CONTROL_ENABLED_ENTITY.value): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="input_boolean")
            ),
            #
            vol.Required(SCDawnInput.BRIGHTNESS_THRESHOLD_STATIC.value): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=10000, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(SCDawnInput.BRIGHTNESS_THRESHOLD_ENTITY.value): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            #
            vol.Required(SCDawnInput.AFTER_SECONDS_STATIC.value): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(SCDawnInput.AFTER_SECONDS_ENTITY.value): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            #
            vol.Optional(SCDawnInput.SHUTTER_MAX_HEIGHT_STATIC.value): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
            ),
            vol.Optional(SCDawnInput.SHUTTER_MAX_HEIGHT_ENTITY.value): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            #
            vol.Optional(SCDawnInput.SHUTTER_MAX_ANGLE_STATIC.value): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
            ),
            vol.Optional(SCDawnInput.SHUTTER_MAX_ANGLE_ENTITY.value): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            #
            vol.Required(SCDawnInput.SHUTTER_LOOK_THROUGH_SECONDS_STATIC.value): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(SCDawnInput.SHUTTER_LOOK_THROUGH_SECONDS_ENTITY.value): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            #
            vol.Required(SCDawnInput.SHUTTER_OPEN_SECONDS_STATIC.value): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(SCDawnInput.SHUTTER_OPEN_SECONDS_ENTITY.value): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            #
            vol.Optional(SCDawnInput.SHUTTER_LOOK_THROUGH_ANGLE_STATIC.value): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
            ),
            vol.Optional(SCDawnInput.SHUTTER_LOOK_THROUGH_ANGLE_ENTITY.value): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            #
            vol.Optional(SCDawnInput.HEIGHT_AFTER_STATIC.value): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
            ),
            vol.Optional(SCDawnInput.HEIGHT_AFTER_ENTITY.value): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            #
            vol.Optional(SCDawnInput.ANGLE_AFTER_STATIC.value): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
            ),
            vol.Optional(SCDawnInput.ANGLE_AFTER_ENTITY.value): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
        })

        if user_input is None:
            # Fill options form with current values of ConfigEntry.
            # Options have precedence before initial data.
            current_options = {**self.config_entry.data, **self.config_entry.options}

            # Use default values at optional fields
            for key, schema_item in OPTIONS_COMBINED_SCHEMA.schema.items():
                if isinstance(schema_item, vol.Optional) and key not in current_options:
                    current_options[key] = schema_item.default

            return self.async_show_form(
                step_id="options",
                data_schema=self.add_suggested_values_to_schema(
                    OPTIONS_COMBINED_SCHEMA, current_options
                ),
                errors=errors,
            )

        if errors:
            return self.async_show_form(
                step_id="options",
                data_schema=self.add_suggested_values_to_schema(
                    OPTIONS_COMBINED_SCHEMA, user_input
                ),
                errors=errors,
            )

        # Save updated options within ConfigEntry
        return self.async_create_entry(title="", data=user_input)
