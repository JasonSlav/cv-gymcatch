"""
Registry gerakan. Titik masuk tunggal: get_movement_config(name).

Menambah gerakan baru:
1. Salin template.py (atau squat_standard.py) → mis. lunge.py
2. Isi indeks landmark, threshold, camera_angle, dan pesan feedback
3. Daftarkan di _MOVEMENTS di bawah — selesai. Pipeline/metrics/geometry
   tidak perlu disentuh.
"""

from __future__ import annotations

from src.movements.back_up import BACK_UP_CONFIG
from src.movements.base import FeedbackRules, MovementConfig
from src.movements.crunch_bicycle import CRUNCH_BICYCLE_CONFIG
from src.movements.crunch_standard import CRUNCH_STANDARD_CONFIG
from src.movements.crunch_swimming import CRUNCH_SWIMMING_CONFIG
from src.movements.pushup_diamond import PUSHUP_DIAMOND_CONFIG
from src.movements.pushup_pike import PUSHUP_PIKE_CONFIG
from src.movements.pushup_standard import PUSHUP_STANDARD_CONFIG
from src.movements.pushup_wide import PUSHUP_WIDE_CONFIG
from src.movements.squat_plie import SQUAT_PLIE_CONFIG
from src.movements.squat_standard import SQUAT_STANDARD_CONFIG
from src.movements.squat_sumo import SQUAT_SUMO_CONFIG

_MOVEMENTS = {
    "squat_standard": SQUAT_STANDARD_CONFIG,
    "squat_sumo": SQUAT_SUMO_CONFIG,
    "squat_plie": SQUAT_PLIE_CONFIG,
    "pushup_standard": PUSHUP_STANDARD_CONFIG,
    "pushup_wide": PUSHUP_WIDE_CONFIG,
    "pushup_diamond": PUSHUP_DIAMOND_CONFIG,
    "pushup_pike": PUSHUP_PIKE_CONFIG,
    "crunch_standard": CRUNCH_STANDARD_CONFIG,
    "crunch_swimming": CRUNCH_SWIMMING_CONFIG,
    "crunch_bicycle": CRUNCH_BICYCLE_CONFIG,
    "back_up": BACK_UP_CONFIG,
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
    "SQUAT_STANDARD_CONFIG",
    "SQUAT_SUMO_CONFIG",
    "SQUAT_PLIE_CONFIG",
    "PUSHUP_STANDARD_CONFIG",
    "PUSHUP_WIDE_CONFIG",
    "PUSHUP_DIAMOND_CONFIG",
    "PUSHUP_PIKE_CONFIG",
    "CRUNCH_STANDARD_CONFIG",
    "CRUNCH_SWIMMING_CONFIG",
    "CRUNCH_BICYCLE_CONFIG",
    "BACK_UP_CONFIG",
]
