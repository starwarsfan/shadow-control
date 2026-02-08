"""Test the AdaptiveBrightnessCalculator class."""

from datetime import UTC, datetime, timedelta, timezone

import pytest

from custom_components.shadow_control.adaptive_brightness import AdaptiveBrightnessCalculator


class TestAdaptiveBrightnessCalculatorInit:
    """Test initialization and validation."""

    def test_init_northern_hemisphere(self):
        """Test initialization with northern hemisphere latitude."""
        calc = AdaptiveBrightnessCalculator(latitude=47.5)

        assert calc._is_southern_hemisphere is False

    def test_init_southern_hemisphere(self):
        """Test initialization with southern hemisphere latitude."""
        calc = AdaptiveBrightnessCalculator(latitude=-33.9)

        assert calc._is_southern_hemisphere is True

    def test_init_equator(self):
        """Test initialization at equator (treated as northern hemisphere)."""
        calc = AdaptiveBrightnessCalculator(latitude=0.0)

        assert calc._is_southern_hemisphere is False

    def test_init_default_latitude(self):
        """Test initialization with default latitude."""
        calc = AdaptiveBrightnessCalculator()

        assert calc._is_southern_hemisphere is False


class TestGetNextSummerSolstice:
    """Test summer solstice calculation."""

    def test_northern_hemisphere_before_june_21_returns_current_year(self):
        """Test that dates before June 21 return current year's solstice (northern)."""
        current = datetime(2024, 3, 15, 12, 0, 0, tzinfo=UTC)
        calc = AdaptiveBrightnessCalculator(latitude=50.0)  # Northern

        solstice = calc._get_next_summer_solstice(current)

        assert solstice.year == 2024
        assert solstice.month == 6
        assert solstice.day == 21

    def test_northern_hemisphere_after_june_21_returns_next_year(self):
        """Test that dates after June 21 return next year's solstice (northern)."""
        current = datetime(2024, 9, 15, 12, 0, 0, tzinfo=UTC)
        calc = AdaptiveBrightnessCalculator(latitude=50.0)  # Northern

        solstice = calc._get_next_summer_solstice(current)

        assert solstice.year == 2025
        assert solstice.month == 6
        assert solstice.day == 21

    def test_southern_hemisphere_before_dec_21_returns_current_year(self):
        """Test that dates before Dec 21 return current year's solstice (southern)."""
        current = datetime(2024, 8, 15, 12, 0, 0, tzinfo=UTC)
        calc = AdaptiveBrightnessCalculator(latitude=-33.9)  # Southern

        solstice = calc._get_next_summer_solstice(current)

        assert solstice.year == 2024
        assert solstice.month == 12
        assert solstice.day == 21

    def test_southern_hemisphere_after_dec_21_returns_next_year(self):
        """Test that dates after Dec 21 return next year's solstice (southern)."""
        current = datetime(2024, 12, 25, 12, 0, 0, tzinfo=UTC)
        calc = AdaptiveBrightnessCalculator(latitude=-33.9)  # Southern

        solstice = calc._get_next_summer_solstice(current)

        assert solstice.year == 2025
        assert solstice.month == 12
        assert solstice.day == 21

    def test_preserves_timezone(self):
        """Test that timezone is preserved in the result."""
        # UTC+2
        tz_offset = timezone(timedelta(hours=2))
        current = datetime(2024, 3, 15, 12, 0, 0, tzinfo=tz_offset)
        calc = AdaptiveBrightnessCalculator(latitude=50.0)

        solstice = calc._get_next_summer_solstice(current)

        assert solstice.tzinfo == tz_offset


