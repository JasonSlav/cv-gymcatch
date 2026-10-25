# PROJECT.md — CV Gym Catch

Sistem Computer Vision untuk Evaluasi Kualitas Gerakan Gym
Prototype penelitian — bukan produk komersial.

---

## 1. Konteks Proyek

- **Jenis:** Prototype penelitian dosen Ilmu Keolahragaan
- **Durasi:** 20 hari (termasuk testing)
- **Target pengguna:** Internal laboratorium penelitian
- **Klaim:** Sistem **belum divalidasi secara ilmiah**. Hanya technical testing.

---

## 2. Tujuan

Mengevaluasi kualitas gerakan olahraga (squat, push-up) menggunakan video
tanpa sensor wearable. Output berupa metrik objektif (sudut sendi, ROM,
jumlah repetisi, konsistensi) yang dapat digunakan untuk penelitian. Sistem dirancang modular agar tidak terbatas pada satu gerakan. Squat adalah implementasi pertama untuk membuktikan validitas pipeline.

---

## 3. Scope

### ✅ Masuk Scope (MVP)
- Input: video 10–15 detik, 1 orang, seluruh tubuh terlihat
- Gerakan prioritas: **squat** → lalu **push-up**
- Deteksi pose per frame + visualisasi landmark
- Sudut sendi per frame: lutut (squat), siku (push-up)
- ROM per repetisi
- Jumlah repetisi (state machine + smoothing)
- Consistency sederhana (jika ≥3 repetisi)
- Skor kualitas, stabilitas & feedback teknis (rule-based prototype, disclaimer di UI)
- Grafik sudut vs waktu
- Ekspor CSV + video berlandmark + grafik PNG
- UI web lokal (kini **Flask + HTML**, sebelumnya Streamlit) dengan disclaimer & error handling
- Dokumentasi asumsi & keterbatasan

### ❌ Di Luar Scope (Future Work)
- **Push-up** — implementasi kedua sesuai prioritas di §3 Masuk Scope (belum dikerjakan; butuh aturan sudut siku + state machine baru)
- **Gerakan lainnya** (lunge, plank, dll.) — lewat modul gerakan terencana `src/movements/` (belum ada; pipeline & UI sudah terpisah dari logika gerakan)
- Lari / gait analysis
- Feedback teknik otomatis berbasis AI (kini baru aturan sederhana)
- Validasi klinis skor/stabilitas terhadap rubrik ahli (skor masih rule-based)
- Real-time camera, mobile native, cloud, login, database
- Validasi ilmiah terhadap penilai ahli

---

## 4. Stack Teknologi (Terkunci)

Target: Windows 10, Python 3.12.3

| Library | Versi | Fungsi |
|---|---|---|
| Python | 3.12.3 | Runtime |
| mediapipe | 1.1.1 | Pose estimation (Tasks API) |
| opencv-python | 5.0.0.93 | Baca/tulis video, visualisasi |
| numpy | 2.5.4 | Komputasi numerik |
| matplotlib | 3.11.2 | Grafik |
| streamlit | 1.40.0 | UI Web Dashboard (kini legacy/backup) |
| Flask | 3.1.3 | Web framework — server backend + sajikan UI HTML |

**Baseline:** CPU (i7-7700HQ). GPU (GTX 1050 Ti) belum dioptimasi.

### ⚠️ Catatan API MediaPipe 1.1.1
- `mp.solutions` **sudah dihapus**. Hanya `mp.tasks` yang tersedia.
- Wajib pakai `PoseLandmarker` dari Tasks API + file model `.task`.
- Model: `models/pose_landmarker_full.task` (9.4 MB)

---

## 5. Struktur Folder

