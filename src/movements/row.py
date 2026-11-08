"""
Konfigurasi gerakan ROW (baris).

Sudut yang dianalisis: sudut siku (shoulder → elbow → wrist).
"""

from __future__ import annotations

from src.movements.base import FeedbackRules, MovementConfig

ROW_CONFIG = MovementConfig(
    name="row",
    joint_name="elbow",

    # Kiri: shoulder(11) → elbow(13) → wrist(15)
    parent_idx=11,
    joint_idx=13,
    child_idx=15,

    # Kanan: shoulder(12) → elbow(14) → wrist(16)
    right_parent_idx=12,
    right_joint_idx=14,
    right_child_idx=16,

    # Lengan lurus > 150°, siku tertarik < 70°
    up_threshold=150.0,
    down_threshold=70.0,

    feedback_rules=FeedbackRules(
        deep_rom_deg=50.0,
        good_rom_deg=65.0,
        low_rom="ROM row kurang. Tarik siku lebih dekat ke tubuh.",
        good_rom="ROM row sudah sangat baik.",
        low_consistency=(
            "Gerakan row kurang konsisten. "
            "Jaga tempo tarik & turunkan terkontrol."
        ),
        low_stability=(
            "Torso terlalu banyak bergerak. "
            "Tegakkan torso & kencangkan core."
        ),
    ),
)
