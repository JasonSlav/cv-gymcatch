"""Unit test untuk src/pose_estimator.py.

Test ini TIDAK memerlukan file model .task.
Fokus ke logika konversi, dataclass, dan konstanta.
Class PoseEstimator diuji hanya untuk jalur error (model tidak ada).
"""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.pose_estimator import (  # noqa: E402
    DEFAULT_MODEL_PATH,
    LEFT_ANKLE,
    LEFT_ELBOW,
    LEFT_HIP,
    LEFT_KNEE,
    LEFT_SHOULDER,
    LEFT_WRIST,
    NUM_LANDMARKS,
    RIGHT_ANKLE,
    RIGHT_ELBOW,
    RIGHT_HIP,
    RIGHT_KNEE,
    RIGHT_SHOULDER,
    RIGHT_WRIST,
    Landmark,
    PoseEstimator,
    PoseEstimatorError,
    PoseResult,
    angle_from_landmarks,
    convert_result,
)


# --- Fake helper untuk mensimulasi MediaPipe NormalizedLandmark ---

class _FakeMPLandmark:
    def __init__(self, x, y, z=0.0, visibility=1.0):
        self.x = x
        self.y = y
        self.z = z
        self.visibility = visibility


class _FakeMPResult:
    def __init__(self, pose_landmarks):
        self.pose_landmarks = pose_landmarks


def _make_mp_landmarks(n=33, visibility=0.9):
    return [_FakeMPLandmark(x=0.5, y=0.5, z=0.0, visibility=visibility) for _ in range(n)]


# --- Konstanta landmark ---

def test_landmark_index_constants_match_mediapipe():
    assert LEFT_SHOULDER == 11
    assert RIGHT_SHOULDER == 12
    assert LEFT_ELBOW == 13
    assert RIGHT_ELBOW == 14
    assert LEFT_WRIST == 15
    assert RIGHT_WRIST == 16
    assert LEFT_HIP == 23
    assert RIGHT_HIP == 24
    assert LEFT_KNEE == 25
    assert RIGHT_KNEE == 26
    assert LEFT_ANKLE == 27
    assert RIGHT_ANKLE == 28


def test_num_landmarks_is_33():
    assert NUM_LANDMARKS == 33


# --- Landmark dataclass ---

def test_landmark_to_xy():
    lm = Landmark(x=0.25, y=0.75, z=0.1, visibility=0.9)
    assert lm.to_xy() == (0.25, 0.75)


def test_landmark_to_xyz():
    lm = Landmark(x=0.25, y=0.75, z=0.1, visibility=0.9)
    assert lm.to_xyz() == (0.25, 0.75, 0.1)


def test_landmark_to_pixel():
    lm = Landmark(x=0.5, y=0.5, z=0.0, visibility=1.0)
    assert lm.to_pixel(640, 480) == (320.0, 240.0)


# --- PoseResult ---

def test_pose_result_default_is_not_detected():
    r = PoseResult()
    assert r.detected is False
    assert r.get(0) is None


def test_pose_result_get_returns_landmark():
    lms = [Landmark(0.1, 0.2, 0.0, 1.0)] * 33
    r = PoseResult(landmarks=lms)
    assert r.detected is True
    assert r.get(0) is lms[0]
    assert r.get(32) is lms[32]


def test_pose_result_get_out_of_range_returns_none():
    lms = [Landmark(0.1, 0.2, 0.0, 1.0)] * 33
    r = PoseResult(landmarks=lms)
    assert r.get(99) is None
    assert r.get(-1) is None


# --- convert_result ---

def test_convert_result_none_input():
    r = convert_result(None)
    assert r.detected is False


def test_convert_result_no_pose_landmarks():
    r = convert_result(_FakeMPResult(pose_landmarks=[]))
    assert r.detected is False


def test_convert_result_empty_first_person():
    r = convert_result(_FakeMPResult(pose_landmarks=[[]]))
    assert r.detected is False


def test_convert_result_happy_path():
    fake = _FakeMPResult(pose_landmarks=[_make_mp_landmarks(33, visibility=0.8)])
    r = convert_result(fake)
    assert r.detected is True
    assert len(r.landmarks) == 33
    assert r.landmarks[0].visibility == pytest.approx(0.8)
    assert r.landmarks[0].x == pytest.approx(0.5)


def test_convert_result_takes_first_person_only():
    person_a = [_FakeMPLandmark(x=0.1, y=0.1, visibility=1.0)] * 33
    person_b = [_FakeMPLandmark(x=0.9, y=0.9, visibility=1.0)] * 33
    fake = _FakeMPResult(pose_landmarks=[person_a, person_b])
    r = convert_result(fake)
    assert r.landmarks[0].x == pytest.approx(0.1)  # orang pertama


