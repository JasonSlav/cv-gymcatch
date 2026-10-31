"""
Definisi konfigurasi gerakan (config-driven).

Menambah gerakan baru = membuat file config baru + mendaftarkannya di
__init__.py — TANPA menyentuh pipeline.py, metrics.py, atau geometry.py.
"""

from __future__ import annotations

from dataclasses import dataclass


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
