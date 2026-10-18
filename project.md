# PROJECT.md — CV Gym Catch

Sistem Computer Vision untuk Evaluasi Kualitas Gerakan Gym
Prototype penelitian — bukan produk komersial.

---

## 1. Konteks Proyek

- **Jenis:** Prototype penelitian dosen Ilmu Keolahragaan
- **Nilai jasa:** Rp 2.500.000
- **Durasi:** 20 hari (termasuk testing)
- **Target pengguna:** Internal laboratorium penelitian
- **Klaim:** Sistem **belum divalidasi secara ilmiah**. Hanya technical testing.

---

## 2. Tujuan

Mengevaluasi kualitas gerakan olahraga (squat, push-up) menggunakan video
tanpa sensor wearable. Output berupa metrik objektif (sudut sendi, ROM,
jumlah repetisi, konsistensi) yang dapat digunakan untuk penelitian.

---

## 3. Scope

### ✅ Masuk Scope (MVP)
- Input: video 5–10 detik, 1 orang, seluruh tubuh terlihat
- Gerakan prioritas: **squat** → lalu **push-up**
- Deteksi pose per frame + visualisasi landmark
- Sudut sendi per frame: lutut (squat), siku (push-up)
- ROM per repetisi
- Jumlah repetisi (state machine + smoothing)
- Consistency sederhana (jika ≥3 repetisi)
- Grafik sudut vs waktu
- Ekspor CSV + video berlandmark + grafik PNG
- UI Streamlit lokal dengan disclaimer & error handling
- README + dokumentasi asumsi & keterbatasan

### ❌ Di Luar Scope (Future Work)
- Lari / gait analysis
- Skor kualitas 0–100 (butuh rubrik ahli)
- Feedback teknik otomatis
- Stability (definisi operasional belum disepakati)
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
| opencv-contrib-python | 5.0.0.93 | Dependensi mediapipe |
| numpy | 2.5.4 | Komputasi numerik |
| matplotlib | 3.11.2 | Grafik |

**Baseline:** CPU (i7-7700HQ). GPU (GTX 1050 Ti) belum dioptimasi.

### ⚠️ Catatan API MediaPipe 1.1.1
- `mp.solutions` **sudah dihapus**. Hanya `mp.tasks` yang tersedia.
- Wajib pakai `PoseLandmarker` dari Tasks API + file model `.task`.
- Model: `models/pose_landmarker_full.task` (9.4 MB)

---

## 5. Struktur Folder

```
C:\Projects\cv\gymcatch\
├─ .venv\                      # virtual environment
├─ requirements.txt            # dependensi terkunci
├─ PROJECT.md                  # dokumen ini
├─ README.md                   # panduan instalasi & penggunaan
├─ prompts.md                  # catatan prompt opencode per sesi (opsional)
│
├─ app.py                      # Streamlit UI tipis (entry point, logika di pipeline.py)
├─ run_squat.py                # CLI wrapper tipis di atas src/pipeline.py
│
├─ src\                        # kode modular
│  ├─ __init__.py
│  ├─ geometry.py              # sudut, normalisasi, interpolasi (murni)
│  ├─ video_io.py              # baca/tulis video, validasi input
│  ├─ pose_estimator.py        # MediaPipe Tasks API wrapper + angle_from_landmarks
│  ├─ metrics.py               # ROM, rep counting, consistency
│  ├─ visualize.py             # gambar landmark, grafik
│  ├─ report.py                # pilih seri, CSV sudut, format summary
│  ├─ pipeline.py              # orkestrasi end-to-end (analyze_video → AnalysisResult)
│  └─ movements\
│     ├─ __init__.py
│     ├─ base.py               # interface gerakan
│     ├─ squat.py              # konfigurasi squat
│     └─ pushup.py             # konfigurasi push-up
│
├─ tests\                      # unit test (127 test)
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
├─ output\                     # hasil analisis (run_squat.py)
│  ├─ squat_annotated.mp4
│  ├─ knee_angle.csv
│  ├─ knee_angle.png
│  └─ summary.txt
│
├─ legacy\
│  └─ poc_squat.py              # PoC awal (monolitik) — diarsipkan, referensi historis
└─ output_poc\                 # backup output PoC awal (baseline perbandingan)
```

