"""Shadow Control switch implementation."""

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity

if TYPE_CHECKING:
    from . import ShadowControlManager

from .const import DEBUG_ENABLED, DOMAIN, DOMAIN_DATA_MANAGERS, SCDawnInput, SCDynamicInput, SCShadowInput


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Create Shadow Control switches based on config entries."""
    # Get the manager and use its logger and sanitized name
    manager: ShadowControlManager | None = hass.data.get(DOMAIN_DATA_MANAGERS, {}).get(config_entry.entry_id)
    instance_logger = manager.logger
    sanitized_instance_name = manager.sanitized_name

    entities = [
        ShadowControlConfigBooleanSwitch(
            hass,
            config_entry,
            key=DEBUG_ENABLED,
            translation_key="debug_enabled",
            instance_name=sanitized_instance_name,
            icon="mdi:developer-board",
            logger=instance_logger,
        ),
        ShadowControlConfigBooleanSwitch(
            hass,
            config_entry,
            key=SCShadowInput.CONTROL_ENABLED_STATIC.value,
            translation_key="shadow_control_enabled_static",
            instance_name=sanitized_instance_name,
            logger=instance_logger,
        ),
        ShadowControlConfigBooleanSwitch(
            hass,
            config_entry,
            key=SCDawnInput.CONTROL_ENABLED_STATIC.value,
            translation_key="dawn_control_enabled_static",
            instance_name=sanitized_instance_name,
            logger=instance_logger,
        ),
        ShadowControlRuntimeBooleanSwitch(
            hass,
            config_entry,
            key=SCDynamicInput.LOCK_INTEGRATION_ENTITY.value,
            instance_name=sanitized_instance_name,
            logger=instance_logger,
            description=SwitchEntityDescription(
                key=SCDynamicInput.LOCK_INTEGRATION_ENTITY.value,
                name="Lock",  # default (English) fallback if no translation found
            ),
        ),
        ShadowControlRuntimeBooleanSwitch(
            hass,
            config_entry,
            key=SCDynamicInput.LOCK_INTEGRATION_WITH_POSITION_ENTITY.value,
            instance_name=sanitized_instance_name,
            logger=instance_logger,
            description=SwitchEntityDescription(
                key=SCDynamicInput.LOCK_INTEGRATION_WITH_POSITION_ENTITY.value,
                name="Lock with position",  # default (English) fallback if no translation found
            ),
        ),
    ]

    # Add all the entities to Home Assistant
    async_add_entities(entities)


class ShadowControlConfigBooleanSwitch(SwitchEntity, RestoreEntity):
    """Represent a boolean config option from Shadow Control as switch."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        key: str,
        translation_key: str,
        logger: logging.Logger,
        instance_name: str,
        icon: str | None = None,
    ) -> None:
        """Initialize the switch."""
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
    def is_on(self) -> bool | None:
        """Return true if the switch is on."""
        # False, if the key doesn't exist e.g., within the first setup or old configuration
        return self._config_entry.options.get(self._key, False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Switch the switch on."""
        # Await the asynchronous _set_option call
        await self._set_option(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Switch the switch off."""
        # Await the asynchronous _set_option call
        await self._set_option(False)

    async def _set_option(self, value: bool) -> None:
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
            current_value = self._config_entry.options.get(self._key, False)
            if self.is_on != current_value:
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
            # The `is_on` property is already reading the value from `_config_entry.options`.
            # If the key is not within `options` the default value (False) is used.


class ShadowControlRuntimeBooleanSwitch(SwitchEntity, RestoreEntity):
    """Represent a boolean option from Shadow Control as switch."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        key: str,
        description: SwitchEntityDescription,
        instance_name: str,
        logger: logging.Logger,
        icon: str | None = None,
    ) -> None:
        """Initialize the switch."""
        self.hass = hass
        self.logger = logger
        self.entity_description = description
        self._config_entry = config_entry
        self._attr_translation_key = description.key
        self._attr_has_entity_name = True

        self._attr_unique_id = f"{instance_name}_{key}"

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

        self._state = False

    @property
    def is_on(self) -> bool | None:
        """Return true if the switch is on."""
        return self._state

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Switch the switch on."""
        self._state = True
        self.async_write_ha_state()
        # Notify integration
        await self.hass.async_create_task(self._notify_integration())

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Switch the switch off."""
        self._state = False
        self.async_write_ha_state()
        # Notify integration
        await self.hass.async_create_task(self._notify_integration())

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
        if last_state:
            self.logger.debug("Restoring last state for %s: %s", self.name, last_state.state)
            self._state = last_state.state == "on"

    async def _notify_integration(self) -> None:
        await self.hass.data[DOMAIN_DATA_MANAGERS][self._config_entry.entry_id].async_calculate_and_apply_cover_position(None)
