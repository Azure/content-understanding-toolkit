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
python -m pip install -e "./packages/core[dev]"
python -m pip install -e "./packages/standalone[dev]"
python -m pip install -e "./packages/azure-cli-extension[dev]"
```

### Build and install the Azure CLI extension locally

The extension depends on the shared core package. Build both wheels, then expose
the core wheel to Azure CLI's package installer while installing the extension:

```bash
cd packages/core
python -m build --wheel

cd ../azure-cli-extension
python -m build --wheel

az extension remove --name content-understanding 2>/dev/null || true
PIP_FIND_LINKS="$(pwd)/../core/dist" \
	az extension add --source dist/content_understanding-*.whl --yes

az cu --help
```

In PowerShell, set `$env:PIP_FIND_LINKS = (Resolve-Path ../core/dist)` before
running `az extension add`.

Before releasing the extension, validate the built wheels in a clean Azure CLI
environment. This check installs only dependencies resolved from the wheels and
loads the command group with `az cu --help`:

```bash
cd ../..
bash scripts/validate_extension_wheel.sh \
	packages/azure-cli-extension/dist/content_understanding-*.whl \
	packages/core/dist/cu_cli_core-*.whl
```

Run the Azure CLI extensions linter before publishing. This clones clean,
temporary copies of the Azure CLI `dev` branch and the extensions repository,
then runs the same pinned `azdev` wheel linter used by their pipeline:

```bash
bash scripts/validate_extension_azdev.sh \
	packages/azure-cli-extension/dist/content_understanding-*.whl \
	packages/core/dist/cu_cli_core-*.whl \
	packages/azure-cli-extension
```

The clean wheel installation and pinned `azdev` checks run automatically in
both `.github/workflows/ci.yml` for pull requests and
`.github/workflows/release.yml` before an extension artifact is published.

## Running checks

```bash
bash scripts/ci.sh
```

Run this from `cu-cli` using the activated development environment. It is the
canonical build, lint, type-check, unit-test, and offline-playback entry point.
On Windows, use a Bash installation and a Git checkout that preserves symbolic
links. A package README checked out as a plain text link target correctly fails
the symlink test; do not disable that test.

### Running tests

```bash
# Standalone unit tests
python -m pytest -c packages/standalone/pyproject.toml -m unit packages/standalone/tests/unit

# Cloud command tests in offline playback mode (default)
python -m pytest -c packages/standalone/pyproject.toml -m integration packages/standalone/tests/integration

# Live run against your endpoint with API key auth
CU_TEST_REC_MODE=live CU_TEST_REC_ENDPOINT=https://<res>.services.ai.azure.com/ \
	CU_TEST_REC_KEY=<key> python -m pytest -c packages/standalone/pyproject.toml -m integration packages/standalone/tests/integration

# Live run with Entra auth (after az login)
CU_TEST_REC_MODE=live CU_TEST_REC_ENDPOINT=https://<res>.services.ai.azure.com/ \
	CU_TEST_REC_AUTH=entra python -m pytest -c packages/standalone/pyproject.toml -m integration packages/standalone/tests/integration

# Refresh sanitized recordings from a live endpoint
CU_TEST_REC_MODE=record CU_TEST_REC_ENDPOINT=https://<res>.services.ai.azure.com/ \
	CU_TEST_REC_KEY=<key> python -m pytest -c packages/standalone/pyproject.toml -m integration packages/standalone/tests/integration
```

Environment variables used by cloud-gated tests:

- `CU_TEST_REC_MODE`: `playback` (default), `record`, or `live`
- `CU_TEST_REC_ENDPOINT`: endpoint URL, required for `record` and `live`
- `CU_TEST_REC_AUTH`: `key` or `entra`
- `CU_TEST_REC_KEY`: required when using key auth

Schema validation, template generation, and local profile operations are offline.
Sample-based schema generation, defaults synchronization, and live deployment
inspection use service boundaries; test those with mocks or sanitized recordings.
Add or update tests for every behavior change.

### Generate public documentation from tests

Every code block in [README.md](README.md) and [docs/usage-guide.md](docs/usage-guide.md)
comes from one documentation test file per document:

| Document | Documentation test |
| --- | --- |
| `README.md` | [tests/docs/test_readme.py](packages/standalone/tests/docs/test_readme.py) |
| `docs/usage-guide.md` | [tests/docs/test_usage_guide.py](packages/standalone/tests/docs/test_usage_guide.py) |

The tests follow the order of their document. Each code block is a named region
that contains only the commands to publish. Run each command with the file's
`_run` helper, and put its assertions directly after `# endregion`:

