"""Smoke test untuk app.py.

Catatan: Streamlit AppTest belum mendukung upload file secara penuh
(di versi 1.40.0). Test di sini fokus ke:
- Render halaman tanpa error.
- Elemen wajib ada (title, disclaimer, uploader, tombol).
Alur analisis penuh diuji secara manual (streamlit run app.py).
"""

import sys
from pathlib import Path

import pytest

# Path ke root proyek
ROOT = Path(__file__).resolve().parents[1]
APP_FILE = ROOT / "app.py"

sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="module")
def app_test():
    """Buat AppTest dari app.py. Skip jika streamlit AppTest tidak tersedia."""
    try:
        from streamlit.testing.v1 import AppTest
    except ImportError:
        pytest.skip("streamlit.testing.v1 tidak tersedia")
    if not APP_FILE.exists():
        pytest.skip(f"app.py tidak ditemukan di {APP_FILE}")
    at = AppTest.from_file(str(APP_FILE), default_timeout=10)
    at.run()
    return at


def test_app_renders_without_exception(app_test):
    assert not app_test.exception


def test_app_has_title(app_test):
    # st.title dirender sebagai markdown header level 1
    titles = [t.value for t in app_test.title]
    assert any("CV Gym Catch" in t for t in titles)


def test_app_has_disclaimer_expander(app_test):
    # Disclaimer ada di expander (label mengandung "Panduan")
    labels = [e.label for e in app_test.expander]
    assert any("Panduan" in lbl for lbl in labels)


def test_app_has_file_uploader(app_test):
    assert len(app_test.get("file_uploader")) >= 1


def test_app_has_analyze_button_disabled_initially(app_test):
    buttons = {b.label: b for b in app_test.button}
    # Cari tombol "Analisis" (label memakai emoji → cari substring)
    analyze = next(
        (b for label, b in buttons.items() if "Analisis" in label), None
    )
    assert analyze is not None
    assert analyze.disabled is True  # belum ada file ter-upload
