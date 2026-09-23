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

Tests are the only source of executable examples in [README.md](README.md) and
[docs/usage-guide.md](docs/usage-guide.md). Neither document defines the command
coverage target: use the actual Click command tree, shared argument metadata,
and the command contracts, including aliases, boundaries, dependencies, mutual
exclusions, and configuration precedence.

Keep command arguments in the owning test and execute them with
`support.command_catalog.invoke_cli` through its existing `_run` helper. Mark
the calls to publish with a named region inside a top-level test function:

```python
# region Snippet:analyze_layout
result = _run("analyze", "sample_invoice.pdf", "-a", "prebuilt-layout")
# endregion
assert result.exit_code == 0, result.output
```

The region name maps directly to the document's `Snippet` marker. Use a stable
semantic name, not a `test_` function name or a document-specific number. Markers
must be standalone comments with matching indentation. Missing closing markers,
duplicate names, regions outside tests, and boundaries splitting a call fail
discovery with a source location. Strings containing marker text are ignored.
No extra pytest label or call-level identifier is required; `unit` and
`integration` retain their existing meanings.

Keep sample/configuration setup and result/request/state assertions in the test,
normally outside the region. Only invocations originating inside the region are
published, including calls through `_run`. The captured runtime arguments become
shell commands; Python setup and assertions are not copied into the document.
Unmarked calls still run normally but do not create documentation snippets.
Do not add a second command string just for documentation.

A region can contain several command calls, which are exported in execution
order with a single newline between them. Blank lines, comments, and line
continuations inside each captured snippet are preserved. Regions may be nested
when a complete workflow and an individual command both need public names. In parameterized
tests, put each distinct region in its corresponding branch and share the
argument construction. A region must execute in exactly one selected test case;
repeated call sites, duplicate exports from other cases, and mixed output
languages are rejected rather than producing an ambiguous example.

For an output snapshot, place `record_output(result.stdout, language="json")`
inside its own named region. It takes the content, not a snippet name; the
region supplies that name. The same region convention applies to `invoke_azure`
and explicitly classified installation/login prerequisites in `record_external`.

For resource-specific values, keep a named placeholder in the test command, such
as `https://<resource-name>.services.ai.azure.com/`, and pass
`placeholder_values={"resource-name": "cu-docs-resource"}` to `invoke_cli`.
The test executes the bound value through normal CLI validation; documentation
keeps the placeholder for the reader to replace. Simple Bash placeholders are
unquoted; values requiring shell quoting use escaped double quotes. Missing or
unused bindings fail before execution.
The same bindings apply to string values in an explicit `env` mapping, including
`CU_ENDPOINT`; generated Bash and PowerShell commands keep the environment
templates. The input mapping and the caller's environment are preserved.
Bindings replace values inside arguments or environment values, never add or
split arguments.

