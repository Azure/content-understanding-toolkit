"""Per-field HITL/STP routing-policy calibration.

Two-track routing per field:
  * **Null track** — Wilson 95% CI on P(GT null | extracted null). When the
    lower bound clears the null target the policy routes nulls to STP;
    otherwise nulls go to HITL.
  * **Non-null track** — Platt-style 1-D logistic regression on raw ACU
    confidence, evaluated with out-of-fold (OOF) predictions and gated on a
    95% bootstrap CI on AUC.

The calibrated signal supports two threshold-selection questions:

  * **Error interception** (the established ``target_catch_rate`` workflow) —
    what minimum share of known extraction errors must HITL intercept?
  * **STP risk budget** — what is the maximum confidence-bounded error rate
    allowed among values sent straight through?

The second mode is additive. The existing error-interception API, CSV contract,
notebooks, and routing behavior remain unchanged.

Everything below is a reorganization of the routing-policy logic baked into
``address_confirmation_notebooks/1024_calibration_experiment_4.ipynb``,
exposed as a callable module so the notebook flow can be reproduced (and
the resulting per-field policy table can be persisted to CSV) without
re-executing the notebook.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import (
    StratifiedGroupKFold,
    StratifiedKFold,
    cross_val_predict,
)
from statsmodels.stats.proportion import proportion_confint


# Canonical row-key tuple — one entry per value the calibrator emits per
# field, in the order they appear as columns in the deliverable table.
_DEFAULT_ROW_KEYS: tuple[str, ...] = (
    "form_type",
    "form_version",
    "form_id",
    "acu_analyzer",
    "field_name",
    "null_target",
    "null_review",
    "non_null_target",
    "non_null_calibrated",
    "lr_coef",
    "lr_intercept",
    "lr_threshold",
    "calibration_timestamp",
)


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────


def _is_null_value(v) -> bool:
    """True only for true nulls (None / NaN). Empty strings are real
    extractions in this pipeline."""
    if v is None:
        return True
    if isinstance(v, float) and math.isnan(v):
        return True
    return False


def _wilson_ci(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Wilson score CI for a binomial proportion via
    :func:`statsmodels.stats.proportion.proportion_confint` with
    ``method='wilson'``. Returns ``(0.0, 1.0)`` when ``n == 0``."""
    if n == 0:
        return (0.0, 1.0)
    lo, hi = proportion_confint(count=k, nobs=n, alpha=alpha, method="wilson")
    return (float(lo), float(hi))


# ─────────────────────────────────────────────────────────────────────────────
# Config + result objects
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class CalibrationConfig:
    """Knobs for the non-null LR track and the null track."""

    target_catch_rate: float = 0.80
    """Error interception target (technical: OOF mis-extraction recall).

    This is the established threshold objective: the minimum fraction of known
    non-null extraction errors that human review must intercept.
    """

    min_null_precision: float = 0.80
    """Null: Wilson-CI lower-bound bar that null precision must clear before
    nulls are routed to STP."""

    min_auc_ci_lower: float = 0.55
    """Non-null: AUC 95% CI lower bound required before a threshold is fit."""

    min_samples: int = 20
    """Minimum non-null rows before we'll attempt to fit the LR."""

    min_errors_for_cv: int = 5
    """Minimum non-null mis-extractions required for the 5-fold CV."""

    min_nulls: int = 10
    """Minimum null extractions required before the null track may route to
    STP. Below this, nulls always go to HITL."""

    n_splits: int = 5
    n_bootstrap: int = 2000
    random_state: int = 42

    group_col: str | None = None
    """Optional document/group column for leakage-safe OOF predictions and
    cluster-bootstrap AUC confidence intervals.

    The default is ``None`` to preserve the established row-level calibration
    behavior. Set this to ``"document_id"`` for datasets containing repeated
    observations from the same document, such as receipt line items.
    """

    score_mode: Literal["logistic", "raw_confidence"] = "logistic"
    """Which score the non-null threshold sweep ranks observations by.

    * ``"logistic"`` (default) — Platt-style logistic regression on raw
      confidence. Leaves room for additional predictors of correctness later.
    * ``"raw_confidence"`` — rank by raw ACU confidence directly, and deploy a
      confidence cutoff instead of model coefficients.

    While confidence is the only predictor these two are strictly monotone
    transforms of one another, so they produce the *same* ranking, AUC,
    threshold sweep and routing decisions; only the units of the exported
    threshold differ. The modes can only diverge once a second predictor is
    added, at which point the logistic score stops being a function of
    confidence alone.
    """

    def __post_init__(self) -> None:
        if self.score_mode not in ("logistic", "raw_confidence"):
            raise ValueError(
                "score_mode must be 'logistic' or 'raw_confidence', got "
                f"{self.score_mode!r}"
            )


@dataclass(frozen=True)
class StpRiskConfig:
    """Business-facing threshold controls for the additive STP-risk mode."""

    max_stp_error_rate: float = 0.05
    """Maximum Wilson upper confidence bound allowed on errors among STP rows."""

    min_stp_samples: int = 20
    """Minimum accepted non-null rows required to trust an STP estimate."""

    min_nulls: int = 10
    """Minimum null predictions required before nulls may be sent to STP."""

    min_auc_ci_lower: float = 0.55
    """Signal gate shared with the established error-interception workflow."""

    ci_level: float = 0.95

    def __post_init__(self) -> None:
        if not 0 <= self.max_stp_error_rate < 1:
            raise ValueError("max_stp_error_rate must be in [0, 1)")
        if self.min_stp_samples < 1:
            raise ValueError("min_stp_samples must be >= 1")
        if self.min_nulls < 1:
            raise ValueError("min_nulls must be >= 1")
        if not 0 < self.ci_level < 1:
            raise ValueError("ci_level must be in (0, 1)")


@dataclass(frozen=True)
class FormMetadata:
    """Form-level constants written into every row of the calibration table."""

    form_type: str
    form_version: str
    form_id: str
    acu_analyzer: str

    friendly_name_map: Mapping[str, str] | None = None
    """Optional override mapping (canonical field key → display name) used to
    populate the ``Field Name (Friendly)`` column. When None, the field key
    from the dataframe is used as-is."""


# ─────────────────────────────────────────────────────────────────────────────
# Per-field policy
# ─────────────────────────────────────────────────────────────────────────────


def build_routing_policy(
    df_full: pd.DataFrame,
    field_name: str,
    *,
    config: CalibrationConfig | None = None,
) -> dict:
    """Build a two-track routing policy for one field.

    Parameters
    ----------
    df_full : DataFrame with both null and non-null rows. Must include
        ``field_name``, ``confidence``, ``is_correct``, ``extracted_value``.
        Don't pre-filter nulls — the function splits them internally.
    field_name : friendly field key to build a policy for.
    config : tunable knobs; defaults to the values used in the notebook.

    Returns
    -------
    dict with keys (subset shown — see source for full list):
        decision               : 'calibrate' | 'always_review' | 'always_trust'
                                 | 'insufficient_data'
        reason                 : human-readable explanation
        threshold              : LR P(correct) cutoff (only for 'calibrate')
        model                  : fitted sklearn LogisticRegression (only for
                                 'calibrate')
        lr_coef, lr_intercept  : convenience copies of the LR parameters
        auc, auc_ci_lower,     : OOF AUC + 95% bootstrap CI
            auc_ci_upper
        confusion_matrix       : OOF CM on non-null rows
        achieved_catch_rate : errors intercepted by review (mis-extraction recall)
        hitl_load            : human-review rate
        stp_miss_rate        : observed error rate among auto-passed values
        null_policy            : sub-dict with keys
            decision ∈ {'null_to_stp', 'null_to_hitl',
                        'no_nulls_observed', 'insufficient_nulls'},
            null_precision, ci_lower, ci_upper, n_nulls, n_nulls_gt_null,
            min_null_precision, min_nulls, reason.

    The returned dict also carries a private ``_cache`` entry holding the
    pre-decision per-field signal (Wilson CI, OOF probs, AUC bootstrap,
    threshold sweep). :func:`redecide_policy` consumes that cache to derive
    new policies for different ``target_catch_rate`` /
    ``min_null_precision`` values without re-running the LR fit or
    bootstrap.
    """
    cfg = config or CalibrationConfig()
    signal = _compute_field_signal(df_full, field_name, cfg)
    return _apply_policy_decisions(signal, cfg)


