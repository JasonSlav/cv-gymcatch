"""
Konfigurasi gerakan BACK UP (back extension).

Sudut yang dianalisis: sudut pinggul (shoulder → hip → knee). Kamera: samping.
Ini proxy ekstensi batang tubuh berbasis hip, bukan pengukuran lumbar langsung.

Threshold 170/160 dan rom_reference 42 masih PROVISIONAL: baru diuji pada
1 video dan bukan standar ROM ideal/klinis.
"""

from __future__ import annotations

from src.movements.base import (
    FeedbackRules,
    MovementConfig,
    MovementControlRules,
)

BACK_UP_CONFIG = MovementConfig(
    name="back_up",
    joint_name="hip",
    camera_angle="side",

    # Kiri: shoulder(11) → hip(23) → knee(25)
    parent_idx=11,
    joint_idx=23,
    child_idx=25,

    # Kanan: shoulder(12) → hip(24) → knee(26)
    right_parent_idx=12,
    right_joint_idx=24,
    right_child_idx=26,

    # PROVISIONAL (1 video, 5 repetisi, 149-180 derajat):
    # down 120 tidak pernah tercapai; down 160 menghasilkan 5 repetisi.
    # Perlu validasi minimal 3 video berlabel dengan variasi kemampuan.
    up_threshold=170.0,
    down_threshold=160.0,

    # PROVISIONAL: selaras dengan good_rom_deg, BUKAN standar ROM ideal/klinis.
    # Komponen ROM menjadi penuh pada 42 derajat; perlu kalibrasi lanjutan.
    rom_reference=42.0,

    feedback_rules=FeedbackRules(
        deep_rom_deg=30.0,
        good_rom_deg=42.0,
        low_rom="Angkat dada & kaki lebih tinggi saat back extension.",
        good_rom="ROM back extension sudah sangat baik.",
        low_consistency=(
            "Gerakan back extension kurang konsisten. "
            "Jaga tempo angkat & turun terkontrol."
        ),
        low_stability=(
            "Pinggul terlalu banyak bergoyang. "
            "Jaga posisi pinggul tetap stabil."
        ),
    ),

    # Diagnostik kontrol gerakan; tidak masuk skor total 40/30/30.
    control_rules=MovementControlRules(
        low_control=(
            "Kontrol gerakan back extension rendah. "
            "Jaga fase angkat dan turun tetap mulus dan terkendali."
        ),
    ),
)