class TestGetDayBrightness:
    """Test seasonal brightness calculation."""

    def test_on_summer_solstice_returns_summer_lux(self):
        """Test that summer solstice returns maximum brightness."""
        calc = AdaptiveBrightnessCalculator(latitude=50.0)  # Northern
        # Use midnight to get exactly 0 days difference
        current = datetime(2024, 6, 21, 0, 0, 0, tzinfo=UTC)

        brightness = calc._get_day_brightness(current, winter_lux=50000, summer_lux=70000)

        assert brightness == 70000

    def test_southern_hemisphere_on_dec_21_returns_summer_lux(self):
        """Test that Dec 21 returns maximum brightness in southern hemisphere."""
        calc = AdaptiveBrightnessCalculator(latitude=-33.9)  # Southern
        current = datetime(2024, 12, 21, 0, 0, 0, tzinfo=UTC)

        brightness = calc._get_day_brightness(current, winter_lux=50000, summer_lux=70000)

        assert brightness == 70000

    def test_near_summer_solstice_returns_near_summer_lux(self):
        """Test that dates near solstice return near-maximum brightness."""
        calc = AdaptiveBrightnessCalculator(latitude=50.0)
        # Noon on June 21 (1 day difference due to implementation)
        current = datetime(2024, 6, 21, 12, 0, 0, tzinfo=UTC)

        brightness = calc._get_day_brightness(current, winter_lux=50000, summer_lux=70000)

        # Will be slightly less than 70000 due to 1-day difference
        assert 69500 <= brightness <= 70000

    def test_on_winter_solstice_returns_winter_lux(self):
        """Test that ~December 21 (±183 days from June 21) returns minimum brightness."""
        calc = AdaptiveBrightnessCalculator(latitude=50.0)
        # December 21, 2023 is 183 days before June 21, 2024
        current = datetime(2023, 12, 21, 12, 0, 0, tzinfo=UTC)

        brightness = calc._get_day_brightness(current, winter_lux=50000, summer_lux=70000)

        # Should be close to winter value (within rounding)
        assert abs(brightness - 50000) <= 110

    def test_equal_winter_summer_returns_constant(self):
        """Test that equal winter/summer values return constant brightness."""
        calc = AdaptiveBrightnessCalculator(latitude=50.0)

        # Test various dates
        dates = [
            datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
            datetime(2024, 6, 21, 12, 0, 0, tzinfo=UTC),
            datetime(2024, 12, 31, 12, 0, 0, tzinfo=UTC),
        ]

        for date in dates:
            brightness = calc._get_day_brightness(date, winter_lux=60000, summer_lux=60000)
            assert brightness == 60000