def _compute_field_signal(
    df_full: pd.DataFrame,
    field_name: str,
    cfg: CalibrationConfig,
) -> dict:
    """Run all per-field heavy computation (Wilson CI, LR fit, OOF probs,
    AUC + bootstrap CI, threshold sweep). Output is *target-independent* —
    it does not apply the ``target_catch_rate`` or ``min_null_precision``
    gates. :func:`_apply_policy_decisions` consumes this signal to emit the
    policy dict; :func:`redecide_policy` reuses it to cheaply re-derive
    policies at different targets.
    """
    required = {"field_name", "confidence", "is_correct", "extracted_value"}
    missing = required - set(df_full.columns)
    if missing:
        raise KeyError(f"df_full is missing required columns: {sorted(missing)}")

    sub = df_full[df_full["field_name"] == field_name].copy()
    is_null = sub["extracted_value"].apply(_is_null_value).to_numpy()
    sub_null = sub.loc[is_null]
    sub_nonnull = sub.loc[~is_null].dropna(subset=["confidence"])

    # ── Null track (Wilson 95% CI on null precision) ─────────────────────────
    n_nulls = int(len(sub_null))
    n_nulls_gt_null = int(sub_null["is_correct"].sum()) if n_nulls else 0
    if n_nulls > 0:
        p_hat = n_nulls_gt_null / n_nulls
        lo, hi = _wilson_ci(n_nulls_gt_null, n_nulls, alpha=0.05)
        null_precision: float | None = float(p_hat)
        null_ci_lower: float | None = float(lo)
        null_ci_upper: float | None = float(hi)
    else:
        null_precision = null_ci_lower = null_ci_upper = None

    # ── Non-null track ───────────────────────────────────────────────────────
    X = sub_nonnull[["confidence"]].to_numpy()
    y = sub_nonnull["is_correct"].to_numpy().astype(int)
    n = len(y)
    n_errors = int((y == 0).sum())
    n_correct = int((y == 1).sum())

    signal: dict = {
        "field_name": field_name,
        "score_mode": cfg.score_mode,
        "n_nulls": n_nulls,
        "n_nulls_gt_null": n_nulls_gt_null,
        "null_precision": null_precision,
        "null_ci_lower": null_ci_lower,
        "null_ci_upper": null_ci_upper,
        "n": n,
        "n_errors": n_errors,
        "n_correct": n_correct,
        # Populated only if LR fit ran:
        "model": None,
        "oof_y": None,
        "oof_probs": None,
        "auc": None,
        "auc_ci_lower": None,
        "auc_ci_upper": None,
        "sweep": None,
        "bootstrap_degenerate": False,
        # Whether we even attempted the LR fit, and why we stopped if not:
        "lr_skip_reason": None,
    }

    if n < cfg.min_samples:
        signal["lr_skip_reason"] = (
            f"n={n} non-null rows below min_samples={cfg.min_samples}"
        )
        return signal
    if n_errors == 0:
        signal["lr_skip_reason"] = "no errors observed in non-null extractions"
        return signal
    if n_correct == 0:
        signal["lr_skip_reason"] = "no correct non-null extractions observed"
        return signal
    if n_errors < cfg.min_errors_for_cv:
        signal["lr_skip_reason"] = (
            f"only {n_errors} errors — too few for {cfg.n_splits}-fold CV"
        )
        return signal

    # Fit + score. In raw_confidence mode the scorer is the identity, so nothing
    # is fit and a row's score is its own confidence.
    raw_mode = cfg.score_mode == "raw_confidence"
    model = None
    if not raw_mode:
        model = LogisticRegression(random_state=cfg.random_state)
        model.fit(X, y)

    def _global_scores() -> np.ndarray:
        return X[:, 0].astype(float) if raw_mode else model.predict_proba(X)[:, 1]

    # With a single predictor the score is a strictly monotone function of
    # confidence, so the ranking -- and with it the AUC and the entire threshold
    # sweep -- cannot depend on the fitted parameters, and fitting introduces no
    # optimism into them. Pooling probabilities from five different fold models
    # would only reorder rows by fold membership, which is noise. Add a second
    # predictor and the weights do drive the ranking, so out-of-fold scoring
    # becomes necessary again.
    rank_globally = X.shape[1] == 1

    groups: np.ndarray | None = None
    if cfg.group_col is not None:
        if cfg.group_col not in sub_nonnull.columns:
            raise KeyError(
                f"group_col {cfg.group_col!r} is missing from the calibration data"
            )
        groups = sub_nonnull[cfg.group_col].to_numpy()
        if pd.isna(groups).any():
            raise ValueError(f"group_col {cfg.group_col!r} contains null values")
        if len(np.unique(groups)) < cfg.n_splits:
            signal["lr_skip_reason"] = (
                f"only {len(np.unique(groups))} unique groups — too few for "
                f"{cfg.n_splits}-fold grouped CV"
            )
            return signal

    if groups is None:
        if rank_globally:
            oof_probs = _global_scores()
        else:
            cv = StratifiedKFold(
                n_splits=cfg.n_splits, shuffle=True, random_state=cfg.random_state
            )
            oof_probs = cross_val_predict(
                model, X, y, cv=cv, method="predict_proba"
            )[:, 1]
    else:
        cv = StratifiedGroupKFold(
            n_splits=cfg.n_splits, shuffle=True, random_state=cfg.random_state
        )
        oof_probs = np.full(n, np.nan, dtype=float)
        try:
            splits = cv.split(X, y, groups)
            for train_idx, test_idx in splits:
                # The fold walk runs in every mode: it is the viability gate that
                # decides whether a field qualifies for a threshold at all.
                if len(np.unique(y[train_idx])) < 2:
                    signal["lr_skip_reason"] = (
                        "a grouped CV training fold contains only one class"
                    )
                    return signal
                if rank_globally:
                    continue
                fold_model = LogisticRegression(random_state=cfg.random_state)
                fold_model.fit(X[train_idx], y[train_idx])
                oof_probs[test_idx] = fold_model.predict_proba(X[test_idx])[:, 1]
        except ValueError as exc:
            signal["lr_skip_reason"] = f"grouped CV unavailable: {exc}"
            return signal
        if rank_globally:
            oof_probs = _global_scores()
        elif np.isnan(oof_probs).any():
            signal["lr_skip_reason"] = "grouped CV did not predict every row"
            return signal

    # AUC + bootstrap CI on OOF probs
    rng = np.random.default_rng(cfg.random_state)
    boot_aucs: list[float] = []
    unique_groups = np.unique(groups) if groups is not None else None
    group_indices = (
        [np.flatnonzero(groups == group) for group in unique_groups]
        if unique_groups is not None
        else None
    )
    for _ in range(cfg.n_bootstrap):
        if unique_groups is None:
            idx = rng.integers(0, n, size=n)
        else:
            sampled_group_indices = rng.integers(
                0,
                len(unique_groups),
                size=len(unique_groups),
            )
            idx = np.concatenate(
                [group_indices[index] for index in sampled_group_indices]
            )
        if len(np.unique(y[idx])) < 2:
            continue
        boot_aucs.append(roc_auc_score(y[idx], oof_probs[idx]))
    auc = float(roc_auc_score(y, oof_probs))
    signal.update(model=model, oof_y=y, oof_probs=oof_probs, auc=auc)

    if len(boot_aucs) < 0.5 * cfg.n_bootstrap:
        signal["bootstrap_degenerate"] = True
        return signal

    ci_lo = float(np.percentile(boot_aucs, 2.5))
    ci_hi = float(np.percentile(boot_aucs, 97.5))
    signal.update(auc_ci_lower=ci_lo, auc_ci_upper=ci_hi)

    # Sweep OOF thresholds — target-independent; downstream picks the
    # lowest-HITL row whose `catch` clears the requested target.
    cands = np.sort(np.unique(oof_probs))
    cands = np.unique(np.concatenate([cands, cands + 1e-9]))
    rows = []
    for t in cands:
        preds = (oof_probs >= t).astype(int)  # 1 = STP, 0 = HITL
        tp = int(((preds == 1) & (y == 1)).sum())
        fp = int(((preds == 1) & (y == 0)).sum())
        tn = int(((preds == 0) & (y == 0)).sum())
        fn = int(((preds == 0) & (y == 1)).sum())
        rows.append((t, tn, fp, fn, tp))
    sweep = pd.DataFrame(rows, columns=["t", "tn", "fp", "fn", "tp"])
    sweep["catch"] = sweep["tn"] / n_errors
    sweep["hitl_load"] = (sweep["tn"] + sweep["fn"]) / n
    sweep["stp_n"] = sweep["tp"] + sweep["fp"]
    sweep["stp_errors"] = sweep["fp"]
    sweep["stp_rate"] = sweep["stp_n"] / n
    sweep["stp_error_rate"] = np.where(
        sweep["stp_n"] > 0,
        sweep["stp_errors"] / sweep["stp_n"],
        np.nan,
    )
    sweep["stp_error_ci_lower"] = np.nan
    sweep["stp_error_ci_upper"] = np.nan
    has_stp = sweep["stp_n"] > 0
    if has_stp.any():
        lo, hi = proportion_confint(
            count=sweep.loc[has_stp, "stp_errors"].to_numpy(dtype=int),
            nobs=sweep.loc[has_stp, "stp_n"].to_numpy(dtype=int),
            alpha=0.05,
            method="wilson",
        )
        sweep.loc[has_stp, "stp_error_ci_lower"] = lo
        sweep.loc[has_stp, "stp_error_ci_upper"] = hi
    signal["sweep"] = sweep
    return signal


