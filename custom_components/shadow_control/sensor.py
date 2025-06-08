# custom_components/shadow_control/sensor.py

import logging
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN, DOMAIN_DATA_MANAGERS
from . import ShadowControlManager

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """
    Set up the Shadow Control sensor platform from a config entry.
    """
    _LOGGER.debug(f"[{DOMAIN}] Setting up sensor platform from config entry: {config_entry.entry_id}")

    manager: ShadowControlManager | None = hass.data.get(DOMAIN_DATA_MANAGERS, {}).get(config_entry.entry_id)

    if manager is None:
        _LOGGER.error(f"[{DOMAIN}] No Shadow Control manager found for config entry {config_entry.entry_id}. Cannot set up sensors.")
        return

    _LOGGER.debug(f"[{DOMAIN}] Creating sensors for manager: {manager._name} (from entry {config_entry.entry_id})")

    entities_to_add = [
        ShadowControlSensor(manager, config_entry.entry_id, "target_height"),
        ShadowControlSensor(manager, config_entry.entry_id, "target_angle"),
        ShadowControlSensor(manager, config_entry.entry_id, "target_angle_degrees"),
        ShadowControlSensor(manager, config_entry.entry_id, "current_state"),
        ShadowControlSensor(manager, config_entry.entry_id, "lock_state"),
        ShadowControlSensor(manager, config_entry.entry_id, "next_shutter_modification"),
    ]

    if entities_to_add:
        async_add_entities(entities_to_add, True)
        _LOGGER.info(f"[{DOMAIN}] Successfully added {len(entities_to_add)} Shadow Control sensor entities for '{manager._name}'.")
    else:
        _LOGGER.warning(f"[{DOMAIN}] No sensor entities created for manager '{manager._name}'.")

class ShadowControlSensor(SensorEntity):
    """
    Represents a Shadow Control sensor.
    """

    def __init__(self, manager: ShadowControlManager, entry_id: str, sensor_type: str) -> None: # <--- HIER ÄNDERN
        """
        Initialize the sensor.
        """
        self._manager = manager
        self._entry_id = entry_id
        self._sensor_type = sensor_type

        # Unique ID must be stable and globally unique across HA
        # The manager's name (which should be unique per config entry) is used here.
        # It's good practice to base unique_id on entry_id as well for full uniqueness guarantee
        # self._attr_unique_id = f"{DOMAIN}_{self._manager._name.lower().replace(' ', '_')}_{sensor_type}_{self._manager.hass.config_entries.async_get_entry(self._manager._config['name']).entry_id}" # Adjusted for better uniqueness based on entry_id
        # Alternatively, if manager has access to its own entry_id:
        self._attr_unique_id = f"{DOMAIN}_{self._entry_id}_{sensor_type}" # <--- HIER ÄNDERN

        # Use the name from the config entry for the device/entity name
        self._attr_name = f"{manager._name} Shadow Control {sensor_type.replace('_', ' ').title()}"

        # Define attributes based on the sensor type
        if sensor_type == "target_height":
            self._attr_native_unit_of_measurement = "%"
            self._attr_icon = "mdi:pan-vertical"
            self._attr_state_class = "measurement"
        elif sensor_type == "target_angle":
            self._attr_native_unit_of_measurement = "%"
            self._attr_icon = "mdi:rotate-3d"
            self._attr_state_class = "measurement"
        elif sensor_type == "target_angle_degrees":
            self._attr_native_unit_of_measurement = "°"
            self._attr_icon = "mdi:rotate-3d"
            self._attr_state_class = "measurement"
        elif sensor_type == "current_state":
            self._attr_icon = "mdi:state-machine"
        elif sensor_type == "lock_state":
            self._attr_icon = "mdi:lock-open-check"
        elif sensor_type == "next_shutter_modification":
            self._attr_icon = "mdi:clock-end"
            self._attr_device_class = SensorDeviceClass.TIMESTAMP
            self._attr_state_class = None
            self._attr_native_unit_of_measurement = None

        # Connect with device (important for UI)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._entry_id)},
            name=manager._name,
            model="Shadow Control",
            manufacturer="Yves Schumann",
        )

    @property
    def native_value(self):
        """
        Return the state of the sensor from the manager.
        """
        # Access the internal values of the manager.
        # Make sure your manager updates these attributes (`_calculated_shutter_height`, etc.)
        # and calls the dispatcher signal when they change.
        if self._sensor_type == "target_height":
            return self._manager._calculated_shutter_height
        elif self._sensor_type == "target_angle":
            return self._manager._calculated_shutter_angle
        elif self._sensor_type == "target_angle_degrees":
            return self._manager._calculated_shutter_angle_degrees
        elif self._sensor_type == "current_state":
            # Assuming _current_shutter_state is an Enum.
            return self._manager._current_shutter_state.value if hasattr(self._manager._current_shutter_state, 'value') else self._manager._current_shutter_state
        elif self._sensor_type == "lock_state":
            # Assuming _current_lock_state is an Enum.
            return self._manager._current_lock_state.value if hasattr(self._manager._current_lock_state, 'value') else self._manager._current_lock_state
        elif self._sensor_type == "next_shutter_modification":
            return self._manager._next_modification_timestamp
        return None

    async def async_added_to_hass(self) -> None:
        """
        Run when this entity has been added to Home Assistant.
        """
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