class TestCalculateThreshold:
    """Test the main threshold calculation."""

    def test_outside_sun_hours_before_sunrise(self):
        """Test that times before sunrise return buffer value."""
        calc = AdaptiveBrightnessCalculator(latitude=50.0)

        current = datetime(2024, 6, 21, 5, 0, 0, tzinfo=UTC)
        sunrise = datetime(2024, 6, 21, 6, 0, 0, tzinfo=UTC)
        sunset = datetime(2024, 6, 21, 20, 0, 0, tzinfo=UTC)

        threshold = calc.calculate_threshold(current, sunrise, sunset, winter_lux=50000, summer_lux=70000, minimal=10000)

        assert threshold == 10000

    def test_outside_sun_hours_after_sunset(self):
        """Test that times after sunset return buffer value."""
        calc = AdaptiveBrightnessCalculator(latitude=50.0)

        current = datetime(2024, 6, 21, 21, 0, 0, tzinfo=UTC)
        sunrise = datetime(2024, 6, 21, 6, 0, 0, tzinfo=UTC)
        sunset = datetime(2024, 6, 21, 20, 0, 0, tzinfo=UTC)

        threshold = calc.calculate_threshold(current, sunrise, sunset, winter_lux=50000, summer_lux=70000, minimal=10000)

        assert threshold == 10000

    def test_at_solar_noon_returns_maximum(self):
        """Test that solar noon (midpoint) returns maximum brightness for that day."""
        calc = AdaptiveBrightnessCalculator(latitude=50.0)

        # Use June 21 midnight to get exact day_brightness = 70000
        sunrise = datetime(2024, 6, 21, 6, 0, 0, tzinfo=UTC)
        sunset = datetime(2024, 6, 21, 20, 0, 0, tzinfo=UTC)
        solar_noon = datetime(2024, 6, 21, 13, 0, 0, tzinfo=UTC)  # Midpoint

        threshold = calc.calculate_threshold(solar_noon, sunrise, sunset, winter_lux=50000, summer_lux=70000, minimal=10000)

        # day_brightness will be ~69781 (1 day from solstice)
        # Peak = day_brightness (not 70000)
        # Allow tolerance for the actual calculated day_brightness
        assert 69500 <= threshold <= 70000

    def test_at_sunrise_returns_buffer_plus_offset(self):
        """Test threshold at sunrise time."""
        calc = AdaptiveBrightnessCalculator(latitude=50.0)

        sunrise = datetime(2024, 6, 21, 6, 0, 0, tzinfo=UTC)
        sunset = datetime(2024, 6, 21, 20, 0, 0, tzinfo=UTC)

        # Test at sunrise (x=0)
        threshold = calc.calculate_threshold(sunrise, sunrise, sunset, winter_lux=50000, summer_lux=70000, minimal=10000)

        # At x=0 the sine curve is at its minimum
        # Result should be close to buffer (10000)
        assert 10000 <= threshold <= 15000

    def test_invalid_sunset_before_sunrise(self, caplog):
        """Test that invalid sun times return buffer and log error."""
        calc = AdaptiveBrightnessCalculator(latitude=50.0)

        current = datetime(2024, 6, 21, 12, 0, 0, tzinfo=UTC)
        sunrise = datetime(2024, 6, 21, 20, 0, 0, tzinfo=UTC)  # Invalid!
        sunset = datetime(2024, 6, 21, 6, 0, 0, tzinfo=UTC)

        threshold = calc.calculate_threshold(current, sunrise, sunset, winter_lux=50000, summer_lux=70000, minimal=10000)

        assert threshold == 10000
        assert "must be after sunrise" in caplog.text

    def test_winter_greater_than_summer_logs_warning(self, caplog):
        """Test that winter > summer logs warning and uses winter for both."""
        calc = AdaptiveBrightnessCalculator(latitude=50.0)

        sunrise = datetime(2024, 6, 21, 6, 0, 0, tzinfo=UTC)
        sunset = datetime(2024, 6, 21, 20, 0, 0, tzinfo=UTC)
        solar_noon = datetime(2024, 6, 21, 13, 0, 0, tzinfo=UTC)

        threshold = calc.calculate_threshold(
            solar_noon,
            sunrise,
            sunset,
            winter_lux=70000,
            summer_lux=50000,
            minimal=10000,  # Invalid!
        )

        assert "should be lower than summer lux" in caplog.text
        # Should still calculate with adjusted values (both 70000)
        assert threshold > 0

    def test_negative_buffer_corrected_to_zero(self):
        """Test that negative buffer is corrected to 0."""
        calc = AdaptiveBrightnessCalculator(latitude=50.0)

        current = datetime(2024, 6, 21, 5, 0, 0, tzinfo=UTC)  # Before sunrise
        sunrise = datetime(2024, 6, 21, 6, 0, 0, tzinfo=UTC)
        sunset = datetime(2024, 6, 21, 20, 0, 0, tzinfo=UTC)

        threshold = calc.calculate_threshold(
            current,
            sunrise,
            sunset,
            winter_lux=50000,
            summer_lux=70000,
            minimal=-5000,  # Negative!
        )

        # Should return 0 (corrected buffer)
        assert threshold == 0

    def test_symmetric_curve_around_noon(self):
        """Test that the curve is symmetric around solar noon."""
        calc = AdaptiveBrightnessCalculator(latitude=50.0)

        sunrise = datetime(2024, 6, 21, 6, 0, 0, tzinfo=UTC)
        sunset = datetime(2024, 6, 21, 20, 0, 0, tzinfo=UTC)

        # 2 hours before noon
        before_noon = datetime(2024, 6, 21, 11, 0, 0, tzinfo=UTC)
        threshold_before = calc.calculate_threshold(before_noon, sunrise, sunset, winter_lux=50000, summer_lux=70000, minimal=10000)

        # 2 hours after noon
        after_noon = datetime(2024, 6, 21, 15, 0, 0, tzinfo=UTC)
        threshold_after = calc.calculate_threshold(after_noon, sunrise, sunset, winter_lux=50000, summer_lux=70000, minimal=10000)

        # Should be equal (or very close due to rounding)
        assert abs(threshold_before - threshold_after) <= 1


