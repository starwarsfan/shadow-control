"""Integration for Shadow Control."""

import logging
import os # Für Pfadmanipulation
from logging.handlers import RotatingFileHandler # Importieren Sie den Handler-Typ

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__) # Dies ist der Logger für __init__.py: 'custom_components.shadow_control'

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Shadow Control component."""
    _LOGGER.info("Shadow Control component is being set up via async_setup (YAML).")

    log_dir = hass.config.path("logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, f"{DOMAIN}.log")

    # Diese Funktion wird vollständig im Executor ausgeführt
    def setup_and_add_file_handler():
        # Holen Sie sich den Logger-Instanz innerhalb dieses Executor-Threads.
        # Es ist dieselbe Instanz wie _LOGGER ausserhalb.
        component_logger = logging.getLogger(__name__) 

        file_handler = RotatingFileHandler(
            log_file_path,
            maxBytes=1048576, # 1 MB
            backupCount=5
        )
        formatter = logging.Formatter('%(asctime)s %(levelname)s (%(threadName)s) [%(name)s] %(message)s')
        file_handler.setFormatter(formatter)
        
        # Level setzen und Handler hinzufügen *innerhalb des Executor-Threads*
        component_logger.setLevel(logging.DEBUG) 
        if file_handler not in component_logger.handlers:
            component_logger.addHandler(file_handler)
            # Auch die erste Log-Meldung, die das File-Öffnen triggern könnte, hier ausführen
            component_logger.debug(f"Configured separate logfile for Shadow Control at: {log_file_path}")
        return True # Rückgabewert ist hier nicht wichtig, aber eine Funktion braucht einen

    # Führen Sie die gesamte Einrichtung des File-Handlers im Executor aus
    await hass.loop.run_in_executor(None, setup_and_add_file_handler)
    
    # Die Debug-Meldung hier ist nicht mehr nötig, da sie im Executor geschehen ist.
    # _LOGGER.debug(f"Configured separate logfile for Shadow Control at: {log_file_path}") # DIESE ZEILE ENTFERNEN

    hass.data[DOMAIN] = config.get(DOMAIN, {})

    return True
