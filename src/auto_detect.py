"""
Auto-detect gerakan berbasis Decision Tree (matematika murni, bukan ML).

Membedakan 12 arketype gerakan (src/movements/) dari fitur postur tubuh
yang diekstrak dari maksimal 50 frame pertama:
- is_horizontal        : tubuh mendatar → plank (statis) / pushup (siku bergerak)
- left_right_diff      : asimetri ROM lutut kiri-kanan → lunge
- torso_angle_change   : perubahan sudut punggung/pinggul → deadlift
- elbow_rom + wrist_up_ratio + shoulder_rom → overhead_press / row / curl
- knee_rom dominan     → squat
- fallback             → squat (video statis/tidak jelas)

Modul ini murni: hanya bergantung pada src.geometry (calculate_angle) dan
tidak mengenal MediaPipe/OpenCV. Landmark dibaca duck-typed (atribut
.x/.y/.visibility) sehingga bisa diuji dengan data dummy.
"""

from __future__ import annotations

from typing import Optional

from src.geometry import calculate_angle

# Indeks landmark MediaPipe Pose (33 titik) — triplet sudut per sendi.
KNEE_TRIPLETS = ((23, 25, 27), (24, 26, 28))      # hip → knee → ankle
ELBOW_TRIPLETS = ((11, 13, 15), (12, 14, 16))     # shoulder → elbow → wrist
TORSO_TRIPLETS = ((11, 23, 25), (12, 24, 26))     # shoulder → hip → knee (hip hinge)
SHOULDER_TRIPLETS = ((23, 11, 13), (24, 12, 14))  # hip → shoulder → elbow

# Batas frame yang dipakai (rentang instruksi: 30-50 frame pertama).
AUTO_DETECT_MAX_FRAMES = 50

# Ambang visibility landmark (konsisten dengan pipeline).
MIN_VISIBILITY = 0.5

# Legacy: ambang ROM tunggal logika lama (dipertahankan demi kompatibilitas;
# pohon keputusan baru memakai ambang spesifik per aturan).
AUTO_DETECT_MIN_ROM_DEG = 20.0

# Fallback bila video statis/tidak jelas.
DEFAULT_MOVEMENT = "squat"

# --- Ambang pohon keputusan ---
HORIZONTAL_MAX_DY = 0.15     # |meanY bahu − meanY pinggul| < 0.15 → tubuh mendatar
PLANK_MAX_KNEE_ROM = 15.0    # mendatar + knee < 15° → plank, selain itu pushup
ASYM_DIFF_DEG = 30.0         # |ROM knee kiri − kanan| > 30° → lunge
TORSO_CHANGE_DEG = 40.0      # perubahan sudut torso > 40° → deadlift
ELBOW_DOMINANT_DEG = 40.0    # ROM siku > 40° (dan knee < 30°) → gerakan lengan
KNEE_DOMINANT_DEG = 40.0     # ROM lutut > 40° → squat
SHOULDER_ROM_DEG = 20.0      # ROM bahu > 20° → OHP/row; else curl
WRIST_UP_MIN_DY = 0.05       # wrist "di atas" bahu bila selisih Y ternormalisasi > 0.05
WRIST_UP_RATIO = 0.15        # TODO: kalibrasi ulang dengan video OHP/Row nyata


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
    """ROM (max-min, derajat) gabungan seluruh triplet dari sudut valid."""
    angles = []
    for landmarks in landmarks_history:
        for triplet in triplets:
            angle = _frame_angle(landmarks, triplet, width, height)
            if angle is not None:
                angles.append(angle)
    if not angles:
        return None
    return max(angles) - min(angles)


def _rom_side(landmarks_history, triplet, width: int, height: int) -> Optional[float]:
    """ROM satu sisi saja (untuk deteksi asimetri kiri-kanan)."""
    angles = []
    for landmarks in landmarks_history:
        angle = _frame_angle(landmarks, triplet, width, height)
        if angle is not None:
            angles.append(angle)
    if not angles:
        return None
    return max(angles) - min(angles)


def _mean_y(landmarks_history, idx: int) -> Optional[float]:
    """Rata-rata Y ternormalisasi landmark idx; None bila tak ada frame valid."""
    ys = []
    for landmarks in landmarks_history:
        if not landmarks or len(landmarks) <= idx:
            continue
        lm = landmarks[idx]
        if lm is None or getattr(lm, "visibility", 1.0) < MIN_VISIBILITY:
            continue
        ys.append(lm.y)
    if not ys:
        return None
    return sum(ys) / len(ys)


