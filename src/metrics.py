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

from src.movements.base import FeedbackRules, MovementControlRules


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


# --- Movement control (diagnostik, bukan validasi klinis) ---

def _phase_control(
    smoothed: np.ndarray,
    times: np.ndarray,
    lo: int,
    hi: int,
    expected_sign: int,
    rules: MovementControlRules,
) -> Optional[dict]:
    """Hitung kontrol satu fase (lo s.d. hi) dari angular velocity."""
    velocities: List[float] = []
    mid_times: List[float] = []
    for i in range(lo, hi):
        a0 = smoothed[i]
        a1 = smoothed[i + 1]
        t0 = times[i]
        t1 = times[i + 1]
        if not (
            np.isfinite(a0) and np.isfinite(a1)
            and np.isfinite(t0) and np.isfinite(t1)
        ):
            continue
        dt = float(t1 - t0)
        if dt <= 0.0 or dt > rules.max_gap_sec:
            continue
        velocities.append(float((a1 - a0) / dt))
        mid_times.append(float((t0 + t1) / 2.0))

    if len(velocities) < rules.min_phase_samples:
        return None

    v = np.asarray(velocities, dtype=float)
    mt = np.asarray(mid_times, dtype=float)

    # Indikator utama: arah velocity sesuai fase (atau berada di deadband).
    inside_deadband = np.abs(v) <= rules.velocity_deadband_deg_s
    direction_ok = (v * expected_sign > 0.0) | inside_deadband
    direction_consistency = float(np.mean(direction_ok))

    # Indikator pendukung: perubahan arah yang jelas di luar deadband.
    signs = np.where(np.abs(v) > rules.velocity_deadband_deg_s, np.sign(v), 0.0)
    active_signs = signs[signs != 0.0]
    reversals = (
        int(np.count_nonzero(np.diff(active_signs) != 0.0))
        if len(active_signs) > 1
        else 0
    )

    # Indikator pendukung: normalized jerk (RMS jerk * T^3 / amplitudo).
    normalized_jerk: Optional[float] = None
    if len(v) >= 3 and len(mt) >= 3:
        dt_mid = np.diff(mt)
        valid_dt = dt_mid > 0.0
        if np.all(valid_dt):
            acc = np.diff(v) / dt_mid
            acc_t = (mt[:-1] + mt[1:]) / 2.0
            dt_acc = np.diff(acc_t)
            if len(acc) >= 2 and np.all(dt_acc > 0.0):
                jerk = np.diff(acc) / dt_acc
                duration = float(times[hi] - times[lo])
                amplitude = abs(float(smoothed[hi] - smoothed[lo]))
                if duration > 0.0 and amplitude > 1e-6:
                    normalized_jerk = float(
                        np.sqrt(np.mean(jerk ** 2)) * duration ** 3 / amplitude
                    )

    duration = (
        float(times[hi] - times[lo])
        if np.isfinite(times[lo]) and np.isfinite(times[hi])
        else None
    )
    return {
        "samples": len(velocities),
        "direction_consistency": float(max(0.0, min(1.0, direction_consistency))),
        "reversals": reversals,
        "normalized_jerk": normalized_jerk,
        "duration_sec": duration,
        "mean_speed_deg_s": float(np.mean(np.abs(v))),
        "peak_speed_deg_s": float(np.max(np.abs(v))),
    }


