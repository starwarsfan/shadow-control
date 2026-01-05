import asyncio
import logging

# Hier war der Fehler: async_setup_component kommt aus dem HA Core
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_mock_service

from custom_components.shadow_control.const import DOMAIN

_LOGGER = logging.getLogger(__name__)

TEST_CONFIG = {
    DOMAIN: [
        {
            "name": "SC Dummy",
            "debug_enabled": True,
            "target_cover_entity": ["cover.sc_dummy"],
            "facade_shutter_type_static": "mode1",
            #
            # Dynamic configuration inputs
            "brightness_entity": "input_number.d01_brightness",
            # "brightness_dawn_entity":
            "sun_elevation_entity": "input_number.d03_sun_elevation",
            "sun_azimuth_entity": "input_number.d04_sun_azimuth",
            "lock_integration_manual": False,
            # "lock_integration_entity": input_boolean.d07_lock_integration
            "lock_integration_with_position_manual": False,
            # "lock_integration_with_position_entity": input_boolean.d08_lock_integration_with_position
            "lock_height_manual": 50,
            # "lock_height_entity": input_number.lock_height_sc_dummy
            "lock_angle_manual": 50,
            # "lock_angle_entity": input_number.lock_angle_sc_dummy
            # no_restriction, only_open, only_close
            "movement_restriction_height_manual": "no_restriction",
            "movement_restriction_angle_manual": "no_restriction",
            # "movement_restriction_height_entity":
            # "movement_restriction_angle_entity":
            # "enforce_positioning_entity": input_boolean.d13_enforce_positioning
            #
            # General facade configuration
            "facade_azimuth_static": 200,
            "facade_offset_sun_in_static": -45,
            "facade_offset_sun_out_static": 45,
            "facade_elevation_sun_min_static": 23,
            "facade_elevation_sun_max_static": 80,
            "facade_slat_width_static": 60,
            "facade_slat_distance_static": 50,
            "facade_slat_angle_offset_static": 0,
            "facade_slat_min_angle_static": 0,
            "facade_shutter_stepping_height_static": 5,
            "facade_shutter_stepping_angle_static": 5,
            "facade_light_strip_width_static": 0,
            "facade_shutter_height_static": 1000,
            "facade_neutral_pos_height_manual": 0,
            # "facade_neutral_pos_height_entity": input_number.g15_neutral_pos_height
            "facade_neutral_pos_angle_manual": 0,
            # "facade_neutral_pos_angle_entity": input_number.g16_neutral_pos_angle
            "facade_max_movement_duration_static": 3,
            "facade_modification_tolerance_height_static": 3,
            "facade_modification_tolerance_angle_static": 3,
            #
            # Shadow configuration
            # "shadow_control_enabled_entity":
            "shadow_control_enabled_manual": True,
            # "shadow_brightness_threshold_entity":
            "shadow_brightness_threshold_manual": 50000,
            # "shadow_after_seconds_entity":
            "shadow_after_seconds_manual": 5,
            # "shadow_shutter_max_height_entity": input_number.automation_shadow_max_height_sc_dummy
            "shadow_shutter_max_height_manual": 90,
            # "shadow_shutter_max_angle_entity": input_number.automation_shadow_max_angle_sc_dummy
            "shadow_shutter_max_angle_manual": 90,
            # "shadow_shutter_look_through_seconds_entity":
            "shadow_shutter_look_through_seconds_manual": 5,
            # "shadow_shutter_open_seconds_entity":
            "shadow_shutter_open_seconds_manual": 5,
            # "shadow_shutter_look_through_angle_entity":
            "shadow_shutter_look_through_angle_manual": 54,
            # "shadow_height_after_sun_entity":
            "shadow_height_after_sun_manual": 80,
            # "shadow_angle_after_sun_entity":
            "shadow_angle_after_sun_manual": 80,
            #
            # Dawn configuration
            # "dawn_control_enabled_entity":
            "dawn_control_enabled_manual": True,
            # "dawn_brightness_threshold_entity":
            "dawn_brightness_threshold_manual": 5000,
            # "dawn_after_seconds_entity":
            "dawn_after_seconds_manual": 5,
            # "dawn_shutter_max_height_entity": input_number.automation_dawn_max_height_sc_dummy
            "dawn_shutter_max_height_manual": 90,
            # "dawn_shutter_max_angle_entity": input_number.automation_dawn_max_angle_sc_dummy
            "dawn_shutter_max_angle_manual": 90,
            # "dawn_shutter_look_through_seconds_entity":
            "dawn_shutter_look_through_seconds_manual": 5,
            # "dawn_shutter_open_seconds_entity":
            "dawn_shutter_open_seconds_manual": 5,
            # "dawn_shutter_look_through_angle_entity":
            "dawn_shutter_look_through_angle_manual": 45,
            # "dawn_height_after_dawn_entity":
            "dawn_height_after_dawn_manual": 10,
            # "dawn_angle_after_dawn_entity":
            "dawn_angle_after_dawn_manual": 10,
        }
    ]
}


async def test_full_sc_dummy_flow_debug(hass):
    """Test mit Echtzeit-Warten und Status-Ausgaben."""

    # 1. Setup der Entities
    hass.states.async_set("input_number.d01_brightness", "0")
    hass.states.async_set("input_number.d03_sun_elevation", "30")
    hass.states.async_set("input_number.d04_sun_azimuth", "200")
    hass.states.async_set("cover.sc_dummy", "open", {"current_position": 100})

    # 2. Integration starten
    # Wir erstellen manuell den Eintrag, den sonst die UI erstellen würde
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=TEST_CONFIG[DOMAIN][0],  # Wir nehmen das erste Element deiner Liste
        entry_id="test_entry_id",
        version=5,
    )
    entry.add_to_hass(hass)

    # Jetzt starten wir die Integration über den Entry, nicht über YAML
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Den Hauptschalter für Shadow Control explizit einschalten
    hass.states.async_set("switch.sc_dummy_s_control_active", "on")
    # Falls es noch einen globalen Lock gibt, diesen sicherheitshalber auf off
    hass.states.async_set("switch.sc_dummy_lock", "off")

    await hass.async_block_till_done()

    # MOCK SERVICE
    calls = async_mock_service(hass, "cover", "set_cover_position")

    # Status-Check nach Start
    active_switch = hass.states.get("switch.sc_dummy_s_control_active")
    _LOGGER.info("Shadow Control Switch State: %s", active_switch.state if active_switch else "NOT FOUND")

    # 3. Trigger: Helligkeit hoch
    _LOGGER.info("Triggering brightness to 60000...")
    hass.states.async_set("input_number.d01_brightness", "60000")
    await hass.async_block_till_done()

    # 4. ECHTZEIT WARTEN
    _LOGGER.info("Sleeping for 11 seconds...")
    await asyncio.sleep(11)

    # Wichtig: Nach dem Sleep muss HA die Timer-Events noch verarbeiten
    await hass.async_block_till_done()

    # 5. Status-Check am Ende
    current_state = hass.states.get("sensor.sc_dummy_state")
    _LOGGER.info("[DEBUG] Final Integration State Sensor: %s", {current_state.state if current_state else "NOT FOUND"})

    # 6. Verifikation
    if len(calls) == 0:
        _LOGGER.info("[DEBUG] FAILED: No service calls caught. Possible reasons: Threshold not hit, Azimuth wrong, or Timer canceled.")

    assert len(calls) > 0