---

## 6. Konvensi Teknis

### 6.1 Sudut Sendi
- **Definisi:** Sudut di titik B, dibentuk vektor B→A dan B→C.
- **Domain:** 0°–180°.
- **Proyeksi:** **2D** (dari frame kamera), **bukan** sudut anatomis 3D.
- **Ruang perhitungan:** sudut dihitung dalam **koordinat piksel** (`x * width, y * height`), **bukan** ruang ternormalisasi [0, 1]. Alasan: ruang ternormalisasi anisotropik ketika aspect ratio ≠ 1, sehingga sudut berbeda dari proyeksi 2D frame yang sebenarnya (terbukti: selisih ~10°/frame pada video 16:9). Helper: `pose_estimator.angle_from_landmarks()`.
- **Keterbatasan:** Dipengaruhi perspektif, posisi kamera, oklusi.

Contoh:
```
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
| Stability | ❌ Tidak | Definisi belum disepakati |
| Skor kualitas 0–100 | ❌ Tidak | Butuh rubrik ahli |

---

## 8. Status Progres

### ✅ Selesai
- [x] Setup venv (Python 3.12.3, Windows)
- [x] Install dependensi (mediapipe 1.1.1, opencv 5.0, numpy 2.5, matplotlib 3.11)
- [x] `requirements.txt` terkunci
- [x] Unduh model `pose_landmarker_full.task`
- [x] Verifikasi API: `mp.solutions` tidak ada, `mp.tasks` tersedia
- [x] PoC `poc_squat.py`: deteksi + sudut + visualisasi + CSV + grafik
- [x] Uji dengan video squat 354 frame → 3 repetisi terdeteksi
- [x] ROM kiri: 44.4° – 179.8° (masuk akal)
- [x] Sesi 1: `src/geometry.py` + `tests/test_geometry.py` (14/14 passed, pytest 9.1.1)
- [x] Sesi 2: `src/video_io.py` + `tests/test_video_io.py` (17/17 passed)
- [x] Sesi 3: `src/pose_estimator.py` + `tests/test_pose_estimator.py` (18/18 passed)
- [x] Sesi 4: `src/metrics.py` + `tests/test_metrics.py` (28/28 passed — ROM, rep counting, smoothing, consistency)
- [x] Sesi 5: `src/visualize.py` + `tests/test_visualize.py` (19/19 passed — skeleton frame, label, grafik + rep annotation)
- [x] Sesi 6: `src/report.py` + `tests/test_report.py` (16/16) + `run_squat.py` pipeline end-to-end — 116/116 passed total
- [x] `run_squat.py` terverifikasi vs PoC: CSV **identik (selisih 0.000000°)**, 3 rep, ROM 135.38°, consistency 0.920, proses 23.6s
- [x] Patch `angle_from_landmarks()` (ruang piksel) + 4 test regresi — konsisten dengan §6.1
- [x] Modularisasi bertahap (pakai opencode, 1 sesi = 1 modul) — 6/6 sesi selesai
- [x] Sesi 7a–7b: `src/pipeline.py` + `tests/test_pipeline.py` (6/6) + `run_squat.py` jadi CLI wrapper tipis — 122/122 passed
- [x] `analyze_video()` → `AnalysisResult`; CSV terverifikasi identik vs baseline `output_poc/` (selisih 0.000000°)
- [x] Sesi 7c: `app.py` + `tests/test_app.py` (5/5) + `streamlit==1.40.0` (persetujuan eksplisit, full re-freeze requirements) — 127/127 passed
- [x] UI smoke test: server hidup (health 200), landing page terekam di `streamlit_landing.png`
- [x] Temuan user: video annotated (`mp4v`) tampil **hitam** di browser → fallback: 3 sampel frame JPG (`extract_sample_frames()` di `pipeline.py`) + tombol download video MP4 — 127/127 passed, `sample_mid.jpg` terverifikasi (posisi bottom berlandmark)

### 📋 Berikutnya
- [ ] Uji ulang upload di browser (`localhost:8501`) — konfirmasi 3 sampel frame tampil normal
- [ ] Testing dengan video nyata (baik & buruk)
- [ ] Dokumentasi akhir (README, asumsi, keterbatasan)

---

## 9. Rencana Pengerjaan (20 Hari)

| Hari | Fokus | Status |
|---|---|---|
| 1 | Setup venv + dependensi | ✅ |
| 2 | PoC squat | ✅ |
| 3 | Modularisasi: geometry ✅ + video_io ✅ | ✅ |
| 4 | Modularisasi: pose_estimator | ✅ |
| 5 | Modularisasi: metrics (ROM) | ✅ |
| 6 | Modularisasi: visualize ✅ + refactor PoC ✅ (run_squat.py) | ✅ |
| 7–8 | Rep counting + smoothing + unit test | ✅ |
| 9 | Consistency (jika ≥3 rep) | ✅ |
| 10 | Penanganan error & validasi input | ⏳ |
| 11–13 | Streamlit UI + disclaimer + status | ✅ |
| 14–16 | Testing dengan video nyata (baik & buruk) | ⏳ |
| 17–18 | Dokumentasi: README, asumsi, keterbatasan | ⏳ |
| 19–20 | Buffer revisi + penyerahan | ⏳ |

---

## 10. Konfigurasi Gerakan

### Squat
- **Landmark:** Hip (23/24), Knee (25/26), Ankle (27/28)
- **Sudut utama:** Lutut (hip–knee–ankle)
- **Fase:** `STANDING` (sudut > 160°) → `DESCENDING` → `BOTTOM` (< 100°) → `ASCENDING` → `STANDING`
- **1 repetisi:** STANDING → BOTTOM → STANDING
- **Panduan kamera:** Side view (samping), 2–3 m, setinggi pinggul

### Push-up
- **Landmark:** Shoulder (11/12), Elbow (13/14), Wrist (15/16)
- **Sudut utama:** Siku (shoulder–elbow–wrist)
- **Fase:** `UP` (sudut > 150°) → `DESCENDING` → `DOWN` (< 90°) → `ASCENDING` → `UP`
- **1 repetisi:** UP → DOWN → UP
- **Panduan kamera:** Side view

---

## 11. Panduan Pengambilan Video (untuk Pengguna)

Ditampilkan sebagai disclaimer di UI Streamlit:

> ⚠️ **Panduan Perekaman Optimal**
> - Durasi 5–10 detik, seluruh tubuh terlihat dalam frame
> - Kamera statis (tripod), 2–3 m dari subjek, setinggi pinggul
> - Sudut pengambilan 60°–90° terhadap bidang gerak
> - Untuk squat/push-up: **dari samping** lebih baik
> - Pencahayaan cukup, latar kontras dengan subjek
> - Satu orang dalam frame, tanpa oklusi
>
> Video di luar kondisi ini tetap diproses, tetapi akurasi
> sudut dan deteksi landmark dapat menurun.

---

## 12. Keterbatasan & Asumsi

### Keterbatasan
1. Sudut yang diukur adalah **proyeksi 2D**, bukan sudut anatomis 3D.
2. Akurasi dipengaruhi perspektif, posisi kamera, oklusi, dan pencahayaan.
3. Sistem **belum divalidasi** terhadap penilaian ahli atau goniometer.
4. Klaim akurasi klinis **tidak didukung**.
5. ROM yang dihasilkan bukan pengukuran klinis tervalidasi.
6. Metrik stability & consistency adalah **proxy visual**, bukan ukuran universal.

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

## 13. Rancangan Evaluasi (Draft)

### Technical Testing (bisa dilakukan sekarang)
- [x] Aplikasi berjalan di Windows lokal (streamlit 1.40.0, health 200, landing page terekam)
- [x] Video valid diproses tanpa error (`squat_sample.mp4`, exit 0, 12.7s)
- [ ] Video rusak ditolak dengan pesan jelas (unit test `video_io` ✓ — jalur UI `PipelineError → st.error` belum diuji manual)
- [x] Sudut konsisten antar-run (test–retest internal: 2 run, selisih CSV 0.000000°)
- [x] Waktu proses tercatat (12.7s < 60 detik untuk video 11.8s)

### Validasi Ilmiah (menunggu data)
- [ ] Bandingkan sudut sistem vs goniometer
- [ ] Bandingkan sudut sistem vs penilaian ahli
- [ ] Reliabilitas inter-rater (2 ahli, video sama)
- [ ] Reliabilitas test–retest (subjek sama, 2 sesi)
- [ ] Uji statistik: ICC, Bland–Altman, korelasi

---

## 14. Cara Kerja Agent (untuk kolaborasi)

1. **Bekerja bertahap**, bukan langsung semua fitur.
2. **1 sesi = 1 modul** (hemat token, rapi).
3. **Selalu jalankan test** setelah implementasi.
4. **Jangan klaim fitur berjalan** jika belum diuji.
5. **Jangan refactor besar** tanpa kebutuhan jelas.
6. **Jangan tambah dependensi** di luar yang terkunci.
7. **Laporkan hasil apa adanya** — termasuk kegagalan.

### Template Prompt opencode
```
Konteks:
- Proyek: CV evaluasi gerakan gym (squat), Python 3.12 +
  MediaPipe 1.1.1 Tasks API + OpenCV 5.0 + NumPy 2.5.
