# CU CLI usage guide

This guide covers the preview `cu` standalone CLI. On macOS, substitute
`cu-cli` because the operating system already provides an unrelated `cu`
command. If you're new to Content Understanding, start with the
[main README](../README.md#content-understanding-concepts) for definitions of
files, analyzers, analyzer results, and Microsoft Foundry resources. See also
the official [Content Understanding terminology](https://learn.microsoft.com/azure/ai-services/content-understanding/glossary).

For installation, start with the [main README](../README.md#install). For
sign-in, permissions, and new or existing Azure resource setup, follow the
[Microsoft Foundry provisioning guide](provisioning.md). This guide builds on
that setup with detailed profile
precedence, environment overrides, batch processing, analyzer management,
Content Understanding defaults, and troubleshooting workflows.

Content Understanding API version. Known versions: 2025-11-01 (GA) and
2026-06-01-preview (preview); any YYYY-MM-DD-preview version is also accepted.

For the local PDF examples, place
[sample_invoice.pdf](../sample_files/sample_invoice.pdf) in your working
directory. Replace placeholder values with your own resource settings.

## CU CLI profiles

A CU CLI profile is local CLI configuration containing the settings used to
access Content Understanding through one Microsoft Foundry resource. A profile
is a CU CLI concept, not a Content Understanding or Azure resource. It can
contain:

- `endpoint`
- `auth_mode` (`login` or `key`)
- `api_key` for key authentication
- `api_version`
- `default_analyzer`
- `model_deployments.<model>` mappings used to configure Content Understanding
  defaults

CU CLI always provides a virtual `default` profile. A fresh installation does
not require `cu profile create`; the first `cu profile set` command materializes
that profile. Create named profiles only when you need separate settings for
resources such as development and production.

### Configure named profiles

The profile examples below use `dev` and `prod`. Set them up once with distinct
resource endpoints, then reuse them in the later sections. If either profile
already exists, skip its `create` command and review its settings before
changing the endpoint. Changing the working directory does not reset profiles.

<!-- Snippet:profile_setup -->
```bash
cu profile create dev
cu profile set endpoint https://<dev-resource>.services.ai.azure.com/ --name dev
cu profile create prod
cu profile set endpoint https://<prod-resource>.services.ai.azure.com/ --name prod
cu profile set-active dev
```

This selects `dev` as the active profile. Commands without `--profile` use it
until you select another profile. Configure authentication for each resource
as described in [Authentication](#authentication).

### Resolution precedence

For normal service commands, CU CLI resolves each setting independently from
the highest available layer:

1. Explicit command options, such as `--endpoint` or `--api-key`.
2. Supported environment variables.
3. The selected CU CLI profile: `--profile NAME`, otherwise the active profile.
4. Shared base values in the `[cu]` Azure CLI configuration section, retained
   for compatibility with configurations created before named profiles.
5. Built-in defaults.

The first layer containing a value wins; layers are not all-or-nothing. For
example, an environment endpoint can override the selected profile's endpoint
while the API version still comes from that profile. CU CLI doesn't write
command or environment overrides back to the profile.

With the profiles above configured, inspect the active `dev` resource:

<!-- Snippet:analyzer_list_active -->
```bash
cu analyzer list --info
```

`--info` prints the resolved non-secret runtime context to standard error before
the operation. It does not make the command a dry run: these examples still
list analyzers from the selected resource, which must be accessible to your
configured identity. Use the context to verify precedence without exposing an
API key.

The runtime context for this command begins with:

<!-- Snippet:runtime_info -->
```text
endpoint: https://<dev-resource>.services.ai.azure.com/
auth mode: entra
api-version: 2025-11-01
CU CLI profile: dev
settings: ~/.azure/config
```

Here, `~` represents the current user's home directory; the settings path is
printed as an absolute path at runtime. It resolves to `$AZURE_CONFIG_DIR/config`
when `AZURE_CONFIG_DIR` is set.

Use `prod` for one command without changing the active profile:

<!-- Snippet:analyzer_list_prod -->
```bash
cu analyzer list --profile prod
```

An environment endpoint overrides the endpoint from `prod`; the remaining
settings still come from that profile:

<!-- Snippet:analyzer_list_env -->
```bash
CU_ENDPOINT=https://<temporary-resource>.services.ai.azure.com/ \
  cu analyzer list --profile prod --info
```

An explicit endpoint overrides both the environment value and the profile:

<!-- Snippet:analyzer_list_explicit -->
```bash
CU_ENDPOINT=https://<temporary-resource>.services.ai.azure.com/ \
  cu analyzer list \
    --profile prod \
    --endpoint https://<one-time-resource>.services.ai.azure.com/ \
    --info
```

### Storage

CU CLI profiles are stored in the Azure CLI configuration file:

- `$AZURE_CONFIG_DIR/config` when `AZURE_CONFIG_DIR` is set.
- `~/.azure/config` otherwise.

CU CLI owns only the `[cu]` section. Writes are atomic and preserve unrelated
Azure CLI sections and their settings. On POSIX systems, saved configuration
files use mode `0600`. On Windows, access is controlled by filesystem ACLs,
not POSIX mode bits. Unknown `[cu]` keys are preserved for forward compatibility.

### CU CLI profile commands

Inspect the active profile, read its endpoint, list profiles, and inspect the
existing `prod` profile. These commands do not change configuration:

<!-- Snippet:profile_workflow -->
```bash
cu profile show
cu profile get endpoint
cu profile list
cu profile show --name prod
```

To opt the `dev` profile into the preview API, change its saved version. This
affects subsequent commands using `dev`; it is not needed for the GA examples:

<!-- Snippet:profile_preview -->
```bash
cu profile set api_version 2026-06-01-preview --name dev
```

For a disposable local configuration, copy `dev` to `test`, rename that copy to
`staging`, and remove it when finished. Run this workflow only when `test` and
`staging` do not already exist, or choose unused names. The final command skips
confirmation and deletes only the newly copied local profile, not an Azure
resource:

<!-- Snippet:profile_copy_cleanup -->
```bash
cu profile copy dev test
cu profile rename test staging
cu profile delete staging --yes
```

`show --name` is view-only and never changes the active CU CLI profile. The
active profile cannot be deleted; activate another profile first. `copy`
creates a separate profile, `rename` moves the profile and its saved values, and
`set-active` changes which CU CLI profile commands use when `--profile` is
omitted.

Profile names contain 1-64 ASCII letters or numbers and may contain internal
hyphens or underscores. The names `default` and `model_deployments` are reserved.

`api_key` is never printed. `get` and `show` display a redacted value.

### Inspect deployments

Deployment inspection requires Azure CLI login and permission to read the
selected resource. It does not change the profile or deploy models:

<!-- Snippet:profile_deployments -->
```bash
cu profile show --deployments --time
```

### Authentication

Login authentication is the recommended default:

<!-- Snippet:login_authentication -->
```bash
az login
cu profile set auth_mode login
```

`az login` authenticates Azure CLI and does not modify CU CLI profile settings.

To use a resource key:

<!-- Snippet:profile_key -->
```bash
cu profile set api_key <key>
```

Setting an API key also selects key authentication. Unsetting the key returns
the CU CLI profile to login authentication:

<!-- Snippet:profile_unset_key -->
```bash
cu profile unset api_key
```

Run `cu profile set api_key --help` for the current key-setting syntax. Treat a
literal key in a command as sensitive because the shell can save it in history.
For automation, inject `CU_API_KEY` through the environment using your
platform's secret facility and remove it when the process finishes. Profile
display and `--info` output redact the key.

### Environment overrides

Use environment variables for temporary or automated overrides rather than
rewriting a saved profile. List the exact variables supported by the installed
version:

<!-- Snippet:environment_inspection -->
```bash
cu env-var list
cu env-var list --json
```

The JSON form returns an array of objects with each variable's `name`, redacted
`value`, and `scope`. It is useful for scripts that need to inspect active
overrides without parsing a rendered table or exposing `CU_API_KEY`.

For example:

<!-- Snippet:env_override_bash -->
```bash
CU_ENDPOINT=https://<temporary-resource>.services.ai.azure.com/ \
  cu analyzer list --info
```

In PowerShell, preserve and restore the previous environment value:

<!-- Snippet:env_override_powershell -->
```powershell
$previous_CU_ENDPOINT = $env:CU_ENDPOINT
$env:CU_ENDPOINT = "https://<temporary-resource>.services.ai.azure.com/"
try {
  cu analyzer list --info
} finally {
  $env:CU_ENDPOINT = $previous_CU_ENDPOINT
}
```

Avoid persisting `CU_API_KEY` in shell startup files.
`cu profile sync-defaults` intentionally uses the endpoint saved in the
selected profile rather than `CU_ENDPOINT`, because synchronization updates
that profile's model mappings.

### Save model deployment mappings

Content Understanding operations that use generative AI require Foundry model
deployments, including a large language model (LLM) for chat completion and an
embeddings model. Content Understanding defaults connect model names and
prebuilt analyzer model aliases to deployment names so each analyze request
doesn't need to provide the mappings.

Import remote Content Understanding defaults into the active CU CLI profile:

<!-- Snippet:profile_sync -->
```bash
cu profile sync-defaults
```

Alternatively, select an existing named profile explicitly:

<!-- Snippet:profile_sync_named -->
```bash
cu profile sync-defaults --name dev
```

Synchronization always uses the endpoint saved in the selected CU CLI profile.
`CU_ENDPOINT` cannot redirect it to a different resource. Authentication can
still be overridden with `--auth-mode` or `--api-key`.

For example, supply a resource key when synchronizing `dev`. The saved endpoint
on `dev` remains authoritative. Replace `<key>` with that resource's key and
observe the [key-handling precautions](#authentication):

<!-- Snippet:profile_sync_auth -->
```bash
cu profile sync-defaults --name dev --auth-mode key --api-key <key> --time
```

Instead of importing mappings, you can set them manually in the active profile.
Replace the deployment names below with existing deployments on your resource.
These commands change local configuration only:

<!-- Snippet:configure_model_mappings -->
```bash
cu profile set model_deployments.gpt-5.2 my-gpt-52-deployment
cu profile set model_deployments.text-embedding-3-large my-embedding-deployment
```

To apply saved mappings to the resource, use
[Update remote mappings](#update-remote-mappings). When applying supported model
mappings, CU CLI also derives the service aliases used by prebuilt analyzers.
For example,
`my-gpt-52-deployment` is also mapped to
`prebuilt-analyzer-completion` and
`prebuilt-analyzer-completion-mini`, while
`my-embedding-deployment` is mapped to `prebuilt-analyzer-embedding`. This lets
prebuilt analyzers find the same deployments without requiring you to enter
those alias mappings separately.

These two stores serve different purposes:

- `cu profile set model_deployments...` changes local CU CLI configuration.
- `cu defaults set` changes remote Content Understanding defaults on the
  Microsoft Foundry resource.
- `cu profile sync-defaults` copies the remote defaults into a local profile.

See [Model deployment options for Content Understanding analyzers](https://learn.microsoft.com/azure/ai-services/content-understanding/concepts/models-deployments)
for the service concepts behind these mappings.

## Provisioning

`cu infra generate` writes an azd/Bicep project; `azd up` performs the Azure
deployment. The project can create or reuse a Microsoft Foundry resource,
deploy supported LLM and embeddings models, configure Content Understanding
defaults, and configure the default CU CLI profile.

For permissions, Azure CLI and azd sign-in, new and existing resource paths,
model-free setup, manual defaults, and generated post-provision behavior, use
the authoritative [Microsoft Foundry provisioning guide](provisioning.md).

### Generate infrastructure

Generate a local project using defaults:

<!-- Snippet:infra_generate -->
```bash
cu infra generate
```

Alternatively, specify the environment, location, output directory, and models.
Replace `Development` with your subscription name or ID and choose a supported
region and your own resource prefix. The following example uses `--force`, which
replaces generated files in the selected output directory. Review any existing
files before using it:

<!-- Snippet:infra_custom -->
```bash
cu infra generate --output-dir infra --environment dev-01 --location westus3 --subscription Development \
  --api-version 2026-06-01-preview \
  --models "gpt-5.2, text-embedding-3-large" \
  --foundry-prefix contoso-cu \
  --assign-roles false \
  --force
```

These are alternative project-generation recipes. Neither provisions Azure
resources; deployment is a separate step in the provisioning guide.

## Analyze

### Analyze a local file

An analyzer defines how Content Understanding processes a file. Analyze one file
with the `prebuilt-layout` content extraction analyzer:

<!-- Snippet:analyze_layout -->
```bash
cu analyze sample_invoice.pdf --analyzer prebuilt-layout
```

By default, CU CLI formats the analyzer result as Markdown with the Content
Understanding SDK's `to_llm_input()` helper. Use `--json` for the complete
analyzer result as JSON or `--llm-input` to select the default Markdown view
explicitly.

For synchronous analysis with the preview API, see the
[inline analysis example](../README.md#supported-content-understanding-api-versions).

Use the CU CLI profile's default analyzer:

<!-- Snippet:analyze_with_profile_default -->
```bash
cu profile set default_analyzer prebuilt-layout
cu analyze sample_invoice.pdf --json
```

### Output formats

Choose the output form you need. Each invocation submits the input for analysis.
For the complete service response on standard output:

<!-- Snippet:analyze_json -->
```bash
cu analyze sample_invoice.pdf --analyzer prebuilt-layout --json
```

To save the Markdown view instead of printing it:

<!-- Snippet:analyze_markdown_file -->
```bash
cu analyze sample_invoice.pdf --analyzer prebuilt-layout --output-file results/invoice.md
```

To save the complete JSON response:

<!-- Snippet:analyze_json_file -->
```bash
cu analyze sample_invoice.pdf --analyzer prebuilt-layout --json --output-file results/invoice.json
```

Parent directories are created as needed. Use an unused output path, or choose
an explicit [existing-output policy](#existing-outputs-and-batch-reports).
If analysis succeeds but the Markdown view has no displayable content, CU CLI
recommends `--json`.

### Analyze an HTTPS or SAS URL

Pass an HTTPS URL with the named `--url` option. CU CLI sends
the reference to Content Understanding and does not download or upload the file
itself. This enables URL-based service limits, including large video workflows:

<!-- Snippet:analyze_video_url -->
```bash
cu analyze --url https://github.com/Azure-Samples/azure-ai-content-understanding-assets/raw/refs/heads/main/videos/sdk_samples/FlightSimulator.mp4 \
  --analyzer prebuilt-videoSearch \
  --json
```

Repeat `--url` for multiple URLs. It cannot be combined with positional inputs,
`--file`, or `--source`. Positional URLs remain available as a standalone
shortcut, including when mixing local and remote inputs. `--pattern` requires
`--source`, and `--recursive` requires a directory input.

Azure Blob SAS query parameters are preserved exactly for the service request.
Replace the placeholders below with your storage account, container, blob, and
SAS token.
Quote the complete URL so the shell does not interpret `&` characters:

<!-- Snippet:analyze_sas_url -->
```bash
cu analyze --url "https://<storage-account>.blob.core.windows.net/<container>/<blob>?<sas-token>" \
  --analyzer prebuilt-videoSearch \
  --json
```

Only absolute HTTPS URLs are accepted, and the service URL limit is 8,192
characters. Use a short-lived SAS with read permission (`sp=r`). CU CLI removes
the query string from console output and `--report-file`; the original URL is
still sent to Content Understanding. If the service cannot read the input,
verify the SAS start and expiry times, read permission, and Azure Storage network
rules.

With `--output-dir`, each remote result uses
`<filename>.result.json` (or `.result.md`), preserving the filename and extension
from the URL path. For example, `invoice.pdf` produces `invoice.pdf.result.json`.
No URL hash is added, and query strings do not participate in naming, so renewing
a SAS does not change the result path. Filenames are sanitized for the local
filesystem; an empty URL path uses `remote-input`.

Generated remote result names, including the result suffix, must fit within 240
UTF-8 bytes, leaving room for atomic-write temporary names. Longer names fail
before analysis instead of being truncated. Analyze that input separately with
a shorter `--output-file` name, or omit file-output options to stream one result
to stdout. Explicit `--output-file` names are unchanged.

If two inputs in the same batch map to one result path and either input is
remote, CU CLI rejects the entire batch before calling the service or writing
files, including during `--dry-run`. `--on-existing skip` and `reanalyze` do not
bypass this check. Analyze the conflicting inputs separately with distinct
`--output-file` paths or output directories. Collisions between local inputs
retain their existing disambiguation behavior.

Across separate invocations, existing results follow `--on-existing`: `error`
(the default), `skip`, or `reanalyze`. This check uses the output path, not source
identity: `skip` can reuse a same-named result from a different URL. Use separate
output paths when the sources differ. Old hash-named results are not
automatically migrated or reused, so a new analysis may incur additional
charges even when `--on-existing skip` is selected.

For multiple inputs that include a URL, specify `--output-dir` because a remote
result cannot be written next to its source. A dry run reports remote sizes as
unavailable and does not probe or download remote content:

<!-- Snippet:analyze_urls_preview -->
```bash
cu analyze --url https://github.com/Azure-Samples/azure-ai-content-understanding-assets/raw/refs/heads/main/document/invoice.pdf \
  --url https://github.com/Azure-Samples/azure-ai-content-understanding-assets/raw/refs/heads/main/document/receipt.png \
  --output-dir results \
  --analyzer prebuilt-layout \
  --dry-run
```

### Select multiple local inputs

To select specific files, repeat `--file`. Place PDFs named `invoice one.pdf`
and `invoice two.pdf` in the working directory, or replace these paths with
your own existing files. Quote paths that contain spaces:

<!-- Snippet:analyze_files_preview -->
```bash
cu analyze --file "invoice one.pdf" --file "invoice two.pdf" --analyzer prebuilt-layout \
  --output-dir selected-results \
  --json \
  --dry-run
```

To select files from multiple directories, repeat `--source`. Prepare the
`incoming` and `archive` directories with PDFs. The same `--pattern` applies
to both directories; only immediate matching files are selected unless you
add `--recursive`:

<!-- Snippet:analyze_sources_preview -->
```bash
cu analyze --source incoming --source archive --pattern "*.pdf" --analyzer prebuilt-layout \
  --output-dir combined-results \
  --json \
  --dry-run
```

These commands preview the selection without contacting Content Understanding
or writing result files. After reviewing the plan, remove `--dry-run` to submit
the files. Do not combine `--file` with `--source`, or mix either named
selection mode with positional inputs.

### Analyze files in local directories

Place the input PDFs in `my_document_dir`; put files in subdirectories when trying
recursive selection. To analyze only immediate files matching the PDF pattern:

<!-- Snippet:analyze_pattern -->
```bash
cu analyze --source my_document_dir --pattern "*.pdf" -a prebuilt-layout --output-dir results \
  --json
```

Directory input selects immediate files only. Add `--recursive` to include
nested directories:

<!-- Snippet:analyze_recursive -->
```bash
cu analyze --source my_document_dir --pattern "*.pdf" --recursive --analyzer prebuilt-layout \
  --output-dir recursive-results \
  --json
```

With `--output-dir`, CU CLI preserves each input path relative to the selected
source directory. For example:

<!-- Snippet:output_mapping -->
```text
my_document_dir/nested/sample_invoice.pdf
  -> recursive-results/nested/sample_invoice.pdf.result.json
```

Markdown results use `.result.md` instead. With one input, omit `--output-dir` to
write the result to standard output or use `--output-file` to choose one file.
`--output-file` is rejected when more than one input is selected.

For the positional directory shortcut, place input files in `docs`. This form
does not use a filename pattern and writes results under `out`:

<!-- Snippet:analyze_directory -->
```bash
cu analyze docs --analyzer prebuilt-layout --output-dir out --json
```

### Preview and run a batch safely

Every non-dry-run analyze request is billed. Preview discovery, output paths,
and existing-file actions before a batch:

<!-- Snippet:analyze_dry_run -->
```bash
cu analyze --source documents --analyzer prebuilt-layout --json --output-dir results \
  --report-file report.json \
  --dry-run
```

A dry run prints the selected file count, bytes and extensions, analyzer,
recursion mode, collision policy, and source-to-output mapping. It makes no
service calls and writes no result files. It cannot validate analyzer
existence, file contents, service-side format acceptance, usage, or cost.
Hidden files directly under a selected or visible directory are named and
counted as skipped. Files inside hidden directories and CU CLI's own
`*.result.md` and `*.result.json` files are excluded from discovery to avoid
infrastructure noise and accidental reanalysis.

After reviewing the selection, remove `--dry-run` to submit the files. For
noninteractive scripts, pass `--yes`; otherwise a large or costly batch can
request confirmation.

### Existing outputs and batch reports

`--on-existing` controls what happens when a result path already exists:

- `error` (default) reports the collision instead of replacing the result.
- `skip` leaves the existing result untouched and records it as skipped.
- `reanalyze` submits the input again and replaces the existing result.

If `result.json` already contains the result for this input, reuse it without
another service call. This example assumes a configured default analyzer. If
the output does not exist, `skip` still runs the analysis:

<!-- Snippet:analyze_skip -->
```bash
cu analyze sample_invoice.pdf --json --output-file result.json --on-existing skip
```

Alternatively, deliberately submit the input again and replace that result.
Reanalysis can incur additional charges:

<!-- Snippet:analyze_reanalyze -->
```bash
cu analyze sample_invoice.pdf --json --output-file result.json --on-existing reanalyze
```

Use `--report-file ./run-report.json` for a machine-readable record of each
input's status. A batch continues after an individual file failure, reports
successful, failed, and skipped inputs, and exits with status `1` if any input
failed. This lets automation keep good results while reporting files that need
attention.

The following noninteractive batch uses eight concurrent jobs and skips the
large-batch confirmation with `--yes`. It writes to `batch-results`, separately
from the earlier directory examples. Use an unused result directory and report
path; if reusing paths, choose an existing-output policy and a new report path:

<!-- Snippet:analyze_recursive_report -->
```bash
cu analyze --source my_document_dir --pattern "*.pdf" --recursive --analyzer prebuilt-layout \
  --output-dir batch-results \
  --json \
  --report-file run-report.json \
  --yes \
  --concurrency 8
```

`--concurrency` or `-j` controls concurrent batch **jobs**. The default is `4`;
the supported range is `1` through `32`.

### Track elapsed time

Use `--time` to print CU service and total command elapsed time. This example
explicitly selects the default Markdown view with `--llm-input`:

<!-- Snippet:analyze_llm_input -->
```bash
cu analyze sample_invoice.pdf --analyzer prebuilt-layout --llm-input --time
```

`--time` output resembles:

<!-- Snippet:analysis_timing -->
```text
CU service calling time: <seconds>s
Total command time: <seconds>s
```

`<seconds>` represents a dynamic duration. Timings vary by machine and request.

### Inspect service usage

Add `--usage` to print the usage returned by the service, and `--time` to include
CU service and total command duration. This submits a new analysis request;
it does not inspect a saved result:

<!-- Snippet:analyze_usage -->
```bash
cu analyze sample_invoice.pdf --analyzer prebuilt-layout --json --usage --time
```

The primary JSON result goes to standard output. Usage and timing go to
standard error, so scripts can consume the result without those messages.
Usage fields depend on the analyzer and API response and are not a cost
estimate. CU CLI reports when the service does not return usage details.

Run `cu analyze --help` for the complete input-selection and output contract.

## Analyzers

Prebuilt analyzers are ready-to-use analyzers supplied by Content Understanding.
A custom analyzer uses an analyzer schema to define processing and the
structured fields your application needs.

Custom analyzer IDs contain 1-64 ASCII letters, numbers, or underscores.
Hyphens are reserved for service-provided prebuilt analyzer IDs.

### Create a schema

Choose one approach below to prepare `schema.json`: a starter template, sample
generation, or an explicit base analyzer. They are alternatives, not consecutive
steps. Schema generation refuses to replace an existing output. Choose another
path, or use `--force` only after reviewing the file you intend to replace.

The first command writes a document extraction template. The other two create
optional image extraction and document classification templates with separate
output names:

<!-- Snippet:schema_templates -->
```bash
cu analyzer schema create --output-file schema.json
cu analyzer schema create --modality image --output-file image-schema.json
cu analyzer schema create --output-file classify.json --type classification
```

Alternatively, generate `schema.json` from a representative sample. This calls
the CU service; existing output paths are checked before the request is sent:

<!-- Snippet:schema_from_sample -->
```bash
cu analyzer schema create --name invoice_v1 --from-sample sample_invoice.pdf --output-file schema.json
```

As another alternative to the default template, specify the base analyzer and
custom analyzer ID explicitly:

<!-- Snippet:schema_base -->
```bash
cu analyzer schema create --base prebuilt-document --name invoice_v1 --output-file schema.json
```

For modality-specific templates, choose the relevant command below. These use
separate filenames so they do not replace the schema selected above:

<!-- Snippet:schema_modalities -->
```bash
cu analyzer schema create --modality document --output-file document-schema.json
cu analyzer schema create --modality audio --output-file audio-schema.json
cu analyzer schema create --modality video --output-file video-schema.json
```

Review and edit the selected schema before deployment. The first validation
command checks its structure; the second also checks the service API
specification and returns JSON. Both are offline:

<!-- Snippet:schema_validation -->
```bash
cu analyzer validate schema.json
cu analyzer validate --schema schema.json --spec --json
```

A successful validation prints an `ok` result and makes no service call. Invalid
JSON, unsupported properties, and incompatible schema options return a nonzero
status with the failing location.

For CI or other workflows that must also reject warnings, add `--strict`.
This command validates locally against the bundled service contract and
prints a JSON report:

<!-- Snippet:schema_validate_strict -->
```bash
cu analyzer validate schema.json --strict --spec --json
```

With `--strict`, a warnings-only result exits with status `2` instead of `0`.
Without `--strict`, warnings alone do not fail validation.

### Create and test

Use the reviewed `schema.json` from the previous section. The ID `invoice_v1`
must not already exist on the selected resource. Create the analyzer, then
evaluate the local invoice:

<!-- Snippet:analyzer_evaluation -->
```bash
cu analyzer create --name invoice_v1 --schema schema.json
cu analyzer test invoice_v1 sample_invoice.pdf
```

For directory evaluation, place representative input PDFs in `samples`. Preview
the matching files, including nested PDFs, without making analyzer service calls:

<!-- Snippet:analyzer_test_preview -->
```bash
cu analyzer test --name invoice_v1 --source samples --pattern "*.pdf" --recursive \
  --dry-run
```

Run the same selection and save one aggregate report with this noninteractive
command. `--yes` skips batch confirmation; ensure the
selected samples are the ones you intend to submit:

<!-- Snippet:analyzer_test_batch -->
```bash
cu analyzer test --name invoice_v1 --source samples --pattern "*.pdf" --recursive \
  --concurrency 2 \
  --yes \
  --json \
  --output-file test-report.json
```

Analyzer test reports preserve existing files by default and are checked before
any samples are sent to the CU service. Pass `--force` only when you
intentionally want to replace the selected report.

`cu analyzer test` summarizes whether fields and confidence values were
returned. It isn't an accuracy benchmark and doesn't compare results with
labeled ground truth. Use `cu analyze --analyzer invoice_v1 --json` when you
need the complete analyzer result.

### Inspect and manage

After creating `invoice_v1`, list available analyzers and read its definition.
These commands do not change or delete an analyzer:

<!-- Snippet:analyzer_management -->
```bash
cu analyzer list
cu analyzer show invoice_v1
```

To list only custom analyzers as sorted JSON:

<!-- Snippet:analyzer_list_custom -->
```bash
cu analyzer list --json --kind custom --sort-by analyzerId
```

### Copy within a resource

To create a separately named copy on the selected resource, use different
source and destination IDs. The source `invoice_v1` must exist, and the
destination `invoice_v2` must not already exist. This creates a new analyzer
definition; it does not copy analysis results:

<!-- Snippet:analyzer_copy_same_resource -->
```bash
cu analyzer copy invoice_v1 invoice_v2
```

Copying still requires Azure CLI sign-in and the
[resource-discovery permissions](#copy-across-resources) described below.
CU service calls use the selected profile's configured authentication. When
the copy is no longer needed, follow [Delete an analyzer](#delete-an-analyzer)
with `invoice_v2`, after verifying the selected profile and endpoint.

### Copy across resources

Use the existing `dev` and `prod` profiles from
[Configure named profiles](#configure-named-profiles). They must point to distinct
resources and use the same API version. The source `invoice_v1` must exist on
`dev`, and the destination ID must not already exist on `prod`. This copies the
analyzer definition, not its analysis results:

<!-- Snippet:analyzer_copy_profiles -->
```bash
cu analyzer copy invoice_v1 invoice_v1 --source-profile dev --destination-profile prod
```

If you previously opted `dev` into the preview API, align the profiles' API
versions before copying, or use `--api-version` to select a shared version for
this copy. The override applies to both sides without changing either saved
profile.

Alternatively, select resources directly for login-authenticated discovery.
Replace each placeholder with a resource name, a Foundry endpoint URL, or a full
`Microsoft.CognitiveServices/accounts` ARM ID. The same source-exists and
destination-unused requirements apply; do not run both recipes against an
already copied destination:

<!-- Snippet:analyzer_copy_resources -->
```bash
cu analyzer copy invoice_v1 invoice_v1 --source-resource <source-resource> --destination-resource <destination-resource>
```

Resource selectors support side-specific subscription and resource-group
options. For every copy, CU CLI resolves each effective endpoint through Azure
before making analyzer calls. `--source-subscription` and
`--destination-subscription` are authoritative when supplied; otherwise CU CLI
uses the active Azure CLI subscription. Discovery never searches other
subscriptions. Direct resource copy uses login authentication and does not
persist discovered endpoints into CU CLI profiles.

Azure resource discovery requires Reader access on each selected subscription
or resource group. Profile-backed data-plane calls continue to use the
CU CLI profile's configured authentication.

### Delete an analyzer

Delete `invoice_v1` only when it is no longer needed on the selected resource.
Verify the active profile and endpoint first. This command asks for confirmation;
declining leaves the analyzer unchanged. It does not delete a copy on another
resource:

<!-- Snippet:analyzer_delete -->
```bash
cu analyzer delete invoice_v1
```

`--yes` skips confirmation and is intended for deliberate noninteractive
cleanup, not routine inspection.

## Content Understanding defaults

Content Understanding defaults map model names and prebuilt analyzer aliases to
deployment names on the Microsoft Foundry resource. `cu defaults` changes those
remote mappings; `cu profile` changes local connection and mapping settings.

### Show remote mappings

Read the selected resource's defaults as JSON without changing them:

<!-- Snippet:defaults_show -->
```bash
cu defaults show
```

The response contains model-to-deployment mappings like the following.
Deployment names depend on the selected resource:

<!-- Snippet:defaults_json_output -->
```json
{
  "modelDeployments": {
    "gpt-5.2": "gpt-5.2-225597",
    "text-embedding-3-large": "text-embedding-3-large-438217",
    "prebuilt-analyzer-completion": "gpt-5.2-225597",
    "prebuilt-analyzer-completion-mini": "gpt-5.2-225597",
    "prebuilt-analyzer-embedding": "text-embedding-3-large-438217"
  }
}
```

For the same read-only operation in table form:

<!-- Snippet:defaults_table -->
```bash
cu defaults show --table
```

### Update remote mappings

The following commands modify the selected resource's defaults and can affect
other analyzers using those mappings. Verify the target resource and use
existing deployment names. To add or update one mapping:

<!-- Snippet:defaults_model -->
```bash
cu defaults set --model gpt-5.2=custom-completion
```

Alternatively, apply the mappings saved in the active CU CLI profile. Review
them with `cu profile show` before running this command:

<!-- Snippet:defaults_from_profile -->
```bash
cu defaults set --from-profile
```

`cu defaults set` requires an explicit source:
`--from-profile`, one or more `--model MODEL=DEPLOYMENT` options, or both. A
bare `cu defaults set` command fails before contacting the service.

### Replace remote defaults

Updates normally merge with existing defaults. Use `--replace` only when you
intend to replace the mapping set. Review the current defaults first and
replace the example deployment names with your own.

The replacement keeps the supplied mappings plus automatically derived prebuilt
analyzer aliases. CU CLI reads the current defaults, then removes mappings
outside that set, so both read and update permissions are required. Unexpected
read failures prevent the update. Avoid concurrent defaults updates: the read
and PATCH are separate operations, not an atomic read-modify-write operation.

`--json` returns the update result:

<!-- Snippet:defaults_replace -->
```bash
cu defaults set --model gpt-5.2=custom-completion --model text-embedding-3-large=custom-embedding \
  --replace \
  --json
```

## Diagnostics and environment

### Check readiness

Run diagnostics after initial setup or when changing resources. These checks
read the service configuration without changing it. The second command uses
the existing `prod` profile without changing the active profile:

<!-- Snippet:diagnose_configuration -->
```bash
cu doctor
cu doctor --profile prod
```

`cu doctor` checks the API version, endpoint, authentication, service
connectivity, and Content Understanding defaults. It exits nonzero when a
required check fails, so scripts can use it as a readiness gate.

### Apply reviewed model mappings

`--fix-defaults` updates remote defaults on the selected Microsoft Foundry
resource. This can affect other analyzers using those mappings. Before running
it, check the target with `cu doctor` and review the local model mappings with
`cu profile show`. Use this repair command only when you intend to apply those
mappings to the resource:

<!-- Snippet:doctor_fix_defaults -->
```bash
cu doctor --fix-defaults
```

See [Environment overrides](#environment-overrides) for temporary configuration
and cleanup. Use `--info` on supported service commands when you need to inspect
their effective non-secret settings.

## Help and exit behavior

Every command has examples and supported-version information:

<!-- Snippet:cli_help_overview -->
```bash
cu --help
cu profile --help
cu analyzer copy --help
```

Command-line usage errors return status `2`. Operational and validation
failures return a nonzero status with an actionable CU CLI error rather than a
Python traceback. Batch analyze returns status `1` after reporting any
per-input failures. Successful commands return status `0`.

## Upgrade

Check the available package version without installing it:

<!-- Snippet:upgrade_check -->
```bash
cu upgrade --check
```

When you are ready to upgrade, the following command installs the update and
skips confirmation with `--yes`. On Windows, the CLI starts a detached upgrade
helper:

<!-- Snippet:upgrade_apply -->
```bash
cu upgrade --yes
```
