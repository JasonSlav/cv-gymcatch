# Panduan Kontribusi

Terima kasih ingin berkontribusi pada CV Gym Catch! Ikuti langkah berikut.

## 1. Fork & Clone
1. Fork repositori ini ke akun GitHub Anda.
2. Clone hasil fork:
   ```cmd
   git clone https://github.com/<username>/cv-gymcatch.git
   cd cv-gymcatch
   ```

## 2. Buat Branch Baru
Gunakan nama branch yang deskriptif, misalnya:
```cmd
git checkout -b feat/nama-fitur
```

## 3. Setup Environment
```cmd
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
```

## 4. Standar Commit Message
Gunakan prefix konvensional (satu baris, ringkas):
- `feat:` fitur baru
- `fix:` perbaikan bug
- `style:` perubahan tampilan/format (tanpa perubahan logika)
- `docs:` dokumentasi
- `refactor:` restrukturisasi kode (tanpa perubahan perilaku)
- `test:` penambahan/perbaikan test

Contoh: `feat: dropdown pemilihan gerakan`

## 5. Jalankan Test
Pastikan semua test hijau sebelum membuat PR:
```cmd
pytest tests/ -q
```

## 6. Pull Request
1. Push branch Anda ke fork.
2. Buka Pull Request ke branch `main` repositori utama.
3. CI (GitHub Actions) akan otomatis menjalankan test — pastikan lulus.
