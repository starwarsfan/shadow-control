"""Shadow Control button implementation."""

import logging
from typing import TYPE_CHECKING

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
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
    """Create Shadow Control button based on config entries."""
    # Get the manager and use its logger and sanitized name
    manager: ShadowControlManager | None = hass.data.get(DOMAIN_DATA_MANAGERS, {}).get(config_entry.entry_id)
    instance_logger = manager.logger
    sanitized_instance_name = manager.sanitized_name

    entities = [
        ShadowControlButton(
            hass,
            config_entry,
            key=SCInternal.ENFORCE_POSITIONING_MANUAL.value,
            instance_name=sanitized_instance_name,
            name="Trigger",
            icon="mdi:developer-board",
            logger=instance_logger,
            description=ButtonEntityDescription(
                key=SCInternal.ENFORCE_POSITIONING_MANUAL.value,
                translation_key=SCInternal.ENFORCE_POSITIONING_MANUAL.value,
                icon="mdi:ray-start-end",
            ),
        ),
    ]

    # Add all the entities to Home Assistant
    async_add_entities(entities)


class ShadowControlButton(ButtonEntity):
    """Represent a momentary button for Shadow Control."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        key: str,  # Use this for your unique ID and internal logic
        description: ButtonEntityDescription,
        logger: logging.Logger,
        instance_name: str,
        name: str,  # The display name
        icon: str | None = None,
    ) -> None:
        """Initialize the button."""
        self.hass = hass
        self.logger = logger
        self.entity_description = description
        self._config_entry = config_entry
        self._attr_translation_key = description.key
        self._attr_has_entity_name = True

        self._attr_unique_id = f"{config_entry.entry_id}_{key}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name=instance_name,
            manufacturer="Yves Schumann",
            model="Shadow Control",
        )

        if icon:
            self._attr_icon = icon

    async def async_press(self) -> None:
        """Handle the button press action."""
        self.logger.debug("Button '%s' pressed! Executing action.", self.name)

        manager = self.hass.data[DOMAIN_DATA_MANAGERS][self._config_entry.entry_id]

        if self.entity_description.key == SCInternal.ENFORCE_POSITIONING_MANUAL.value:
            # Setze das Flag für erzwungene Positionierung
            self.logger.info("Enforce positioning triggered via button")
            await manager.async_trigger_enforce_positioning()

        # 2. You can also notify Home Assistant of the event
        # self.hass.bus.async_fire("shadow_control_button_pressed", {"entity_id": self.entity_id})

        # Important: Since it's a ButtonEntity, you **do not** need to call
        # self.async_write_ha_state(). There is no state change to record.
