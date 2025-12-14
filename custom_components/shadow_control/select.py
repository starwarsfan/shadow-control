"""Shadow Control select implementation."""

import logging
from typing import TYPE_CHECKING

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity

if TYPE_CHECKING:
    from . import ShadowControlManager

from .const import DOMAIN, DOMAIN_DATA_MANAGERS, SELECT_INTERNAL_TO_EXTERNAL_MAP, MovementRestricted, SCInternal


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Create Shadow Control selection based on config entries."""
    # Get the manager and use its logger
    manager: ShadowControlManager | None = hass.data.get(DOMAIN_DATA_MANAGERS, {}).get(config_entry.entry_id)
    instance_logger = manager.logger
    sanitized_instance_name = manager.sanitized_name

    entities = [
        ShadowControlSelect(
            hass,
            config_entry,
            key=SCInternal.MOVEMENT_RESTRICTION_HEIGHT_MANUAL.value,
            instance_name=sanitized_instance_name,
            logger=instance_logger,
            description=SelectEntityDescription(
                key=SCInternal.MOVEMENT_RESTRICTION_HEIGHT_MANUAL.value,
                name="Restrict height movement",
                translation_key=SCInternal.MOVEMENT_RESTRICTION_HEIGHT_MANUAL.value,
            ),
        ),
        ShadowControlSelect(
            hass,
            config_entry,
            key=SCInternal.MOVEMENT_RESTRICTION_ANGLE_MANUAL.value,
            instance_name=sanitized_instance_name,
            logger=instance_logger,
            description=SelectEntityDescription(
                key=SCInternal.MOVEMENT_RESTRICTION_ANGLE_MANUAL.value,
                name="Restrict angle movement",
                translation_key=SCInternal.MOVEMENT_RESTRICTION_ANGLE_MANUAL.value,
            ),
        ),
    ]

    entities_to_add = []
    for entity in entities:
        internal_key = entity.entity_description.key
        external_config_key = SELECT_INTERNAL_TO_EXTERNAL_MAP.get(internal_key)

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

    async_add_entities(entities_to_add)


class ShadowControlSelect(SelectEntity, RestoreEntity):
    """Represent a boolean config option from Shadow Control as selection."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        key: str,
        description: SelectEntityDescription,
        instance_name: str,
        logger: logging.Logger,
        icon: str | None = None,
    ) -> None:
        """Initialize the selection."""
        self.hass = hass
        self.logger = logger
        self.entity_description = description
        self._key = key
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
        self._attr_extra_state_attributes = {}  # For additional attributes if required

        if icon:
            self._attr_icon = icon

    @property
    def options(self) -> list[str]:
        """Return the list of options for the selection."""
        # The options are static, so we return a predefined list
        return [state.to_ha_state_string() for state in MovementRestricted]

    @property
    def current_option(self) -> str:
        """Return the current selected option."""
        # Get the current value from the config entry options
        return self.hass.data[DOMAIN].get("select_states", {}).get(self.unique_id, MovementRestricted.NO_RESTRICTION.value)

    def select_option(self, option: str) -> None:
        """Change the selected option, delegate to async."""
        self.logger.debug("Synchronous select_option called for '%s' with value '%s'. Scheduling async update.", self._key, option)
        self.hass.loop.create_task(self.async_select_option(option))

    async def async_select_option(self, option: str) -> None:
        """Change the selected option asynchronously."""
        self.logger.debug("Setting option '%s' to %s for entry '%s'", self._key, option, self._config_entry.entry_id)
        if "select_states" not in self.hass.data[DOMAIN]:
            self.hass.data[DOMAIN]["select_states"] = {}
        self.hass.data[DOMAIN]["select_states"][self.unique_id] = option
        self.async_write_ha_state()

    async def _set_option(self, value: str) -> None:
        """Update a config option within ConfigEntry."""
        self.logger.debug("Setting option '%s' to %s for entry '%s'", self._key, value, self._config_entry.entry_id)
        self.hass.data[DOMAIN]["select_states"][self.unique_id] = value

    async def async_added_to_hass(self) -> None:
        """Register callbacks with entity registration at HA."""
        await super().async_added_to_hass()

        if "unique_id_map" not in self.hass.data.setdefault(DOMAIN, {}):
            self.hass.data[DOMAIN]["unique_id_map"] = {}

        self.hass.data[DOMAIN]["unique_id_map"][self.unique_id] = self.entity_id

        last_state = await self.async_get_last_state()
        if last_state:
            self.logger.debug("Restoring last state for %s: %s", self.name, last_state.state)
            # Restore the selection state in hass.data
            self.hass.data[DOMAIN].setdefault("select_states", {})[self.unique_id] = last_state.state
            self.async_write_ha_state()

    async def _notify_integration(self) -> None:
        await self.hass.data[DOMAIN_DATA_MANAGERS][self._config_entry.entry_id].async_calculate_and_apply_cover_position(None)