- PoC monolitik ada di legacy/poc_squat.py (terlampir).
- Sedang modularisasi bertahap.

Tugas sesi ini:
Buat [nama modul] di [path].

Batasan:
- JANGAN ubah file lain.
- JANGAN tambah dependensi baru.
- Tanpa class kalau tidak perlu.
- Docstring singkat.

Sertakan tests/[nama test file] dengan test case:
- [case 1]
- [case 2]

Setelah selesai, tunjukkan cara menjalankan test-nya.
```

---

## 15. Penyerahan (Deliverable Akhir)

- [ ] Source code (folder `src/`, `app.py`, `legacy/poc_squat.py`)
- [ ] `requirements.txt` terkunci
- [ ] `README.md` — instalasi & cara jalankan di Windows CMD
- [ ] Contoh input yang diizinkan untuk demo (`data/squat_sample.mp4`)
- [ ] Dokumentasi fitur, asumsi, keterbatasan
- [ ] Hasil pengujian (log & screenshot)
- [ ] Panduan penggunaan singkat

---

## 16. Log Keputusan

| Tanggal | Keputusan | Alasan |
|---|---|---|
| 2026-10-15 | Pakai video 5–10 detik, bukan foto | Foto tidak bisa hitung ROM/repetisi/consistency |
| 2026-10-15 | Squat dulu, push-up menyusul | MVP, hindari scope creep |
| 2026-10-15 | Lari keluar scope | Gait analysis butuh model & setup berbeda |
| 2026-10-15 | Pakai MediaPipe Tasks API | `mp.solutions` dihapus di MediaPipe 1.1.1 |
| 2026-10-15 | Modularisasi bertahap pakai opencode | Brief minta struktur modular; hemat token |
| 2026-10-15 | Skor kualitas tidak dibuat | Butuh rubrik ahli, hindari klaim arbitrer |
| 2026-10-16 | `ValidationLimits` default permisif (min 0.5s) | Library harus fleksibel; aturan 5–10 detik ditegakkan di UI Streamlit. Test tidak boleh menurunkan standar validasi |
| 2026-10-16 | Rep counting pakai state machine eksplisit dengan hysteresis (bukan peak detection) | Hysteresis default 10° — parameter pertama yang dituning kalau ada false rep di video nyata |
| 2026-10-16 | `metrics.py` selesai dalam 1 sesi, mencakup item Hari 5, 7–8, 9. Hari 6 (visualize) dipisah | Modularisasi bertahap; 1 sesi = 1 modul, hindari refactor besar |
| 2026-10-16 | `visualize.py` pakai Matplotlib OO API (Figure + FigureCanvasAgg), bukan pyplot | Aman headless tanpa konfigurasi backend; landmark di-duck-type, tidak import `pose_estimator`, hindari coupling |
| 2026-10-16 | Sudut dihitung di ruang piksel, helper `angle_from_landmarks()` di `pose_estimator.py` | Ruang ternormalisasi anisotropik (beda ~10°/frame pada video 16:9); helper publik agar bisa di-unit-test |
| 2026-10-16 | Pipeline modular end-to-end terbukti via `run_squat.py`; `poc_squat.py` tidak ditimpa (Brief §9) | Output PoC dipindah ke `output_poc/` sebagai baseline; CSV terverifikasi identik (selisih 0.000000°) |
| 2026-10-16 | `poc_squat.py` diarsipkan ke `legacy/poc_squat.py` | Brief §9 melarang hapus tanpa izin; referensi historis untuk debugging / membandingkan pipeline modular |
| 2026-10-16 | Orkestrasi pipeline dipindah ke `src/pipeline.py` (`analyze_video()` return `AnalysisResult`); `run_squat.py` jadi CLI wrapper tipis | Memungkinkan `app.py` Streamlit (Sesi 7c) memakai pipeline yang sama tanpa duplikasi logika |
| 2026-10-17 | `streamlit==1.40.0` ditambahkan ke requirements (**persetujuan eksplisit owner**, melanggar aturan §14.6 "dependensi terkunci"); file di-full re-freeze 20→61 baris — resolver men-downgrade `pillow 12.3.0→11.3.0`, `packaging 26.3→24.2`; test-deps (pytest dll) akhirnya ikut terkunci | 127/127 passed setelah downgrade — tidak ada regresi |
| 2026-10-17 | `app.py` tipis: hanya UI + disclaimer + error handling; logika di `pipeline.py`; hasil disimpan di `session_state` agar tombol download tidak hilang antar-rerun | Prinsip proyek: UI wrapper boleh tipis, pipeline tetap satu-satunya sumber logika |
| 2026-10-17 | Video annotated ditulis codec `mp4v` (MPEG-4 Part 2) — Chrome/Edge sering tidak decode codec ini saat `st.video` | **Belum diverifikasi di browser.** Jika gagal: opsi re-encode H.264 atau sediakan download file video (sesi berikutnya) |
| 2026-10-17 | Browser modern tidak mendukung codec mp4v (terbukti: video tampil hitam saat uji manual user). Mengganti `st.video` dengan 3 sampel frame (JPG: start/valley/end via `extract_sample_frames()` di `pipeline.py`) + tombol download video MP4. `tests/test_app.py` tidak berubah (tidak ada assertion `st.video`) | Mematuhi aturan tanpa menambah dependensi, tanpa import cv2 di `app.py`; 127/127 passed |

---

## 17. Kontak & Referensi

- **Pemilik proyek:** (dosen Ilmu Keolahragaan)
- **Developer:** (Anda)
- **Brief asli:** `Project Brief — Computer Vision untuk Evaluasi.txt`
- **Deskripsi desain:** `Deskripsi Desain Alat Sensor Melalui Foto dan Video.doc`

---

*Terakhir diperbarui: 2026-10-16*
```