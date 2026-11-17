"""
Konfigurasi gerakan BACK UP (back extension).

Sudut yang dianalisis: sudut pinggul (shoulder → hip → knee). Kamera: samping.
"""

from __future__ import annotations

from src.movements.base import FeedbackRules, MovementConfig

BACK_UP_CONFIG = MovementConfig(
    name="back_up",
    joint_name="hip",
    camera_angle="side",

    # Kiri: shoulder(11) → hip(23) → knee(25)
    parent_idx=11,
    joint_idx=23,
    child_idx=25,

    # Kanan: shoulder(12) → hip(24) → knee(26)
    right_parent_idx=12,
    right_joint_idx=24,
    right_child_idx=26,

    # Pinggul di matras > 170°, dada & kaki terangkat < 120°
    up_threshold=170.0,
    down_threshold=120.0,

    feedback_rules=FeedbackRules(
        deep_rom_deg=30.0,
        good_rom_deg=42.0,
        low_rom="Angkat dada & kaki lebih tinggi saat back extension.",
        good_rom="ROM back extension sudah sangat baik.",
        low_consistency=(
            "Gerakan back extension kurang konsisten. "
            "Jaga tempo angkat & turun terkontrol."
        ),
        low_stability=(
            "Gerakan memakai momentum ayunan. "
            "Angkat terkontrol dengan otot punggung."
        ),
    ),
)
