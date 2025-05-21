"""Integration for Shadow Control."""

import logging
import os # Für Pfadmanipulation
from logging.handlers import RotatingFileHandler # Importieren Sie den Handler-Typ

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__) # Dies ist der Logger für __init__.py: 'custom_components.shadow_control'

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Shadow Control component for YAML configuration."""
    _LOGGER.info("Shadow Control component is being set up via async_setup (YAML).")

    # === HINZUGEFÜGT: Konfiguration für separates Logfile ===
    # Bestimmen des Pfades zum Konfigurationsverzeichnis
    config_dir = hass.config.config_dir
    log_dir = os.path.join(config_dir, "logs") # Erstellen Sie einen 'logs' Unterordner
    os.makedirs(log_dir, exist_ok=True) # Stellen Sie sicher, dass der Ordner existiert

    log_file_path = os.path.join(log_dir, "shadow_control.log")
    
    # Erstellen Sie einen RotatingFileHandler
    file_handler = RotatingFileHandler(
        filename=log_file_path,
        maxBytes=10485760, # 10 MB
        backupCount=5,
        encoding='utf-8' # Wichtig für Umlaute etc.
    )

    # Definieren Sie das Format für die Log-Meldungen
    formatter = logging.Formatter('%(asctime)s %(levelname)s (%(threadName)s) [%(name)s] %(message)s')
    file_handler.setFormatter(formatter)

    # Setzen Sie das Log-Level für diesen Handler
    file_handler.setLevel(logging.DEBUG) # DEBUG, um alle Meldungen aufzufangen

    # Fügen Sie den Handler zu Ihrem spezifischen Logger hinzu.
    # HINWEIS: Wir fügen ihn dem ROOT-LOGGER der Komponente hinzu ('custom_components.shadow_control').
    # Standardmässig propagieren Nachrichten von Sub-Loggern (wie 'custom_components.shadow_control.shadow_control')
    # zu ihren Parent-Loggern. So erhalten Sie alle Logs in einer Datei.
    target_logger = logging.getLogger("custom_components.shadow_control")
    target_logger.addHandler(file_handler)

    _LOGGER.debug(f"Configured separate logfile for Shadow Control at: {log_file_path}")
    # === ENDE DER LOGFILE-KONFIGURATION ===

    return True
