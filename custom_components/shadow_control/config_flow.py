import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import DOMAIN # Annahme: DOMAIN ist in const.py definiert

_LOGGER = logging.getLogger(__name__)

# --- STEP 1: Name, cover entity  ---
STEP_GENERAL_DATA_SCHEMA = vol.Schema({
    vol.Required("name"): selector.TextSelector(
        selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
    ),
    vol.Required("target_cover_entity_id"): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="cover")
    ),
})

# --- STEP 2: General settings (facade, cover type, ...) ---
STEP_FACADE_SETTINGS_SCHEMA = vol.Schema({
    vol.Optional("facade_azimuth"): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=359, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional("facade_offset_sun_in"): selector.NumberSelector(
        selector.NumberSelectorConfig(min=-90, max=0, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional("facade_offset_sun_out"): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=90, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional("facade_elevation_sun_min"): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=90, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional("facade_elevation_sun_max"): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=90, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional("facade_slat_width"): selector.NumberSelector(
        selector.NumberSelectorConfig(min=20, max=150, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional("facade_slat_distance"): selector.NumberSelector(
        selector.NumberSelectorConfig(min=19, max=150, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional("facade_slat_angle_offset"): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=10, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional("facade_slat_min_angle"): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=90, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional("facade_shutter_stepping_height"): selector.NumberSelector(
        selector.NumberSelectorConfig(min=1, max=20, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional("facade_shutter_stepping_angle"): selector.NumberSelector(
        selector.NumberSelectorConfig(min=1, max=20, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional("facade_shutter_type", default="0-90"): selector.SelectSelector(
        selector.SelectSelectorConfig(options=["0-90", "0-180"])
    ),
    vol.Optional("facade_neutral_pos_height"): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional("facade_neutral_pos_angle"): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional("facade_light_strip_width"): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=2000, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional("facade_shutter_height"): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=3000, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional("facade_movement_restriction_height", default="No restriction"): selector.SelectSelector(
        selector.SelectSelectorConfig(options=[
            "No restriction",
            "Only close",
            "Only open",
        ])
    ),
    vol.Optional("facade_movement_restriction_angle", default="No restriction"): selector.SelectSelector(
        selector.SelectSelectorConfig(options=[
            "No restriction",
            "Only close",
            "Only open",
        ])
    ),
})

# --- STEP 3: Dynamic settings ---
STEP_DYNAMIC_INPUTS_SCHEMA = vol.Schema({
    vol.Optional("brightness_entity_id"): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="sensor", device_class="illuminance")
    ),
    vol.Optional("brightness_dawn_entity_id"): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="sensor", device_class="illuminance")
    ),
    vol.Optional("sun_elevation_entity_id"): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="sensor")
    ),
    vol.Optional("sun_azimuth_entity_id"): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="sensor")
    ),
    vol.Optional("shutter_current_height_entity_id"): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="sensor")
    ),
    vol.Optional("shutter_current_angle_entity_id"): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="sensor")
    ),
    vol.Optional("lock_integration_entity_id"): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="input_boolean")
    ),
    vol.Optional("lock_integration_with_position_entity_id"): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="input_boolean")
    ),
    vol.Optional("lock_height_entity_id"): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional("lock_angle_entity_id"): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional("modification_tolerance_height_entity_id"): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=20, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional("modification_tolerance_angle_entity_id"): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=20, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
})

# --- STEP 4: Shadow settings ---
STEP_SHADOW_SETTINGS_SCHEMA = vol.Schema({
    vol.Optional("shadow_control_enabled_entity_id"): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="input_boolean")
    ),
    vol.Optional("shadow_brightness_threshold"): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=300000, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional("shadow_after_seconds"): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional("shadow_shutter_max_height"): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
    ),
    vol.Optional("shadow_shutter_max_angle"): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
    ),
    vol.Optional("shadow_shutter_look_through_seconds"): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional("shadow_shutter_open_seconds"): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional("shadow_shutter_look_through_angle"): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
    ),
    vol.Optional("shadow_height_after_sun"): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
    ),
    vol.Optional("shadow_angle_after_sun"): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
    ),
})

