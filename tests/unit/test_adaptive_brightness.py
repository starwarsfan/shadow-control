"""Test the AdaptiveBrightnessCalculator class."""

from datetime import UTC, datetime, timedelta, timezone

from custom_components.shadow_control.adaptive_brightness import AdaptiveBrightnessCalculator


class TestAdaptiveBrightnessCalculatorInit:
    """Test initialization and validation."""

    def test_init_valid_parameters(self):
        """Test initialization with valid parameters."""
        calc = AdaptiveBrightnessCalculator(
            winter_lux=50000,
            summer_lux=70000,
            buffer=10000,
        )

        assert calc._winter_lux == 50000
        assert calc._summer_lux == 70000
        assert calc._buffer == 10000

    def test_init_default_buffer(self):
        """Test initialization with default buffer value."""
        calc = AdaptiveBrightnessCalculator(
            winter_lux=50000,
            summer_lux=70000,
        )

        assert calc._buffer == 10000

    def test_init_winter_equals_summer(self, caplog):
        """Test that equal winter/summer values trigger warning."""
        calc = AdaptiveBrightnessCalculator(
            winter_lux=60000,
            summer_lux=60000,
        )

        assert calc._winter_lux == 60000
        assert calc._summer_lux == 60000
        # No adjustment needed when equal

    def test_init_winter_greater_than_summer(self, caplog):
        """Test that winter > summer triggers warning and adjustment."""
        calc = AdaptiveBrightnessCalculator(
            winter_lux=70000,
            summer_lux=50000,
        )

        assert calc._winter_lux == 70000
        assert calc._summer_lux == 70000  # Adjusted to match winter
        assert "should be lower than summer lux" in caplog.text

    def test_init_negative_buffer(self):
        """Test that negative buffer is corrected to 0."""
        calc = AdaptiveBrightnessCalculator(
            winter_lux=50000,
            summer_lux=70000,
            buffer=-5000,
        )

        assert calc._buffer == 0


class TestGetNextSummerSolstice:
    """Test summer solstice calculation."""

    def test_before_june_21_returns_current_year(self):
        """Test that dates before June 21 return current year's solstice."""
        current = datetime(2024, 3, 15, 12, 0, 0, tzinfo=UTC)
        calc = AdaptiveBrightnessCalculator(50000, 70000)

        solstice = calc._get_next_summer_solstice(current)

        assert solstice.year == 2024
        assert solstice.month == 6
        assert solstice.day == 21
        assert solstice.hour == 0
        assert solstice.minute == 0
        assert solstice.second == 0

    def test_on_june_21_returns_next_year(self):
        """Test that June 21 at noon already returns next year (due to > comparison)."""
        current = datetime(2024, 6, 21, 12, 0, 0, tzinfo=UTC)
        calc = AdaptiveBrightnessCalculator(50000, 70000)

        solstice = calc._get_next_summer_solstice(current)

        # Implementation uses >, so June 21 12:00 is after midnight June 21
        assert solstice.year == 2025
        assert solstice.month == 6
        assert solstice.day == 21

    def test_on_june_21_midnight_returns_current_year(self):
        """Test that June 21 at midnight returns current year."""
        current = datetime(2024, 6, 21, 0, 0, 0, tzinfo=UTC)
        calc = AdaptiveBrightnessCalculator(50000, 70000)

        solstice = calc._get_next_summer_solstice(current)

        # At exactly midnight, current == solstice, so not >
        assert solstice.year == 2024
        assert solstice.month == 6
        assert solstice.day == 21

    def test_after_june_21_returns_next_year(self):
        """Test that dates after June 21 return next year's solstice."""
        current = datetime(2024, 9, 15, 12, 0, 0, tzinfo=UTC)
        calc = AdaptiveBrightnessCalculator(50000, 70000)

        solstice = calc._get_next_summer_solstice(current)

        assert solstice.year == 2025
        assert solstice.month == 6
        assert solstice.day == 21

    def test_preserves_timezone(self):
        """Test that timezone is preserved in the result."""
        # UTC+2
        tz_offset = timezone(timedelta(hours=2))
        current = datetime(2024, 3, 15, 12, 0, 0, tzinfo=tz_offset)
        calc = AdaptiveBrightnessCalculator(50000, 70000)

        solstice = calc._get_next_summer_solstice(current)

        assert solstice.tzinfo == tz_offset


