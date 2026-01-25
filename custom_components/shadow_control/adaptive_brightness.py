"""Shadow Control adaptive brightness calculation."""

import logging
import math
from datetime import datetime

_LOGGER = logging.getLogger(__name__)


class AdaptiveBrightnessCalculator:
    """Calculate dynamic brightness thresholds based on seasonal and daily sun position."""

    def __init__(
        self,
        latitude: float = 0.0,
        logger: Logger | None = None,
    ) -> None:
        """
        Initialize the adaptive brightness calculator.

        Args:
            latitude: Geographic latitude for hemisphere detection (negative = southern hemisphere)
            logger: Logger instance to use (falls back to module logger if not provided)

        """
        self._is_southern_hemisphere = latitude < 0
        self._logger = logger if logger is not None else _LOGGER

    def calculate_threshold(
        self,
        current_time: datetime,
        sunrise: datetime,
        sunset: datetime,
        winter_lux: float,
        summer_lux: float,
        buffer: float,
    ) -> float:
        """
        Calculate the adaptive brightness threshold for the current time.

        Args:
            current_time: Current datetime
            sunrise: Today's sunrise datetime
            sunset: Today's sunset datetime
            winter_lux: Minimum brightness threshold (winter solstice)
            summer_lux: Maximum brightness threshold (summer solstice)
            buffer: Y-axis offset for the sine curve (prevents false triggers)

        Returns:
            Brightness threshold in lux

        """
        # Ensure buffer >= 0
        buffer = max(0, buffer)

        # Validation
        if winter_lux >= summer_lux:
            self._logger.warning(
                "Winter lux (%s) should be lower than summer lux (%s). Using winter_lux for both.",
                winter_lux,
                summer_lux,
            )
            summer_lux = winter_lux

        # Validate sun times
        if sunset <= sunrise:
            self._logger.error("Sunset (%s) must be after sunrise (%s). Returning buffer value.", sunset, sunrise)
            return buffer

        # Get daily brightness based on season
        day_brightness = self._get_day_brightness(current_time, winter_lux, summer_lux)

        self._logger.debug("Daily brightness threshold (seasonal): %s lux", day_brightness)

        # Check if we're between sunrise and sunset
        if not (sunrise <= current_time <= sunset):
            self._logger.debug("Outside sun hours (%s - %s), returning buffer: %s", sunrise.time(), sunset.time(), buffer)
            return buffer

        # Calculate sine curve parameters
        period_minutes = (sunset - sunrise).total_seconds() / 60
        minutes_since_sunrise = (current_time - sunrise).total_seconds() / 60

        # Sine function: f(x) = a * sin(b * (x - c)) + d
        amplitude = (day_brightness - buffer) / 2
        frequency = (2 * math.pi) / period_minutes
        phase_shift = period_minutes / 4  # Peak at solar noon
        y_offset = amplitude + buffer

        threshold = amplitude * math.sin(frequency * (minutes_since_sunrise - phase_shift)) + y_offset

        self._logger.debug(
            "Adaptive threshold: %s lux (x=%s min, period=%s min, a=%s, b=%s, c=%s, d=%s)",
            round(threshold),
            round(minutes_since_sunrise),
            round(period_minutes),
            round(amplitude),
            round(frequency, 6),
            round(phase_shift),
            round(y_offset),
        )

        return round(threshold)

    def _get_day_brightness(self, current_time: datetime) -> float:
        """
        Calculate daily brightness threshold based on distance to summer solstice.

        Linear interpolation between winter_lux (at ±183 days from Jun 21)
        and summer_lux (at Jun 21).

        Args:
            current_time: Current datetime

        Returns:
            Daily brightness threshold in lux

        """
        if self._winter_lux == self._summer_lux:
            return self._summer_lux

        # Find next June 21st
        next_solstice = self._get_next_summer_solstice(current_time)

        # Calculate days difference
        diff_days = abs((next_solstice - current_time).days)

        # Linear interpolation: max at solstice (0 days), min at ±183 days
        brightness = self._winter_lux + abs(diff_days - 183) * ((self._summer_lux - self._winter_lux) / 183)

        _LOGGER.debug("Seasonal calculation: next solstice %s, diff_days=%s, brightness=%s", next_solstice.date(), diff_days, round(brightness))

        return round(brightness)

    @staticmethod
    def _get_next_summer_solstice(current_time: datetime) -> datetime:
        """
        Get the next June 21st (summer solstice in northern hemisphere).

        Args:
            current_time: Current datetime

        Returns:
            Datetime of next June 21st at midnight

        """
        year = current_time.year
        tz = current_time.tzinfo

        # Check if we're past June 21st this year
        solstice_this_year = datetime(year, 6, 21, 0, 0, 0, tzinfo=tz)

        if current_time > solstice_this_year:
            # Use next year's solstice
            return datetime(year + 1, 6, 21, 0, 0, 0, tzinfo=tz)

        return solstice_this_year
