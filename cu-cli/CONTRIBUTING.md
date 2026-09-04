# Contributing to cu-cli

Thank you for your interest in contributing! This project welcomes contributions
and suggestions.

## Contributor License Agreement

Most contributions require you to agree to a Contributor License Agreement (CLA)
declaring that you have the right to, and actually do, grant us the rights to use
your contribution. For details, visit <https://cla.opensource.microsoft.com>.

When you submit a pull request, a CLA bot will automatically determine whether you
need to provide a CLA and decorate the PR appropriately (e.g., status check,
comment). Simply follow the instructions provided by the bot. You will only need to
do this once across all repos using our CLA.

This project follows the repository-wide
[Microsoft Open Source Code of Conduct](../CODE_OF_CONDUCT.md).

## Development setup

```bash
git clone https://github.com/Azure/content-understanding-toolkit
cd content-understanding-toolkit/cu-cli
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Running checks

```bash
pytest            # unit + CLI tests (offline; no Azure calls)
ruff check .      # lint
mypy src          # type check
```

### Running tests

```bash
# Full local suite
pytest

# Cloud command tests in offline playback mode (default)
pytest -q tests/test_cloud_playback.py

# Live run against your endpoint with API key auth
CU_TEST_REC_MODE=live CU_TEST_REC_ENDPOINT=https://<res>.services.ai.azure.com/ \
	CU_TEST_REC_KEY=<key> pytest -q tests/test_cloud_playback.py

# Live run with Entra auth (after az login)
CU_TEST_REC_MODE=live CU_TEST_REC_ENDPOINT=https://<res>.services.ai.azure.com/ \
	CU_TEST_REC_AUTH=entra pytest -q tests/test_cloud_playback.py

# Refresh sanitized recordings from a live endpoint
CU_TEST_REC_MODE=record CU_TEST_REC_ENDPOINT=https://<res>.services.ai.azure.com/ \
	CU_TEST_REC_KEY=<key> pytest -q tests/test_cloud_playback.py
```

Environment variables used by cloud-gated tests:

- `CU_TEST_REC_MODE`: `playback` (default), `record`, or `live`
- `CU_TEST_REC_ENDPOINT`: endpoint URL, required for `record` and `live`
- `CU_TEST_REC_AUTH`: `key` or `entra`
- `CU_TEST_REC_KEY`: required when using key auth

The `analyzer validate`, `analyzer schema create`, and `profile` commands are
fully offline, so most
tests run without any Azure resource. Please add or update tests for any behavior you
change, and keep the deterministic (no-LLM) contract of the CLI intact.

## Pull requests

- Keep changes focused and include tests.
- Ensure `pytest`, `ruff`, and `mypy` pass before requesting review.
- Reference the related issue in your PR description.

Maintainers should follow [RELEASING.md](RELEASING.md) for approval-gated PyPI
publishing.

## Trademarks

This project may contain trademarks or logos for projects, products, or services.
Authorized use of Microsoft trademarks or logos is subject to and must follow
[Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must not
cause confusion or imply Microsoft sponsorship. Any use of third-party trademarks or
logos is subject to those third parties' policies.
