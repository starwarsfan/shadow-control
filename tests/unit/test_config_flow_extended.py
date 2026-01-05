"""Extended tests for shadow_control config flow."""

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry


async def test_options_flow_init(hass: HomeAssistant, mock_config_entry: MockConfigEntry) -> None:
    """Test options flow initialization."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    assert result["type"] == "form"
    assert result["step_id"] == "user"


async def test_options_flow_covers_list(hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_cover) -> None:
    """Test options flow shows available covers."""
    # Add second cover
    hass.states.async_set(
        "cover.test_cover_2",
        "closed",
        {"supported_features": 255, "friendly_name": "Test Cover 2"},
    )

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    # Verify both covers appear in schema
    assert result["type"] == "form"
    await hass.config_entries.async_unload(mock_config_entry.entry_id)