```text
C:\Projects\cv\gymcatch\
├─ .venv\                      # virtual environment
├─ requirements.txt            # dependensi terkunci
├─ PROJECT.md                  # dokumen ini
├─ README.md                   # panduan instalasi & penggunaan (penguji)
├─ app.py                      # Streamlit UI — [LEGACY/BACKUP] (cadangan, port 8501)
├─ app_flask.py                # Backend Flask — entry point BARU (port 5000)
├─ run_squat.py                # CLI wrapper tipis di atas src/pipeline.py
│
├─ templates\
│  └─ index.html               # UI murni HTML/CSS/JS (i18n ID/EN, sesuai mockup)
│
├─ static\
│  ├─ logo.png                 # logo navbar
│  ├─ fik.png                  # logo FIK (footer)
│  └─ bg_gym_small.jpg         # background hero
│
├─ src\                        # kode modular
│  ├─ geometry.py              # sudut, normalisasi, interpolasi (murni)
│  ├─ video_io.py              # baca/tulis video, validasi input
│  ├─ pose_estimator.py        # MediaPipe Tasks API wrapper + angle_from_landmarks
│  ├─ metrics.py               # ROM, rep counting, consistency
│  ├─ visualize.py             # gambar landmark, grafik
│  ├─ report.py                # pilih seri, CSV sudut, format summary
│  └─ pipeline.py              # orkestrasi end-to-end (analyze_video → AnalysisResult)
│
├─ tests\                      # unit test (131 test)
│  ├─ test_geometry.py
│  ├─ test_metrics.py
│  ├─ test_video_io.py
│  ├─ test_pose_estimator.py
│  ├─ test_visualize.py
│  ├─ test_report.py
│  ├─ test_pipeline.py
│  └─ test_app.py
│
├─ models\
│  └─ pose_landmarker_full.task
│
├─ data\                       # video contoh (untuk demo)
│  └─ squat_sample.mp4
│
├─ output\                     # hasil analisis
│
└─ legacy\
   └─ poc_squat.py             # PoC awal (monolitik) — referensi historis
```

---

## 6. Konvensi Teknis

### 6.1 Sudut Sendi
- **Definisi:** Sudut di titik B, dibentuk vektor B→A dan B→C.
- **Domain:** 0°–180°.
- **Proyeksi:** **2D** (dari frame kamera), **bukan** sudut anatomis 3D.
- **Ruang perhitungan:** sudut dihitung dalam **koordinat piksel** (`x * width, y * height`), **bukan** ruang ternormalisasi [0, 1]. Alasan: ruang ternormalisasi anisotropik ketika aspect ratio ≠ 1, sehingga sudut berbeda dari proyeksi 2D frame yang sebenarnya. Helper: `pose_estimator.angle_from_landmarks()`.
- **Keterbatasan:** Dipengaruhi perspektif, posisi kamera, oklusi.

Contoh:
```text
Sudut lutut = sudut di titik KNEE, antara HIP–KNEE–ANKLE
Landmark MediaPipe: 23 (L hip), 25 (L knee), 27 (L ankle)
                    24 (R hip), 26 (R knee), 28 (R ankle)
```

### 6.2 Indeks Landmark MediaPipe (33 titik)
| Sendi | Kiri | Kanan |
|---|---|---|
| Shoulder | 11 | 12 |
| Elbow | 13 | 14 |
| Wrist | 15 | 16 |
| Hip | 23 | 24 |
| Knee | 25 | 26 |
| Ankle | 27 | 28 |

### 6.3 Ambang Visibility
- Nilai awal: **0.5** (dapat dikalibrasi)
- Landmark dengan visibility < 0.5 → ditandai invalid, tidak dihitung
- Frame dengan landmark invalid → sudut diisi kosong (bukan 0)

### 6.4 ROM (Range of Motion)
- **Definisi:** `max(sudut) − min(sudut)` per repetisi
- Diukur pada sisi tubuh yang valid
- **Bukan** pengukuran klinis tervalidasi

### 6.5 Konsistensi
- **Definisi:** `1 − (RMSE antar-repetisi / ROM rata-rata)`
- Hanya dihitung jika **≥3 repetisi** terdeteksi
- Interpolasi tiap repetisi ke 100 titik sebelum RMSE

### 6.6 Sisi Tubuh
- Track **kedua sisi** (kiri & kanan)
- Tampilkan yang valid; kalau hanya satu, tampilkan satu
- **Tidak** memaksa hitung sisi yang visibility-nya rendah

---

## 7. Parameter yang Dihasilkan

| Parameter | Status | Catatan |
|---|---|---|
| Sudut sendi per frame | ✅ Wajib | Inti PoC |
| ROM per repetisi | ✅ Wajib | |
| Jumlah repetisi | ✅ Wajib | State machine |
| Consistency | ⚠️ Opsional | Jika ≥3 repetisi |
| Stability | ⚠️ Proxy | Goyangan pinggul (px), rule-based |
| Skor kualitas 0–100 | ⚠️ Rule-based | Aturan sederhana, bukan validasi klinis |
| Feedback teknis | ⚠️ Rule-based | Saran otomatis dari ambang metrik |

