"""
Modul metrik analisis gerakan.

Semua fungsi di sini:
- Murni komputasi — hanya bergantung pada NumPy.
- Tidak menyentuh MediaPipe, OpenCV, atau I/O.
- Menerima deret sudut (derajat) dengan nilai None untuk frame invalid.

Kebijakan:
- Jangan mengarang nilai untuk kasus tak terdefinisi → return None.
- Threshold default untuk squat, tetapi dapat di-override.
- State machine eksplisit dengan hysteresis, bukan peak detection rapuh.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

import numpy as np


# --- Konstanta state machine ---
STATE_UNKNOWN = "UNKNOWN"
STATE_STANDING = "STANDING"
STATE_DESCENDING = "DESCENDING"
STATE_BOTTOM = "BOTTOM"
STATE_ASCENDING = "ASCENDING"

# Default threshold (derajat) untuk squat
DEFAULT_UP_THRESHOLD = 160.0
DEFAULT_DOWN_THRESHOLD = 100.0
DEFAULT_HYSTERESIS = 10.0
DEFAULT_SMOOTH_WINDOW = 5
DEFAULT_CONSISTENCY_POINTS = 100
MIN_REPS_FOR_CONSISTENCY = 3


# --- Dataclass hasil ---

@dataclass(frozen=True)
class RepInfo:
    """Info satu repetisi."""

    start_idx: int      # frame peak awal (STANDING)
    valley_idx: int     # frame bottom (BOTTOM)
    end_idx: int        # frame peak akhir (STANDING berikutnya)
    peak_angle: float   # sudut di peak awal
    valley_angle: float # sudut di valley

    @property
    def rom(self) -> float:
        return self.peak_angle - self.valley_angle

    @property
    def duration_frames(self) -> int:
        return self.end_idx - self.start_idx + 1


@dataclass
class RepCountResult:
    """Hasil hitung repetisi."""

    reps: List[RepInfo]
    final_state: str

    @property
    def count(self) -> int:
        return len(self.reps)


# --- Fungsi murni ---

def to_array(angles: Sequence[Optional[float]]) -> np.ndarray:
    """Konversi sequence (boleh ada None) ke numpy array float dengan NaN."""
    arr = np.empty(len(angles), dtype=float)
    for i, a in enumerate(angles):
        arr[i] = np.nan if a is None else float(a)
    return arr


def smooth_angles(
    angles: Sequence[Optional[float]],
    window: int = DEFAULT_SMOOTH_WINDOW,
) -> np.ndarray:
    """
    Moving average dengan window tetap. NaN diabaikan (di-skip).
    Output: numpy array float; NaN jika seluruh window NaN.
    """
    if window < 1:
        raise ValueError(f"window harus >= 1, dapat {window}")
    arr = to_array(angles)
    n = len(arr)
    out = np.full(n, np.nan)
    half = window // 2
    for i in range(n):
        lo = max(0, i - half)
        hi = min(n, i + half + 1)
        window_vals = arr[lo:hi]
        valid = window_vals[~np.isnan(window_vals)]
        if len(valid) > 0:
            out[i] = float(np.mean(valid))
    return out


def compute_rom(angles: Sequence[Optional[float]]) -> Optional[float]:
    """ROM = max - min dari nilai valid. Return None jika tidak ada nilai valid."""
    arr = to_array(angles)
    valid = arr[~np.isnan(arr)]
    if len(valid) == 0:
        return None
    return float(valid.max() - valid.min())


def count_reps(
    angles: Sequence[Optional[float]],
    up_threshold: float = DEFAULT_UP_THRESHOLD,
    down_threshold: float = DEFAULT_DOWN_THRESHOLD,
    hysteresis: float = DEFAULT_HYSTERESIS,
    smooth_window: int = DEFAULT_SMOOTH_WINDOW,
) -> RepCountResult:
    """
    Hitung repetisi dari deret sudut (derajat) via state machine.

    Aturan:
    - STANDING: sudut > up_threshold.
    - BOTTOM: sudut < down_threshold.
    - 1 repetisi = STANDING → DESCENDING → BOTTOM → ASCENDING → STANDING.
    - Hysteresis menghindari false transition karena noise.
    - Signal di-smooth dulu (moving average) untuk stabilisasi.

    Raises
    ------
    ValueError
        Jika up_threshold <= down_threshold.
    """
    if up_threshold <= down_threshold:
        raise ValueError("up_threshold harus > down_threshold")

    smoothed = smooth_angles(angles, window=smooth_window)

    state = STATE_UNKNOWN
    reps: List[RepInfo] = []

    rep_start_peak_idx: Optional[int] = None
    rep_start_peak_angle: Optional[float] = None
    valley_idx: Optional[int] = None
    valley_angle: Optional[float] = None

    stand_back_threshold = up_threshold - hysteresis
    rise_from_bottom_threshold = down_threshold + hysteresis

    for i, a in enumerate(smoothed):
        if np.isnan(a):
            continue

        if state == STATE_UNKNOWN:
            if a > up_threshold:
                state = STATE_STANDING
                rep_start_peak_idx = i
                rep_start_peak_angle = a

        elif state == STATE_STANDING:
            if a > rep_start_peak_angle:
                rep_start_peak_idx = i
                rep_start_peak_angle = a
            elif a < stand_back_threshold:
                state = STATE_DESCENDING

        elif state == STATE_DESCENDING:
            if a < down_threshold:
                state = STATE_BOTTOM
                valley_idx = i
                valley_angle = a
            elif a > stand_back_threshold:
                # Abort — tidak sampai bottom, kembali ke standing
                state = STATE_STANDING

        elif state == STATE_BOTTOM:
            if a < valley_angle:
                valley_idx = i
                valley_angle = a
            elif a > rise_from_bottom_threshold:
                state = STATE_ASCENDING

        elif state == STATE_ASCENDING:
            if a > up_threshold:
                # Repetisi selesai
                reps.append(
                    RepInfo(
                        start_idx=rep_start_peak_idx,
                        valley_idx=valley_idx,
                        end_idx=i,
                        peak_angle=rep_start_peak_angle,
                        valley_angle=valley_angle,
                    )
                )
                # Persiapan repetisi berikutnya
                state = STATE_STANDING
                rep_start_peak_idx = i
                rep_start_peak_angle = a
                valley_idx = None
                valley_angle = None
            elif a < rise_from_bottom_threshold:
                # Balik lagi ke bottom (gerakan tidak selesai)
                state = STATE_BOTTOM

    return RepCountResult(reps=reps, final_state=state)


def extract_rep_curves(
    angles: Sequence[Optional[float]],
    result: RepCountResult,
) -> List[np.ndarray]:
    """Ekstrak deret sudut per repetisi (start_idx s.d end_idx). Return list array."""
    arr = to_array(angles)
    curves: List[np.ndarray] = []
    for rep in result.reps:
        curves.append(arr[rep.start_idx : rep.end_idx + 1].copy())
    return curves


def resample_curve(
    curve: np.ndarray,
    n_points: int = DEFAULT_CONSISTENCY_POINTS,
) -> np.ndarray:
    """
    Linear-interpolate 1D curve ke n_points.

    - NaN internal di-interpolasi terhadap indeks valid.
    - Jika seluruh array NaN, return NaN array.
    - Jika length 0, return NaN array.
    """
    arr = np.asarray(curve, dtype=float)
    n = len(arr)
    if n == 0 or np.all(np.isnan(arr)):
        return np.full(n_points, np.nan)
    valid_idx = np.where(~np.isnan(arr))[0]
    x_old = valid_idx.astype(float)
    y_old = arr[valid_idx]
    x_new = np.linspace(0.0, float(n - 1), n_points)
    return np.interp(x_new, x_old, y_old)


def compute_consistency(
    rep_curves: Sequence[np.ndarray],
    n_points: int = DEFAULT_CONSISTENCY_POINTS,
) -> Optional[float]:
    """
    Hitung consistency index dari beberapa kurva repetisi.

    Definisi (PROJECT.md §6.5):
        consistency = 1 - (mean_RMSE / mean_ROM)

    RMSE dihitung terhadap mean curve setelah resample ke n_points.
    Hasil di-clip ke [0, 1].

    Return None jika:
    - Jumlah kurva valid < MIN_REPS_FOR_CONSISTENCY.
    - Mean ROM terlalu kecil (< 1e-6, hindari division by zero).
    """
    if len(rep_curves) < MIN_REPS_FOR_CONSISTENCY:
        return None

    resampled = []
    for c in rep_curves:
        r = resample_curve(c, n_points=n_points)
        if np.all(np.isnan(r)):
            continue
        resampled.append(r)

    if len(resampled) < MIN_REPS_FOR_CONSISTENCY:
        return None

    stacked = np.vstack(resampled)
    mean_curve = np.nanmean(stacked, axis=0)
    rmse_per_rep = np.sqrt(np.nanmean((stacked - mean_curve) ** 2, axis=1))
    mean_rmse = float(np.nanmean(rmse_per_rep))

    roms = np.nanmax(stacked, axis=1) - np.nanmin(stacked, axis=1)
    mean_rom = float(np.nanmean(roms))

    if mean_rom < 1e-6:
        return None

    consistency = 1.0 - (mean_rmse / mean_rom)
    return float(max(0.0, min(1.0, consistency)))
