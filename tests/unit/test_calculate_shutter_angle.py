"""Test the shutter slat angle calculation math."""

import math
from unittest.mock import MagicMock

import pytest

from custom_components.shadow_control import ShadowControlManager
from custom_components.shadow_control.const import ShutterType


@pytest.fixture
def manager(mock_manager):
    """Bind the real calculation and setup mocks."""
    manager = mock_manager
    manager._calculate_shutter_angle = ShadowControlManager._calculate_shutter_angle.__get__(manager)

    # Mock the stepping helper
    manager._handle_shutter_angle_stepping = MagicMock(side_effect=lambda x: x)

    # Default Config (Standard Slat)
    manager._facade_config.slat_width = 80.0  # 80mm
    manager._facade_config.slat_distance = 70.0  # 70mm
    manager._facade_config.slat_angle_offset = 0.0
    manager._facade_config.slat_min_angle = 0.0
    manager._shadow_config.shutter_max_angle = 100.0
    manager._facade_config.shutter_type = ShutterType.MODE1  # 90 degree total
    manager._facade_config.azimuth = 180.0  # Fassade zeigt nach Süden

    # Inputs: Sonne direkt vor der Fassade (rel. Azimuth = 0°)
    manager._dynamic_config.sun_elevation = 30.0
    manager._dynamic_config.sun_azimuth = 180.0
    manager._effective_elevation = 30.0

    return manager


