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

# =================================================================================================
# Voluptuous schemas for minimal configuration
# They are used the initial configuration of a new instance, as the instance name is the one and
# only configuration value, which is immutable. So it must be stored within `data`. All
# other options will be stored as `options`.

# Wrapper for minimal configuration, which will be stored within `data`
STEP_MINIMAL_DATA = vol.Schema({
    vol.Optional(SC_CONF_NAME, default=""): selector.TextSelector(
        selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
    ),
})

# Wrapper for minimal options, which will be used and validated within ConfigFlow and OptionFlow
STEP_MINIMAL_OPTIONS = vol.Schema({
    vol.Optional(TARGET_COVER_ENTITY_ID): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="cover", multiple=True)
    ),
    vol.Optional(SCFacadeConfig.AZIMUTH_STATIC.value, default=180): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=359, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional(SCDynamicInput.BRIGHTNESS_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["sensor", "input_number"])
    ),
    vol.Optional(SCDynamicInput.SUN_ELEVATION_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["sensor", "input_number"])
    ),
    vol.Optional(SCDynamicInput.SUN_AZIMUTH_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["sensor", "input_number"])
    ),
})

# Wrapper for minimal configuration, which is used to show initial ConfigFlow
STEP_MINIMAL_KONFIGURATION = vol.Schema(
    STEP_MINIMAL_DATA.schema |
    STEP_MINIMAL_OPTIONS.schema
)
# End of minimal configuration schema
# =================================================================================================


# =================================================================================================
# Voluptuous schemas for options
#
# --- STEP 2: 1st part of facade configuration  ---
STEP_FACADE_SETTINGS_PART1_SCHEMA = vol.Schema({
    vol.Optional(TARGET_COVER_ENTITY_ID): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="cover", multiple=True)
    ),
    vol.Optional(SCFacadeConfig.AZIMUTH_STATIC.value, default=180): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=359, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional(SCFacadeConfig.OFFSET_SUN_IN_STATIC.value, default=-90): selector.NumberSelector(
        selector.NumberSelectorConfig(min=-90, max=0, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional(SCFacadeConfig.OFFSET_SUN_OUT_STATIC.value, default=90): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=90, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional(SCFacadeConfig.ELEVATION_SUN_MIN_STATIC.value, default=0): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=90, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional(SCFacadeConfig.ELEVATION_SUN_MAX_STATIC.value, default=90): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=90, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional(DEBUG_ENABLED, default=False): selector.BooleanSelector(),
})

