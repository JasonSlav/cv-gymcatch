"""Unit test untuk src/auto_detect.py (Decision Tree, data dummy deterministik).

Semua frame dummy dibangun dari geometri eksplisit (bukan acak):
- _make_frame           : tubuh berdiri vertikal (bahu jauh di atas pinggul)
- _make_horizontal_frame: tubuh mendatar (bahu & pinggul se-Y)
- _make_press_frame     : gerakan lengan (bahu tetap, siku & wrist bebas)
- _make_deadlift_frame  : hip hinge (bahu bergeser maju-bawah seiring t)
"""

import math
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.auto_detect import detect_movement  # noqa: E402

WIDTH, HEIGHT = 640, 480


def _lm(x, y, vis=1.0):
    """Landmark dummy (duck-typed: .x/.y/.visibility) — koordinat ternormalisasi."""
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


def _make_frame(knee_angle=None, elbow_angle=None, right_knee_angle=None, vis=1.0):
    """Frame berdiri vertikal: lutut kiri/kanan & siku kiri dikonfigurasi."""
    frame = [_lm(0.0, 0.0, vis=0.0) for _ in range(33)]
    if knee_angle is not None:
        hip, knee, ankle = _triplet(0.5, 0.6, knee_angle)
        frame[23] = _lm(*hip, vis=vis)
        frame[25] = _lm(*knee, vis=vis)
        frame[27] = _lm(*ankle, vis=vis)
    if right_knee_angle is not None:
        hip, knee, ankle = _triplet(0.7, 0.6, right_knee_angle)
        frame[24] = _lm(*hip, vis=vis)
        frame[26] = _lm(*knee, vis=vis)
        frame[28] = _lm(*ankle, vis=vis)
    if elbow_angle is not None:
        shoulder, elbow, wrist = _triplet(0.2, 0.25, elbow_angle)
        frame[11] = _lm(*shoulder, vis=vis)
        frame[13] = _lm(*elbow, vis=vis)
        frame[15] = _lm(*wrist, vis=vis)
    return frame


def _make_horizontal_frame(knee_angle=None):
    """Frame tubuh mendatar: bahu (11) & pinggul (23) berada pada Y serupa.

    Lutut: titik lutut tetap, ankle bergerak → sudut di lutut = knee_angle.
    """
    frame = [_lm(0.0, 0.0, vis=0.0) for _ in range(33)]
    frame[11] = _lm(0.3, 0.5)   # bahu
    frame[23] = _lm(0.6, 0.5)   # pinggul (Y sama dengan bahu → mendatar)
    if knee_angle is not None:
        frame[25] = _lm(0.75, 0.5)  # lutut
        th = math.radians(180.0 - knee_angle)
        frame[27] = _lm(0.75 - 0.2 * math.cos(th), 0.5 + 0.2 * math.sin(th))
    return frame


def _make_press_frame(elbow_xy, wrist_xy):
    """Frame gerakan lengan: bahu & pinggul tetap, siku & wrist di posisi bebas."""
    frame = [_lm(0.0, 0.0, vis=0.0) for _ in range(33)]
    frame[11] = _lm(0.3, 0.3)        # bahu
    frame[13] = _lm(*elbow_xy)       # siku
    frame[15] = _lm(*wrist_xy)       # wrist
    frame[23] = _lm(0.35, 0.65)      # pinggul (jauh di bawah bahu → vertikal)
    return frame


def _make_deadlift_frame(t):
    """Frame hip hinge: bahu bergeser maju-bawah seiring t (0=tegak, 1=hinge)."""
    frame = [_lm(0.0, 0.0, vis=0.0) for _ in range(33)]
    sh_x = 0.5 - 0.35 * t
    sh_y = 0.2 + 0.15 * t
    frame[11] = _lm(sh_x, sh_y)
    frame[23] = _lm(0.5, 0.6)
    frame[25] = _lm(0.5, 0.8)
    frame[12] = _lm(sh_x, sh_y)
    frame[24] = _lm(0.5, 0.6)
    frame[26] = _lm(0.5, 0.8)
    return frame


# --- Aturan e: dominan lutut (vertikal) → squat ---


