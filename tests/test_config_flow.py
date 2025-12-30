"""Test the Shadow Control config flow."""

from homeassistant import config_entries, data_entry_flow
from homeassistant.core import HomeAssistant

from custom_components.shadow_control.const import DOMAIN


async def test_form(hass: HomeAssistant) -> None:
    """Test we get the user form."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {}
    assert result["step_id"] == "user"


async def test_options_flow(hass: HomeAssistant, mock_config_entry, mock_cover, mock_sun) -> None:
    """Test options flow."""
    mock_config_entry.add_to_hass(hass)

    # Setup entry first
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Initiate options flow
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    # Shadow Control sollte einen Options Flow haben
    assert result["type"] == data_entry_flow.FlowResultType.FORM
