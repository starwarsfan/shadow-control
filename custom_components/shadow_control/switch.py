"""Shadow Control switch implementation."""

import logging
from typing import TYPE_CHECKING, Any

import homeassistant.helpers.entity_registry as er
from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity

if TYPE_CHECKING:
    from . import ShadowControlManager

from .const import DEBUG_ENABLED, DOMAIN, DOMAIN_DATA_MANAGERS, INTERNAL_TO_DEFAULTS_MAP, SWITCH_INTERNAL_TO_EXTERNAL_MAP, SCInternal


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
    config_entry_id = config_entry.entry_id

    entities = [
        ShadowControlConfigSwitch(
            hass,
            config_entry,
            key=DEBUG_ENABLED,
            instance_name=sanitized_instance_name,
            icon="mdi:developer-board",
            logger=instance_logger,
            description=SwitchEntityDescription(
                key=DEBUG_ENABLED,
                name="Debug mode",  # default (English) fallback if no translation found
            ),
        ),
        ShadowControlSwitch(
            hass,
            config_entry,
            key=SCInternal.SHADOW_CONTROL_ENABLED_MANUAL.value,
            instance_name=sanitized_instance_name,
            icon="mdi:toggle-switch",
            logger=instance_logger,
            description=SwitchEntityDescription(
                key=SCInternal.SHADOW_CONTROL_ENABLED_MANUAL.value,
                name="Shadow control",  # default (English) fallback if no translation found
            ),
        ),
        ShadowControlSwitch(
            hass,
            config_entry,
            key=SCInternal.DAWN_CONTROL_ENABLED_MANUAL.value,
            instance_name=sanitized_instance_name,
            icon="mdi:toggle-switch",
            logger=instance_logger,
            description=SwitchEntityDescription(
                key=SCInternal.DAWN_CONTROL_ENABLED_MANUAL.value,
                name="Dawn control",  # default (English) fallback if no translation found
            ),
        ),
        ShadowControlSwitch(
            hass,
            config_entry,
            key=SCInternal.LOCK_INTEGRATION_MANUAL.value,
            instance_name=sanitized_instance_name,
            logger=instance_logger,
            icon="mdi:toggle-switch",
            description=SwitchEntityDescription(
                key=SCInternal.LOCK_INTEGRATION_MANUAL.value,
                name="Lock",  # default (English) fallback if no translation found
            ),
        ),
        ShadowControlSwitch(
            hass,
            config_entry,
            key=SCInternal.LOCK_INTEGRATION_WITH_POSITION_MANUAL.value,
            instance_name=sanitized_instance_name,
            logger=instance_logger,
            icon="mdi:toggle-switch",
            description=SwitchEntityDescription(
                key=SCInternal.LOCK_INTEGRATION_WITH_POSITION_MANUAL.value,
                name="Lock with position",  # default (English) fallback if no translation found
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
        external_config_key = SWITCH_INTERNAL_TO_EXTERNAL_MAP.get(internal_key)

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
    for internal_key in SWITCH_INTERNAL_TO_EXTERNAL_MAP:
        # Construct the unique ID as it appears in the entity's __init__ method (e.g., sc_entryid_key)
        unique_id = f"{config_entry_id}_{internal_key}"

        # If the unique ID is NOT in the set of currently required entities (i.e., external is configured)...
        if unique_id not in required_internal_unique_ids:
            # Look up in the registry using Platform.SWITCH
            entity_id = registry.async_get_entity_id(Platform.SWITCH, DOMAIN, unique_id)

            if entity_id:
                instance_logger.debug("Removing deprecated internal switch entity: %s (unique_id: %s)", entity_id, unique_id)
                # Remove the entity from the registry.
                registry.async_remove(entity_id)

    async_add_entities(entities_to_add)


class ShadowControlConfigSwitch(SwitchEntity, RestoreEntity):
    """Represent a boolean config option from Shadow Control as switch."""

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
        self._key = key

        self._attr_translation_key = description.key
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


class ShadowControlSwitch(SwitchEntity, RestoreEntity):
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
        else:
            # Match this entity's key to the Enum
            member = next((m for m in SCInternal if m.value == self.entity_description.key), None)
            if member and member in INTERNAL_TO_DEFAULTS_MAP:
                self._state = INTERNAL_TO_DEFAULTS_MAP[member]
                self.logger.debug("Entity %s initialized with default: %s", self.entity_id, self._state)

        self.async_write_ha_state()

    async def _notify_integration(self) -> None:
        await self.hass.data[DOMAIN_DATA_MANAGERS][self._config_entry.entry_id].async_calculate_and_apply_cover_position(None)
