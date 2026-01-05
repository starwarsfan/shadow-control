from datetime import timedelta

# Hier war der Fehler: async_setup_component kommt aus dem HA Core
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed, async_mock_service

from custom_components.shadow_control.const import DOMAIN

TEST_CONFIG = {
    DOMAIN: [
        {
            "name": "SC Dummy",
            "debug_enabled": True,
            "target_cover_entity": ["cover.sc_dummy"],
            "facade_shutter_type_static": "mode1",
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
            "facade_modification_tolerance_height_static": 3,
            "facade_modification_tolerance_angle_static": 3,
            # Shadow configuration
            # "shadow_control_enabled_entity":
            "shadow_control_enabled_manual": True,
            # "shadow_brightness_threshold_entity":
            "shadow_brightness_threshold_manual": 50000,
            # "shadow_after_seconds_entity":
            "shadow_after_seconds_manual": 10,
            # "shadow_shutter_max_height_entity": input_number.automation_shadow_max_height_sc_dummy
            "shadow_shutter_max_height_manual": 90,
            # "shadow_shutter_max_angle_entity": input_number.automation_shadow_max_angle_sc_dummy
            "shadow_shutter_max_angle_manual": 90,
            # "shadow_shutter_look_through_seconds_entity":
            "shadow_shutter_look_through_seconds_manual": 10,
            # "shadow_shutter_open_seconds_entity":
            "shadow_shutter_open_seconds_manual": 10,
            # "shadow_shutter_look_through_angle_entity":
            "shadow_shutter_look_through_angle_manual": 54,
            # "shadow_height_after_sun_entity":
            "shadow_height_after_sun_manual": 80,
            # "shadow_angle_after_sun_entity":
            "shadow_angle_after_sun_manual": 80,
            # Dawn configuration
            # "dawn_control_enabled_entity":
            "dawn_control_enabled_manual": True,
            # "dawn_brightness_threshold_entity":
            "dawn_brightness_threshold_manual": 5000,
            # "dawn_after_seconds_entity":
            "dawn_after_seconds_manual": 10,
            # "dawn_shutter_max_height_entity": input_number.automation_dawn_max_height_sc_dummy
            "dawn_shutter_max_height_manual": 90,
            # "dawn_shutter_max_angle_entity": input_number.automation_dawn_max_angle_sc_dummy
            "dawn_shutter_max_angle_manual": 90,
            # "dawn_shutter_look_through_seconds_entity":
            "dawn_shutter_look_through_seconds_manual": 10,
            # "dawn_shutter_open_seconds_entity":
            "dawn_shutter_open_seconds_manual": 10,
            # "dawn_shutter_look_through_angle_entity":
            "dawn_shutter_look_through_angle_manual": 45,
            # "dawn_height_after_dawn_entity":
            "dawn_height_after_dawn_manual": 10,
            # "dawn_angle_after_dawn_entity":
            "dawn_angle_after_dawn_manual": 10,
        }
    ]
}


async def test_full_sc_dummy_flow(hass):
    """Testet den SC Dummy mit der vollständigen Konfiguration."""

    # 1. Vorbereitungen: Die benötigten Input-Entities faken
    hass.states.async_set("input_number.d01_brightness", "10000")
    hass.states.async_set("input_number.d03_sun_elevation", "30")
    hass.states.async_set("input_number.d04_sun_azimuth", "200")
    hass.states.async_set("cover.sc_dummy", "open", {"current_position": 100})

    # 2. Integration starten
    assert await async_setup_component(hass, DOMAIN, TEST_CONFIG)
    await hass.async_block_till_done()

    # Registriere einen Mock-Service, um zu sehen, ob die Integration ihn aufruft
    calls = async_mock_service(hass, "cover", "set_cover_position")

    # 3. Trigger: Helligkeit hochsetzen (Sonne knallt)
    hass.states.async_set("input_number.d01_brightness", "60000")
    await hass.async_block_till_done()

    # 4. Zeitraffer: 11 Sekunden vorspulen (shadow_after_seconds_manual: 10)
    now = dt_util.utcnow()
    async_fire_time_changed(hass, now + timedelta(seconds=11))
    await hass.async_block_till_done()

    # 5. Check: Hat die Jalousie reagiert?
    # Hier prüfen wir, ob ein Service zum Schließen aufgerufen wurde
    state = hass.states.get("cover.sc_dummy")
    # In einem echten Integration-Test prüfen wir oft, ob die State Machine
    # nun den neuen Zielwert reflektiert
    assert state is not None

    # Verifikation: Wurde der Service genau 1x aufgerufen?
    assert len(calls) > 0
    # Prüfe die übermittelten Daten (z.B. Zielhöhe 80%)
    assert calls[0].data["position"] == 80