# --- STEP 5: Dawn settings ---
STEP_DAWN_SETTINGS_SCHEMA = vol.Schema({
    vol.Optional("dawn_control_enabled_entity_id"): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="input_boolean")
    ),
    vol.Optional("dawn_brightness_threshold"): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=10000, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional("dawn_after_seconds"): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional("dawn_shutter_max_height"): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
    ),
    vol.Optional("dawn_shutter_max_angle"): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
    ),
    vol.Optional("dawn_shutter_look_through_seconds"): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional("dawn_shutter_open_seconds"): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional("dawn_shutter_look_through_angle"): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
    ),
    vol.Optional("dawn_height_after_dawn"): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
    ),
    vol.Optional("dawn_angle_after_dawn"): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
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
            target_cover_entity_id = user_input.get("target_cover_entity_id")

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
            vol.Optional("facade_azimuth", default=0): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=360, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional("facade_offset_sun_in", default=0): selector.NumberSelector(
                selector.NumberSelectorConfig(min=-180, max=180, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional("facade_offset_sun_out", default=0): selector.NumberSelector(
                selector.NumberSelectorConfig(min=-180, max=180, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional("facade_elevation_sun_min", default=0): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=90, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional("facade_elevation_sun_max", default=90): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=90, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional("facade_slat_width", default=0): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional("facade_slat_distance", default=0): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional("facade_slat_angle_offset", default=0): selector.NumberSelector(
                selector.NumberSelectorConfig(min=-90, max=90, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional("facade_slat_min_angle", default=0): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=90, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional("facade_shutter_stepping_height", default=1): selector.NumberSelector(
                selector.NumberSelectorConfig(min=1, max=100, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional("facade_shutter_stepping_angle", default=1): selector.NumberSelector(
                selector.NumberSelectorConfig(min=1, max=100, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional("facade_shutter_type", default="Venetian blind"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=["Venetian blind", "Roller shutter"])
            ),
            vol.Optional("facade_neutral_pos_height", default=0): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional("facade_neutral_pos_angle", default=0): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional("facade_light_strip_width", default=0): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional("facade_shutter_height", default=0): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=1000, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional("facade_movement_restriction_height", default=100): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional("facade_movement_restriction_angle", default=100): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional("facade_update_lock_output", default=False): selector.BooleanSelector(),
            vol.Optional("cover_supports_tilt", default=False): selector.BooleanSelector(),

            # STEP_DYNAMIC_INPUTS_SCHEMA
            vol.Optional("brightness_entity_id"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="illuminance")
            ),
            vol.Optional("brightness_dawn_entity_id"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="illuminance")
            ),
            vol.Optional("sun_elevation_entity_id"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sun")
            ),
            vol.Optional("sun_azimuth_entity_id"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional("shutter_current_height_entity_id"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional("shutter_current_angle_entity_id"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional("lock_integration_entity_id"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="input_boolean")
            ),
            vol.Optional("lock_integration_with_position_entity_id"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="input_boolean")
            ),
            vol.Optional("lock_height_entity_id"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="input_boolean")
            ),
            vol.Optional("lock_angle_entity_id"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="input_boolean")
            ),
            vol.Optional("modification_tolerance_height_entity_id"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="input_number")
            ),
            vol.Optional("modification_tolerance_angle_entity_id"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="input_number")
            ),

            # STEP_SHADOW_SETTINGS_SCHEMA
            vol.Optional("shadow_control_enabled_entity_id"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="input_boolean")
            ),
            vol.Optional("shadow_brightness_threshold", default=0): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=10000, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional("shadow_after_seconds", default=0): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional("shadow_shutter_max_height", default=100): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
            ),
            vol.Optional("shadow_shutter_max_angle", default=100): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
            ),
            vol.Optional("shadow_shutter_look_through_seconds", default=0): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional("shadow_shutter_open_seconds", default=0): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional("shadow_shutter_look_through_angle", default=0): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
            ),
            vol.Optional("shadow_height_after_sun", default=100): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
            ),
            vol.Optional("shadow_angle_after_sun", default=100): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
            ),

            # STEP_DAWN_SETTINGS_SCHEMA
            vol.Optional("dawn_control_enabled_entity_id"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="input_boolean")
            ),
            vol.Optional("dawn_brightness_threshold", default=0): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=10000, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional("dawn_after_seconds", default=0): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional("dawn_shutter_max_height", default=100): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
            ),
            vol.Optional("dawn_shutter_max_angle", default=100): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
            ),
            vol.Optional("dawn_shutter_look_through_seconds", default=0): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional("dawn_shutter_open_seconds", default=0): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional("dawn_shutter_look_through_angle", default=0): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
            ),
            vol.Optional("dawn_height_after_dawn", default=100): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
            ),
            vol.Optional("dawn_angle_after_dawn", default=100): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER)
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