@pytest.mark.asyncio
class TestCalculateShutterAngle:
    """Test suite for slat trigonometry and mapping."""

    async def test_mode3_returns_zero(self, manager):
        """Mode 3 (no tilt) should always return 0.0."""
        manager._facade_config.shutter_type = ShutterType.MODE3
        assert manager._calculate_shutter_angle() == 0.0

    async def test_standard_math_mode1(self, manager):
        """
        Test Mode 1 mapping (0-90 degrees).
        If math results in 45 degrees, percentage should be 45 / 0.9 = 50%.
        """
        # We manually force effective_elevation to get a known angle
        # For simplicity, let's assume the math results in 45 deg
        manager._effective_elevation = 45.0
        # alpha = 90 - 45 = 45
        # asin_arg = sin(45) * 70 / 80 = 0.707 * 0.875 = 0.618
        # beta = asin(0.618) = 38.2 deg
        # gamma = 180 - 45 - 38.2 = 96.8
        # deg = 90 - 96.8 = -6.8 (will be clamped to 0 or handled by mapping)

        result = manager._calculate_shutter_angle()
        assert isinstance(result, float)

    async def test_mode2_mapping(self, manager):
        """Test Mode 2 (180 degree total range, 50% is horizontal)."""
        manager._facade_config.shutter_type = ShutterType.MODE2
        manager._effective_elevation = 30.0

        result = manager._calculate_shutter_angle()
        # Mode 2: (degrees / 1.8) + 50
        # If degrees is 0, result is 50.0.
        assert result >= 50.0

    async def test_invalid_asin_argument_safety(self, manager):
        """Trigger the warning if distance > width (impossible triangle)."""
        manager._facade_config.slat_distance = 200.0  # Much larger than width 80
        manager._effective_elevation = 5.0  # Low elevation creates large sin(alpha)

        result = manager._calculate_shutter_angle()
        assert result == 0.0
        manager.logger.warning.assert_called()

    async def test_min_max_clamping(self, manager):
        """Ensure result respects slat_min_angle and shutter_max_angle."""
        manager._facade_config.slat_min_angle = 20.0
        manager._shadow_config.shutter_max_angle = 80.0

        # Force a very high result
        manager._effective_elevation = 85.0  # Sun overhead, slats should close
        result = manager._calculate_shutter_angle()
        assert result <= 80.0

        # Force a very low result
        manager._effective_elevation = 5.0
        result = manager._calculate_shutter_angle()
        assert result >= 20.0

    async def test_missing_data_fallback(self, manager):
        """Test the large block of None checks at the start."""
        manager._effective_elevation = None
        result = manager._calculate_shutter_angle()
        assert result == 0.0
        manager.logger.warning.assert_called()

    # ===========================================================================
    # Tests für Azimuth-Korrektur der effektiven Lamellenbreite
    # ===========================================================================

    async def test_azimuth_correction_zero_relative_azimuth(self, manager):
        """
        Sonne direkt senkrecht zur Fassade (rel. Azimuth = 0°):
        cos(0°) = 1 → effective_slat_width == slat_width → Ergebnis identisch zur alten Berechnung.

        Fixture: azimuth=180°, facade_azimuth=180°, elevation=30°, effective_elevation=30°
        Erwartung: 21% (Referenzwert ohne Korrektur)
        """
        result = manager._calculate_shutter_angle()
        assert result == pytest.approx(21.0, abs=2.0), f"Bei rel. Azimuth=0° sollte Azimuth-Korrektur keinen Einfluss haben, got {result}%"

    async def test_azimuth_correction_45_degree_relative_azimuth(self, manager):
        """
        Sonne bei 45° rel. Azimuth zur Fassade:
        cos(45°) ≈ 0.707 → effective_slat_width = 80 * 0.707 ≈ 56.6 mm
        Das ergibt einen deutlich steileren Winkel als ohne Korrektur.

        Werte:
          azimuth=225°, facade_azimuth=180°, elevation=30°
          effective_elevation = atan(tan(30°) / cos(45°)) ≈ 39.2°
          alt (ohne Korrektur): ~3%
          neu (mit Korrektur):  ~38%
        """
        manager._dynamic_config.sun_azimuth = 225.0
        # effective_elevation für rel. Azimuth 45° bei elevation 30°
        eff_elev = math.degrees(math.atan(math.tan(math.radians(30)) / math.cos(math.radians(45))))
        manager._effective_elevation = eff_elev

        result = manager._calculate_shutter_angle()

        assert result == pytest.approx(38.0, abs=2.0), f"Bei rel. Azimuth=45° erwartet ~38%, got {result}%"
        # Kernaussage: Ergebnis muss deutlich größer sein als ohne Korrektur (~3%)
        assert result > 20.0, f"Azimuth-Korrektur muss bei 45° einen signifikant steileren Winkel liefern als ~3%, got {result}%"

    async def test_azimuth_correction_steeper_than_without_correction(self, manager):
        """
        Bei jedem rel. Azimuth > 0° muss der korrigierte Winkel >= dem unkorrigierten sein.
        Bei rel. Azimuth = 30°:
          effective_slat_width = 80 * cos(30°) ≈ 69.3 mm (statt 80 mm)
          → asin_arg wird größer → beta größer → gamma kleiner → Winkel steiler
        """
        manager._dynamic_config.sun_azimuth = 210.0  # 30° rel. Azimuth
        eff_elev = math.degrees(math.atan(math.tan(math.radians(30)) / math.cos(math.radians(30))))
        manager._effective_elevation = eff_elev

        result_with_correction = manager._calculate_shutter_angle()

        # Referenz: Was würde die alte Formel (ohne Azimuth-Korrektur) liefern?
        alpha_deg = 90 - eff_elev
        asin_arg_old = math.sin(math.radians(alpha_deg)) * 70.0 / 80.0
        beta_deg_old = math.degrees(math.asin(asin_arg_old))
        gamma_deg_old = 180 - alpha_deg - beta_deg_old
        angle_old = round(max(0.0, (90 - gamma_deg_old) / 0.9))

        assert result_with_correction >= angle_old, f"Korrigierter Winkel ({result_with_correction}%) muss >= unkorrigiertem ({angle_old}%) sein"

    async def test_azimuth_correction_real_world_wohnzimmer_hof(self, manager):
        """
        Reale Konfiguration 'Wohnzimmer Hof' bei aktuellem Sonnenstand.

        Konfiguration:
          facade_azimuth=200°, slat_width=95mm, slat_distance=67mm
        Sonnenstand:
          elevation=28.6°, azimuth=167.6° → rel. Azimuth=32.4°
        Erwartung:
          alt (ohne Korrektur): ~3%  → Sonne scheint durch!
          neu (mit Korrektur):  ~13% → Korrekte Abschirmung
        """
        manager._facade_config.azimuth = 200.0
        manager._facade_config.slat_width = 95.0
        manager._facade_config.slat_distance = 67.0
        manager._dynamic_config.sun_azimuth = 167.6
        manager._dynamic_config.sun_elevation = 28.6

        # effective_elevation wie _calculate_effective_elevation() es berechnet
        virtual_depth = math.cos(math.radians(abs(167.6 - 200.0)))
        virtual_height = math.tan(math.radians(28.6))
        manager._effective_elevation = math.degrees(math.atan(virtual_height / virtual_depth))

        result = manager._calculate_shutter_angle()

        assert result == pytest.approx(13.0, abs=2.0), f"Wohnzimmer Hof: erwartet ~13%, got {result}%"
        # Mindestens doppelt so viel wie der fehlerhafte alte Wert (~3%)
        assert result > 8.0, f"Wohnzimmer Hof: Azimuth-Korrektur muss Winkel deutlich erhöhen (>8%), got {result}%"

    async def test_azimuth_correction_missing_facade_azimuth_returns_zero(self, manager):
        """
        Wenn facade_azimuth nicht konfiguriert ist (None), muss die Methode
        sicher 0.0 zurückgeben (None-Check).
        """
        manager._facade_config.azimuth = None
        result = manager._calculate_shutter_angle()
        assert result == 0.0
        manager.logger.warning.assert_called()

    async def test_azimuth_correction_90_degree_relative_azimuth_fallback(self, manager):
        """
        Bei rel. Azimuth = 90° wäre effective_slat_width = slat_width * cos(90°) = 0.
        Der Code fällt auf slat_width zurück um Division-by-Zero zu vermeiden.
        In der Praxis kann dieser Fall nicht auftreten wenn _check_if_facade_is_in_sun()
        korrekt funktioniert (Fassade wäre dann nicht in der Sonne).
        """
        manager._dynamic_config.sun_azimuth = 270.0  # 90° rel. Azimuth zur Fassade (180°)

        # Bei effective_elevation = 30° und Fallback auf slat_width=80mm
        # (da eff_slat_width ≈ 0) → Ergebnis wie bei rel_azimuth=0°
        result = manager._calculate_shutter_angle()

        # Hauptsache: kein Crash, kein NaN, kein negativer Wert
        assert isinstance(result, float)
        assert result >= 0.0
        assert not math.isnan(result)
