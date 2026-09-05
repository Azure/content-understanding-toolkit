"""Smoke tests for the calibration lab.

Run from this folder::

    pytest test_calibration.py -q

They cover the claims the README makes and the fallbacks that keep routing
safe when a field or a value is not covered by the table.
"""

from __future__ import annotations

import math

import pandas as pd
import pytest

import calibration as calib
import matching


@pytest.fixture(scope="module")
def data() -> pd.DataFrame:
    return calib.load_demo_data()


@pytest.fixture(scope="module")
def base(data: pd.DataFrame) -> dict:
    return calib.fit_base_policies(data, split="train")


def test_matching_reproduces_the_shipped_labels(data: pd.DataFrame) -> None:
    rebuilt = matching.add_is_correct(data)
    assert rebuilt["is_correct"].astype(bool).equals(data["is_correct"].astype(bool))


def test_normalization_changes_a_documented_share_of_verdicts(data: pd.DataFrame) -> None:
    strict = matching.add_is_correct(
        data, normalizer=lambda v, field: None if matching.is_null(v) else str(v)
    )
    changed = (strict["is_correct"].astype(bool) != data["is_correct"].astype(bool)).mean()
    assert changed == pytest.approx(0.024, abs=0.001)


def test_blank_definition_agrees_across_modules() -> None:
    from acu_calibrator import _is_null_value

    for value in (None, float("nan"), "", "   "):
        assert _is_null_value(value) is True
        assert matching.is_null(value) is True
    for value in ("0", "x", 0.0):
        assert _is_null_value(value) is False
        assert matching.is_null(value) is False


def test_raw_and_logistic_route_identically(data: pd.DataFrame) -> None:
    """Same boundary, different units — the README's central equivalence claim."""
    routes = {}
    for mode in ("raw_confidence", "logistic"):
        policies = calib.select_policies(
            calib.fit_base_policies(data, split="train", score_mode=mode), 0.80
        )
        routes[mode] = calib.route_frame(data, policies, split="test")["route_to_hitl"]
    assert routes["raw_confidence"].equals(routes["logistic"])


def test_calibration_table_round_trips(base: dict, tmp_path) -> None:
    policies = calib.select_policies(base, 0.80)
    path = calib.save_calibration_table(policies, tmp_path / "table.csv")
    reloaded = calib.load_calibration_table(path)

    assert set(reloaded) == set(policies)
    for field, policy in policies.items():
        assert reloaded[field]["decision"] == policy["decision"]
        assert reloaded[field]["null_policy"]["decision"] == policy["null_policy"]["decision"]
        if policy["decision"] == "calibrate":
            assert reloaded[field]["threshold"] == pytest.approx(policy["threshold"])


def test_routing_falls_back_to_review(base: dict) -> None:
    """Anything the table cannot decide must go to a person, not straight through."""
    policies = calib.select_policies(base, 0.80)
    calibrated = next(f for f, p in policies.items() if p["decision"] == "calibrate")

    frame = pd.DataFrame(
        [
            {
                "document_id": "d1",
                "split": "test",
                "field_name": "a_field_not_in_the_table",
                "extracted_value": "x",
                "confidence": 0.99,
                "is_correct": True,
            },
            {
                "document_id": "d1",
                "split": "test",
                "field_name": calibrated,
                "extracted_value": "x",
                "confidence": None,
                "is_correct": True,
            },
        ]
    )
    routed = calib.route_frame(frame, policies, split="test")
    assert routed["route_to_hitl"].all()
    assert set(routed["route_reason"]) == {"unknown_field", "missing_confidence"}


def test_savings_attribution_is_exhaustive(base: dict, data: pd.DataFrame) -> None:
    policies = calib.select_policies(base, 0.80)
    per_field, portfolio = calib.savings_attribution(
        policies, calib.calibration_input(data, split="train")
    )
    totals = per_field["null_savings"] + per_field["lr_savings"] + per_field["expected_hitl"]
    assert (totals == per_field["baseline_hitl"]).all()
    assert portfolio["null_savings_pct"] + portfolio["lr_savings_pct"] + portfolio[
        "hitl_load"
    ] == pytest.approx(1.0)


def test_the_dial_is_monotone_on_held_out_documents(base: dict, data: pd.DataFrame) -> None:
    """More coverage asked for must never mean less coverage delivered."""
    tracking = calib.coverage_tracking(base, data, split="test", step=0.1)
    assert tracking["calibrated_catch"].is_monotonic_increasing
    assert tracking["overall_stp_rate"].is_monotonic_decreasing


def test_the_target_is_a_floor_on_the_calibrated_track_only(
    base: dict, data: pd.DataFrame
) -> None:
    """The README promises the target governs the calibrated track, and that the
    overall figure sits above it because fully reviewed fields catch everything."""
    target = 0.80
    routed = calib.route_frame(data, calib.select_policies(base, target), split="test")
    _, totals = calib.held_out_metrics(routed)

    thresholded = routed["route_reason"].isin(calib.THRESHOLD_ROUTE_REASONS)
    incorrect = ~routed["is_correct"].astype(bool)
    calibrated_catch = int(
        (incorrect & thresholded & routed["route_to_hitl"].astype(bool)).sum()
    ) / int((incorrect & thresholded).sum())

    assert calibrated_catch < totals["catch_rate"]
    # Selection has no margin, so held-out catch lands near the target, not above it.
    assert abs(calibrated_catch - target) < 0.05


def test_unknown_score_mode_is_rejected() -> None:
    from acu_calibrator import CalibrationConfig

    with pytest.raises(ValueError):
        CalibrationConfig(score_mode="nonsense")


def test_target_range_is_inclusive() -> None:
    assert calib.target_range(0.5, 0.9, 0.1) == [0.5, 0.6, 0.7, 0.8, 0.9]
    with pytest.raises(ValueError):
        calib.target_range(0.5, 0.9, 0.0)


def test_missing_columns_are_reported(tmp_path) -> None:
    path = tmp_path / "bad.csv"
    pd.DataFrame({"document_id": ["d1"]}).to_csv(path, index=False)
    with pytest.raises(KeyError):
        calib.load_canonical_file(path)


def test_portfolio_metrics_handle_an_empty_denominator() -> None:
    per_field = pd.DataFrame(
        [
            {
                "field_name": "f",
                "n_observations": 3,
                "auto_approved": 0,
                "mistakes_slipped_through": 0,
                "total_mistakes": 0,
                "mistakes_caught": 0,
            }
        ]
    )
    totals = calib.portfolio_metrics(per_field)
    assert totals["auto_approve_rate"] == 0.0
    assert math.isnan(totals["stp_error_rate"])
    assert math.isnan(totals["catch_rate"])
