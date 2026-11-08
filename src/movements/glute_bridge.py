"""
Konfigurasi gerakan GLUTE BRIDGE.

Sudut yang dianalisis: sudut pinggul (shoulder → hip → knee) — mengecil
saat pinggul terangkat ke atas.
"""

from __future__ import annotations

from src.movements.base import FeedbackRules, MovementConfig

GLUTE_BRIDGE_CONFIG = MovementConfig(
    name="glute_bridge",
    joint_name="hip",

    # Kiri: shoulder(11) → hip(23) → knee(25)
    parent_idx=11,
    joint_idx=23,
    child_idx=25,

    # Kanan: shoulder(12) → hip(24) → knee(26)
    right_parent_idx=12,
    right_joint_idx=24,
    right_child_idx=26,

    # Pinggul di matras > 170°, terangkat penuh < 120°
    up_threshold=170.0,
    down_threshold=120.0,

    feedback_rules=FeedbackRules(
        deep_rom_deg=30.0,
        good_rom_deg=42.0,
        low_rom="Angkat pinggul lebih tinggi hingga tubuh membentuk garis lurus.",
        good_rom="ROM glute bridge sudah sangat baik.",
        low_consistency=(
            "Gerakan glute bridge kurang konsisten. "
            "Jaga tempo angkat & turun terkontrol."
        ),
        low_stability=(
            "Pinggul miring ke satu sisi. "
            "Angkat kedua sisi secara merata."
        ),
    ),
)
