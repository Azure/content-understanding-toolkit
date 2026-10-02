# Cassettes (record / playback)

Sanitized HTTP recordings for cloud-gated commands, replayed by the tests in
`tests/integration` and the documentation tests in `tests/docs` in **playback**
mode (default, offline, CI).

Modes are selected via env (not stripped by the test env isolation):

| Var                    | Values                                 | Notes                             |
| ---------------------- | -------------------------------------- | --------------------------------- |
| `CU_TEST_REC_MODE`     | `playback` (default), `record`, `live` | playback needs no network/secrets |
| `CU_TEST_REC_ENDPOINT` | `https://<res>.services.ai.azure.com/` | required for record/live          |
| `CU_TEST_REC_AUTH`     | `key` (default if key set), `entra`    |                                   |
| `CU_TEST_REC_KEY`      | `<api-key>`                            | required for key auth             |
| `CU_TEST_REC_COPY_SOURCE_ID` | ready custom analyzer ID        | same-resource record/live test    |
| `CU_TEST_REC_SOURCE_ARM_ID` | source account ARM ID           | cross-resource live test only     |
| `CU_TEST_REC_TARGET_ENDPOINT` | target Foundry endpoint        | cross-resource live test only     |
| `CU_TEST_REC_TARGET_ARM_ID` | target account ARM ID             | cross-resource live test only     |

Regenerate a selected scenario from `cu-cli/packages/standalone` against an
approved test endpoint. Recording mode makes real, potentially billed requests;
lifecycle scenarios also create or delete test analyzers:

    CU_TEST_REC_MODE=record CU_TEST_REC_ENDPOINT=https://<res>.services.ai.azure.com/ \
  CU_TEST_REC_AUTH=entra python -m pytest tests/integration/test_analyze.py::test_scenario_1_analyze_single_file_markdown

Cassettes are host-agnostic (matched on method + path + query) and have all
secrets and real hostnames scrubbed, so they are safe to commit.

## Workflow Coverage Map

- Analyze local files
  - `analyze_single.yaml`
- Generate and validate a starter schema
  - `analyzer_create.yaml`
  - `analyzer_show.yaml`
  - `analyzer_delete.yaml`
  - plus offline validate step in test before create
- Create/test/list/show/delete analyzers
  - `analyzer_list.yaml`
  - `analyzer_test.yaml`
  - `analyzer_create.yaml`
  - `analyzer_show.yaml`
  - `analyzer_delete.yaml`
- Analyzer copy lifecycle tests are live/record-only. Same-resource copy needs
  `CU_TEST_REC_COPY_SOURCE_ID` set to a stable, ready custom analyzer. Cross-resource
  copy needs two Azure resources. Set the corresponding `CU_TEST_REC_*` values and run
  `CU_TEST_REC_MODE=live pytest tests/integration/test_analyzer.py::test_analyzer_copy_same_resource_live`
  or
  `CU_TEST_REC_MODE=live pytest tests/integration/test_analyzer.py::test_analyzer_copy_cross_resource_live`.
- Manage connectivity and defaults
  - `doctor.yaml`

Note: `cu profile` and `cu infra generate` setup flows are covered
in offline command tests, not in cassette-backed cloud playback.

## Live Verification (2026-09-15)

An approved East US resource was tested using Microsoft Entra ID. The 19 existing
analysis, output-policy, defaults-read, analyzer-list, and analyzer-evaluation
tests passed against the service. Two additional examples now have new recordings:

| Recording | API Version | Analyzer | Input |
| --- | --- | --- | --- |
| [analyze_inline_preview.yaml](analyze_inline_preview.yaml) | `2026-06-01-preview` | `prebuilt-layout` | The complete invoice fixture and SHA-256 documented below |
| [analyze_public_video_url.yaml](analyze_public_video_url.yaml) | `2025-11-01` | `prebuilt-videoSearch` | The published FlightSimulator URL in the usage guide |

Both recording runs and subsequent network-blocked playback runs passed. The
inline recording contains a synchronous `analyzeBinaryInline` HTTP 200 response;
the video recording contains the HTTP 202 submission and completed LRO polling.
The video URL is mutable: this records the response to that submitted URL on the
test date, not a separately verified immutable media-file hash. The README and
usage-guide tests replay these recordings.

Defaults updates and cross-resource copying were not performed. Local JUnit
reports belong under `.pytest_cache`, not in the published documentation.

## Sample Data and Gaps

The complete [invoice fixture](../fixtures/sample_invoice.pdf) is byte-for-byte
identical to the public `cu-cli/sample_files/sample_invoice.pdf` (151,363 bytes;
SHA-256 `4da941f20655cb852986df272a22f66aff47c97a18b103a1e8e44641cf581642`).
The documentation tests copy the public sample into the isolated working
directory without modifying the source. Directory examples can copy the same
invoice to multiple locations; they must not claim those copies are distinct
business documents.

The legacy cassettes use `2025-11-01`; the new inline recording uses
`2026-06-01-preview`. The legacy analysis and schema-suggestion recordings contain
document results. Published local analysis,
default-analyzer selection, output views, existing-result policies, directory
selection, schema suggestion, analyzer listings, defaults reads, and doctor
examples reuse the corresponding recordings. They run the real CLI and SDK
offline, not a newly fabricated success response. The defaults JSON example is
a recorded GET result, not evidence for a defaults update.

Uploaded bodies were scrubbed, and the harness matches method, path, and query,
not original input bytes. Replaying a cassette does not prove that a different
sample produced its result. The checked-in fixture is the input used by the
existing tests; future recordings should record the input file hash, API
version, analyzer ID/schema, and provenance outside the secret-bearing request.
Do not relabel old results as a different analyzer, API version, or input.

The following data is still needed before the corresponding contract tests can
be promoted to matching service-backed examples:

| Scenario | Needed Data | Current Limit |
| --- | --- | --- |
| SAS-protected HTTPS inputs | Approved working sample URLs and recordings for the exact URLs/analyzers; keep SAS credentials local | The public video URL now has a matching recording. SAS examples remain placeholders; dry-run cannot validate remote content. |
| Local image, audio, and video inputs | Shareable files, provenance, and matching analyzer recordings | No such input files are checked into `cu-cli`; public video URL ingestion is covered, but generating modality templates is not an ingestion test. |
| Mixed or distinct-file batches | At least two distinct representative inputs with matching batch results | Directory tests currently exercise one invoice or copies of it. |
| Recorded custom `invoice_v1` workflow | Matching create, test, analyze, show, and delete recordings | The documentation tests use recorded schema generation, then keep the created `invoice_v1` analyzer in memory. |
| Defaults updates and `doctor --fix-defaults` | Sanitized PATCH/read-back recordings with known before/after deployment mappings | Existing defaults recordings are GET-only; mutation semantics use controlled state. |
| Cross-resource copy and reusable discovery/copy recordings | A second approved resource and sanitized ARM discovery and copy recordings | Offline copy tests use doubles for ARM discovery and the copy operation; cross-resource copying remains unverified. |

Resource names, keys, profile names, and deployment mappings intentionally remain
safe placeholders when testing configuration or destructive operations. Do not
commit private customer documents or real credentials to make examples appear
more realistic. A missing or failed recording must remain an explicit gap.
