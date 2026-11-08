"""
Konfigurasi gerakan LATERAL RAISE.

Sudut yang dianalisis: sudut bahu (hip → shoulder → elbow).
"""

from __future__ import annotations

from src.movements.base import FeedbackRules, MovementConfig

LATERAL_RAISE_CONFIG = MovementConfig(
    name="lateral_raise",
    joint_name="shoulder",

    # Kiri: hip(23) → shoulder(11) → elbow(13)
    parent_idx=23,
    joint_idx=11,
    child_idx=13,

    # Kanan: hip(24) → shoulder(12) → elbow(14)
    right_parent_idx=24,
    right_joint_idx=12,
    right_child_idx=14,

    # Lengan di samping tubuh > 160°, terangkat sejajar bahu < 80°
    up_threshold=160.0,
    down_threshold=80.0,

    feedback_rules=FeedbackRules(
        deep_rom_deg=50.0,
        good_rom_deg=65.0,
        low_rom="ROM lateral raise kurang. Angkat lengan hingga sejajar bahu.",
        good_rom="ROM lateral raise sudah sangat baik.",
        low_consistency=(
            "Gerakan lateral raise kurang konsisten. "
            "Jaga tempo angkat & turunkan terkontrol."
        ),
        low_stability=(
            "Tubuh berayun memakai momentum. "
            "Turunkan beban & kencangkan core."
        ),
    ),
)