def compute_movement_control(
    angles: Sequence[Optional[float]],
    timestamps_sec: Optional[Sequence[Optional[float]]],
    rep_result: Optional[RepCountResult],
    rules: MovementControlRules,
    fps: Optional[float] = None,
) -> Optional[dict]:
    """Diagnostik kontrol gerakan dari arah, kelancaran, dan fase repetisi.

    Skor utama memakai direction consistency (tidak memakai kecepatan
    absolut). Reversal, normalized jerk, dan tempo hanya indikator
    pendukung/diagnostik. Return None bila data tidak cukup.

    Catatan: fungsi ini bukan pengukuran momentum fisik dan bukan validasi
    klinis.
    """
    if rep_result is None or not rep_result.reps:
        return None
    if rules.max_gap_sec <= 0.0 or rules.min_phase_samples < 1:
        return None

    smoothed = smooth_angles(angles, window=DEFAULT_SMOOTH_WINDOW)
    n = len(smoothed)
    if n == 0:
        return None

    times = np.full(n, np.nan, dtype=float)
    if timestamps_sec is not None and len(timestamps_sec) == n:
        for i, ts in enumerate(timestamps_sec):
            if ts is None:
                continue
            try:
                value = float(ts)
            except (TypeError, ValueError):
                continue
            if np.isfinite(value):
                times[i] = value
    elif fps is not None and float(fps) > 0.0:
        times = np.arange(n, dtype=float) / float(fps)
    else:
        return None

    phase_controls: List[dict] = []
    lift_durations: List[float] = []
    lower_durations: List[float] = []
    reps_used = 0

    for rep in rep_result.reps:
        start, valley, end = rep.start_idx, rep.valley_idx, rep.end_idx
        if not (0 <= start < valley < end < n):
            continue
        a_start = smoothed[start]
        a_valley = smoothed[valley]
        a_end = smoothed[end]
        if not (np.isfinite(a_start) and np.isfinite(a_valley) and np.isfinite(a_end)):
            continue

        # Back Up: fase angkat menurunkan sudut, fase turun menaikkan sudut.
        if not (a_start > a_valley and a_end > a_valley):
            continue

        rep_used = False
        lift = _phase_control(smoothed, times, start, valley, -1, rules)
        if lift is not None:
            phase_controls.append(lift)
            if lift["duration_sec"] is not None:
                lift_durations.append(lift["duration_sec"])
            rep_used = True

        lower = _phase_control(smoothed, times, valley, end, 1, rules)
        if lower is not None:
            phase_controls.append(lower)
            if lower["duration_sec"] is not None:
                lower_durations.append(lower["duration_sec"])
            rep_used = True

        if rep_used:
            reps_used += 1

    if not phase_controls:
        return None

    score = 100.0 * float(
        np.mean([p["direction_consistency"] for p in phase_controls])
    )

    tempo_cvs: List[float] = []
    for durations in (lift_durations, lower_durations):
        if len(durations) >= 3:
            mean_duration = float(np.mean(durations))
            if mean_duration > 1e-6:
                tempo_cvs.append(float(np.std(durations) / mean_duration))
    tempo_cv = float(np.mean(tempo_cvs)) if tempo_cvs else None

    jerk_values = [
        p["normalized_jerk"] for p in phase_controls
        if p["normalized_jerk"] is not None
    ]
    return {
        "score": float(max(0.0, min(100.0, score))),
        "direction_consistency": float(
            np.mean([p["direction_consistency"] for p in phase_controls])
        ),
        "reversal_count": int(sum(p["reversals"] for p in phase_controls)),
        "normalized_jerk": (
            float(np.mean(jerk_values)) if jerk_values else None
        ),
        "tempo_cv": tempo_cv,
        "reps_used": reps_used,
        "phases": list(phase_controls),
    }


# --- Scoring rule-based (prototype, bukan validasi klinis) ---

# Landmark MediaPipe (indeks 33 titik)
_L_HIP_IDX = 23
_R_HIP_IDX = 24

# Goyangan horizontal pinggul dianggap parah bila std > 50 px → stability 0
MAX_STABILITY_SWAY_PX = 50.0

# Ambang feedback
ROM_DEEP_SQUAT_DEG = 90.0
ROM_GOOD_SQUAT_DEG = 120.0
ROM_REFERENCE_DEG = 135.0
MIN_GOOD_CONSISTENCY = 0.8
MIN_GOOD_STABILITY = 70.0

# Ambang label skor
SCORE_GOOD_THRESHOLD = 80.0
SCORE_OK_THRESHOLD = 60.0


def compute_stability_proxy(
    landmarks_history: Sequence,
    width: int,
    height: int,
) -> float:
    """
    Proksi stabilitas tubuh dari goyangan horizontal pinggul (0–100).

    Per frame: rata-rata x piksel hip kiri (23) dan hip kanan (24).
    Std dev deret tersebut dinormalisasi: goyangan > 50 px → stability 0.

    - Frame dengan landmarks None (atau jumlah landmark < indeks 24)
      diabaikan.
    - Tidak ada frame valid → 0.0 (tidak ada data = tidak ada klaim).
    - Landmark di-duck-type: cukup punya atribut `.x` (ruang ternormalisasi
      [0, 1], dikalikan `width` untuk jadi piksel).
    - `height` disediakan untuk kelengkapan signature (analisis 2D sumbu X).

    Return: float 0–100 (100 = sangat stabil).
    """
    hip_means_px = []
    for lm in landmarks_history:
        if lm is None or len(lm) <= max(_L_HIP_IDX, _R_HIP_IDX):
            continue
        hip_x = (lm[_L_HIP_IDX].x + lm[_R_HIP_IDX].x) / 2.0
        hip_means_px.append(hip_x * width)

    if len(hip_means_px) == 0:
        return 0.0

    sway_px = float(np.std(np.asarray(hip_means_px, dtype=float)))
    stability = (1.0 - sway_px / MAX_STABILITY_SWAY_PX) * 100.0
    return float(max(0.0, min(100.0, stability)))


