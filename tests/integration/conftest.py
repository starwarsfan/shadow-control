"""Fixtures für Integration Tests."""

import contextlib
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
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed, async_mock_service

from custom_components.shadow_control.const import DOMAIN, SC_CONF_NAME, SCInternal

_LOGGER = logging.getLogger(__name__)


class SelectiveColoredFormatter(ColoredFormatter):
    """Formatter, der nur für Test-Files Farben anwendet."""

    def format(self, record):
        # Wenn der Log aus der Integration kommt, Farben entfernen
        if "shadow_control" in record.name:
            neutral_formatter = logging.Formatter(fmt="%(levelname)-8s %(filename)30s: %(lineno)4s %(message)s", datefmt="%H:%M:%S")
            return neutral_formatter.format(record)

        # Ansonsten: Standard colorlog Verhalten (für Tests)
        return super().format(record)


@pytest.fixture(autouse=True, scope="session")
def setup_logging():
    # color_format = "%(log_color)s%(levelname)-8s%(reset)s %(cyan)s%(filename)-25s:%(lineno)-4s%(reset)s %(blue)s%(message)s%(reset)s"
    color_format = "%(log_color)s%(levelname)-8s%(reset)s %(cyan)s%(filename)30s: %(lineno)4s %(message)s%(reset)s"

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

    # Entferne duplizierte Handler, behalte nur pytest's Handler
    seen_handler_types = {}
    unique_handlers = []

    for handler in root_logger.handlers:
        handler_type = type(handler).__name__

        # Behalte nur pytest-spezifische Handler
        if handler_type in ("_LiveLoggingStreamHandler", "_FileHandler", "LogCaptureHandler"):
            # Für LogCaptureHandler: nur den ersten behalten
            if handler_type == "LogCaptureHandler" and handler_type in seen_handler_types:
                continue  # Skip duplizierte LogCaptureHandler

            seen_handler_types[handler_type] = True
            handler.setFormatter(formatter)
            handler.setLevel(logging.DEBUG)
            unique_handlers.append(handler)

    root_logger.handlers = unique_handlers
    root_logger.setLevel(logging.DEBUG)


