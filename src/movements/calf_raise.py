"""
Konfigurasi gerakan CALF RAISE.

Sudut yang dianalisis: sudut pergelangan kaki (knee → ankle → foot_index).
"""

from __future__ import annotations

from src.movements.base import FeedbackRules, MovementConfig

CALF_RAISE_CONFIG = MovementConfig(
    name="calf_raise",
    joint_name="ankle",

    # Kiri: knee(25) → ankle(27) → foot_index(31)
    parent_idx=25,
    joint_idx=27,
    child_idx=31,

    # Kanan: knee(26) → ankle(28) → foot_index(32)
    right_parent_idx=26,
    right_joint_idx=28,
    right_child_idx=32,

    # Tumit turun > 160°, tumit terangkat maksimal < 120°
    up_threshold=160.0,
    down_threshold=120.0,

    feedback_rules=FeedbackRules(
        deep_rom_deg=25.0,
        good_rom_deg=32.0,
        low_rom="ROM calf raise kurang. Angkat tumit setinggi mungkin.",
        good_rom="ROM calf raise sudah sangat baik.",
        low_consistency=(
            "Gerakan calf raise kurang konsisten. "
            "Jaga tempo naik-turun & jeda di puncak."
        ),
        low_stability=(
            "Tubuh bergoyang saat naik. "
            "Pegangan stabil & seimbangkan beban."
        ),
    ),
)
