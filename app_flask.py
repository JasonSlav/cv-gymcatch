"""
Backend Flask untuk CV Gym Catch (arsitektur client-server).

Route:
- GET  /                    → render templates/index.html
- POST /analyze             → terima video, jalankan src.pipeline.analyze_video,
                              balik JSON (skor, metrik, feedback, sampel frame)
- GET  /history             → daftar riwayat analisis (SQLite)
- GET  /result/<job_id>     → detail satu riwayat
- GET  /download/<job_id>/<file> → unduh file dari output/<job_id>/
- GET  /output/<filename>   → sajikan file hasil analisis dari folder output/

Logika AI tetap di src/ (tidak disentuh). app.py (Streamlit) dibiarkan
sebagai cadangan.

Jalankan:
    python app_flask.py
    → http://localhost:5000  (atau http://<ip-laptop>:5000 dari perangkat lain)
"""

from __future__ import annotations

import json
import re
import sqlite3
import tempfile
import threading
import uuid
from datetime import datetime
from pathlib import Path

from flask import Flask, abort, jsonify, render_template, request, send_from_directory

from src.pipeline import DEFAULT_MODEL_PATH, PipelineError, analyze_video

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
DB_PATH = BASE_DIR / "history.db"
MAX_FILE_SIZE_MB = 50
ALLOWED_EXTENSIONS = {".mp4", ".mov"}
JOB_ID_RE = re.compile(r"^req_[0-9a-f]{12}$")

# Mencegah 2 analisis berjalan bersamaan (MediaPipe & writer tidak thread-safe).
ANALYSIS_LOCK = threading.Lock()

app = Flask(__name__)


def _to_output_url(path) -> str:
    """URL publik untuk file di dalam OUTPUT_DIR (mendukung subfolder UUID)."""
    return "/output/" + Path(path).relative_to(OUTPUT_DIR).as_posix()


def init_db() -> None:
    """Buat tabel riwayat jika belum ada (idempotent)."""
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY,
                job_id TEXT NOT NULL UNIQUE,
                timestamp TEXT NOT NULL,
                video_name TEXT NOT NULL,
                score REAL,
                score_label TEXT,
                reps INTEGER,
                rom REAL,
                stability REAL,
                consistency REAL,
                feedbacks TEXT,
                folder_path TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


init_db()


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
    # Folder unik per request → file antar-device tidak saling menimpa.
    out_dir = OUTPUT_DIR / f"req_{uuid.uuid4().hex[:12]}"
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(data)
            tmp_path = Path(tmp.name)

        with ANALYSIS_LOCK:
            result = analyze_video(
                video_path=tmp_path,
                model_path=DEFAULT_MODEL_PATH,
                output_dir=str(out_dir),
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
        _to_output_url(p)
        for p in result.sample_frames
        if p is not None and Path(p).exists()
    ]
    plot = None
    if result.plot_path is not None and Path(result.plot_path).exists():
        plot = _to_output_url(result.plot_path)

    # Video hasil: WebM/VP8 bisa diputar browser langsung; mp4v hanya
    # sebagai fallback codec (browser umumnya tidak mendukung).
    video_url = _to_output_url(result.annotated_video_path)
    is_browser_playable = result.annotated_video_path.suffix.lower() == ".webm"

    # Simpan metadata ke history (SQLite). Kegagalan DB tidak boleh
    # membatalkan hasil analisis.
    job_id = result.annotated_video_path.parent.name
    try:
        with ANALYSIS_LOCK:
            conn = sqlite3.connect(DB_PATH)
            try:
                conn.execute(
                    "INSERT INTO analyses (job_id, timestamp, video_name, score,"
                    " score_label, reps, rom, stability, consistency, feedbacks,"
                    " folder_path) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        job_id,
                        datetime.now().isoformat(timespec="seconds"),
                        file.filename,
                        round(result.score, 1),
                        result.score_label,
                        primary.rep_count,
                        round(primary.rom, 1) if primary.rom is not None else None,
                        round(result.stability),
                        (
                            round(primary.consistency, 3)
                            if primary.consistency is not None
                            else None
                        ),
                        json.dumps(list(result.feedback_list), ensure_ascii=False),
                        f"output/{job_id}",
                    ),
                )
                conn.commit()
            finally:
                conn.close()
    except Exception as e:  # noqa: BLE001 — history gagal tidak membatalkan analisis
        print(f"[WARN] Gagal menyimpan history: {e}")

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


@app.route("/history")
def history():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id, job_id, timestamp, video_name, score, score_label, reps,"
            " folder_path FROM analyses ORDER BY timestamp DESC, id DESC"
        ).fetchall()
    finally:
        conn.close()

    # Lengkapi tiap baris dengan nama file yang benar-benar ada di foldernya
    # (video bisa .webm atau fallback .mp4).
    data = []
    for r in rows:
        folder = OUTPUT_DIR / r["job_id"]
        video = next((f.name for f in sorted(folder.glob("squat_annotated.*"))), None)
        csv_file = "knee_angle.csv" if (folder / "knee_angle.csv").exists() else None
        data.append({**dict(r), "video_file": video, "csv_file": csv_file})

    return render_template("history.html", mode="list", rows=data)


@app.route("/result/<job_id>")
def result_detail(job_id: str):
    if not JOB_ID_RE.match(job_id):
        abort(404)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT * FROM analyses WHERE job_id = ?", (job_id,)
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        abort(404)

    try:
        feedbacks = json.loads(row["feedbacks"]) if row["feedbacks"] else []
    except (ValueError, TypeError):
        feedbacks = []

    folder = OUTPUT_DIR / job_id
    files = {}
    for key, pattern in (
        ("video", "squat_annotated.*"),
        ("plot", "knee_angle.png"),
        ("csv", "knee_angle.csv"),
    ):
        name = next((f.name for f in sorted(folder.glob(pattern))), None)
        if name:
            files[key] = name

    return render_template(
        "history.html", mode="detail", row=row, feedbacks=feedbacks, files=files
    )


@app.route("/download/<job_id>/<path:filename>")
def download_file(job_id: str, filename: str):
    if not JOB_ID_RE.match(job_id):
        abort(404)
    return send_from_directory(OUTPUT_DIR / job_id, filename, as_attachment=True)


@app.route("/output/<path:filename>")
def output_file(filename: str):
    return send_from_directory(OUTPUT_DIR, filename)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
