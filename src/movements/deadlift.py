"""
Konfigurasi gerakan DEADLIFT (hip hinge).

Sudut yang dianalisis: sudut pinggul (shoulder → hip → knee).
"""

from __future__ import annotations

from src.movements.base import FeedbackRules, MovementConfig

DEADLIFT_CONFIG = MovementConfig(
    name="deadlift",
    joint_name="hip",

    # Kiri: shoulder(11) → hip(23) → knee(25)
    parent_idx=11,
    joint_idx=23,
    child_idx=25,

    # Kanan: shoulder(12) → hip(24) → knee(26)
    right_parent_idx=12,
    right_joint_idx=24,
    right_child_idx=26,

    # Tegak > 170°, hinge dalam < 90°
    up_threshold=170.0,
    down_threshold=90.0,

    feedback_rules=FeedbackRules(
        deep_rom_deg=50.0,
        good_rom_deg=65.0,
        low_rom="Rentang gerak pinggul kurang. Turunkan torso lebih dalam saat hinge.",
        good_rom="Rentang gerak hip hinge sudah sangat baik.",
        low_consistency=(
            "Gerakan deadlift kurang konsisten. "
            "Jaga tempo hinge & posisi punggung lurus."
        ),
        low_stability=(
            "Punggung melengkung/tubuh goyang. "
            "Kencangkan core & dada terbuka."
        ),
    ),
)
