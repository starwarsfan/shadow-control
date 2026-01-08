"""Fixtures für Integration Tests."""

import logging
from datetime import timedelta
from typing import Any

import pytest
from colorlog import ColoredFormatter
from homeassistant.components.cover import (
    DOMAIN as COVER_DOMAIN,
)
from homeassistant.components.input_number import DOMAIN as INPUT_NUMBER_DOMAIN
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import HomeAssistant, State
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed, async_mock_service

from custom_components.shadow_control.const import DOMAIN, SC_CONF_NAME

_LOGGER = logging.getLogger(__name__)


class SelectiveColoredFormatter(ColoredFormatter):
    """Formatter, der nur für Test-Files Farben anwendet."""

    def format(self, record):
        # Wenn der Log aus der Integration kommt, Farben entfernen
        if record.name.startswith("custom_components"):
            # Speichere das Original-Format kurzzeitig
            original_format = self._style._fmt
            # Setze ein neutrales Format ohne Farben
            self._style._fmt = "%(levelname)-8s %(filename)-25s:%(lineno)-4s %(message)s"
            result = logging.Formatter.format(self, record)
            # Zurücksetzen auf das farbige Format
            self._style._fmt = original_format
            return result

        # Ansonsten: Standard colorlog Verhalten
        return super().format(record)


@pytest.fixture(autouse=True, scope="session")
def setup_logging():
    # color_format = "%(log_color)s%(levelname)-8s%(reset)s %(cyan)s%(filename)-25s:%(lineno)-4s%(reset)s %(blue)s%(message)s%(reset)s"
    color_format = "%(log_color)s%(levelname)-8s%(reset)s %(cyan)s%(filename)-25s:%(lineno)-4s %(message)s%(reset)s"

    formatter = SelectiveColoredFormatter(
        color_format,
        datefmt="%H:%M:%S",
        reset=True,
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bg_white",
        },
    )

    root_logger = logging.getLogger()

    # Vorhandene Pytest-Handler auf unseren neuen Formatter umstellen
    if root_logger.handlers:
        for handler in root_logger.handlers:
            handler.setFormatter(formatter)
    else:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    root_logger.setLevel(logging.INFO)


# ============================================================================
# Helper: Setup mit User-Config
# ============================================================================


@pytest.fixture
async def setup_from_user_config(hass: HomeAssistant, mock_minimal_entities):
    async def _setup(config: dict):
        raw_config = config[DOMAIN][0]
        instance_name = raw_config.get("name")

        # WICHTIG: Erstelle eine Kopie für options, damit das Original-Dict
        # im Test nicht manipuliert wird
        options_dict = dict(raw_config)

        entry = MockConfigEntry(
            domain=DOMAIN,
            title=instance_name,
            data={SC_CONF_NAME: instance_name},  # Nur Name in data
            options=options_dict,  # Alles inkl. sc_internal_values in options
            entry_id="test_entry_id",
            version=5,
        )
        entry.add_to_hass(hass)

        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        return entry

    return _setup


# ============================================================================
# Mock Entities (Minimal Setup)
# ============================================================================