def _build_null_policy(signal: dict, cfg: CalibrationConfig) -> dict:
    """Build the ``null_policy`` sub-dict from cached signal + current cfg."""
    n_nulls = signal["n_nulls"]
    n_nulls_gt_null = signal["n_nulls_gt_null"]
    null_policy: dict = {
        "min_null_precision": cfg.min_null_precision,
        "min_nulls": cfg.min_nulls,
        "n_nulls": n_nulls,
        "n_nulls_gt_null": n_nulls_gt_null,
        "null_precision": signal["null_precision"],
        "ci_lower": signal["null_ci_lower"],
        "ci_upper": signal["null_ci_upper"],
        "decision": None,
        "reason": "",
    }
    if n_nulls == 0:
        null_policy.update(
            decision="no_nulls_observed",
            reason="no null extractions in labeled data → route nulls to HITL",
        )
        return null_policy
    p_hat = signal["null_precision"]
    lo = signal["null_ci_lower"]
    hi = signal["null_ci_upper"]
    if n_nulls < cfg.min_nulls:
        null_policy.update(
            decision="insufficient_nulls",
            reason=(
                f"only {n_nulls} null extractions observed "
                f"(< min_nulls={cfg.min_nulls}) → route nulls to HITL"
            ),
        )
    elif lo >= cfg.min_null_precision:
        null_policy.update(
            decision="null_to_stp",
            reason=(
                f"null precision {p_hat:.1%} "
                f"[95% CI {lo:.1%}–{hi:.1%}] clears "
                f"{cfg.min_null_precision:.0%} bar → STP"
            ),
        )
    else:
        null_policy.update(
            decision="null_to_hitl",
            reason=(
                f"null precision {p_hat:.1%} "
                f"[95% CI {lo:.1%}–{hi:.1%}] below "
                f"{cfg.min_null_precision:.0%} bar → HITL"
            ),
        )
    return null_policy


def _apply_policy_decisions(signal: dict, cfg: CalibrationConfig) -> dict:
    """Cheap: derive a policy dict from a precomputed field signal + cfg.
    No LR fit, no bootstrap — just gates and threshold pick."""
    null_policy = _build_null_policy(signal, cfg)

    base: dict = {
        "field_name": signal["field_name"],
        "score_mode": signal.get("score_mode", "logistic"),
        "n": signal["n"],
        "n_errors": signal["n_errors"],
        "target_catch_rate": cfg.target_catch_rate,
        "decision": None,
        "reason": "",
        "threshold": None,
        "model": signal.get("model"),
        "lr_coef": None,
        "lr_intercept": None,
        "achieved_catch_rate": None,
        "hitl_load": None,
        "stp_miss_rate": None,
        "confusion_matrix": None,
        "auc": signal.get("auc"),
        "auc_ci_lower": signal.get("auc_ci_lower"),
        "auc_ci_upper": signal.get("auc_ci_upper"),
        "null_policy": null_policy,
        "_cache": signal,
    }

    skip_reason = signal.get("lr_skip_reason")
    if skip_reason is not None:
        if signal["n"] < cfg.min_samples:
            base.update(decision="insufficient_data", reason=skip_reason)
        elif signal["n_errors"] == 0:
            base.update(decision="always_trust", reason=skip_reason)
        else:
            base.update(decision="always_review", reason=skip_reason)
        return base

    if signal["bootstrap_degenerate"]:
        base.update(
            decision="always_review",
            reason="bootstrap degenerate — CI unreliable",
        )
        return base

    ci_lo = signal["auc_ci_lower"]
    if ci_lo < cfg.min_auc_ci_lower:
        base.update(
            decision="always_review",
            reason=(
                f"AUC CI lower {ci_lo:.3f} < {cfg.min_auc_ci_lower} — "
                "signal not trustworthy"
            ),
        )
        return base

    sweep: pd.DataFrame = signal["sweep"]
    n = signal["n"]
    n_errors = signal["n_errors"]
    hits = sweep[sweep["catch"] >= cfg.target_catch_rate]
    if hits.empty:
        base.update(
            decision="always_review",
            reason=(
                f"target catch {cfg.target_catch_rate:.0%} "
                "not achievable on OOF"
            ),
        )
        return base
    chosen = hits.loc[hits["hitl_load"].idxmin()]
    threshold = float(chosen["t"])
    tn, fp, fn, tp = (
        int(chosen["tn"]),
        int(chosen["fp"]),
        int(chosen["fn"]),
        int(chosen["tp"]),
    )
    cm = np.array([[tn, fp], [fn, tp]])
    achieved_catch = tn / n_errors
    hitl_load = (tn + fn) / n
    stp_miss = fp / (tp + fp) if (tp + fp) else float("nan")
    model = signal["model"]

    base.update(
        decision="calibrate",
        reason=(
            f"target catch {cfg.target_catch_rate:.0%} met at "
            f"threshold {threshold:.4f}"
        ),
        threshold=threshold,
        lr_coef=float(model.coef_[0, 0]) if model is not None else None,
        lr_intercept=float(model.intercept_[0]) if model is not None else None,
        achieved_catch_rate=float(achieved_catch),
        hitl_load=float(hitl_load),
        stp_miss_rate=float(stp_miss) if not np.isnan(stp_miss) else None,
        confusion_matrix=cm,
    )
    return base


def redecide_policy(policy: Mapping, *, config: CalibrationConfig) -> dict:
    """Re-derive a policy at a new ``config`` using the cached field signal,
    skipping the LR fit and AUC bootstrap.

    The input ``policy`` must have been produced by :func:`build_routing_policy`
    (which attaches a ``_cache`` entry holding the per-field signal).
    """
    cache = policy.get("_cache")
    if cache is None:
        raise ValueError(
            "policy is missing its _cache — was it built with the current "
            "version of build_routing_policy?"
        )
    return _apply_policy_decisions(cache, config)


def redecide_policies(
    policies: Mapping[str, Mapping],
    *,
    config: CalibrationConfig,
) -> dict[str, dict]:
    """Vector form of :func:`redecide_policy` over a ``{field: policy}``
    mapping."""
    return {f: redecide_policy(p, config=config) for f, p in policies.items()}


def stp_risk_frontier(
    policy: Mapping,
    *,
    ci_level: float = 0.95,
) -> pd.DataFrame:
    """Return the cached non-null automation/risk frontier for one field.

    Each row is a candidate calibrated-probability threshold. ``stp_rate`` is
    the share of non-null field observations auto-passed, while
    ``stp_error_ci_upper`` is the Wilson upper confidence bound on the error
    rate among those auto-passed observations.
    """
    if not 0 < ci_level < 1:
        raise ValueError("ci_level must be in (0, 1)")
    cache = policy.get("_cache")
    if cache is None:
        raise ValueError(
            "policy is missing its _cache — was it built with the current "
            "version of build_routing_policy?"
        )
    sweep = cache.get("sweep")
    if sweep is None:
        return pd.DataFrame(
            columns=[
                "t",
                "tn",
                "fp",
                "fn",
                "tp",
                "catch",
                "hitl_load",
                "stp_n",
                "stp_errors",
                "stp_rate",
                "stp_error_rate",
                "stp_error_ci_lower",
                "stp_error_ci_upper",
            ]
        )

    frontier = sweep.copy()
    alpha = 1.0 - ci_level
    frontier["stp_error_ci_lower"] = np.nan
    frontier["stp_error_ci_upper"] = np.nan
    for idx, row in frontier.loc[frontier["stp_n"] > 0].iterrows():
        lo, hi = _wilson_ci(
            int(row["stp_errors"]), int(row["stp_n"]), alpha=alpha
        )
        frontier.loc[idx, "stp_error_ci_lower"] = lo
        frontier.loc[idx, "stp_error_ci_upper"] = hi
    return frontier


