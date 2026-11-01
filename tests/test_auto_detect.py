"""Unit test untuk src/auto_detect.py (heuristic ROM, data dummy)."""

import math
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.auto_detect import detect_movement  # noqa: E402

WIDTH, HEIGHT = 640, 480


def _lm(x, y, vis=1.0):
    """Landmark dummy (duck-typed: .x/.y/.visibility)."""
    return SimpleNamespace(x=x, y=y, z=0.0, visibility=vis)


def _triplet(bx, by, angle_deg, length=0.2):
    """
    Titik (a, b, c) sehingga sudut di b = angle_deg.
    b→a selalu menunjuk ke atas; b→c diputar sebesar angle_deg.
    """
    th = math.radians(angle_deg)
    a = (bx, by - length)
    c = (bx + length * math.sin(th), by - length * math.cos(th))
    return a, (bx, by), c


def _make_frame(knee_angle=None, elbow_angle=None, vis=1.0):
    """Frame 33 landmark: lutut & siku kiri dikonfigurasi, sisanya invis."""
    frame = [_lm(0.0, 0.0, vis=0.0) for _ in range(33)]
    if knee_angle is not None:
        hip, knee, ankle = _triplet(0.5, 0.6, knee_angle)
        frame[23] = _lm(*hip, vis=vis)
        frame[25] = _lm(*knee, vis=vis)
        frame[27] = _lm(*ankle, vis=vis)
    if elbow_angle is not None:
        shoulder, elbow, wrist = _triplet(0.2, 0.25, elbow_angle)
        frame[11] = _lm(*shoulder, vis=vis)
        frame[13] = _lm(*elbow, vis=vis)
        frame[15] = _lm(*wrist, vis=vis)
    return frame


def test_large_knee_rom_returns_squat():
    frames = [
        _make_frame(knee_angle=a, elbow_angle=170.0) for a in (170.0, 120.0, 80.0)
    ]
    assert detect_movement(frames, WIDTH, HEIGHT) == "squat"


def test_large_elbow_rom_returns_pushup():
    frames = [
        _make_frame(knee_angle=170.0, elbow_angle=a) for a in (170.0, 120.0, 80.0)
    ]
    assert detect_movement(frames, WIDTH, HEIGHT) == "pushup"


def test_both_static_returns_default_squat():
    frames = [_make_frame(knee_angle=170.0, elbow_angle=170.0) for _ in range(5)]
    assert detect_movement(frames, WIDTH, HEIGHT) == "squat"


def test_empty_history_returns_default():
    assert detect_movement([], WIDTH, HEIGHT) == "squat"


def test_none_frames_are_skipped():
    frames = [
        None,
        _make_frame(knee_angle=170.0),
        None,
        _make_frame(knee_angle=80.0),
    ]
    assert detect_movement(frames, WIDTH, HEIGHT) == "squat"


def test_low_visibility_landmarks_are_ignored():
    frames = [_make_frame(knee_angle=90.0, vis=0.2) for _ in range(5)]
    assert detect_movement(frames, WIDTH, HEIGHT) == "squat"


def test_short_landmark_lists_are_skipped():
    frames = [
        [_lm(0.0, 0.0)] * 5,
        _make_frame(knee_angle=170.0),
        _make_frame(knee_angle=80.0),
    ]
    assert detect_movement(frames, WIDTH, HEIGHT) == "squat"


def test_both_move_larger_rom_wins_squat():
    frames = [
        _make_frame(knee_angle=170.0, elbow_angle=170.0),
        _make_frame(knee_angle=80.0, elbow_angle=130.0),
    ]
    assert detect_movement(frames, WIDTH, HEIGHT) == "squat"


def test_both_move_larger_rom_wins_pushup():
    frames = [
        _make_frame(knee_angle=170.0, elbow_angle=170.0),
        _make_frame(knee_angle=130.0, elbow_angle=80.0),
    ]
    assert detect_movement(frames, WIDTH, HEIGHT) == "pushup"


def test_rom_below_threshold_is_treated_static():
    frames = [_make_frame(knee_angle=a) for a in (160.0, 145.0)]  # ROM 15°
    assert detect_movement(frames, WIDTH, HEIGHT) == "squat"