class TestGetDayBrightness:
    """Test seasonal brightness calculation."""

    def test_on_summer_solstice_returns_summer_lux(self):
        """Test that June 21 returns maximum (summer) brightness."""
        calc = AdaptiveBrightnessCalculator(50000, 70000)
        # Use midnight to get exactly 0 days difference
        current = datetime(2024, 6, 21, 0, 0, 0, tzinfo=UTC)

        brightness = calc._get_day_brightness(current)

        # Should be exactly 70000 at midnight June 21
        assert brightness == 70000

    def test_near_summer_solstice_returns_near_summer_lux(self):
        """Test that dates near June 21 return near-maximum brightness."""
        calc = AdaptiveBrightnessCalculator(50000, 70000)
        # Noon on June 21 (1 day difference due to implementation)
        current = datetime(2024, 6, 21, 12, 0, 0, tzinfo=UTC)

        brightness = calc._get_day_brightness(current)

        # Will be slightly less than 70000 due to 1-day difference
        assert 69500 <= brightness <= 70000

    def test_on_winter_solstice_returns_winter_lux(self):
        """Test that ~December 21 (±183 days from June 21) returns minimum brightness."""
        calc = AdaptiveBrightnessCalculator(50000, 70000)
        # December 21, 2023 is 183 days before June 21, 2024
        current = datetime(2023, 12, 21, 12, 0, 0, tzinfo=UTC)

        brightness = calc._get_day_brightness(current)

        # Should be close to winter value (within rounding)
        assert abs(brightness - 50000) <= 110  # Allow for day rounding

    def test_linear_interpolation_halfway(self):
        """Test that 91 days from solstice gives halfway brightness."""
        calc = AdaptiveBrightnessCalculator(50000, 70000)
        # Approximately 91 days after June 21 (September 20)
        current = datetime(2024, 9, 20, 12, 0, 0, tzinfo=UTC)

        brightness = calc._get_day_brightness(current)

        # At 92 days: abs(92 - 183) = 91
        # Expected: 50000 + 91 * (20000 / 183) = 50000 + 9945 ≈ 59945
        assert 59000 <= brightness <= 61000

    def test_equal_winter_summer_returns_constant(self):
        """Test that equal winter/summer values return constant brightness."""
        calc = AdaptiveBrightnessCalculator(60000, 60000)

        # Test various dates
        dates = [
            datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
            datetime(2024, 6, 21, 12, 0, 0, tzinfo=UTC),
            datetime(2024, 12, 31, 12, 0, 0, tzinfo=UTC),
        ]

        for date in dates:
            brightness = calc._get_day_brightness(date)
            assert brightness == 60000


