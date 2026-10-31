"""
Konfigurasi gerakan SQUAT.

Sudut yang dianalisis: sudut lutut (hip → knee → ankle).
"""

from __future__ import annotations

from src.movements.base import FeedbackRules, MovementConfig

SQUAT_CONFIG = MovementConfig(
    name="squat",
    joint_name="knee",

    # Kiri: hip(23) → knee(25) → ankle(27)
    parent_idx=23,
    joint_idx=25,
    child_idx=27,

    # Kanan: hip(24) → knee(26) → ankle(28)
    right_parent_idx=24,
    right_joint_idx=26,
    right_child_idx=28,

    # Tegak > 160°, bottom < 100° (nilai lama pipeline, tidak berubah)
    up_threshold=160.0,
    down_threshold=100.0,

    feedback_rules=FeedbackRules(
        deep_rom_deg=90.0,
        good_rom_deg=120.0,
        low_rom="Kedalaman squat kurang. Usahakan turun lebih dalam.",
        good_rom="Kedalaman squat sudah sangat baik.",
        low_consistency="Gerakan kurang konsisten. Perhatikan tempo naik-turun.",
        low_stability=(
            "Tubuh terlalu banyak bergoyang. "
            "Fokuskan berat badan di tengah kaki."
        ),
    ),
)
