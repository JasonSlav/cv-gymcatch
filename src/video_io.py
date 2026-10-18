"""
Modul I/O video.

Semua fungsi di sini:
- Hanya bergantung pada OpenCV dan stdlib.
- Tidak menyentuh MediaPipe atau logika analisis gerakan.
- Memisahkan I/O murni (read/iter/write) dari kebijakan validasi.

Konvensi:
- Frame disimpan sebagai np.ndarray BGR (sesuai cv2).
- Path menerima str atau Path.
- Error dilempar sebagai VideoIOError dengan pesan spesifik.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Optional, Tuple

import cv2
import numpy as np

DEFAULT_OUTPUT_FOURCC = "mp4v"


class VideoIOError(Exception):
    """Error saat membaca, menulis, atau memvalidasi video."""


@dataclass(frozen=True)
class VideoMeta:
    """Metadata video hasil read_meta()."""

    path: Path
    fps: float
    width: int
    height: int
    frame_count: int

    @property
    def duration_sec(self) -> float:
        if self.fps <= 0:
            return 0.0
        return self.frame_count / self.fps


@dataclass(frozen=True)
class ValidationLimits:
    """Batas validasi video. Dapat diubah per pemanggilan."""

    min_duration_sec: float = 0.5
    max_duration_sec: float = 60.0
    min_fps: float = 1.0
    max_fps: float = 240.0
    min_width: int = 320
    min_height: int = 240


def _as_path(path) -> Path:
    return path if isinstance(path, Path) else Path(path)


def read_meta(path) -> VideoMeta:
    """
    Baca metadata video tanpa mengiterasi frame.

    Raises
    ------
    VideoIOError
        Jika file tidak ada, tidak bisa dibuka, atau metadata tidak lengkap.
    """
    p = _as_path(path)
    if not p.exists():
        raise VideoIOError(f"File video tidak ditemukan: {p}")

    cap = cv2.VideoCapture(str(p))
    try:
        if not cap.isOpened():
            raise VideoIOError(
                f"Gagal membuka video (format tidak didukung atau file rusak): {p}"
            )
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    finally:
        cap.release()

    if width <= 0 or height <= 0:
        raise VideoIOError(f"Resolusi video tidak valid ({width}x{height}): {p}")
    if frame_count <= 0:
        raise VideoIOError(f"Video tidak berisi frame: {p}")

    return VideoMeta(
        path=p, fps=fps, width=width, height=height, frame_count=frame_count
    )


def iter_frames(path) -> Iterator[Tuple[int, np.ndarray]]:
    """
    Generator yang yield (frame_idx, frame_bgr) sampai video habis.

    Frame yang gagal dibaca di-skip (tidak di-yield). Generator berhenti
    ketika cap.read() mengembalikan False.

    Raises
    ------
    VideoIOError
        Jika video tidak bisa dibuka sejak awal.
    """
    p = _as_path(path)
    if not p.exists():
        raise VideoIOError(f"File video tidak ditemukan: {p}")

    cap = cv2.VideoCapture(str(p))
    if not cap.isOpened():
        raise VideoIOError(
            f"Gagal membuka video (format tidak didukung atau file rusak): {p}"
        )

    try:
        idx = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            yield idx, frame
            idx += 1
    finally:
        cap.release()


def write_video(
    path,
    frames: Iterable[np.ndarray],
    fps: float,
    size: Tuple[int, int],
    fourcc: str = DEFAULT_OUTPUT_FOURCC,
) -> int:
    """
    Tulis frame ke file video.

    Parameter
    ---------
    path : str | Path
        Path file output.
    frames : Iterable[np.ndarray]
        Iterable frame BGR.
    fps : float
        Frame rate output. Harus > 0.
    size : (width, height)
        Ukuran output (sesuai cv2.VideoWriter).
    fourcc : str
        FourCC codec, default "mp4v".

    Returns
    -------
    int
        Jumlah frame yang berhasil ditulis.

    Raises
    ------
    VideoIOError
        Jika fps/size tidak valid atau VideoWriter gagal dibuat.
    """
    if fps <= 0:
        raise VideoIOError(f"fps harus > 0, dapat {fps}")
    if len(size) != 2 or size[0] <= 0 or size[1] <= 0:
        raise VideoIOError(f"size tidak valid: {size}")

    p = _as_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    fourcc_code = cv2.VideoWriter_fourcc(*fourcc)
    writer = cv2.VideoWriter(str(p), fourcc_code, float(fps), tuple(size))
    if not writer.isOpened():
        raise VideoIOError(
            f"Gagal membuat VideoWriter untuk {p} "
            f"(codec={fourcc}, fps={fps}, size={size})"
        )

    written = 0
    try:
        for frame in frames:
            writer.write(frame)
            written += 1
    finally:
        writer.release()
    return written


def validate_video(
    path, limits: Optional[ValidationLimits] = None
) -> VideoMeta:
    """
    Baca metadata dan validasi terhadap batas yang ditentukan.

    Returns
    -------
    VideoMeta
        Metadata video jika lulus validasi.

    Raises
    ------
    VideoIOError
        Jika metadata tidak bisa dibaca atau melanggar salah satu batas.
    """
    lim = limits or ValidationLimits()
    meta = read_meta(path)
    dur = meta.duration_sec

    if meta.fps < lim.min_fps or meta.fps > lim.max_fps:
        raise VideoIOError(
            f"fps {meta.fps:.2f} di luar rentang [{lim.min_fps}, {lim.max_fps}]"
        )
    if dur < lim.min_duration_sec:
        raise VideoIOError(
            f"durasi {dur:.2f}s < minimum {lim.min_duration_sec}s"
        )
    if dur > lim.max_duration_sec:
        raise VideoIOError(
            f"durasi {dur:.2f}s > maksimum {lim.max_duration_sec}s"
        )
    if meta.width < lim.min_width or meta.height < lim.min_height:
        raise VideoIOError(
            f"resolusi {meta.width}x{meta.height} < minimum "
            f"{lim.min_width}x{lim.min_height}"
        )
    return meta
