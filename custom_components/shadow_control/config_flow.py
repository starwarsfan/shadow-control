import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from voluptuous import Any

from .const import DOMAIN, SCFacadeConfig, \
    SCDynamicInput, TARGET_COVER_ENTITY_ID, SC_CONF_NAME, \
    SCShadowInput, SCDawnInput, DEBUG_ENABLED

_LOGGER = logging.getLogger(__name__)

# --- STEP 1: Name, cover entity  ---
STEP_GENERAL_DATA_SCHEMA = vol.Schema({
    vol.Optional(SC_CONF_NAME, default=""): selector.TextSelector(
        selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
    ),
    vol.Optional(TARGET_COVER_ENTITY_ID): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="cover")
    ),
    vol.Optional(DEBUG_ENABLED, default=False): selector.BooleanSelector(),
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
    vol.Required(SCFacadeConfig.SLAT_ANGLE_OFFSET_STATIC.value, default=0): selector.NumberSelector(
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
    vol.Optional(SCFacadeConfig.LIGHT_STRIP_WIDTH_STATIC.value, default=0): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=2000, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional(SCFacadeConfig.SHUTTER_HEIGHT_STATIC.value, default=1000): selector.NumberSelector(
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
    vol.Optional(SCDynamicInput.BRIGHTNESS_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["sensor", "input_number"])
    ),
    vol.Optional(SCDynamicInput.BRIGHTNESS_DAWN_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["sensor", "input_number"])
    ),
    vol.Optional(SCDynamicInput.SUN_ELEVATION_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["sensor", "input_number"])
    ),
    vol.Optional(SCDynamicInput.SUN_AZIMUTH_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["sensor", "input_number"])
    ),
    # vol.Optional(SCDynamicInput.SHUTTER_CURRENT_HEIGHT_ENTITY.value): selector.EntitySelector(
    #     selector.EntitySelectorConfig(domain=["sensor", "input_number"])
    # ),
    # vol.Optional(SCDynamicInput.SHUTTER_CURRENT_ANGLE_ENTITY.value): selector.EntitySelector(
    #     selector.EntitySelectorConfig(domain=["sensor", "input_number"])
    # ),
    vol.Optional(SCDynamicInput.LOCK_INTEGRATION_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="input_boolean")
    ),
    vol.Optional(SCDynamicInput.LOCK_INTEGRATION_WITH_POSITION_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="input_boolean")
    ),
    vol.Optional(SCDynamicInput.LOCK_HEIGHT_ENTITY.value, default=0): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional(SCDynamicInput.LOCK_ANGLE_ENTITY.value, default=0): selector.NumberSelector(
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
    vol.Optional(SCShadowInput.CONTROL_ENABLED_STATIC.value, default=True): selector.BooleanSelector(),
    vol.Optional(SCShadowInput.CONTROL_ENABLED_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="input_boolean")
    ),
    # -----------------------------------------------------------------------
    vol.Optional(SCShadowInput.BRIGHTNESS_THRESHOLD_STATIC.value, default=50000): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=300000, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional(SCShadowInput.BRIGHTNESS_THRESHOLD_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["sensor", "input_number"])
    ),
    # -----------------------------------------------------------------------
    vol.Optional(SCShadowInput.AFTER_SECONDS_STATIC.value, default=15): selector.NumberSelector(
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
    vol.Optional(SCShadowInput.SHUTTER_LOOK_THROUGH_SECONDS_STATIC.value, default=15): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional(SCShadowInput.SHUTTER_LOOK_THROUGH_SECONDS_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["sensor", "input_number"])
    ),
    # -----------------------------------------------------------------------
    vol.Optional(SCShadowInput.SHUTTER_OPEN_SECONDS_STATIC.value, default=15): selector.NumberSelector(
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
    vol.Optional(SCDawnInput.CONTROL_ENABLED_STATIC.value, default=True): selector.BooleanSelector(),
    vol.Optional(SCDawnInput.CONTROL_ENABLED_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="input_boolean")
    ),
    # -----------------------------------------------------------------------
    vol.Optional(SCDawnInput.BRIGHTNESS_THRESHOLD_STATIC.value, default=500): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=10000, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional(SCDawnInput.BRIGHTNESS_THRESHOLD_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["sensor", "input_number"])
    ),
    # -----------------------------------------------------------------------
    vol.Optional(SCDawnInput.AFTER_SECONDS_STATIC.value, default=15): selector.NumberSelector(
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
    vol.Optional(SCDawnInput.SHUTTER_LOOK_THROUGH_SECONDS_STATIC.value, default=15): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=7200, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional(SCDawnInput.SHUTTER_LOOK_THROUGH_SECONDS_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["sensor", "input_number"])
    ),
    # -----------------------------------------------------------------------
    vol.Optional(SCDawnInput.SHUTTER_OPEN_SECONDS_STATIC.value, default=15): selector.NumberSelector(
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

# Combined schema for final validation and options flow
FULL_CONFIG_SCHEMA = vol.Schema( # <--- Korrektur hier
    STEP_GENERAL_DATA_SCHEMA.schema |
    STEP_FACADE_SETTINGS_SCHEMA.schema |
    STEP_DYNAMIC_INPUTS_SCHEMA.schema |
    STEP_SHADOW_SETTINGS_SCHEMA.schema |
    STEP_DAWN_SETTINGS_SCHEMA.schema
)

class ShadowControlConfigFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Shadow Control."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self):
        """Initialize the config flow."""
        self.config_data = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        # Initialize data for the form, using user_input if available, else empty for initial display
        # This ensures fields are pre-filled if the form is redisplayed due to errors
        form_data = user_input if user_input is not None else {}

        if user_input is not None:
            _LOGGER.debug(f"[ConfigFlow] Received user_input: {user_input}")

            # Manual validation of input fields to provide possible error messages
            # for each field at once and not step by step.
            if not user_input.get(SC_CONF_NAME):
                errors[SC_CONF_NAME] = "name" # Error code from within strings.json

            if not user_input.get(TARGET_COVER_ENTITY_ID):
                errors[TARGET_COVER_ENTITY_ID] = "target_cover_entity" # Error code from within strings.json

            # If configuration errors found, show the config form again
            if errors:
                return self.async_show_form(
                    step_id="user",
                    data_schema=self.add_suggested_values_to_schema(STEP_GENERAL_DATA_SCHEMA, form_data),
                    errors=errors,
                )

            # All fine, now perform voluptuous validation
            try:
                validated_user_input = STEP_GENERAL_DATA_SCHEMA(user_input)

                # Additional entity validation
                if validated_user_input.get(TARGET_COVER_ENTITY_ID): # Nur prüfen, wenn ein Wert vorhanden ist
                    target_entity = self.hass.states.get(validated_user_input[TARGET_COVER_ENTITY_ID])
                    if not target_entity or target_entity.domain != "cover":
                        errors[TARGET_COVER_ENTITY_ID] = "invalid_entity"
                        return self.async_show_form(step_id="user", data_schema=self.add_suggested_values_to_schema(STEP_GENERAL_DATA_SCHEMA, form_data), errors=errors)


                self.config_data.update(validated_user_input)
                _LOGGER.debug(f"[ConfigFlow] After general_settings, config_data: {self.config_data}")

                return await self.async_step_facade_settings()

            except vol.Invalid as exc:
                _LOGGER.error("Validation error during user step (voluptuous): %s", exc)
                for error in exc.errors:
                    field_key = str(error.path[0]) if error.path else "base"
                    errors[field_key] = "general_input_error"

                    # Catched voluptuous error, show the input form again
                return self.async_show_form(
                    step_id="user",
                    data_schema=self.add_suggested_values_to_schema(STEP_GENERAL_DATA_SCHEMA, form_data), # <--- Hier 'form_data' verwenden
                    errors=errors,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_GENERAL_DATA_SCHEMA, # Hier kein suggested_values, da noch keine Eingaben
            errors=errors, # Bleibt leer beim initialen Aufruf
        )

    async def async_step_facade_settings(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the facade settings step."""
        errors: dict[str, str] = {}
        form_data = user_input if user_input is not None else {}

        if user_input is not None:
            _LOGGER.debug(f"[ConfigFlow] Received user_input: {user_input}")

            sun_min = user_input.get(SCFacadeConfig.ELEVATION_SUN_MIN_STATIC.value)
            sun_max = user_input.get(SCFacadeConfig.ELEVATION_SUN_MAX_STATIC.value)
            if sun_min >= sun_max:
                errors[SCFacadeConfig.ELEVATION_SUN_MIN_STATIC.value] = "minGreaterThanMax"
                errors[SCFacadeConfig.ELEVATION_SUN_MAX_STATIC.value] = "minGreaterThanMax"

            slat_width = user_input.get(SCFacadeConfig.SLAT_WIDTH_STATIC.value)
            slat_distance = user_input.get(SCFacadeConfig.SLAT_DISTANCE_STATIC.value)
            if slat_width <= slat_distance:
                errors[SCFacadeConfig.SLAT_WIDTH_STATIC.value] = "slatWidthSmallerThanDistance"
                errors[SCFacadeConfig.SLAT_DISTANCE_STATIC.value] = "slatWidthSmallerThanDistance"

            # If configuration errors found, show the config form again
            if errors:
                return self.async_show_form(
                    step_id="facade_settings",
                    data_schema=self.add_suggested_values_to_schema(STEP_FACADE_SETTINGS_SCHEMA, form_data),
                    errors=errors,
                )

            try:
                validated_user_input = STEP_FACADE_SETTINGS_SCHEMA(user_input)
                self.config_data.update(self._clean_number_inputs(validated_user_input))
                _LOGGER.debug(f"[ConfigFlow] After facade_settings, config_data: {self.config_data}")
                return await self.async_step_dynamic_inputs()

            except vol.Invalid as exc:
                # Catch validation errors and map them to the corresponding fields
                _LOGGER.error("Validation error during user step: %s", exc)
                for error in exc.errors:
                    if error.path:
                        errors[str(error.path[0])] = "invalid_input"
                    else:
                        # Commons errors without mapping to a specific field
                        errors["base"] = "unknown_error"

        return self.async_show_form(
            step_id="facade_settings",
            data_schema=self.add_suggested_values_to_schema(STEP_FACADE_SETTINGS_SCHEMA, self.config_data),
            errors=errors,
        )

    async def async_step_dynamic_inputs(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the dynamic inputs step."""
        errors: dict[str, str] = {}
        form_data = user_input if user_input is not None else {}

        if user_input is not None:
            _LOGGER.debug(f"[ConfigFlow] Received user_input: {user_input}")

            if not user_input.get(SCDynamicInput.BRIGHTNESS_ENTITY.value):
                errors[SCDynamicInput.BRIGHTNESS_ENTITY.value] = "dynamic_brightness_missing"

            if not user_input.get(SCDynamicInput.SUN_ELEVATION_ENTITY.value):
                errors[SCDynamicInput.SUN_ELEVATION_ENTITY.value] = "dynamic_sun_elevation_missing"

            if not user_input.get(SCDynamicInput.SUN_AZIMUTH_ENTITY.value):
                errors[SCDynamicInput.SUN_AZIMUTH_ENTITY.value] = "dynamic_sun_azimuth_missing"

            if errors:
                return self.async_show_form(
                    step_id="dynamic_inputs",
                    data_schema=self.add_suggested_values_to_schema(STEP_DYNAMIC_INPUTS_SCHEMA, form_data),
                    errors=errors,
                )

            try:
                validated_user_input = STEP_DYNAMIC_INPUTS_SCHEMA(user_input)
                self.config_data.update(self._clean_number_inputs(validated_user_input))
                _LOGGER.debug(f"[ConfigFlow] After dynamic_inputs, config_data: {self.config_data}")
                return await self.async_step_shadow_settings()

            except vol.Invalid as exc:
                _LOGGER.error("Validation error during user step (voluptuous): %s", exc)
                for error in exc.errors:
                    field_key = str(error.path[0]) if error.path else "base"
                    errors[field_key] = "general_input_error"

                # Catched voluptuous error, show the input form again
                return self.async_show_form(
                    step_id="dynamic_inputs",
                    data_schema=self.add_suggested_values_to_schema(STEP_DYNAMIC_INPUTS_SCHEMA, form_data),
                    errors=errors,
                )

        return self.async_show_form(
            step_id="dynamic_inputs",
            data_schema=self.add_suggested_values_to_schema(STEP_DYNAMIC_INPUTS_SCHEMA, self.config_data),
            errors=errors,
        )

    async def async_step_shadow_settings(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the shadow settings step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self.config_data.update(self._clean_number_inputs(user_input))
            _LOGGER.debug(f"[ConfigFlow] After shadow_settings, config_data: {self.config_data}") # NEU: Debug-Log
            return await self.async_step_dawn_settings()

        return self.async_show_form(
            step_id="shadow_settings",
            data_schema=self.add_suggested_values_to_schema(STEP_SHADOW_SETTINGS_SCHEMA, self.config_data),
            errors=errors,
        )

    async def async_step_dawn_settings(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the dawn settings step (final step for configuration)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self.config_data.update(self._clean_number_inputs(user_input))
            _LOGGER.debug(f"[ConfigFlow] After dawn_settings, config_data: {self.config_data}") # NEU: Debug-Log
            _LOGGER.debug(f"Final config data before creation: {self.config_data}")

            try:
                # Validate the entire configuration using the combined schema
                validated_data = FULL_CONFIG_SCHEMA(self.config_data)
                _LOGGER.debug(f"Validated config data: {validated_data}")
                return self.async_create_entry(
                    title=self.config_data[SC_CONF_NAME],
                    data={},  # Configuration data is stored as options now
                    options=validated_data, # Store the full config as options
                )
            except vol.Invalid as exc:
                _LOGGER.error("Validation error during final config flow step: %s", exc)
                for error in exc.errors:
                    if error.path:
                        errors[str(error.path[0])] = "invalid_input"
                    else:
                        errors["base"] = "unknown_error"

        return self.async_show_form(
            step_id="dawn_settings",
            data_schema=self.add_suggested_values_to_schema(STEP_DAWN_SETTINGS_SCHEMA, self.config_data),
            errors=errors,
        )

    def _clean_number_inputs(self, user_input: dict[str, Any]) -> dict[str, Any]:
        """Convert empty string number fields to 0 or their default."""
        cleaned_input = user_input.copy()
        for key, value in cleaned_input.items():
            if isinstance(value, str) and value == "":
                # For selectors, the default should come from the schema itself
                # or be explicitly handled. Setting to 0 here for number fields.
                cleaned_input[key] = 0
                _LOGGER.debug(f"Cleaned empty string for key '{key}' to 0.")
        return cleaned_input

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return ShadowControlOptionsFlowHandler(config_entry)

class ShadowControlOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Shadow Control."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        self.options_data = dict(config_entry.options) # Start with current options

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage the options."""
        # Redirect to the first specific options step
        return await self.async_step_general_data_options()

    async def async_step_general_data_options(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle general data options."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self.options_data.update(user_input)
            return await self.async_step_facade_settings_options()

        return self.async_show_form(
            step_id="general_data_options",
            data_schema=self.add_suggested_values_to_schema(STEP_GENERAL_DATA_SCHEMA, self.options_data),
            errors=errors,
        )

    async def async_step_facade_settings_options(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle facade settings options."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self.options_data.update(self._clean_number_inputs(user_input))
            return await self.async_step_dynamic_inputs_options()

        return self.async_show_form(
            step_id="facade_settings_options",
            data_schema=self.add_suggested_values_to_schema(STEP_FACADE_SETTINGS_SCHEMA, self.options_data),
            errors=errors,
        )

    async def async_step_dynamic_inputs_options(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle dynamic inputs options."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self.options_data.update(self._clean_number_inputs(user_input))
            return await self.async_step_shadow_settings_options()

        return self.async_show_form(
            step_id="dynamic_inputs_options",
            data_schema=self.add_suggested_values_to_schema(STEP_DYNAMIC_INPUTS_SCHEMA, self.options_data),
            errors=errors,
        )

    async def async_step_shadow_settings_options(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle shadow settings options."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self.options_data.update(self._clean_number_inputs(user_input))
            return await self.async_step_dawn_settings_options()

        return self.async_show_form(
            step_id="shadow_settings_options",
            data_schema=self.add_suggested_values_to_schema(STEP_SHADOW_SETTINGS_SCHEMA, self.options_data),
            errors=errors,
        )

    async def async_step_dawn_settings_options(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle dawn settings options (final options step)."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self.options_data.update(self._clean_number_inputs(user_input))
            _LOGGER.debug(f"Final options data before update: {self.options_data}")

            try:
                # Validate the entire options configuration using the combined schema
                validated_options = FULL_CONFIG_SCHEMA(self.options_data)
                _LOGGER.debug(f"Validated options data: {validated_options}")

                # In einem Optionsfluss wird 'async_create_entry' mit den aktualisierten Daten
                # verwendet, um die Optionen des *bestehenden* Eintrags zu speichern und
                # den Home Assistant Kern zu informieren, dass eine Aktualisierung erfolgt ist.
                # Home Assistant wird den Eintrag dann bei Bedarf automatisch neu laden.
                # Der manuelle Aufruf von async_update_entry und async_reload ist nicht nötig.
                return self.async_create_entry(title="", data=validated_options)

            except vol.Invalid as exc:
                _LOGGER.error("Validation error during options flow final step: %s", exc)
                for error in exc.errors:
                    if error.path:
                        errors[str(error.path[0])] = "invalid_input"
                    else:
                        errors["base"] = "unknown_error"

        return self.async_show_form(
            step_id="dawn_settings_options",
            data_schema=self.add_suggested_values_to_schema(STEP_DAWN_SETTINGS_SCHEMA, self.options_data),
            errors=errors,
        )

    def _clean_number_inputs(self, user_input: dict[str, Any]) -> dict[str, Any]:
        """Convert empty string number fields to 0 or their default."""
        cleaned_input = user_input.copy()
        for key, value in cleaned_input.items():
            if isinstance(value, str) and value == "":
                cleaned_input[key] = 0
                _LOGGER.debug(f"Cleaned empty string for key '{key}' to 0 in options flow.")
        return cleaned_input