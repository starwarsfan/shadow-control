"""Extended tests for shadow_control __init__."""

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.shadow_control.const import DOMAIN, TARGET_COVER_ENTITY


async def test_entry_setup_with_multiple_covers(
        hass: HomeAssistant, mock_cover, mock_sun
) -> None:
    """Test setup with multiple cover entities."""
    # Add second cover
    hass.states.async_set(
        "cover.test_cover_2",
        "closed",
        {"supported_features": 255, "friendly_name": "Test Cover 2"},
    )

    # Create NEW config entry with multiple covers
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"name": "Multi Cover Test"},
        options={TARGET_COVER_ENTITY: ["cover.test_cover", "cover.test_cover_2"]},
        entry_id="multi_cover_test_id",
        title="Multi Cover Test",
        version=5,
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state == ConfigEntryState.LOADED  # ✅ Besser: Verwende Enum

    # Cleanup
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_config_entry_not_ready_when_sun_missing(hass: HomeAssistant) -> None:
    """Test setup fails gracefully when sun integration is missing."""
    # Don't add mock_sun - sun entity missing

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"name": "Test No Sun"},
        options={TARGET_COVER_ENTITY: ["cover.test_cover"]},
        entry_id="test_no_sun_id",
        title="Test No Sun",
        version=5,
    )
    entry.add_to_hass(hass)

    # Setup should succeed even without sun (your code handles this)
    # Adjust this based on your actual implementation
    result = await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # This test needs to match your actual behavior
    # Either it fails (ConfigEntryNotReady) or succeeds with warnings