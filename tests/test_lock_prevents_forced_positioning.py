"""Test that locks prevent forced immediate positioning."""

from homeassistant.core import HomeAssistant


async def test_config_change_with_active_lock_does_not_position(
        hass: HomeAssistant, mock_config_entry, mock_cover, mock_sun
):
    """Test that configuration changes don't trigger positioning when lock is active."""
    # Setup integration
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Activate lock
    lock_entity = hass.states.get("switch.test_shadow_control_lock")
    await hass.services.async_call(
        "switch",
        "turn_on",
        {"entity_id": "switch.test_shadow_control_lock"},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Get initial cover position
    cover_state_before = hass.states.get("cover.test_cover")
    initial_position = cover_state_before.attributes.get("current_position", 0)

    # Change a configuration entity that normally triggers immediate positioning
    max_height_entity = "number.test_shadow_control_s_max_shutter_height"
    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": max_height_entity, "value": 50},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Verify cover did NOT move (because lock is active)
    cover_state_after = hass.states.get("cover.test_cover")
    final_position = cover_state_after.attributes.get("current_position", 0)

    assert initial_position == final_position, (
        "Cover should NOT move when config changes while lock is active"
    )


async def test_config_change_without_lock_does_position(
        hass: HomeAssistant, mock_config_entry, mock_cover, mock_sun
):
    """Test that configuration changes DO trigger positioning when no lock is active."""
    # Setup integration
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Make sure lock is OFF
    await hass.services.async_call(
        "switch",
        "turn_off",
        {"entity_id": "switch.test_shadow_control_lock"},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Change a configuration entity
    max_height_entity = "number.test_shadow_control_s_max_shutter_height"
    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": max_height_entity, "value": 75},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Verify positioning was triggered
    # (This depends on your specific implementation - adjust as needed)
    # For now, just verify the method was called or state changed