"""Shadow Control sensor implementation."""

import homeassistant.helpers.entity_registry as er
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ShadowControlManager
from .const import DOMAIN, DOMAIN_DATA_MANAGERS, EXTERNAL_SENSOR_DEFINITIONS, SCFacadeConfig2, SensorEntries, ShutterState, ShutterType


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Shadow Control sensor platform from a config entry."""
    # Get the manager and use its logger
    manager: ShadowControlManager | None = hass.data.get(DOMAIN_DATA_MANAGERS, {}).get(config_entry.entry_id)
    instance_logger = manager.logger
    instance_logger.debug("Setting up sensor platform from config entry: %s", config_entry.entry_id)
    config_options = config_entry.options
    config_entry_id = config_entry.entry_id  # Shortcut for entry ID

    if manager is None:
        instance_logger.error("No Shadow Control manager found for config entry %s. Cannot set up sensors.", config_entry.entry_id)
        return

    instance_logger.debug("Creating sensors for manager: %s (from entry %s)", manager.name, config_entry.entry_id)

    shutter_type_value = config_entry.data.get(SCFacadeConfig2.SHUTTER_TYPE_STATIC.value)
    instance_logger.debug("Shutter type for instance %s is %s", manager.name, shutter_type_value)

    entities_to_add = [
        ShadowControlSensor(manager, config_entry.entry_id, SensorEntries.USED_HEIGHT),
        ShadowControlSensor(manager, config_entry.entry_id, SensorEntries.COMPUTED_HEIGHT),
        ShadowControlSensor(manager, config_entry.entry_id, SensorEntries.CURRENT_STATE),
        ShadowControlSensor(manager, config_entry.entry_id, SensorEntries.LOCK_STATE),
        ShadowControlSensor(manager, config_entry.entry_id, SensorEntries.NEXT_SHUTTER_MODIFICATION),
        ShadowControlSensor(manager, config_entry.entry_id, SensorEntries.IS_IN_SUN),
    ]

    if shutter_type_value != ShutterType.MODE3.value:
        # Sensoren, die nur für MODE3 relevant sind (Jalousien mit Neigungswinkelsteuerung)
        entities_to_add.extend(
            [
                ShadowControlSensor(manager, config_entry.entry_id, SensorEntries.USED_ANGLE),
                ShadowControlSensor(manager, config_entry.entry_id, SensorEntries.USED_ANGLE_DEGREES),
                ShadowControlSensor(manager, config_entry.entry_id, SensorEntries.COMPUTED_ANGLE),
            ]
        )

    text_sensor = ShadowControlCurrentStateTextSensor(manager, config_entry.entry_id, manager.name)
    entities_to_add.append(text_sensor)

    instance_name = manager.sanitized_name
    config_options = config_entry.options

    # ----------------------------------------------------------------------
    # PART 1: Identify and Create REQUIRED External Sensors
    # ----------------------------------------------------------------------
    required_external_unique_ids = set()

    for definition in EXTERNAL_SENSOR_DEFINITIONS:
        config_key = definition["config_key"]
        external_entity_id = config_options.get(config_key)

        unique_id = f"{config_entry_id}_{config_key}_source_value"

        # Check if an external entity ID is configured and is not an empty/none value
        if external_entity_id and external_entity_id.lower() not in ("none", ""):
            # 1. Entity IS required: track its unique ID
            required_external_unique_ids.add(unique_id)

            # 2. Create the entity instance
            sensor = ShadowControlExternalEntityValueSensor(
                hass,
                manager,
                config_entry_id,
                instance_name,
                definition,
                external_entity_id,
            )
            entities_to_add.append(sensor)

    # ----------------------------------------------------------------------
    # PART 2: Cleanup Unrequired External Sensors from the Registry
    # ----------------------------------------------------------------------
    registry = er.async_get(hass)

    # Iterate over ALL possible external sensor unique IDs
    for definition in EXTERNAL_SENSOR_DEFINITIONS:
        config_key = definition["config_key"]
        unique_id = f"{config_entry_id}_{config_key}_source_value"

        # If this unique ID is NOT in the set of currently required entities...
        if unique_id not in required_external_unique_ids:
            # Look it up in the registry
            entity_id = registry.async_get_entity_id(Platform.SENSOR, DOMAIN, unique_id)

            if entity_id:
                instance_logger.debug("Removing deprecated external sensor entity: %s (unique_id: %s)", entity_id, unique_id)
                # Remove the entity from the registry. This removes it from the UI immediately.
                registry.async_remove(entity_id)

    if entities_to_add:
        async_add_entities(entities_to_add, True)
        instance_logger.info("Successfully added %s Shadow Control sensor entities for '%s'.", len(entities_to_add), manager.name)
    else:
        instance_logger.warning("No sensor entities created for manager '%s'.", manager.name)


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
        self._attr_unique_id = f"{self._entry_id}_{self._sensor_entry_type.value}"

        # Define key used within translation files based on enum values e.g. "target_height".
        self._attr_translation_key = f"sensor_{self._sensor_entry_type.value}"

        # Define attributes based on the sensor type
        if self._sensor_entry_type == SensorEntries.USED_HEIGHT:
            self._attr_native_unit_of_measurement = "%"
            self._attr_icon = "mdi:pan-vertical"
            self._attr_state_class = "measurement"
        elif self._sensor_entry_type == SensorEntries.USED_ANGLE:
            self._attr_native_unit_of_measurement = "%"
            self._attr_icon = "mdi:rotate-3d"
            self._attr_state_class = "measurement"
        elif self._sensor_entry_type == SensorEntries.USED_ANGLE_DEGREES:
            self._attr_native_unit_of_measurement = "°"
            self._attr_icon = "mdi:rotate-3d"
            self._attr_state_class = "measurement"
        if self._sensor_entry_type == SensorEntries.COMPUTED_HEIGHT:
            self._attr_native_unit_of_measurement = "%"
            self._attr_icon = "mdi:pan-vertical"
            self._attr_state_class = "measurement"
        elif self._sensor_entry_type == SensorEntries.COMPUTED_ANGLE:
            self._attr_native_unit_of_measurement = "%"
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
            self._attr_state_class = None  # TIMESTAMP devices typically don't have a state class
            self._attr_native_unit_of_measurement = None
        elif self._sensor_entry_type == SensorEntries.IS_IN_SUN:
            self._attr_icon = "mdi:sun-angle-outline"

        # Connect with the device (important for UI)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._entry_id)},
            name=manager.name,
            model="Shadow Control",
            manufacturer="Yves Schumann",
        )

    @property
    def native_value(self):  # noqa: ANN201
        """Return the state of the sensor from the manager."""
        value = None
        if self._sensor_entry_type == SensorEntries.USED_HEIGHT:
            value = self._manager.used_shutter_height
        if self._sensor_entry_type == SensorEntries.USED_ANGLE:
            value = self._manager.used_shutter_angle
        if self._sensor_entry_type == SensorEntries.USED_ANGLE_DEGREES:
            value = self._manager.used_shutter_angle_degrees
        if self._sensor_entry_type == SensorEntries.COMPUTED_HEIGHT:
            value = self._manager.calculated_shutter_height
        if self._sensor_entry_type == SensorEntries.COMPUTED_ANGLE:
            value = self._manager.calculated_shutter_angle
        if self._sensor_entry_type == SensorEntries.CURRENT_STATE:
            value = (
                self._manager.current_shutter_state.value
                if hasattr(self._manager.current_shutter_state, "value")
                else self._manager.current_shutter_state
            )
        if self._sensor_entry_type == SensorEntries.LOCK_STATE:
            value = self._manager.current_lock_state.value if hasattr(self._manager.current_lock_state, "value") else self._manager.current_lock_state
        if self._sensor_entry_type == SensorEntries.NEXT_SHUTTER_MODIFICATION:
            value = self._manager.next_modification_timestamp
        if self._sensor_entry_type == SensorEntries.IS_IN_SUN:
            # For boolean states, ensure it's a native Python boolean
            value = bool(self._manager.is_in_sun)

        if value is None:
            return None

            # 2. Apply the rounding logic for clean UI display
        if isinstance(value, (float, int)):
            # Round and cast to int to ensure the final output is a whole number,
            # which removes the trailing decimals in the HA frontend.
            return int(round(value))  # noqa: RUF046

            # Return all other types (strings, etc.) as is
        return value

    async def async_added_to_hass(self) -> None:
        """Run when this entity has been added to Home Assistant."""
        # Register a Dispatcher listener here to receive updates.
        # The manager must then send this signal when its data is updated.
        # The signal name must exactly match what the manager sends.
        # Use the manager's name (which is unique for each config entry) to create a unique signal.
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{DOMAIN}_update_{self._manager.name.lower().replace(' ', '_')}",  # Unique signal for this manager
                self.async_write_ha_state,  # Calls this sensor's method to update its state in HA
            )
        )


class ShadowControlCurrentStateTextSensor(SensorEntity):
    """Sensor for the current state in human-readable form."""

    def __init__(self, manager: ShadowControlManager, config_entry_id: str, instance_name: str) -> None:
        """Initialize the sensor."""
        self._manager = manager
        self._config_entry_id = config_entry_id
        self._instance_name = instance_name

        self._attr_unique_id = f"{config_entry_id}_current_state_text"
        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_translation_key = "sensor_current_state_text"  # translation key
        self._attr_has_entity_name = True
        self._attr_icon = "mdi:state-machine"

        # Possible options as a list of strings (lowercase names of enum members)
        self._attr_options = [state.to_ha_state_string() for state in ShutterState]

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry_id)},
            name=instance_name,
            model="Shadow Control",
            manufacturer="Yves Schumann",
        )

    @property
    def state(self) -> str | None:
        """Return "speaking" state of sensor."""
        return self._manager.current_shutter_state.to_ha_state_string()

    async def async_added_to_hass(self) -> None:
        """Register callbacks at the entity registry."""
        await super().async_added_to_hass()

        # Register a dispatcher listener to get updates. Manager needs to send this signal to update
        # its data. Important to update within the UI if the state changes.
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{DOMAIN}_update_{self._manager.name.lower().replace(' ', '_')}",
                self.async_write_ha_state,
            )
        )


class ShadowControlExternalEntityValueSensor(SensorEntity):
    """Sensor that mirrors the state of a configured external entity."""

    def __init__(
        self,
        hass: HomeAssistant,
        manager: ShadowControlManager,
        config_entry_id: str,
        instance_name: str,
        definition: dict,
        external_entity_id: str,
    ) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self._manager = manager
        self._external_entity_id = external_entity_id
        self._attr_translation_key = definition["translation_key"]
        self._attr_has_entity_name = True
        self.logger = manager.logger

        # Unique ID based on the config key to ensure one per external entity type
        self._attr_unique_id = f"{config_entry_id}_{definition['config_key']}_source_value"

        # Attributes
        self._attr_native_unit_of_measurement = definition.get("unit")
        self._attr_state_class = definition.get("state_class")
        self._attr_device_class = definition.get("device_class")
        self._attr_icon = definition.get("icon")

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry_id)},
            name=manager.name,
            model="Shadow Control",
            manufacturer="Yves Schumann",
        )

    @property
    def native_value(self) -> float | int | str | None:
        """Return the state of the sensor."""
        entity_id = self._external_entity_id

        # Keine Entität konfiguriert
        if not entity_id or entity_id == "none":
            return None

        state = self.hass.states.get(entity_id)

        # Entität existiert nicht oder ist nicht verfügbar
        if state is None or state.state in ("unknown", "unavailable"):
            return None

        # Versuche den Wert zu konvertieren
        try:
            # Für numerische Sensoren (haben state_class)
            if self._attr_state_class is not None:
                # Versuche Float-Konvertierung
                return float(state.state)
        except (ValueError, TypeError) as e:
            self.logger.debug("Could not convert state '%s' of entity '%s' to numeric value: %s", state.state, entity_id, e)
            return None
        else:
            # Für text-basierte Sensoren (kein state_class)
            # Wird nur ausgeführt wenn kein Exception auftritt UND state_class None ist
            return state.state

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        entity_id = self._external_entity_id

        # Keine Entität konfiguriert
        if not entity_id or entity_id == "none":
            return False

        state = self.hass.states.get(entity_id)

        # Sensor ist nur verfügbar wenn die verknüpfte Entität verfügbar ist
        if state is None:
            return False

        return state.state not in ("unknown", "unavailable")
