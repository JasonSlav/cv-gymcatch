"""
Konfigurasi gerakan SQUAT PLIE.

Sudut yang dianalisis: sudut lutut (hip → knee → ankle). Kamera: depan.
"""

from __future__ import annotations

from src.movements.base import FeedbackRules, MovementConfig

SQUAT_PLIE_CONFIG = MovementConfig(
    name="squat_plie",
    joint_name="knee",
    camera_angle="front",

    # Kiri: hip(23) → knee(25) → ankle(27)
    parent_idx=23,
    joint_idx=25,
    child_idx=27,

    # Kanan: hip(24) → knee(26) → ankle(28)
    right_parent_idx=24,
    right_joint_idx=26,
    right_child_idx=28,

    # Tegak > 160°, bottom < 110° (kaki dibuka, ujung kaki keluar)
    up_threshold=160.0,
    down_threshold=110.0,

    feedback_rules=FeedbackRules(
        deep_rom_deg=80.0,
        good_rom_deg=110.0,
        low_rom="Kedalaman squat plie kurang. Buka pinggul & turun lebih dalam.",
        good_rom="Kedalaman squat plie sudah sangat baik.",
        low_consistency="Gerakan squat plie kurang konsisten. Jaga tempo turun-naik.",
        low_stability=(
            "Tubuh terlalu banyak bergoyang. "
            "Jaga berat badan seimbang di kedua kaki."
        ),
    ),
)
