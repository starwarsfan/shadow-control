"""Unit tests for YAML schema validation."""

import pytest
import voluptuous as vol

from custom_components.shadow_control.config_flow import YAML_CONFIG_SCHEMA


class TestYAMLSchemaValidation:
    """Test YAML configuration schema validation."""

    def test_valid_minimal_config_passes(self):
        """Test that minimal valid configuration passes validation."""
        config = {
            "name": "Test Instance",
            "facade_shutter_type_static": "mode1",
            "target_cover_entity": ["cover.test"],
            "brightness_entity": "sensor.brightness",
            "sun_elevation_entity": "sensor.elevation",
            "sun_azimuth_entity": "sensor.azimuth",
            "sunrise_entity": "sensor.sunrise",
            "sunset_entity": "sensor.sunset",
            "facade_azimuth_static": 180,
            "facade_offset_sun_in_static": -80,
            "facade_offset_sun_out_static": 80,
            "facade_elevation_sun_min_static": 10,
            "facade_elevation_sun_max_static": 80,
            "facade_slat_width_static": 60,
            "facade_slat_distance_static": 50,
            "facade_slat_angle_offset_static": 0,
            "facade_slat_min_angle_static": 0,
            "facade_shutter_stepping_height_static": 5,
            "facade_shutter_stepping_angle_static": 5,
            "facade_light_strip_width_static": 0,
            "facade_shutter_height_static": 1000,
            "facade_max_movement_duration_static": 3,
            "facade_modification_tolerance_height_static": 3,
            "facade_modification_tolerance_angle_static": 3,
        }

        # Should not raise
        validated = YAML_CONFIG_SCHEMA(config)
        assert validated["name"] == "Test Instance"

    def test_unknown_key_raises_error(self):
        """Test that unknown keys raise validation error."""
        config = {
            "name": "Test Instance",
            "facade_shutter_type_static": "mode1",
            "target_cover_entity": ["cover.test"],
            "brightness_entity": "sensor.brightness",
            "sun_elevation_entity": "sensor.elevation",
            "sun_azimuth_entity": "sensor.azimuth",
            "sunrise_entity": "sensor.sunrise",
            "sunset_entity": "sensor.sunset",
            "facade_azimuth_static": 180,
            "facade_offset_sun_in_static": -80,
            "facade_offset_sun_out_static": 80,
            "facade_elevation_sun_min_static": 10,
            "facade_elevation_sun_max_static": 80,
            "facade_slat_width_static": 60,
            "facade_slat_distance_static": 50,
            "facade_slat_angle_offset_static": 0,
            "facade_slat_min_angle_static": 0,
            "facade_shutter_stepping_height_static": 5,
            "facade_shutter_stepping_angle_static": 5,
            "facade_light_strip_width_static": 0,
            "facade_shutter_height_static": 1000,
            "facade_max_movement_duration_static": 3,
            "facade_modification_tolerance_height_static": 3,
            "facade_modification_tolerance_angle_static": 3,
            # Unknown key - should fail
            "foobar": 123,
        }

        with pytest.raises(vol.Invalid) as exc_info:
            YAML_CONFIG_SCHEMA(config)

        # Error message should mention the unknown key
        error_msg = str(exc_info.value)
        assert "foobar" in error_msg or "extra keys not allowed" in error_msg.lower()

    def test_typo_in_key_name_raises_error(self):
        """Test that typos in key names are caught."""
        config = {
            "name": "Test Instance",
            "facade_shutter_type_static": "mode1",
            "target_cover_entity": ["cover.test"],
            "brightness_entity": "sensor.brightness",
            "sun_elevation_entity": "sensor.elevation",
            "sun_azimuth_entity": "sensor.azimuth",
            "sunrise_entity": "sensor.sunrise",
            "sunset_entity": "sensor.sunset",
            # Typo: "fagade" instead of "facade"
            "fagade_azimuth_static": 180,
            "facade_offset_sun_in_static": -80,
            "facade_offset_sun_out_static": 80,
            "facade_elevation_sun_min_static": 10,
            "facade_elevation_sun_max_static": 80,
            "facade_slat_width_static": 60,
            "facade_slat_distance_static": 50,
            "facade_slat_angle_offset_static": 0,
            "facade_slat_min_angle_static": 0,
            "facade_shutter_stepping_height_static": 5,
            "facade_shutter_stepping_angle_static": 5,
            "facade_light_strip_width_static": 0,
            "facade_shutter_height_static": 1000,
            "facade_max_movement_duration_static": 3,
            "facade_modification_tolerance_height_static": 3,
            "facade_modification_tolerance_angle_static": 3,
        }

        with pytest.raises(vol.Invalid) as exc_info:
            YAML_CONFIG_SCHEMA(config)

        error_msg = str(exc_info.value)
        # Should mention either the typo or that a required key is missing
        assert "fagade" in error_msg or "facade_azimuth_static" in error_msg

    def test_deprecated_keys_are_allowed(self):
        """Test that deprecated keys are allowed (but will be handled separately)."""
        config = {
            "name": "Test Instance",
            "facade_shutter_type_static": "mode1",
            "target_cover_entity": ["cover.test"],
            "brightness_entity": "sensor.brightness",
            "sun_elevation_entity": "sensor.elevation",
            "sun_azimuth_entity": "sensor.azimuth",
            "sunrise_entity": "sensor.sunrise",
            "sunset_entity": "sensor.sunset",
            "facade_azimuth_static": 180,
            "facade_offset_sun_in_static": -80,
            "facade_offset_sun_out_static": 80,
            "facade_elevation_sun_min_static": 10,
            "facade_elevation_sun_max_static": 80,
            "facade_slat_width_static": 60,
            "facade_slat_distance_static": 50,
            "facade_slat_angle_offset_static": 0,
            "facade_slat_min_angle_static": 0,
            "facade_shutter_stepping_height_static": 5,
            "facade_shutter_stepping_angle_static": 5,
            "facade_light_strip_width_static": 0,
            "facade_shutter_height_static": 1000,
            "facade_max_movement_duration_static": 3,
            "facade_modification_tolerance_height_static": 3,
            "facade_modification_tolerance_angle_static": 3,
            # Deprecated key - should be allowed by schema
            "shadow_brightness_threshold_manual": 30000,
        }

        # Should not raise - deprecated keys are in the schema
        validated = YAML_CONFIG_SCHEMA(config)
        assert "shadow_brightness_threshold_manual" in validated

    def test_multiple_unknown_keys_raise_error(self):
        """Test that multiple unknown keys are caught."""
        config = {
            "name": "Test Instance",
            "facade_shutter_type_static": "mode1",
            "target_cover_entity": ["cover.test"],
            "brightness_entity": "sensor.brightness",
            "sun_elevation_entity": "sensor.elevation",
            "sun_azimuth_entity": "sensor.azimuth",
            "sunrise_entity": "sensor.sunrise",
            "sunset_entity": "sensor.sunset",
            "facade_azimuth_static": 180,
            "facade_offset_sun_in_static": -80,
            "facade_offset_sun_out_static": 80,
            "facade_elevation_sun_min_static": 10,
            "facade_elevation_sun_max_static": 80,
            "facade_slat_width_static": 60,
            "facade_slat_distance_static": 50,
            "facade_slat_angle_offset_static": 0,
            "facade_slat_min_angle_static": 0,
            "facade_shutter_stepping_height_static": 5,
            "facade_shutter_stepping_angle_static": 5,
            "facade_light_strip_width_static": 0,
            "facade_shutter_height_static": 1000,
            "facade_max_movement_duration_static": 3,
            "facade_modification_tolerance_height_static": 3,
            "facade_modification_tolerance_angle_static": 3,
            # Multiple unknown keys
            "unknown_key_1": "value1",
            "unknown_key_2": "value2",
        }

        with pytest.raises(vol.Invalid):
            YAML_CONFIG_SCHEMA(config)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
