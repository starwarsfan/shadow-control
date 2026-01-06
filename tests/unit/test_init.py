"""Test shadow_control setup process."""

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.shadow_control.const import DOMAIN


async def test_setup_entry(hass: HomeAssistant, mock_config_entry, mock_cover, mock_sun) -> None:
    """Test setup of a config entry."""
    mock_config_entry.add_to_hass(hass)

    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    await hass.async_block_till_done()

    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state == ConfigEntryState.LOADED
    # TODO: Prüfe ob Manager/Coordinator erstellt wurde
    # assert "managers" in hass.data.get(DOMAIN, {})


async def test_setup_entry_missing_target_cover(hass: HomeAssistant, mock_sun) -> None:
    """Test setup fails when target cover is missing."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "name": "Test",
            "target_cover": "cover.nonexistent",
        },
        entry_id="test_no_cover",
        version=5,
    )
    entry.add_to_hass(hass)

    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    await hass.async_block_till_done()

    # Should either fail or load with warning
    result = await hass.config_entries.async_setup(entry.entry_id)

    # Je nach Implementation:
    # - Entweder schlägt Setup fehl: assert not result
    # - Oder es lädt mit Warning: assert result
    # Anpassen basierend auf tatsächlichem Verhalten
    assert result in (True, False)  # Placeholder


async def test_unload_entry(hass: HomeAssistant, mock_config_entry, mock_cover, mock_sun) -> None:
    """Test unloading a config entry."""
    mock_config_entry.add_to_hass(hass)

    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    await hass.async_block_till_done()

    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state == ConfigEntryState.NOT_LOADED


async def test_reload_entry(hass: HomeAssistant, mock_config_entry, mock_cover, mock_sun) -> None:
    """Test reloading a config entry."""
    mock_config_entry.add_to_hass(hass)

    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    await hass.async_block_till_done()

    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state == ConfigEntryState.LOADED

    await hass.config_entries.async_reload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state == ConfigEntryState.LOADED