def _build_null_policy_for_stp_risk(
    signal: Mapping,
    cfg: StpRiskConfig,
) -> dict:
    """Apply a confidence-bounded error budget to null predictions."""
    n_nulls = int(signal["n_nulls"])
    n_correct = int(signal["n_nulls_gt_null"])
    n_errors = n_nulls - n_correct
    alpha = 1.0 - cfg.ci_level
    error_rate = n_errors / n_nulls if n_nulls else None
    ci_lower, ci_upper = (
        _wilson_ci(n_errors, n_nulls, alpha=alpha)
        if n_nulls
        else (None, None)
    )
    result = {
        "policy_mode": "stp_risk_budget",
        "max_stp_error_rate": cfg.max_stp_error_rate,
        "min_nulls": cfg.min_nulls,
        "n_nulls": n_nulls,
        "n_nulls_gt_null": n_correct,
        "n_null_errors": n_errors,
        "null_precision": signal["null_precision"],
        "null_error_rate": error_rate,
        "error_ci_lower": ci_lower,
        "error_ci_upper": ci_upper,
        # Compatibility aliases used by existing visualizations.
        "ci_lower": signal["null_ci_lower"],
        "ci_upper": signal["null_ci_upper"],
        "decision": None,
        "reason": "",
    }
    if n_nulls == 0:
        result.update(
            decision="no_nulls_observed",
            reason="no null predictions observed → route nulls to HITL",
        )
    elif n_nulls < cfg.min_nulls:
        result.update(
            decision="insufficient_nulls",
            reason=(
                f"only {n_nulls} null predictions observed "
                f"(< min_nulls={cfg.min_nulls}) → route nulls to HITL"
            ),
        )
    elif ci_upper is not None and ci_upper <= cfg.max_stp_error_rate:
        result.update(
            decision="null_to_stp",
            reason=(
                f"null STP error {error_rate:.1%} "
                f"(upper {cfg.ci_level:.0%} bound {ci_upper:.1%}) is within "
                f"the {cfg.max_stp_error_rate:.1%} risk budget → STP"
            ),
        )
    else:
        result.update(
            decision="null_to_hitl",
            reason=(
                f"null STP error upper {cfg.ci_level:.0%} bound "
                f"{ci_upper:.1%} exceeds the "
                f"{cfg.max_stp_error_rate:.1%} risk budget → HITL"
            ),
        )
    return result


def redecide_policy_for_stp_risk(
    policy: Mapping,
    *,
    config: StpRiskConfig | None = None,
) -> dict:
    """Select the most automated threshold within an STP error-rate budget.

    Heavy work is reused from the cached Platt fit and OOF predictions created
    by :func:`build_routing_policy`. A candidate is eligible only when its
    Wilson upper confidence bound is within ``max_stp_error_rate``. Among
    eligible candidates, the one accepting the most observations is selected.
    """
    cfg = config or StpRiskConfig()
    cache = policy.get("_cache")
    if cache is None:
        raise ValueError(
            "policy is missing its _cache — was it built with the current "
            "version of build_routing_policy?"
        )

    null_policy = _build_null_policy_for_stp_risk(cache, cfg)
    n = int(cache["n"])
    n_errors = int(cache["n_errors"])
    base = {
        "field_name": cache["field_name"],
        "score_mode": cache.get("score_mode", "logistic"),
        "policy_mode": "stp_risk_budget",
        "max_stp_error_rate": cfg.max_stp_error_rate,
        "n": n,
        "n_errors": n_errors,
        "decision": None,
        "reason": "",
        "threshold": None,
        "model": cache.get("model"),
        "lr_coef": None,
        "lr_intercept": None,
        "achieved_catch_rate": None,
        "hitl_load": 1.0 if n else None,
        "stp_rate": 0.0 if n else None,
        "stp_n": 0,
        "stp_errors": 0,
        "stp_miss_rate": None,
        "stp_error_ci_lower": None,
        "stp_error_ci_upper": None,
        "confusion_matrix": None,
        "auc": cache.get("auc"),
        "auc_ci_lower": cache.get("auc_ci_lower"),
        "auc_ci_upper": cache.get("auc_ci_upper"),
        "null_policy": null_policy,
        "_cache": cache,
    }

    skip_reason = cache.get("lr_skip_reason")
    if skip_reason is not None:
        if n_errors == 0 and n >= cfg.min_stp_samples:
            lo, hi = _wilson_ci(0, n, alpha=1.0 - cfg.ci_level)
            if hi <= cfg.max_stp_error_rate:
                base.update(
                    decision="always_trust",
                    reason=(
                        f"no errors in {n} non-null observations and upper "
                        f"{cfg.ci_level:.0%} bound {hi:.1%} is within the "
                        f"{cfg.max_stp_error_rate:.1%} risk budget"
                    ),
                    hitl_load=0.0,
                    stp_rate=1.0,
                    stp_n=n,
                    stp_errors=0,
                    stp_miss_rate=0.0,
                    stp_error_ci_lower=lo,
                    stp_error_ci_upper=hi,
                )
                return base
        decision = "insufficient_data" if n < cfg.min_stp_samples else "always_review"
        base.update(decision=decision, reason=f"{skip_reason} → route to HITL")
        return base

    if cache["bootstrap_degenerate"]:
        base.update(
            decision="always_review",
            reason="bootstrap degenerate — signal confidence interval is unreliable",
        )
        return base
    if float(cache["auc_ci_lower"]) < cfg.min_auc_ci_lower:
        base.update(
            decision="always_review",
            reason=(
                f"AUC CI lower {cache['auc_ci_lower']:.3f} < "
                f"{cfg.min_auc_ci_lower:.2f} — signal not trustworthy"
            ),
        )
        return base

    frontier = stp_risk_frontier(policy, ci_level=cfg.ci_level)
    eligible = frontier[
        (frontier["stp_n"] >= cfg.min_stp_samples)
        & (frontier["stp_error_ci_upper"] <= cfg.max_stp_error_rate)
    ]
    if eligible.empty:
        base.update(
            decision="always_review",
            reason=(
                "no threshold has enough accepted samples and a confidence-bounded "
                f"STP error rate ≤ {cfg.max_stp_error_rate:.1%}"
            ),
        )
        return base

    chosen = eligible.loc[eligible["stp_n"].idxmax()]
    threshold = float(chosen["t"])
    tn, fp, fn, tp = (
        int(chosen["tn"]),
        int(chosen["fp"]),
        int(chosen["fn"]),
        int(chosen["tp"]),
    )
    model = cache["model"]
    base.update(
        decision="calibrate",
        reason=(
            f"maximum automation within {cfg.max_stp_error_rate:.1%} STP "
            f"error budget at threshold {threshold:.4f}"
        ),
        threshold=threshold,
        lr_coef=float(model.coef_[0, 0]) if model is not None else None,
        lr_intercept=float(model.intercept_[0]) if model is not None else None,
        achieved_catch_rate=float(chosen["catch"]),
        hitl_load=float(chosen["hitl_load"]),
        stp_rate=float(chosen["stp_rate"]),
        stp_n=int(chosen["stp_n"]),
        stp_errors=int(chosen["stp_errors"]),
        stp_miss_rate=float(chosen["stp_error_rate"]),
        stp_error_ci_lower=float(chosen["stp_error_ci_lower"]),
        stp_error_ci_upper=float(chosen["stp_error_ci_upper"]),
        confusion_matrix=np.array([[tn, fp], [fn, tp]]),
    )
    return base


def redecide_policies_for_stp_risk(
    policies: Mapping[str, Mapping],
    *,
    max_stp_error_rates: float | Mapping[str, float],
    base_config: StpRiskConfig | None = None,
) -> dict[str, dict]:
    """Apply one or per-field STP risk budgets without refitting models."""
    base = base_config or StpRiskConfig()
    if isinstance(max_stp_error_rates, Mapping):
        missing = sorted(set(policies) - set(max_stp_error_rates))
        if missing:
            raise KeyError(f"missing STP risk targets for fields: {missing}")
        targets = max_stp_error_rates
    else:
        targets = {field: float(max_stp_error_rates) for field in policies}

    return {
        field: redecide_policy_for_stp_risk(
            policy,
            config=replace(base, max_stp_error_rate=float(targets[field])),
        )
        for field, policy in policies.items()
    }


# ─────────────────────────────────────────────────────────────────────────────
# Calibration table
# ─────────────────────────────────────────────────────────────────────────────


def _null_review_flag(null_decision: str) -> bool:
    """True ⇔ nulls for this field are routed to HITL (i.e. require review)."""
    return null_decision != "null_to_stp"


