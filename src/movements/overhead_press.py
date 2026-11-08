"""
Konfigurasi gerakan OVERHEAD PRESS.

Sudut yang dianalisis: sudut siku (shoulder → elbow → wrist).
"""

from __future__ import annotations

from src.movements.base import FeedbackRules, MovementConfig

OVERHEAD_PRESS_CONFIG = MovementConfig(
    name="overhead_press",
    joint_name="elbow",

    # Kiri: shoulder(11) → elbow(13) → wrist(15)
    parent_idx=11,
    joint_idx=13,
    child_idx=15,

    # Kanan: shoulder(12) → elbow(14) → wrist(16)
    right_parent_idx=12,
    right_joint_idx=14,
    right_child_idx=16,

    # Lengan lurus di atas kepala > 160°, siku menekuk (beban di bahu) < 70°
    up_threshold=160.0,
    down_threshold=70.0,

    feedback_rules=FeedbackRules(
        deep_rom_deg=55.0,
        good_rom_deg=75.0,
        low_rom="ROM overhead press kurang. Tekan hingga lengan lurus penuh di atas kepala.",
        good_rom="ROM overhead press sudah sangat baik.",
        low_consistency=(
            "Gerakan press kurang konsisten. "
            "Jaga tempo dorong & turunkan terkontrol."
        ),
        low_stability=(
            "Torso miring saat menekan. "
            "Kencangkan core & jangan melengkungkan punggung."
        ),
    ),
)
