# CV Gym Catch — Evaluasi Kualitas Gerakan Gym

Prototype sistem Computer Vision untuk menganalisis kualitas gerakan *squat* (dan nantinya *push-up*) dari video menggunakan MediaPipe, **Flask**, dan HTML/CSS murni.

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

> Catatan: UI Streamlit lama (`app.py`) masih tersedia sebagai **cadangan/legacy**, bukan jalur utama lagi.

---

## 🛠️ Opsi: Menjalankan via CLI (Tanpa UI)
Jika ingin melihat log di terminal secara langsung:
```cmd
python run_squat.py
```
Hasil analisis (CSV, Grafik, Teks Ringkasan) akan tersimpan di folder `output/`.

---

## 🧪 Untuk Pengembang
- Jalankan seluruh unit test (131 test):
```cmd
pytest tests/ -q
```
- Detail teknis (keterbatasan, konvensi sudut, log keputusan) ada di [`PROJECT.md`](PROJECT.md).

---

## ⚙️ Batasan Sistem
- **Analisis 2D:** Sudut yang diukur adalah proyeksi 2D dari kamera, bukan sudut anatomis 3D.
- **Posisi Kamera:** Hasil terbaik didapat jika kamera sejajar lantai (setinggi pinggul) dan mengambil dari samping (sagittal view).
- **Video Codec:** Browser tidak bisa memutar video hasil (mp4v), sehingga UI menampilkan 3 frame sampel (Awal, Tengah, Akhir). Video utuh tetap bisa diunduh dan diputar via VLC/Media Player.
- **Skor & Feedback:** Skor kualitas, stabilitas, dan feedback teknis dihasilkan dari aturan sederhana (rule-based), bukan validasi klinis. Disclaimer ditampilkan di UI.
