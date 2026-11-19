"""Test khusus gerakan Back Up / Back Extension."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.geometry import calculate_angle  # noqa: E402
from src.metrics import (  # noqa: E402
    RepCountResult,
    RepInfo,
    compute_consistency,
    compute_movement_control,
    compute_rom,
    compute_stability_proxy,
    count_reps,
    extract_rep_curves,
    generate_rule_based_feedback,
    smooth_angles,
)
from src.movements import get_movement_config  # noqa: E402
from src.movements.base import MovementControlRules  # noqa: E402
from src.pipeline import analyze_side  # noqa: E402


def _curve(
    n_reps: int = 5,
    top: float = 177.0,
    valley: float = 152.0,
    per_phase: int = 12,
) -> np.ndarray:
    """Kurva back extension sintetis dengan puncak/lembah berulang."""
    chunks = []
    for _ in range(n_reps):
        chunks.extend(np.linspace(top, valley, per_phase))
        chunks.extend(np.linspace(valley, top, per_phase)[1:])
    return np.asarray(chunks, dtype=float)


def _timestamps(n: int, fps: float = 30.0) -> list:
    return [i / fps for i in range(n)]


def _rules() -> MovementControlRules:
    return MovementControlRules()


# --- registry & konfigurasi ---

def test_back_up_registered_and_config_valid():
    config = get_movement_config("back_up")
    assert config.name == "back_up"
    assert config.joint_name == "hip"
    assert config.camera_angle == "side"
    assert config.exercise_type == "dynamic"


def test_back_up_thresholds_and_provisional_rom_reference():
    config = get_movement_config("back_up")
    assert config.up_threshold == pytest.approx(170.0)
    assert config.down_threshold == pytest.approx(160.0)
    assert config.rom_reference == pytest.approx(42.0)
    assert config.feedback_rules.deep_rom_deg == pytest.approx(30.0)
    assert config.feedback_rules.good_rom_deg == pytest.approx(42.0)


def test_back_up_landmark_indices():
    config = get_movement_config("back_up")
    assert (config.parent_idx, config.joint_idx, config.child_idx) == (11, 23, 25)
    assert (
        config.right_parent_idx,
        config.right_joint_idx,
        config.right_child_idx,
    ) == (12, 24, 26)


def test_back_up_control_rules_enabled():
    config = get_movement_config("back_up")
    assert config.control_rules is not None
    assert config.control_rules.min_good_control == pytest.approx(70.0)


# --- geometri & orientasi sudut ---

def test_back_up_angle_flat_prone_is_straight():
    angle = calculate_angle((0.0, 0.0), (1.0, 0.0), (2.0, 0.0))
    assert angle == pytest.approx(180.0)


def test_back_up_angle_decreases_when_chest_lifts():
    flat = calculate_angle((0.0, 0.0), (1.0, 0.0), (2.0, 0.0))
    lifted = calculate_angle((0.0, -0.6), (1.0, 0.0), (2.0, 0.0))
    assert lifted < flat
    assert lifted > 120.0


# --- ROM, repetisi, consistency ---

def test_back_up_rom():
    assert compute_rom(_curve(1, top=180.0, valley=150.0)) == pytest.approx(30.0)
    assert compute_rom([None, None]) is None


def test_back_up_five_clean_reps():
    result = count_reps(_curve(5), up_threshold=170.0, down_threshold=160.0)
    assert result.count == 5


def test_back_up_one_cycle_counts_once():
    result = count_reps(_curve(1), up_threshold=170.0, down_threshold=160.0)
    assert result.count == 1


def test_back_up_partial_rep_not_counted():
    result = count_reps(
        _curve(3, valley=165.0), up_threshold=170.0, down_threshold=160.0
    )
    assert result.count == 0


def test_back_up_small_noise_does_not_add_reps():
    base = _curve(5)
    noise = np.tile([2.5, -2.0, 3.0, -1.5], int(np.ceil(len(base) / 4)))[: len(base)]
    result = count_reps(
        base + noise, up_threshold=170.0, down_threshold=160.0
    )
    assert result.count == 5


def test_back_up_jitter_at_top_does_not_count():
    base = np.full(120, 177.0)
    jitter = base + np.tile([3.0, -3.0], 60)
    result = count_reps(jitter, up_threshold=170.0, down_threshold=160.0)
    assert result.count == 0


def test_back_up_smoothing_preserves_rep_count():
    raw = _curve(5)
    result_raw = count_reps(raw, up_threshold=170.0, down_threshold=160.0)
    result_smoothed = count_reps(
        smooth_angles(raw, window=5), up_threshold=170.0, down_threshold=160.0
    )
    assert result_raw.count == result_smoothed.count == 5


def test_back_up_consistency_identical_reps():
    angles = _curve(3)
    reps = count_reps(angles, up_threshold=170.0, down_threshold=160.0)
    curves = extract_rep_curves(angles, reps)
    consistency = compute_consistency(curves)
    assert consistency is not None
    assert consistency > 0.95


def test_back_up_analyze_side_all_invalid():
    result = analyze_side([None] * 20, "kiri", 170.0, 160.0)
    assert result.valid_frames == 0
    assert result.rep_count == 0
    assert result.rom is None


# --- movement control ---

def test_movement_control_clean_curve_high_score():
    angles = _curve(5)
    reps = count_reps(angles, up_threshold=170.0, down_threshold=160.0)
    control = compute_movement_control(
        angles, _timestamps(len(angles)), reps, _rules()
    )
    assert control is not None
    assert control["score"] == pytest.approx(100.0)
    assert control["reps_used"] == 5
    assert control["direction_consistency"] == pytest.approx(1.0)
    assert control["reversal_count"] == 0


def test_movement_control_speed_invariant():
    angles = _curve(5)
    reps = count_reps(angles, up_threshold=170.0, down_threshold=160.0)
    slow = compute_movement_control(
        angles, [i / 15.0 for i in range(len(angles))], reps, _rules()
    )
    fast = compute_movement_control(
        angles, [i / 60.0 for i in range(len(angles))], reps, _rules()
    )
    assert slow is not None and fast is not None
    assert slow["score"] == pytest.approx(fast["score"])


def test_movement_control_detects_reversals():
    angles = _curve(5)
    jagged = angles.copy()
    jagged[1:-1] += np.where(
        np.arange(1, len(angles) - 1) % 2 == 0, 8.0, -8.0
    )
    reps_clean = count_reps(angles, up_threshold=170.0, down_threshold=160.0)
    reps_jagged = count_reps(jagged, up_threshold=170.0, down_threshold=160.0)
    assert reps_jagged.count == 5
    clean = compute_movement_control(
        angles, _timestamps(len(angles)), reps_clean, _rules()
    )
    jagged_control = compute_movement_control(
        jagged, _timestamps(len(jagged)), reps_jagged, _rules()
    )
    assert clean is not None and jagged_control is not None
    assert jagged_control["score"] < clean["score"]
    assert jagged_control["reversal_count"] > clean["reversal_count"]


def test_movement_control_rejects_wrong_phase_order():
    angles = np.linspace(150.0, 180.0, 30)
    rep = RepInfo(
        start_idx=0,
        valley_idx=10,
        end_idx=20,
        peak_angle=150.0,
        valley_angle=160.0,
    )
    result = RepCountResult(reps=[rep], final_state="STANDING")
    control = compute_movement_control(
        angles, _timestamps(len(angles)), result, _rules()
    )
    assert control is None


def test_movement_control_handles_incomplete_phase():
    angles = _curve(3)
    reps = count_reps(angles, up_threshold=170.0, down_threshold=160.0)
    first = reps.reps[0]
    damaged = list(angles)
    for i in range(first.start_idx + 2, first.valley_idx):
        damaged[i] = None
    control = compute_movement_control(
        damaged,
        _timestamps(len(damaged)),
        reps,
        MovementControlRules(min_phase_samples=8),
    )
    assert control is not None
    assert len(control["phases"]) < 2 * reps.count


def test_movement_control_invalid_timestamps_returns_none():
    angles = _curve(2)
    reps = count_reps(angles, up_threshold=170.0, down_threshold=160.0)
    control = compute_movement_control(
        angles, [None] * len(angles), reps, _rules(), fps=None
    )
    assert control is None


def test_movement_control_fps_fallback():
    angles = _curve(2)
    reps = count_reps(angles, up_threshold=170.0, down_threshold=160.0)
    control = compute_movement_control(
        angles, None, reps, _rules(), fps=30.0
    )
    assert control is not None


def test_movement_control_skips_zero_and_large_gaps():
    angles = _curve(2)
    reps = count_reps(angles, up_threshold=170.0, down_threshold=160.0)
    timestamps = _timestamps(len(angles))
    timestamps[5] = timestamps[4]  # dt = 0
    timestamps[30] = timestamps[29] + 2.0  # gap > max_gap_sec
    control = compute_movement_control(angles, timestamps, reps, _rules())
    assert control is not None
    assert 0.0 <= control["score"] <= 100.0


def test_movement_control_partial_reps_returns_none():
    angles = _curve(3, valley=165.0)
    reps = count_reps(angles, up_threshold=170.0, down_threshold=160.0)
    assert reps.count == 0
    assert (
        compute_movement_control(
            angles, _timestamps(len(angles)), reps, _rules()
        )
        is None
    )


def test_movement_control_none_when_reps_missing():
    angles = _curve(1)
    assert (
        compute_movement_control(
            angles,
            _timestamps(len(angles)),
            RepCountResult(reps=[], final_state="UNKNOWN"),
            _rules(),
        )
        is None
    )


# --- stability tetap terpisah ---

def test_back_up_horizontal_stability_still_available():
    from types import SimpleNamespace

    def landmark(x):
        return SimpleNamespace(x=x, y=0.5, z=0.0, visibility=1.0)

    def frame(x_left, x_right):
        lm = [landmark(0.0) for _ in range(33)]
        lm[23] = landmark(x_left)
        lm[24] = landmark(x_right)
        return lm

    history = [frame(0.4, 0.5), frame(0.4, 0.5), frame(0.4, 0.5)]
    assert compute_stability_proxy(history, 1280, 720) == pytest.approx(100.0)


# --- scoring & feedback ---

def test_back_up_scoring_alignment_and_labels():
    config = get_movement_config("back_up")
    result = generate_rule_based_feedback(
        42.0, 1.0, 100.0, config.feedback_rules, config.rom_reference
    )
    assert result["score"] == pytest.approx(100.0)
    assert result["label"] == "Baik"


def test_back_up_feedback_messages():
    config = get_movement_config("back_up")
    low = generate_rule_based_feedback(
        20.0, 0.5, 50.0, config.feedback_rules, config.rom_reference
    )
    assert config.feedback_rules.low_rom in low["feedback_list"]

    good = generate_rule_based_feedback(
        45.0, 0.9, 95.0, config.feedback_rules, config.rom_reference
    )
    assert config.feedback_rules.good_rom in good["feedback_list"]


def test_back_up_score_is_clamped():
    config = get_movement_config("back_up")
    high = generate_rule_based_feedback(
        500.0, 5.0, 500.0, config.feedback_rules, config.rom_reference
    )
    low = generate_rule_based_feedback(
        -50.0, -1.0, -100.0, config.feedback_rules, config.rom_reference
    )
    assert high["score"] == pytest.approx(100.0)
    assert low["score"] == pytest.approx(0.0)


# --- regression konfigurasi lain ---

def test_other_movement_configs_unchanged():
    expected = {
        "squat_standard": (160.0, 100.0, 135.0, "dynamic"),
        "squat_sumo": (160.0, 110.0, 135.0, "dynamic"),
        "squat_plie": (160.0, 110.0, 135.0, "dynamic"),
        "pushup_standard": (150.0, 90.0, 135.0, "dynamic"),
        "pushup_wide": (150.0, 90.0, 135.0, "dynamic"),
        "pushup_diamond": (150.0, 80.0, 135.0, "dynamic"),
        "pushup_pike": (160.0, 80.0, 135.0, "dynamic"),
        "crunch_standard": (120.0, 40.0, 135.0, "dynamic"),
        "crunch_swimming": (150.0, 100.0, 135.0, "dynamic"),
        "crunch_bicycle": (120.0, 40.0, 135.0, "dynamic"),
        "vsit_hold": (130.0, 90.0, 40.0, "static"),
    }
    for name, values in expected.items():
        config = get_movement_config(name)
        assert (
            config.up_threshold,
            config.down_threshold,
            config.rom_reference,
            config.exercise_type,
        ) == values
        assert config.control_rules is None
