"""Precompute every number the explainer site displays.

The site is fully static: this script runs the real calibration once, over the
whole range of coverage targets and both scoring engines, and writes the results
to ``src/data/payload.json``. Nothing Python-related runs at page-view time.

Usage (from this folder)::

    python build_payload.py

The generated payload is committed, so regenerating it is only necessary after
changing the dataset or the calibration logic.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
WEB_APP = HERE.parent
LAB = WEB_APP.parent / "calibration_lab"

if not LAB.exists():
    raise SystemExit(f"calibration_lab not found at {LAB}; the two folders ship together")
sys.path.insert(0, str(LAB))

import calibration as lab  # noqa: E402  (needs the sys.path entry above)


OUTPUT = WEB_APP / "src" / "data" / "payload.json"

# Business dial: the share of known mistakes human review must catch.
TARGET_START, TARGET_END, TARGET_STEP = 0.50, 0.99, 0.01

# Global-cutoff strawman: raw CU confidence applied uniformly to every field.
CUTOFF_STEP = 0.02

# Labeled-volume sweep: how many training documents the signal is measured on.
# Anything at or above the split size collapses to the single exhaustive draw.
VOLUME_GRID = (25, 50, 100, 150, 200, 300, 400, 500, 600, 700)
VOLUME_REPEATS = 10
VOLUME_SEED = 7

ENGINES = ("raw_confidence", "logistic")

FIELD_LABELS = {
    "menu.name": "Item name",
    "menu.price": "Item price",
    "menu.quantity": "Item quantity",
    "subtotal_price": "Subtotal",
    "tax_price": "Tax",
    "service_price": "Service charge",
    "other_adjustment": "Discount",
    "total_price": "Total",
}

# Buckets ``estimate_hitl_savings`` assigns; anything not calibrated or
# blanket-trusted means every filled-in value goes to review.
_AUTOMATED_BUCKETS = frozenset({"calibrate", "always_trust"})


def label_for(field: str) -> str:
    return FIELD_LABELS.get(field, field)


def r(value, digits: int = 4):
    """Round for transport, mapping NaN/None to null so JSON stays valid."""
    if value is None:
        return None
    if isinstance(value, (np.floating, float)):
        return None if np.isnan(value) else round(float(value), digits)
    if isinstance(value, (np.integer, int)):
        return int(value)
    return value


def build_meta(data: pd.DataFrame, targets: list[float]) -> dict:
    metadata = json.loads((LAB / "data" / "metadata.json").read_text(encoding="utf-8"))
    documents = data.groupby("split")["document_id"].nunique().to_dict()
    observations = data["split"].value_counts().to_dict()
    train = data.loc[data["split"] == "train"]
    test = data.loc[data["split"] == "test"]
    return {
        "datasetName": metadata["name"],
        "sourceDataset": metadata["source_dataset"],
        "license": metadata["license"],
        "analyzer": metadata["analyzer_id"],
        "completionModel": metadata["completion_model"],
        "apiVersion": metadata["api_version"],
        "documents": {split: int(n) for split, n in documents.items()},
        "observations": {split: int(n) for split, n in observations.items()},
        "totalObservations": int(len(data)),
        "trainMistakes": int((~train["is_correct"].astype(bool)).sum()),
        "testMistakes": int((~test["is_correct"].astype(bool)).sum()),
        "blankShare": r(float(train["extracted_value"].isna().mean())),
        "targets": [r(t, 2) for t in targets],
        "minAucCiLower": lab.MIN_AUC_CI_LOWER,
        "fieldOrder": [label_for(f) for f in sorted(FIELD_LABELS)],
    }


def build_fields(data: pd.DataFrame, base_policies: dict) -> list[dict]:
    """Per-field static profile: volume, accuracy, and how much signal the
    confidence score carries. Target-independent."""
    train = lab.calibration_input(data, split="train")
    signal = lab.signal_frame(base_policies).set_index("field_name")
    rows = []
    for field, group in train.groupby("field_name", sort=True):
        record = signal.loc[field]
        blank = group["extracted_value"].isna()
        rows.append(
            {
                "field": field,
                "label": label_for(field),
                "nTotal": int(len(group)),
                "nBlank": int(blank.sum()),
                "nFilled": int((~blank).sum()),
                "blankShare": r(float(blank.mean())),
                "accuracy": r(float(group["is_correct"].mean())),
                "nMistakes": int((~group["is_correct"].astype(bool)).sum()),
                "meanConfidence": r(float(group["confidence"].mean())),
                "auc": r(record["auc"]),
                "aucLow": r(record["auc_ci_lower"]),
                "aucHigh": r(record["auc_ci_upper"]),
                "confidenceIsUsable": bool(record["confidence_is_usable"]),
                "blankPrecision": r(record["blank_precision"]),
                "blankLow": r(record["blank_ci_lower"]),
                "blankHigh": r(record["blank_ci_upper"]),
            }
        )
    return rows


def build_confidence_distribution(data: pd.DataFrame, bins: int = 20) -> list[dict]:
    """Histogram of confidence for correct vs incorrect filled-in values, per
    field. Shows how heavily the two distributions overlap."""
    train = lab.calibration_input(data, split="train")
    filled = train.loc[train["extracted_value"].notna()]
    edges = np.linspace(0.0, 1.0, bins + 1)
    rows = []
    for field, group in filled.groupby("field_name", sort=True):
        correct = group.loc[group["is_correct"].astype(bool), "confidence"]
        wrong = group.loc[~group["is_correct"].astype(bool), "confidence"]
        rows.append(
            {
                "field": field,
                "label": label_for(field),
                "correct": np.histogram(correct, bins=edges)[0].tolist(),
                "incorrect": np.histogram(wrong, bins=edges)[0].tolist(),
            }
        )
    return {"binEdges": [r(e, 3) for e in edges], "fields": rows}


def build_signal_vs_volume(data: pd.DataFrame) -> dict:
    """Re-measure every field's signal on progressively larger slices of the
    training split, so the site can show intervals tightening as labeled
    documents accumulate. Sub-sample sizes are averaged over several draws;
    the final point is the whole split, so it reproduces ``build_fields``."""
    train_docs = np.array(
        sorted(data.loc[data["split"] == "train", "document_id"].unique())
    )
    total = int(len(train_docs))
    grid = [n for n in VOLUME_GRID if n < total] + [total]

    per_field: dict[str, list[dict]] = {field: [] for field in FIELD_LABELS}
    for n_docs in grid:
        # One draw is exhaustive once the sub-sample is the whole split.
        repeats = 1 if n_docs >= total else VOLUME_REPEATS
        print(f"  volume sweep: {n_docs} docs x {repeats} ...", flush=True)
        draws: dict[str, list[pd.Series]] = {field: [] for field in FIELD_LABELS}
        for repeat in range(repeats):
            rng = np.random.default_rng(VOLUME_SEED + repeat)
            picked = set(rng.choice(train_docs, size=n_docs, replace=False))
            subset = data.loc[data["document_id"].isin(picked)]
            policies = lab.fit_base_policies(subset, split="train")
            signal = lab.signal_frame(policies).set_index("field_name")
            for field in FIELD_LABELS:
                if field in signal.index:
                    draws[field].append(signal.loc[field])

        for field, records in draws.items():
            per_field[field].append(_average_signal(records, repeats))

    return {"documentCounts": grid, "repeats": VOLUME_REPEATS, "perField": per_field}


def _average_signal(records: list[pd.Series], repeats: int) -> dict:
    """Mean point estimate and interval across draws, for both tracks. A draw
    that left a field without enough data reports nothing; if that is most of
    them, the field counts as unmeasured at this volume rather than being scored
    on the lucky draws."""
    filled = _average_interval(
        records, repeats, ("auc", "auc_ci_lower", "auc_ci_upper")
    )
    blank = _average_interval(
        records, repeats, ("blank_precision", "blank_ci_lower", "blank_ci_upper")
    )
    return {
        "auc": filled[0],
        "aucLow": filled[1],
        "aucHigh": filled[2],
        # The blank track's bar is the coverage target, which the site picks
        # later, so only the filled-in track can be judged here.
        "usable": filled[1] is not None and filled[1] >= lab.MIN_AUC_CI_LOWER,
        "nFilled": _mean_count(records, "n_filled"),
        "blankPrecision": blank[0],
        "blankLow": blank[1],
        "blankHigh": blank[2],
        "nBlank": _mean_count(records, "n_blank"),
    }


def _average_interval(
    records: list[pd.Series], repeats: int, keys: tuple[str, str, str]
) -> tuple[float | None, float | None, float | None]:
    # A draw that could not measure the field reports NaN, not None: the signal
    # frame is a DataFrame, so its missing values are already coerced to float.
    measured = [record for record in records if not pd.isna(record[keys[1]])]
    if len(measured) * 2 < repeats:
        return None, None, None
    point, lower, upper = (
        r(float(np.mean([record[key] for record in measured]))) for key in keys
    )
    return point, lower, upper


def _mean_count(records: list[pd.Series], key: str) -> int:
    return round(float(np.mean([record[key] for record in records]))) if records else 0


def build_global_cutoff(data: pd.DataFrame) -> dict:
    """The strawman: one raw-confidence cutoff applied to every field. Traced
    per field so it is visible that the same number lands very differently."""
    train = lab.calibration_input(data, split="train")
    cutoffs = [round(c, 3) for c in np.arange(0.0, 1.0 + CUTOFF_STEP / 2, CUTOFF_STEP)]
    confidence = train["confidence"].to_numpy(dtype=float)
    correct = train["is_correct"].to_numpy(dtype=bool)
    fields = train["field_name"].to_numpy()

    per_field: dict[str, list[dict]] = {}
    for field in sorted(train["field_name"].unique()):
        mask = fields == field
        field_confidence = confidence[mask]
        field_correct = correct[mask]
        series = []
        for cutoff in cutoffs:
            auto = np.where(np.isnan(field_confidence), False, field_confidence >= cutoff)
            n_auto = int(auto.sum())
            series.append(
                {
                    "stpRate": r(n_auto / len(field_confidence)),
                    "errorRate": r(
                        float((~field_correct[auto]).mean()) if n_auto else None
                    ),
                    "nAuto": n_auto,
                }
            )
        per_field[field] = series

    overall = []
    total_errors = int((~correct).sum())
    for cutoff in cutoffs:
        auto = np.where(np.isnan(confidence), False, confidence >= cutoff)
        n_auto = int(auto.sum())
        overall.append(
            {
                "stpRate": r(n_auto / len(confidence)),
                "errorRate": r(float((~correct[auto]).mean()) if n_auto else None),
                "catch": r(int((~correct & ~auto).sum()) / total_errors),
            }
        )
    return {"cutoffs": cutoffs, "perField": per_field, "overall": overall}


def build_engine(data: pd.DataFrame, targets: list[float], score_mode: str) -> dict:
    """Expected (training) and measured (unseen test) results at every target."""
    print(f"  fitting base policies [{score_mode}] ...", flush=True)
    base_policies = lab.fit_base_policies(data, split="train", score_mode=score_mode)
    train = lab.calibration_input(data, split="train")

    expected_portfolio: list[dict] = []
    expected_per_field: dict[str, list[dict]] = {}
    measured_portfolio: list[dict] = []
    measured_per_field: dict[str, list[dict]] = {}
    cutoffs: dict[str, list] = {}

    for index, target in enumerate(targets):
        policies = lab.select_policies(base_policies, target)

        # Expected: what the policy forecasts on the documents it learned from.
        per_field, portfolio = lab.savings_attribution(policies, train)
        expected_portfolio.append(
            {
                "target": r(target, 2),
                "blankSaved": r(portfolio["null_savings_pct"]),
                "filledSaved": r(portfolio["lr_savings_pct"]),
                "reviewed": r(portfolio["hitl_load"]),
                "totalSaved": r(portfolio["hitl_savings_pct"]),
                "blankSavedCount": int(portfolio["null_savings"]),
                "filledSavedCount": int(portfolio["lr_savings"]),
                "reviewedCount": int(portfolio["expected_hitl"]),
                "calibratedFields": int(portfolio["n_calibrated_fields"]),
                "reviewedFields": int(portfolio["n_always_review_fields"]),
            }
        )
        for row in per_field.to_dict(orient="records"):
            field = row["field"]
            expected_per_field.setdefault(field, []).append(
                {
                    "blankSaved": int(row["null_savings"]),
                    "filledSaved": int(row["lr_savings"]),
                    "reviewed": int(row["expected_hitl"]),
                    "nTotal": int(row["n_total"]),
                    "automated": row["bucket"] in _AUTOMATED_BUCKETS,
                }
            )
            policy = policies[field]
            cutoffs.setdefault(field, []).append(
                {
                    "cutoff": r(policy.get("threshold"), 3),
                    "blankAutoApproved": policy["null_policy"]["decision"] == "null_to_stp",
                }
            )

        # Measured: the frozen policy run against documents it never saw.
        routed = lab.route_frame(data, policies, split="test")
        measured, totals = lab.held_out_metrics(routed)
        to_hitl = routed["route_to_hitl"].astype(bool)
        incorrect = ~routed["is_correct"].astype(bool)
        thresholded = routed["route_reason"].isin(lab.THRESHOLD_ROUTE_REASONS)
        thresholded_errors = int((incorrect & thresholded).sum())
        measured_portfolio.append(
            {
                "target": r(target, 2),
                "autoApproveRate": r(totals["auto_approve_rate"]),
                "reviewRate": r(totals["review_rate"]),
                "catch": r(totals["catch_rate"]),
                "calibratedCatch": r(
                    int((incorrect & thresholded & to_hitl).sum()) / thresholded_errors
                    if thresholded_errors
                    else None
                ),
                "stpErrorRate": r(totals["stp_error_rate"]),
                "mistakesSlipped": int(totals["mistakes_slipped_through"]),
                "mistakesCaught": int(totals["mistakes_caught"]),
                "totalMistakes": int(totals["total_mistakes"]),
            }
        )
        for row in measured.to_dict(orient="records"):
            measured_per_field.setdefault(row["field_name"], []).append(
                {
                    "autoApproveRate": r(row["auto_approve_rate"]),
                    "catch": r(row["catch_rate"]),
                    "stpErrorRate": r(row["stp_error_rate"]),
                }
            )

        if (index + 1) % 10 == 0:
            print(f"    {index + 1}/{len(targets)} targets", flush=True)

    return {
        "expected": {"portfolio": expected_portfolio, "perField": expected_per_field},
        "measured": {"portfolio": measured_portfolio, "perField": measured_per_field},
        "cutoffs": cutoffs,
    }


def main() -> None:
    print("loading dataset ...", flush=True)
    data = lab.load_demo_data()
    targets = lab.target_range(TARGET_START, TARGET_END, TARGET_STEP)

    print("fitting the reference signal ...", flush=True)
    reference_policies = lab.fit_base_policies(data, split="train")

    payload = {
        "meta": build_meta(data, targets),
        "fields": build_fields(data, reference_policies),
        "confidenceDistribution": build_confidence_distribution(data),
        "signalVsVolume": build_signal_vs_volume(data),
        "globalCutoff": build_global_cutoff(data),
        "naiveFrontier": [
            {"threshold": r(row["threshold"], 3), "stpRate": r(row["stpRate"]), "catch": r(row["catch"])}
            for row in lab.naive_threshold_sweep(data, split="test", step=0.005)
            .rename(columns={"stp_rate": "stpRate"})
            .to_dict(orient="records")
        ],
        "engines": {},
    }

    for score_mode in ENGINES:
        print(f"engine: {score_mode}", flush=True)
        payload["engines"][score_mode] = build_engine(data, targets, score_mode)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    size_kb = OUTPUT.stat().st_size / 1024
    print(f"\nwrote {OUTPUT.relative_to(WEB_APP)} ({size_kb:,.0f} KB)")


if __name__ == "__main__":
    main()
