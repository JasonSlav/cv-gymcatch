"""Unit test untuk src/metrics.py."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.metrics import (  # noqa: E402
    DEFAULT_CONSISTENCY_POINTS,
    MIN_REPS_FOR_CONSISTENCY,
    STATE_ASCENDING,
    STATE_BOTTOM,
    STATE_DESCENDING,
    STATE_STANDING,
    STATE_UNKNOWN,
    RepCountResult,
    RepInfo,
    compute_consistency,
    compute_rom,
    count_reps,
    extract_rep_curves,
    resample_curve,
    smooth_angles,
    to_array,
)


# --- Helper sintetis ---

def make_rep_curve(up: float = 175.0, down: float = 50.0, half: int = 15) -> np.ndarray:
    """Satu repetisi sintetis: turun dari up ke down lalu naik ke up."""
    down_phase = np.linspace(up, down, half)
    up_phase = np.linspace(down, up, half)
    return np.concatenate([down_phase, up_phase])


def make_n_rep_curve(n: int, **kwargs) -> np.ndarray:
    return np.concatenate([make_rep_curve(**kwargs) for _ in range(n)])


# --- to_array ---

def test_to_array_basic():
    arr = to_array([90.0, None, 120.0])
    assert arr.shape == (3,)
    assert arr[0] == pytest.approx(90.0)
    assert np.isnan(arr[1])
    assert arr[2] == pytest.approx(120.0)


def test_to_array_empty():
    arr = to_array([])
    assert arr.shape == (0,)


# --- smooth_angles ---

def test_smooth_angles_constant_signal_unchanged():
    angles = [100.0] * 10
    out = smooth_angles(angles, window=3)
    assert np.allclose(out, 100.0)


def test_smooth_angles_propagates_nan_edges():
    angles = [None, None, 100.0, 100.0, 100.0]
    out = smooth_angles(angles, window=3)
    # frame 2,3,4 punya cukup nilai valid
    assert not np.isnan(out[2])
    assert not np.isnan(out[3])
    assert not np.isnan(out[4])


def test_smooth_angles_all_nan():
    out = smooth_angles([None, None, None], window=3)
    assert np.all(np.isnan(out))


def test_smooth_angles_invalid_window_raises():
    with pytest.raises(ValueError):
        smooth_angles([1.0, 2.0], window=0)


# --- compute_rom ---

def test_compute_rom_basic():
    assert compute_rom([50.0, 100.0, 175.0]) == pytest.approx(125.0)


def test_compute_rom_with_nan_ignores_invalid():
    assert compute_rom([50.0, None, 175.0]) == pytest.approx(125.0)


def test_compute_rom_all_nan_returns_none():
    assert compute_rom([None, None]) is None


def test_compute_rom_empty_returns_none():
    assert compute_rom([]) is None


# --- count_reps ---

def test_count_reps_three_clean_reps():
    curve = make_n_rep_curve(3)
    result = count_reps(curve)
    assert result.count == 3
    assert result.final_state == STATE_STANDING


def test_count_reps_one_rep():
    curve = make_n_rep_curve(1)
    result = count_reps(curve)
    assert result.count == 1


def test_count_reps_zero_constant_high():
    curve = [175.0] * 60
    result = count_reps(curve)
    assert result.count == 0
    assert result.final_state == STATE_STANDING


def test_count_reps_zero_shallow_motion():
    # Turun ke 140 lalu naik — tidak sampai BOTTOM (< 100)
    curve = list(np.linspace(175, 140, 20)) + list(np.linspace(140, 175, 20))
    result = count_reps(curve)
    assert result.count == 0


def test_count_reps_with_small_noise():
    rng = np.random.default_rng(seed=42)
    base = make_n_rep_curve(3)
    noise = rng.normal(0.0, 3.0, size=len(base))
    noisy = base + noise
    result = count_reps(noisy)
    assert result.count == 3


def test_count_reps_invalid_thresholds_raises():
    with pytest.raises(ValueError):
        count_reps([100.0, 150.0], up_threshold=100.0, down_threshold=150.0)


def test_count_reps_rep_info_has_positive_rom():
    curve = make_n_rep_curve(2)
    result = count_reps(curve)
    assert result.count == 2
    for rep in result.reps:
        assert rep.rom > 0
        assert rep.duration_frames > 0
        assert rep.start_idx <= rep.valley_idx <= rep.end_idx


# --- extract_rep_curves ---

def test_extract_rep_curves_length_matches_count():
    curve = make_n_rep_curve(3)
    result = count_reps(curve)
    curves = extract_rep_curves(curve, result)
    assert len(curves) == result.count == 3


def test_extract_rep_curves_nonempty():
    curve = make_n_rep_curve(2)
    result = count_reps(curve)
    curves = extract_rep_curves(curve, result)
    for c in curves:
        assert len(c) > 0


# --- resample_curve ---

def test_resample_curve_length():
    out = resample_curve(np.array([1.0, 2.0, 3.0, 4.0]), n_points=10)
    assert len(out) == 10


def test_resample_curve_preserves_endpoints():
    curve = np.array([10.0, 20.0, 30.0])
    out = resample_curve(curve, n_points=5)
    assert out[0] == pytest.approx(10.0)
    assert out[-1] == pytest.approx(30.0)


def test_resample_curve_with_internal_nan():
    curve = np.array([10.0, np.nan, 30.0])
    out = resample_curve(curve, n_points=5)
    assert not np.any(np.isnan(out))
    assert out[0] == pytest.approx(10.0)
    assert out[-1] == pytest.approx(30.0)


def test_resample_curve_all_nan():
    out = resample_curve(np.array([np.nan, np.nan]), n_points=4)
    assert np.all(np.isnan(out))


# --- compute_consistency ---

def test_consistency_identical_reps_returns_one():
    curve = np.array([175.0, 100.0, 50.0, 100.0, 175.0])
    reps = [curve.copy() for _ in range(3)]
    c = compute_consistency(reps, n_points=5)
    assert c == pytest.approx(1.0, abs=1e-6)


def test_consistency_different_reps_below_one():
    base = np.array([175.0, 100.0, 50.0, 100.0, 175.0])
    deep = np.array([175.0, 80.0, 30.0, 80.0, 175.0])
    shallow = np.array([175.0, 120.0, 80.0, 120.0, 175.0])
    c = compute_consistency([base, deep, shallow], n_points=5)
    assert c is not None
    assert c < 1.0
    assert c >= 0.0


def test_consistency_fewer_than_min_reps_returns_none():
    curve = np.array([175.0, 100.0, 50.0, 100.0, 175.0])
    reps = [curve.copy() for _ in range(MIN_REPS_FOR_CONSISTENCY - 1)]
    assert compute_consistency(reps) is None


def test_consistency_zero_rom_returns_none():
    curve = np.full(5, 100.0)
    reps = [curve.copy() for _ in range(3)]
    assert compute_consistency(reps, n_points=5) is None


def test_consistency_clipped_to_zero_one():
    # Rep dengan bentuk sangat berbeda — pastikan hasil di [0, 1]
    r1 = np.array([175.0, 170.0, 165.0, 170.0, 175.0])
    r2 = np.array([175.0, 100.0, 50.0, 100.0, 175.0])
    r3 = np.array([175.0, 130.0, 80.0, 130.0, 175.0])
    c = compute_consistency([r1, r2, r3], n_points=5)
    assert c is not None
    assert 0.0 <= c <= 1.0
