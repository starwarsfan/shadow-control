"""Shadow Control time entity implementation."""

import datetime
import logging
from typing import TYPE_CHECKING

import homeassistant.helpers.entity_registry as er
from homeassistant.components.time import TimeEntity, TimeEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity

if TYPE_CHECKING:
    from . import ShadowControlManager

from .const import DOMAIN, DOMAIN_DATA_MANAGERS, INTERNAL_TO_DEFAULTS_MAP, TIME_INTERNAL_TO_EXTERNAL_MAP, SCInternal


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Set up Shadow Control time entities."""
    # Get the manager and use its logger and sanitized name
    manager: ShadowControlManager | None = hass.data.get(DOMAIN_DATA_MANAGERS, {}).get(config_entry.entry_id)
    instance_logger = manager.logger
    sanitized_instance_name = manager.sanitized_name
    config_entry_id = config_entry.entry_id

    entities = [
        ShadowControlTimeEntity(
            hass,
            config_entry,
            key=SCInternal.DAWN_OPEN_NOT_BEFORE_MANUAL.value,
            instance_name=sanitized_instance_name,
            logger=instance_logger,
            description=TimeEntityDescription(
                key=SCInternal.DAWN_OPEN_NOT_BEFORE_MANUAL.value,
                name="Dawn open not before",  # default (English) fallback if no translation found
            ),
            icon="mdi:clock-start",
        ),
        ShadowControlTimeEntity(
            hass,
            config_entry,
            key=SCInternal.DAWN_CLOSE_NOT_LATER_THAN_MANUAL.value,
            instance_name=sanitized_instance_name,
            logger=instance_logger,
            description=TimeEntityDescription(
                key=SCInternal.DAWN_CLOSE_NOT_LATER_THAN_MANUAL.value,
                name="Dawn close not later than",  # default (English) fallback if no translation found
            ),
            icon="mdi:clock-end",
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
        external_config_key = TIME_INTERNAL_TO_EXTERNAL_MAP.get(internal_key)

        is_external_entity_configured = False

        if external_config_key:
            external_entity_id = config_entry.options.get(external_config_key)

            # Check if the external config key is present and is not "none" or empty
            if external_entity_id and external_entity_id.lower() not in ("none", ""):
                is_external_entity_configured = True
                instance_logger.debug(
                    "Skipping internal time text entity '%s' because external entity '%s' is configured: %s",
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
    for internal_key in TIME_INTERNAL_TO_EXTERNAL_MAP:
        # Construct the unique ID as it appears in the entity's __init__ method
        unique_id = f"{config_entry_id}_{internal_key}"

        # If the unique ID is NOT in the set of currently required entities (i.e., external is configured)...
        if unique_id not in required_internal_unique_ids:
            # Look up in the registry using Platform.TEXT
            entity_id = registry.async_get_entity_id(Platform.TIME, DOMAIN, unique_id)

            if entity_id:
                instance_logger.debug("Removing deprecated internal time text entity: %s (unique_id: %s)", entity_id, unique_id)
                # Remove the entity from the registry.
                registry.async_remove(entity_id)

    async_add_entities(entities_to_add)


class ShadowControlTimeEntity(TimeEntity, RestoreEntity):
    """Representation of a Shadow Control time entity (HH:MM format)."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        key: str,
        description: TimeEntityDescription,
        instance_name: str,
        logger: logging.Logger,
        icon: str | None = None,
    ) -> None:
        """Initialize the time entity."""
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
        )

        if icon:
            self._attr_icon = icon

        self._state: datetime.time | None = None

    @property
    def native_value(self) -> datetime.time | None:
        """Return the current time value."""
        return self._state

    async def async_set_value(self, value: datetime.time) -> None:
        """Set the time value."""
        self._state = value
        self.async_write_ha_state()

        # Notify integration of change
        await self._notify_integration()

    async def async_added_to_hass(self) -> None:
        """Register callbacks with entity registration at HA."""
        await super().async_added_to_hass()

        # Ensure the mapping dictionary exists
        if "unique_id_map" not in self.hass.data.setdefault(DOMAIN, {}):
            self.hass.data[DOMAIN]["unique_id_map"] = {}

        # Store the mapping
        self.hass.data[DOMAIN]["unique_id_map"][self.unique_id] = self.entity_id

        # Restore last state after Home Assistant restart
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in ("unknown", "unavailable"):
            self.logger.debug("Restoring last state for %s: %s", self.name, last_state.state)
            try:
                time_parts = last_state.state.split(":")
                self._state = datetime.time(int(time_parts[0]), int(time_parts[1]))
            except (ValueError, IndexError):
                self.logger.warning(
                    "Restored state '%s' for %s has invalid format. Using default.",
                    last_state.state,
                    self.entity_id,
                )
                self._state = self._get_default_value()
        else:
            # Use default value
            self._state = self._get_default_value()

        self.async_write_ha_state()

    def _get_default_value(self) -> datetime.time | None:
        """Get the default value for this entity."""
        member = next((m for m in SCInternal if m.value == self.entity_description.key), None)
        if member and member in INTERNAL_TO_DEFAULTS_MAP:
            default = INTERNAL_TO_DEFAULTS_MAP[member]
            if default and isinstance(default, str):
                try:
                    parts = default.split(":")
                    result = datetime.time(int(parts[0]), int(parts[1]))
                    self.logger.debug("Entity %s initialized with default: %s", self.entity_id, result)
                    return result
                except (ValueError, IndexError):
                    pass

        self.logger.debug("No valid default found for entity %s", self.entity_id)
        return None

    async def _notify_integration(self) -> None:
        """Notify the integration that the value changed."""
        manager = self.hass.data[DOMAIN_DATA_MANAGERS].get(self._config_entry.entry_id)
        if manager:
            await manager.async_calculate_and_apply_cover_position(None)