# --- STEP 3: 2nd part of facade configuration ---
STEP_FACADE_SETTINGS_PART2_SCHEMA = vol.Schema({
    vol.Optional(SCFacadeConfig.NEUTRAL_POS_HEIGHT_STATIC.value, default=0): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional(SCFacadeConfig.NEUTRAL_POS_ANGLE_STATIC.value, default=0): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional(SCFacadeConfig.SLAT_WIDTH_STATIC.value, default=95): selector.NumberSelector(
        selector.NumberSelectorConfig(min=20, max=150, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional(SCFacadeConfig.SLAT_DISTANCE_STATIC.value, default=67): selector.NumberSelector(
        selector.NumberSelectorConfig(min=20, max=150, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional(SCFacadeConfig.SLAT_ANGLE_OFFSET_STATIC.value, default=0): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=10, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional(SCFacadeConfig.SLAT_MIN_ANGLE_STATIC.value, default=0): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=90, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional(SCFacadeConfig.SHUTTER_STEPPING_HEIGHT_STATIC.value, default=5): selector.NumberSelector(
        selector.NumberSelectorConfig(min=1, max=20, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional(SCFacadeConfig.SHUTTER_STEPPING_ANGLE_STATIC.value, default=5): selector.NumberSelector(
        selector.NumberSelectorConfig(min=1, max=20, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional(SCFacadeConfig.LIGHT_STRIP_WIDTH_STATIC.value, default=0): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=2000, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional(SCFacadeConfig.SHUTTER_HEIGHT_STATIC.value, default=1000): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=3000, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional(SCFacadeConfig.MODIFICATION_TOLERANCE_HEIGHT_STATIC.value, default=0): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=20, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional(SCFacadeConfig.MODIFICATION_TOLERANCE_ANGLE_STATIC.value, default=0): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=20, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional(SCFacadeConfig.SHUTTER_TYPE_STATIC.value, default="mode1"): selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=[
                "mode1",
                "mode2"
            ],
            translation_key="facade_shutter_type"
        )
    ),
})

# --- STEP 4: Dynamic settings ---
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
    vol.Optional(SCDynamicInput.LOCK_HEIGHT_STATIC.value, default=0): selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=100, step=1, mode=selector.NumberSelectorMode.BOX)
    ),
    vol.Optional(SCDynamicInput.LOCK_ANGLE_STATIC.value, default=0): selector.NumberSelector(
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
    vol.Optional(SCDynamicInput.ENFORCE_POSITIONING_ENTITY.value): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="input_boolean")
    ),
})

# --- STEP 5: Shadow settings ---
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

# --- STEP 6: Dawn settings ---
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

# Combined schema for OptionsFlow
FULL_OPTIONS_SCHEMA = vol.Schema(
    STEP_FACADE_SETTINGS_PART1_SCHEMA.schema |
    STEP_FACADE_SETTINGS_PART2_SCHEMA.schema |
    STEP_DYNAMIC_INPUTS_SCHEMA.schema |
    STEP_SHADOW_SETTINGS_SCHEMA.schema |
    STEP_DAWN_SETTINGS_SCHEMA.schema
)
# End of Voluptuous schemas for options
# =================================================================================================

class ShadowControlConfigFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """
    Handle a config flow for Shadow Control.
    """

    VERSION = 2
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_migrate_entry(self, entry: config_entries.ConfigEntry):
        """
        Migrate old configuration
        """
        _LOGGER.debug(f"[{DOMAIN}] Migrating config entry from version {entry.version} to {self.VERSION}")

        new_data = entry.data.copy()
        new_options = entry.options.copy()

        # Migrate v1 to v2
        if entry.version == 1:
            old_lock_height_key = "lock_height_entity"
            old_lock_angle_key = "lock_angle_entity"

            if old_lock_height_key in new_options:
                new_options[SCDynamicInput.LOCK_HEIGHT_STATIC] = new_options.pop(old_lock_height_key)
                _LOGGER.debug(f"[{DOMAIN}] Migrated: Renamed '{old_lock_height_key}' to '{SCDynamicInput.LOCK_HEIGHT_STATIC}'.")
            else:
                # If the old key was not found, make sure it is there after migration.
                if SCDynamicInput.LOCK_HEIGHT_STATIC not in new_options:
                    new_options[SCDynamicInput.LOCK_HEIGHT_STATIC] = 0 # Default value

            if old_lock_angle_key in new_options:
                new_options[SCDynamicInput.LOCK_ANGLE_STATIC] = new_options.pop(old_lock_angle_key)
                _LOGGER.debug(f"[{DOMAIN}] Migrated: Renamed '{old_lock_angle_key}' to '{SCDynamicInput.LOCK_ANGLE_STATIC}'.")
            else:
                # If the old key was not found, make sure it is there after migration.
                if SCDynamicInput.LOCK_ANGLE_STATIC not in new_options:
                    new_options[SCDynamicInput.LOCK_ANGLE_STATIC] = 0 # Default value

            # Update data and options with migrated values
            entry.version = self.VERSION
            entry.data = new_data
            entry.options = new_options

            _LOGGER.info(f"[{DOMAIN}] Config entry successfully migrated to version {entry.version}")
            return True

        # Migrate v2 to v3
        #if entry.version == 2:
        #    old_lock_height_key = "lock_height_entity"
        #    old_lock_angle_key = "lock_angle_entity"

        _LOGGER.error(f"[{DOMAIN}] Unknown config entry version {entry.version} for migration. This should not happen.")
        return False # Migration fehlgeschlagen für unbekannte oder zu hohe Version

    def __init__(self):
        """
        Initialize the config flow.
        """
        self.config_data = {}

    async def async_step_import(self, import_config: dict[str, Any]) -> FlowResult:
        """
        Handle a flow initiated by a YAML configuration.
        """
        # Check if there is already an instance to prevent duplicated entries
        # The name is the key
        instance_name = import_config.get(SC_CONF_NAME)
        if instance_name:
            for entry in self.hass.config_entries.async_entries(DOMAIN):
                if entry.data.get(SC_CONF_NAME) == instance_name:
                    _LOGGER.warning(f"Attempted to import duplicate Shadow Control instance '{instance_name}' from YAML. Skipping.")
                    return self.async_abort(reason="already_configured")

        _LOGGER.debug(f"[ConfigFlow] Importing from YAML with config: {import_config}")

        # Convert yaml configuration into ConfigEntry, 'name' goes to 'data' section,
        # all the rest into 'options'.
        # Must be the same as in __init__.py!
        config_data_for_entry = {
            SC_CONF_NAME: import_config.pop(SC_CONF_NAME) # Remove name from import_config
        }
        # All the rest into 'options'
        options_data_for_entry = import_config

        # Optional validation against FULL_OPTIONS_SCHEMA to verify the yaml data
        try:
            validated_options = FULL_OPTIONS_SCHEMA(options_data_for_entry)
        except vol.Invalid as exc:
            _LOGGER.error(f"Validation error during YAML import for '{instance_name}': {exc}")
            return self.async_abort(reason="invalid_yaml_config")

        # Create ConfigEntry with 'title' as the name within the UI
        return self.async_create_entry(
            title=instance_name,
            data=config_data_for_entry,
            options=validated_options,
        )

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """
        Handle the initial step.
        """
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

            if not user_input.get(SCFacadeConfig.AZIMUTH_STATIC.value):
                errors[SCFacadeConfig.AZIMUTH_STATIC.value] = "facade_azimuth_static_missing"

            if not user_input.get(SCDynamicInput.BRIGHTNESS_ENTITY.value):
                errors[SCDynamicInput.BRIGHTNESS_ENTITY.value] = "dynamic_brightness_missing"

            if not user_input.get(SCDynamicInput.SUN_ELEVATION_ENTITY.value):
                errors[SCDynamicInput.SUN_ELEVATION_ENTITY.value] = "dynamic_sun_elevation_missing"

            if not user_input.get(SCDynamicInput.SUN_AZIMUTH_ENTITY.value):
                errors[SCDynamicInput.SUN_AZIMUTH_ENTITY.value] = "dynamic_sun_azimuth_missing"

            # If configuration errors found, show the config form again
            if errors:
                return self.async_show_form(
                    step_id="user",
                    data_schema=self.add_suggested_values_to_schema(STEP_MINIMAL_KONFIGURATION, form_data),
                    errors=errors,
                )

            instance_name = user_input.get(SC_CONF_NAME, "")

            # Check for already existing entries
            for entry in self.hass.config_entries.async_entries(DOMAIN):
                if entry.data.get(SC_CONF_NAME) == instance_name:
                    errors = {"base": "already_configured"}
                    return self.async_show_form(step_id="user", data_schema=STEP_MINIMAL_KONFIGURATION, errors=errors)

            # Immutable configuration data, not available within OptionsFlow
            config_data_for_entry = {
                SC_CONF_NAME: instance_name
            }

            # Create list of options, which are visible and editable within OptionsFlow
            options_data_for_entry = {
                key: value
                for key, value in user_input.items()
                if key != SC_CONF_NAME # Remove instance name
            }

            # All fine, now perform voluptuous validation
            try:
                validated_options_initial = STEP_MINIMAL_OPTIONS(options_data_for_entry)
                _LOGGER.debug(f"Creating entry with data: {config_data_for_entry} and options: {validated_options_initial}")
                return self.async_create_entry(
                    title=instance_name,
                    data=config_data_for_entry,
                    options=validated_options_initial,
                )
            except vol.Invalid as exc:
                _LOGGER.error("Validation error during final config flow step: %s", exc)
                for error in exc.errors:
                    if error.path:
                        errors[str(error.path[0])] = "invalid_input"
                    else:
                        errors["base"] = "unknown_error"

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(STEP_MINIMAL_KONFIGURATION, self.config_data),
            errors=errors,
        )

    def _clean_number_inputs(self, user_input: dict[str, Any]) -> dict[str, Any]:
        """
        Convert empty string number fields to 0 or their default.
        """
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
        """
        Create the options flow.
        """
        return ShadowControlOptionsFlowHandler()

