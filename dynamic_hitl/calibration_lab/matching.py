"""Decide whether an extracted value matches ground truth.

The calibration never compares extractions to ground truth itself -- it consumes
the ``is_correct`` column and calibrates against it. This module produces that
column: **exact match after normalization**, so that cosmetic differences
(currency symbols, casing, stray whitespace, thousands separators) are not
counted as extraction mistakes.

These are the rules that produced ``is_correct`` for the bundled receipts, and
running :func:`add_is_correct` over that dataset reproduces every one of its
13,853 labels. Normalization is not cosmetic there: it decides 2.4% of the
verdicts, mostly quantities where ground truth reads ``1 x`` and the extraction
reads ``1 X`` or ``1 ×``. For strict string equality instead, pass a normalizer
that only handles blanks::

    matching.add_is_correct(
        data, normalizer=lambda v, field: None if matching.is_null(v) else str(v)
    )

Typical use, once you have a frame of extractions paired with ground truth::

    import matching

    data = matching.add_is_correct(data)

Which normalizer runs is chosen per field, by looking for tokens in the field
name (see :data:`FIELD_RULES`). Adapt those rules -- or pass your own
``normalizer`` -- so the definition of "correct" here is the same one your
business already uses. Everything downstream inherits it: too strict and the
calibration chases mistakes that were never mistakes, too loose and it certifies
real ones as correct.
"""

from __future__ import annotations

import math
import re
import unicodedata
from decimal import Decimal, InvalidOperation
from typing import Any, Callable

import pandas as pd


Normalizer = Callable[[Any], str | None]


def is_null(value: Any) -> bool:
    """True when a value counts as "nothing was extracted"."""
    if value is None:
        return True
    if isinstance(value, float):
        return math.isnan(value)
    if isinstance(value, str):
        return not value.strip()
    return False


def normalize_text(value: Any) -> str | None:
    """Case-fold, collapse whitespace, and apply Unicode NFKC."""
    if is_null(value):
        return None
    text = unicodedata.normalize("NFKC", str(value)).casefold()
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def normalize_quantity(value: Any) -> str | None:
    """Pull the leading number out of values like ``"1 x"`` or ``"x2"``."""
    text = normalize_text(value)
    if text is None:
        return None
    match = re.search(r"[-+]?\d+(?:[.,]\d+)?", text)
    if not match:
        return text
    number = match.group(0).replace(",", ".")
    try:
        quantity = Decimal(number)
    except InvalidOperation:
        return text
    return format(quantity.normalize(), "f")


def normalize_money(value: Any) -> str | None:
    """Strip currency symbols and separators down to a comparable number.

    Handles both decimal conventions (``1.234,56`` and ``1,234.56``) and treats
    a leading ``-`` or surrounding parentheses as negative.
    """
    text = normalize_text(value)
    if text is None:
        return None
    negative = text.startswith("-") or (text.startswith("(") and text.endswith(")"))
    cleaned = re.sub(r"[^\d,.\-]", "", text)
    if not cleaned:
        return text
    cleaned = cleaned.replace("-", "")
    if "," in cleaned and "." in cleaned:
        # Whichever separator comes last is the decimal point.
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif cleaned.count(",") > 1:
        cleaned = cleaned.replace(",", "")
    elif cleaned.count(".") > 1:
        cleaned = cleaned.replace(".", "")
    elif "," in cleaned:
        tail = cleaned.rsplit(",", 1)[1]
        cleaned = (
            cleaned.replace(",", ".")
            if len(tail) in (1, 2)
            else cleaned.replace(",", "")
        )
    try:
        amount = Decimal(cleaned)
    except InvalidOperation:
        return text
    if negative:
        amount = -amount
    return format(amount.normalize(), "f")


# Tokens searched for in the field name, in order, to pick a normalizer.
# Extend this for your own schema -- dates, account numbers, postcodes, and
# similar domain formats belong here rather than in the calibration.
FIELD_RULES: tuple[tuple[tuple[str, ...], Normalizer], ...] = (
    (("price", "total", "tax", "service", "amount"), normalize_money),
    (("quantity", ".cnt", "_count"), normalize_quantity),
)

DEFAULT_NORMALIZER: Normalizer = normalize_text


def normalizer_for(field_name: str) -> Normalizer:
    """The normalizer that :func:`normalize_value` would use for a field."""
    lower = str(field_name).casefold()
    for tokens, normalizer in FIELD_RULES:
        if any(token in lower for token in tokens):
            return normalizer
    return DEFAULT_NORMALIZER


def normalize_value(value: Any, field_name: str) -> str | None:
    """Normalize one value the way its field expects."""
    return normalizer_for(field_name)(value)


def values_match(ground_truth: Any, extracted: Any, field_name: str) -> bool:
    """Whether an extraction should count as correct for this field.

    Two blanks match: when the extraction is empty and ground truth is empty
    too, the model was right to return nothing. That is the quantity the blank
    routing track is calibrated on.
    """
    return normalize_value(ground_truth, field_name) == normalize_value(
        extracted, field_name
    )


def add_is_correct(
    frame: pd.DataFrame,
    *,
    ground_truth_column: str = "ground_truth_value",
    extracted_column: str = "extracted_value",
    field_column: str = "field_name",
    normalizer: Callable[[Any, str], str | None] | None = None,
) -> pd.DataFrame:
    """Return a copy of ``frame`` with an ``is_correct`` column filled in.

    Pass ``normalizer`` -- any ``(value, field_name) -> comparable`` callable --
    to swap in your own matching rules wholesale.
    """
    missing = [
        column
        for column in (ground_truth_column, extracted_column, field_column)
        if column not in frame.columns
    ]
    if missing:
        raise KeyError(f"frame is missing required columns: {missing}")

    normalize = normalizer or normalize_value
    result = frame.copy()
    result["is_correct"] = [
        normalize(ground_truth, field) == normalize(extracted, field)
        for ground_truth, extracted, field in zip(
            result[ground_truth_column],
            result[extracted_column],
            result[field_column],
        )
    ]
    return result