#    print("\n=== ROOT LOGGER HANDLERS ===")
#    for i, handler in enumerate(root_logger.handlers):
#        print(f"Handler {i}: {type(handler).__name__}, Level: {handler.level} ({logging.getLevelName(handler.level)})")
#        print(f"  Formatter: {type(handler.formatter).__name__ if handler.formatter else None}")
#    print("=== END HANDLERS ===\n")


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

        # Entferne "name" aus options, da es in data ist
        options_dict.pop("name", None)

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
                "initial": 100,  # Full HA-open
                "name": "Cover Position",
            },
            "cover_tilt_position": {
                "min": 0,
                "max": 100,
                "initial": 100,  # Full HA-open
                "name": "Cover Tilt Position",
            },
            "d01_brightness": {
                "min": 0,
                "max": 100000,
                "initial": 20000,
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
def time_travel(hass: HomeAssistant, freezer):
    """Fixture zum Zeitsprung für Timer-Tests.

    Diese Fixture funktioniert mit async_track_point_in_utc_time und async_call_later Timern.

    Args:
        hass: Home Assistant instance
        freezer: pytest-freezegun freezer fixture
    """

    async def _travel(*, seconds: int = 0, minutes: int = 0, hours: int = 0):
        """Spring in der Zeit vorwärts."""
        delta = timedelta(seconds=seconds, minutes=minutes, hours=hours)
        # total_seconds = delta.total_seconds()
        # logging.getLogger().info("Time traveling %s seconds...", total_seconds)

        # Berechne Zielzeit
        target_time = dt_util.utcnow() + delta

        # Bewege freezegun Zeit
        freezer.move_to(target_time)

        # Wichtig: async_fire_time_changed triggert HA Timer
        async_fire_time_changed(hass, target_time)

        # Gib HA Zeit alle Timer-Callbacks zu verarbeiten
        await hass.async_block_till_done()

        # Manchmal braucht es mehrere Durchläufe
        await hass.async_block_till_done()
        await hass.async_block_till_done()

    return _travel


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


def get_cover_position(pos_calls, tilt_calls) -> tuple[str, str]:
    """Get formatted height/angle for display.

    Args:
        pos_calls: List of ServiceCall objects for cover.set_cover_position
        tilt_calls: List of ServiceCall objects for cover.set_cover_tilt_position

    Returns:
        Tuple of (height, angle) as strings
    """
    if not pos_calls and not tilt_calls:
        return "N/A", "N/A"

    # ServiceCall.data enthält die Parameter
    height = str(pos_calls[-1].data.get("position", "N/A")) if pos_calls else "N/A"
    angle = str(tilt_calls[-1].data.get("tilt_position", "N/A")) if tilt_calls else "N/A"

    return height, angle


def log_cover_position(pos_calls, tilt_calls):
    """Log current cover position and tilt angle.

    Args:
        pos_calls: List of position service calls
        tilt_calls: List of tilt service calls
    """
    height, angle = get_cover_position(pos_calls, tilt_calls)
    _LOGGER.info("Height/Angle: %s/%s", height, angle)


async def simulate_manual_cover_change(
    hass: HomeAssistant, entity_id: str, *, position: float | None = None, tilt_position: float | None = None
) -> None:
    """Simulate manual cover movement (external change).

    This sets the cover state directly to simulate user intervention,
    which should trigger auto-lock in Shadow Control.

    Args:
        hass: Home Assistant instance
        entity_id: Cover entity ID (e.g., "cover.sc_dummy")
        position: New height position 0-100 (optional)
        tilt_position: New tilt/angle position 0-100 (optional)
    """
    current_state = hass.states.get(entity_id)
    if not current_state:
        _LOGGER.warning("Cover entity %s not found", entity_id)
        return

    # Kopiere aktuelle Attribute
    new_attributes = dict(current_state.attributes)

    # Aktualisiere Position(en)
    if position is not None:
        new_attributes["current_position"] = int(position)
        _LOGGER.info("Simulating manual height change: %s -> %s%%", entity_id, position)

    if tilt_position is not None:
        new_attributes["current_tilt_position"] = int(tilt_position)
        _LOGGER.info("Simulating manual tilt change: %s -> %s%%", entity_id, tilt_position)

    # Setze neuen State (triggert state_changed Event)
    hass.states.async_set(entity_id, current_state.state, new_attributes)
    await hass.async_block_till_done()

    # Gib der Integration Zeit zu reagieren
    await hass.async_block_till_done()


async def time_travel_and_check(
    time_travel_func,
    hass: HomeAssistant,
    entity_id: str,
    *,
    seconds: int = 0,
    minutes: int = 0,
    hours: int = 0,
    pos_calls=None,
    tilt_calls=None,
    with_attributes: bool = False,
    executions: int = 1,
) -> State:
    """Time travel and return entity state.

    Logs only at start, on state changes, and at end to reduce output.

    Args:
        time_travel_func: The time_travel fixture function
        hass: Home Assistant instance
        entity_id: Entity ID to check
        seconds: Seconds to travel per execution
        minutes: Minutes to travel per execution
        hours: Hours to travel per execution
        pos_calls: Optional position calls list to log
        tilt_calls: Optional tilt calls list to log
        with_attributes: Include attributes in log
        executions: Number of times to execute the time travel (default: 1)

    Returns:
        State object of the entity after the last execution
    """

    def get_current_state_info():
        """Get current state and position info."""
        state = hass.states.get(entity_id)
        if pos_calls is not None and tilt_calls is not None:
            height, angle = get_cover_position(pos_calls, tilt_calls)
            return state, height, angle
        return state, None, None

    def log_state(state, height, angle, prefix=""):
        """Log state with optional position info."""
        if height is not None and angle is not None:
            if with_attributes:
                _LOGGER.info(
                    "%-12s → Height/Angle: %-12s %s: %s, Attributes: %s", prefix, f"{height}/{angle},", entity_id, state.state, state.attributes
                )
            else:
                _LOGGER.info("%-12s → Height/Angle: %-12s %s: %s", prefix, f"{height}/{angle},", entity_id, state.state)
        elif with_attributes:
            _LOGGER.info("%-12s → %s: %s, Attributes: %s", prefix, entity_id, state.state, state.attributes)
        else:
            _LOGGER.info("%-12s → %s: %s", prefix, entity_id, state.state)

    # 1. Initial state
    state, height, angle = get_current_state_info()
    log_state(state, height, angle, "Initial")
    previous_state_value = state.state

    total_seconds_traveled = 0
    seconds_per_iteration = seconds + (minutes * 60) + (hours * 3600)

    # 2-4. Time travel loop
    for i in range(executions):
        # Time travel (silent)
        await time_travel_func(seconds=seconds, minutes=minutes, hours=hours)
        total_seconds_traveled += seconds_per_iteration

        # Check new state
        state, height, angle = get_current_state_info()

        # Log only on state change or last iteration
        if state.state != previous_state_value:
            log_state(state, height, angle, f"After {total_seconds_traveled}s")
            previous_state_value = state.state
        elif i == executions - 1:
            # Last iteration: always log
            log_state(state, height, angle, f"Final ({total_seconds_traveled}s)")

    return state


async def set_entity_state(hass: HomeAssistant, entity_id: str, value: str | float | bool, attributes: dict | None = None) -> None:
    """Set entity state by calling appropriate service.

    This triggers state change events that integrations can listen to.

    Args:
        hass: Home Assistant instance
        entity_id: Entity ID to set
        value: New value (state for switches, numeric value for numbers, etc.)
        attributes: Optional attributes dict (currently not used)
    """
    domain = entity_id.split(".")[0]

    if domain == "switch":
        # Switches: turn_on/turn_off
        service = "turn_on" if value in (True, "on", "ON") else "turn_off"
        _LOGGER.info("Calling %s.%s for %s (value: %s)", domain, service, entity_id, value)
        await hass.services.async_call(domain, service, {"entity_id": entity_id}, blocking=True)

    elif domain in ("number", "input_number"):
        # Numbers: set_value
        _LOGGER.info("Set %s = %s", entity_id, value)
        await hass.services.async_call(domain, "set_value", {"entity_id": entity_id, "value": float(value)}, blocking=True)

    elif domain == "input_boolean":
        # Input booleans: turn_on/turn_off
        service = "turn_on" if value in (True, "on", "ON") else "turn_off"
        _LOGGER.info("Called %s.%s for %s", domain, service, entity_id)
        await hass.services.async_call(domain, service, {"entity_id": entity_id}, blocking=True)

    elif domain == "select":
        # Select: select_option
        _LOGGER.info("Set %s = %s", entity_id, value)
        await hass.services.async_call(domain, "select_option", {"entity_id": entity_id, "option": str(value)}, blocking=True)

    else:
        # Fallback: Direktes State-Setting (für Sensoren etc.)
        _LOGGER.warning("No service mapping for domain '%s', using direct state setting for %s", domain, entity_id)
        hass.states.async_set(entity_id, value, attributes or {})

    await hass.async_block_till_done()
    await hass.async_block_till_done()  # Zweimal für async Updates


async def set_lock_state(
    hass: HomeAssistant,
    instance_name: str,
    *,
    lock: bool | None = None,
    lock_with_position: bool | None = None,
    lock_height: float | None = None,
    lock_angle: float | None = None,
) -> None:
    """Set lock-related entities for a Shadow Control instance.

    Args:
        hass: Home Assistant instance
        instance_name: Instance name (e.g., "sc_test_instance")
        lock: Simple lock state (on/off)
        lock_with_position: Lock with forced position (on/off)
        lock_height: Forced height position (0-100)
        lock_angle: Forced angle position (0-100)
    """
    if lock is not None:
        await set_entity_state(hass, f"switch.{instance_name}_lock", lock)

    if lock_with_position is not None:
        await set_entity_state(hass, f"switch.{instance_name}_lock_with_position", lock_with_position)

    if lock_height is not None:
        await set_entity_state(hass, f"number.{instance_name}_zwangsposition_hohe", lock_height)

    if lock_angle is not None:
        await set_entity_state(hass, f"number.{instance_name}_zwangsposition_lamellenwinkel", lock_angle)


async def set_sun_position(
    hass: HomeAssistant, *, elevation: float | None = None, azimuth: float | None = None, brightness: float | None = None
) -> None:
    """Set sun position and brightness for testing.

    Args:
        hass: Home Assistant instance
        elevation: Sun elevation in degrees
        azimuth: Sun azimuth in degrees
        brightness: Brightness in lux
    """
    if elevation is not None:
        await set_entity_state(hass, "input_number.d03_sun_elevation", str(elevation))

    if azimuth is not None:
        await set_entity_state(hass, "input_number.d04_sun_azimuth", str(azimuth))

    if brightness is not None:
        await set_entity_state(hass, "input_number.d01_brightness", str(brightness))


def assert_equal(actual, expected, context: str = "Value") -> None:
    """Assert that actual equals expected with readable error message.

    Handles Enums automatically by comparing .value or .name attributes.
    Handles numeric comparisons (int, float, string) flexibly.

    Args:
        actual: Actual value (can be string, int, float, enum, etc.)
        expected: Expected value (can be string, int, float, enum, etc.)
        context: Context for error message (e.g., "Lock state", "Height")
    """
    # Handle Enums
    expected_val = expected.value if hasattr(expected, "value") else expected
    expected_name = expected.name if hasattr(expected, "name") else str(expected)
    actual_val = actual.value if hasattr(actual, "value") else actual

    # Special handling for Enums: try matching by name OR value
    if hasattr(expected, "value") and hasattr(expected, "name") and isinstance(actual_val, str):
        # Expected is an Enum - try matching actual against both name and value
        # Try matching by name (case-insensitive and with underscores)
        if actual_val.lower() == expected_name.lower():
            actual_val = expected_val  # Match found via name
        elif actual_val.replace("_", "").lower() == expected_name.replace("_", "").lower():
            actual_val = expected_val  # Match found via normalized name
        else:
            # Try numeric conversion as fallback
            with contextlib.suppress(ValueError, TypeError):
                actual_val = int(actual_val)

    # Try numeric comparison (handles "100" vs "100.0" vs 100 vs 100.0)
    with contextlib.suppress(ValueError, TypeError):
        expected_num = float(expected_val)
        actual_num = float(actual_val)
        expected_val = expected_num
        actual_val = actual_num

    assert actual_val == expected_val, f"{context} should be {expected_name} ({expected_val}), but is {actual_val}"

    # Bei Erfolg: Log it!
    _LOGGER.info("✓ %s is %s (%s)", context, expected_name, expected_val)


def assert_not_equal(actual, expected, context: str = "Value") -> None:
    """Assert that actual does NOT equal expected with readable error message.

    Handles Enums automatically by comparing .value or .name attributes.
    Handles numeric comparisons (int, float, string) flexibly.

    Args:
        actual: Actual value (can be string, int, float, enum, etc.)
        expected: Expected value (can be string, int, float, enum, etc.)
        context: Context for error message (e.g., "Lock state", "Height")
    """
    # Handle Enums
    expected_val = expected.value if hasattr(expected, "value") else expected
    expected_name = expected.name if hasattr(expected, "name") else str(expected)
    actual_val = actual.value if hasattr(actual, "value") else actual

    # Special handling for Enums: try matching by name OR value
    if hasattr(expected, "value") and hasattr(expected, "name") and isinstance(actual_val, str):
        # Expected is an Enum - try matching actual against both name and value
        # Try matching by name (case-insensitive and with underscores)
        if actual_val.lower() == expected_name.lower():
            actual_val = expected_val  # Match found via name
        elif actual_val.replace("_", "").lower() == expected_name.replace("_", "").lower():
            actual_val = expected_val  # Match found via normalized name
        else:
            # Try numeric conversion as fallback
            with contextlib.suppress(ValueError, TypeError):
                actual_val = int(actual_val)

    # Try numeric comparison (handles "100" vs "100.0" vs 100 vs 100.0)
    with contextlib.suppress(ValueError, TypeError):
        expected_num = float(expected_val)
        actual_num = float(actual_val)
        expected_val = expected_num
        actual_val = actual_num

    assert actual_val != expected_val, f"{context} should NOT be {expected_name} ({expected_val}), but it is"

    # Bei Erfolg: Log it!
    _LOGGER.info("✓ %s is NOT %s (%s), actual: %s", context, expected_name, expected_val, actual_val)


async def set_internal_entity(hass: HomeAssistant, instance_name: str, internal_enum: SCInternal, value: str | float | bool | None = None) -> None:
    """Set internal SC entity value using registry lookup.

    This automatically finds the correct entity ID regardless of translations.

    Args:
        hass: Home Assistant instance
        instance_name: SC instance name
        internal_enum: SCInternal enum value
        value: Value to set (not needed for buttons)

    Raises:
        ValueError: If entity cannot be found in registry
    """

    # Hole Domain vom Enum
    domain = internal_enum.domain

    # Suche Entity in der Registry
    registry = er.async_get(hass)

    entity_id = None
    for entity in registry.entities.values():
        # Prüfe: richtige Platform, Domain und unique_id enthält den enum value
        if (
            entity.platform == "shadow_control"
            and entity.domain == domain
            and internal_enum.value in entity.unique_id
            and instance_name.lower() in entity.entity_id.lower()
        ):
            entity_id = entity.entity_id
            _LOGGER.debug("Found entity %s for %s", entity_id, internal_enum.name)
            break

    if not entity_id:
        msg = f"Could not find entity for {internal_enum.name} (domain: {domain}, instance: {instance_name}) in registry"
        raise ValueError(msg)

    if domain == "button":
        # Buttons werden gedrückt, kein value nötig
        await hass.services.async_call("button", "press", {"entity_id": entity_id}, blocking=True)
        _LOGGER.info("Pressed button: %s", entity_id)
    else:
        # Für Switch, Number, Select: Nutze set_entity_state
        await set_entity_state(hass, entity_id, value)

    await hass.async_block_till_done()
