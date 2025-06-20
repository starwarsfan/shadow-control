# custom_components/shadow_control/sensor.py

import logging

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ShadowControlManager
from .const import DOMAIN, DOMAIN_DATA_MANAGERS, SensorEntries

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Shadow Control sensor platform from a config entry."""
    _LOGGER.debug(f"[{DOMAIN}] Setting up sensor platform from config entry: {config_entry.entry_id}")

    manager: ShadowControlManager | None = hass.data.get(DOMAIN_DATA_MANAGERS, {}).get(config_entry.entry_id)

    if manager is None:
        _LOGGER.error(f"[{DOMAIN}] No Shadow Control manager found for config entry {config_entry.entry_id}. Cannot set up sensors.")
        return

    _LOGGER.debug(f"[{DOMAIN}] Creating sensors for manager: {manager._name} (from entry {config_entry.entry_id})")

    entities_to_add = [
        ShadowControlSensor(manager, config_entry.entry_id, SensorEntries.TARGET_HEIGHT),
        ShadowControlSensor(manager, config_entry.entry_id, SensorEntries.TARGET_ANGLE),
        ShadowControlSensor(manager, config_entry.entry_id, SensorEntries.TARGET_ANGLE_DEGREES),
        ShadowControlSensor(manager, config_entry.entry_id, SensorEntries.CURRENT_STATE),
        ShadowControlSensor(manager, config_entry.entry_id, SensorEntries.LOCK_STATE),
        ShadowControlSensor(manager, config_entry.entry_id, SensorEntries.NEXT_SHUTTER_MODIFICATION),
        ShadowControlSensor(manager, config_entry.entry_id, SensorEntries.IS_IN_SUN),
    ]

    if entities_to_add:
        async_add_entities(entities_to_add, True)
        _LOGGER.info(f"[{DOMAIN}] Successfully added {len(entities_to_add)} Shadow Control sensor entities for '{manager._name}'.")
    else:
        _LOGGER.warning(f"[{DOMAIN}] No sensor entities created for manager '{manager._name}'.")

class ShadowControlSensor(SensorEntity):
    """Represents a Shadow Control sensor."""

    def __init__(self, manager: ShadowControlManager, entry_id: str, sensor_entry_type: SensorEntries) -> None:
        """Initialize the sensor."""
        self._manager = manager
        self._entry_id = entry_id

        # Store the enum itself, not only the string representation
        self._sensor_entry_type = sensor_entry_type

        # Set _attr_has_entity_name true for naming convention
        self._attr_has_entity_name = True

        # Use stable unique_id based on entry_id and the sensor type
        self._attr_unique_id = f"sc_{self._entry_id}_{self._sensor_entry_type.value}"

        # Define key used within translation files based on enum values e.g. "target_height".
        self._attr_translation_key = f"sensor_{self._sensor_entry_type.value}"

        # Define attributes based on the sensor type
        if self._sensor_entry_type == SensorEntries.TARGET_HEIGHT:
            self._attr_native_unit_of_measurement = "%"
            self._attr_icon = "mdi:pan-vertical"
            self._attr_state_class = "measurement"
        elif self._sensor_entry_type == SensorEntries.TARGET_ANGLE:
            self._attr_native_unit_of_measurement = "%"
            self._attr_icon = "mdi:rotate-3d"
            self._attr_state_class = "measurement"
        elif self._sensor_entry_type == SensorEntries.TARGET_ANGLE_DEGREES:
            self._attr_native_unit_of_measurement = "°"
            self._attr_icon = "mdi:rotate-3d"
            self._attr_state_class = "measurement"
        elif self._sensor_entry_type == SensorEntries.CURRENT_STATE:
            self._attr_icon = "mdi:state-machine"
            # States for enums are usually handled directly by HA or via attribute in translation
        elif self._sensor_entry_type == SensorEntries.LOCK_STATE:
            self._attr_icon = "mdi:lock-open-check"
            # States for enums are usually handled directly by HA or via attribute in translation
        elif self._sensor_entry_type == SensorEntries.NEXT_SHUTTER_MODIFICATION:
            self._attr_icon = "mdi:clock-end"
            self._attr_device_class = SensorDeviceClass.TIMESTAMP
            self._attr_state_class = None # TIMESTAMP devices typically don't have a state class
            self._attr_native_unit_of_measurement = None
        elif self._sensor_entry_type == SensorEntries.IS_IN_SUN:
            self._attr_icon = "mdi:sun-angle-outline"

        # Connect with the device (important for UI)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._entry_id)}, # Hier self._entry_id verwenden
            name=manager._name, # Der Name der Instanz (aus der Konfiguration)
            model="Shadow Control",
            manufacturer="Yves Schumann",
        )

    @property
    def native_value(self):
        """Return the state of the sensor from the manager."""
        # Verwenden Sie _sensor_entry_type (die Enum)
        if self._sensor_entry_type == SensorEntries.TARGET_HEIGHT:
            return self._manager._calculated_shutter_height
        if self._sensor_entry_type == SensorEntries.TARGET_ANGLE:
            return self._manager._calculated_shutter_angle
        if self._sensor_entry_type == SensorEntries.TARGET_ANGLE_DEGREES:
            return self._manager._calculated_shutter_angle_degrees
        if self._sensor_entry_type == SensorEntries.CURRENT_STATE:
            return self._manager._current_shutter_state.value if hasattr(self._manager._current_shutter_state, "value") else self._manager._current_shutter_state
        if self._sensor_entry_type == SensorEntries.LOCK_STATE:
            return self._manager._current_lock_state.value if hasattr(self._manager._current_lock_state, "value") else self._manager._current_lock_state
        if self._sensor_entry_type == SensorEntries.NEXT_SHUTTER_MODIFICATION:
            return self._manager._next_modification_timestamp
        if self._sensor_entry_type == SensorEntries.IS_IN_SUN:
            # For boolean states, ensure it's a native Python boolean
            return bool(self._manager._is_in_sun)
        return None

    async def async_added_to_hass(self) -> None:
        """Run when this entity has been added to Home Assistant."""
        # Register a Dispatcher listener here to receive updates.
        # The manager must then send this signal when its data is updated.
        # The signal name must exactly match what the manager sends.
        # Use the manager's name (which is unique for each config entry) to create a unique signal.
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{DOMAIN}_update_{self._manager._name.lower().replace(' ', '_')}", # Unique signal for this manager
                self.async_write_ha_state, # Calls this sensor's method to update its state in HA
            )
        )
