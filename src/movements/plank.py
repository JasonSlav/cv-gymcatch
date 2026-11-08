"""
Konfigurasi gerakan PLANK (alignment).

Sudut yang dianalisis: sudut pinggul (shoulder → hip → ankle) sebagai
ukur kelurusan tubuh — 180° = garis lurus sempurna.
"""

from __future__ import annotations

from src.movements.base import FeedbackRules, MovementConfig

PLANK_CONFIG = MovementConfig(
    name="plank",
    joint_name="hip",

    # Kiri: shoulder(11) → hip(23) → ankle(27)
    parent_idx=11,
    joint_idx=23,
    child_idx=27,

    # Kanan: shoulder(12) → hip(24) → ankle(28)
    right_parent_idx=12,
    right_joint_idx=24,
    right_child_idx=28,

    # Kelurusan sempurna > 175°, pinggul turun/signum < 150°
    up_threshold=175.0,
    down_threshold=150.0,

    feedback_rules=FeedbackRules(
        deep_rom_deg=15.0,
        good_rom_deg=20.0,
        low_rom="Pinggul turun terlalu jauh. Jaga tubuh tetap lurus dari kepala ke tumit.",
        good_rom="Alignment plank sudah sangat baik dan terjaga.",
        low_consistency=(
            "Posisi plank kurang konsisten. "
            "Pertahankan alignment sepanjang durasi."
        ),
        low_stability=(
            "Tubuh bergoyang saat plank. "
            "Kencangkan core & jangkar bahu."
        ),
    ),
)
