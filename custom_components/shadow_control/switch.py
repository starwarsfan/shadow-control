"""Shadow Control switch implementation."""

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.restore_state import RestoreEntity

if TYPE_CHECKING:
    from . import ShadowControlManager

from .const import DEBUG_ENABLED, DOMAIN, DOMAIN_DATA_MANAGERS, SCDawnInput, SCDynamicInput, SCInternal, SCShadowInput


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
        ShadowControlConfigSwitch(
            hass,
            config_entry,
            key=DEBUG_ENABLED,
            translation_key="debug_enabled",
            instance_name=sanitized_instance_name,
            icon="mdi:developer-board",
            logger=instance_logger,
        ),
        ShadowControlSwitch(
            hass,
            config_entry,
            key=SCInternal.SHADOW_CONTROL_ENABLED_MANUAL.value,
            description=SwitchEntityDescription(
                key=SCInternal.SHADOW_CONTROL_ENABLED_MANUAL.value,
                name="Enable shadow control",  # default (English) fallback if no translation found
            ),
            external_config_key=SCShadowInput.CONTROL_ENABLED_ENTITY.value,
            instance_name=sanitized_instance_name,
            logger=instance_logger,
        ),
        ShadowControlSwitch(
            hass,
            config_entry,
            key=SCInternal.DAWN_CONTROL_ENABLED_MANUAL.value,
            description=SwitchEntityDescription(
                key=SCInternal.DAWN_CONTROL_ENABLED_MANUAL.value,
                name="Enable dawn control",  # default (English) fallback if no translation found
            ),
            external_config_key=SCDawnInput.CONTROL_ENABLED_ENTITY.value,
            instance_name=sanitized_instance_name,
            logger=instance_logger,
        ),
        ShadowControlSwitch(
            hass,
            config_entry,
            key=SCInternal.LOCK_INTEGRATION_MANUAL.value,
            instance_name=sanitized_instance_name,
            logger=instance_logger,
            description=SwitchEntityDescription(
                key=SCInternal.LOCK_INTEGRATION_MANUAL.value,
                name="Lock",  # default (English) fallback if no translation found
            ),
            external_config_key=SCDynamicInput.LOCK_INTEGRATION_ENTITY.value,
        ),
        ShadowControlSwitch(
            hass,
            config_entry,
            key=SCInternal.LOCK_INTEGRATION_WITH_POSITION_MANUAL.value,
            instance_name=sanitized_instance_name,
            logger=instance_logger,
            description=SwitchEntityDescription(
                key=SCInternal.LOCK_INTEGRATION_WITH_POSITION_MANUAL.value,
                name="Lock with position",  # default (English) fallback if no translation found
            ),
            external_config_key=SCDynamicInput.LOCK_INTEGRATION_WITH_POSITION_ENTITY.value,
        ),
    ]

    # Add all the entities to Home Assistant
    async_add_entities(entities)


class ShadowControlConfigSwitch(SwitchEntity, RestoreEntity):
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
        external_config_key: str | None = None,
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

        self._external_config_key = external_config_key
        self._is_overridden_by_external = False

        self._manager: ShadowControlManager = hass.data[DOMAIN_DATA_MANAGERS][config_entry.entry_id]
        if self._external_config_key:
            # Check if an external entity ID is configured in options
            external_id = self._manager.config_entry.options.get(self._external_config_key)
            # The entity is overridden if the config key has a non-empty string value
            self._is_overridden_by_external = external_id not in (None, "")

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
    def available(self) -> bool:
        """Return True if entity is available."""
        # The internal switch is NOT available if it is overridden by an external entity
        return not self._is_overridden_by_external

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        # If overridden, read the state from the external entity
        if self._is_overridden_by_external:
            external_id = self._manager.config_entry.options.get(self._external_config_key)
            state = self.hass.states.get(external_id)
            # Use STATE_ON constant for comparison
            return state.state == STATE_ON if state else False

        # Otherwise, return the internal state
        return self._state

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Switch the switch on."""
        if self._is_overridden_by_external:
            self.logger.warning("Attempted to turn on internal switch '%s', but it is overridden by an external entity.", self.name)
            return

        self._state = True
        self.async_write_ha_state()
        await self.hass.async_create_task(self._notify_integration())

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Switch the switch off."""
        if self._is_overridden_by_external:
            self.logger.warning("Attempted to turn off internal switch '%s', but it is overridden by an external entity.", self.name)
            return

        self._state = False
        self.async_write_ha_state()
        await self.hass.async_create_task(self._notify_integration())

    async def async_added_to_hass(self) -> None:
        """Register callbacks with entity registration at HA."""
        await super().async_added_to_hass()

        # ... (Existing unique_id_map storage logic) ...
        # Restore last state after Home Assistant restart.
        last_state = await self.async_get_last_state()

        # Only restore state if not overridden, otherwise the state comes from the external entity
        if last_state and not self._is_overridden_by_external:
            self.logger.debug("Restoring last state for %s: %s", self.name, last_state.state)
            self._state = last_state.state == STATE_ON

            # --- NEW LISTENER LOGIC START ---
        if self._is_overridden_by_external:
            external_id = self._manager.config_entry.options.get(self._external_config_key)
            # Listen for external state changes to update the internal switch's state
            self.async_on_remove(async_track_state_change_event(self.hass, [external_id], self._async_external_state_change_listener))

        # Ensure initial state (including 'available' and 'is_on') is written to HA
        self.async_write_ha_state()
        # --- NEW LISTENER LOGIC END ---

    @callback
    def _async_external_state_change_listener(self, event: Event) -> None:
        """Handle external entity state changes and update internal entity state."""
        # This forces the entity to re-read the state from the external entity via self.is_on
        self.async_write_ha_state()

    async def _notify_integration(self) -> None:
        await self.hass.data[DOMAIN_DATA_MANAGERS][self._config_entry.entry_id].async_calculate_and_apply_cover_position(None)