def test_large_knee_rom_returns_squat():
    frames = [
        _make_frame(knee_angle=a, elbow_angle=170.0) for a in (170.0, 120.0, 80.0)
    ]
    assert detect_movement(frames, WIDTH, HEIGHT) == "squat"


# --- Aturan d: dominan siku (vertikal) → curl / overhead_press / row ---


def test_elbow_dominant_vertical_returns_curl():
    # Badan vertikal + siku dominan + bahu tak bergerak → curl (bukan pushup;
    # pushup pada pohon baru mensyaratkan tubuh mendatar).
    frames = [
        _make_frame(knee_angle=170.0, elbow_angle=a) for a in (170.0, 80.0)
    ]
    assert detect_movement(frames, WIDTH, HEIGHT) == "curl"


def test_both_move_larger_rom_wins_squat():
    # Lutut dominan (ROM ~87°) vs siku (ROM ~48°) → squat.
    frames = [
        _make_frame(knee_angle=170.0, elbow_angle=170.0),
        _make_frame(knee_angle=80.0, elbow_angle=130.0),
    ]
    assert detect_movement(frames, WIDTH, HEIGHT) == "squat"


def test_both_move_elbow_dominant_returns_curl():
    # Siku dominan (ROM ~87°), lutut minor (ROM ~9° < 30°), bahu statis → curl.
    frames = [
        _make_frame(knee_angle=170.0, elbow_angle=170.0),
        _make_frame(knee_angle=150.0, elbow_angle=80.0),
    ]
    assert detect_movement(frames, WIDTH, HEIGHT) == "curl"


# --- Aturan a: tubuh mendatar → plank / pushup ---


def test_horizontal_with_knee_rom_returns_pushup():
    frames = [_make_horizontal_frame(knee_angle=a) for a in (170.0, 140.0)]
    assert detect_movement(frames, WIDTH, HEIGHT) == "pushup"


def test_horizontal_static_returns_plank():
    frames = [_make_horizontal_frame(knee_angle=170.0) for _ in range(4)]
    assert detect_movement(frames, WIDTH, HEIGHT) == "plank"


# --- Aturan b: asimetri kiri-kanan → lunge ---


def test_knee_asymmetry_returns_lunge():
    # Lutut kiri bergerak dalam (ROM ~87°), kanan nyaris diam (ROM ~9°).
    frames = [
        _make_frame(knee_angle=170.0, right_knee_angle=170.0),
        _make_frame(knee_angle=80.0, right_knee_angle=150.0),
    ]
    assert detect_movement(frames, WIDTH, HEIGHT) == "lunge"


# --- Aturan c: hip hinge → deadlift ---


def test_torso_hinge_returns_deadlift():
    frames = [_make_deadlift_frame(t) for t in (0.0, 0.5, 1.0)]
    assert detect_movement(frames, WIDTH, HEIGHT) == "deadlift"


# --- Aturan d: overhead_press vs row (wrist_up_ratio) ---


def test_wrist_above_shoulder_returns_overhead_press():
    # Siku bergerak (ROM ~77°), wrist naik jelas di atas bahu di separuh frame.
    frames = [
        _make_press_frame(elbow_xy=(0.32, 0.5), wrist_xy=(0.45, 0.45)),
        _make_press_frame(elbow_xy=(0.3, 0.05), wrist_xy=(0.36, -0.15)),
    ]
    assert detect_movement(frames, WIDTH, HEIGHT) == "overhead_press"


def test_wrist_never_above_shoulder_returns_row():
    # Siku bergerak (ROM ~54°) tetapi wrist tidak pernah di atas bahu → row.
    frames = [
        _make_press_frame(elbow_xy=(0.32, 0.5), wrist_xy=(0.45, 0.55)),
        _make_press_frame(elbow_xy=(0.2, 0.42), wrist_xy=(0.1, 0.5)),
    ]
    assert detect_movement(frames, WIDTH, HEIGHT) == "row"


# --- Fallback (aturan f): video statis / data tidak layak ---


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


def test_rom_below_threshold_is_treated_static():
    frames = [_make_frame(knee_angle=a) for a in (160.0, 145.0)]  # ROM ~17°
    assert detect_movement(frames, WIDTH, HEIGHT) == "squat"
