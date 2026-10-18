"""
PoC: Deteksi pose + sudut lutut pada video squat.
MediaPipe 1.1.1 Tasks API + OpenCV.
"""

import csv
from pathlib import Path

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import numpy as np
import matplotlib
matplotlib.use("Agg")  # non-interactive backend untuk menyimpan PNG
import matplotlib.pyplot as plt

# --- Konfigurasi ---
VIDEO_PATH = "data/squat_sample.mp4"
MODEL_PATH = "models/pose_landmarker_full.task"
OUT_DIR = Path("output")
OUT_DIR.mkdir(exist_ok=True)

# Indeks landmark MediaPipe Pose (33 titik)
LEFT_HIP, LEFT_KNEE, LEFT_ANKLE = 23, 25, 27
RIGHT_HIP, RIGHT_KNEE, RIGHT_ANKLE = 24, 26, 28
MIN_VISIBILITY = 0.5

# Koneksi skeleton standar MediaPipe Pose (33 landmark)
POSE_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 7), (0, 4), (4, 5), (5, 6), (6, 8),
    (9, 10),
    (11, 12), (11, 13), (13, 15), (15, 17), (15, 19), (15, 21), (17, 19),
    (12, 14), (14, 16), (16, 18), (16, 20), (16, 22), (18, 20),
    (11, 23), (12, 24), (23, 24),
    (23, 25), (24, 26), (25, 27), (26, 28), (27, 29), (28, 30),
    (29, 31), (30, 32), (27, 31), (28, 32),
]


def calculate_angle(a, b, c):
    """Sudut (derajat) di titik b, dibentuk vektor b->a dan b->c."""
    a = np.array(a[:2], dtype=float)
    b = np.array(b[:2], dtype=float)
    c = np.array(c[:2], dtype=float)
    ba = a - b
    bc = c - b
    denom = (np.linalg.norm(ba) * np.linalg.norm(bc)) + 1e-9
    cosine = np.clip(np.dot(ba, bc) / denom, -1.0, 1.0)
    return float(np.degrees(np.arccos(cosine)))


def draw_pose(frame, landmarks, w, h):
    """Gambar landmark + koneksi manual dengan OpenCV."""
    pts = [(int(lm.x * w), int(lm.y * h)) for lm in landmarks]
    # gambar garis
    for a, b in POSE_CONNECTIONS:
        if a < len(pts) and b < len(pts):
            cv2.line(frame, pts[a], pts[b], (255, 255, 255), 2)
    # gambar titik
    for i, (x, y) in enumerate(pts):
        # highlight landmark yang kita pakai (hip, knee, ankle)
        if i in (LEFT_HIP, LEFT_KNEE, LEFT_ANKLE):
            color = (0, 255, 0)  # hijau = kiri
            r = 6
        elif i in (RIGHT_HIP, RIGHT_KNEE, RIGHT_ANKLE):
            color = (0, 128, 255)  # oranye = kanan
            r = 6
        else:
            color = (200, 200, 200)
            r = 3
        cv2.circle(frame, (x, y), r, color, -1)


def main():
    if not Path(VIDEO_PATH).exists():
        raise FileNotFoundError(f"Video tidak ditemukan: {VIDEO_PATH}")
    if not Path(MODEL_PATH).exists():
        raise FileNotFoundError(f"Model tidak ditemukan: {MODEL_PATH}")

    base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
    options = vision.PoseLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.VIDEO,
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    detector = vision.PoseLandmarker.create_from_options(options)

    cap = cv2.VideoCapture(VIDEO_PATH)
    if not cap.isOpened():
        raise RuntimeError("Gagal membuka video.")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"[INFO] Video: {w}x{h}, {fps:.2f} fps, ~{n_frames} frame")

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(OUT_DIR / "squat_annotated.mp4"), fourcc, fps, (w, h))

    rows = []
    frame_idx = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        timestamp_ms = int((frame_idx / fps) * 1000)
        result = detector.detect_for_video(mp_image, timestamp_ms)

        left_angle = right_angle = None
        left_ok = right_ok = False

        if result.pose_landmarks and len(result.pose_landmarks) > 0:
            lm = result.pose_landmarks[0]

            def get(idx):
                p = lm[idx]
                return (p.x * w, p.y * h, p.visibility)

            lh, lk, la = get(LEFT_HIP), get(LEFT_KNEE), get(LEFT_ANKLE)
            rh, rk, ra = get(RIGHT_HIP), get(RIGHT_KNEE), get(RIGHT_ANKLE)

            if min(lh[2], lk[2], la[2]) >= MIN_VISIBILITY:
                left_angle = calculate_angle(lh, lk, la)
                left_ok = True
            if min(rh[2], rk[2], ra[2]) >= MIN_VISIBILITY:
                right_angle = calculate_angle(rh, rk, ra)
                right_ok = True

            draw_pose(frame, lm, w, h)

            if left_ok:
                cv2.putText(frame, f"L knee: {left_angle:.1f}", (20, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
            if right_ok:
                cv2.putText(frame, f"R knee: {right_angle:.1f}", (20, 80),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 128, 255), 2)

        writer.write(frame)
        rows.append((frame_idx, left_angle, right_angle, left_ok, right_ok))
        frame_idx += 1

    cap.release()
    writer.release()
    detector.close()

    # CSV
    csv_path = OUT_DIR / "knee_angle.csv"
    with open(csv_path, "w", newline="") as f:
        wtr = csv.writer(f)
        wtr.writerow(["frame", "left_knee_angle_deg", "right_knee_angle_deg",
                      "left_valid", "right_valid"])
        for r in rows:
            wtr.writerow([
                r[0],
                "" if r[1] is None else f"{r[1]:.3f}",
                "" if r[2] is None else f"{r[2]:.3f}",
                int(r[3]), int(r[4]),
            ])

    # Grafik
    frames = [r[0] for r in rows]
    left_series = [r[1] if r[3] else np.nan for r in rows]
    right_series = [r[2] if r[4] else np.nan for r in rows]

    plt.figure(figsize=(10, 4))
    plt.plot(frames, left_series, label="Left knee", color="green")
    plt.plot(frames, right_series, label="Right knee", color="orange")
    plt.xlabel("Frame")
    plt.ylabel("Sudut lutut (derajat)")
    plt.title("Sudut lutut per frame — Squat (PoC)")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "knee_angle.png", dpi=120)
    plt.close()

    valid_left = [r[1] for r in rows if r[3]]
    valid_right = [r[2] for r in rows if r[4]]
    print(f"[DONE] Frame diproses : {frame_idx}")
    print(f"[DONE] Frame L valid  : {len(valid_left)}/{frame_idx}")
    print(f"[DONE] Frame R valid  : {len(valid_right)}/{frame_idx}")
    if valid_left:
        print(f"[DONE] ROM L (min-max): {min(valid_left):.1f} - {max(valid_left):.1f} derajat")
    if valid_right:
        print(f"[DONE] ROM R (min-max): {min(valid_right):.1f} - {max(valid_right):.1f} derajat")
    print(f"[OUT ] {OUT_DIR / 'squat_annotated.mp4'}")
    print(f"[OUT ] {csv_path}")
    print(f"[OUT ] {OUT_DIR / 'knee_angle.png'}")


if __name__ == "__main__":
    main()