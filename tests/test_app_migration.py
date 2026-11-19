"""Test migrasi DB dan kompatibilitas history lama."""

import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Arahkan init_db saat import ke DB sementara agar history.db asli tidak
# tersentuh oleh test suite.
_IMPORT_TMP = Path(tempfile.mkdtemp(prefix="gymcatch-app-test-"))
os.environ["GYMCATCH_DB_PATH"] = str(_IMPORT_TMP / "import.db")

import app_flask  # noqa: E402


def _create_legacy_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.execute(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE analyses (
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
                user_id INTEGER,
                movement_type TEXT DEFAULT 'squat',
                duration_sec REAL,
                exercise_type TEXT DEFAULT 'dynamic'
            )
            """
        )
        conn.execute(
            "INSERT INTO users (id, username, password_hash)"
            " VALUES (1, 'tester', 'x')"
        )
        conn.execute(
            "INSERT INTO analyses (job_id, timestamp, video_name, score,"
            " score_label, reps, rom, stability, consistency, feedbacks,"
            " folder_path, user_id, movement_type, duration_sec, exercise_type)"
            " VALUES ('req_000000000001', '2026-11-19T10:00:00', 'old.mp4',"
            " 70, 'Cukup', 3, 50, 90, 0.8, '[]', 'output/req_000000000001',"
            " 1, 'back_up', 5.0, 'dynamic')"
        )
        conn.commit()
    finally:
        conn.close()


def test_init_db_is_idempotent_and_preserves_old_row(tmp_path):
    db_path = tmp_path / "legacy.db"
    _create_legacy_db(db_path)

    app_flask.init_db(db_path)
    app_flask.init_db(db_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        analysis_cols = {
            r[1] for r in conn.execute("PRAGMA table_info(analyses)").fetchall()
        }
        user_cols = {
            r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()
        }
        assert "movement_control" in analysis_cols
        assert "full_name" in user_cols
        assert "email" in user_cols

        row = conn.execute(
            "SELECT * FROM analyses WHERE job_id = 'req_000000000001'"
        ).fetchone()
        assert row is not None
        assert row["movement_control"] is None

        conn.execute(
            "UPDATE analyses SET movement_control = 0"
            " WHERE job_id = 'req_000000000001'"
        )
        conn.commit()
        row = conn.execute(
            "SELECT movement_control FROM analyses"
            " WHERE job_id = 'req_000000000001'"
        ).fetchone()
        assert row["movement_control"] is not None
        assert row["movement_control"] == 0
    finally:
        conn.close()


def _prepare_app_db(db_path: Path, output_dir: Path) -> None:
    app_flask.init_db(db_path)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "INSERT INTO users (id, username, password_hash, full_name, email)"
            " VALUES (1, 'tester', 'x', '', 'tester@example.com')"
        )
        rows = [
            ("req_000000000002", None),
            ("req_000000000003", 0.0),
        ]
        for job_id, control in rows:
            (output_dir / job_id).mkdir(parents=True, exist_ok=True)
            conn.execute(
                "INSERT INTO analyses (job_id, timestamp, video_name, score,"
                " score_label, reps, rom, stability, consistency, feedbacks,"
                " folder_path, user_id, movement_type, duration_sec,"
                " exercise_type, movement_control)"
                " VALUES (?, '2026-11-19T10:00:00', 'old.mp4', 70, 'Cukup',"
                " 3, 50, 90, 0.8, ?, ?, 1, 'back_up', 5.0, 'dynamic', ?)",
                (
                    job_id,
                    json.dumps([]),
                    f"output/{job_id}",
                    control,
                ),
            )
        conn.commit()
    finally:
        conn.close()


def test_history_and_detail_handle_old_null_and_zero(tmp_path, monkeypatch):
    db_path = tmp_path / "history.db"
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    _prepare_app_db(db_path, output_dir)

    monkeypatch.setattr(app_flask, "DB_PATH", db_path)
    monkeypatch.setattr(app_flask, "OUTPUT_DIR", output_dir)
    app_flask.app.config["TESTING"] = True

    client = app_flask.app.test_client()
    with client.session_transaction() as session:
        session["_user_id"] = "1"
        session["_fresh"] = True

    response = client.get("/history")
    assert response.status_code == 200

    # Row lama dengan movement_control NULL tidak menampilkan tile.
    old = client.get("/result/req_000000000002")
    assert old.status_code == 200
    assert "Kontrol Gerakan" not in old.get_data(as_text=True)

    # Nilai 0 adalah nilai valid dan harus tampil sebagai 0%.
    zero = client.get("/result/req_000000000003")
    assert zero.status_code == 200
    body = zero.get_data(as_text=True)
    assert "Kontrol Gerakan" in body
    assert "0%" in body


def test_read_angle_series_accepts_legacy_and_new(tmp_path):
    legacy = tmp_path / "legacy"
    legacy.mkdir()
    (legacy / "knee_angle.csv").write_text(
        "frame,left_hip_angle_deg,right_hip_angle_deg,left_valid,right_valid\n"
        "0,170.0,171.0,1,1\n"
        "1,,172.0,0,1\n",
        encoding="utf-8",
    )
    old_data = app_flask._read_angle_series(legacy)
    assert old_data is not None
    assert old_data["mode"] == "both"
    assert old_data["left"] == [170.0, None]

    modern = tmp_path / "modern"
    modern.mkdir()
    (modern / "joint_angle.csv").write_text(
        "frame,left_knee_angle_deg,right_knee_angle_deg,left_valid,right_valid\n"
        "0,100.0,110.0,1,1\n",
        encoding="utf-8",
    )
    (modern / "knee_angle.csv").write_text(
        "frame,left_knee_angle_deg,right_knee_angle_deg,left_valid,right_valid\n"
        "0,1.0,2.0,1,1\n",
        encoding="utf-8",
    )
    new_data = app_flask._read_angle_series(modern)
    assert new_data is not None
    assert new_data["left"] == [100.0]
