"""Unit test untuk src/video_io.py."""

import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.video_io import (  # noqa: E402
    ValidationLimits,
    VideoIOError,
    VideoMeta,
    iter_frames,
    read_meta,
    validate_video,
    write_video,
)


# --- Fixtures ---

@pytest.fixture
def dummy_video(tmp_path):
    """Buat video 30 frame, 640x480, 30fps di tmp_path (~1 detik)."""
    path = tmp_path / "dummy.mp4"
    fps = 30.0
    size = (640, 480)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(path), fourcc, fps, size)
    assert writer.isOpened(), "VideoWriter gagal dibuka (codec tidak tersedia?)"
    try:
        for i in range(30):
            frame = np.full((480, 640, 3), fill_value=(i * 20) % 255, dtype=np.uint8)
            writer.write(frame)
    finally:
        writer.release()
    assert path.exists() and path.stat().st_size > 0
    return path


@pytest.fixture
def corrupt_video(tmp_path):
    """File dengan ekstensi .mp4 tapi isinya bukan video."""
    path = tmp_path / "corrupt.mp4"
    path.write_bytes(b"not a real video file")
    return path


# --- read_meta ---

def test_read_meta_returns_correct_values(dummy_video):
    meta = read_meta(dummy_video)
    assert isinstance(meta, VideoMeta)
    assert meta.width == 640
    assert meta.height == 480
    assert meta.fps == pytest.approx(30.0, abs=1.0)
    # Codec bisa mengubah jumlah frame sedikit; toleransi ±2
    assert abs(meta.frame_count - 30) <= 2


def test_read_meta_raises_on_missing_file(tmp_path):
    with pytest.raises(VideoIOError, match="tidak ditemukan"):
        read_meta(tmp_path / "tidak_ada.mp4")


def test_read_meta_raises_on_corrupt_file(corrupt_video):
    with pytest.raises(VideoIOError):
        read_meta(corrupt_video)


# --- VideoMeta.duration_sec ---

def test_video_meta_duration_property():
    meta = VideoMeta(path=Path("x.mp4"), fps=30.0, width=640, height=480, frame_count=90)
    assert meta.duration_sec == pytest.approx(3.0)


def test_video_meta_duration_zero_fps():
    meta = VideoMeta(path=Path("x.mp4"), fps=0.0, width=640, height=480, frame_count=90)
    assert meta.duration_sec == 0.0


# --- iter_frames ---

def test_iter_frames_yields_correct_count(dummy_video):
    frames = list(iter_frames(dummy_video))
    assert abs(len(frames) - 30) <= 2


def test_iter_frames_yields_correct_shape(dummy_video):
    for idx, frame in iter_frames(dummy_video):
        assert isinstance(idx, int)
        assert isinstance(frame, np.ndarray)
        assert frame.shape == (480, 640, 3)
        assert frame.dtype == np.uint8


def test_iter_frames_index_starts_at_zero(dummy_video):
    first = next(iter_frames(dummy_video))
    assert first[0] == 0


def test_iter_frames_raises_on_missing_file(tmp_path):
    with pytest.raises(VideoIOError, match="tidak ditemukan"):
        list(iter_frames(tmp_path / "tidak_ada.mp4"))


# --- write_video ---

def test_write_video_creates_readable_file(tmp_path):
    out = tmp_path / "out.mp4"
    frames = [
        np.full((240, 320, 3), fill_value=i * 30, dtype=np.uint8) for i in range(5)
    ]
    written = write_video(out, frames, fps=30.0, size=(320, 240))
    assert written == 5
    assert out.exists() and out.stat().st_size > 0

    # Baca balik
    meta = read_meta(out)
    assert meta.width == 320
    assert meta.height == 240


def test_write_video_raises_on_invalid_fps(tmp_path):
    out = tmp_path / "out.mp4"
    with pytest.raises(VideoIOError, match="fps"):
        write_video(out, [], fps=0.0, size=(320, 240))


def test_write_video_raises_on_invalid_size(tmp_path):
    out = tmp_path / "out.mp4"
    with pytest.raises(VideoIOError, match="size"):
        write_video(out, [], fps=30.0, size=(0, 0))


# --- validate_video ---

def test_validate_video_passes_valid(dummy_video):
    meta = validate_video(dummy_video)
    assert isinstance(meta, VideoMeta)


def test_validate_video_rejects_too_short(dummy_video):
    strict = ValidationLimits(min_duration_sec=100.0)
    with pytest.raises(VideoIOError, match="durasi"):
        validate_video(dummy_video, limits=strict)


def test_validate_video_rejects_too_long(dummy_video):
    strict = ValidationLimits(max_duration_sec=0.01)
    with pytest.raises(VideoIOError, match="durasi"):
        validate_video(dummy_video, limits=strict)


def test_validate_video_rejects_low_resolution(dummy_video):
    strict = ValidationLimits(min_width=1920, min_height=1080)
    with pytest.raises(VideoIOError, match="resolusi"):
        validate_video(dummy_video, limits=strict)


def test_validate_video_rejects_bad_fps(dummy_video):
    strict = ValidationLimits(min_fps=100.0)
    with pytest.raises(VideoIOError, match="fps"):
        validate_video(dummy_video, limits=strict)
