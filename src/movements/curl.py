"""
Konfigurasi gerakan CURL (biceps).

Sudut yang dianalisis: sudut siku (shoulder → elbow → wrist).
"""

from __future__ import annotations

from src.movements.base import FeedbackRules, MovementConfig

CURL_CONFIG = MovementConfig(
    name="curl",
    joint_name="elbow",

    # Kiri: shoulder(11) → elbow(13) → wrist(15)
    parent_idx=11,
    joint_idx=13,
    child_idx=15,

    # Kanan: shoulder(12) → elbow(14) → wrist(16)
    right_parent_idx=12,
    right_joint_idx=14,
    right_child_idx=16,

    # Lengan lurus > 160°, fleksi penuh < 40°
    up_threshold=160.0,
    down_threshold=40.0,

    feedback_rules=FeedbackRules(
        deep_rom_deg=70.0,
        good_rom_deg=100.0,
        low_rom="ROM curl kurang. Fleksikan lengan hingga penuh ke arah bahu.",
        good_rom="ROM curl sudah sangat baik.",
        low_consistency=(
            "Gerakan curl kurang konsisten. "
            "Jaga tempo angkat-turun & siku tetap diam."
        ),
        low_stability=(
            "Tubuh terlalu banyak berayun. "
            "Kencangkan core & jangan memakai momentum."
        ),
    ),
)