class TestCalculateThreshold:
    """Test the main threshold calculation."""

    def test_outside_sun_hours_before_sunrise(self):
        """Test that times before sunrise return buffer value."""
        calc = AdaptiveBrightnessCalculator(50000, 70000, buffer=10000)

        current = datetime(2024, 6, 21, 5, 0, 0, tzinfo=UTC)
        sunrise = datetime(2024, 6, 21, 6, 0, 0, tzinfo=UTC)
        sunset = datetime(2024, 6, 21, 20, 0, 0, tzinfo=UTC)

        threshold = calc.calculate_threshold(current, sunrise, sunset)

        assert threshold == 10000

    def test_outside_sun_hours_after_sunset(self):
        """Test that times after sunset return buffer value."""
        calc = AdaptiveBrightnessCalculator(50000, 70000, buffer=10000)

        current = datetime(2024, 6, 21, 21, 0, 0, tzinfo=UTC)
        sunrise = datetime(2024, 6, 21, 6, 0, 0, tzinfo=UTC)
        sunset = datetime(2024, 6, 21, 20, 0, 0, tzinfo=UTC)

        threshold = calc.calculate_threshold(current, sunrise, sunset)

        assert threshold == 10000

    def test_at_solar_noon_returns_maximum(self):
        """Test that solar noon (midpoint) returns maximum brightness for that day."""
        calc = AdaptiveBrightnessCalculator(50000, 70000, buffer=10000)

        # Use June 21 midnight to get exact day_brightness = 70000
        sunrise = datetime(2024, 6, 21, 6, 0, 0, tzinfo=UTC)
        sunset = datetime(2024, 6, 21, 20, 0, 0, tzinfo=UTC)
        solar_noon = datetime(2024, 6, 21, 13, 0, 0, tzinfo=UTC)  # Midpoint

        threshold = calc.calculate_threshold(solar_noon, sunrise, sunset)

        # day_brightness will be ~69781 (1 day from solstice)
        # Peak = day_brightness (not 70000)
        # Allow tolerance for the actual calculated day_brightness
        assert 69500 <= threshold <= 70000

    def test_at_sunrise_returns_buffer_plus_offset(self):
        """Test threshold at sunrise time."""
        calc = AdaptiveBrightnessCalculator(50000, 70000, buffer=10000)

        sunrise = datetime(2024, 6, 21, 6, 0, 0, tzinfo=UTC)
        sunset = datetime(2024, 6, 21, 20, 0, 0, tzinfo=UTC)

        # Test at sunrise (x=0)
        # Sin curve at x=0 with phase shift c = period/4 gives sin(-c)
        # which is the minimum of the sine wave
        threshold = calc.calculate_threshold(sunrise, sunrise, sunset)

        # At x=0: sin(-period/4) gives negative value
        # Result should be close to buffer (10000)
        assert 10000 <= threshold <= 15000

    def test_invalid_sunset_before_sunrise(self, caplog):
        """Test that invalid sun times return buffer and log error."""
        calc = AdaptiveBrightnessCalculator(50000, 70000, buffer=10000)

        current = datetime(2024, 6, 21, 12, 0, 0, tzinfo=UTC)
        sunrise = datetime(2024, 6, 21, 20, 0, 0, tzinfo=UTC)  # Invalid!
        sunset = datetime(2024, 6, 21, 6, 0, 0, tzinfo=UTC)

        threshold = calc.calculate_threshold(current, sunrise, sunset)

        assert threshold == 10000
        assert "must be after sunrise" in caplog.text

    def test_winter_solstice_solar_noon(self):
        """Test calculation on winter solstice at solar noon."""
        calc = AdaptiveBrightnessCalculator(50000, 70000, buffer=10000)

        # December 21 (winter): day_brightness ≈ 50000
        sunrise = datetime(2023, 12, 21, 8, 0, 0, tzinfo=UTC)
        sunset = datetime(2023, 12, 21, 16, 0, 0, tzinfo=UTC)
        solar_noon = datetime(2023, 12, 21, 12, 0, 0, tzinfo=UTC)

        threshold = calc.calculate_threshold(solar_noon, sunrise, sunset)

        # At winter: day_brightness ≈ 50000
        # Peak should be close to 50000
        assert 48000 <= threshold <= 52000

    def test_symmetric_curve_around_noon(self):
        """Test that the curve is symmetric around solar noon."""
        calc = AdaptiveBrightnessCalculator(50000, 70000, buffer=10000)

        sunrise = datetime(2024, 6, 21, 6, 0, 0, tzinfo=UTC)
        sunset = datetime(2024, 6, 21, 20, 0, 0, tzinfo=UTC)

        # 2 hours before noon
        before_noon = datetime(2024, 6, 21, 11, 0, 0, tzinfo=UTC)
        threshold_before = calc.calculate_threshold(before_noon, sunrise, sunset)

        # 2 hours after noon
        after_noon = datetime(2024, 6, 21, 15, 0, 0, tzinfo=UTC)
        threshold_after = calc.calculate_threshold(after_noon, sunrise, sunset)

        # Should be equal (or very close due to rounding)
        assert abs(threshold_before - threshold_after) <= 1

    def test_different_day_lengths(self):
        """Test calculation with different sunrise/sunset durations."""
        calc = AdaptiveBrightnessCalculator(50000, 70000, buffer=10000)

        # Short winter day
        sunrise_winter = datetime(2024, 1, 15, 8, 0, 0, tzinfo=UTC)
        sunset_winter = datetime(2024, 1, 15, 16, 0, 0, tzinfo=UTC)  # 8 hours
        noon_winter = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)

        # Long summer day
        sunrise_summer = datetime(2024, 6, 21, 5, 0, 0, tzinfo=UTC)
        sunset_summer = datetime(2024, 6, 21, 21, 0, 0, tzinfo=UTC)  # 16 hours
        noon_summer = datetime(2024, 6, 21, 13, 0, 0, tzinfo=UTC)

        threshold_winter = calc.calculate_threshold(noon_winter, sunrise_winter, sunset_winter)
        threshold_summer = calc.calculate_threshold(noon_summer, sunrise_summer, sunset_summer)

        # Summer noon should have higher threshold due to higher day_brightness
        assert threshold_summer > threshold_winter

    def test_zero_buffer(self):
        """Test calculation with zero buffer."""
        calc = AdaptiveBrightnessCalculator(50000, 70000, buffer=0)

        sunrise = datetime(2024, 6, 21, 6, 0, 0, tzinfo=UTC)
        sunset = datetime(2024, 6, 21, 20, 0, 0, tzinfo=UTC)

        # Outside sun hours should return 0
        before_sunrise = datetime(2024, 6, 21, 5, 0, 0, tzinfo=UTC)
        threshold = calc.calculate_threshold(before_sunrise, sunrise, sunset)

        assert threshold == 0


