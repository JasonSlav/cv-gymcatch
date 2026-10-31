"""
Konfigurasi gerakan PUSH-UP.

Sudut yang dianalisis: sudut siku (shoulder → elbow → wrist).
"""

from __future__ import annotations

from src.movements.base import FeedbackRules, MovementConfig

PUSHUP_CONFIG = MovementConfig(
    name="pushup",
    joint_name="elbow",

    # Kiri: shoulder(11) → elbow(13) → wrist(15)
    parent_idx=11,
    joint_idx=13,
    child_idx=15,

    # Kanan: shoulder(12) → elbow(14) → wrist(16)
    right_parent_idx=12,
    right_joint_idx=14,
    right_child_idx=16,

    # Lengan lurus > 150°, dada rendah < 90°
    up_threshold=150.0,
    down_threshold=90.0,

    feedback_rules=FeedbackRules(
        deep_rom_deg=90.0,
        good_rom_deg=120.0,
        low_rom="Kedalaman push-up kurang. Turunkan dada lebih dekat ke lantai.",
        good_rom="Kedalaman push-up sudah sangat baik.",
        low_consistency="Gerakan push-up kurang konsisten. Jaga tempo turun-naik.",
        low_stability=(
            "Pinggul terlalu banyak bergoyang. "
            "Kencangkan core saat push-up."
        ),
    ),
)