def _is_horizontal(landmarks_history) -> bool:
    """True bila bahu & pinggul berada pada ketinggian serupa (tubuh mendatar).

    Mencoba sisi kiri (11/23) terlebih dahulu, lalu kanan (12/24) bila kiri
    tidak terlihat.
    """
    for shoulder_idx, hip_idx in ((11, 23), (12, 24)):
        shoulder_y = _mean_y(landmarks_history, shoulder_idx)
        hip_y = _mean_y(landmarks_history, hip_idx)
        if shoulder_y is None or hip_y is None:
            continue
        if abs(shoulder_y - hip_y) < HORIZONTAL_MAX_DY:
            return True
    return False


def _wrist_up_ratio(landmarks_history) -> Optional[float]:
    """Fraksi frame valid dengan wrist jelas di atas bahu (indikasi overhead)."""
    above = 0
    total = 0
    for landmarks in landmarks_history:
        frame_has_data = False
        frame_above = False
        for shoulder_idx, wrist_idx in ((11, 15), (12, 16)):
            if not landmarks or len(landmarks) <= max(shoulder_idx, wrist_idx):
                continue
            sh = landmarks[shoulder_idx]
            wr = landmarks[wrist_idx]
            if sh is None or wr is None:
                continue
            if getattr(sh, "visibility", 1.0) < MIN_VISIBILITY:
                continue
            if getattr(wr, "visibility", 1.0) < MIN_VISIBILITY:
                continue
            frame_has_data = True
            if sh.y - wr.y > WRIST_UP_MIN_DY:
                frame_above = True
        if frame_has_data:
            total += 1
            if frame_above:
                above += 1
    if total == 0:
        return None
    return above / total


def _extract_features(landmarks_history, width: int, height: int) -> dict:
    """Ekstrak seluruh fitur pohon keputusan dari maks 50 frame pertama."""
    frames = landmarks_history[:AUTO_DETECT_MAX_FRAMES]

    knee_rom = _rom_deg(frames, KNEE_TRIPLETS, width, height)
    elbow_rom = _rom_deg(frames, ELBOW_TRIPLETS, width, height)
    shoulder_rom = _rom_deg(frames, SHOULDER_TRIPLETS, width, height)

    # Hip hinge memakai triplet yang sama dengan torso (11-23-25) → hip_rom
    # identik dengan torso_angle_change; diekspos sebagai fitur namun tidak
    # dipakai di pohon keputusan.
    hip_rom = _rom_deg(frames, TORSO_TRIPLETS, width, height)
    torso_angle_change = hip_rom

    rom_left = _rom_side(frames, KNEE_TRIPLETS[0], width, height)
    rom_right = _rom_side(frames, KNEE_TRIPLETS[1], width, height)
    left_right_diff = (
        abs(rom_left - rom_right)
        if rom_left is not None and rom_right is not None
        else None
    )

    return {
        "is_horizontal": _is_horizontal(frames),
        "left_right_diff": left_right_diff,
        "torso_angle_change": torso_angle_change,
        "hip_rom": hip_rom,
        "elbow_rom": elbow_rom,
        "knee_rom": knee_rom,
        "shoulder_rom": shoulder_rom,
        "wrist_up_ratio": _wrist_up_ratio(frames),
    }


def detect_movement(landmarks_history, width: int, height: int) -> str:
    """
    Klasifikasikan gerakan via Decision Tree (urutan aturan penting).

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
        Salah satu kunci gerakan di src/movements/; fallback "squat".
    """
    feats = _extract_features(landmarks_history, width, height)

    # a. Tubuh mendatar → plank (lutut statis) atau pushup (lutut bergerak)
    if feats["is_horizontal"]:
        if feats["knee_rom"] is None or feats["knee_rom"] < PLANK_MAX_KNEE_ROM:
            return "plank"
        return "pushup"

    # b. Asimetri kiri-kanan → lunge
    if feats["left_right_diff"] is not None and feats["left_right_diff"] > ASYM_DIFF_DEG:
        return "lunge"

    # c. Hip hinge dominan → deadlift
    if (
        feats["torso_angle_change"] is not None
        and feats["torso_angle_change"] > TORSO_CHANGE_DEG
    ):
        return "deadlift"

    # d. Dominan siku → overhead_press / row / curl
    if (
        feats["elbow_rom"] is not None
        and feats["elbow_rom"] > ELBOW_DOMINANT_DEG
        and (feats["knee_rom"] is None or feats["knee_rom"] < KNEE_DOMINANT_DEG)
    ):
        if feats["shoulder_rom"] is not None and feats["shoulder_rom"] > SHOULDER_ROM_DEG:
            # TODO: kalibrasi ulang dengan video OHP/Row nyata
            if (
                feats["wrist_up_ratio"] is not None
                and feats["wrist_up_ratio"] > WRIST_UP_RATIO
            ):
                return "overhead_press"
            return "row"
        return "curl"

    # e. Dominan lutut → squat
    if feats["knee_rom"] is not None and feats["knee_rom"] > KNEE_DOMINANT_DEG:
        return "squat"

    # f. Video statis/tidak jelas → default
    return DEFAULT_MOVEMENT