def build_calibration_table(
    df_full: pd.DataFrame,
    *,
    metadata: FormMetadata,
    fields: Iterable[str] | None = None,
    config: CalibrationConfig | None = None,
    policies: Mapping[str, dict] | None = None,
) -> pd.DataFrame:
    """Run the two-track calibration over every field and emit the
    deliverable per-field policy table.

    Parameters
    ----------
    df_full : the unfiltered comparison frame (must contain both null and
        non-null rows; same shape consumed by ``build_routing_policy``).
    metadata : ``FormMetadata`` carrying the form-level constants
        (form type/version/id, ACU analyzer name, optional friendly-name
        override map). Forcing a field to always be reviewed is **not** part
        of the calibration contract — leave that field out of the table and
        routing sends it to review.
    fields : iterable of friendly field keys to include. Defaults to every
        unique value of ``df_full['field_name']`` (or the keys of
        ``policies`` when supplied).
    config : ``CalibrationConfig`` knobs; defaults to the notebook values
        (target_catch_rate=0.80, min_null_precision=0.80, …).
    policies : optional precomputed mapping ``{field: policy_dict}`` from
        :func:`build_routing_policies`. When provided, the per-field LR
        fits are reused instead of recomputed; ``df_full`` is then only
        consulted for the default field list.

    Returns
    -------
    DataFrame with columns (in order, defined by ``_DEFAULT_ROW_KEYS``):
        form_type, form_version, form_id, acu_analyzer,
        field_name,
        null_target, null_review,
        non_null_target, non_null_calibrated,
        lr_coef, lr_intercept, lr_threshold,
        calibration_timestamp

    Per-row semantics:
      * **null_target**          — ``config.min_null_precision`` (the bar
        the null Wilson-CI lower bound had to clear).
      * **null_review**          — True iff null_decision != 'null_to_stp'
        (i.e. nulls go to HITL).
      * **non_null_target**      — ``config.target_catch_rate``.
      * **non_null_calibrated**  — True iff non-null decision == 'calibrate'.
        For 'always_trust' / 'always_review' / 'insufficient_data' this is
        False and the LR columns are NaN.
      * **lr_coef / lr_intercept / lr_threshold** — only populated when
        non_null_calibrated is True.
      * **calibration_timestamp** — ISO-8601 UTC timestamp captured once
        per call, identical across every row in the returned table.
    """
    cfg = config or CalibrationConfig()

    if fields is None:
        if policies is not None:
            fields = list(policies.keys())
        else:
            fields = sorted(df_full["field_name"].dropna().unique())

    name_map = metadata.friendly_name_map or {}
    # Single timestamp stamped onto every row so the whole table reflects
    # one calibration run.
    calibrated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    rows: list[dict] = []
    for field_key in fields:
        if policies is not None and field_key in policies:
            policy = policies[field_key]
        else:
            policy = build_routing_policy(df_full, field_key, config=cfg)
        np_ = policy["null_policy"]
        calibrated = policy["decision"] == "calibrate"
        rows.append(
            {
                "form_type":             metadata.form_type,
                "form_version":          metadata.form_version,
                "form_id":               metadata.form_id,
                "acu_analyzer":          metadata.acu_analyzer,
                "field_name":            name_map.get(field_key, field_key),
                "null_target":           cfg.min_null_precision,
                "null_review":           _null_review_flag(np_["decision"]),
                "non_null_target":       cfg.target_catch_rate,
                "non_null_calibrated":   calibrated,
                "lr_coef":               policy["lr_coef"] if calibrated else np.nan,
                "lr_intercept":          policy["lr_intercept"] if calibrated else np.nan,
                "lr_threshold":          policy["threshold"] if calibrated else np.nan,
                "calibration_timestamp": calibrated_at,
            }
        )

    return pd.DataFrame(rows, columns=list(_DEFAULT_ROW_KEYS))


def save_calibration_table(
    table: pd.DataFrame,
    path: str | Path,
    *,
    overwrite: bool = True,
) -> Path:
    """Persist a calibration table to CSV.

    Parameters
    ----------
    table : the dataframe returned by :func:`build_calibration_table`.
        Column order is enforced against ``_DEFAULT_ROW_KEYS`` so
        downstream consumers see a stable schema.
    path : output path (``str`` or ``pathlib.Path``). Parent directories
        are created if they don't exist.
    overwrite : when False, raises ``FileExistsError`` if ``path`` already
        exists. Defaults to True.

    Returns
    -------
    The resolved ``Path`` written to.
    """
    cols = list(_DEFAULT_ROW_KEYS)
    missing = [c for c in cols if c not in table.columns]
    if missing:
        raise ValueError(
            f"calibration table is missing required columns: {missing}"
        )

    out = Path(path)
    if out.exists() and not overwrite:
        raise FileExistsError(f"refusing to overwrite existing file: {out}")
    out.parent.mkdir(parents=True, exist_ok=True)

    table[cols].to_csv(out, index=False)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Visualizations
# ─────────────────────────────────────────────────────────────────────────────


# Null-policy decisions that send nulls to HITL (i.e. NOT routed to STP).
_NULL_TO_HITL_DECISIONS = frozenset(
    {"null_to_hitl", "no_nulls_observed", "insufficient_nulls"}
)


def build_routing_policies(
    df_full: pd.DataFrame,
    fields: Iterable[str] | None = None,
    *,
    config: CalibrationConfig | None = None,
) -> dict[str, dict]:
    """Convenience: run :func:`build_routing_policy` for every field and
    return the mapping ``{field_name: policy_dict}`` consumed by the
    plotting functions below.

    Parameters
    ----------
    df_full : the unfiltered comparison frame (same shape consumed by
        ``build_routing_policy``).
    fields : iterable of friendly field keys to include. Defaults to every
        unique value of ``df_full['field_name']``.
    config : ``CalibrationConfig`` knobs; defaults to
        ``CalibrationConfig()``.
    """
    cfg = config or CalibrationConfig()
    if fields is None:
        fields = sorted(df_full["field_name"].dropna().unique())
    return {f: build_routing_policy(df_full, f, config=cfg) for f in fields}


def plot_calibrated_policies(
    policies: Mapping[str, dict],
    *,
    target_catch_rate: float | None = None,
    ax: "plt.Axes | None" = None,
) -> "plt.Axes":
    """Per-field paired bars: errors caught vs HITL load, for every field
    whose policy decision is ``'calibrate'``.

    A vertical dashed line marks the target catch rate (read from the first
    policy's ``target_catch_rate`` if not supplied).
    """
    rows = [
        {
            "field": name,
            "achieved_catch": p["achieved_catch_rate"],
            "hitl_load": p["hitl_load"],
            "target": p["target_catch_rate"],
        }
        for name, p in policies.items()
        if p.get("decision") == "calibrate"
    ]
    if not rows:
        raise ValueError("no calibrated policies to plot")
    df_plot = (
        pd.DataFrame(rows)
        .sort_values("achieved_catch", ascending=True)
        .reset_index(drop=True)
    )
    if target_catch_rate is None:
        target_catch_rate = float(df_plot["target"].iloc[0])

    n = len(df_plot)
    if ax is None:
        _, ax = plt.subplots(figsize=(11, max(4.5, 0.42 * n + 1.5)))
    y = np.arange(n)
    bar_h = 0.38
    ax.barh(
        y - bar_h / 2, df_plot["achieved_catch"], height=bar_h,
        color="steelblue", label="Errors caught (catch rate)",
    )
    ax.barh(
        y + bar_h / 2, df_plot["hitl_load"], height=bar_h,
        color="tomato", alpha=0.85, label="HITL load",
    )
    for i, row in df_plot.iterrows():
        ax.text(
            row["achieved_catch"] + 0.005, i - bar_h / 2,
            f"{row['achieved_catch']:.0%}", va="center", fontsize=8.5,
        )
        ax.text(
            row["hitl_load"] + 0.005, i + bar_h / 2,
            f"{row['hitl_load']:.0%}", va="center", fontsize=8.5,
        )
    ax.axvline(
        target_catch_rate, color="navy", linestyle="--", lw=1.2,
        label=f"Target catch = {target_catch_rate:.0%}",
    )
    ax.set_yticks(y)
    ax.set_yticklabels(df_plot["field"], fontsize=9)
    ax.set_xlabel("Fraction of non-null traffic", fontsize=11)
    ax.set_xlim(
        0,
        max(1.02, df_plot[["achieved_catch", "hitl_load"]].max().max() + 0.08),
    )
    ax.set_title(
        f"Calibrated routing policies — target catch rate {target_catch_rate:.0%}\n"
        "(per-field OOF 5-fold CV; lower bar = HITL cost, upper bar = errors caught)",
        fontsize=12,
    )
    ax.grid(axis="x", alpha=0.3)
    ax.legend(loc="lower right", fontsize=9)
    plt.tight_layout()
    return ax