def test_convert_result_missing_visibility_defaults_to_one():
    lm = _FakeMPLandmark(x=0.5, y=0.5, z=0.0)
    del lm.visibility  # hapus atribut visibility
    fake = _FakeMPResult(pose_landmarks=[[lm] * 33])
    r = convert_result(fake)
    assert r.landmarks[0].visibility == pytest.approx(1.0)


# --- PoseEstimator: jalur error saja ---

def test_pose_estimator_raises_when_model_missing(tmp_path):
    missing = tmp_path / "tidak_ada.task"
    with pytest.raises(PoseEstimatorError, match="tidak ditemukan"):
        PoseEstimator(model_path=missing)


def test_pose_estimator_detect_raises_when_frame_none():
    # Buat instance tanpa load model asli — kita hanya uji guard frame kosong.
    # Trik: panggil detect lewat objek yang belum di-__init__ penuh.
    est = PoseEstimator.__new__(PoseEstimator)
    est._detector = None
    est._closed = False
    with pytest.raises(PoseEstimatorError, match="Frame kosong"):
        est.detect(None, timestamp_ms=0)
    with pytest.raises(PoseEstimatorError, match="Frame kosong"):
        est.detect(np.zeros((0, 0, 3), dtype=np.uint8), timestamp_ms=0)


def test_pose_estimator_detect_raises_when_closed():
    est = PoseEstimator.__new__(PoseEstimator)
    est._detector = None
    est._closed = True
    with pytest.raises(PoseEstimatorError, match="sudah ditutup"):
        est.detect(np.zeros((10, 10, 3), dtype=np.uint8), timestamp_ms=0)


def test_pose_estimator_close_is_idempotent():
    class _FakeDetector:
        def __init__(self):
            self.closed = 0

        def close(self):
            self.closed += 1

    est = PoseEstimator.__new__(PoseEstimator)
    est._detector = _FakeDetector()
    est._closed = False
    est.close()
    est.close()
    assert est._detector.closed == 1
    assert est._closed is True


# --- angle_from_landmarks (ruang piksel) ---

def test_angle_from_landmarks_matches_pixel_calculation():
    from src.geometry import calculate_angle
    hip = Landmark(0.5, 0.3, 0.0, 1.0)
    knee = Landmark(0.5, 0.6, 0.0, 1.0)
    ankle = Landmark(0.5, 0.9, 0.0, 1.0)
    a = angle_from_landmarks(hip, knee, ankle, 640, 480)
    # Manual: (320,144),(320,288),(320,432) → koliner → 180°
    expected = calculate_angle((320, 144), (320, 288), (320, 432))
    assert a == pytest.approx(expected)
    assert a == pytest.approx(180.0)


def test_angle_from_landmarks_differs_from_normalized_when_aspect_ratio_not_one():
    from src.geometry import calculate_angle
    # Titik NON-kolineer (kolineer akan lolos di kedua ruang — skala anisotropik
    # memelihara kolinearitas, jadi harus pakai konfigurasi umum).
    hip = Landmark(0.3, 0.3, 0.0, 1.0)
    knee = Landmark(0.5, 0.6, 0.0, 1.0)
    ankle = Landmark(0.8, 0.7, 0.0, 1.0)
    a_pixel = angle_from_landmarks(hip, knee, ankle, 640, 480)
    a_norm = calculate_angle(hip.to_xy(), knee.to_xy(), ankle.to_xy())
    # Bug lama: dua nilai ini beda (145.67 vs 142.13) → regresi ini menjaga
    # kita tetap di ruang piksel
    assert a_pixel != pytest.approx(a_norm, abs=0.5)


def test_angle_from_landmarks_returns_none_for_missing():
    hip = Landmark(0.5, 0.3, 0.0, 1.0)
    assert angle_from_landmarks(None, hip, hip, 640, 480) is None
    assert angle_from_landmarks(hip, None, hip, 640, 480) is None
    assert angle_from_landmarks(hip, hip, None, 640, 480) is None


def test_angle_from_landmarks_returns_none_for_low_visibility():
    low = Landmark(0.5, 0.3, 0.0, 0.3)
    ok = Landmark(0.5, 0.6, 0.0, 1.0)
    assert angle_from_landmarks(low, ok, ok, 640, 480, min_visibility=0.5) is None
    assert angle_from_landmarks(low, ok, ok, 640, 480, min_visibility=0.2) is not None
