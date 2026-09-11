# Release History

## 0.1.0 (2026-09-09)

### Features Added

- Initial release of the Dynamic HITL tool for turning Content Understanding confidence scores into a per-field human-review policy.
- Added `calibration_lab/` with the calibration library, a five-step notebook (`run_calibration.ipynb`), and a bundled dataset of measured Content Understanding results for 1,000 [CORD v2](https://huggingface.co/datasets/naver-clova-ix/cord-v2) receipts; no Azure credentials are needed to run it.
- Added per-field policy fitting that measures each field separately, splits blank values from filled-in values, and selects cutoffs from a single business dial — the share of known mistakes that human review must catch.
- Added a portable calibration table (one CSV row per field) that can be saved, reloaded, and used to route unseen documents with a dictionary lookup and a comparison; no model is served at inference time.
- Added conservative routing fallbacks so that unknown fields and values with no confidence score are always sent to human review.
- Added savings attribution and held-out coverage tracking to forecast review load and verify that the dial holds on documents the policy never saw.
- Added `web_app/` — an interactive static site with six scrolling sections that explains the method and its payoff, driven by numbers precomputed from the calibration lab so the site and the implementation cannot drift apart.
- Added `calibration_lab/test_calibration.py`, covering the claims the README makes and the routing fallbacks, wired into CI to run when files under `dynamic_hitl/` change.
