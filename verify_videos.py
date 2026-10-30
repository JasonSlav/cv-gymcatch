"""
Verifikasi end-to-end Fase 1: UUID folder, Rotasi video HP, VFR timestamps.

Jalankan manual (bukan bagian tests/):
    python verify_videos.py

Setiap video diproses ke folder output/verify_<nama>/ agar bisa dicek
secara visual setelahnya. Ringkasan LULUS/GAGAL/SKIP dicetak di akhir.
"""

from __future__ import annotations

import itertools
import time
from pathlib import Path

from src.pipeline import analyze_video
from src.video_io import iter_frames_timestamped, read_meta

VIDEOS = [
    ("data/squat_sample.mp4", "landscape"),
    ("data/portrait.mp4", "portrait"),
    ("data/vfr.mp4", "vfr"),
]


def check_vfr(path: Path, n: int = 50) -> bool:
    """Cek 50 frame pertama: msec monotonik naik.

    Frame pertama sah bernilai 0 (awal video). Alarm hanya bila semua
    msec = 0 (PTS tidak tersedia) atau ada nilai yang mundur.
    """
    msecs = [m for _, _, m in itertools.islice(iter_frames_timestamped(path), n)]
    monotonik = all(b >= a for a, b in zip(msecs, msecs[1:]))
    semua_nol = all(m <= 0 for m in msecs)
    print(
        f"  [VFR] {n} frame pertama: monotonik={monotonik}, "
        f"semua_msec=0={semua_nol}"
    )
    if semua_nol:
        print("  [WARNING] PTS tidak tersedia (semua msec=0) -> fallback formula frame/fps.")
        return False
    if not monotonik:
        print("  [WARNING] Timestamp mundur (bukan monotonik).")
        return False
    print(f"        contoh: {msecs[:3]} ... {msecs[-1]:.1f} ms")
    return True


def check_rotation_output(out_dir: Path, meta) -> bool:
    """Video hasil harus berdimensi tertukar bila input berotasi +/-90."""
    hasil = sorted(out_dir.glob("squat_annotated.*"))
    if not hasil:
        print("  [CEK] Video hasil tidak ditemukan untuk verifikasi dimensi.")
        return False
    vmeta = read_meta(hasil[0])
    tertukar = vmeta.width == meta.height and vmeta.height == meta.width
    print(
        f"  [CEK] Dimensi hasil {vmeta.width}x{vmeta.height} "
        f"(input {meta.width}x{meta.height}, rotation={meta.rotation}) "
        f"→ tertukar: {tertukar}"
    )
    return tertukar


def main() -> int:
    ringkasan: list[tuple[str, str, str]] = []

    for raw_path, kind in VIDEOS:
        path = Path(raw_path)
        label = f"{kind:9s} {path.name:22s}"
        if not path.exists():
            print(f"\n[SKIP] {path} tidak ditemukan.")
            ringkasan.append((label, "SKIP"))
            continue

        print(f"\n=== {path.name} ({kind}) ===")
        status = "LULUS"
        try:
            meta = read_meta(path)
            print(
                f"  [META] {meta.width}x{meta.height} @ {meta.fps:.2f} fps | "
                f"{meta.frame_count} frame | rotation={meta.rotation}"
            )

            if kind == "portrait" and meta.rotation != 0:
                print(
                    f"  [ROTASI] rotation={meta.rotation} → pipeline harus "
                    f"menukar dimensi menjadi {meta.height}x{meta.width}"
                )
            elif kind == "portrait":
                print("  [ROTASI] rotation=0 - metadata rotasi tidak ada di video ini.")

            if kind == "vfr" and not check_vfr(path):
                status = "WARNING (VFR)"

            t0 = time.time()
            out_dir = Path("output") / f"verify_{path.stem}"
            res = analyze_video(path, output_dir=str(out_dir))
            dt = time.time() - t0

            print(
                f"  [HASIL] skor={res.score:.1f} ({res.score_label}) | "
                f"reps kiri={res.left_analysis.rep_count} "
                f"kanan={res.right_analysis.rep_count} | "
                f"proses={dt:.1f}s | out={out_dir}"
            )

            if res.left_analysis.rep_count == 0 and res.right_analysis.rep_count == 0:
                status = "GAGAL (repetisi 0 kedua sisi)"

            if meta.rotation in (90, -90, 270) and not check_rotation_output(
                out_dir, meta
            ):
                status = "GAGAL (dimensi hasil tidak tertukar)"
        except Exception as e:  # noqa: BLE001 — satu video gagal tak boleh matikan lainnya
            print(f"  [GAGAL] {type(e).__name__}: {e}")
            status = f"GAGAL ({type(e).__name__})"

        ringkasan.append((label, status))

    print("\n=== RINGKASAN ===")
    for label, status in ringkasan:
        print(f"  {label} -> {status}")
    gagal = sum(1 for _, s in ringkasan if s.startswith("GAGAL"))
    return 1 if gagal else 0


if __name__ == "__main__":
    raise SystemExit(main())
