"""
Konfigurasi gerakan CRUNCH BIASA.

Sudut yang dianalisis: sudut torso (shoulder → hip → knee). Kamera: samping.
"""

from __future__ import annotations

from src.movements.base import FeedbackRules, MovementConfig

CRUNCH_STANDARD_CONFIG = MovementConfig(
    name="crunch_standard",
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

    # Posisi terlentang > 120°, crunch penuh < 40°
    up_threshold=120.0,
    down_threshold=40.0,

    feedback_rules=FeedbackRules(
        deep_rom_deg=50.0,
        good_rom_deg=65.0,
        low_rom="ROM crunch kurang. Angkat tubuh bagian atas lebih tinggi.",
        good_rom="ROM crunch sudah sangat baik.",
        low_consistency=(
            "Gerakan crunch kurang konsisten. "
            "Jaga tempo angkat & turun terkontrol."
        ),
        low_stability=(
            "Gerakan memakai momentum leher. "
            "Pegang posisi & gunakan otot perut."
        ),
    ),
)
