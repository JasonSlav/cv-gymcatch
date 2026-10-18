"""Unit test untuk src/geometry.py."""

import math
import sys
from pathlib import Path

import pytest

# Tambahkan root proyek ke sys.path agar `import src.geometry` bisa jalan
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.geometry import (  # noqa: E402
    angle_from_vertical,
    calculate_angle,
    midpoint,
    normalize_to_origin,
    point_distance,
)


# --- calculate_angle ---

def test_angle_90_degrees():
    # Siku tegak lurus: a di kanan, b di tengah, c di atas
    a = (1.0, 0.0)
    b = (0.0, 0.0)
    c = (0.0, 1.0)
    assert calculate_angle(a, b, c) == pytest.approx(90.0, abs=1e-6)


def test_angle_180_degrees_straight_line():
    # Tiga titik kolinear
    a = (-1.0, 0.0)
    b = (0.0, 0.0)
    c = (1.0, 0.0)
    assert calculate_angle(a, b, c) == pytest.approx(180.0, abs=1e-6)


def test_angle_0_degrees_identical_rays():
    # Vektor b→a dan b→c menunjuk arah sama
    a = (1.0, 0.0)
    b = (0.0, 0.0)
    c = (2.0, 0.0)
    assert calculate_angle(a, b, c) == pytest.approx(0.0, abs=1e-6)


def test_angle_45_degrees():
    # Sudut 45° antara dua vektor
    a = (1.0, 0.0)
    b = (0.0, 0.0)
    c = (1.0, 1.0)
    assert calculate_angle(a, b, c) == pytest.approx(45.0, abs=1e-6)


def test_angle_degenerate_b_equals_a():
    # Titik b berimpit dengan a → fallback 180°
    a = (0.0, 0.0)
    b = (0.0, 0.0)
    c = (1.0, 0.0)
    assert calculate_angle(a, b, c) == pytest.approx(180.0, abs=1e-6)


def test_angle_accepts_3d_input_ignores_z():
    # Input 3D: hanya x, y yang dipakai
    a = (1.0, 0.0, 99.0)
    b = (0.0, 0.0, 99.0)
    c = (0.0, 1.0, 99.0)
    assert calculate_angle(a, b, c) == pytest.approx(90.0, abs=1e-6)


def test_angle_raises_on_invalid_point():
    with pytest.raises(ValueError):
        calculate_angle((1.0,), (0.0, 0.0), (0.0, 1.0))


# --- point_distance ---

def test_distance_3_4_5_triangle():
    assert point_distance((0.0, 0.0), (3.0, 4.0)) == pytest.approx(5.0)


def test_distance_zero_for_same_point():
    assert point_distance((2.0, 3.0), (2.0, 3.0)) == pytest.approx(0.0)


# --- midpoint ---

def test_midpoint_basic():
    result = midpoint((0.0, 0.0), (4.0, 6.0))
    assert result[0] == pytest.approx(2.0)
    assert result[1] == pytest.approx(3.0)


# --- normalize_to_origin ---

def test_normalize_to_origin():
    result = normalize_to_origin((5.0, 7.0), (2.0, 3.0))
    assert result[0] == pytest.approx(3.0)
    assert result[1] == pytest.approx(4.0)


# --- angle_from_vertical ---

def test_angle_from_vertical_straight_up():
    # Vektor dari bawah ke atas = (0, -1) → 0°
    a = (0.0, 1.0)
    b = (0.0, 0.0)
    assert angle_from_vertical(a, b) == pytest.approx(0.0, abs=1e-6)


def test_angle_from_vertical_horizontal():
    # Vektor horizontal → 90°
    a = (0.0, 0.0)
    b = (1.0, 0.0)
    assert angle_from_vertical(a, b) == pytest.approx(90.0, abs=1e-6)


def test_angle_from_vertical_degenerate():
    a = (1.0, 1.0)
    b = (1.0, 1.0)
    assert angle_from_vertical(a, b) == pytest.approx(0.0)