class ShadowControlOptionsFlowHandler(config_entries.OptionsFlow):
    """
    Handle options flow for Shadow Control.
    """

    def __init__(self):
        """
        Initialize options flow.
        """
        self.options_data = None

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """
        Manage the options.
        """
        # Initialize options_data from config_entry.options, with all editable options
        self.options_data = dict(self.config_entry.options)

        _LOGGER.debug(f"Initial options_data: {self.options_data}")

        # Redirect to the first specific options step
        return await self.async_step_user(user_input)

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """
        Handle general data options.
        """
        errors: dict[str, str] = {}
        if user_input is not None:
            _LOGGER.debug(f"[OptionsFlow] Received user_input: {user_input}")

            # Manual validation of input fields to provide possible error messages
            # for each field at once and not step by step.
            if not user_input.get(TARGET_COVER_ENTITY_ID):
                errors[TARGET_COVER_ENTITY_ID] = "target_cover_entity" # Error code from within strings.json

            if not user_input.get(SCFacadeConfig.AZIMUTH_STATIC.value):
                errors[SCFacadeConfig.AZIMUTH_STATIC.value] = "facade_azimuth_static_missing"

            sun_min = user_input.get(SCFacadeConfig.ELEVATION_SUN_MIN_STATIC.value)
            sun_max = user_input.get(SCFacadeConfig.ELEVATION_SUN_MAX_STATIC.value)
            if sun_min >= sun_max:
                errors[SCFacadeConfig.ELEVATION_SUN_MIN_STATIC.value] = "minGreaterThanMax"
                errors[SCFacadeConfig.ELEVATION_SUN_MAX_STATIC.value] = "minGreaterThanMax"

            # If configuration errors found, show the config form again
            if errors:
                return self.async_show_form(
                    step_id="user",
                    data_schema=self.add_suggested_values_to_schema(STEP_FACADE_SETTINGS_PART1_SCHEMA, self.options_data),
                    errors=errors,
                )

            self.options_data.update(user_input)
            return await self.async_step_facade_settings()

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(STEP_FACADE_SETTINGS_PART1_SCHEMA, self.options_data),
            errors=errors,
        )

    async def async_step_facade_settings(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """
        Handle facade settings options.
        """
        errors: dict[str, str] = {}
        if user_input is not None:
            _LOGGER.debug(f"[OptionsFlow] Received user_input: {user_input}")

            # Manual validation of input fields to provide possible error messages
            # for each field at once and not step by step.
            slat_width = user_input.get(SCFacadeConfig.SLAT_WIDTH_STATIC.value)
            slat_distance = user_input.get(SCFacadeConfig.SLAT_DISTANCE_STATIC.value)
            if slat_width <= slat_distance:
                errors[SCFacadeConfig.SLAT_WIDTH_STATIC.value] = "slatWidthSmallerThanDistance"
                errors[SCFacadeConfig.SLAT_DISTANCE_STATIC.value] = "slatWidthSmallerThanDistance"

            # If configuration errors found, show the config form again
            if errors:
                return self.async_show_form(
                    step_id="facade_settings",
                    data_schema=self.add_suggested_values_to_schema(STEP_FACADE_SETTINGS_PART2_SCHEMA, self.options_data),
                    errors=errors,
                )

            self.options_data.update(self._clean_number_inputs(user_input))
            return await self.async_step_dynamic_inputs()

        return self.async_show_form(
            step_id="facade_settings",
            data_schema=self.add_suggested_values_to_schema(STEP_FACADE_SETTINGS_PART2_SCHEMA, self.options_data),
            errors=errors,
        )

    async def async_step_dynamic_inputs(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """
        Handle dynamic inputs options.
        """
        errors: dict[str, str] = {}
        if user_input is not None:
            _LOGGER.debug(f"[OptionsFlow] Received user_input: {user_input}")

            # Manual validation of input fields to provide possible error messages
            # for each field at once and not step by step.
            if not user_input.get(SCDynamicInput.BRIGHTNESS_ENTITY.value):
                errors[SCDynamicInput.BRIGHTNESS_ENTITY.value] = "dynamic_brightness_missing"

            if not user_input.get(SCDynamicInput.SUN_ELEVATION_ENTITY.value):
                errors[SCDynamicInput.SUN_ELEVATION_ENTITY.value] = "dynamic_sun_elevation_missing"

            if not user_input.get(SCDynamicInput.SUN_AZIMUTH_ENTITY.value):
                errors[SCDynamicInput.SUN_AZIMUTH_ENTITY.value] = "dynamic_sun_azimuth_missing"

            # If configuration errors found, show the config form again
            if errors:
                return self.async_show_form(
                    step_id="dynamic_inputs",
                    data_schema=self.add_suggested_values_to_schema(STEP_DYNAMIC_INPUTS_SCHEMA, self.options_data),
                    errors=errors,
                )

            self.options_data.update(self._clean_number_inputs(user_input))
            return await self.async_step_shadow_settings()

        return self.async_show_form(
            step_id="dynamic_inputs",
            data_schema=self.add_suggested_values_to_schema(STEP_DYNAMIC_INPUTS_SCHEMA, self.options_data),
            errors=errors,
        )

    async def async_step_shadow_settings(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """
        Handle shadow settings options.
        """
        errors: dict[str, str] = {}
        if user_input is not None:
            self.options_data.update(self._clean_number_inputs(user_input))
            return await self.async_step_dawn_settings()

        return self.async_show_form(
            step_id="shadow_settings",
            data_schema=self.add_suggested_values_to_schema(STEP_SHADOW_SETTINGS_SCHEMA, self.options_data),
            errors=errors,
        )

    async def async_step_dawn_settings(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """
        Handle dawn settings options (final options step).
        """
        errors: dict[str, str] = {}
        if user_input is not None:
            self.options_data.update(self._clean_number_inputs(user_input))
            _LOGGER.debug(f"Final options data before update: {self.options_data}")

            try:
                # Validate the entire options configuration using the combined schema
                validated_options = FULL_OPTIONS_SCHEMA(self.options_data)
                _LOGGER.debug(f"Validated options data: {validated_options}")

                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data=self.config_entry.data,
                    options=validated_options
                )

                return self.async_create_entry(title="", data=validated_options)

            except vol.Invalid as exc:
                _LOGGER.error("Validation error during options flow final step: %s", exc)
                for error in exc.errors:
                    if error.path:
                        errors[str(error.path[0])] = "invalid_input"
                    else:
                        errors["base"] = "unknown_error"

        return self.async_show_form(
            step_id="dawn_settings",
            data_schema=self.add_suggested_values_to_schema(STEP_DAWN_SETTINGS_SCHEMA, self.options_data),
            errors=errors,
        )

    def _clean_number_inputs(self, user_input: dict[str, Any]) -> dict[str, Any]:
        """
        Convert empty string number fields to 0 or their default.
        """
        cleaned_input = user_input.copy()
        for key, value in cleaned_input.items():
            if isinstance(value, str) and value == "":
                cleaned_input[key] = 0
                _LOGGER.debug(f"Cleaned empty string for key '{key}' to 0 in options flow.")
        return cleaned_input