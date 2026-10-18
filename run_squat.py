"""
CLI wrapper tipis di atas src.pipeline.analyze_video().

Contoh pemakaian:
    python run_squat.py

Output di folder output/ (lihat AnalysisResult).
"""

from __future__ import annotations

import sys

from src.pipeline import DEFAULT_MODEL_PATH, PipelineError, analyze_video


VIDEO_PATH = "data/squat_sample.mp4"
OUT_DIR = "output"


def _progress(done: int, total: int) -> None:
    print(f"[INFO] Proses {done}/{total} frame")


def main() -> int:
    print(f"[INFO] Video: {VIDEO_PATH}")
    try:
        result = analyze_video(
            video_path=VIDEO_PATH,
            model_path=DEFAULT_MODEL_PATH,
            output_dir=OUT_DIR,
            progress_callback=_progress,
        )
    except PipelineError as e:
        print(f"[ERROR] {e}")
        return 1

    print(result.summary_text)
    print(f"[OUT ] {result.annotated_video_path}")
    print(f"[OUT ] {result.csv_path}")
    if result.plot_path is not None:
        print(f"[OUT ] {result.plot_path}")
    print(f"[OUT ] {result.summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