Use complete repository samples and matching sanitized service recordings for
successful examples whenever available. `support.recording.copy_sample_invoice`
copies the public invoice fixture into the test's isolated directory. Do not
write a short text string or a PDF header into a `.pdf` file for a normal example.
Keep constructed invalid inputs and deterministic service doubles for negative,
boundary, and side-effect tests, but do not present them as real service results.
Do not change analyzer IDs or API versions in existing recordings to make a
different scenario pass. Report missing samples or recordings instead.
The [recording data notes](packages/standalone/tests/integration/recordings/README.md#sample-data-and-gaps)
list available data and the remaining gaps. Keep secrets in local configuration,
not in test arguments, published samples, recordings, or chat.

Link a fenced block directly with `<!-- Snippet:analyze_inline -->`. Names are
unique in the test sources, but the same name can be referenced multiple times
within either document or across both documents. Do not add document-specific
aliases or an `Examples:` mapping.

Keep the marker and code block at the document's top level. Code fences nested
inside lists or block quotes are rejected before either document is updated;
move both the block and its marker outside the container. Fence-like text inside
a code block remains literal output.

For a continuous workflow, enclose all its commands in one named region, as in
`configure_key` and `profile_copy_cleanup`. To combine already published regions
from independent tests into a documentation section, use the test-side
`DOC_SCENARIOS` mapping in
[test_public_docs.py](packages/standalone/tests/unit/test_public_docs.py).
For example, `configure_login` groups the existing `profile_endpoint`,
`profile_login`, `azure_login`, and `doctor` sources; its document marker is simply
`<!-- Snippet:configure_login -->`. Scenarios preserve source order and combine
already tested commands of the same language with a single newline between
sources, without duplicating their text or changing their internal formatting.
They do not replace end-to-end workflow tests. A single command uses its own
name directly. Missing members and duplicate source or scenario names fail.
Exported sources must be referenced directly or by a referenced scenario.
Tests that fail, skip, or fail during cleanup cannot publish examples.
An unexecuted region also prevents synchronization, even if its test passes.

The verification report distinguishes consecutive commands from one passing
test (`continuous`) from examples composed across tests or with intervening
commands (`composed`). Continuous execution proves shared local state and
command order; it does not imply that all service calls use real recordings.
The configuration-to-analysis workflow starts from an empty profile. The custom
analyzer workflow passes the recorded schema-suggestion output file through
creation, sample testing, analysis, inspection, and deletion using a stateful
service double after schema generation. Its missing live recordings remain
explicit in the report and recording data notes.

Write headings and longer command descriptions outside the marked code block. An
initial description may be drafted automatically, then edited by hand; later
updates only replace the block's contents. They preserve all surrounding prose
and whitespace and do not compare handwritten descriptions with test wording.

For step comments inside a generated code block, pass `comment="..."` to
`invoke_cli`, `invoke_azure`, or `record_external`; separate multiple lines with
`\n`. Local `_run` wrappers must forward this parameter. Each line is rendered
as a shell comment before the command, never passed to the CLI or executed.
Preserve existing step comments in these test sources rather than editing the
generated blocks. Python comments inside a region are not copied automatically.

Use `invoke_azure` for actual Azure CLI extension parsing. `record_output` validates
JSON/YAML or publishes an asserted, normalized output snapshot. Installation and
interactive login are explicitly classified external prerequisites with reasons;
CU commands cannot use that classification. Documentation generation forces
playback and blocks live network connections in source tests. A missing recording
fails rather than silently skipping. It never signs in, deploys, or upgrades the
developer's environment while executing an example.

The generator and pytest protections use the same source-discovery function.
Each parameterized variant of a source test receives the offline network guard;
when exporting documentation, a skipped source test is a failure. Ordinary tests
without named examples keep their normal skip behavior.

The command renderer derives shell syntax from the tested argument vector. It
supports quoting, multiline Bash/PowerShell, temporary environment overrides,
comments, and explicit expected exit codes. Normal examples require exit code 0;
intentional failures must declare their expected code and are labeled in output.

After changing a source test, regenerate and then run the read-only check:

```bash
python scripts/update-snippet.py update
python scripts/update-snippet.py check --report .pytest_cache/snippet-verification.json
```

Both modes execute the source tests. `update` validates all references and block
structure before writing either document. `check` never rewrites either
documentation file and fails on missing markers, duplicate test-side names,
missing/unused sources, skipped tests, language mismatch, or code-block drift.
Reusing a source name in the documents is allowed. PR CI runs `check`.

`--report` writes a separate artifact in either mode. Its path must not refer
to either document, the synchronizer script, or a Python file in the test tree,
including through symbolic links or hard links. Conflicting report paths fail
before source tests run and are checked again before the report is written.

The optional JSON report lists source locations, validation modes (`local`,
`playback`, `mocked`, or `external`), output validation types, and hashes of
checked-in samples and consumed recordings. It excludes command text and
credentials. `playback` requires the invocation to consume a recorded response;
entering an unused cassette alone does not count. Hashes identify the fixtures
used in this run, not the original input bytes scrubbed from old recordings.
Multi-command regions retain per-command evidence and indicate whether the
commands were consecutive; their mode is `mixed` when the evidence modes differ.
CI uploads this report and the invocation matrix as artifacts, including on a
failed check. Do not commit the generated reports.

Test fixtures fix both Rich help and CLI consoles to deterministic non-colored
output, independent of the host terminal. Windows CI enables symbolic links
before checkout, so the package README is validated as a real link rather than
silently skipping the check.

Refresh the invocation evidence matrix when changing the command surface:

```bash
python -m pytest -c packages/standalone/pyproject.toml -m unit packages/standalone/tests/unit \
	--command-catalog .pytest_cache/command-catalog.json \
	--command-matrix .pytest_cache/command-test-matrix.md \
	--require-command-coverage
```

The generated matrix records observed option combinations and test IDs, not an
assertion of exhaustive arbitrary value/state coverage. Keep this report in the
cache or CI artifacts rather than committing a machine-dependent snapshot.
The gate requires every public command and option spelling to appear in non-help
calls from passing tests. Parsing uses callback-free copies of the actual Click
parameters; rejected syntax, invalid values, and missing option values do not
count. Application-level expected failures may still provide invocation evidence.
This gate does not replace semantic assertions, boundary tests, or request and
side-effect checks. CI writes its matrix to the cache, not to tracked documentation.

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
