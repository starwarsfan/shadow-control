"""Shadow Control binary sensor implementation."""

import logging
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.restore_state import RestoreEntity

if TYPE_CHECKING:
    from . import ShadowControlManager

from .const import (
    DOMAIN,
    DOMAIN_DATA_MANAGERS,
    SCInternal,
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Create Shadow Control binary sensors based on config entries."""
    manager: ShadowControlManager | None = hass.data.get(DOMAIN_DATA_MANAGERS, {}).get(config_entry.entry_id)
    instance_logger = manager.logger
    sanitized_instance_name = manager.sanitized_name

    async_add_entities(
        [
            ShadowControlAutoLockBinarySensor(
                hass,
                config_entry,
                instance_name=sanitized_instance_name,
                logger=instance_logger,
            ),
        ]
    )


class ShadowControlAutoLockBinarySensor(BinarySensorEntity, RestoreEntity):
    """
    Read-only binary sensor that persists the manager's auto-lock state across HA restarts.

    This sensor is controlled exclusively by the integration — it is not user-editable.
    EntityCategory.DIAGNOSTIC keeps it in the diagnostics view as a status indicator only.

    Restore flow:
      async_added_to_hass() reads the last HA state via RestoreEntity and immediately
      calls manager.restore_auto_lock() before the first calculation runs.

    Sync flow:
      Subscribes to the manager's dispatcher signal. Whenever the manager updates
      (position change, auto-lock toggle, etc.) _handle_manager_update() is called,
      which writes the current manager.auto_lock_active value to hass.states
      so it is persisted by the recorder.
    """

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        instance_name: str,
        logger: logging.Logger,
    ) -> None:
        """Initialize the auto-lock binary sensor."""
        self.hass = hass
        self.logger = logger
        self._config_entry = config_entry

        self.entity_description = BinarySensorEntityDescription(
            key=SCInternal.AUTO_LOCK_ACTIVE.value,
            name="Auto lock active",
        )
        self._attr_translation_key = SCInternal.AUTO_LOCK_ACTIVE.value
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{config_entry.entry_id}_{SCInternal.AUTO_LOCK_ACTIVE.value}"
        self._attr_icon = "mdi:lock-clock"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name=instance_name,
            manufacturer="Yves Schumann",
            model="Shadow Control",
        )

        self._state = False

    @property
    def is_on(self) -> bool:
        """Return current auto-lock state."""
        return self._state

    async def async_added_to_hass(self) -> None:
        """Restore auto-lock state and subscribe to manager updates."""
        await super().async_added_to_hass()

        # Restore last persisted state
        last_state = await self.async_get_last_state()
        self._state = last_state.state == "on" if last_state else False

        # Push restored value into the manager immediately so the next calculation
        # sees the correct _locked_by_auto_lock before any event fires.
        manager = self.hass.data.get(DOMAIN_DATA_MANAGERS, {}).get(self._config_entry.entry_id)
        if manager:
            manager.restore_auto_lock(self._state)
            self.logger.debug("Restored manager auto_lock_active=%s from last HA state", self._state)
            signal = f"{DOMAIN}_update_{manager.name.lower().replace(' ', '_')}"
            self.async_on_remove(async_dispatcher_connect(self.hass, signal, self._handle_manager_update))

        self.async_write_ha_state()

    @callback
    def _handle_manager_update(self) -> None:
        """Sync sensor state with manager._locked_by_auto_lock on every manager update."""
        manager = self.hass.data.get(DOMAIN_DATA_MANAGERS, {}).get(self._config_entry.entry_id)
        if manager:
            new_state = manager.auto_lock_active
            if self._state != new_state:
                self._state = new_state
                self.async_write_ha_state()
