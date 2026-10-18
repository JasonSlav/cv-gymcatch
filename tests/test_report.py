"""Unit test untuk src/report.py."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.report import (  # noqa: E402
    choose_display_series,
    format_summary_text,
    write_angles_csv,
)


# --- choose_display_series ---

def test_choose_both_when_both_fully_valid():
    left = [100.0] * 10
    right = [110.0] * 10
    mode, s1, s2 = choose_display_series(left, right)
    assert mode == "both"
    assert s1 is left
    assert s2 is right


def test_choose_both_at_threshold_boundary():
    left = [100.0] * 9 + [None]  # 90%
    right = [100.0] * 9 + [None]  # 90%
    mode, _, _ = choose_display_series(left, right, both_threshold=0.9)
    assert mode == "both"


def test_choose_left_when_only_left_valid():
    left = [100.0] * 10
    right = [None] * 10
    mode, s1, s2 = choose_display_series(left, right)
    assert mode == "left"
    assert s1 is left
    assert s2 is None


def test_choose_right_when_only_right_valid():
    left = [None] * 10
    right = [100.0] * 10
    mode, s1, s2 = choose_display_series(left, right)
    assert mode == "right"
    assert s1 is None
    assert s2 is right


def test_choose_left_when_left_more_valid():
    left = [100.0] * 8 + [None] * 2  # 80%
    right = [100.0] * 4 + [None] * 6  # 40%
    mode, _, _ = choose_display_series(left, right)
    assert mode == "left"


def test_choose_right_when_right_more_valid():
    left = [100.0] * 3 + [None] * 7  # 30%
    right = [100.0] * 8 + [None] * 2  # 80%
    mode, _, _ = choose_display_series(left, right)
    assert mode == "right"


def test_choose_none_when_all_invalid():
    mode, s1, s2 = choose_display_series([None] * 5, [None] * 5)
    assert mode == "none"
    assert s1 is None
    assert s2 is None


def test_choose_none_when_empty():
    mode, s1, s2 = choose_display_series([], [])
    assert mode == "none"


def test_choose_raises_on_length_mismatch():
    with pytest.raises(ValueError, match="Panjang"):
        choose_display_series([100.0, 100.0], [100.0])


# --- write_angles_csv ---

def test_write_angles_csv_writes_header_and_rows(tmp_path):
    left = [100.0, None, 90.0]
    right = [None, 80.0, None]
    out = tmp_path / "angles.csv"
    n = write_angles_csv(out, left, right)
    assert n == 3

    content = out.read_text(encoding="utf-8")
    lines = content.strip().split("\n")
    assert lines[0] == "frame,left_knee_angle_deg,right_knee_angle_deg,left_valid,right_valid"
    assert len(lines) == 4

    # Baris 1: left=100, right kosong
    assert lines[1] == "0,100.000,,1,0"
    # Baris 2: left kosong, right=80
    assert lines[2] == "1,,80.000,0,1"


def test_write_angles_csv_creates_parent_dir(tmp_path):
    out = tmp_path / "nested" / "deep" / "angles.csv"
    write_angles_csv(out, [100.0], [100.0])
    assert out.exists()


def test_write_angles_csv_empty(tmp_path):
    out = tmp_path / "empty.csv"
    n = write_angles_csv(out, [], [])
    assert n == 0
    content = out.read_text(encoding="utf-8").strip().split("\n")
    assert len(content) == 1  # hanya header


def test_write_angles_csv_raises_on_mismatch(tmp_path):
    with pytest.raises(ValueError):
        write_angles_csv(tmp_path / "x.csv", [1.0], [1.0, 2.0])


# --- format_summary_text ---

def test_format_summary_contains_key_info():
    text = format_summary_text(
        video_name="test.mp4",
        width=640, height=480, fps=30.0,
        frame_count=100, process_sec=5.5,
        side_results=[
            {"side": "kiri", "valid_frames": 100, "rep_count": 3,
             "rom": 130.5, "consistency": 0.9},
            {"side": "kanan", "valid_frames": 0, "rep_count": 0,
             "rom": None, "consistency": None},
        ],
    )
    assert "test.mp4" in text
    assert "640x480" in text
    assert "30.00" in text
    assert "3.33s" in text  # 100/30
    assert "5.50s" in text
    assert "Sisi kiri" in text
    assert "Sisi kanan" in text
    assert "130.50" in text
    assert "0.900" in text
    assert "N/A" in text


def test_format_summary_handles_zero_fps():
    text = format_summary_text(
        video_name="x.mp4", width=100, height=100, fps=0.0,
        frame_count=10, process_sec=1.0, side_results=[],
    )
    assert "Durasi       : N/A" in text


def test_format_summary_handles_empty_side_results():
    text = format_summary_text(
        video_name="x.mp4", width=100, height=100, fps=30.0,
        frame_count=10, process_sec=1.0, side_results=[],
    )
    assert "tidak ada sisi" in text
