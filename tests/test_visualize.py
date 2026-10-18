"""Unit test untuk src/visualize.py."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.metrics import RepCountResult, RepInfo, count_reps  # noqa: E402
from src.visualize import (  # noqa: E402
    LEFT_INDICES,
    POSE_CONNECTIONS,
    RIGHT_INDICES,
    draw_angle_label,
    draw_pose_on_frame,
    plot_angle_series,
)


# --- Helper ---

class _FakeLM:
    """Landmark minimal dengan .x dan .y (mirip src.pose_estimator.Landmark)."""

    def __init__(self, x, y):
        self.x = x
        self.y = y


def _blank_frame(w=320, h=240):
    return np.zeros((h, w, 3), dtype=np.uint8)


def _full_landmarks(n=33, x=0.5, y=0.5):
    return [_FakeLM(x=x, y=y) for _ in range(n)]


# --- Konstanta ---

def test_pose_connections_are_valid_indices():
    for a, b in POSE_CONNECTIONS:
        assert 0 <= a <= 32
        assert 0 <= b <= 32


def test_left_and_right_sets_are_disjoint():
    assert LEFT_INDICES.isdisjoint(RIGHT_INDICES)


# --- draw_pose_on_frame ---

def test_draw_pose_returns_same_shape():
    frame = _blank_frame()
    out = draw_pose_on_frame(frame, _full_landmarks())
    assert out.shape == frame.shape
    assert out.dtype == frame.dtype


def test_draw_pose_modifies_pixels():
    frame = _blank_frame()
    before = frame.copy()
    out = draw_pose_on_frame(frame, _full_landmarks(), inplace=True)
    # Frame di tempat harus berubah
    assert not np.array_equal(out, before)


def test_draw_pose_inplace_false_does_not_mutate_input():
    frame = _blank_frame()
    before = frame.copy()
    out = draw_pose_on_frame(frame, _full_landmarks(), inplace=False)
    assert np.array_equal(frame, before)
    assert not np.array_equal(out, before)


def test_draw_pose_returns_frame_when_landmarks_none():
    frame = _blank_frame()
    out = draw_pose_on_frame(frame, None)
    assert out is frame  # inplace=True default → identitas sama


def test_draw_pose_returns_frame_when_landmarks_empty():
    frame = _blank_frame()
    out = draw_pose_on_frame(frame, [])
    assert out is frame


def test_draw_pose_accepts_tuple_landmarks():
    frame = _blank_frame()
    lms = [(0.5, 0.5)] * 33
    out = draw_pose_on_frame(frame, lms)
    assert out.shape == frame.shape


def test_draw_pose_skips_invalid_landmarks_gracefully():
    # Beberapa landmark invalid (string) — tidak boleh crash
    frame = _blank_frame()
    lms = [_FakeLM(0.5, 0.5)] * 11 + ["bukan landmark"] + [_FakeLM(0.5, 0.5)] * 21
    out = draw_pose_on_frame(frame, lms)
    assert out.shape == frame.shape


def test_draw_pose_out_of_bounds_does_not_crash():
    frame = _blank_frame()
    # Landmark di luar [0, 1]
    lms = [_FakeLM(1.5, -0.2)] * 33
    out = draw_pose_on_frame(frame, lms)
    assert out.shape == frame.shape


# --- draw_angle_label ---

def test_draw_angle_label_modifies_frame():
    frame = _blank_frame()
    before = frame.copy()
    out = draw_angle_label(frame, "90.0 deg", (10, 30))
    assert out is frame
    assert not np.array_equal(out, before)


# --- plot_angle_series ---

def test_plot_single_series_returns_figure():
    angles = [180.0, 100.0, 50.0, 100.0, 180.0]
    fig = plot_angle_series(angles=angles)
    assert fig is not None
    assert hasattr(fig, "savefig")
    assert len(fig.axes) == 1


def test_plot_two_series_returns_figure():
    left = [180.0, 100.0, 50.0, 100.0, 180.0]
    right = [178.0, 105.0, 55.0, 105.0, 178.0]
    fig = plot_angle_series(left_angles=left, right_angles=right)
    assert len(fig.axes) == 1
    # Legend punya 2 entri
    ax = fig.axes[0]
    legend = ax.get_legend()
    assert legend is not None
    assert len(legend.get_texts()) == 2


def test_plot_saves_png_file(tmp_path):
    angles = [180.0, 100.0, 50.0, 100.0, 180.0]
    out = tmp_path / "sub" / "plot.png"
    fig = plot_angle_series(angles=angles, output_path=out)
    assert out.exists()
    assert out.stat().st_size > 0
    # File PNG valid (magic bytes)
    assert out.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_plot_raises_when_no_series():
    with pytest.raises(ValueError):
        plot_angle_series()


def test_plot_handles_none_values():
    angles = [180.0, None, 50.0, None, 180.0]
    fig = plot_angle_series(angles=angles)
    assert len(fig.axes) == 1


def test_plot_handles_empty_sequence():
    fig = plot_angle_series(angles=[])
    assert len(fig.axes) == 1


def test_plot_with_rep_result_draws_annotations(tmp_path):
    curve = list(np.linspace(175, 50, 20)) + list(np.linspace(50, 175, 20))
    curve = curve * 3
    result = count_reps(curve)
    assert result.count == 3  # sanity

    out = tmp_path / "plot_with_reps.png"
    fig = plot_angle_series(angles=curve, rep_result=result, output_path=out)
    assert out.exists()

    # Cari teks anotasi "R1", "R2", "R3" di axis
    ax = fig.axes[0]
    texts = [t.get_text() for t in ax.texts]
    assert "R1" in texts
    assert "R2" in texts
    assert "R3" in texts


def test_plot_rep_result_none_does_not_crash():
    angles = [180.0, 100.0, 50.0]
    fig = plot_angle_series(angles=angles, rep_result=None)
    ax = fig.axes[0]
    assert len(ax.texts) == 0  # tidak ada anotasi
