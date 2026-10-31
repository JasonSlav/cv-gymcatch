"""
Modul report: pilih seri tampilan, tulis CSV sudut, format summary.

Semua fungsi di sini:
- Hanya bergantung pada stdlib + numpy.
- Tidak menyentuh MediaPipe, OpenCV, atau I/O video.
- Menerima deret sudut dengan None untuk frame invalid.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Optional, Sequence, Tuple

import numpy as np


def choose_display_series(
    left_angles: Sequence[Optional[float]],
    right_angles: Sequence[Optional[float]],
    both_threshold: float = 0.9,
) -> Tuple[str, Optional[Sequence], Optional[Sequence]]:
    """
    Pilih seri yang akan ditampilkan berdasarkan rasio frame valid.

    Returns
    -------
    (mode, series1, series2) di mana mode ∈ {"both", "left", "right", "none"}.
    - "both"  → series1 = left_angles, series2 = right_angles
    - "left"  → series1 = left_angles,  series2 = None
    - "right" → series1 = None,          series2 = right_angles
    - "none"  → keduanya None

    Aturan:
    - "both" jika kedua rasio valid >= both_threshold.
    - "left"/"right" jika hanya satu sisi punya frame valid dan lebih tinggi.
    - "none" jika tidak ada frame valid di kedua sisi.

    Raises
    ------
    ValueError
        Jika panjang left_angles != right_angles (harus sejajar per frame).
    """
    if len(left_angles) != len(right_angles):
        raise ValueError(
            f"Panjang deret tidak sama: left={len(left_angles)}, "
            f"right={len(right_angles)}"
        )
    n = len(left_angles)
    if n == 0:
        return ("none", None, None)

    left_valid = sum(1 for a in left_angles if a is not None)
    right_valid = sum(1 for a in right_angles if a is not None)
    left_ratio = left_valid / n
    right_ratio = right_valid / n

    if left_ratio >= both_threshold and right_ratio >= both_threshold:
        return ("both", left_angles, right_angles)
    if left_valid == 0 and right_valid == 0:
        return ("none", None, None)
    if left_valid >= right_valid:
        return ("left", left_angles, None)
    return ("right", None, right_angles)


def write_angles_csv(
    path,
    left_angles: Sequence[Optional[float]],
    right_angles: Sequence[Optional[float]],
    joint_name: str = "knee",
) -> int:
    """
    Tulis CSV sudut. Format sama dengan PoC lama:
        frame,left_<joint>_angle_deg,right_<joint>_angle_deg,left_valid,right_valid

    `joint_name` berasal dari konfigurasi gerakan ("knee", "elbow", ...).
    Default "knee" mempertahankan header lama untuk squat.

    Returns
    -------
    int
        Jumlah baris data (tidak termasuk header).

    Raises
    ------
    ValueError
        Jika panjang left_angles != right_angles.
    """
    if len(left_angles) != len(right_angles):
        raise ValueError(
            f"Panjang deret tidak sama: left={len(left_angles)}, "
            f"right={len(right_angles)}"
        )
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [f"frame", f"left_{joint_name}_angle_deg",
             f"right_{joint_name}_angle_deg", "left_valid", "right_valid"]
        )
        for i, (lv, rv) in enumerate(zip(left_angles, right_angles)):
            w.writerow([
                i,
                "" if lv is None else f"{lv:.3f}",
                "" if rv is None else f"{rv:.3f}",
                int(lv is not None),
                int(rv is not None),
            ])
    return len(left_angles)


def format_summary_text(
    video_name: str,
    width: int,
    height: int,
    fps: float,
    frame_count: int,
    process_sec: float,
    side_results: list,
) -> str:
    """
    Format teks ringkasan untuk stdout dan file `summary.txt`.

    Parameter
    ---------
    side_results : list[dict]
        Setiap dict minimal punya kunci:
        "side" (str), "valid_frames" (int), "rep_count" (int),
        "rom" (float|None), "consistency" (float|None).
    """
    lines = []
    lines.append("=" * 60)
    lines.append("Ringkasan Analisis Gerakan")
    lines.append("=" * 60)
    lines.append(f"Video        : {video_name}")
    lines.append(f"Resolusi     : {width}x{height}")
    lines.append(f"FPS          : {fps:.2f}")
    lines.append(f"Frame        : {frame_count}")
    if fps > 0:
        lines.append(f"Durasi       : {frame_count / fps:.2f}s")
    else:
        lines.append("Durasi       : N/A")
    lines.append(f"Waktu proses : {process_sec:.2f}s")
    lines.append("-" * 60)
    if not side_results:
        lines.append("(tidak ada sisi yang dianalisis)")
    for r in side_results:
        lines.append(f"Sisi {r['side']}:")
        lines.append(f"  Frame valid     : {r['valid_frames']}/{frame_count}")
        lines.append(f"  Repetisi        : {r['rep_count']}")
        if r.get("rom") is not None:
            lines.append(f"  ROM             : {r['rom']:.2f} derajat")
        else:
            lines.append("  ROM             : N/A")
        if r.get("consistency") is not None:
            lines.append(f"  Consistency     : {r['consistency']:.3f}")
        else:
            lines.append("  Consistency     : N/A (butuh >= 3 repetisi)")
    lines.append("=" * 60)
    return "\n".join(lines)
