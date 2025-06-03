# custom_components/shadow_control/sensor.py

import logging
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect

# New import for ConfigEntry
from homeassistant.config_entries import ConfigEntry

# Importieren Sie Konstanten und Klassen aus Ihrer Hauptintegration (__init__.py)
from .const import DOMAIN # Assuming DOMAIN is in const.py now
# You will get the manager directly from hass.data[DOMAIN][entry.entry_id] in async_setup_entry
# No need to import DOMAIN_DATA_MANAGERS here if you store managers by entry_id directly.
# Assuming ShadowControlManager is defined in __init__.py for simplicity, otherwise import it from its file.
from . import ShadowControlManager # <- Assuming ShadowControlManager is in __init__.py

_LOGGER = logging.getLogger(__name__)

# # Diese Funktion wird von Home Assistant aufgerufen, wenn Ihre Sensor-Plattform geladen wird.
# async def async_setup_platform(
#         hass: HomeAssistant,
#         config: ConfigType, # Dies ist der Home Assistant globale config Dict
#         async_add_entities, # Callback-Funktion zum Hinzufügen von Entitäten
#         discovery_info: DiscoveryInfoType = None, # Die Daten, die von async_load_platform übergeben wurden
# ) -> None:
#     """Set up the Shadow Control sensor platform."""
#     _LOGGER.debug(f"[{DOMAIN}] Setting up sensor platform.")
#
#     if discovery_info is None:
#         _LOGGER.error(f"[{DOMAIN}] No discovery info for sensor platform. Cannot set up sensors.")
#         return False # Oder True, je nachdem wie kritisch das ist
#
#     # Holen Sie sich die Liste der Manager, die in __init__.py in hass.data gespeichert wurden
#     managers = hass.data.get(DOMAIN, {}).get(DOMAIN_DATA_MANAGERS)
#     if not managers:
#         _LOGGER.warning(f"[{DOMAIN}] No Shadow Control managers found in hass.data to create sensors for.")
#         return False
#
#     entities_to_add = []
#     for manager in managers:
#         _LOGGER.debug(f"[{DOMAIN}] Creating sensors for manager: {manager._name}")
#         entities_to_add.append(ShadowControlSensor(manager, "target_height"))
#         entities_to_add.append(ShadowControlSensor(manager, "target_angle"))
#         entities_to_add.append(ShadowControlSensor(manager, "current_state"))
#         entities_to_add.append(ShadowControlSensor(manager, "lock_state"))
#
#     if entities_to_add:
#         # Fügen Sie die erstellten Sensoren zu Home Assistant hinzu.
#         # True bedeutet, dass der Status der Entitäten sofort aktualisiert werden soll.
#         async_add_entities(entities_to_add, True)
#         _LOGGER.info(f"[{DOMAIN}] Successfully added {len(entities_to_add)} Shadow Control sensor entities.")

# custom_components/shadow_control/sensor.py

