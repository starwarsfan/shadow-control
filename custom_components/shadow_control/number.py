"""Shadow Control number implementation."""

import logging
from typing import TYPE_CHECKING

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo

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
            key=SCInternal.LOCK_HEIGHT_ENTITY.value,
            instance_name=sanitized_instance_name,
            logger=instance_logger,
            description=NumberEntityDescription(
                key=SCInternal.LOCK_HEIGHT_ENTITY.value,
                name="Height",  # default (English) fallback if no translation found
                min_value=0.0,
                max_value=100.0,
                step=1.0,
            ),
        ),
        ShadowControlNumber(
            hass,
            config_entry,
            key=SCInternal.LOCK_ANGLE_ENTITY.value,
            instance_name=sanitized_instance_name,
            logger=instance_logger,
            description=NumberEntityDescription(
                key=SCInternal.LOCK_ANGLE_ENTITY.value,
                name="Angle",  # default (English) fallback if no translation found
                min_value=0.0,
                max_value=100.0,
                step=1.0,
            ),
        ),
    ]
    async_add_entities(entities)


class ShadowControlNumber(NumberEntity):
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
    def value(self) -> float:
        """Return the current value."""
        return self._value

    async def async_set_value(self, value: float) -> None:
        """Set new value."""
        self._value = value
        self.async_write_ha_state()
