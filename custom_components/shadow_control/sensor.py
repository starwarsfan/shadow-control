# custom_components/shadow_control/sensor.py

import logging
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType, AddEntitiesCallback # Add AddEntitiesCallback
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

# Diese Funktion wird von Home Assistant aufgerufen, wenn Ihre Sensor-Plattform geladen wird.
async def async_setup_platform(
        hass: HomeAssistant,
        config: ConfigType, # Dies ist der Home Assistant globale config Dict
        async_add_entities, # Callback-Funktion zum Hinzufügen von Entitäten
        discovery_info: DiscoveryInfoType = None, # Die Daten, die von async_load_platform übergeben wurden
) -> None:
    """Set up the Shadow Control sensor platform."""
    _LOGGER.debug(f"[{DOMAIN}] Setting up sensor platform.")

    if discovery_info is None:
        _LOGGER.error(f"[{DOMAIN}] No discovery info for sensor platform. Cannot set up sensors.")
        return False # Oder True, je nachdem wie kritisch das ist

    # Holen Sie sich die Liste der Manager, die in __init__.py in hass.data gespeichert wurden
    managers = hass.data.get(DOMAIN, {}).get(DOMAIN_DATA_MANAGERS)
    if not managers:
        _LOGGER.warning(f"[{DOMAIN}] No Shadow Control managers found in hass.data to create sensors for.")
        return False

    entities_to_add = []
    for manager in managers:
        _LOGGER.debug(f"[{DOMAIN}] Creating sensors for manager: {manager._name}")
        entities_to_add.append(ShadowControlSensor(manager, "target_height"))
        entities_to_add.append(ShadowControlSensor(manager, "target_angle"))
        entities_to_add.append(ShadowControlSensor(manager, "current_state"))
        entities_to_add.append(ShadowControlSensor(manager, "lock_state"))

    if entities_to_add:
        # Fügen Sie die erstellten Sensoren zu Home Assistant hinzu.
        # True bedeutet, dass der Status der Entitäten sofort aktualisiert werden soll.
        async_add_entities(entities_to_add, True)
        _LOGGER.info(f"[{DOMAIN}] Successfully added {len(entities_to_add)} Shadow Control sensor entities.")


# Die ShadowControlSensor Klasse definiert, wie Ihr Sensor funktioniert und seine Daten abruft.
class ShadowControlSensor(SensorEntity):
    """Represents a Shadow Control sensor."""

    def __init__(self, manager, sensor_type):
        """Initialize the sensor."""
        self._manager = manager
        self._sensor_type = sensor_type
        # Unique ID muss stabil und global eindeutig sein
        # Der Manager-Name ist hier der eindeutige Identifier für das Cover
        self._attr_unique_id = f"{DOMAIN}_{manager._name.lower().replace(' ', '_')}_{sensor_type}"
        self._attr_name = f"{manager._name} Shadow Control {sensor_type.replace('_', ' ').title()}"

        # Definieren Sie Attribute basierend auf dem Sensortyp
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

    @property
    def native_value(self):
        """Return the state of the sensor from the manager."""
        # Greifen Sie auf die internen Werte des Managers zu
        if self._sensor_type == "target_height":
            return self._manager._calculated_shutter_height
        elif self._sensor_type == "target_angle":
            return self._manager._calculated_shutter_angle
        elif self._sensor_type == "current_state":
            return self._manager._current_shutter_state
        elif self._sensor_type == "lock_state":
            return self._manager._current_lock_state
        return None

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info for this sensor."""
        # Dies verknüpft den Sensor mit einem "Gerät" in Home Assistant
        # und ermöglicht die Gruppierung in der UI.
        return DeviceInfo(
            identifiers={(DOMAIN, self._manager._name)}, # Eindeutiger Identifier für das "Gerät" (das Manager-Objekt)
            name=f"{self._manager._name} Shadow Control",
            manufacturer="Your Company", # Ersetzen Sie dies
            model="Manager for Cover Control",
            # entry_type=DeviceEntryType.SERVICE, # Optional: Kann das Gerät selbst Dienste anbieten?
        )

    async def async_added_to_hass(self) -> None:
        """Run when this entity has been added to Home Assistant."""
        # Registrieren Sie hier einen Dispatcher-Listener, um Updates zu erhalten.
        # Der Manager muss dann dieses Signal senden, wenn seine Daten aktualisiert werden.
        # Der Signal-Name muss genau dem entsprechen, was der Manager sendet.
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{DOMAIN}_update_{self._manager._name.lower().replace(' ', '_')}", # Eindeutiges Signal für diesen Manager
                self.async_write_ha_state, # Ruft diese Methode des Sensors auf, um den Status in HA zu aktualisieren
            )
        )