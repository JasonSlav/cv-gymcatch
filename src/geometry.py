"""
Modul geometri murni untuk analisis pose.

Semua fungsi di sini:
- Hanya bergantung pada NumPy.
- Tidak menyentuh MediaPipe, OpenCV, atau I/O.
- Menggunakan proyeksi 2D (x, y) — nilai z diabaikan jika ada.

Konvensi sudut:
- Sudut diukur di titik vertex (b), dibentuk oleh vektor b→a dan b→c.
- Domain: 0°–180°.
- Sudut 180° = garis lurus, 0° = titik berimpit.
"""

from __future__ import annotations

import numpy as np

# Toleransi untuk deteksi titik degenerate (dua titik berimpit)
EPS = 1e-9


def _to_2d(point) -> np.ndarray:
    """Konversi titik (x, y) atau (x, y, z) menjadi array 2D [x, y]."""
    arr = np.asarray(point, dtype=float).flatten()
    if arr.size < 2:
        raise ValueError(f"Titik harus punya minimal 2 koordinat, dapat {arr.size}")
    return arr[:2]


def point_distance(a, b) -> float:
    """Jarak Euclidean 2D antara dua titik."""
    pa = _to_2d(a)
    pb = _to_2d(b)
    return float(np.linalg.norm(pa - pb))


def calculate_angle(a, b, c) -> float:
    """
    Sudut (derajat) di titik b, dibentuk oleh vektor b→a dan b→c.

    Parameter
    ---------
    a, b, c : tuple/list/array
        Koordinat titik. Format (x, y) atau (x, y, z). Nilai z diabaikan.

    Returns
    -------
    float
        Sudut dalam derajat, domain [0, 180].

    Raises
    ------
    ValueError
        Jika salah satu titik tidak punya minimal 2 koordinat.

    Catatan
    -------
    - Jika b berimpit dengan a atau c (jarak < EPS), sudut tidak terdefinisi.
      Dalam kasus ini, fungsi mengembalikan 180.0 sebagai fallback aman
      (garis lurus) dan pemanggil sebaiknya memfilter frame seperti ini
      berdasarkan visibility landmark.
    - Hasil di-clip ke [0, 180] untuk mengatasi error numerik.
    """
    pa = _to_2d(a)
    pb = _to_2d(b)
    pc = _to_2d(c)

    ba = pa - pb
    bc = pc - pb

    norm_ba = np.linalg.norm(ba)
    norm_bc = np.linalg.norm(bc)

    if norm_ba < EPS or norm_bc < EPS:
        return 180.0

    cosine = float(np.dot(ba, bc) / (norm_ba * norm_bc))
    cosine = max(-1.0, min(1.0, cosine))
    angle = float(np.degrees(np.arccos(cosine)))
    return angle


def midpoint(a, b):
    """Titik tengah 2D antara dua titik."""
    pa = _to_2d(a)
    pb = _to_2d(b)
    return (pa + pb) / 2.0


def normalize_to_origin(point, origin):
    """Geser titik relatif terhadap origin. Berguna untuk normalisasi posisi."""
    return _to_2d(point) - _to_2d(origin)


def angle_from_vertical(a, b) -> float:
    """
    Sudut (derajat) antara vektor a→b dan sumbu vertikal (0, -1).

    Konvensi: sumbu Y mengarah ke bawah (konvensi gambar), sehingga
    vektor (0, -1) menunjuk ke atas. Berguna untuk mengukur
    kemiringan torso atau alignment postural.

    Returns
    -------
    float
        Sudut dalam derajat, domain [0, 180].
    """
    pa = _to_2d(a)
    pb = _to_2d(b)
    v = pb - pa
    norm_v = np.linalg.norm(v)
    if norm_v < EPS:
        return 0.0
    vertical = np.array([0.0, -1.0])
    cosine = float(np.dot(v, vertical) / norm_v)
    cosine = max(-1.0, min(1.0, cosine))
    return float(np.degrees(np.arccos(cosine)))
