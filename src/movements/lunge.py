"""
Konfigurasi gerakan LUNGE.

Sudut yang dianalisis: sudut lutut (hip → knee → ankle).
"""

from __future__ import annotations

from src.movements.base import FeedbackRules, MovementConfig

LUNGE_CONFIG = MovementConfig(
    name="lunge",
    joint_name="knee",

    # Kiri: hip(23) → knee(25) → ankle(27)
    parent_idx=23,
    joint_idx=25,
    child_idx=27,

    # Kanan: hip(24) → knee(26) → ankle(28)
    right_parent_idx=24,
    right_joint_idx=26,
    right_child_idx=28,

    # Tegak > 160°, lutut depan menekuk < 100°
    up_threshold=160.0,
    down_threshold=100.0,

    feedback_rules=FeedbackRules(
        deep_rom_deg=40.0,
        good_rom_deg=50.0,
        low_rom="Kedalaman lunge kurang. Turunkan lutut belakang lebih dalam.",
        good_rom="Kedalaman lunge sudah sangat baik.",
        low_consistency="Gerakan lunge kurang konsisten. Jaga tempo & jarak langkah.",
        low_stability=(
            "Tubuh bergoyang. "
            "Fokus pada satu titik & tegakkan torso."
        ),
    ),
)
