"""
Konfigurasi gerakan PUSH-UP PIKE.

Sudut yang dianalisis: sudut siku (shoulder → elbow → wrist). Kamera: samping.
"""

from __future__ import annotations

from src.movements.base import FeedbackRules, MovementConfig

PUSHUP_PIKE_CONFIG = MovementConfig(
    name="pushup_pike",
    joint_name="elbow",
    camera_angle="side",

    # Kiri: shoulder(11) → elbow(13) → wrist(15)
    parent_idx=11,
    joint_idx=13,
    child_idx=15,

    # Kanan: shoulder(12) → elbow(14) → wrist(16)
    right_parent_idx=12,
    right_joint_idx=14,
    right_child_idx=16,

    # Siku atas > 160°, kepala turun < 80° (pinggul tetap tinggi)
    up_threshold=160.0,
    down_threshold=80.0,

    feedback_rules=FeedbackRules(
        deep_rom_deg=90.0,
        good_rom_deg=120.0,
        low_rom="Kedalaman pike push-up kurang. Turunkan kepala ke arah lantai.",
        good_rom="Kedalaman pike push-up sudah sangat baik.",
        low_consistency="Gerakan pike push-up kurang konsisten. Jaga tempo turun-naik.",
        low_stability=(
            "Pinggul turun terlalu jauh. "
            "Jaga bentuk pike tetap tinggi."
        ),
    ),
)
