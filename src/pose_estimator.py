"""
Modul pose estimation — satu-satunya jembatan ke MediaPipe Tasks API.

Filosofi:
- Modul lain (metrics, visualize, movements) TIDAK boleh import mediapipe.
- Semua tipe MediaPipe dikonversi ke dataclass netral (Landmark, PoseResult).
- Logika konversi (`convert_result`) murni dan bisa di-unit-test tanpa model.

Referensi:
- MediaPipe 1.1.1 Tasks API (mp.solutions sudah dihapus).
- Model: models/pose_landmarker_full.task
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
import numpy as np

from src.geometry import calculate_angle


# --- Konstanta indeks landmark MediaPipe Pose (33 titik) ---
# Referensi: https://developers.google.com/mediapipe/solutions/vision/pose_landmarker
NOSE = 0
LEFT_SHOULDER = 11
RIGHT_SHOULDER = 12
LEFT_ELBOW = 13
RIGHT_ELBOW = 14
LEFT_WRIST = 15
RIGHT_WRIST = 16
LEFT_HIP = 23
RIGHT_HIP = 24
LEFT_KNEE = 25
RIGHT_KNEE = 26
LEFT_ANKLE = 27
RIGHT_ANKLE = 28

NUM_LANDMARKS = 33

DEFAULT_MODEL_PATH = Path("models/pose_landmarker_full.task")


class PoseEstimatorError(Exception):
    """Error saat inisialisasi atau inferensi pose."""


@dataclass(frozen=True)
class Landmark:
    """
    Satu landmark pose, dalam koordinat ternormalisasi.

    x, y : float di [0, 1] — relatif terhadap lebar/tinggi frame.
    z    : float — kedalaman relatif (bukan skala absolut).
    visibility : float di [0, 1] — seberapa yakin landmark terlihat.
    """

    x: float
    y: float
    z: float
    visibility: float

    def to_pixel(self, width: int, height: int) -> tuple:
        """Konversi ke koordinat piksel (x_px, y_px)."""
        return (self.x * width, self.y * height)

    def to_xyz(self) -> tuple:
        """Tuple (x, y, z) — untuk input ke src.geometry."""
        return (self.x, self.y, self.z)

    def to_xy(self) -> tuple:
        """Tuple (x, y) — proyeksi 2D untuk analisis sudut."""
        return (self.x, self.y)


@dataclass
class PoseResult:
    """
    Hasil deteksi pose untuk satu frame.

    landmarks : list[Landmark] | None
        - None jika tidak ada pose terdeteksi.
        - list berisi NUM_LANDMARKS (33) elemen jika terdeteksi.
    """

    landmarks: Optional[List[Landmark]] = None

    @property
    def detected(self) -> bool:
        return self.landmarks is not None and len(self.landmarks) > 0

    def get(self, idx: int) -> Optional[Landmark]:
        """Ambil landmark ke-idx. Return None jika tidak terdeteksi atau idx invalid."""
        if not self.detected:
            return None
        if 0 <= idx < len(self.landmarks):
            return self.landmarks[idx]
        return None


def _landmark_from_mp(mp_lm) -> Landmark:
    """
    Konversi satu landmark MediaPipe (NormalizedLandmark) ke dataclass kita.

    NormalizedLandmark memiliki atribut .x, .y, .z, .visibility, .presence.
    Kita pakai .visibility (bukan .presence) karena lebih relevan untuk
    menentukan apakah landmark cukup terlihat untuk dianalisis.
    """
    return Landmark(
        x=float(mp_lm.x),
        y=float(mp_lm.y),
        z=float(mp_lm.z),
        visibility=float(getattr(mp_lm, "visibility", 1.0)),
    )


def convert_result(mp_result) -> PoseResult:
    """
    Konversi hasil MediaPipe (PoseLandmarkerResult) ke PoseResult kita.

    Murni — tidak menyentuh MediaPipe runtime. Bisa di-test dengan fake object
    yang punya atribut `.pose_landmarks` berupa list[list[objek dengan .x/.y/.z/.visibility]].

    Kebijakan:
    - Ambil orang pertama saja (`pose_landmarks[0]`).
    - Kalau tidak ada orang → PoseResult(landmarks=None).
    - Kalau ada orang tapi landmark kurang dari NUM_LANDMARKS → tetap diteruskan;
      validasi jumlah jadi tanggung jawab pemanggil.
    """
    if mp_result is None:
        return PoseResult(landmarks=None)

    pose_landmarks = getattr(mp_result, "pose_landmarks", None)
    if not pose_landmarks:
        return PoseResult(landmarks=None)

    first_person = pose_landmarks[0]
    if not first_person:
        return PoseResult(landmarks=None)

    landmarks = [_landmark_from_mp(lm) for lm in first_person]
    return PoseResult(landmarks=landmarks)


DEFAULT_MIN_VISIBILITY = 0.5


def angle_from_landmarks(
    lm_a: Optional[Landmark],
    lm_b: Optional[Landmark],
    lm_c: Optional[Landmark],
    width: int,
    height: int,
    min_visibility: float = DEFAULT_MIN_VISIBILITY,
) -> Optional[float]:
    """
    Hitung sudut di lm_b (derajat) menggunakan koordinat PIKSEL.

    Kenapa piksel, bukan ternormalisasi?
    - Ruang ternormalisasi [0,1] anisotropik: x diskalakan oleh width,
      y oleh height. Sudut di ruang ini ≠ sudut di ruang piksel ketika
      aspect ratio ≠ 1.
    - Konvensi PROJECT.md §6.1: sudut dihitung pada proyeksi 2D frame
      (piksel), sesuai PoC lama.

    Return None jika salah satu landmark None atau visibility < min_visibility.
    """
    if lm_a is None or lm_b is None or lm_c is None:
        return None
    if min(lm_a.visibility, lm_b.visibility, lm_c.visibility) < min_visibility:
        return None
    return calculate_angle(
        lm_a.to_pixel(width, height),
        lm_b.to_pixel(width, height),
        lm_c.to_pixel(width, height),
    )


class PoseEstimator:
    """
    Wrapper tipis MediaPipe PoseLandmarker (Tasks API).

    Pemakaian:
        estimator = PoseEstimator(model_path="models/pose_landmarker_full.task")
        try:
            for idx, frame_bgr in iter_frames(video):
                result = estimator.detect(frame_bgr, timestamp_ms=int(idx * 33))
                # pakai result.landmarks ...
        finally:
            estimator.close()

    Catatan:
    - detect() menerima frame BGR (cv2 default), bukan RGB.
    - timestamp_ms harus monoton naik per video (MediaPipe syarat).
    """

    def __init__(
        self,
        model_path=DEFAULT_MODEL_PATH,
        num_poses: int = 1,
        min_pose_detection_confidence: float = 0.5,
        min_pose_presence_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
    ):
        model_path = Path(model_path)
        if not model_path.exists():
            raise PoseEstimatorError(
                f"File model tidak ditemukan: {model_path}. "
                f"Unduh dari https://storage.googleapis.com/mediapipe-models/"
                f"pose_landmarker/pose_landmarker_full/float16/latest/"
                f"pose_landmarker_full.task"
            )

        base_options = mp_python.BaseOptions(model_asset_path=str(model_path))
        options = mp_vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=mp_vision.RunningMode.VIDEO,
            num_poses=num_poses,
            min_pose_detection_confidence=min_pose_detection_confidence,
            min_pose_presence_confidence=min_pose_presence_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )
        try:
            self._detector = mp_vision.PoseLandmarker.create_from_options(options)
        except Exception as e:
            raise PoseEstimatorError(f"Gagal membuat PoseLandmarker: {e}") from e

        self._closed = False

    def detect(self, frame_bgr: np.ndarray, timestamp_ms: int) -> PoseResult:
        """
        Deteksi pose pada satu frame.

        Parameter
        ---------
        frame_bgr : np.ndarray
            Frame BGR (dari cv2.VideoCapture.read()).
        timestamp_ms : int
            Timestamp monoton naik dalam milidetik.

        Returns
        -------
        PoseResult
            Hasil deteksi. `.landmarks` None jika tidak ada pose.

        Raises
        ------
        PoseEstimatorError
            Jika estimator sudah ditutup atau frame tidak valid.
        """
        if self._closed:
            raise PoseEstimatorError("Estimator sudah ditutup (close() dipanggil).")
        if frame_bgr is None or frame_bgr.size == 0:
            raise PoseEstimatorError("Frame kosong atau None.")

        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        raw_result = self._detector.detect_for_video(mp_image, int(timestamp_ms))
        return convert_result(raw_result)

    def close(self) -> None:
        """Release resource MediaPipe. Aman dipanggil berkali-kali."""
        if self._closed:
            return
        try:
            self._detector.close()
        finally:
            self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
