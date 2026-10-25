"""
Pipeline end-to-end modular: video → pose → sudut → rep → visualisasi.

Modul ini adalah satu-satunya tempat orkestrasi. Ia bergantung pada
modul-modul di src/, tapi TIDAK menyentuh MediaPipe/OpenCV secara langsung
(kecuali VideoWriter untuk output).

Dipakai oleh:
- run_squat.py (CLI wrapper)
- app.py (Streamlit wrapper) — sesi berikutnya
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional, Sequence

import cv2

from src.metrics import (
    MIN_REPS_FOR_CONSISTENCY,
    RepCountResult,
    compute_consistency,
    compute_rom,
    compute_stability_proxy,
    count_reps,
    extract_rep_curves,
    generate_rule_based_feedback,
)
from src.pose_estimator import (
    LEFT_ANKLE,
    LEFT_HIP,
    LEFT_KNEE,
    RIGHT_ANKLE,
    RIGHT_HIP,
    RIGHT_KNEE,
    PoseEstimator,
    PoseEstimatorError,
    angle_from_landmarks,
)
from src.report import (
    choose_display_series,
    format_summary_text,
    write_angles_csv,
)
from src.video_io import VideoIOError, VideoMeta, iter_frames, read_meta
from src.visualize import (
    draw_angle_label,
    draw_pose_on_frame,
    plot_angle_series,
)


DEFAULT_MODEL_PATH = Path("models/pose_landmarker_full.task")
DEFAULT_MIN_VISIBILITY = 0.5
PROGRESS_EVERY_N_FRAMES = 30


class PipelineError(Exception):
    """Error di level orkestrasi pipeline."""


@dataclass
class SideAnalysis:
    """Hasil analisis satu sisi tubuh."""

    side: str
    valid_frames: int
    rep_count: int
    rom: Optional[float]
    consistency: Optional[float]
    rep_result: RepCountResult

    def to_dict(self) -> dict:
        return {
            "side": self.side,
            "valid_frames": self.valid_frames,
            "rep_count": self.rep_count,
            "rom": self.rom,
            "consistency": self.consistency,
        }


@dataclass
class AnalysisResult:
    """Hasil lengkap satu analisis video."""

    meta: VideoMeta
    left_angles: list
    right_angles: list
    left_analysis: SideAnalysis
    right_analysis: SideAnalysis
    display_mode: str  # "both" | "left" | "right" | "none"
    annotated_video_path: Path
    csv_path: Path
    plot_path: Optional[Path]
    summary_path: Path
    summary_text: str
    process_sec: float
    stability: float
    score: float
    score_label: str
    feedback_list: list[str]
    sample_frames: list[Path] = field(default_factory=list)


def analyze_side(
    angles: Sequence[Optional[float]],
    side_name: str,
) -> SideAnalysis:
    """
    Hitung rep count, ROM, consistency untuk satu sisi.

    Murni — bisa di-unit-test tanpa video atau model.
    """
    rep_result = count_reps(angles)
    rom = compute_rom(angles)
    consistency = None
    if rep_result.count >= MIN_REPS_FOR_CONSISTENCY:
        curves = extract_rep_curves(angles, rep_result)
        consistency = compute_consistency(curves)
    return SideAnalysis(
        side=side_name,
        valid_frames=sum(1 for a in angles if a is not None),
        rep_count=rep_result.count,
        rom=rom,
        consistency=consistency,
        rep_result=rep_result,
    )


def extract_sample_frames(
    video_path: Path,
    valley_idx: int,
    total_frames: int,
    output_dir: Path,
) -> list[Path]:
    """
    Ambil 3 frame sampel dari video hasil (start, mid/valley, end).

    Codec mp4v (MPEG-4 Part 2) pada video hasil tidak diputar oleh browser
    modern — frame JPG dipakai sebagai fallback tampilan web.

    Mengembalikan list path yang berhasil disimpan (boleh < 3; [] jika
    video tidak bisa dibuka).
    """
    output_dir = Path(output_dir)
    if total_frames <= 0:
        return []
    mid_idx = max(0, min(valley_idx, total_frames - 1))
    targets = (
        (0, "sample_start.jpg"),
        (mid_idx, "sample_mid.jpg"),
        (total_frames - 1, "sample_end.jpg"),
    )
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return []
    paths: list[Path] = []
    try:
        for idx, name in targets:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ok, frame = cap.read()
            if not ok:
                continue
            out_path = output_dir / name
            if cv2.imwrite(str(out_path), frame):
                paths.append(out_path)
    finally:
        cap.release()
    return paths


def analyze_video(
    video_path,
    model_path=DEFAULT_MODEL_PATH,
    output_dir="output",
    min_visibility: float = DEFAULT_MIN_VISIBILITY,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> AnalysisResult:
    """
    Jalankan pipeline end-to-end untuk satu video.

    Parameter
    ---------
    video_path : str | Path
    model_path : str | Path
        Path ke file model .task.
    output_dir : str | Path
        Folder output. Dibuat jika belum ada.
    min_visibility : float
        Ambang visibility landmark, default 0.5.
    progress_callback : callable | None
        Callback(done_frames, total_frames) dipanggil periodik. Error di
        callback tidak akan mematikan pipeline.

    Returns
    -------
    AnalysisResult

    Raises
    ------
    PipelineError
        Jika baca video, inisialisasi pose, atau tulis video gagal.
    """
    t0 = time.time()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # --- Baca metadata ---
    try:
        meta = read_meta(video_path)
    except VideoIOError as e:
        raise PipelineError(str(e)) from e

    # --- Siapkan VideoWriter ---
    annotated_path = output_dir / "squat_annotated.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(
        str(annotated_path), fourcc, meta.fps, (meta.width, meta.height)
    )
    if not writer.isOpened():
        raise PipelineError(f"Gagal membuat VideoWriter untuk {annotated_path}")

    # --- Inisialisasi estimator ---
    try:
        estimator = PoseEstimator(model_path=model_path)
    except PoseEstimatorError as e:
        writer.release()
        raise PipelineError(str(e)) from e

    left_angles: list = []
    right_angles: list = []
    landmarks_history: list = []

    try:
        with estimator:
            for idx, frame in iter_frames(video_path):
                timestamp_ms = (
                    int(idx / meta.fps * 1000) if meta.fps > 0 else idx * 33
                )
                result = estimator.detect(frame, timestamp_ms)
                landmarks_history.append(result.landmarks)

                left_a = right_a = None
                if result.detected:
                    lm = result.landmarks
                    left_a = angle_from_landmarks(
                        lm[LEFT_HIP], lm[LEFT_KNEE], lm[LEFT_ANKLE],
                        meta.width, meta.height, min_visibility,
                    )
                    right_a = angle_from_landmarks(
                        lm[RIGHT_HIP], lm[RIGHT_KNEE], lm[RIGHT_ANKLE],
                        meta.width, meta.height, min_visibility,
                    )

                    draw_pose_on_frame(frame, lm, inplace=True)
                    if left_a is not None:
                        draw_angle_label(
                            frame, f"L knee: {left_a:.1f}", (20, 40),
                            color=(0, 255, 0),
                        )
                    if right_a is not None:
                        draw_angle_label(
                            frame, f"R knee: {right_a:.1f}", (20, 80),
                            color=(0, 128, 255),
                        )

                left_angles.append(left_a)
                right_angles.append(right_a)
                writer.write(frame)

                if progress_callback is not None and (
                    (idx + 1) % PROGRESS_EVERY_N_FRAMES == 0
                    or (idx + 1) == meta.frame_count
                ):
                    try:
                        progress_callback(idx + 1, meta.frame_count)
                    except Exception:
                        # callback error tidak boleh mematikan pipeline
                        pass
    finally:
        writer.release()

    # --- Analisis ---
    left_analysis = analyze_side(left_angles, "kiri")
    right_analysis = analyze_side(right_angles, "kanan")

    # --- Sampel frame (fallback tampilan web: mp4v tidak diputar browser) ---
    valley_idx = (
        left_analysis.rep_result.reps[0].valley_idx
        if left_analysis.rep_result.reps
        else meta.frame_count // 2
    )
    sample_frames = extract_sample_frames(
        annotated_path, valley_idx, meta.frame_count, output_dir
    )

    # --- Skor & feedback rule-based (prototype, bukan validasi klinis) ---
    stability = compute_stability_proxy(
        landmarks_history, meta.width, meta.height
    )
    primary = (
        left_analysis
        if left_analysis.rep_count >= right_analysis.rep_count
        else right_analysis
    )
    score_info = generate_rule_based_feedback(
        primary.rom, primary.consistency, stability
    )

    # --- CSV ---
    csv_path = output_dir / "knee_angle.csv"
    write_angles_csv(csv_path, left_angles, right_angles)

    # --- Plot ---
    mode, s1, s2 = choose_display_series(left_angles, right_angles)
    plot_path: Optional[Path] = None
    png_path = output_dir / "knee_angle.png"
    try:
        if mode == "both":
            plot_angle_series(left_angles=s1, right_angles=s2, output_path=png_path)
            plot_path = png_path
        elif mode == "left":
            plot_angle_series(
                angles=s1, rep_result=left_analysis.rep_result,
                output_path=png_path,
            )
            plot_path = png_path
        elif mode == "right":
            plot_angle_series(
                angles=s2, rep_result=right_analysis.rep_result,
                output_path=png_path,
            )
            plot_path = png_path
    except ValueError:
        plot_path = None

    # --- Summary ---
    elapsed = time.time() - t0
    summary_text = format_summary_text(
        video_name=str(video_path),
        width=meta.width, height=meta.height, fps=meta.fps,
        frame_count=meta.frame_count, process_sec=elapsed,
        side_results=[left_analysis.to_dict(), right_analysis.to_dict()],
    )
    summary_path = output_dir / "summary.txt"
    summary_path.write_text(summary_text, encoding="utf-8")

    return AnalysisResult(
        meta=meta,
        left_angles=left_angles,
        right_angles=right_angles,
        left_analysis=left_analysis,
        right_analysis=right_analysis,
        display_mode=mode,
        annotated_video_path=annotated_path,
        csv_path=csv_path,
        plot_path=plot_path,
        summary_path=summary_path,
        summary_text=summary_text,
        process_sec=elapsed,
        stability=stability,
        score=score_info["score"],
        score_label=score_info["label"],
        feedback_list=score_info["feedback_list"],
        sample_frames=sample_frames,
    )
