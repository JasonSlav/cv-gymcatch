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
from src.movements.calf_raise import CALF_RAISE_CONFIG
from src.movements.crunch import CRUNCH_CONFIG
from src.movements.curl import CURL_CONFIG
from src.movements.deadlift import DEADLIFT_CONFIG
from src.movements.glute_bridge import GLUTE_BRIDGE_CONFIG
from src.movements.lateral_raise import LATERAL_RAISE_CONFIG
from src.movements.lunge import LUNGE_CONFIG
from src.movements.overhead_press import OVERHEAD_PRESS_CONFIG
from src.movements.plank import PLANK_CONFIG
from src.movements.pushup import PUSHUP_CONFIG
from src.movements.row import ROW_CONFIG
from src.movements.squat import SQUAT_CONFIG

_MOVEMENTS = {
    "squat": SQUAT_CONFIG,
    "pushup": PUSHUP_CONFIG,
    "lunge": LUNGE_CONFIG,
    "curl": CURL_CONFIG,
    "deadlift": DEADLIFT_CONFIG,
    "overhead_press": OVERHEAD_PRESS_CONFIG,
    "row": ROW_CONFIG,
    "plank": PLANK_CONFIG,
    "calf_raise": CALF_RAISE_CONFIG,
    "lateral_raise": LATERAL_RAISE_CONFIG,
    "crunch": CRUNCH_CONFIG,
    "glute_bridge": GLUTE_BRIDGE_CONFIG,
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
    "LUNGE_CONFIG",
    "CURL_CONFIG",
    "DEADLIFT_CONFIG",
    "OVERHEAD_PRESS_CONFIG",
    "ROW_CONFIG",
    "PLANK_CONFIG",
    "CALF_RAISE_CONFIG",
    "LATERAL_RAISE_CONFIG",
    "CRUNCH_CONFIG",
    "GLUTE_BRIDGE_CONFIG",
]
