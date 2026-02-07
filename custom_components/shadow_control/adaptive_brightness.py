"""Shadow Control adaptive brightness calculation."""

import logging
import math
from datetime import datetime
from logging import Logger

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
        dawn_threshold: float | None = None,
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
            dawn_threshold: Optional dawn brightness threshold. If provided,
                          ensures shadow threshold stays above dawn throughout the entire day

        Returns:
            Brightness threshold in lux

        """
        # Ensure buffer >= 0
        buffer = max(0, buffer)

        # CRITICAL: If dawn is enabled, ensure the sine curve minimum (buffer)
        # is high enough to keep shadow threshold above dawn at all times
        effective_buffer = buffer
        if dawn_threshold is not None:
            # Shadow must always be above dawn + safety margin
            min_buffer = dawn_threshold + 1000  # 1000 lx safety margin
            if buffer < min_buffer:
                self._logger.info(
                    "Adjusting adaptive brightness curve minimum from %.0f lx to %.0f lx "
                    "to maintain shadow threshold above dawn threshold (%.0f lx) at all times.",
                    buffer,
                    min_buffer,
                    dawn_threshold,
                )
                effective_buffer = min_buffer

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
            return effective_buffer

        # Get daily brightness based on season
        day_brightness = self._get_day_brightness(current_time, winter_lux, summer_lux)

        self._logger.debug("Daily brightness threshold (seasonal): %s lux", day_brightness)

        # Handle sun_next_rising/sun_next_setting sensors
        # These sensors always point to the NEXT occurrence, so:
        # - After sunset: both sunrise and sunset are tomorrow
        # - Before sunrise: sunrise is today, sunset is tomorrow
        if sunrise > current_time and sunset > current_time:
            # Both times in future = we're in the night (after sunset or before sunrise)
            self._logger.debug(
                "Both sunrise (%s) and sunset (%s) are in the future (current time: %s). "
                "This indicates we are in the night period. Returning buffer: %s",
                sunrise,
                sunset,
                current_time,
                effective_buffer,
            )
            return effective_buffer

        # Check if we're between sunrise and sunset
        if not (sunrise <= current_time <= sunset):
            self._logger.debug(
                "Outside sun hours (%s - %s), returning buffer: %s",
                sunrise.time(),
                sunset.time(),
                effective_buffer,
            )
            return effective_buffer

        # Calculate sine curve parameters
        period_minutes = (sunset - sunrise).total_seconds() / 60
        minutes_since_sunrise = (current_time - sunrise).total_seconds() / 60

        # Sine function: f(x) = a * sin(b * (x - c)) + d
        # Using effective_buffer ensures the curve minimum stays above dawn threshold
        amplitude = (day_brightness - effective_buffer) / 2
        frequency = (2 * math.pi) / period_minutes
        phase_shift = period_minutes / 4  # Peak at solar noon
        y_offset = amplitude + effective_buffer

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

    def _get_day_brightness(self, current_time: datetime, winter_lux: float, summer_lux: float) -> float:
        """
        Calculate daily brightness threshold based on distance to summer solstice.

        Linear interpolation between winter_lux (at ±183 days from summer solstice)
        and summer_lux (at summer solstice).

        Args:
            current_time: Current datetime
            winter_lux: Minimum brightness threshold
            summer_lux: Maximum brightness threshold

        Returns:
            Daily brightness threshold in lux

        """
        if winter_lux == summer_lux:
            return summer_lux

        # Find next summer solstice (hemisphere-aware)
        next_solstice = self._get_next_summer_solstice(current_time)

        # Calculate days difference
        diff_days = abs((next_solstice - current_time).days)

        # Linear interpolation: max at solstice (0 days), min at ±183 days
        brightness = winter_lux + abs(diff_days - 183) * ((summer_lux - winter_lux) / 183)

        self._logger.debug("Seasonal calculation: next solstice %s, diff_days=%s, brightness=%s", next_solstice.date(), diff_days, round(brightness))

        return round(brightness)

    def _get_next_summer_solstice(self, current_time: datetime) -> datetime:
        """
        Get the next summer solstice date (hemisphere-aware).

        Northern hemisphere: June 21
        Southern hemisphere: December 21

        Args:
            current_time: Current datetime

        Returns:
            Datetime of next summer solstice at midnight

        """
        year = current_time.year
        tz = current_time.tzinfo

        # Determine solstice date based on hemisphere
        if self._is_southern_hemisphere:
            solstice_month, solstice_day = 12, 21  # December 21 (southern summer)
        else:
            solstice_month, solstice_day = 6, 21  # June 21 (northern summer)

        # Check if we're past this year's solstice
        solstice_this_year = datetime(year, solstice_month, solstice_day, 0, 0, 0, tzinfo=tz)

        if current_time > solstice_this_year:
            # Use next year's solstice
            return datetime(year + 1, solstice_month, solstice_day, 0, 0, 0, tzinfo=tz)

        return solstice_this_year