@pytest.fixture
async def mock_minimal_entities(hass: HomeAssistant):
    """Erstelle minimale Entities die User-Configs erwarten."""

    # Input Numbers für Cover Position und andere Werte
    input_number_config = {
        INPUT_NUMBER_DOMAIN: {
            "cover_position": {
                "min": 0,
                "max": 100,
                "initial": 50,
                "name": "Cover Position",
            },
            "cover_tilt_position": {
                "min": 0,
                "max": 90,
                "initial": 45,
                "name": "Cover Tilt Position",
            },
            "d01_brightness": {
                "min": 0,
                "max": 100000,
                "initial": 50000,
                "name": "Brightness",
            },
            "d03_sun_elevation": {
                "min": -90,
                "max": 90,
                "initial": 45,
                "name": "Sun Elevation",
            },
            "d04_sun_azimuth": {
                "min": 0,
                "max": 360,
                "initial": 180,
                "name": "Sun Azimuth",
            },
        }
    }

    # Setup Input Numbers zuerst
    assert await async_setup_component(hass, INPUT_NUMBER_DOMAIN, input_number_config)
    await hass.async_block_till_done()

    # Setup Cover mit Template Platform
    cover_config = {
        COVER_DOMAIN: [
            {
                "platform": "template",
                "covers": {
                    "sc_dummy": {
                        "friendly_name": "SC Dummy",
                        "device_class": "shutter",
                        "position_template": "{{ states('input_number.cover_position') | int(50) }}",
                        "open_cover": {
                            "service": "input_number.set_value",
                            "target": {"entity_id": "input_number.cover_position"},
                            "data": {"value": 100},
                        },
                        "close_cover": {
                            "service": "input_number.set_value",
                            "target": {"entity_id": "input_number.cover_position"},
                            "data": {"value": 0},
                        },
                        "set_cover_position": {
                            "service": "input_number.set_value",
                            "target": {"entity_id": "input_number.cover_position"},
                            "data": {"value": "{{ position }}"},
                        },
                        "set_cover_tilt_position": {
                            "service": "input_number.set_value",
                            "target": {"entity_id": "input_number.cover_tilt_position"},
                            "data": {"value": "{{ tilt_position }}"},
                        },
                    }
                },
            }
        ]
    }

    # Setup Cover Template
    assert await async_setup_component(hass, COVER_DOMAIN, cover_config)
    await hass.async_block_till_done()

    return {
        "cover": "cover.sc_dummy",
        "input_numbers": [
            "input_number.d01_brightness",
            "input_number.d03_sun_elevation",
            "input_number.d04_sun_azimuth",
        ],
    }


# ============================================================================
# Time Travel Helper
# ============================================================================


# Stelle sicher dass Integration Tests echte Timer verwenden
@pytest.fixture(autouse=True)
def use_real_timers():
    """Ensure integration tests use real timers, not mocks."""
    # Diese Fixture tut nichts, stellt aber sicher dass die
    # Unit Test Mocks hier nicht greifen
    return


@pytest.fixture
def time_travel(hass: HomeAssistant):
    """Fixture zum Zeitsprung für Timer-Tests.

    Diese Fixture funktioniert mit async_call_later Timern.
    """

    async def _travel(*, seconds: int = 0, minutes: int = 0, hours: int = 0):
        """Spring in der Zeit vorwärts."""
        logging.getLogger().info("Time traveling 6 seconds...")
        delta = timedelta(seconds=seconds, minutes=minutes, hours=hours)
        target_time = dt_util.utcnow() + delta

        # Wichtig: async_fire_time_changed triggert async_call_later Timer
        async_fire_time_changed(hass, target_time)

        # Gib HA Zeit alle Timer-Callbacks zu verarbeiten
        await hass.async_block_till_done()

        # Manchmal braucht es mehrere Durchläufe
        await hass.async_block_till_done()
        await hass.async_block_till_done()

    return _travel