```python
with use_cassette("defaults_get"):
    # region Snippet:defaults_show
    result = _run(
        "defaults", "show",
        comment="Show the Content Understanding defaults configured on the resource.",
    )
    # endregion
assert json.loads(result.stdout)["modelDeployments"]
```

The region name is the document marker. The block after
`<!-- Snippet:defaults_show -->` receives the command that the region ran:

```bash
# Show the Content Understanding defaults configured on the resource.
cu defaults show
```

For a block with several commands, give each command its own nested step region
and assert after each step:

```python
# region Snippet:configure_key
# region Snippet:key_endpoint
_run(
    "profile", "set", "endpoint", "https://<resource-name>.services.ai.azure.com/",
    placeholder_values={"resource-name": "sanitized"},
    comment="Save the endpoint on the active profile.",
)
# endregion
assert ProfileStore.load().get("endpoint") == PLACEHOLDER_ENDPOINT
# region Snippet:profile_key
_run(
    "profile", "set", "api_key", "<key>",
    placeholder_values={"key": "playback-dummy-key"},
    comment="Save a resource key on the active profile and select key authentication.",
)
# endregion
assert ProfileStore.load().get("auth_mode") == "key"
# endregion
```

The outer region publishes all of its commands in execution order. Step regions
only structure the test, so the document does not need to reference them. Write
only assertions between step regions: a command called there is also published.
Run additional verification commands after the outer region.

- Use semantic `snake_case` names without a `test_` prefix. Names are unique
  within a documentation test; both documents can use the same name.
- Put markers on their own lines, with matching indentation, inside a top-level
  test function. A region cannot split a call. Prepare files, profiles, and
  service doubles before the region.
- `comment="..."` becomes shell comment lines before the command; separate lines
  with `\n`. Python comments are not published.
- Keep resource-specific values as placeholders, such as
  `https://<resource-name>.services.ai.azure.com/`, and pass `placeholder_values`.
  The test runs the bound value, and the document keeps the placeholder. The same
  bindings apply to string values in an `env` mapping. Missing or unused bindings
  fail before the command runs.
- Pass `language="powershell"` to render a PowerShell block. Use
  `record_output(content, language=...)` in its own region for an output block,
  `invoke_azure` through `_az` for Azure CLI examples, and `record_external(...,
  reason=...)` only for installation and interactive sign-in, which tests never
  run.

Use the complete repository sample (the `sample_invoice` and `copy_invoice`
fixtures) and sanitized recordings (`use_cassette`) for successful examples. Use
service doubles only where no recording exists, and do not present them as real
service results. The [recording data notes](packages/standalone/tests/integration/recordings/README.md#sample-data-and-gaps)
list the available data and the remaining gaps. Keep secrets in local
configuration, not in tests, recordings, documents, or chat.

Documentation tests run offline. Generation forces playback, a network
connection fails the test, and a skipped test fails. A test publishes its regions
only when its setup, call, and teardown pass, and every region must publish.
Snippet regions are allowed only in the two documentation tests.

Keep headings and longer descriptions outside the marked code blocks. Updates
replace only the block contents and preserve the surrounding prose. Keep each
marker and its block at the document's top level; code fences inside lists or
block quotes are rejected.

After changing a documentation test, regenerate the documents and then run the
read-only check:

```bash
python scripts/update-snippet.py update
python scripts/update-snippet.py check
```

Both commands run the documentation tests. `update` validates both documents
before writing either. `check` never writes and fails on code-block drift,
unmarked blocks, markers without regions, regions that the document does not use,
language mismatches, and failing or skipped tests. PR CI runs `check`.

Documentation test fixtures render Rich help and CLI output without terminal
styling at a fixed width, independent of the host terminal. Windows CI enables
symbolic links before checkout, so the package README is validated as a real link
rather than silently skipping the check.

## Pull requests

- Keep changes focused and include tests.
- Ensure `pytest`, `ruff`, and `mypy` pass before requesting review.
- Reference the related issue in your PR description.

## Trademarks

This project may contain trademarks or logos for projects, products, or services.
Authorized use of Microsoft trademarks or logos is subject to and must follow
[Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must not
cause confusion or imply Microsoft sponsorship. Any use of third-party trademarks or
logos is subject to those third parties' policies.
