"""
Modul visualisasi: gambar landmark di frame + plot grafik sudut.

Semua fungsi di sini:
- Hanya bergantung pada OpenCV, NumPy, Matplotlib.
- TIDAK import MediaPipe atau src.pose_estimator (duck typing).
- Menerima landmark sebagai objek dengan .x/.y ATAU tuple (x, y) ternormalisasi.

Landmark diasumsikan dalam koordinat ternormalisasi [0, 1] relatif terhadap
lebar/tinggi frame. Jika di luar [0, 1], gambar tetap dilakukan (OpenCV akan
memotong sendiri), bukan error.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence

import cv2
import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure


# --- Konstanta ---

# Koneksi skeleton MediaPipe Pose (33 titik)
POSE_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 7), (0, 4), (4, 5), (5, 6), (6, 8),
    (9, 10),
    (11, 12), (11, 13), (13, 15), (15, 17), (15, 19), (15, 21), (17, 19),
    (12, 14), (14, 16), (16, 18), (16, 20), (16, 22), (18, 20),
    (11, 23), (12, 24), (23, 24),
    (23, 25), (24, 26), (25, 27), (26, 28), (27, 29), (28, 30),
    (29, 31), (30, 32), (27, 31), (28, 32),
]

# Indeks landmark per sisi
LEFT_INDICES = {11, 13, 15, 23, 25, 27}
RIGHT_INDICES = {12, 14, 16, 24, 26, 28}

# Warna default (BGR, sesuai OpenCV)
DEFAULT_LINE_COLOR = (255, 255, 255)
DEFAULT_OTHER_COLOR = (200, 200, 200)
DEFAULT_LEFT_COLOR = (0, 255, 0)      # hijau
DEFAULT_RIGHT_COLOR = (0, 128, 255)   # oranye
DEFAULT_TEXT_COLOR = (0, 255, 0)


def _pixel(lm, width: int, height: int) -> tuple:
    """
    Konversi satu landmark (objek .x/.y atau tuple) ke koordinat piksel int.

    Raises
    ------
    TypeError
        Jika lm bukan objek dengan .x/.y dan bukan tuple/list 2-elemen.
    """
    if hasattr(lm, "x") and hasattr(lm, "y"):
        return (int(lm.x * width), int(lm.y * height))
    if isinstance(lm, (tuple, list)) and len(lm) >= 2:
        return (int(lm[0] * width), int(lm[1] * height))
    raise TypeError(
        f"Landmark harus objek dengan .x/.y atau tuple (x, y), dapat: {type(lm)}"
    )


def draw_pose_on_frame(
    frame: np.ndarray,
    landmarks: Optional[Sequence],
    line_color=DEFAULT_LINE_COLOR,
    line_thickness: int = 2,
    point_radius: int = 3,
    left_color=DEFAULT_LEFT_COLOR,
    right_color=DEFAULT_RIGHT_COLOR,
    other_color=DEFAULT_OTHER_COLOR,
    highlight_radius: int = 6,
    inplace: bool = True,
) -> np.ndarray:
    """
    Gambar skeleton + titik landmark di atas frame.

    Parameter
    ---------
    frame : np.ndarray
        Frame BGR (dari cv2).
    landmarks : sequence | None
        List landmark (objek .x/.y atau tuple). Jika None/kosong, frame
        dikembalikan tanpa perubahan.
    inplace : bool
        Jika True, modifikasi frame di tempat. Jika False, salin dulu.

    Returns
    -------
    np.ndarray
        Frame (yang sama jika inplace, atau salinan).
    """
    if not inplace:
        frame = frame.copy()

    if landmarks is None or len(landmarks) == 0:
        return frame

    h, w = frame.shape[:2]
    pts = []
    for lm in landmarks:
        try:
            pts.append(_pixel(lm, w, h))
        except TypeError:
            # Landmark invalid di tengah list → skip, jangan crash
            pts.append(None)

    # Gambar garis koneksi
    for a, b in POSE_CONNECTIONS:
        if a < len(pts) and b < len(pts) and pts[a] is not None and pts[b] is not None:
            cv2.line(frame, pts[a], pts[b], line_color, line_thickness)

    # Gambar titik
    for i, pt in enumerate(pts):
        if pt is None:
            continue
        if i in LEFT_INDICES:
            cv2.circle(frame, pt, highlight_radius, left_color, -1)
        elif i in RIGHT_INDICES:
            cv2.circle(frame, pt, highlight_radius, right_color, -1)
        else:
            cv2.circle(frame, pt, point_radius, other_color, -1)

    return frame


def draw_angle_label(
    frame: np.ndarray,
    label: str,
    position: tuple,
    color=DEFAULT_TEXT_COLOR,
    font_scale: float = 0.9,
    thickness: int = 2,
) -> np.ndarray:
    """
    Tulis label teks (misal sudut) di frame. Inplace — return frame yang sama.
    """
    cv2.putText(
        frame,
        label,
        position,
        cv2.FONT_HERSHEY_SIMPLEX,
        font_scale,
        color,
        thickness,
    )
    return frame


def _to_float_array(seq: Optional[Sequence]) -> Optional[np.ndarray]:
    """Konversi sequence (boleh ada None) ke numpy array float dengan NaN."""
    if seq is None:
        return None
    arr = np.empty(len(seq), dtype=float)
    for i, v in enumerate(seq):
        arr[i] = np.nan if v is None else float(v)
    return arr


def _mark_reps(ax, rep_result) -> None:
    """Tandai boundary repetisi di axis: garis vertikal di valley + shading."""
    if rep_result is None or not getattr(rep_result, "reps", None):
        return
    for rep in rep_result.reps:
        ax.axvline(rep.valley_idx, color="red", alpha=0.3, linestyle="--", linewidth=1)
        ax.annotate(
            f"R{rep_result.reps.index(rep) + 1}",
            xy=(rep.valley_idx, rep.valley_angle),
            xytext=(0, -12),
            textcoords="offset points",
            ha="center",
            fontsize=9,
            color="red",
        )


def plot_angle_series(
    angles: Optional[Sequence] = None,
    left_angles: Optional[Sequence] = None,
    right_angles: Optional[Sequence] = None,
    rep_result=None,
    title: str = "Sudut per Frame",
    xlabel: str = "Frame",
    ylabel: str = "Sudut (derajat)",
    output_path=None,
    dpi: int = 120,
    figsize: tuple = (10, 4),
) -> Figure:
    """
    Plot deret sudut vs frame. Bisa satu seri (`angles`) atau dua seri
    (`left_angles` + `right_angles`). Opsional tandai boundary repetisi.

    Menggunakan Matplotlib OO API (Figure + FigureCanvasAgg) — aman headless.

    Parameter
    ---------
    angles : sequence | None
        Satu seri sudut (misal sisi terpilih).
    left_angles, right_angles : sequence | None
        Jika keduanya diberikan, akan diplot sebagai dua seri.
        `angles` akan diabaikan dalam kasus ini.
    rep_result : RepCountResult | None
        Jika ada, tandai valley + nomor repetisi.
    output_path : str | Path | None
        Jika diberikan, simpan PNG ke path tersebut.

    Returns
    -------
    matplotlib.figure.Figure
        Objek figure (bisa dipakai untuk st.dispay atau savefig manual).

    Raises
    ------
    ValueError
        Jika tidak ada seri yang diberikan.
    """
    has_two_series = left_angles is not None and right_angles is not None
    if not has_two_series and angles is None:
        raise ValueError("Harus ada `angles` atau pasangan `left_angles` + `right_angles`.")

    fig = Figure(figsize=figsize)
    FigureCanvasAgg(fig)
    ax = fig.add_subplot(111)

    if has_two_series:
        left_arr = _to_float_array(left_angles)
        right_arr = _to_float_array(right_angles)
        ax.plot(left_arr, label="Kiri", color="green")
        ax.plot(right_arr, label="Kanan", color="orange")
        n_frames = max(len(left_arr), len(right_arr))
        x_ref = np.arange(n_frames)
    else:
        arr = _to_float_array(angles)
        ax.plot(arr, label="Sudut", color="green")
        n_frames = len(arr)
        x_ref = np.arange(n_frames)

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0, max(1, n_frames - 1))
    ax.legend(loc="best")

    # Pastikan rep boundary hanya digambar jika ada
    if rep_result is not None:
        _mark_reps(ax, rep_result)

    fig.tight_layout()

    if output_path is not None:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, dpi=dpi)

    return fig
