"""
Backend Flask untuk CV Gym Catch (arsitektur client-server).

Route:
- GET  /                    → render templates/index.html
- POST /analyze             → terima video, jalankan src.pipeline.analyze_video,
                               balik JSON (skor, metrik, feedback, sampel frame)
- GET  /output/<filename>   → sajikan file hasil analisis dari folder output/

Logika AI tetap di src/ (tidak disentuh). app.py (Streamlit) dibiarkan
sebagai cadangan.

Jalankan:
    python app_flask.py
    → http://localhost:5000  (atau http://<ip-laptop>:5000 dari perangkat lain)
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory

from src.pipeline import DEFAULT_MODEL_PATH, PipelineError, analyze_video

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
MAX_FILE_SIZE_MB = 50
ALLOWED_EXTENSIONS = {".mp4", ".mov"}

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    file = request.files.get("video")
    if file is None or not file.filename:
        return jsonify({"error": "Tidak ada file video yang diunggah."}), 400

    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        return (
            jsonify({"error": "Format tidak didukung. Gunakan mp4 atau mov."}),
            400,
        )

    data = file.read()
    size_mb = len(data) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        return (
            jsonify(
                {
                    "error": (
                        f"Ukuran file {size_mb:.1f} MB melebihi batas "
                        f"{MAX_FILE_SIZE_MB} MB."
                    )
                }
            ),
            400,
        )

    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(data)
            tmp_path = Path(tmp.name)

        result = analyze_video(
            video_path=tmp_path,
            model_path=DEFAULT_MODEL_PATH,
            output_dir=str(OUTPUT_DIR),
        )
    except PipelineError as e:
        return jsonify({"error": f"Gagal menganalisis video: {e}"}), 422
    except Exception as e:  # noqa: BLE001
        return jsonify({"error": f"Terjadi kesalahan tak terduga: {e}"}), 500
    finally:
        if tmp_path is not None and tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass

    # Pemilihan sisi — kaidah identik dengan app.py (Streamlit).
    left = result.left_analysis
    right = result.right_analysis
    if result.display_mode == "both":
        primary = left if left.rep_count >= right.rep_count else right
    elif result.display_mode == "left":
        primary = left
    elif result.display_mode == "right":
        primary = right
    else:
        primary = left

    duration = (
        result.meta.frame_count / result.meta.fps if result.meta.fps else 0.0
    )
    samples = [
        f"/output/{Path(p).name}"
        for p in result.sample_frames
        if p is not None and Path(p).exists()
    ]
    plot = None
    if result.plot_path is not None and Path(result.plot_path).exists():
        plot = f"/output/{Path(result.plot_path).name}"

    # Video hasil: WebM/VP8 bisa diputar browser langsung; mp4v hanya
    # sebagai fallback codec (browser umumnya tidak mendukung).
    video_url = f"/output/{result.annotated_video_path.name}"
    is_browser_playable = result.annotated_video_path.suffix.lower() == ".webm"

    return jsonify(
        {
            "score": round(result.score, 1),
            "score_label": result.score_label,
            "reps": primary.rep_count,
            "rom": round(primary.rom, 1) if primary.rom is not None else None,
            "stability": round(result.stability),
            "consistency": (
                round(primary.consistency, 3)
                if primary.consistency is not None
                else None
            ),
            "duration_sec": round(duration, 1),
            "side": primary.side,
            "feedbacks": list(result.feedback_list),
            "process_sec": round(result.process_sec, 2),
            "samples": samples,
            "plot": plot,
            "video_url": video_url,
            "is_browser_playable": is_browser_playable,
            # Deret sudut untuk grafik interaktif (Chart.js).
            # None di list otomatis menjadi null oleh jsonify.
            "angle_data": {
                "mode": result.display_mode,  # "both" | "left" | "right"
                "left": list(result.left_angles),
                "right": list(result.right_angles),
            },
        }
    )


@app.route("/output/<path:filename>")
def output_file(filename: str):
    return send_from_directory(OUTPUT_DIR, filename)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
