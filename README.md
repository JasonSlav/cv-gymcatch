# CV Gym Catch — Evaluasi Kualitas Gerakan Gym

![Tests](https://github.com/JasonSlav/cv-gymcatch/actions/workflows/python-tests.yml/badge.svg)

Prototype sistem Computer Vision untuk menganalisis kualitas gerakan olahraga. Saat ini sistem telah mengimplementasikan analisis gerakan **squat**, dengan arsitektur modular yang siap dikembangkan untuk gerakan lain (seperti *push-up*, *lunge*, dll) di masa depan. Dibangun menggunakan MediaPipe, **Flask**, dan HTML/CSS murni.

> ⚠️ **Disclaimer:** Sistem ini adalah prototipe penelitian. Belum divalidasi secara klinis dan tidak boleh digunakan sebagai pengganti penilaian ahli/instruktur.

---

## 📋 Prasyarat
- **Python 3.12.3** (Sangat disarankan versi ini agar tidak bentrok).
- **Git** (untuk clone repositori).
- Sistem Operasi: Windows 10 / 11.

---

## 🚀 Cara Instalasi & Menjalankan (Untuk Penguji)

Buka **CMD** (Command Prompt), lalu ikuti langkah berikut:

### 1. Clone Repositori & Masuk ke Folder
```cmd
git clone https://github.com/JasonSlav/cv-gymcatch.git
cd cv-gymcatch
```

### 2. Buat & Aktifkan Virtual Environment
```cmd
python -m venv .venv
.venv\Scripts\activate
```
(Pastikan muncul `(.venv)` di awal baris CMD Anda)

### 3. Install Dependensi
```cmd
pip install -r requirements.txt
```
( Termasuk **Flask** — web server untuk UI utama. )

### 4. Unduh Model AI (Pose Landmarker)
Model tidak dimasukkan ke dalam GitHub karena berukuran ~9 MB. Jalankan perintah ini di CMD untuk mengunduhnya:
```cmd
mkdir models
curl -L -o models\pose_landmarker_full.task "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/latest/pose_landmarker_full.task"
```

### 5. Siapkan Video Uji
Buat folder `data` di dalam proyek, lalu masukkan video squat Anda ke dalamnya dengan nama `squat_sample.mp4`.
(Pastikan video memenuhi panduan: durasi 10–15 detik, kamera statis dari samping, seluruh badan terlihat).

### 6. Jalankan Aplikasi
```cmd
python app_flask.py
```
Buka browser di **http://localhost:5000** — dari HP/LAN gunakan `http://<ip-laptop>:5000`.

> Catatan keamanan: untuk deploy di server, **wajib** mengatur variabel lingkungan `SECRET_KEY` (lihat [`.env.example`](.env.example)).

> Catatan: UI Streamlit lama (`legacy/app_streamlit.py`) masih tersedia sebagai **cadangan/legacy**, bukan jalur utama lagi.

---

## 🛠️ Opsi: Menjalankan via CLI (Tanpa UI)
Jika ingin melihat log di terminal secara langsung:
```cmd
python run_squat.py
```
Hasil analisis (CSV, Grafik, Teks Ringkasan) akan tersimpan di folder `output/`.

---

## 🔌 API Contract
`POST /analyze` (multipart form: `video`, `movement_type`, `job_id`; wajib login) mengembalikan JSON:
```json
{
  "score": 77.8,
  "score_label": "Cukup",
  "reps": 3,
  "rom": 130.8,
  "stability": 41,
  "consistency": 0.915,
  "duration_sec": 12.5,
  "side": "left",
  "feedbacks": ["Kedalaman squat kurang. Usahakan turun lebih dalam."],
  "process_sec": 12.8,
  "samples": ["/output/req_xxx/sample_1.jpg", "/output/req_xxx/sample_2.jpg", "/output/req_xxx/sample_3.jpg"],
  "plot": "/output/req_xxx/knee_angle.png",
  "video_url": "/output/req_xxx/squat_annotated.webm",
  "is_browser_playable": true,
  "angle_data": {"mode": "both", "left": [170.2, "..."], "right": [169.8, "..."]}
}
```
- `feedbacks` berisi pesan rule-based (dari `src/movements/`); kosong bila gerakan sudah baik.
- `angle_data` = deret sudut per frame untuk grafik interaktif.
- Error: 400 (file tidak valid), 422 (gerakan/pipeline gagal), 500 (kesalahan tak terduga).

---

## 🧪 Untuk Pengembang
- Install dependensi development (test):
```cmd
pip install -r requirements-dev.txt
```
- Jalankan seluruh unit test (126 test, folder `tests/`):
```cmd
pytest tests/ -q
```
- Test Streamlit legacy (opsional): `pytest legacy/ -q`.
- Detail teknis (keterbatasan, konvensi sudut, log keputusan) ada di [`PROJECT.md`](PROJECT.md).

---

## 🚀 Roadmap & Skalabilitas
Sistem ini dirancang secara modular. Logika utama (deteksi pose, perhitungan sudut, state machine repetisi) terpisah dari antarmuka (UI).
- **Gerakan yang Didukung Saat Ini:** Squat.
- **Pengembangan Selanjutnya:** Push-up, Lunge, Plank (memerlukan penyesuaian aturan sudut dan state machine — rencana struktur: `src/movements/`, belum ada di repo).
- **Validasi Ilmiah:** Perbandingan hasil AI dengan penilaian ahli/instruktur (rubrik) untuk menguji akurasi klinis.

---

## ⚙️ Batasan Sistem
- **Analisis 2D:** Sudut yang diukur adalah proyeksi 2D dari kamera, bukan sudut anatomis 3D.
- **Posisi Kamera:** Hasil terbaik didapat jika kamera sejajar lantai (setinggi pinggul) dan mengambil dari samping (sagittal view).
- **Video Codec:** Browser tidak bisa memutar video hasil (mp4v), sehingga UI menampilkan 3 frame sampel (Awal, Tengah, Akhir). Video utuh tetap bisa diunduh dan diputar via VLC/Media Player.
- **Skor & Feedback:** Skor kualitas, stabilitas, dan feedback teknis dihasilkan dari aturan sederhana (rule-based), bukan validasi klinis. Disclaimer ditampilkan di UI.