def plot_null_routing(
    policies: Mapping[str, dict],
    *,
    min_null_precision: float | None = None,
) -> "plt.Figure":
    """Twin-panel chart of the null-routing track for every field.

    Includes every field that has a ``null_policy`` block — not just the
    LR-calibrated ones — so the full contribution of the null-track to
    HITL savings is visible (always-review and insufficient-data fields
    can still route nulls to STP when null precision clears the bar).

    Left: null volume per field (correct nulls vs null mis-extractions),
    colored by route (green = STP, red = HITL).
    Right: observed null precision with 95% Wilson CI, vs the
    ``min_null_precision`` decision bar.
    """
    rows = []
    for name, pol in policies.items():
        np_ = pol.get("null_policy")
        if np_ is None:
            continue
        n_nulls = int(np_["n_nulls"])
        n_correct = int(np_["n_nulls_gt_null"])
        routes_to_hitl = np_["decision"] in _NULL_TO_HITL_DECISIONS
        rows.append(
            {
                "field": name,
                "n_nulls": n_nulls,
                "n_nulls_gt_null": n_correct,
                "n_null_errors": n_nulls - n_correct,
                "null_precision": np_["null_precision"],
                "ci_lower": np_["ci_lower"],
                "ci_upper": np_["ci_upper"],
                "null_route": "HITL" if routes_to_hitl else "STP",
                "min_null_precision": np_["min_null_precision"],
            }
        )
    if not rows:
        raise ValueError("no calibrated policies to plot")
    df_chart = (
        pd.DataFrame(rows)
        .sort_values("n_nulls", ascending=True)
        .reset_index(drop=True)
    )
    if min_null_precision is None:
        min_null_precision = float(df_chart["min_null_precision"].iloc[0])

    n = len(df_chart)
    y = np.arange(n)
    fig, (ax_vol, ax_prec) = plt.subplots(
        1, 2, figsize=(14, max(4.5, 0.42 * n + 1.5)), sharey=True,
        gridspec_kw={"width_ratios": [1, 1]},
    )

    route_color = {"STP": "mediumseagreen", "HITL": "tomato"}
    bar_face = [route_color[r] for r in df_chart["null_route"]]

    ax_vol.barh(
        y, df_chart["n_nulls_gt_null"], color=bar_face, alpha=0.55,
    )
    ax_vol.barh(
        y, df_chart["n_null_errors"], left=df_chart["n_nulls_gt_null"],
        color=bar_face, alpha=1.0, hatch="//", edgecolor="black", lw=0.6,
    )
    max_nulls = max(int(df_chart["n_nulls"].max()), 1)
    for i, row in df_chart.iterrows():
        ax_vol.text(
            row["n_nulls"] + max_nulls * 0.01, i,
            f"{int(row['n_nulls'])}  → {row['null_route']}",
            va="center", fontsize=8.5,
        )
    ax_vol.set_yticks(y)
    ax_vol.set_yticklabels(df_chart["field"], fontsize=9)
    ax_vol.set_xlabel("Null extractions on this dataset (count)", fontsize=11)
    ax_vol.set_title("Null volume per field", fontsize=12)
    ax_vol.grid(axis="x", alpha=0.3)

    # Build a 2x2 legend showing both possible colors for each segment type.
    from matplotlib.patches import Patch
    vol_legend_handles = [
        Patch(facecolor=route_color["STP"], alpha=0.55,
              label="GT also null (correct null) — nulls → STP"),
        Patch(facecolor=route_color["HITL"], alpha=0.55,
              label="GT also null (correct null) — nulls → HITL"),
        Patch(facecolor=route_color["STP"], alpha=1.0, hatch="//",
              edgecolor="black", lw=0.6,
              label="GT non-null (null mis-extraction) — nulls → STP"),
        Patch(facecolor=route_color["HITL"], alpha=1.0, hatch="//",
              edgecolor="black", lw=0.6,
              label="GT non-null (null mis-extraction) — nulls → HITL"),
    ]
    ax_vol.legend(
        handles=vol_legend_handles,
        loc="upper center", bbox_to_anchor=(0.5, -0.12),
        ncol=2, fontsize=8.5, frameon=False,
    )

    has_prec = df_chart["null_precision"].notna()
    if has_prec.any():
        sub = df_chart.loc[has_prec]
        ax_prec.barh(
            y[has_prec.to_numpy()], sub["null_precision"],
            color=[route_color[r] for r in sub["null_route"]], alpha=0.85,
        )
        xerr_lo = (sub["null_precision"] - sub["ci_lower"]).to_numpy()
        xerr_hi = (sub["ci_upper"] - sub["null_precision"]).to_numpy()
        ax_prec.errorbar(
            sub["null_precision"], y[has_prec.to_numpy()],
            xerr=[xerr_lo, xerr_hi], fmt="none",
            color="black", capsize=3, lw=1.2,
        )
        for idx_pos, (_, row) in zip(y[has_prec.to_numpy()], sub.iterrows()):
            ax_prec.text(
                min(row["ci_upper"] + 0.01, 0.97), idx_pos,
                f"{row['null_precision']:.0%}", va="center", fontsize=8.5,
            )
    for idx_pos in y[(~has_prec).to_numpy()]:
        ax_prec.text(
            0.02, idx_pos, "no nulls observed → HITL",
            va="center", fontsize=8.5, color="gray", style="italic",
        )

    ax_prec.axvline(
        min_null_precision, color="navy", linestyle="--", lw=1.2,
    )
    ax_prec.set_xlim(0, 1.05)
    ax_prec.set_xlabel("P(GT null | extracted null)", fontsize=11)
    ax_prec.set_title("Null precision vs decision threshold", fontsize=12)
    ax_prec.grid(axis="x", alpha=0.3)

    from matplotlib.lines import Line2D
    prec_legend_handles = [
        Patch(facecolor=route_color["STP"], alpha=0.85,
              label="Nulls → STP (null-routing policy applied)"),
        Patch(facecolor=route_color["HITL"], alpha=0.85,
              label="Nulls → HITL (no null-routing policy)"),
        Line2D([0], [0], color="black", lw=1.2, label="95% Wilson CI"),
        Line2D([0], [0], color="navy", linestyle="--", lw=1.2,
               label=f"min_null_precision = {min_null_precision:.0%}"),
    ]
    ax_prec.legend(
        handles=prec_legend_handles,
        loc="upper center", bbox_to_anchor=(0.5, -0.12),
        ncol=2, fontsize=8.5, frameon=False,
    )

    fig.suptitle(
        "Null-routing policy results per field\n"
        "Green = null-routing policy applied (nulls → STP)   ·   "
        "Red = no null-routing policy (nulls → HITL)",
        fontsize=12, y=1.02,
    )
    plt.tight_layout()
    return fig


def plot_hitl_savings(
    policies: Mapping[str, dict],
    *,
    target_catch_rate: float | None = None,
) -> "plt.Figure":
    """Twin-panel HITL volume + savings vs the all-HITL baseline, per
    calibrated field. Also annotates the portfolio-level savings.

    Left: stacked HITL volume (non-null routed-to-HITL by the LR threshold +
    null routed-to-HITL by the null policy), with the all-HITL baseline
    overlaid as a dashed outline.
    Right: per-field HITL savings (1 − calibrated/baseline), with the
    portfolio savings drawn as a vertical reference line.
    """
    rows = []
    for name, pol in policies.items():
        if pol.get("decision") != "calibrate":
            continue
        np_ = pol["null_policy"]
        n_nonnull = int(pol["n"])
        n_nulls = int(np_["n_nulls"])
        total = n_nonnull + n_nulls
        nonnull_hitl = int(round(pol["hitl_load"] * n_nonnull))
        null_hitl = n_nulls if np_["decision"] in _NULL_TO_HITL_DECISIONS else 0
        calibrated_hitl = nonnull_hitl + null_hitl
        savings_pct = 1.0 - calibrated_hitl / total if total else float("nan")
        rows.append(
            {
                "field": name,
                "n_nonnull": n_nonnull,
                "n_nulls": n_nulls,
                "nonnull_hitl": nonnull_hitl,
                "null_hitl": null_hitl,
                "calibrated_hitl": calibrated_hitl,
                "baseline_hitl": total,
                "hitl_savings_pct": savings_pct,
                "target": pol["target_catch_rate"],
            }
        )
    if not rows:
        raise ValueError("no calibrated policies to plot")
    if target_catch_rate is None:
        target_catch_rate = float(rows[0]["target"])
    df_chart = (
        pd.DataFrame(rows)
        .sort_values("hitl_savings_pct", ascending=True)
        .reset_index(drop=True)
    )

    total_calibrated = int(df_chart["calibrated_hitl"].sum())
    total_baseline = int(df_chart["baseline_hitl"].sum())
    portfolio_savings = (
        1.0 - total_calibrated / total_baseline if total_baseline else float("nan")
    )

    n = len(df_chart)
    y = np.arange(n)
    fig, (ax_vol, ax_sav) = plt.subplots(
        1, 2, figsize=(14, max(4.5, 0.42 * n + 1.5)), sharey=True,
        gridspec_kw={"width_ratios": [2, 1]},
    )

    ax_vol.barh(
        y, df_chart["nonnull_hitl"], color="steelblue",
        label="Non-null → HITL (LR threshold)",
    )
    ax_vol.barh(
        y, df_chart["null_hitl"], left=df_chart["nonnull_hitl"],
        color="slategray", label="Null → HITL (null-policy)",
    )
    ax_vol.barh(
        y, df_chart["baseline_hitl"], facecolor="none",
        edgecolor="tomato", lw=1.4, linestyle="--",
        label="Baseline: route 100% to HITL",
    )
    max_baseline = max(int(df_chart["baseline_hitl"].max()), 1)
    for i, row in df_chart.iterrows():
        ax_vol.text(
            row["baseline_hitl"] + max_baseline * 0.01, i,
            f"{int(row['calibrated_hitl']):,} / {int(row['baseline_hitl']):,}",
            va="center", fontsize=8.5,
        )
    ax_vol.set_yticks(y)
    ax_vol.set_yticklabels(df_chart["field"], fontsize=9)
    ax_vol.set_xlabel("HITL routings on this dataset (count)", fontsize=11)
    ax_vol.set_title("Calibrated HITL volume vs all-HITL baseline", fontsize=12)
    ax_vol.grid(axis="x", alpha=0.3)
    ax_vol.legend(loc="lower right", fontsize=9)

    ax_sav.barh(y, df_chart["hitl_savings_pct"], color="mediumseagreen", alpha=0.9)
    for i, v in enumerate(df_chart["hitl_savings_pct"]):
        ax_sav.text(v + 0.005, i, f"{v:.0%}", va="center", fontsize=9)
    ax_sav.axvline(
        portfolio_savings, color="navy", linestyle="--", lw=1.2,
        label=f"Portfolio savings = {portfolio_savings:.0%}",
    )
    ax_sav.set_xlim(0, 1.05)
    ax_sav.set_xlabel("HITL savings vs all-HITL", fontsize=11)
    ax_sav.set_title("Savings per field", fontsize=12)
    ax_sav.grid(axis="x", alpha=0.3)
    ax_sav.legend(loc="lower right", fontsize=9)

    fig.suptitle(
        f"HITL volume & savings — target catch rate {target_catch_rate:.0%}\n"
        "(includes both non-null calibrated routings and null-policy routings)",
        fontsize=13, y=1.02,
    )
    plt.tight_layout()
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Portfolio-level savings estimate
# ─────────────────────────────────────────────────────────────────────────────


