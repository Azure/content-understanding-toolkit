# Cassettes (record / playback)

Sanitized HTTP recordings for cloud-gated commands, replayed by
`tests/test_cloud_playback.py` in **playback** mode (default, offline, CI).

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

Regenerate against a live endpoint:

    CU_TEST_REC_MODE=record CU_TEST_REC_ENDPOINT=https://<res>.services.ai.azure.com/ \
      CU_TEST_REC_KEY=<key> pytest tests/test_cloud_playback.py

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
