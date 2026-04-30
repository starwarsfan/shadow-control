"""Tests for the own logfile feature (OWN_LOGFILE_ENABLED option)."""

import logging
import logging.handlers
import re
from pathlib import Path

import pytest
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.shadow_control.const import (
    DEBUG_ENABLED,
    DOMAIN,
    OWN_LOGFILE_ENABLED,
    SC_CONF_NAME,
    TARGET_COVER_ENTITY,
)

_INSTANCE_NAME = "Test Shadow Control"
_SANITIZED_NAME = "test_shadow_control"
_LOGGER_NAME = f"{DOMAIN}.{_SANITIZED_NAME}"


@pytest.fixture
def entry_with_logfile() -> MockConfigEntry:
    """Config entry with own logfile enabled."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={SC_CONF_NAME: _INSTANCE_NAME},
        options={
            TARGET_COVER_ENTITY: ["cover.test_cover"],
            OWN_LOGFILE_ENABLED: True,
        },
        entry_id="logfile_test_entry_id",
        title=_INSTANCE_NAME,
        version=5,
    )


def _file_handlers(logger_name: str) -> list[logging.handlers.RotatingFileHandler]:
    """Return all RotatingFileHandlers attached to the named logger."""
    return [h for h in logging.getLogger(logger_name).handlers if isinstance(h, logging.handlers.RotatingFileHandler)]


async def test_handler_added_when_enabled(
    hass: HomeAssistant,
    mock_cover,
    mock_sun,
    entry_with_logfile: MockConfigEntry,
) -> None:
    """A RotatingFileHandler is attached to the instance logger when the option is enabled."""
    entry_with_logfile.add_to_hass(hass)
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    await hass.async_block_till_done()

    assert await hass.config_entries.async_setup(entry_with_logfile.entry_id)
    await hass.async_block_till_done()

    assert len(_file_handlers(_LOGGER_NAME)) == 1

    await hass.config_entries.async_unload(entry_with_logfile.entry_id)
    await hass.async_block_till_done()


async def test_handler_not_added_when_disabled(
    hass: HomeAssistant,
    mock_cover,
    mock_sun,
    mock_config_entry: MockConfigEntry,
) -> None:
    """No RotatingFileHandler is attached when the option is False (the default)."""
    mock_config_entry.add_to_hass(hass)
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    await hass.async_block_till_done()

    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert len(_file_handlers(_LOGGER_NAME)) == 0

    await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()


async def test_logfile_path(
    hass: HomeAssistant,
    mock_cover,
    mock_sun,
    entry_with_logfile: MockConfigEntry,
) -> None:
    """The log file is placed in the HA config directory and named after the sanitized instance name."""
    entry_with_logfile.add_to_hass(hass)
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    await hass.async_block_till_done()

    assert await hass.config_entries.async_setup(entry_with_logfile.entry_id)
    await hass.async_block_till_done()

    handler = _file_handlers(_LOGGER_NAME)[0]
    log_path = Path(handler.baseFilename)

    assert log_path.parent == Path(hass.config.config_dir)
    assert log_path.name == f"shadow_control_{_SANITIZED_NAME}.log"

    await hass.config_entries.async_unload(entry_with_logfile.entry_id)
    await hass.async_block_till_done()


async def test_handler_closed_on_unload(
    hass: HomeAssistant,
    mock_cover,
    mock_sun,
    entry_with_logfile: MockConfigEntry,
) -> None:
    """The RotatingFileHandler is closed and removed from the logger on unload."""
    entry_with_logfile.add_to_hass(hass)
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    await hass.async_block_till_done()

    assert await hass.config_entries.async_setup(entry_with_logfile.entry_id)
    await hass.async_block_till_done()

    assert len(_file_handlers(_LOGGER_NAME)) == 1

    assert await hass.config_entries.async_unload(entry_with_logfile.entry_id)
    await hass.async_block_till_done()

    assert len(_file_handlers(_LOGGER_NAME)) == 0


async def test_no_duplicate_handlers_on_reload(
    hass: HomeAssistant,
    mock_cover,
    mock_sun,
    entry_with_logfile: MockConfigEntry,
) -> None:
    """Reloading the entry does not leave duplicate file handlers."""
    entry_with_logfile.add_to_hass(hass)
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    await hass.async_block_till_done()

    assert await hass.config_entries.async_setup(entry_with_logfile.entry_id)
    await hass.async_block_till_done()

    await hass.config_entries.async_reload(entry_with_logfile.entry_id)
    await hass.async_block_till_done()

    assert len(_file_handlers(_LOGGER_NAME)) == 1

    await hass.config_entries.async_unload(entry_with_logfile.entry_id)
    await hass.async_block_till_done()


def _read_logfile(handler: logging.handlers.RotatingFileHandler) -> str:
    """Flush and read the full content of the handler's log file."""
    handler.flush()
    return Path(handler.baseFilename).read_text(encoding="utf-8")