def generate_rule_based_feedback(
    rom: Optional[float],
    consistency: Optional[float],
    stability: float,
    rules: Optional[FeedbackRules] = None,
    rom_reference: float = ROM_REFERENCE_DEG,
) -> dict:
    """
    Skor & feedback berbasis aturan (prototype, BUKAN validasi klinis).

    Rumus skor (0–100):
        (min(rom/rom_reference, 1) * 40) + (consistency * 30) + (stability/100 * 30)
    - rom None (tidak ada repetisi) → 0.
    - consistency None (<3 repetisi) → 0.
    - rom_reference default 135° (perilaku lama); gerakan statis dapat
      meng-override dari MovementConfig.

    Label: >=80 "Baik", >=60 "Cukup", selain itu "Perlu Perbaikan".
    feedback_list: SEMUA pesan yang kondisinya terpenuhi (bukan first-match).

    `rules` diambil dari konfigurasi gerakan (src/movements/); bila None
    dipakai FeedbackRules default (squat) — perilaku identik dengan versi
    sebelum config-driven.

    Return: {"score": float, "label": str, "stability": float,
             "feedback_list": list[str]}
    """
    if rules is None:
        rules = FeedbackRules()

    rom_val = 0.0 if rom is None else float(rom)
    cons_val = 0.0 if consistency is None else float(consistency)
    stab_val = float(stability)
    ref_val = (
        float(rom_reference)
        if rom_reference is not None and float(rom_reference) > 0
        else ROM_REFERENCE_DEG
    )

    score = (
        min(rom_val / ref_val, 1.0) * 40.0
        + cons_val * 30.0
        + (stab_val / 100.0) * 30.0
    )
    score = max(0.0, min(100.0, score))

    if score >= SCORE_GOOD_THRESHOLD:
        label = "Baik"
    elif score >= SCORE_OK_THRESHOLD:
        label = "Cukup"
    else:
        label = "Perlu Perbaikan"

    feedback_list = []
    if rom_val < rules.deep_rom_deg:
        feedback_list.append(rules.low_rom)
    elif rom_val > rules.good_rom_deg:
        feedback_list.append(rules.good_rom)
    if cons_val < MIN_GOOD_CONSISTENCY:
        feedback_list.append(rules.low_consistency)
    if stab_val < MIN_GOOD_STABILITY:
        feedback_list.append(rules.low_stability)

    return {
        "score": float(score),
        "label": label,
        "stability": stab_val,
        "feedback_list": feedback_list,
    }


def compute_isometric_score(
    duration_sec: Optional[float],
    stability: Optional[float],
    target_duration: Optional[float],
) -> dict:
    """Skor gerakan isometrik: 40% durasi tahan + 60% stabilitas."""
    duration_val = 0.0 if duration_sec is None else float(duration_sec)
    stability_val = 0.0 if stability is None else float(stability)
    target_val = 0.0 if target_duration is None else float(target_duration)

    duration_component = 0.0
    if target_val > 0:
        duration_component = min(max(duration_val, 0.0) / target_val, 1.0) * 40.0

    score = duration_component + (stability_val / 100.0) * 60.0

    if score >= SCORE_GOOD_THRESHOLD:
        label = "Baik"
    elif score >= SCORE_OK_THRESHOLD:
        label = "Cukup"
    else:
        label = "Perlu Perbaikan"

    feedback_list = []
    if target_val > 0 and duration_val < target_val:
        feedback_list.append(
            "Durasi tahan kurang. Tahan posisi lebih lama."
        )
    if stability_val < MIN_GOOD_STABILITY:
        feedback_list.append(
            "Tubuh bergoyang. Kencangkan otot perut dan punggung."
        )

    return {
        "score": float(score),
        "label": label,
        "feedback_list": feedback_list,
    }
