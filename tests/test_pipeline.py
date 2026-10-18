"""Unit test untuk src/pipeline.py.

Fokus ke logika murni: analyze_side().
analyze_video() adalah orkestrasi — diuji via run_squat.py (integration manual).
"""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.pipeline import SideAnalysis, analyze_side  # noqa: E402


def _make_rep_curve(up=175.0, down=50.0, half=15):
    down_phase = np.linspace(up, down, half)
    up_phase = np.linspace(down, up, half)
    return np.concatenate([down_phase, up_phase])


def _make_n_rep(n):
    return np.concatenate([_make_rep_curve() for _ in range(n)])


def test_analyze_side_three_reps():
    angles = _make_n_rep(3).tolist()
    result = analyze_side(angles, "kiri")
    assert isinstance(result, SideAnalysis)
    assert result.side == "kiri"
    assert result.rep_count == 3
    assert result.valid_frames == len(angles)
    assert result.rom is not None
    assert result.rom > 100


def test_analyze_side_consistency_when_3_or_more():
    angles = _make_n_rep(3).tolist()
    result = analyze_side(angles, "kiri")
    assert result.consistency is not None
    assert 0.0 <= result.consistency <= 1.0


def test_analyze_side_consistency_none_when_fewer_than_3():
    angles = _make_n_rep(2).tolist()
    result = analyze_side(angles, "kiri")
    assert result.rep_count == 2
    assert result.consistency is None


def test_analyze_side_handles_none_values():
    angles = [None] * 10 + _make_n_rep(1).tolist() + [None] * 10
    result = analyze_side(angles, "kiri")
    assert result.valid_frames == 30
    assert result.rep_count == 1


def test_analyze_side_all_none():
    result = analyze_side([None] * 20, "kanan")
    assert result.valid_frames == 0
    assert result.rep_count == 0
    assert result.rom is None
    assert result.consistency is None


def test_analyze_side_to_dict():
    angles = _make_n_rep(3).tolist()
    result = analyze_side(angles, "kiri")
    d = result.to_dict()
    assert set(d.keys()) == {
        "side", "valid_frames", "rep_count", "rom", "consistency"
    }
    assert d["side"] == "kiri"
    assert d["rep_count"] == 3
