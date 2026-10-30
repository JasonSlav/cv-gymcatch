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
import os
import re
import sqlite3
import tempfile
import threading
import uuid
from datetime import datetime
from pathlib import Path

from flask import (
    Flask,
    abort,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from werkzeug.security import check_password_hash, generate_password_hash

from src.pipeline import DEFAULT_MODEL_PATH, PipelineError, analyze_video

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
DB_PATH = BASE_DIR / "history.db"
MAX_FILE_SIZE_MB = 50
ALLOWED_EXTENSIONS = {".mp4", ".mov"}
JOB_ID_RE = re.compile(r"^req_[0-9a-f]{12}$")

# Mencegah 2 analisis berjalan bersamaan (MediaPipe & writer tidak thread-safe).
ANALYSIS_LOCK = threading.Lock()

# Progres analisis per job_id (diisi callback pipeline, dibaca GET /progress).
PROGRESS_DICT: dict = {}
progress_lock = threading.Lock()

PROGRESS_JOB_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

app = Flask(__name__)
# Prototype: fallback dev key. Produksi wajib pakai env SECRET_KEY.
app.secret_key = os.environ.get("SECRET_KEY", "gymcatch-dev-secret-prototype")

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)


class User(UserMixin):
    """User Flask-Login yang dibaca dari tabel users (SQLite)."""

    def __init__(self, id_: int, username: str):
        self.id = str(id_)
        self.username = username

    @staticmethod
    def get(user_id: int) -> "User | None":
        conn = sqlite3.connect(DB_PATH)
        try:
            row = conn.execute(
                "SELECT id, username FROM users WHERE id = ?", (user_id,)
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            return None
        return User(row[0], row[1])

    @staticmethod
    def find_by_username(username: str) -> "User | None":
        conn = sqlite3.connect(DB_PATH)
        try:
            row = conn.execute(
                "SELECT id, username FROM users WHERE username = ?",
                (username,),
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            return None
        return User(row[0], row[1])

    @staticmethod
    def create(username: str, password_hash: str) -> "User | None":
        conn = sqlite3.connect(DB_PATH)
        try:
            cur = conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, password_hash),
            )
            conn.commit()
            return User(cur.lastrowid, username)
        except sqlite3.IntegrityError:
            return None
        finally:
            conn.close()


@login_manager.user_loader
def load_user(user_id: str):
    try:
        return User.get(int(user_id))
    except (TypeError, ValueError):
        return None


def _to_output_url(path) -> str:
    """URL publik untuk file di dalam OUTPUT_DIR (mendukung subfolder UUID)."""
    return "/output/" + Path(path).relative_to(OUTPUT_DIR).as_posix()


def init_db() -> None:
    """Buat/migrasi tabel (idempotent) — users + analyses(user_id)."""
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL
            )
            """
        )
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
                folder_path TEXT NOT NULL,
                user_id INTEGER
            )
            """
        )
        # Migrasi DB lama: tambah kolom user_id bila belum ada.
        cols = {r[1] for r in conn.execute("PRAGMA table_info(analyses)").fetchall()}
        if "user_id" not in cols:
            conn.execute("ALTER TABLE analyses ADD COLUMN user_id INTEGER")
            # Baris tanpa user (demo/legacy) dihapus agar riwayat bersifat privat.
            conn.execute("DELETE FROM analyses WHERE user_id IS NULL")
        conn.commit()
    finally:
        conn.close()


init_db()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        user = User.find_by_username(username) if username else None
        if user is None or not check_password_hash(
            _get_hash(username), password
        ):
            error = "Username atau password salah."
        else:
            login_user(user)
            return redirect(url_for("index"))
    return render_template("login.html", error=error)


def _get_hash(username: str) -> str:
    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute(
            "SELECT password_hash FROM users WHERE username = ?", (username,)
        ).fetchone()
    finally:
        conn.close()
    return row[0] if row else ""


@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        if not username or not password:
            error = "Username dan password wajib diisi."
        elif len(password) < 4:
            error = "Password minimal 4 karakter."
        else:
            user = User.create(username, generate_password_hash(password))
            if user is None:
                error = "Username sudah dipakai."
            else:
                login_user(user)
                return redirect(url_for("index"))
    return render_template("register.html", error=error)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("index"))


@app.route("/analyze", methods=["POST"])
@login_required
def analyze():
    # job_id dari frontend (FormData); bila tidak valid/absen, server
    # menghasilkan sendiri — dipakai sebagai key progress polling.
    job_id = request.form.get("job_id") or ""
    if not PROGRESS_JOB_ID_RE.match(job_id):
        job_id = uuid.uuid4().hex[:12]

    def on_progress(done: int, total: int) -> None:
        with progress_lock:
            PROGRESS_DICT[job_id] = (done, total)

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
                progress_callback=on_progress,
            )
    except PipelineError as e:
        return jsonify({"error": f"Gagal menganalisis video: {e}"}), 422
    except Exception as e:  # noqa: BLE001
        return jsonify({"error": f"Terjadi kesalahan tak terduga: {e}"}), 500
    finally:
        with progress_lock:
            PROGRESS_DICT.pop(job_id, None)
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
                    " folder_path, user_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
                        current_user.get_id() and int(current_user.get_id()),
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


@app.route("/progress/<job_id>")
@login_required
def progress(job_id: str):
    if not PROGRESS_JOB_ID_RE.match(job_id):
        abort(404)
    with progress_lock:
        done, total = PROGRESS_DICT.get(job_id, (0, 0))
    return jsonify({"done": done, "total": total})


@app.route("/history")
@login_required
def history():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id, job_id, timestamp, video_name, score, score_label, reps,"
            " folder_path FROM analyses WHERE user_id = ?"
            " ORDER BY timestamp DESC, id DESC",
            (current_user.get_id(),),
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
@login_required
def result_detail(job_id: str):
    if not JOB_ID_RE.match(job_id):
        abort(404)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT * FROM analyses WHERE job_id = ? AND user_id = ?",
            (job_id, current_user.get_id()),
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
@login_required
def download_file(job_id: str, filename: str):
    if not JOB_ID_RE.match(job_id):
        abort(404)
    if not _owns_job(job_id):
        abort(404)
    return send_from_directory(OUTPUT_DIR / job_id, filename, as_attachment=True)


def _owns_job(job_id: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute(
            "SELECT 1 FROM analyses WHERE job_id = ? AND user_id = ?",
            (job_id, current_user.get_id()),
        ).fetchone()
    finally:
        conn.close()
    return row is not None


@app.route("/output/<path:filename>")
@login_required
def output_file(filename: str):
    # Segmen pertama = folder job (req_xxx). Pastikan milik user ini.
    parts = filename.split("/")
    if len(parts) > 1 and JOB_ID_RE.match(parts[0]) and not _owns_job(parts[0]):
        abort(404)
    return send_from_directory(OUTPUT_DIR, filename)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
