"""
Auto-detect gerakan berbasis heuristic ROM (matematika murni, bukan ML).

Idenya: sendi yang paling banyak bergerak pada beberapa frame pertama
menentukan jenis gerakan — ROM lutut dominan → squat, ROM siku dominan →
push-up. Bila tidak ada yang cukup bergerak (video statis/tidak jelas),
kembali ke default "squat".

Modul ini murni: hanya bergantung pada src.geometry (calculate_angle) dan
tidak mengenal MediaPipe/OpenCV. Landmark dibaca duck-typed (atribut
.x/.y/.visibility) sehingga bisa diuji dengan data dummy.
"""

from __future__ import annotations

from typing import Optional

from src.geometry import calculate_angle

# Indeks landmark MediaPipe Pose (33 titik).
# Lutut: hip-knee-ankle; siku: shoulder-elbow-wrist (kiri & kanan).
KNEE_TRIPLETS = ((23, 25, 27), (24, 26, 28))
ELBOW_TRIPLETS = ((11, 13, 15), (12, 14, 16))

# Batas frame yang dipakai (rentang instruksi: 30-50 frame pertama).
AUTO_DETECT_MAX_FRAMES = 50

# Ambang minimum ROM (derajat) agar gerakan dianggap nyata.
AUTO_DETECT_MIN_ROM_DEG = 20.0

# Konsisten dengan ambang visibility pipeline.
MIN_VISIBILITY = 0.5

# Fallback bila video statis/tidak jelas.
DEFAULT_MOVEMENT = "squat"


def _frame_angle(landmarks, triplet, width: int, height: int) -> Optional[float]:
    """Sudut satu triplet pada satu frame; None bila tidak layak ukur."""
    if not landmarks or len(landmarks) <= max(triplet):
        return None
    pts = []
    for idx in triplet:
        lm = landmarks[idx]
        if lm is None or getattr(lm, "visibility", 1.0) < MIN_VISIBILITY:
            return None
        # Konversi ke piksel — sudut di ruang piksel (koreksi aspect ratio),
        # konvensi sama dengan angle_from_landmarks di pose_estimator.
        pts.append((lm.x * width, lm.y * height))
    return calculate_angle(pts[0], pts[1], pts[2])


def _rom_deg(landmarks_history, triplets, width: int, height: int) -> Optional[float]:
    """ROM (max-min, derajat) gabungan kedua sisi dari seluruh sudut valid."""
    angles = []
    for landmarks in landmarks_history[:AUTO_DETECT_MAX_FRAMES]:
        for triplet in triplets:
            angle = _frame_angle(landmarks, triplet, width, height)
            if angle is not None:
                angles.append(angle)
    if not angles:
        return None
    return max(angles) - min(angles)


def detect_movement(landmarks_history, width: int, height: int) -> str:
    """
    Tebak jenis gerakan dari ROM lutut vs siku (heuristic).

    Parameter
    ---------
    landmarks_history : sequence
        List per-frame landmark (masing-masing None atau list objek dengan
        atribut .x/.y ternormalisasi dan .visibility).
    width, height : int
        Dimensi frame (piksel) untuk konversi koordinat.

    Returns
    -------
    str
        "squat" | "pushup". ROM di bawah ambang / data kosong → default.
    """
    knee_rom = _rom_deg(landmarks_history, KNEE_TRIPLETS, width, height)
    elbow_rom = _rom_deg(landmarks_history, ELBOW_TRIPLETS, width, height)

    knee_ok = knee_rom is not None and knee_rom > AUTO_DETECT_MIN_ROM_DEG
    elbow_ok = elbow_rom is not None and elbow_rom > AUTO_DETECT_MIN_ROM_DEG

    if knee_ok and not elbow_ok:
        return "squat"
    if elbow_ok and not knee_ok:
        return "pushup"
    if knee_ok and elbow_ok:
        # Keduanya cukup bergerak: pilih ROM terbesar (seri → squat).
        return "squat" if knee_rom >= elbow_rom else "pushup"
    return DEFAULT_MOVEMENT
