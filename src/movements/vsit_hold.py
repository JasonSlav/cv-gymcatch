"""
Konfigurasi gerakan V-SIT HOLD (isometrik/tahan posisi).

Sudut yang dianalisis: sudut torso (shoulder → hip → knee). Kamera: samping.
Gerakan statis: skor ROM memakai referensi kecil (40°) karena rentang gerak
memang minimal saat posisi ditahan.
"""

from __future__ import annotations

from src.movements.base import FeedbackRules, MovementConfig

VSIT_HOLD_CONFIG = MovementConfig(
    name="vsit_hold",
    joint_name="torso",
    camera_angle="side",

    # Kiri: shoulder(11) → hip(23) → knee(25)
    parent_idx=11,
    joint_idx=23,
    child_idx=25,

    # Kanan: shoulder(12) → hip(24) → knee(26)
    right_parent_idx=12,
    right_joint_idx=24,
    right_child_idx=26,

    # Ambang state machine (tahan posisi): 90°–130°.
    up_threshold=130.0,
    down_threshold=90.0,

    # V-Sit memang ROM kecil karena statis.
    rom_reference=40.0,
    exercise_type="static",
    target_duration_sec=30.0,

    feedback_rules=FeedbackRules(
        deep_rom_deg=40.0,
        good_rom_deg=45.0,
        low_rom="Posisi tahan V-Sit sudah dalam, pertahankan!",
        good_rom="Posisi tahan V-Sit sudah sangat baik.",
        low_consistency="Posisi tahan sudah stabil. Pertahankan!",
        low_stability=(
            "Tubuh bergoyang. Kencangkan otot perut dan punggung."
        ),
    ),
)
