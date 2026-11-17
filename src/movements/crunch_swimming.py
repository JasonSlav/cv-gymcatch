"""
Konfigurasi gerakan CRUNCH SWIMMING.

Sudut yang dianalisis: sudut torso (shoulder → hip → knee). Kamera: samping.
"""

from __future__ import annotations

from src.movements.base import FeedbackRules, MovementConfig

CRUNCH_SWIMMING_CONFIG = MovementConfig(
    name="crunch_swimming",
    joint_name="torso",
    camera_angle="side",

    # Kiri: shoulder(11) → hip(23) → knee(25)
    parent_idx=11,
    joint_idx=23,
    child_idx=25,

    # Kanan: shoulder(12) → hip(24) → knee(26)
    right_parent_idx=12,
    right_joint_idx=24,
    right_child_idx=26,

    # Posisi netral > 150°, ayunan penuh < 100°
    up_threshold=150.0,
    down_threshold=100.0,

    feedback_rules=FeedbackRules(
        deep_rom_deg=30.0,
        good_rom_deg=42.0,
        low_rom="ROM crunch swimming kurang. Jaga gerakan kaki & tangan tetap luas.",
        good_rom="ROM crunch swimming sudah sangat baik.",
        low_consistency=(
            "Gerakan swimming kurang konsisten. "
            "Jaga irama kaki-tangan bergantian."
        ),
        low_stability=(
            "Pinggul terlalu banyak bergoyang. "
            "Tekan punggung bawah ke matras."
        ),
    ),
)