---

## 8. Status Progres

### ✅ Selesai
- [x] Setup environment (Python 3.12.3, Windows)
- [x] Install dependensi (mediapipe, opencv, numpy, matplotlib, streamlit)
- [x] `requirements.txt` terkunci
- [x] Unduh model `pose_landmarker_full.task`
- [x] PoC squat: deteksi + sudut + visualisasi + CSV + grafik (3 repetisi terdeteksi)
- [x] Modularisasi `src/` (geometry, video_io, pose_estimator, metrics, visualize, report, pipeline) — 127/127 test passed
- [x] Pipeline end-to-end terbukti konsisten (selisih 0.000000° antar run)
- [x] Streamlit UI + fallback 3 sampel frame (mengatasi codec video yang tidak didukung browser) + tombol download
- [x] Dokumentasi akhir: README.md (panduan penguji) + PROJECT.md (asumsi, keterbatasan, log keputusan)
- [x] Migrasi Frontend dari Streamlit ke Flask + HTML/CSS murni (UI 100% sesuai mockup, i18n ID/EN, integrasi API)

### 📋 Berikutnya
- [ ] Testing dengan video nyata kondisi buruk (goyang, oklusi, durasi ekstrem)
- [ ] Uji coba push-up (Future Work)

---

## 9. Panduan Pengambilan Video (untuk Pengguna)

Ditampilkan sebagai panduan di UI (halaman Flask `index.html` & app.py legacy):

> ⚠️ **Panduan Perekaman Optimal**
> - Durasi 10–15 detik, seluruh tubuh terlihat dalam frame
> - Kamera statis (tripod), 2–3 m dari subjek, setinggi pinggul
> - Sudut pengambilan 60°–90° terhadap bidang gerak
> - Untuk squat/push-up: **dari samping** lebih baik
> - Pencahayaan cukup, latar kontras dengan subjek
> - Satu orang dalam frame, tanpa oklusi
>
> Video di luar kondisi ini tetap diproses, tetapi akurasi
> sudut dan deteksi landmark dapat menurun.

---

## 10. Keterbatasan & Asumsi

### Keterbatasan
1. Sudut yang diukur adalah **proyeksi 2D**, bukan sudut anatomis 3D.
2. Akurasi dipengaruhi perspektif, posisi kamera, oklusi, dan pencahayaan.
3. Sistem **belum divalidasi** terhadap penilaian ahli atau goniometer.
4. Klaim akurasi klinis **tidak didukung**.
5. ROM yang dihasilkan bukan pengukuran klinis tervalidasi.
6. Metrik consistency adalah **proxy visual**, bukan ukuran universal.

### Asumsi
1. Video memenuhi protokol pengambilan (side view, 1 orang, full body).
2. Landmark dengan visibility ≥ 0.5 dianggap dapat dipercaya.
3. Repetisi dideteksi dari perubahan sudut, bukan dari ground truth.
4. Threshold state machine dapat dikalibrasi ulang per video.

### Yang Belum Tersedia
- Rubrik penilaian ahli
- Data pembanding (video dengan skor ahli)
- Protokol validasi & reliabilitas
- Sampel subjek penelitian

**Konsekuensi:** Klaim validitas/reliabilitas **belum dapat dinyatakan**.

---

## 11. Rancangan Evaluasi (Draft)

### Technical Testing
- [x] Aplikasi berjalan di Windows lokal (Streamlit health 200; kini Flask `GET /` 200)
- [x] Video valid diproses tanpa error
- [ ] Video rusak ditolak dengan pesan jelas (unit test lolos, UI manual belum diuji)
- [x] Sudut konsisten antar-run (test–retest internal: 2 run, selisih CSV 0.000000°)
- [x] Waktu proses tercatat (~12–30 detik untuk video 11.8 detik)

