"""
Definisi konfigurasi gerakan (config-driven).

Menambah gerakan baru = membuat file config baru + mendaftarkannya di
__init__.py — TANPA menyentuh pipeline.py, metrics.py, atau geometry.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class FeedbackRules:
    """Aturan & pesan feedback rule-based untuk satu gerakan."""

    # Ambang ROM (derajat) untuk pesan kedalaman gerakan
    deep_rom_deg: float = 90.0   # ROM di bawah ini → pesan "kurang dalam"
    good_rom_deg: float = 120.0  # ROM di atas ini → pesan "sangat baik"

    # Pesan feedback (dipakai oleh metrics.generate_rule_based_feedback)
    low_rom: str = "Kedalaman squat kurang. Usahakan turun lebih dalam."
    good_rom: str = "Kedalaman squat sudah sangat baik."
    low_consistency: str = "Gerakan kurang konsisten. Perhatikan tempo naik-turun."
    low_stability: str = (
        "Tubuh terlalu banyak bergoyang. "
        "Fokuskan berat badan di tengah kaki."
    )


@dataclass(frozen=True)
class MovementControlRules:
    """Aturan diagnostik kontrol gerakan (bukan validasi klinis).

    Skor kontrol terutama berasal dari konsistensi arah fase; reversal dan
    normalized jerk hanya indikator pendukung. Nilai default bersifat
    provisional dan perlu dikalibrasi dengan video berlabel.
    """

    min_good_control: float = 70.0
    velocity_deadband_deg_s: float = 5.0
    max_gap_sec: float = 0.25
    min_phase_samples: int = 3
    low_control: str = (
        "Kontrol gerakan kurang. Jaga fase gerak tetap mulus dan terkendali."
    )


@dataclass(frozen=True)
class MovementConfig:
    """
    Konfigurasi lengkap satu gerakan untuk pipeline.

    Indeks landmark mengikuti MediaPipe Pose (33 titik). Set kiri wajib;
    set kanan eksplisit (bukan diturunkan otomatis) agar mudah dibaca.
    """

    name: str            # id gerakan: "squat", "pushup", dst.
    joint_name: str      # nama sendi utk label overlay & header CSV: "knee", "elbow"

    # Sisi kiri: parent → joint → child (contoh squat: hip → knee → ankle)
    parent_idx: int
    joint_idx: int
    child_idx: int

    # Sisi kanan (mirror MediaPipe: 24/26/28 utk squat)
    right_parent_idx: int
    right_joint_idx: int
    right_child_idx: int

    # State machine repetisi (derajat). up = pose tegak/naik,
    # down = pose bawah. Wajib up_threshold > down_threshold.
    up_threshold: float
    down_threshold: float

    feedback_rules: FeedbackRules

    # Referensi ROM (derajat) untuk normalisasi skor. Default 135° agar
    # perilaku gerakan lama tidak berubah.
    rom_reference: float = 135.0

    # Rekomendasi sudut kamera perekaman: "side" (samping) / "front" (depan)
    camera_angle: str = "side"

    # Jenis gerakan: "dynamic" (repetisi) / "static" (tahan posisi).
    exercise_type: str = "dynamic"

    # Target durasi tahan (detik) untuk gerakan statis.
    target_duration_sec: float = 0.0

    # Movement control opsional; None = tidak dihitung (perilaku lama).
    control_rules: Optional[MovementControlRules] = None
