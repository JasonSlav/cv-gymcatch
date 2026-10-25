"""
Streamlit UI tipis di atas src.pipeline.analyze_video().

Prinsip:
- Tidak ada logika bisnis di sini. Semua di pipeline.py.
- Tidak import MediaPipe/OpenCV langsung.
- Error handling lengkap: file terlalu besar, format salah, PipelineError.

Jalankan:
    streamlit run app.py
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

from src.pipeline import DEFAULT_MODEL_PATH, PipelineError, analyze_video


# --- Konstanta UI ---
MAX_FILE_SIZE_MB = 50
ALLOWED_EXTENSIONS = ["mp4", "mov"]
DISCLAIMER_MD = """
⚠️ **Panduan Perekaman Optimal**
- Durasi 10–15 detik, seluruh tubuh terlihat dalam frame.
- Kamera statis (tripod), 2–3 m dari subjek, setinggi pinggul.
- Sudut pengambilan 60°–90° terhadap bidang gerak.
- Untuk squat: **dari samping** lebih baik.
- Pencahayaan cukup, latar kontras dengan subjek.
- Satu orang dalam frame, tanpa oklusi.

_Video di luar kondisi ini tetap diproses, tetapi akurasi sudut dan deteksi
landmark dapat menurun. Hasil belum divalidasi terhadap penilaian ahli._
"""


def _bytes_to_mb(n_bytes: int) -> float:
    return n_bytes / (1024 * 1024)


def _reset_analysis() -> None:
    """Hapus hasil analisis dari session state."""
    for key in ("analysis_result", "uploaded_name", "uploaded_sig"):
        st.session_state.pop(key, None)


def main() -> None:
    st.set_page_config(
        page_title="CV Gym Catch — Analisis Gerakan",
        page_icon="🏋️",
        layout="wide",
    )

    st.title("🏋️ CV Gym Catch — Analisis Gerakan Squat")
    st.caption(
        "Prototype penelitian. Belum divalidasi secara ilmiah. "
        "Hasil hanya untuk keperluan internal laboratorium."
    )

    with st.expander("📋 Panduan Perekaman (klik untuk buka)", expanded=True):
        st.markdown(DISCLAIMER_MD)

    st.divider()

    # --- Upload ---
    uploaded = st.file_uploader(
        "Unggah video squat (mp4/mov, maks 50 MB)",
        type=ALLOWED_EXTENSIONS,
        key="video_uploader",
    )

    if uploaded is not None:
        size_mb = _bytes_to_mb(uploaded.size)
        if size_mb > MAX_FILE_SIZE_MB:
            st.error(
                f"Ukuran file {size_mb:.1f} MB melebihi batas "
                f"{MAX_FILE_SIZE_MB} MB."
            )
            return

        st.info(f"File: **{uploaded.name}** ({size_mb:.1f} MB)")

    # Hapus file = X bawaan file_uploader; hasil disembunyikan otomatis
    # saat file berubah/dihapus (blok anti-stale di bawah).
    run_clicked = st.button(
        "🚀 Analisis",
        type="primary",
        disabled=uploaded is None,
        use_container_width=True,
    )

    # --- Proses ---
    if run_clicked and uploaded is not None:
        _reset_analysis()

        tmp_path: Path | None = None
        try:
            with st.spinner("Menyimpan file sementara…"):
                suffix = Path(uploaded.name).suffix or ".mp4"
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=suffix
                ) as tmp:
                    tmp.write(uploaded.getbuffer())
                    tmp_path = Path(tmp.name)

            progress_bar = st.progress(0.0, text="Menganalisis…")

            def _on_progress(done: int, total: int) -> None:
                frac = done / total if total > 0 else 0.0
                progress_bar.progress(
                    frac, text=f"Menganalisis… {done}/{total} frame"
                )

            with st.spinner("Menganalisis video…"):
                result = analyze_video(
                    video_path=tmp_path,
                    model_path=DEFAULT_MODEL_PATH,
                    output_dir="output",
                    progress_callback=_on_progress,
                )

            progress_bar.progress(1.0, text="Selesai.")
            st.session_state["analysis_result"] = result
            st.session_state["uploaded_name"] = uploaded.name
            st.session_state["uploaded_sig"] = (uploaded.name, uploaded.size)

        except PipelineError as e:
            st.error(f"❌ Gagal menganalisis video: {e}")
        except Exception as e:  # noqa: BLE001
            st.error(f"❌ Terjadi kesalahan tak terduga: {e}")
        finally:
            if tmp_path is not None and tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass

    # --- Hasil ---
    result = st.session_state.get("analysis_result")
    if result is None:
        return

    # Anti-stale: sembunyikan hasil jika file diubah/dihapus via uploader
    # (state tidak dihapus — file identik yang dikembalikan → hasil muncul lagi)
    current_sig = (
        (uploaded.name, uploaded.size) if uploaded is not None else None
    )
    if current_sig != st.session_state.get("uploaded_sig"):
        st.warning(
            "File berubah/dihapus — hasil analisis sebelumnya disembunyikan. "
            "Klik 🚀 Analisis untuk menganalisis file ini."
        )
        return

    st.divider()
    st.subheader("📊 Hasil Analisis")
    st.caption(f"Video: {st.session_state.get('uploaded_name', '(unknown)')}")

    # Pemilihan sisi untuk ditampilkan metriknya
    left = result.left_analysis
    right = result.right_analysis

    st.markdown("### Metrik Utama")

    if result.display_mode == "both":
        # Jika dua sisi valid, tampilkan yang paling lengkap (>=3 rep)
        primary = left if left.rep_count >= right.rep_count else right
    elif result.display_mode == "left":
        primary = left
    elif result.display_mode == "right":
        primary = right
    else:
        primary = left  # fallback

    rom_str = f"{primary.rom:.1f}°" if primary.rom is not None else "N/A"
    cons_str = (
        f"{primary.consistency:.3f}"
        if primary.consistency is not None
        else "N/A (<3 rep)"
    )
    duration = (
        result.meta.frame_count / result.meta.fps if result.meta.fps else 0.0
    )

    # Baris 1
    r1c1, r1c2, r1c3 = st.columns(3)
    r1c1.metric("Skor Kualitas", f"{result.score:.1f}", result.score_label)
    r1c2.metric("Repetisi", primary.rep_count)
    r1c3.metric("Durasi", f"{duration:.1f} detik")

    # Baris 2
    r2c1, r2c2, r2c3 = st.columns(3)
    r2c1.metric("ROM", rom_str)
    r2c2.metric(
        "Stabilitas Tubuh",
        f"{result.stability:.0f}%",
        "Stabil" if result.stability > 70 else "Goyah",
    )
    r2c3.metric("Consistency", cons_str)

    feedback_text = "\n".join(f"- {fb}" for fb in result.feedback_list)
    if not feedback_text:
        feedback_text = "Tidak ada masalah signifikan terdeteksi."
    st.info(feedback_text)
    st.caption(
        "Skor dan feedback dihasilkan dari aturan prototype, "
        "belum divalidasi klinis."
    )

    st.caption(
        f"Sisi dianalisis: **{primary.side}** "
        f"(frame valid: {primary.valid_frames}/{result.meta.frame_count}). "
        f"Waktu proses: {result.process_sec:.2f}s."
    )

    st.divider()
    st.subheader("🖼️ Sampel Frame")
    if len(result.sample_frames) >= 3:
        cols = st.columns(3)
        captions = ("Awal", "Tengah", "Akhir")
        for col, frame_path, cap in zip(cols, result.sample_frames, captions):
            with col:
                st.image(str(frame_path), caption=cap)
    else:
        st.caption("Frame sampel tidak tersedia — gunakan tombol unduh video.")

    if result.plot_path is not None and result.plot_path.exists():
        st.subheader("📈 Grafik Sudut Lutut")
        st.image(str(result.plot_path))

    st.divider()
    st.subheader("⬇️ Unduh Hasil")

    dc1, dc2, dc3, dc4 = st.columns(4)
    with dc1:
        st.download_button(
            "Unduh CSV",
            data=result.csv_path.read_bytes(),
            file_name="knee_angle.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with dc2:
        if result.plot_path is not None and result.plot_path.exists():
            st.download_button(
                "Unduh Grafik (PNG)",
                data=result.plot_path.read_bytes(),
                file_name="knee_angle.png",
                mime="image/png",
                use_container_width=True,
            )
    with dc3:
        st.download_button(
            "Unduh Summary (TXT)",
            data=result.summary_text.encode("utf-8"),
            file_name="summary.txt",
            mime="text/plain",
            use_container_width=True,
        )
    with dc4:
        st.download_button(
            "Unduh Video (MP4)",
            data=result.annotated_video_path.read_bytes(),
            file_name="squat_annotated.mp4",
            mime="video/mp4",
            use_container_width=True,
        )


if __name__ == "__main__":
    main()