class TestIntegration:
    """Integration tests simulating real-world scenarios."""

    def test_full_day_progression_northern_hemisphere(self):
        """Test threshold progression through a full day in northern hemisphere."""
        calc = AdaptiveBrightnessCalculator(latitude=50.0)

        sunrise = datetime(2024, 6, 21, 6, 0, 0, tzinfo=UTC)
        sunset = datetime(2024, 6, 21, 20, 0, 0, tzinfo=UTC)

        # Sample times throughout the day
        times = [
            (datetime(2024, 6, 21, 5, 0, 0, tzinfo=UTC), "before sunrise"),
            (datetime(2024, 6, 21, 6, 0, 0, tzinfo=UTC), "at sunrise"),
            (datetime(2024, 6, 21, 10, 0, 0, tzinfo=UTC), "morning"),
            (datetime(2024, 6, 21, 13, 0, 0, tzinfo=UTC), "noon"),
            (datetime(2024, 6, 21, 16, 0, 0, tzinfo=UTC), "afternoon"),
            (datetime(2024, 6, 21, 20, 0, 0, tzinfo=UTC), "at sunset"),
            (datetime(2024, 6, 21, 21, 0, 0, tzinfo=UTC), "after sunset"),
        ]

        thresholds = []
        for time, label in times:
            threshold = calc.calculate_threshold(time, sunrise, sunset, winter_lux=50000, summer_lux=70000, minimal=10000)
            thresholds.append((label, threshold))

        # Verify general pattern
        assert thresholds[0][1] == 10000  # Before sunrise = buffer
        assert 69500 <= thresholds[3][1] <= 70000  # Noon ≈ maximum (with tolerance)
        assert thresholds[6][1] == 10000  # After sunset = buffer

        # Morning should be rising
        assert thresholds[1][1] < thresholds[2][1] < thresholds[3][1]

        # Afternoon should be falling
        assert thresholds[3][1] > thresholds[4][1] > thresholds[5][1]

    def test_southern_hemisphere_dec_solstice(self):
        """Test that southern hemisphere uses December as summer."""
        calc_south = AdaptiveBrightnessCalculator(latitude=-33.9)

        # December 21 at noon (southern summer)
        current = datetime(2024, 12, 21, 0, 0, 0, tzinfo=UTC)
        brightness = calc_south._get_day_brightness(current, winter_lux=50000, summer_lux=70000)

        # Should be at maximum (summer)
        assert brightness == 70000


