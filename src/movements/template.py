"""
TEMPLATE gerakan baru — salin file ini untuk menambah gerakan.

Panduan menambah gerakan baru (misal lunge, curl):
1. Salin file ini menjadi src/movements/<nama>.py (mis. lunge.py).
2. Buang baris komentar di bawah, isi indeks landmark MediaPipe
   (33 titik — lihat https://developers.google.com/mediapipe.
   Indeks contoh: hip 23/24, knee 25/26, ankle 27/28, shoulder 11/12,
   elbow 13/14, wrist 15/16).
3. Tentukan up_threshold (pose awal/naik) & down_threshold (pose bawah),
   pastikan up > down. State machine memakai hysteresis 10° bawaan.
4. Tulis pesan feedback khas gerakan tersebut (Bahasa Indonesia —
   nanti diterjemahkan otomatis oleh UI via kamus i18n).
5. Daftarkan config baru di src/movements/__init__.py → _MOVEMENTS.
6. Selesai — pipeline, metrics, geometry, UI tidak perlu diubah.

Catatan: input video tetap side-view (60°-90° terhadap bidang gerak).
"""

# from __future__ import annotations
#
# from src.movements.base import FeedbackRules, MovementConfig
#
# LUNGE_CONFIG = MovementConfig(
#     name="lunge",
#     joint_name="knee",
#     parent_idx=23,          # kiri: hip
#     joint_idx=25,           # kiri: knee
#     child_idx=27,           # kiri: ankle
#     right_parent_idx=24,    # kanan: hip
#     right_joint_idx=26,     # kanan: knee
#     right_child_idx=28,     # kanan: ankle
#     up_threshold=165.0,     # berdiri tegak
#     down_threshold=95.0,    # lutut depan menekuk dalam
#     feedback_rules=FeedbackRules(
#         deep_rom_deg=90.0,
#         good_rom_deg=120.0,
#         low_rom="Kedalaman lunge kurang. Turunkan lutut belakang lebih dalam.",
#         good_rom="Kedalaman lunge sudah sangat baik.",
#         low_consistency="Gerakan lunge kurang konsisten. Jaga tempo & jarak langkah.",
#         low_stability="Tubuh bergoyang. Fokus pada satu titik & tegakkan torso.",
#     ),
# )
