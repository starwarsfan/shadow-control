"""Global fixtures for shadow_control tests."""

# ============================================================================
# WINDOWS COMPATIBILITY: Mock fcntl module
# ============================================================================
import logging
import sys
from unittest.mock import AsyncMock, MagicMock

from custom_components.shadow_control import ShadowControlManager

if sys.platform == "win32":
    sys.modules["fcntl"] = MagicMock()
# ============================================================================

from collections.abc import Generator
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.shadow_control.const import (
    DEBUG_ENABLED,
    DOMAIN,
    SC_CONF_NAME,
    TARGET_COVER_ENTITY,
    ShutterState,
)

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable loading custom integrations in all tests."""
    return


@pytest.fixture(autouse=True, scope="session")
def configure_test_logging():
    """Configure logging to suppress sun integration errors."""

    # Create a custom filter
    class SunErrorFilter(logging.Filter):
        def filter(self, record):
            msg = record.getMessage()
            return not any(
                blocked in msg
                for blocked in [
                    "Error unloading entry Sun for sun",
                    "'NoneType' object has no attribute 'loop'",
                    "Error adding entity sensor.sun_",
                    "'Sun' object has no attribute",
                ]
            )

    # Add filter to relevant loggers
    sun_filter = SunErrorFilter()
    logging.getLogger().addFilter(sun_filter)
    logging.getLogger("homeassistant.config_entries").addFilter(sun_filter)
    logging.getLogger("homeassistant.components.sensor").addFilter(sun_filter)


@pytest.fixture(name="mock_cover")
def mock_cover_fixture(hass: HomeAssistant) -> str:
    """Mock a cover entity with full feature support."""
    hass.states.async_set(
        "cover.test_cover",
        "closed",
        {
            "current_position": 0,
            "current_tilt_position": 0,
            "supported_features": 255,
            "friendly_name": "Test Cover",
        },
    )
    return "cover.test_cover"


@pytest.fixture(name="mock_sun")
def mock_sun_fixture(hass: HomeAssistant) -> str:
    """Mock sun entity for sun position calculations."""
    # Create a simple state with only the attributes Shadow Control needs
    hass.states.async_set(
        "sun.sun",
        "above_horizon",
        {
            "azimuth": 180.0,
            "elevation": 45.0,
            "rising": False,
        },
    )
    return "sun.sun"


@pytest.fixture(name="mock_brightness_sensor")
def mock_brightness_sensor_fixture(hass: HomeAssistant) -> str:
    """Mock brightness sensor."""
    hass.states.async_set(
        "sensor.brightness",
        "50000",
        {
            "unit_of_measurement": "lx",
            "device_class": "illuminance",
        },
    )
    return "sensor.brightness"


@pytest.fixture(name="mock_config_entry")
def mock_config_entry_fixture() -> MockConfigEntry:
    """Return a mock config entry with minimal configuration."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            SC_CONF_NAME: "Test Shadow Control",
            DEBUG_ENABLED: False,
        },
        options={
            TARGET_COVER_ENTITY: ["cover.test_cover"],
        },
        entry_id="test_entry_id",
        unique_id="test_unique_id",
        title="Test Shadow Control",
        version=5,
    )


@pytest.fixture(autouse=True)
def expected_lingering_tasks() -> bool:
    """Allow lingering tasks."""
    return True


@pytest.fixture(autouse=True)
def expected_lingering_timers() -> bool:
    """Allow lingering timers."""
    return True


@pytest.fixture(autouse=True)
def mock_async_track_time_interval() -> Generator[MagicMock]:
    """Mock async_track_time_interval to prevent timer issues in tests."""
    with patch("homeassistant.helpers.event.async_track_time_interval") as mock:
        mock.return_value = MagicMock()
        yield mock


@pytest.fixture(autouse=True)
def mock_async_track_state_change() -> Generator[MagicMock]:
    """Mock async_track_state_change_event to prevent state change listeners."""
    with patch("homeassistant.helpers.event.async_track_state_change_event") as mock:
        mock.return_value = MagicMock()
        yield mock


@pytest.fixture(autouse=True)
def mock_async_call_later() -> Generator[MagicMock]:
    """Mock async_call_later to prevent timer issues."""
    with patch("homeassistant.helpers.event.async_call_later") as mock:
        mock.return_value = MagicMock()
        yield mock


@pytest.fixture(name="mock_manager")
def mock_manager_fixture(hass: HomeAssistant) -> MagicMock:
    """Fixture to mock ShadowControlManager and its state handlers."""
    manager = MagicMock()
    manager.hass = hass
    manager.logger = MagicMock()
    manager.current_shutter_state = ShutterState.NEUTRAL

    # Mock internal methods used by the orchestrator
    manager._update_extra_state_attributes = MagicMock()
    manager._cancel_timer = MagicMock()

    # Create the state handlers dictionary with AsyncMocks for every state
    # We populate it with mocks that by default return the current state (no change)
    manager._state_handlers = {state: AsyncMock(return_value=state) for state in ShutterState}

    # Bind the real orchestrator logic to the mock instance
    manager._process_shutter_state = ShadowControlManager._process_shutter_state.__get__(manager)

    return manager