class TestIntegration:
    """Integration tests simulating real-world scenarios."""

    def test_full_day_progression(self):
        """Test threshold progression through a full day."""
        calc = AdaptiveBrightnessCalculator(50000, 70000, buffer=10000)

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
            threshold = calc.calculate_threshold(time, sunrise, sunset)
            thresholds.append((label, threshold))

        # Verify general pattern
        assert thresholds[0][1] == 10000  # Before sunrise = buffer
        assert 69500 <= thresholds[3][1] <= 70000  # Noon ≈ maximum (with tolerance)
        assert thresholds[6][1] == 10000  # After sunset = buffer

        # Morning should be rising
        assert thresholds[1][1] < thresholds[2][1] < thresholds[3][1]

        # Afternoon should be falling
        assert thresholds[3][1] > thresholds[4][1] > thresholds[5][1]

    def test_year_round_noon_values(self):
        """Test that noon values follow seasonal pattern."""
        calc = AdaptiveBrightnessCalculator(50000, 70000, buffer=10000)

        # Test noon on different dates throughout the year
        dates = [
            (datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC), "winter"),
            (datetime(2024, 4, 15, 12, 0, 0, tzinfo=UTC), "spring"),
            (datetime(2024, 6, 21, 13, 0, 0, tzinfo=UTC), "summer solstice"),
            (datetime(2024, 9, 15, 12, 0, 0, tzinfo=UTC), "fall"),
        ]

        noon_thresholds = []
        for date, season in dates:
            # Approximate sunrise/sunset for each season
            if season == "winter":
                sunrise = date.replace(hour=8)
                sunset = date.replace(hour=16)
            elif season == "summer solstice":
                sunrise = date.replace(hour=5)
                sunset = date.replace(hour=21)
            else:
                sunrise = date.replace(hour=6)
                sunset = date.replace(hour=19)

            threshold = calc.calculate_threshold(date, sunrise, sunset)
            noon_thresholds.append((season, threshold))

        # Summer solstice should have highest threshold
        summer_threshold = next(t for s, t in noon_thresholds if s == "summer solstice")
        assert all(summer_threshold >= t for s, t in noon_thresholds)

        # Winter should have lowest threshold (excluding buffer times)
        winter_threshold = next(t for s, t in noon_thresholds if s == "winter")
        assert all(winter_threshold <= t for s, t in noon_thresholds)