### Validasi Ilmiah (menunggu data)
- [ ] Bandingkan sudut sistem vs goniometer
- [ ] Bandingkan sudut sistem vs penilaian ahli
- [ ] Reliabilitas inter-rater (2 ahli, video sama)
- [ ] Reliabilitas test–retest (subjek sama, 2 sesi)
- [ ] Uji statistik: ICC, Bland–Altman, korelasi

---

## 12. Prinsip Pengembangan

1. **Bekerja bertahap**, tidak membangun semua fitur sekaligus.
2. **Modularitas ketat**: Satu file = satu tanggung jawab (UI, Pipeline, Geometri, dll).
3. **Selalu jalankan test** setelah implementasi (131 unit test).
4. **Jujur pada hasil**: Jangan klaim fitur berjalan jika belum diuji dengan data nyata.
5. **Jangan tambah dependensi** di luar yang terkunci tanpa persetujuan.
6. **Laporkan error/gagal** apa adanya, jangan di-*bypass*.

---

## 13. Log Keputusan (Technical)

| Tanggal | Keputusan | Alasan |
|---|---|---|
| 2026-10-15 | Pakai video 5–10 detik, bukan foto | Foto tidak bisa hitung ROM/repetisi/consistency |
| 2026-10-15 | Pakai MediaPipe Tasks API | `mp.solutions` dihapus di MediaPipe 1.1.1 |
| 2026-10-16 | Rep counting pakai state machine eksplisit dengan hysteresis | Lebih stabil dari peak detection pada sinyal ber-noise |
| 2026-10-16 | Sudut dihitung di ruang piksel, bukan ruang ternormalisasi | Ruang ternormalisasi anisotropik (beda ~10°/frame pada video 16:9) |
| 2026-10-17 | `streamlit` ditambahkan ke requirements | Dibutuhkan untuk UI Web Dashboard |
| 2026-10-17 | Fallback 3 sampel frame JPG menggantikan `st.video` | Browser modern tidak mendukung codec mp4v secara native |
| 2026-10-23 | Menambahkan skor kualitas (0–100), stabilitas (%) & feedback teknis **rule-based** + disclaimer di UI | Permintaan mockup UI klien; aturan matematika transparan — bukan AI maupun validasi klinis |
| 2026-10-23 | Reset total (hasil + file uploader) via pola flag `_clear_pending`; anti-stale: hasil disembunyikan + hint saat file berubah | State widget Streamlit hanya boleh dihapus sebelum widget terinstansiasi; signature (nama+ukuran file) deteksi file berganti tanpa menghapus data diam-diam |
| 2026-10-23 | Tombol Reset `disabled` dihitung dari (ada hasil **atau** ada file), bukan dari hasil saja | `analysis_result` baru diset setelah tombol dirender pada run yang sama → Reset lama tetap abu-abu sampai run berikutnya; versi ini aktif sejak file ter-upload sehingga selalu bisa di-klik setelah analisis |
| 2026-10-23 | Tombol 🔄 Reset custom **dihapus**; hapus file = X bawaan uploader, hasil disembunyikan otomatis saat file berubah (anti-stale) | Duplikasi kontrol membingungkan; mesin flag Reset memunculkan bug disabled-timing — fewer stateful widgets = fewer Streamlit bugs |
| 2026-10-23 | Durasi panduan diubah 5–10 → 10–15 detik | Permintaan klien; video lebih panjang memberi lebih banyak frame per repetisi; video demo 11.8s kini sesuai panduan |
| 2026-10-25 | Migrasi UI dari Streamlit ke Flask + HTML murni | Streamlit terlalu terbatas untuk mencapai desain mockup 100%; Flask memisahkan Frontend (HTML/JS) dan Backend (Python/AI) secara bersih. |

---

## 14. Konfigurasi & Roadmap Gerakan

Catatan: arsitektur yang direncanakan di `src/movements/` memungkinkan
penambahan file baru untuk gerakan lain tanpa menyentuh pipeline utama.

- Aturan squat kini berada di `src/metrics.py` (state machine + ambang sudut).
- Gerakan baru direncanakan berupa file aturan sudut & state machine per gerakan di `src/movements/` + rekomendasi umpan balik per gerakan.
- Didukung saat ini: **Squat** | Pengembangan: Push-up → Lunge → Plank.
- Validasi ilmiah: perbandingan hasil AI dengan rubrik ahli/instruktur.

---

*Terakhir diperbarui: 2026-10-25*