def estimate_hitl_savings(
    df_full: pd.DataFrame,
    policies: Mapping[str, dict],
    metadata: FormMetadata,
) -> dict:
    """Estimate the OOF-honest HITL load (and savings vs an all-HITL
    baseline) for the **entire form**, not just the calibrated fields.

    Every field present in ``df_full`` is bucketed and its expected HITL
    routings counted:

      * **calibrate**      → non-null HITL = ``hitl_load × n_nonnull``
                              (OOF estimate from the policy);
                              null HITL governed by the null-policy.
      * **always_trust**   → 0 non-null HITL; null HITL governed by the
                              null-policy.
      * everything else    → 100% HITL (always_review,
                              insufficient_data, no_policy).

    The non-null ``hitl_load`` figure is the **out-of-fold** estimate from
    5-fold CV inside :func:`build_routing_policy`, so the resulting
    portfolio savings is an honest forecast — *not* an in-sample
    optimistic number.

    Parameters
    ----------
    df_full : the unfiltered comparison frame used to fit the policies
        (must contain ``field_name`` and ``extracted_value``). The row
        counts here define the field volume per form.
    policies : ``{field_name: policy_dict}`` from
        :func:`build_routing_policies`.
    metadata : ``FormMetadata`` — currently unused but accepted for API
        symmetry with the rest of the module.

    Returns
    -------
    dict with keys:
        per_field : DataFrame, one row per field in ``df_full`` with
            columns: field, bucket, n_total, n_nonnull, n_nulls,
            null_savings, lr_savings, expected_hitl, baseline_hitl,
            hitl_savings_pct. ``null_savings + lr_savings + expected_hitl
            == baseline_hitl`` for every row.
        portfolio : dict with n_total, expected_hitl, baseline_hitl,
            null_savings, lr_savings, null_savings_pct, lr_savings_pct,
            hitl_load, hitl_savings_pct, plus per-bucket field counts.
            ``null_savings_pct + lr_savings_pct + hitl_load == 1.0``.
    """
    del metadata  # accepted for API symmetry; not consulted here.
    rows: list[dict] = []

    for field_name in sorted(df_full["field_name"].dropna().unique()):
        sub = df_full[df_full["field_name"] == field_name]
        is_null = sub["extracted_value"].apply(_is_null_value).to_numpy()
        n_total = int(len(sub))
        n_nulls = int(is_null.sum())
        n_nonnull = n_total - n_nulls

        pol = policies.get(field_name)

        # Per-track savings: count of routings the policy diverts to STP
        # vs the all-HITL baseline. ``null_savings`` comes from the null
        # track, ``lr_savings`` comes from the non-null track.
        null_savings = 0
        lr_savings = 0

        if pol is None:
            bucket = "no_policy"
            expected_hitl = n_total
        else:
            decision = pol.get("decision")
            null_to_hitl = pol["null_policy"]["decision"] in _NULL_TO_HITL_DECISIONS
            null_hitl = n_nulls if null_to_hitl else 0
            null_savings = n_nulls - null_hitl  # nulls routed to STP
            if decision == "calibrate":
                bucket = "calibrate"
                # hitl_load is the OOF non-null HITL fraction for this field.
                nonnull_hitl = int(round(float(pol["hitl_load"]) * n_nonnull))
                lr_savings = n_nonnull - nonnull_hitl
                expected_hitl = nonnull_hitl + null_hitl
            elif decision == "always_trust":
                bucket = "always_trust"
                lr_savings = n_nonnull
                expected_hitl = null_hitl
            else:
                # always_review, insufficient_data, etc.: non-null → HITL.
                bucket = decision or "no_policy"
                expected_hitl = n_nonnull + null_hitl

        baseline_hitl = n_total
        savings_pct = (
            1.0 - expected_hitl / baseline_hitl if baseline_hitl else float("nan")
        )
        rows.append(
            {
                "field":            field_name,
                "bucket":           bucket,
                "n_total":          n_total,
                "n_nonnull":        n_nonnull,
                "n_nulls":          n_nulls,
                "null_savings":     int(null_savings),
                "lr_savings":       int(lr_savings),
                "expected_hitl":    int(expected_hitl),
                "baseline_hitl":    int(baseline_hitl),
                "hitl_savings_pct": float(savings_pct),
            }
        )

    per_field = pd.DataFrame(rows)

    total_baseline = int(per_field["baseline_hitl"].sum())
    total_expected = int(per_field["expected_hitl"].sum())
    total_null_savings = int(per_field["null_savings"].sum())
    total_lr_savings = int(per_field["lr_savings"].sum())
    portfolio_savings = (
        1.0 - total_expected / total_baseline if total_baseline else float("nan")
    )
    portfolio_hitl_load = (
        total_expected / total_baseline if total_baseline else float("nan")
    )

    bucket_counts = per_field["bucket"].value_counts().to_dict()
    portfolio = {
        "n_total":                total_baseline,
        "expected_hitl":          total_expected,
        "baseline_hitl":          total_baseline,
        "null_savings":           total_null_savings,
        "lr_savings":             total_lr_savings,
        "null_savings_pct":       (
            total_null_savings / total_baseline if total_baseline else float("nan")
        ),
        "lr_savings_pct":         (
            total_lr_savings / total_baseline if total_baseline else float("nan")
        ),
        "hitl_load":              float(portfolio_hitl_load),
        "hitl_savings_pct":       float(portfolio_savings),
        "n_calibrated_fields":    int(bucket_counts.get("calibrate", 0)),
        "n_always_trust_fields":  int(bucket_counts.get("always_trust", 0)),
        "n_always_review_fields": int(bucket_counts.get("always_review", 0)),
        "n_no_policy_fields":     int(bucket_counts.get("no_policy", 0)),
    }

    return {"per_field": per_field, "portfolio": portfolio}