async def async_setup_entry(
        hass: HomeAssistant,
        entry: ConfigEntry, # ConfigEntry object directly passed
        async_add_entities: AddEntitiesCallback, # Renamed from async_add_entities to follow HA guidelines
) -> None:
    """Set up the Shadow Control sensor platform from a config entry."""
    _LOGGER.debug(f"[{DOMAIN}] Setting up sensor platform from config entry: {entry.entry_id}")

    # Retrieve the specific manager instance associated with this config entry
    # This assumes you stored it under hass.data[DOMAIN][entry.entry_id]["manager"] in __init__.py
    manager_data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if not manager_data or "manager" not in manager_data:
        _LOGGER.error(f"[{DOMAIN}] No Shadow Control manager found for config entry {entry.entry_id}. Cannot set up sensors.")
        # Wichtig: Wenn ein Fehler auftritt, sollte die Funktion False zurückgeben,
        # damit Home Assistant weiß, dass die Einrichtung fehlgeschlagen ist.
        return False # <-- Füge diesen Return-Wert hinzu bei Fehler

    manager = manager_data["manager"] # Get the manager instance

    _LOGGER.debug(f"[{DOMAIN}] Creating sensors for manager: {manager._name} (from entry {entry.entry_id})")

    entities_to_add = [
        # Passen Sie den Konstruktor des ShadowControlSensor an,
        # um die entry.entry_id als separates Argument zu übergeben.
        ShadowControlSensor(manager, entry.entry_id, "target_height"),
        ShadowControlSensor(manager, entry.entry_id, "target_angle"),
        ShadowControlSensor(manager, entry.entry_id, "current_state"),
        ShadowControlSensor(manager, entry.entry_id, "lock_state"),
        # Add any other sensors you want to expose here
    ]

    if entities_to_add:
        async_add_entities(entities_to_add, True)
        _LOGGER.info(f"[{DOMAIN}] Successfully added {len(entities_to_add)} Shadow Control sensor entities for '{manager._name}'.")
    else:
        _LOGGER.warning(f"[{DOMAIN}] No sensor entities created for manager '{manager._name}'.")

    # Wenn alles erfolgreich war, gibt die async_setup_entry normalerweise True zurück,
    # auch wenn der Rückgabetyp None ist (für Plattformen). Die Abwesenheit eines Fehlers reicht aus.
    # Sie können es auch explizit mit `return True` abschließen, wenn Sie möchten.

# Die ShadowControlSensor Klasse definiert, wie Ihr Sensor funktioniert und seine Daten abruft.
class ShadowControlSensor(SensorEntity):
    """Represents a Shadow Control sensor."""

    def __init__(self, manager: ShadowControlManager, entry_id: str, sensor_type: str) -> None: # <--- HIER ÄNDERN
        """Initialize the sensor."""
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
            self._attr_icon = "mdi:ruler-vertical"
            self._attr_state_class = "measurement"
        elif sensor_type == "target_angle":
            self._attr_native_unit_of_measurement = "°"
            self._attr_icon = "mdi:rotate-3d"
            self._attr_state_class = "measurement"
        elif sensor_type == "current_state":
            self._attr_icon = "mdi:state-machine"
        elif sensor_type == "lock_state":
            self._attr_icon = "mdi:lock-open-check"

        # Verknüpfung mit dem Device (wichtig für die UI-Darstellung)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._entry_id)},
            name=manager._name,
            model="Shadow Control",
            manufacturer="Yves Schumann",
            configuration_url=f"/config/integrations/integration/{DOMAIN}",
        )

    @property
    def native_value(self):
        """Return the state of the sensor from the manager."""
        # Access the internal values of the manager.
        # Make sure your manager updates these attributes (`_calculated_shutter_height`, etc.)
        # and calls the dispatcher signal when they change.
        if self._sensor_type == "target_height":
            return self._manager._calculated_shutter_height
        elif self._sensor_type == "target_angle":
            return self._manager._calculated_shutter_angle
        elif self._sensor_type == "current_state":
            # Assuming _current_shutter_state is an Enum. You might want its value.
            return self._manager._current_shutter_state.value if hasattr(self._manager._current_shutter_state, 'value') else self._manager._current_shutter_state
        elif self._sensor_type == "lock_state":
            # Assuming _current_lock_state is an Enum. You might want its value.
            return self._manager._current_lock_state.value if hasattr(self._manager._current_lock_state, 'value') else self._manager._current_lock_state
        return None

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info for this sensor."""
        # This links the sensor to a "device" in Home Assistant
        # and allows grouping in the UI.
        # It's crucial for device-centric management in HA.
        return DeviceInfo(
            identifiers={(DOMAIN, self._manager._name)}, # Unique identifier for the "device" (the manager/cover instance)
            name=f"{self._manager._name} Shadow Control",
            manufacturer="Your Company", # Replace this
            model="Manager for Cover Control",
            # entry_type=DeviceEntryType.SERVICE, # Optional: Can the device itself offer services?
            # It's a good idea to link it to the config entry for proper device management in the UI
            configuration_url=f"/config/integrations/integration/{DOMAIN}", # Link to your integration page
        )

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