"""Test shadow_control entities."""

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry


async def test_sensor_entities_created(hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_cover, mock_sun) -> None:
    """Test all sensor entities are created."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Check expected sensors exist
    expected_sensors = [
        "sensor.test_shadow_control_height",
        "sensor.test_shadow_control_angle",
        "sensor.test_shadow_control_state",
        # ... add all expected sensor entity_ids
    ]

    for sensor_id in expected_sensors:
        state = hass.states.get(sensor_id)
        assert state is not None, f"Sensor {sensor_id} not found"


async def test_button_entity_press(hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_cover, mock_sun) -> None:
    """Test button entity can be pressed."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Press the button
    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": "button.test_shadow_control_do_positioning"},
        blocking=True,
    )

    # Verify button was pressed (add appropriate assertions based on behavior)


async def test_switch_entity_toggle(hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_cover, mock_sun) -> None:
    """Test switch entity can be toggled."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Toggle the switch
    await hass.services.async_call(
        "switch",
        "turn_on",
        {"entity_id": "switch.test_shadow_control_lock"},
        blocking=True,
    )

    state = hass.states.get("switch.test_shadow_control_lock")
    assert state.state == "on"