async def test_message_written_to_file(
    hass: HomeAssistant,
    mock_cover,
    mock_sun,
    entry_with_logfile: MockConfigEntry,
) -> None:
    """A log message emitted via the instance logger appears in the logfile."""
    entry_with_logfile.add_to_hass(hass)
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    await hass.async_block_till_done()

    assert await hass.config_entries.async_setup(entry_with_logfile.entry_id)
    await hass.async_block_till_done()

    sentinel = "logfile-content-test-sentinel-42"
    logging.getLogger(_LOGGER_NAME).info(sentinel)

    content = _read_logfile(_file_handlers(_LOGGER_NAME)[0])

    assert sentinel in content

    await hass.config_entries.async_unload(entry_with_logfile.entry_id)
    await hass.async_block_till_done()


async def test_logfile_format(
    hass: HomeAssistant,
    mock_cover,
    mock_sun,
    entry_with_logfile: MockConfigEntry,
) -> None:
    """Each line follows the expected format: timestamp  LEVEL     logger — message."""
    entry_with_logfile.add_to_hass(hass)
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    await hass.async_block_till_done()

    assert await hass.config_entries.async_setup(entry_with_logfile.entry_id)
    await hass.async_block_till_done()

    sentinel = "format-check-sentinel"
    logging.getLogger(_LOGGER_NAME).info(sentinel)

    content = _read_logfile(_file_handlers(_LOGGER_NAME)[0])

    # Find the sentinel line and validate every field.
    sentinel_line = next(line for line in content.splitlines() if sentinel in line)

    # Timestamp:  2025-01-30 14:05:32,123
    assert re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}", sentinel_line)
    # Level padded to 8 chars:  INFO
    assert "INFO    " in sentinel_line
    # Logger name
    assert _LOGGER_NAME in sentinel_line
    # Em-dash separator
    assert "—" in sentinel_line
    # The message itself
    assert sentinel in sentinel_line

    await hass.config_entries.async_unload(entry_with_logfile.entry_id)
    await hass.async_block_till_done()


async def test_debug_messages_excluded_at_info_level(
    hass: HomeAssistant,
    mock_cover,
    mock_sun,
    entry_with_logfile: MockConfigEntry,
) -> None:
    """DEBUG messages do not appear in the file when debug_enabled is False."""
    entry_with_logfile.add_to_hass(hass)
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    await hass.async_block_till_done()

    assert await hass.config_entries.async_setup(entry_with_logfile.entry_id)
    await hass.async_block_till_done()

    debug_sentinel = "debug-should-not-appear"
    info_sentinel = "info-should-appear"
    logger = logging.getLogger(_LOGGER_NAME)
    logger.debug(debug_sentinel)
    logger.info(info_sentinel)

    content = _read_logfile(_file_handlers(_LOGGER_NAME)[0])

    assert info_sentinel in content
    assert debug_sentinel not in content

    await hass.config_entries.async_unload(entry_with_logfile.entry_id)
    await hass.async_block_till_done()


async def test_debug_messages_appear_when_debug_enabled(
    hass: HomeAssistant,
    mock_cover,
    mock_sun,
) -> None:
    """DEBUG messages appear in the file when both debug_enabled and own_logfile_enabled are True."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={SC_CONF_NAME: _INSTANCE_NAME},
        options={
            TARGET_COVER_ENTITY: ["cover.test_cover"],
            DEBUG_ENABLED: True,
            OWN_LOGFILE_ENABLED: True,
        },
        entry_id="logfile_debug_entry_id",
        title=_INSTANCE_NAME,
        version=5,
    )
    entry.add_to_hass(hass)
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    await hass.async_block_till_done()

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    debug_sentinel = "debug-should-appear-in-file"
    logging.getLogger(_LOGGER_NAME).debug(debug_sentinel)

    content = _read_logfile(_file_handlers(_LOGGER_NAME)[0])

    assert debug_sentinel in content
    assert "DEBUG   " in content

    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_rotation_config(
    hass: HomeAssistant,
    mock_cover,
    mock_sun,
    entry_with_logfile: MockConfigEntry,
) -> None:
    """The handler is configured with the expected rotation parameters."""
    entry_with_logfile.add_to_hass(hass)
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    await hass.async_block_till_done()

    assert await hass.config_entries.async_setup(entry_with_logfile.entry_id)
    await hass.async_block_till_done()

    handler = _file_handlers(_LOGGER_NAME)[0]

    assert handler.maxBytes == 5 * 1024 * 1024
    assert handler.backupCount == 3

    await hass.config_entries.async_unload(entry_with_logfile.entry_id)
    await hass.async_block_till_done()
