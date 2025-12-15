"""Shadow Control number implementation."""

import logging
from typing import TYPE_CHECKING

import homeassistant.helpers.entity_registry as er
from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity

if TYPE_CHECKING:
    from . import ShadowControlManager

from .const import DOMAIN, DOMAIN_DATA_MANAGERS, NUMBER_INTERNAL_TO_EXTERNAL_MAP, SCInternal


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Set up Shadow Control number entities."""
    # Get the manager and use its logger and sanitized name
    manager: ShadowControlManager | None = hass.data.get(DOMAIN_DATA_MANAGERS, {}).get(config_entry.entry_id)
    instance_logger = manager.logger
    sanitized_instance_name = manager.sanitized_name
    config_entry_id = config_entry.entry_id

    entities = [
        ShadowControlNumber(
            hass,
            config_entry,
            key=SCInternal.LOCK_HEIGHT_MANUAL.value,
            instance_name=sanitized_instance_name,
            logger=instance_logger,
            description=NumberEntityDescription(
                key=SCInternal.LOCK_HEIGHT_MANUAL.value,
                name="Height",  # default (English) fallback if no translation found
                native_min_value=0.0,
                native_max_value=100.0,
                native_step=1.0,
                native_unit_of_measurement="%",
            ),
        ),
        ShadowControlNumber(
            hass,
            config_entry,
            key=SCInternal.LOCK_ANGLE_MANUAL.value,
            instance_name=sanitized_instance_name,
            logger=instance_logger,
            description=NumberEntityDescription(
                key=SCInternal.LOCK_ANGLE_MANUAL.value,
                name="Angle",  # default (English) fallback if no translation found
                native_min_value=0.0,
                native_max_value=100.0,
                native_step=1.0,
                native_unit_of_measurement="%",
            ),
        ),
        ShadowControlNumber(
            hass,
            config_entry,
            key=SCInternal.NEUTRAL_POS_HEIGHT_MANUAL.value,
            instance_name=sanitized_instance_name,
            logger=instance_logger,
            description=NumberEntityDescription(
                key=SCInternal.NEUTRAL_POS_HEIGHT_MANUAL.value,
                name="Neutral height",  # default (English) fallback if no translation found
                native_min_value=0.0,
                native_max_value=100.0,
                native_step=1.0,
                native_unit_of_measurement="%",
            ),
        ),
        ShadowControlNumber(
            hass,
            config_entry,
            key=SCInternal.NEUTRAL_POS_ANGLE_MANUAL.value,
            instance_name=sanitized_instance_name,
            logger=instance_logger,
            description=NumberEntityDescription(
                key=SCInternal.NEUTRAL_POS_ANGLE_MANUAL.value,
                name="Neutral angle",  # default (English) fallback if no translation found
                native_min_value=0.0,
                native_max_value=100.0,
                native_step=1.0,
                native_unit_of_measurement="%",
            ),
        ),
        ShadowControlNumber(
            hass,
            config_entry,
            key=SCInternal.SHADOW_BRIGHTNESS_THRESHOLD_MANUAL.value,
            instance_name=sanitized_instance_name,
            logger=instance_logger,
            description=NumberEntityDescription(
                key=SCInternal.SHADOW_BRIGHTNESS_THRESHOLD_MANUAL.value,
                name="Shadow brightness threshold",  # default (English) fallback if no translation found
                native_min_value=0.0,
                native_max_value=300000.0,
                native_step=10.0,
                native_unit_of_measurement="Lx",
            ),
        ),
        ShadowControlNumber(
            hass,
            config_entry,
            key=SCInternal.SHADOW_AFTER_SECONDS_MANUAL.value,
            instance_name=sanitized_instance_name,
            logger=instance_logger,
            description=NumberEntityDescription(
                key=SCInternal.SHADOW_AFTER_SECONDS_MANUAL.value,
                name="Close after x seconds",  # default (English) fallback if no translation found
                native_min_value=0.0,
                native_max_value=60.0 * 60.0 * 24.0,
                native_step=1.0,
                native_unit_of_measurement="s",
            ),
        ),
        ShadowControlNumber(
            hass,
            config_entry,
            key=SCInternal.SHADOW_SHUTTER_MAX_HEIGHT_MANUAL.value,
            instance_name=sanitized_instance_name,
            logger=instance_logger,
            description=NumberEntityDescription(
                key=SCInternal.SHADOW_SHUTTER_MAX_HEIGHT_MANUAL.value,
                name="Max shutter height",  # default (English) fallback if no translation found
                native_min_value=0.0,
                native_max_value=100.0,
                native_step=1.0,
                native_unit_of_measurement="%",
            ),
        ),
        ShadowControlNumber(
            hass,
            config_entry,
            key=SCInternal.SHADOW_SHUTTER_MAX_ANGLE_MANUAL.value,
            instance_name=sanitized_instance_name,
            logger=instance_logger,
            description=NumberEntityDescription(
                key=SCInternal.SHADOW_SHUTTER_MAX_ANGLE_MANUAL.value,
                name="Max shutter angle",  # default (English) fallback if no translation found
                native_min_value=0.0,
                native_max_value=100.0,
                native_step=1.0,
                native_unit_of_measurement="%",
            ),
        ),
        ShadowControlNumber(
            hass,
            config_entry,
            key=SCInternal.SHADOW_SHUTTER_LOOK_THROUGH_SECONDS_MANUAL.value,
            instance_name=sanitized_instance_name,
            logger=instance_logger,
            description=NumberEntityDescription(
                key=SCInternal.SHADOW_SHUTTER_LOOK_THROUGH_SECONDS_MANUAL.value,
                name="Look through after x seconds",  # default (English) fallback if no translation found
                native_min_value=0.0,
                native_max_value=60.0 * 60.0 * 24.0,
                native_step=1.0,
                native_unit_of_measurement="s",
            ),
        ),
        ShadowControlNumber(
            hass,
            config_entry,
            key=SCInternal.SHADOW_SHUTTER_OPEN_SECONDS_MANUAL.value,
            instance_name=sanitized_instance_name,
            logger=instance_logger,
            description=NumberEntityDescription(
                key=SCInternal.SHADOW_SHUTTER_OPEN_SECONDS_MANUAL.value,
                name="Open after x seconds",  # default (English) fallback if no translation found
                native_min_value=0.0,
                native_max_value=60.0 * 60.0 * 24.0,
                native_step=1.0,
                native_unit_of_measurement="s",
            ),
        ),
        ShadowControlNumber(
            hass,
            config_entry,
            key=SCInternal.SHADOW_SHUTTER_LOOK_THROUGH_ANGLE_MANUAL.value,
            instance_name=sanitized_instance_name,
            logger=instance_logger,
            description=NumberEntityDescription(
                key=SCInternal.SHADOW_SHUTTER_LOOK_THROUGH_ANGLE_MANUAL.value,
                name="Look through angle",  # default (English) fallback if no translation found
                native_min_value=0.0,
                native_max_value=100.0,
                native_step=1.0,
                native_unit_of_measurement="%",
            ),
        ),
        ShadowControlNumber(
            hass,
            config_entry,
            key=SCInternal.SHADOW_HEIGHT_AFTER_SUN_MANUAL.value,
            instance_name=sanitized_instance_name,
            logger=instance_logger,
            description=NumberEntityDescription(
                key=SCInternal.SHADOW_HEIGHT_AFTER_SUN_MANUAL.value,
                name="Height after shadow",  # default (English) fallback if no translation found
                native_min_value=0.0,
                native_max_value=100.0,
                native_step=1.0,
                native_unit_of_measurement="%",
            ),
        ),
        ShadowControlNumber(
            hass,
            config_entry,
            key=SCInternal.SHADOW_ANGLE_AFTER_SUN_MANUAL.value,
            instance_name=sanitized_instance_name,
            logger=instance_logger,
            description=NumberEntityDescription(
                key=SCInternal.SHADOW_ANGLE_AFTER_SUN_MANUAL.value,
                name="Angle after shadow",  # default (English) fallback if no translation found
                native_min_value=0.0,
                native_max_value=100.0,
                native_step=1.0,
                native_unit_of_measurement="%",
            ),
        ),
        ShadowControlNumber(
            hass,
            config_entry,
            key=SCInternal.DAWN_BRIGHTNESS_THRESHOLD_MANUAL.value,
            instance_name=sanitized_instance_name,
            logger=instance_logger,
            description=NumberEntityDescription(
                key=SCInternal.DAWN_BRIGHTNESS_THRESHOLD_MANUAL.value,
                name="Dawn brightness threshold",  # default (English) fallback if no translation found
                native_min_value=0.0,
                native_max_value=30000.0,
                native_step=10.0,
                native_unit_of_measurement="Lx",
            ),
        ),
        ShadowControlNumber(
            hass,
            config_entry,
            key=SCInternal.DAWN_AFTER_SECONDS_MANUAL.value,
            instance_name=sanitized_instance_name,
            logger=instance_logger,
            description=NumberEntityDescription(
                key=SCInternal.DAWN_AFTER_SECONDS_MANUAL.value,
                name="Close after x seconds",  # default (English) fallback if no translation found
                native_min_value=0.0,
                native_max_value=60.0 * 60.0 * 24.0,
                native_step=1.0,
                native_unit_of_measurement="s",
            ),
        ),
        ShadowControlNumber(
            hass,
            config_entry,
            key=SCInternal.DAWN_SHUTTER_MAX_HEIGHT_MANUAL.value,
            instance_name=sanitized_instance_name,
            logger=instance_logger,
            description=NumberEntityDescription(
                key=SCInternal.DAWN_SHUTTER_MAX_HEIGHT_MANUAL.value,
                name="Max shutter height",  # default (English) fallback if no translation found
                native_min_value=0.0,
                native_max_value=100.0,
                native_step=1.0,
                native_unit_of_measurement="%",
            ),
        ),
        ShadowControlNumber(
            hass,
            config_entry,
            key=SCInternal.DAWN_SHUTTER_MAX_ANGLE_MANUAL.value,
            instance_name=sanitized_instance_name,
            logger=instance_logger,
            description=NumberEntityDescription(
                key=SCInternal.DAWN_SHUTTER_MAX_ANGLE_MANUAL.value,
                name="Max shutter angle",  # default (English) fallback if no translation found
                native_min_value=0.0,
                native_max_value=100.0,
                native_step=1.0,
                native_unit_of_measurement="%",
            ),
        ),
        ShadowControlNumber(
            hass,
            config_entry,
            key=SCInternal.DAWN_SHUTTER_LOOK_THROUGH_SECONDS_MANUAL.value,
            instance_name=sanitized_instance_name,
            logger=instance_logger,
            description=NumberEntityDescription(
                key=SCInternal.DAWN_SHUTTER_LOOK_THROUGH_SECONDS_MANUAL.value,
                name="Look through after x seconds",  # default (English) fallback if no translation found
                native_min_value=0.0,
                native_max_value=60.0 * 60.0 * 24.0,
                native_step=1.0,
                native_unit_of_measurement="s",
            ),
        ),
        ShadowControlNumber(
            hass,
            config_entry,
            key=SCInternal.DAWN_SHUTTER_OPEN_SECONDS_MANUAL.value,
            instance_name=sanitized_instance_name,
            logger=instance_logger,
            description=NumberEntityDescription(
                key=SCInternal.DAWN_SHUTTER_OPEN_SECONDS_MANUAL.value,
                name="Open after x seconds",  # default (English) fallback if no translation found
                native_min_value=0.0,
                native_max_value=60.0 * 60.0 * 24.0,
                native_step=1.0,
                native_unit_of_measurement="s",
            ),
        ),
        ShadowControlNumber(
            hass,
            config_entry,
            key=SCInternal.DAWN_SHUTTER_LOOK_THROUGH_ANGLE_MANUAL.value,
            instance_name=sanitized_instance_name,
            logger=instance_logger,
            description=NumberEntityDescription(
                key=SCInternal.DAWN_SHUTTER_LOOK_THROUGH_ANGLE_MANUAL.value,
                name="Look through angle",  # default (English) fallback if no translation found
                native_min_value=0.0,
                native_max_value=100.0,
                native_step=1.0,
                native_unit_of_measurement="%",
            ),
        ),
        ShadowControlNumber(
            hass,
            config_entry,
            key=SCInternal.DAWN_HEIGHT_AFTER_DAWN_MANUAL.value,
            instance_name=sanitized_instance_name,
            logger=instance_logger,
            description=NumberEntityDescription(
                key=SCInternal.DAWN_HEIGHT_AFTER_DAWN_MANUAL.value,
                name="Height after dawn",  # default (English) fallback if no translation found
                native_min_value=0.0,
                native_max_value=100.0,
                native_step=1.0,
                native_unit_of_measurement="%",
            ),
        ),
        ShadowControlNumber(
            hass,
            config_entry,
            key=SCInternal.DAWN_ANGLE_AFTER_DAWN_MANUAL.value,
            instance_name=sanitized_instance_name,
            logger=instance_logger,
            description=NumberEntityDescription(
                key=SCInternal.DAWN_ANGLE_AFTER_DAWN_MANUAL.value,
                name="Angle after dawn",  # default (English) fallback if no translation found
                native_min_value=0.0,
                native_max_value=100.0,
                native_step=1.0,
                native_unit_of_measurement="%",
            ),
        ),
    ]

    entities_to_add = []
    required_internal_unique_ids = set()
    registry = er.async_get(hass)  # Access the Home Assistant Entity Registry

    # ----------------------------------------------------------------------
    # PART 1: Conditional Addition and Tracking
    # ----------------------------------------------------------------------
    for entity in entities:
        internal_key = entity.entity_description.key
        external_config_key = NUMBER_INTERNAL_TO_EXTERNAL_MAP.get(internal_key)

        is_external_entity_configured = False

        if external_config_key:
            external_entity_id = config_entry.options.get(external_config_key)

            # Check if the external config key is present and is not "none" or empty
            if external_entity_id and external_entity_id.lower() not in ("none", ""):
                is_external_entity_configured = True
                instance_logger.debug(
                    "Skipping internal number entity '%s' because external entity '%s' is configured: %s",
                    internal_key,
                    external_config_key,
                    external_entity_id,
                )

        if not is_external_entity_configured:
            # Only add the internal entity if NO external entity is configured
            entities_to_add.append(entity)
            # Track the unique ID of the added entity
            required_internal_unique_ids.add(entity.unique_id)

    # ----------------------------------------------------------------------
    # PART 2: Cleanup Unrequired Internal Entities from the Registry
    # ----------------------------------------------------------------------

    # Check all internal keys that have an associated external control mapping
    for internal_key in NUMBER_INTERNAL_TO_EXTERNAL_MAP:
        # Construct the unique ID as it appears in the entity's __init__ method (e.g., sc_entryid_key)
        unique_id = f"{config_entry_id}_{internal_key}"

        # If the unique ID is NOT in the set of currently required entities (i.e., external is configured)...
        if unique_id not in required_internal_unique_ids:
            # Look up in the registry using Platform.NUMBER
            entity_id = registry.async_get_entity_id(Platform.NUMBER, DOMAIN, unique_id)

            if entity_id:
                instance_logger.debug("Removing deprecated internal number entity: %s (unique_id: %s)", entity_id, unique_id)
                # Remove the entity from the registry.
                registry.async_remove(entity_id)

    async_add_entities(entities_to_add)


class ShadowControlNumber(NumberEntity, RestoreEntity):
    """Representation of a Shadow Control number entity."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        key: str,
        description: NumberEntityDescription,
        instance_name: str,
        logger: logging.Logger,
    ) -> None:
        """Initialize the number."""
        self.hass = hass
        self.logger = logger
        self.entity_description = description
        self._config_entry = config_entry
        self._attr_translation_key = description.key
        self._attr_has_entity_name = True

        self._attr_unique_id = f"{self._config_entry.entry_id}_{key}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name=instance_name,
            manufacturer="Yves Schumann",
            model="Shadow Control",
            # entry_type=DeviceInfo.EntryType.SERVICE,
        )

        # Initialize with default value
        self._value = 0.0

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return self._value

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit of measurement."""
        return self.entity_description.unit_of_measurement

    @property
    def state(self) -> str | None:
        """Return the state of the entity."""
        # Get the native (float) value
        value = self.native_value

        if value is None:
            return None

        # Crucial Step:
        # Round and cast to integer to remove decimals from the HA UI
        return str(round(value))

    async def async_set_native_value(self, value: float) -> None:
        """Set new value."""
        self._value = value
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Register callbacks with entity registration at HA."""
        await super().async_added_to_hass()

        # Ensure the mapping dictionary exists
        if "unique_id_map" not in self.hass.data.setdefault(DOMAIN, {}):
            self.hass.data[DOMAIN]["unique_id_map"] = {}

        # Store the mapping
        self.hass.data[DOMAIN]["unique_id_map"][self.unique_id] = self.entity_id

        # Restore last state after Home Assistant restart.
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in ("unknown", "unavailable", "none") and last_state.state is not None:
            try:
                self.logger.debug("Restoring last state for %s: %s", self.name, last_state.state)
                # Safely convert the state to a float
                self._value = float(last_state.state)
            except ValueError:
                # Catch any unexpected format errors and log them
                self.logger.warning(
                    "Could not restore last state for %s. Last state value '%s' is not a valid float.",
                    self.name,
                    last_state.state,
                )

        # --- IMPORTANT: WE WILL CLEAN UP THE REST OF THIS METHOD IN THE NEXT STEP ---
        # ... (If your code still contains listener logic here, we'll remove it next)
        self.async_write_ha_state()