class TestDawnProtection:
    """Test dawn threshold protection feature."""

    def test_no_dawn_threshold_uses_buffer(self):
        """Test that without dawn_threshold, buffer is used as-is."""
        calc = AdaptiveBrightnessCalculator(latitude=50.0)

        current = datetime(2024, 1, 15, 5, 0, 0, tzinfo=UTC)  # Before sunrise
        sunrise = datetime(2024, 1, 15, 8, 0, 0, tzinfo=UTC)
        sunset = datetime(2024, 1, 15, 16, 0, 0, tzinfo=UTC)

        threshold = calc.calculate_threshold(
            current,
            sunrise,
            sunset,
            winter_lux=30000,
            summer_lux=50000,
            minimal=1000,
            dawn_threshold=None,  # No dawn protection
        )

        assert threshold == 1000  # Returns original buffer

    def test_dawn_lower_than_buffer_no_adjustment(self):
        """Test that when dawn < buffer, no adjustment is needed."""
        calc = AdaptiveBrightnessCalculator(latitude=50.0)

        sunrise = datetime(2024, 6, 21, 6, 0, 0, tzinfo=UTC)
        sunset = datetime(2024, 6, 21, 20, 0, 0, tzinfo=UTC)
        noon = datetime(2024, 6, 21, 13, 0, 0, tzinfo=UTC)

        threshold = calc.calculate_threshold(
            noon,
            sunrise,
            sunset,
            winter_lux=30000,
            summer_lux=50000,
            minimal=10000,  # Higher than dawn
            dawn_threshold=5000,
        )

        # No adjustment - buffer already high enough
        assert threshold > 10000  # Above buffer at noon

    def test_dawn_higher_than_buffer_adjusts_minimum(self, caplog):
        """Test that when dawn > buffer, effective_buffer is raised."""
        calc = AdaptiveBrightnessCalculator(latitude=50.0)

        current = datetime(2024, 1, 15, 5, 0, 0, tzinfo=UTC)  # Before sunrise
        sunrise = datetime(2024, 1, 15, 8, 0, 0, tzinfo=UTC)
        sunset = datetime(2024, 1, 15, 16, 0, 0, tzinfo=UTC)

        threshold = calc.calculate_threshold(
            current,
            sunrise,
            sunset,
            winter_lux=30000,
            summer_lux=50000,
            minimal=1000,  # Lower than dawn
            dawn_threshold=5000,
        )

        # Should return dawn + 1000 (safety margin) = 6000
        assert threshold == 6000

        # Should log the adjustment
        assert "Adjusting adaptive brightness curve minimum" in caplog.text
        assert "from 1000 lx to 6000 lx" in caplog.text

    def test_minimum_never_below_dawn_at_sunrise(self):
        """Test that threshold at sunrise never falls below dawn + safety."""
        calc = AdaptiveBrightnessCalculator(latitude=50.0)

        sunrise = datetime(2024, 1, 15, 8, 0, 0, tzinfo=UTC)
        sunset = datetime(2024, 1, 15, 16, 0, 0, tzinfo=UTC)

        dawn_threshold = 5000
        expected_min = dawn_threshold + 1000  # Safety margin

        # Test at sunrise (where sine curve would normally be at minimum)
        threshold = calc.calculate_threshold(
            sunrise,
            sunrise,
            sunset,
            winter_lux=30000,
            summer_lux=50000,
            minimal=1000,
            dawn_threshold=dawn_threshold,
        )

        assert threshold >= expected_min

    def test_minimum_maintained_throughout_day(self):
        """Test that threshold stays above dawn + safety at all times."""
        calc = AdaptiveBrightnessCalculator(latitude=50.0)

        sunrise = datetime(2024, 1, 15, 8, 0, 0, tzinfo=UTC)
        sunset = datetime(2024, 1, 15, 16, 0, 0, tzinfo=UTC)

        dawn_threshold = 5000
        expected_min = dawn_threshold + 1000

        # Test multiple times throughout the day
        test_times = [
            sunrise,  # 08:00 - sunrise
            sunrise.replace(hour=10),  # 10:00 - morning
            sunrise.replace(hour=12),  # 12:00 - noon
            sunrise.replace(hour=14),  # 14:00 - afternoon
            sunset,  # 16:00 - sunset
        ]

        for time in test_times:
            threshold = calc.calculate_threshold(
                time,
                sunrise,
                sunset,
                winter_lux=30000,
                summer_lux=50000,
                minimal=1000,
                dawn_threshold=dawn_threshold,
            )

            assert threshold >= expected_min, f"Failed at {time.hour}:00 - threshold {threshold} < minimum {expected_min}"

    def test_real_world_winter_scenario(self):
        """Test realistic winter scenario with your actual values."""
        calc = AdaptiveBrightnessCalculator(latitude=47.0)  # Zürich

        # January 29, 2026
        sunrise = datetime(2026, 1, 29, 7, 30, 0, tzinfo=UTC)
        sunset = datetime(2026, 1, 29, 17, 0, 0, tzinfo=UTC)
        noon = datetime(2026, 1, 29, 12, 0, 0, tzinfo=UTC)

        threshold = calc.calculate_threshold(
            noon,
            sunrise,
            sunset,
            winter_lux=30000,
            summer_lux=50000,
            minimal=1000,
            dawn_threshold=5000,
        )

        # At noon in winter, threshold should be above dawn + safety
        assert threshold > 6000  # Above dawn + 1000
        assert threshold < 35000  # But not too high (it's winter)

    def test_curve_shifted_up_with_dawn(self):
        """Test that dawn protection shifts the entire curve upward."""
        calc = AdaptiveBrightnessCalculator(latitude=50.0)

        sunrise = datetime(2024, 6, 21, 6, 0, 0, tzinfo=UTC)
        sunset = datetime(2024, 6, 21, 20, 0, 0, tzinfo=UTC)
        noon = datetime(2024, 6, 21, 13, 0, 0, tzinfo=UTC)

        # Without dawn
        threshold_no_dawn = calc.calculate_threshold(
            noon,
            sunrise,
            sunset,
            winter_lux=30000,
            summer_lux=50000,
            minimal=1000,
            dawn_threshold=None,
        )

        # With dawn
        threshold_with_dawn = calc.calculate_threshold(
            noon,
            sunrise,
            sunset,
            winter_lux=30000,
            summer_lux=50000,
            minimal=1000,
            dawn_threshold=5000,
        )

        # With dawn, the curve baseline is higher
        assert threshold_with_dawn >= threshold_no_dawn

    def test_extreme_dawn_threshold(self):
        """Test with very high dawn threshold."""
        calc = AdaptiveBrightnessCalculator(latitude=50.0)

        sunrise = datetime(2024, 1, 15, 8, 0, 0, tzinfo=UTC)
        sunset = datetime(2024, 1, 15, 16, 0, 0, tzinfo=UTC)

        # Dawn higher than winter_lux
        threshold = calc.calculate_threshold(
            sunrise,
            sunrise,
            sunset,
            winter_lux=30000,
            summer_lux=50000,
            minimal=1000,
            dawn_threshold=35000,  # Very high!
        )

        # Should be dawn + 1000 = 36000
        assert threshold == 36000

    def test_zero_buffer_with_dawn(self):
        """Test that zero buffer works with dawn protection."""
        calc = AdaptiveBrightnessCalculator(latitude=50.0)

        current = datetime(2024, 1, 15, 5, 0, 0, tzinfo=UTC)  # Before sunrise
        sunrise = datetime(2024, 1, 15, 8, 0, 0, tzinfo=UTC)
        sunset = datetime(2024, 1, 15, 16, 0, 0, tzinfo=UTC)

        threshold = calc.calculate_threshold(
            current,
            sunrise,
            sunset,
            winter_lux=30000,
            summer_lux=50000,
            minimal=0,  # Zero
            dawn_threshold=5000,
        )

        # Should use dawn + 1000 = 6000, not 0
        assert threshold == 6000


