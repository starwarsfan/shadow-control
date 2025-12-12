"""Shadow Control number implementation."""

import logging
from typing import TYPE_CHECKING

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.restore_state import RestoreEntity

if TYPE_CHECKING:
    from . import ShadowControlManager

from .const import DOMAIN, DOMAIN_DATA_MANAGERS, SCInternal


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
    async_add_entities(entities)


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

        self._key = key
        self._manager: ShadowControlManager = hass.data[DOMAIN_DATA_MANAGERS][config_entry.entry_id]

        # Determine the external config key
        if key.endswith("_manual"):
            # e.g., 'lock_height_manual' -> 'lock_height_entity'
            self._external_config_key = key.replace("_manual", "_entity")
        else:
            # Fallback for entities without an external override option
            self._external_config_key = None

    @property
    def available(self) -> bool:
        """Return True if the entity is available (i.e., not overridden by an external entity)."""
        if not self._external_config_key:
            # Always available if there is no external override option
            return True

        # Get the currently configured entity ID from the ConfigEntry options
        external_id = self._manager.config_entry.options.get(self._external_config_key)

        # The internal entity is available ONLY IF:
        # 1. The option is not set (None).
        # 2. The option is set to the 'no selection' sentinel value ("none").

        # If external_id is NOT None and NOT "none", it is overridden, so we return False (unavailable)
        is_overridden = bool(external_id and external_id.lower() != "none")

        return not is_overridden

    # In custom_components/shadow_control/number.py (ShadowControlNumber class)

    # Helper method (can be shared or put in a mixin if you have one)
    @property
    def _is_overridden_by_external(self) -> bool:
        """Reusable check for override status."""
        if not self._external_config_key:
            return False
        external_id = self._manager.config_entry.options.get(self._external_config_key)
        return bool(external_id and external_id.lower() != "none")

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        if self._is_overridden_by_external:
            external_id = self._manager.config_entry.options.get(self._external_config_key)
            state = self.hass.states.get(external_id)

            # Safely check and convert external state
            if state and state.state not in ("unknown", "unavailable", None):
                try:
                    return float(state.state)
                except ValueError:
                    self.logger.warning("External entity '%s' state '%s' is not a valid number.", external_id, state.state)
            return None  # Fallback

        return self._value  # Use internal state if not overridden

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
        """Set new value (Blocked if overridden)."""
        if self._is_overridden_by_external:
            self.logger.warning("Attempted to set internal entity '%s' while overridden by external configuration. Ignoring.", self.entity_id)
            return

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
        if (
            last_state
            and last_state.state not in ("unknown", "unavailable", "none")
            # Check if the state can be converted to a number
            and last_state.state is not None
        ):
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

        if self._is_overridden_by_external:
            external_id = self._manager.config_entry.options.get(self._external_config_key)
            self.async_on_remove(async_track_state_change_event(self.hass, [external_id], self._async_external_state_change_listener))

        # Ensure initial state is written to HA
        self.async_write_ha_state()

    @callback
    def _async_external_state_change_listener(self, event: Event) -> None:
        """Handle external entity state changes and update internal entity state."""
        # This will trigger a read of the new state via native_value property
        self.async_write_ha_state()