def plot_savings_attribution(
    savings: Mapping,
    *,
    sort_by: str = "total_savings",
) -> "plt.Figure":
    """Stacked-bar attribution of HITL savings into null-track vs
    non-null (LR) track contributions.

    Each per-field bar spans the full all-HITL baseline. The bar is
    segmented into three pieces summing to ``baseline_hitl``:

      * **Retained HITL** (red)     — routings that still need review.
      * **Null → STP** (blue)        — savings from the null-track
                                       (``null_savings``).
      * **Non-null → STP** (green)   — savings from the non-null LR/
                                       always_trust track (``lr_savings``).

    A portfolio-total bar is shown at the top, normalized to the same
    width as the per-field bars (each per-field bar is normalized to its
    own baseline so all bars line up at 100%).

    Parameters
    ----------
    savings : the return value of :func:`estimate_hitl_savings`.
    sort_by : ``'total_savings'`` (default), ``'null_savings'``,
        ``'lr_savings'``, ``'baseline'``, or ``'field'``.
    """
    per_field = savings["per_field"].copy()
    portfolio = savings["portfolio"]

    if per_field.empty:
        raise ValueError("savings['per_field'] is empty")

    # Normalize each row to its own baseline so all bars span [0, 1].
    per_field["null_pct"] = per_field["null_savings"] / per_field["baseline_hitl"]
    per_field["lr_pct"] = per_field["lr_savings"] / per_field["baseline_hitl"]
    per_field["retained_pct"] = (
        per_field["expected_hitl"] / per_field["baseline_hitl"]
    )

    if sort_by == "total_savings":
        per_field = per_field.sort_values("hitl_savings_pct", ascending=False)
    elif sort_by == "null_savings":
        per_field = per_field.sort_values("null_pct", ascending=False)
    elif sort_by == "lr_savings":
        per_field = per_field.sort_values("lr_pct", ascending=False)
    elif sort_by == "baseline":
        per_field = per_field.sort_values("baseline_hitl", ascending=False)
    elif sort_by == "field":
        per_field = per_field.sort_values("field", ascending=True)
    else:
        raise ValueError(f"unknown sort_by={sort_by!r}")
    per_field = per_field.reset_index(drop=True)

    n_fields = len(per_field)
    # +2 rows: spacer + portfolio total at the top.
    fig, ax = plt.subplots(figsize=(12, max(4.5, 0.42 * n_fields + 2.0)))

    color_retained = "tomato"
    color_null = "steelblue"
    color_lr = "mediumseagreen"

    # ── Per-field bars ───────────────────────────────────────────────────────
    y = np.arange(n_fields)
    ax.barh(y, per_field["retained_pct"], color=color_retained,
            label="Retained HITL")
    ax.barh(y, per_field["null_pct"], left=per_field["retained_pct"],
            color=color_null, label="Null → STP (null-policy)")
    ax.barh(
        y, per_field["lr_pct"],
        left=per_field["retained_pct"] + per_field["null_pct"],
        color=color_lr, label="Non-null → STP (LR / always-trust)",
    )

    for i, row in per_field.iterrows():
        ax.text(
            1.01, i,
            f"  {row['hitl_savings_pct']:.0%} saved  "
            f"(n={int(row['baseline_hitl']):,}, {row['bucket']})",
            va="center", fontsize=8.5,
        )
        # Inline segment labels when wide enough to read.
        if row["null_pct"] >= 0.06:
            ax.text(
                row["retained_pct"] + row["null_pct"] / 2, i,
                f"{row['null_pct']:.0%}",
                ha="center", va="center", fontsize=8, color="white",
            )
        if row["lr_pct"] >= 0.06:
            ax.text(
                row["retained_pct"] + row["null_pct"] + row["lr_pct"] / 2, i,
                f"{row['lr_pct']:.0%}",
                ha="center", va="center", fontsize=8, color="white",
            )

    # ── Portfolio total bar ──────────────────────────────────────────────────
    port_y = n_fields + 1.0
    port_retained = portfolio["hitl_load"]
    port_null = portfolio["null_savings_pct"]
    port_lr = portfolio["lr_savings_pct"]
    ax.barh(port_y, port_retained, color=color_retained,
            edgecolor="black", lw=1.2)
    ax.barh(port_y, port_null, left=port_retained, color=color_null,
            edgecolor="black", lw=1.2)
    ax.barh(port_y, port_lr, left=port_retained + port_null, color=color_lr,
            edgecolor="black", lw=1.2)
    ax.text(
        1.01, port_y,
        f"  {portfolio['hitl_savings_pct']:.0%} saved  "
        f"(n={portfolio['baseline_hitl']:,}, portfolio)",
        va="center", fontsize=9.5, fontweight="bold",
    )
    if port_null >= 0.04:
        ax.text(port_retained + port_null / 2, port_y,
                f"{port_null:.0%}", ha="center", va="center",
                fontsize=9, color="white", fontweight="bold")
    if port_lr >= 0.04:
        ax.text(port_retained + port_null + port_lr / 2, port_y,
                f"{port_lr:.0%}", ha="center", va="center",
                fontsize=9, color="white", fontweight="bold")

    ax.set_yticks(list(y) + [port_y])
    ax.set_yticklabels(
        list(per_field["field"]) + ["PORTFOLIO TOTAL"],
        fontsize=9,
    )
    ax.set_xlim(0, 1.30)
    ax.set_xticks(np.linspace(0, 1.0, 6))
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.set_xlabel(
        "Fraction of all-HITL baseline (per-field rows normalized to own baseline)",
        fontsize=11,
    )
    ax.set_title(
        f"HITL savings attribution — portfolio savings = "
        f"{portfolio['hitl_savings_pct']:.1%}  "
        f"(null-track {portfolio['null_savings_pct']:.1%} + "
        f"non-null-track {portfolio['lr_savings_pct']:.1%})",
        fontsize=12,
    )
    ax.grid(axis="x", alpha=0.3)
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.08),
        ncol=3,
        fontsize=9,
        frameon=False,
    )
    ax.invert_yaxis()
    plt.tight_layout()
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Coverage-target sweep
# ─────────────────────────────────────────────────────────────────────────────


def sweep_target_savings(
    df_full: pd.DataFrame,
    policies: Mapping[str, Mapping],
    *,
    metadata: FormMetadata,
    start: float = 0.50,
    end: float = 0.95,
    step: float = 0.05,
    base_config: CalibrationConfig | None = None,
) -> pd.DataFrame:
    """Sweep the coverage target c from ``start`` to ``end`` (inclusive) in
    increments of ``step``, applying ``c`` to both ``target_catch_rate`` and
    ``min_null_precision`` at every step. Reuses the per-field signal cache
    attached to ``policies`` (built once by :func:`build_routing_policies`)
    so the LR fit and AUC bootstrap are not re-run.

    Returns one row per target with portfolio-level savings broken down
    into null-track and non-null (LR/always-trust) contributions.

    Columns
    -------
    target, hitl_load, hitl_savings_pct,
    null_savings_pct, lr_savings_pct,
    expected_hitl, baseline_hitl,
    null_savings, lr_savings,
    n_calibrated_fields,
    n_always_review_fields, n_always_trust_fields, n_no_policy_fields
    """
    if step <= 0:
        raise ValueError(f"step must be > 0, got {step}")
    if end < start:
        raise ValueError(f"end ({end}) must be >= start ({start})")
    base_cfg = base_config or CalibrationConfig()

    # Build target list inclusive of `end` (with float tolerance).
    n_steps = int(round((end - start) / step)) + 1
    targets = [round(start + i * step, 10) for i in range(n_steps)]
    targets = [t for t in targets if t <= end + 1e-9]

    rows = []
    for c in targets:
        cfg = replace(base_cfg, target_catch_rate=c, min_null_precision=c)
        new_policies = redecide_policies(policies, config=cfg)
        savings = estimate_hitl_savings(df_full, new_policies, metadata)
        p = savings["portfolio"]
        rows.append(
            {
                "target": c,
                "hitl_load":              p["hitl_load"],
                "hitl_savings_pct":       p["hitl_savings_pct"],
                "null_savings_pct":       p["null_savings_pct"],
                "lr_savings_pct":         p["lr_savings_pct"],
                "expected_hitl":          p["expected_hitl"],
                "baseline_hitl":          p["baseline_hitl"],
                "null_savings":           p["null_savings"],
                "lr_savings":             p["lr_savings"],
                "n_calibrated_fields":    p["n_calibrated_fields"],
                "n_always_review_fields": p["n_always_review_fields"],
                "n_always_trust_fields":  p["n_always_trust_fields"],
                "n_no_policy_fields":     p["n_no_policy_fields"],
            }
        )
    return pd.DataFrame(rows)


def plot_target_sweep(
    df_sweep: pd.DataFrame,
    *,
    ax: "plt.Axes | None" = None,
) -> "plt.Axes":
    """Plot the output of :func:`sweep_target_savings` — three lines
    (total / null-track / non-null LR-track) over the swept target."""
    if df_sweep.empty:
        raise ValueError("df_sweep is empty")

    if ax is None:
        _, ax = plt.subplots(figsize=(11, 5.5))

    x = df_sweep["target"].to_numpy()
    series = [
        ("hitl_savings_pct", "Total portfolio savings",       "navy",            "o"),
        ("null_savings_pct", "Null-track savings",            "steelblue",       "s"),
        ("lr_savings_pct",   "Non-null (LR) calibration savings", "mediumseagreen", "^"),
    ]
    for col, label, color, marker in series:
        y = df_sweep[col].to_numpy()
        ax.plot(x, y, marker=marker, color=color, lw=2.0, label=label)
        for xi, yi in zip(x, y):
            if pd.notna(yi):
                ax.annotate(
                    f"{yi:.0%}", xy=(xi, yi), xytext=(0, 6),
                    textcoords="offset points",
                    ha="center", fontsize=8.5, color=color, fontweight="bold",
                )

    y_max = max(0.55, float(df_sweep["hitl_savings_pct"].max()) + 0.10)
    ax.set_xlim(min(x) - 0.01, max(x) + 0.01)
    ax.set_ylim(0, y_max)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{t:.0%}" for t in x])
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.set_xlabel(
        "Coverage target  (applied to both target_catch_rate and min_null_precision)",
        fontsize=11,
    )
    ax.set_ylabel("Portfolio HITL savings vs all-HITL baseline", fontsize=11)
    ax.set_title(
        "HITL savings vs coverage target — null-track vs non-null LR-track contributions",
        fontsize=12,
    )
    ax.grid(alpha=0.3)
    ax.legend(
        loc="upper center", bbox_to_anchor=(0.5, -0.12),
        ncol=3, fontsize=9, frameon=False,
    )
    plt.tight_layout()
    return ax