@pytest.fixture
def fast_forward_timers(time_travel):
    """Auto-forwarde Timer basierend auf Config-Werten.

    Usage:
        # Timer in Config: shadow_after_seconds_manual: 5
        await fast_forward_timers("shadow_after_seconds")
        # Springt automatisch 6 Sekunden vor (Config-Wert + 1)
    """
    _config_cache = {}

    async def _fast_forward(timer_key: str, extra_seconds: int = 1):
        """Forward timer basierend auf Config."""
        # Hole Config-Wert (müsste aus der Integration gelesen werden)
        # Für jetzt: manuelle Mappings
        timer_mapping = {
            "shadow_after_seconds": "shadow_after_seconds_manual",
            "dawn_after_seconds": "dawn_after_seconds_manual",
            "shadow_look_through_seconds": "shadow_shutter_look_through_seconds_manual",
            "dawn_look_through_seconds": "dawn_shutter_look_through_seconds_manual",
            "shadow_open_seconds": "shadow_shutter_open_seconds_manual",
            "dawn_open_seconds": "dawn_shutter_open_seconds_manual",
            "max_movement_duration": "facade_max_movement_duration_static",
        }

        config_key = timer_mapping.get(timer_key, timer_key)

        # Hole Wert aus HA Data (falls gespeichert)
        # Fallback zu Standard-Werten
        timer_seconds = _config_cache.get(config_key, 5)

        await time_travel(seconds=timer_seconds + extra_seconds)

    # Helper um Config zu cachen
    def cache_config(config: dict):
        """Cache config values für Timer."""
        if DOMAIN in config:
            for instance in config[DOMAIN]:
                _config_cache.update(instance)

    _fast_forward.cache_config = cache_config

    return _fast_forward


# ============================================================================
# Helper: Update Sun Position
# ============================================================================


@pytest.fixture
def update_sun(hass: HomeAssistant):
    """Helper um Sonnenposition zu ändern.

    Usage:
        await update_sun(elevation=60, azimuth=180, brightness=70000)
    """

    async def _update(
        elevation: float,
        azimuth: float,
        brightness: float | None = None,
    ):
        """Update sun position via input_numbers."""
        await hass.services.async_call(
            "input_number",
            "set_value",
            {
                "entity_id": "input_number.d03_sun_elevation",
                "value": elevation,
            },
            blocking=True,
        )
        await hass.services.async_call(
            "input_number",
            "set_value",
            {
                "entity_id": "input_number.d04_sun_azimuth",
                "value": azimuth,
            },
            blocking=True,
        )

        if brightness is not None:
            await hass.services.async_call(
                "input_number",
                "set_value",
                {
                    "entity_id": "input_number.d01_brightness",
                    "value": brightness,
                },
                blocking=True,
            )

        await hass.async_block_till_done()

    return _update


async def setup_instance(caplog, hass: HomeAssistant, setup_from_user_config, test_config) -> tuple[Any, Any]:
    caplog.set_level(logging.DEBUG, logger="custom_components.shadow_control")

    await setup_from_user_config(test_config)
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    await hass.async_block_till_done()
    # Mocke die Cover-Dienste, damit das Dummy-Script gar nicht erst läuft
    tilt_calls = async_mock_service(hass, "cover", "set_cover_tilt_position")
    pos_calls = async_mock_service(hass, "cover", "set_cover_position")
    return pos_calls, tilt_calls


async def show_instance_entity_states(hass: HomeAssistant, i: int):
    # Zeige alle Shadow Control Entities
    states = hass.states.async_all()
    sc_entities = [s for s in states if "sc_test_instance" in s.entity_id]

    line = f" SHADOW CONTROL ENTITIES START (#{i}) ==="
    _LOGGER.info("%s%s", "=" * (80 - len(line)), line)
    for entity in sc_entities:
        # _LOGGER.info("%s: %s, Attributes: %s", entity.entity_id, entity.state, entity.attributes)
        _LOGGER.info("%s: %s", entity.entity_id, entity.state)
    line = f" SHADOW CONTROL ENTITIES END (#{i}) ==="
    _LOGGER.info("%s%s", "=" * (80 - len(line)), line)


async def get_entity_and_show_state(hass: HomeAssistant, entity_id: str, with_attributes: bool = False) -> State:
    """Get entity state and log it.

    Args:
        hass: Home Assistant instance
        entity_id: Entity ID to fetch
        with_attributes: If True, log attributes as well (default: False)

    Returns:
        State object of the entity
    """
    entity = hass.states.get(entity_id)
    if with_attributes:
        _LOGGER.info("State of %s: %s, Attributes: %s", entity_id, entity.state, entity.attributes)
    else:
        _LOGGER.info("State of %s: %s", entity_id, entity.state)
    return entity