class TestDawnThresholdProtection:
    """Test dawn threshold protection feature."""

    def test_no_dawn_threshold_no_adjustment(self):
        """Test that without dawn_threshold, buffer is used as-is."""
        calc = AdaptiveBrightnessCalculator(latitude=47.0)

        current = datetime(2024, 1, 15, 5, 0, 0, tzinfo=UTC)  # Before sunrise
        sunrise = datetime(2024, 1, 15, 8, 0, 0, tzinfo=UTC)
        sunset = datetime(2024, 1, 15, 16, 0, 0, tzinfo=UTC)

        threshold = calc.calculate_threshold(
            current,
            sunrise,
            sunset,
            winter_lux=30000,
            summer_lux=50000,
            minimal=1000,
            dawn_threshold=None,  # No dawn protection
        )

        # Should return original buffer
        assert threshold == 1000

    def test_dawn_lower_than_buffer_no_adjustment(self):
        """Test that when dawn < buffer, no adjustment is made."""
        calc = AdaptiveBrightnessCalculator(latitude=47.0)

        sunrise = datetime(2024, 1, 15, 8, 0, 0, tzinfo=UTC)
        sunset = datetime(2024, 1, 15, 16, 0, 0, tzinfo=UTC)
        current = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)

        threshold = calc.calculate_threshold(
            current,
            sunrise,
            sunset,
            winter_lux=30000,
            summer_lux=50000,
            minimal=10000,  # Higher than dawn
            dawn_threshold=5000,
        )

        # No adjustment needed - buffer already high enough
        # Threshold should be calculated normally
        assert threshold > 10000  # Above buffer at noon

    def test_dawn_higher_than_buffer_adjusts_minimum(self, caplog):
        """Test that when dawn > buffer, effective_buffer is raised."""
        calc = AdaptiveBrightnessCalculator(latitude=47.0)

        current = datetime(2024, 1, 15, 5, 0, 0, tzinfo=UTC)  # Before sunrise
        sunrise = datetime(2024, 1, 15, 8, 0, 0, tzinfo=UTC)
        sunset = datetime(2024, 1, 15, 16, 0, 0, tzinfo=UTC)

        threshold = calc.calculate_threshold(
            current,
            sunrise,
            sunset,
            winter_lux=30000,
            summer_lux=50000,
            minimal=1000,  # Lower than dawn
            dawn_threshold=5000,
        )

        # Should return dawn + 1000 (safety margin) = 6000
        assert threshold == 6000

        # Should log the adjustment
        assert "Adjusting adaptive brightness curve minimum" in caplog.text
        assert "from 1000 lx to 6000 lx" in caplog.text

    def test_minimum_always_above_dawn_at_sunrise(self):
        """Test that threshold at sunrise never falls below dawn + safety."""
        calc = AdaptiveBrightnessCalculator(latitude=47.0)

        sunrise = datetime(2024, 1, 15, 8, 0, 0, tzinfo=UTC)
        sunset = datetime(2024, 1, 15, 16, 0, 0, tzinfo=UTC)

        dawn_threshold = 5000
        expected_min = dawn_threshold + 1000  # Safety margin

        # Test at sunrise (where sine curve is at minimum)
        threshold = calc.calculate_threshold(
            sunrise,
            sunrise,
            sunset,
            winter_lux=30000,
            summer_lux=50000,
            minimal=1000,
            dawn_threshold=dawn_threshold,
        )

        # Should be at or above the safe minimum
        assert threshold >= expected_min

    def test_minimum_always_above_dawn_throughout_day(self):
        """Test that threshold never falls below dawn + safety at any time of day."""
        calc = AdaptiveBrightnessCalculator(latitude=47.0)

        sunrise = datetime(2024, 1, 15, 8, 0, 0, tzinfo=UTC)
        sunset = datetime(2024, 1, 15, 16, 0, 0, tzinfo=UTC)

        dawn_threshold = 5000
        expected_min = dawn_threshold + 1000

        # Test multiple times throughout the day
        times = [
            sunrise,  # Start of day
            sunrise.replace(hour=10),  # Morning
            sunrise.replace(hour=12),  # Noon
            sunrise.replace(hour=14),  # Afternoon
            sunset,  # End of day
        ]

        for time in times:
            threshold = calc.calculate_threshold(
                time,
                sunrise,
                sunset,
                winter_lux=30000,
                summer_lux=50000,
                minimal=1000,
                dawn_threshold=dawn_threshold,
            )

            assert threshold >= expected_min, f"Threshold {threshold} below minimum at {time.hour}:00"

    def test_adjustment_only_logged_once(self, caplog):
        """Test that adjustment is only logged once per calculation."""
        calc = AdaptiveBrightnessCalculator(latitude=47.0)

        sunrise = datetime(2024, 1, 15, 8, 0, 0, tzinfo=UTC)
        sunset = datetime(2024, 1, 15, 16, 0, 0, tzinfo=UTC)

        # First call - should log
        caplog.clear()
        calc.calculate_threshold(
            sunrise,
            sunrise,
            sunset,
            winter_lux=30000,
            summer_lux=50000,
            minimal=1000,
            dawn_threshold=5000,
        )

        log_count_1 = caplog.text.count("Adjusting adaptive brightness curve minimum")
        assert log_count_1 == 1

        # Second call - should log again (not cached)
        caplog.clear()
        calc.calculate_threshold(
            sunrise.replace(hour=12),
            sunrise,
            sunset,
            winter_lux=30000,
            summer_lux=50000,
            minimal=1000,
            dawn_threshold=5000,
        )

        log_count_2 = caplog.text.count("Adjusting adaptive brightness curve minimum")
        assert log_count_2 == 1

    def test_real_world_scenario_winter_with_dawn(self):
        """Test realistic winter scenario with dawn protection."""
        calc = AdaptiveBrightnessCalculator(latitude=47.0)

        # January 29, 2026 - real date from your dev instance
        sunrise = datetime(2026, 1, 29, 7, 30, 0, tzinfo=UTC)
        sunset = datetime(2026, 1, 29, 17, 0, 0, tzinfo=UTC)
        current = datetime(2026, 1, 29, 12, 0, 0, tzinfo=UTC)  # Noon

        threshold = calc.calculate_threshold(
            current,
            sunrise,
            sunset,
            winter_lux=30000,
            summer_lux=50000,
            minimal=1000,
            dawn_threshold=5000,
        )

        # At noon in winter, threshold should be well above dawn
        assert threshold > 6000  # Above dawn + safety
        assert threshold < 35000  # But below summer max

    def test_effective_buffer_affects_amplitude(self):
        """Test that effective_buffer changes the curve amplitude."""
        calc = AdaptiveBrightnessCalculator(latitude=47.0)

        sunrise = datetime(2024, 6, 21, 6, 0, 0, tzinfo=UTC)
        sunset = datetime(2024, 6, 21, 20, 0, 0, tzinfo=UTC)
        noon = datetime(2024, 6, 21, 13, 0, 0, tzinfo=UTC)

        # Without dawn (buffer = 1000)
        threshold_no_dawn = calc.calculate_threshold(
            noon,
            sunrise,
            sunset,
            winter_lux=30000,
            summer_lux=50000,
            minimal=1000,
            dawn_threshold=None,
        )

        # With dawn (effective_buffer = 6000)
        threshold_with_dawn = calc.calculate_threshold(
            noon,
            sunrise,
            sunset,
            winter_lux=30000,
            summer_lux=50000,
            minimal=1000,
            dawn_threshold=5000,
        )

        # With higher effective_buffer, the curve is shifted up
        # At noon both should be high, but with_dawn should be slightly higher
        # due to the shifted baseline
        assert threshold_with_dawn >= threshold_no_dawn

    def test_high_dawn_threshold(self):
        """Test with unusually high dawn threshold."""
        calc = AdaptiveBrightnessCalculator(latitude=47.0)

        sunrise = datetime(2024, 1, 15, 8, 0, 0, tzinfo=UTC)
        sunset = datetime(2024, 1, 15, 16, 0, 0, tzinfo=UTC)

        # Dawn threshold higher than winter_lux - extreme case
        threshold = calc.calculate_threshold(
            sunrise,
            sunrise,
            sunset,
            winter_lux=30000,
            summer_lux=50000,
            minimal=1000,
            dawn_threshold=35000,  # Very high!
        )

        # Should be dawn + 1000 = 36000
        assert threshold == 36000

    def test_zero_buffer_with_dawn(self):
        """Test that zero buffer works correctly with dawn protection."""
        calc = AdaptiveBrightnessCalculator(latitude=47.0)

        current = datetime(2024, 1, 15, 5, 0, 0, tzinfo=UTC)  # Before sunrise
        sunrise = datetime(2024, 1, 15, 8, 0, 0, tzinfo=UTC)
        sunset = datetime(2024, 1, 15, 16, 0, 0, tzinfo=UTC)

        threshold = calc.calculate_threshold(
            current,
            sunrise,
            sunset,
            winter_lux=30000,
            summer_lux=50000,
            minimal=0,  # Zero buffer
            dawn_threshold=5000,
        )

        # Should return dawn + 1000 = 6000 (not 0)
        assert threshold == 6000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
