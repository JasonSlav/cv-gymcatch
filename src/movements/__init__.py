"""
Registry gerakan. Titik masuk tunggal: get_movement_config(name).

Menambah gerakan baru:
1. Salin template.py (atau squat.py) → mis. lunge.py
2. Isi indeks landmark, threshold, dan pesan feedback
3. Daftarkan di _MOVEMENTS di bawah — selesai. Pipeline/metrics/geometry
   tidak perlu disentuh.
"""

from __future__ import annotations

from src.movements.base import FeedbackRules, MovementConfig
from src.movements.pushup import PUSHUP_CONFIG
from src.movements.squat import SQUAT_CONFIG

_MOVEMENTS = {
    "squat": SQUAT_CONFIG,
    "pushup": PUSHUP_CONFIG,
}


def get_movement_config(name: str) -> MovementConfig:
    """
    Ambil konfigurasi gerakan berdasarkan nama (case-insensitive).

    Raises
    ------
    ValueError
        Jika nama gerakan tidak terdaftar.
    """
    key = (name or "").strip().lower()
    if key not in _MOVEMENTS:
        raise ValueError(
            f"Gerakan tidak dikenal: {name!r}. Tersedia: {sorted(_MOVEMENTS)}"
        )
    return _MOVEMENTS[key]


__all__ = [
    "FeedbackRules",
    "MovementConfig",
    "get_movement_config",
    "SQUAT_CONFIG",
    "PUSHUP_CONFIG",
]
