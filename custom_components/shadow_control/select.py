"""Shadow Control select implementation."""

import logging
from typing import TYPE_CHECKING

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity

if TYPE_CHECKING:
    from . import ShadowControlManager

from .const import DOMAIN, DOMAIN_DATA_MANAGERS, SC_CONF_NAME, MovementRestricted, SCDynamicInput


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Create Shadow Control selection based on config entries."""
    # Get the manager and use its logger
    manager: ShadowControlManager | None = hass.data.get(DOMAIN_DATA_MANAGERS, {}).get(config_entry.entry_id)
    instance_logger = manager.logger
    instance_name = config_entry.data.get(SC_CONF_NAME, DOMAIN)

    entities = [
        ShadowControlSelect(
            hass,
            config_entry,
            key=SCDynamicInput.MOVEMENT_RESTRICTION_HEIGHT_STATIC.value,
            translation_key="movement_restriction_height_static",
            instance_name=instance_name,
            logger=instance_logger,
        ),
        ShadowControlSelect(
            hass,
            config_entry,
            key=SCDynamicInput.MOVEMENT_RESTRICTION_ANGLE_STATIC.value,
            translation_key="movement_restriction_angle_static",
            instance_name=instance_name,
            logger=instance_logger,
        ),
    ]

    # Add all the entities to Home Assistant
    async_add_entities(entities)


class ShadowControlSelect(SelectEntity, RestoreEntity):
    """Represent a boolean config option from Shadow Control as selection."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        key: str,
        logger: logging.Logger,
        translation_key: str,
        instance_name: str,
        icon: str | None = None,
    ) -> None:
        """Initialize the selection."""
        self.hass = hass
        self.logger = logger
        self._config_entry = config_entry
        self._key = key

        self._attr_translation_key = translation_key
        self._attr_has_entity_name = True

        self._attr_unique_id = f"{config_entry.entry_id}_{key}"

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
        current_value = self._config_entry.options.get(self._key, MovementRestricted.NO_RESTRICTION.value)
        self.logger.debug("Current option for '%s': %s", self._key, current_value)
        return current_value

    def select_option(self, option: str) -> None:
        """Change the selected option, delegate to async."""
        self.logger.debug("Synchronous select_option called for '%s' with value '%s'. Scheduling async update.", self._key, option)
        # Planen Sie die asynchrone Methode im Event-Loop
        self.hass.loop.create_task(self.async_select_option(option))

    async def async_select_option(self, option: str) -> None:
        """Change the selected option asynchronously."""
        self.logger.debug("Setting option '%s' to %s for entry '%s'", self._key, option, self._config_entry.entry_id)
        current_options = self._config_entry.options.copy()
        current_options[self._key] = option

        # Update config entry by triggering listeners
        self.hass.config_entries.async_update_entry(self._config_entry, options=current_options)

    async def _set_option(self, value: str) -> None:
        """Update a config option within ConfigEntry."""
        self.logger.debug("Setting option '%s' to %s for entry '%s'", self._key, value, self._config_entry.entry_id)
        current_options = self._config_entry.options.copy()
        current_options[self._key] = value

        # Update config entry by triggering listeners
        self.hass.config_entries.async_update_entry(self._config_entry, options=current_options)

    @callback
    async def _handle_options_update(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Handle option updates from within the config entry."""
        if entry.entry_id == self._config_entry.entry_id:
            # Get the newest value from the option
            new_value = self._config_entry.options.get(self._key, MovementRestricted.NO_RESTRICTION.value)
            if self.current_option != new_value:
                self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Register callbacks with entity registration at HA."""
        await super().async_added_to_hass()

        # Ensure the entity is following changes at the config_entry. Important if changed within
        # the ConfigFlow and UI should \"see\" that change too.
        self._config_entry.async_on_unload(self._config_entry.add_update_listener(self._handle_options_update))

        # Restore last state after Home Assistant restart.
        last_state = await self.async_get_last_state()
        if last_state:
            self.logger.debug("Restoring last state for %s: %s", self.name, last_state.state)
            if self.current_option != last_state.state:
                self.async_write_ha_state()
