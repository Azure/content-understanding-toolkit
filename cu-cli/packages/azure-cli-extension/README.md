# Azure Content Understanding extension for Azure CLI

This preview extension adds Azure Content Understanding commands under `az cu`.
It uses the identity, cloud, and active subscription selected by Azure CLI and
supports standard Azure CLI output formats and JMESPath queries.

> [!IMPORTANT]
> This package is an implementation preview. The `az cu` command name and public
> Azure CLI extension registration remain subject to Azure CLI maintainer review.

## Content Understanding concepts

Content Understanding processes unstructured content, including documents,
images, audio, and video, into structured output for automation, analytics, and
search workflows. It is a Foundry Tool that you access through a Microsoft
Foundry resource in Azure.

The Content Understanding documentation uses these terms:

- A **file** is the input. It can be a document, image, audio file, video, or
	other [supported file type](https://learn.microsoft.com/azure/ai-services/content-understanding/service-limits#input-file-limits).
- An **analyzer** defines how Content Understanding processes a file and
	extracts content and structured fields.
- An **analyzer result** is the output from processing a file. It can include
	extracted Markdown content, structured fields, and modality-specific details.
- A **prebuilt analyzer** is a ready-to-use analyzer supplied by Content
	Understanding for common content extraction, search, and domain scenarios.
- A **custom analyzer** is an analyzer you define for your scenario. It uses a
	base analyzer for a content type and a field schema that describes the
	structured fields to extract.

The extension lets you configure a Microsoft Foundry resource, select an
analyzer, submit local files or URLs, and save analyzer results without calling
the REST API directly.

Further reading:

- [What is Content Understanding?](https://learn.microsoft.com/azure/ai-services/content-understanding/overview)
- [Content Understanding terminology](https://learn.microsoft.com/azure/ai-services/content-understanding/glossary)

## Install

Requirements:

- [Azure CLI](https://aka.ms/azcli)
- [Azure Developer CLI](https://aka.ms/azd) only when using
  `az cu infra generate`

Install the extension wheel produced by this repository. After extension-index
publication, installation by name will use
`az extension add --name content-understanding`.

```bash
# Install a locally built preview extension wheel.
az extension add --source ./content_understanding-0.1.0b1-py3-none-any.whl

# Show the installed extension commands.
az cu --help
```

## Connect to Microsoft Foundry and check setup

You need a Microsoft Foundry resource endpoint. LLM-based prebuilt analyzers and
custom analyzers also need supported LLM and embeddings deployments plus Content
Understanding defaults. If any of these are missing, follow the complete
[Microsoft Foundry provisioning guide](../../docs/provisioning.md).

Use either an Azure CLI login or a Microsoft Foundry resource API key for data-plane
authentication. Azure login also supplies cloud and subscription context for
resource-management operations. A shared CU profile supplies authentication,
the Microsoft Foundry endpoint, API version, and optional model-deployment mappings.
Configure the automatically available `default` profile for a ready resource:

```bash
# Sign in and select the Azure subscription used by az cu commands.
az login

# Save the Microsoft Foundry endpoint in the default CU profile.
az cu profile set \
	--key endpoint \
	--value https://<resource-name>.services.ai.azure.com/

# Verify endpoint connectivity, authentication, and model readiness.
az cu doctor --output table
```

To use key authentication without the Cognitive Services User role, save it in
the shared profile or pass it explicitly:

```bash
# Preferred: both `cu` and `az cu` reuse the saved key.
az cu profile set --key auth_mode --value key
az cu profile set --key api_key --value <resource-key>
az cu analyzer list

# One-command override. Avoid this form when shell history or process listings
# could expose the key.
az cu analyzer list --auth-mode key --api-key <resource-key> \
	--endpoint https://<resource-name>.services.ai.azure.com/
```

`CU_AUTH_MODE=key` with `CU_API_KEY` is also supported. Explicit
`--auth-mode login` selects Azure CLI authentication even when the profile has a key.

`az cu doctor` checks the API version, endpoint, selected authentication mode,
service connectivity, and Content Understanding defaults. It exits nonzero
when a required check fails, so it can serve as a readiness gate.

## Use `az cu` and `cu` interchangeably

The Azure CLI extension and standalone CU CLI are two frontends over the same
`cu-cli-core` operations. Install either frontend, or install both and move
between them for the same analyzer, analysis, defaults, profile, diagnostics,
and infrastructure-generation workflows.

Both frontends read and write the same `[cu]` profile settings in the active
Azure CLI configuration file (`~/.azure/config` by default, or the file under
`AZURE_CONFIG_DIR`). An endpoint, API version, default analyzer, active profile,
or model-deployment mapping saved with one frontend is immediately available to
the other. For example:

```bash
# Save the endpoint with the Azure CLI extension.
az cu profile set \
	--key endpoint \
	--value https://<resource-name>.services.ai.azure.com/

# Use the same default profile with the standalone frontend.
cu analyzer list

# Change the default analyzer with the standalone frontend.
cu profile set default_analyzer prebuilt-layout

# Use that setting with the Azure CLI extension.
az cu analyze --file document.pdf
```

The command names and capabilities overlap, but frontend conventions differ:

| Azure CLI extension | Standalone CU CLI |
| --- | --- |
| Starts commands with `az cu`. | Starts commands with `cu` (`cu-cli` on macOS). |
| Uses explicit options plus global Azure CLI `--output`, `--query`, and `--subscription`. | Supports standalone positional shortcuts and Rich/JSON output options. |
| Always uses the active `az login` identity; shared API keys and `auth_mode` do not override Azure CLI host authentication. | Uses the profile's `auth_mode` and can use a saved API key. |

Run `az cu <command> --help` or `cu <command> --help` when translating a command
between frontends. Profile values are shared; authentication sessions are not,
so sign in with `az login` before using `az cu`. An API key saved by standalone
`cu` is not used by `az cu`.

## Supported Content Understanding API versions

Known Content Understanding API versions are `2025-11-01` (GA) and
`2026-06-01-preview` (preview); other API versions that follow the
`YYYY-MM-DD-preview` format are also accepted.

The extension defaults to `2025-11-01`. Override the version for one command
with `--api-version`, save it to a profile, or set the `CU_API_VERSION`
environment variable. Run `az cu profile show` to see the effective version.

The preview API adds capabilities beyond the GA version. Inline analysis is the
only preview capability that requires a dedicated command option: `--inline`
runs supported analysis synchronously instead of using the default
long-running-operation polling flow.

```bash
# Run synchronous analysis with the preview API for this request.
az cu analyze \
	--file document.pdf \
	--analyzer prebuilt-layout \
	--inline \
	--api-version 2026-06-01-preview

# Save the preview API version to the active profile.
az cu profile set \
	--key api_version \
	--value 2026-06-01-preview
```

Pin production workloads that do not need preview capabilities to
`2025-11-01`.

Further reading:

- [What's new in the `2026-06-01-preview` API](https://learn.microsoft.com/azure/ai-services/content-understanding/whats-new#july-2026)
- Run `az cu analyze --help` for all analysis options.

## Use prebuilt analyzers

Download the public sample invoice so the following examples are runnable from
the current directory:

```bash
# Download the Azure Content Understanding sample invoice.
curl --fail --location --output invoice.pdf \
	https://raw.githubusercontent.com/Azure-Samples/azure-ai-content-understanding-assets/main/document/invoice.pdf
```

Inspect the available analyzers and start with `prebuilt-layout`. It extracts
text, paragraphs, tables, figures, and document structure without requiring a
language model or embeddings model:

```bash
# List all analyzers available on the configured resource.
az cu analyzer list --output table

# Analyze a document and format the result for generative AI model input.
az cu analyze \
	--file invoice.pdf \
	--analyzer prebuilt-layout \
	--llm-input
```

Without `--llm-input`, `az cu analyze` returns the complete structured analyzer
result through standard Azure CLI output. Use global `--output json` for JSON,
or combine `--llm-input` with `--output-file` to save Markdown formatted by the
Content Understanding SDK's `to_llm_input()` helper.

Domain-specific prebuilt analyzers, such as `prebuilt-invoice`, extract a
defined set of structured fields. They require the model setup described in
[Deploy models and configure defaults](../../docs/provisioning.md#deploy-models-and-configure-defaults):

```bash
# Show the prebuilt invoice analyzer definition.
az cu analyzer show --name prebuilt-invoice

# Analyze the downloaded invoice and return its complete structured result.
az cu analyze \
	--file invoice.pdf \
	--analyzer prebuilt-invoice \
	--output json
```

Use standard Azure CLI queries to select results. This example lists the
mortgage analyzer IDs documented under
[`prebuilt-schema/2025-11-01/mortgage.us`](../../../prebuilt-schema/2025-11-01/mortgage.us):

```bash
# Return only analyzer IDs whose names start with prebuilt-mortgage.
az cu analyzer list \
	--query "[?starts_with(analyzerId, 'prebuilt-mortgage')].analyzerId" \
	--output tsv
```

Analyze remote input without downloading it first:

```bash
# Analyze the public sample invoice directly from its HTTPS URL.
az cu analyze \
	--url https://raw.githubusercontent.com/Azure-Samples/azure-ai-content-understanding-assets/main/document/invoice.pdf \
	--analyzer prebuilt-invoice
```

Azure Blob SAS parameters are sent to the service but redacted from reports and
errors. Large batches require confirmation unless `--yes` is supplied.

Analyze several files into one output directory:

```bash
# Analyze PDF files and preserve their source-relative paths under results.
az cu analyze \
	--source ./documents \
	--pattern "*.pdf" \
	--output-dir ./results \
	--analyzer prebuilt-layout \
	--yes
```

Each result is written under `./results`. Use `--dry-run` to inspect the local
execution plan before service calls or writes, and use `--report-file` to retain
a machine-readable per-input status report.

Further reading:

- [Prebuilt analyzers](https://learn.microsoft.com/azure/ai-services/content-understanding/concepts/prebuilt-analyzers)
- [Supported input files and service limits](https://learn.microsoft.com/azure/ai-services/content-understanding/service-limits#input-file-limits)
- [Content Understanding SDK `to_llm_input()` helper](https://learn.microsoft.com/azure/ai-services/content-understanding/whats-new#april-2026)
- Run `az cu analyze --help` for input, output, overwrite, concurrency, and
  reporting options.

## Create a custom analyzer

A custom analyzer lets you define the structured fields needed by your
application. Its analyzer schema identifies a base analyzer for the content
type and includes a field schema that describes the field names, value types,
and generation methods.

Custom analyzers require supported model deployments and configured Content
Understanding defaults. Inspect defaults, create and validate a schema, create
an analyzer, and test it:

```bash
# Show the resource's model-to-deployment defaults.
az cu defaults show --output table

# Derive a starter extraction schema from the sample invoice.
az cu analyzer schema create \
	--from-sample invoice.pdf \
	--output-file invoice-schema.json

# Validate the edited schema before sending it to the service.
az cu analyzer validate \
	--schema invoice-schema.json \
	--spec \
	--strict

# Create a custom analyzer after reviewing and editing the generated schema.
az cu analyzer create \
	--name invoice_v1 \
	--schema invoice-schema.json

# Run the custom analyzer over the sample and write a structured test report.
az cu analyzer test \
	--name invoice_v1 \
	--file invoice.pdf \
	--output-file test-report.json \
	--yes
```

Schema generation preserves existing files by default. Pass `--force` only
when you intentionally want to replace the selected `--output-file`.

Further reading:

- [Create a custom analyzer](https://learn.microsoft.com/azure/ai-services/content-understanding/tutorial/create-custom-analyzer)
- [Supported generative models](https://learn.microsoft.com/azure/ai-services/content-understanding/service-limits#supported-generative-models)
- Run `az cu analyzer --help` for analyzer management and testing commands.

## Generate Microsoft Foundry infrastructure

`az cu infra generate` writes a self-contained azd/Bicep project. It does not
provision resources or run `azd up`. On a terminal it offers subscription,
resource, region, model, and RBAC choices; use `--yes` for deterministic
automation.

```bash
# Generate the project interactively using Azure CLI subscription context.
az cu infra generate --output-dir provision

# Enter the generated project directory.
cd provision

# Authenticate Azure Developer CLI for infrastructure deployment.
azd auth login

# Provision the generated project and run its az cu post-provision setup.
azd up
```

Generated hooks use the internal `az cu infra _models` helper and do not require
the standalone `cu-cli` package.

## Command overview

| Command | Purpose |
| --- | --- |
| `az cu analyze` | Analyze local files, directories, or HTTPS URLs. |
| `az cu analyzer` | List, show, create, copy, delete, validate, and test analyzers and schemas. |
| `az cu defaults` | Read or configure model-to-deployment defaults. |
| `az cu profile` | Manage local endpoint, API version, and model settings. |
| `az cu infra generate` | Generate an azd/Bicep project; the user runs `azd up`. |
| `az cu doctor` | Return structured connectivity and readiness checks. |
| `az cu env-var list` | Inspect recognized environment variables with secrets redacted. |

This extension intentionally does not register direct provisioning or
self-upgrade. Update an indexed installation with
`az extension update --name content-understanding`.

Every command provides examples:

```bash
# Show profile-management examples and options.
az cu profile --help

# Show cross-resource analyzer-copy examples and options.
az cu analyzer copy --help

# Show infrastructure-generation examples and options.
az cu infra generate --help
```

## CU CLI usage guide

Use this README for installation, resource connection, and the first successful
analysis. For Azure provisioning, see the
[Microsoft Foundry provisioning guide](../../docs/provisioning.md). For detailed
operational guidance shared by both frontends, see the
[CU CLI usage guide](../../docs/usage-guide.md). It explains:

- profile resolution and environment-variable overrides
- safe batch previews, output handling, and machine-readable reports
- analyzer schema, lifecycle, testing, and cross-resource copy workflows
- Content Understanding defaults and troubleshooting

The usage guide uses standalone `cu` syntax. Use `az cu <command> --help` for
the equivalent Azure CLI options.

## More information

- [Azure Content Understanding documentation](https://aka.ms/cu-doc)
- [Standalone CU CLI README](../../README.md)
- [Support](../../SUPPORT.md)
- [Contributing](../../CONTRIBUTING.md)

## Implementation boundary

The runtime depends on `cu-cli-core`, not the standalone `cu_cli` package, and
does not import Click or Rich. The wheel contains a build-time snapshot of the
repository's canonical azd/Bicep template. Microsoft Entra authentication uses
the active Azure CLI host credential. This preview supports AzureCloud only.

## Use multiple profiles

If you work with multiple resources, create named profiles and either activate
one or select it per command:

```bash
# Create and configure development and production profiles.
az cu profile create --name dev
az cu profile set \
	--key endpoint \
	--value https://<dev-resource>.services.ai.azure.com/ \
	--name dev
az cu profile create --name prod
az cu profile set \
	--key endpoint \
	--value https://<prod-resource>.services.ai.azure.com/ \
	--name prod

# Activate dev, or select prod for only one command.
az cu profile set-active --name dev
az cu analyzer list
az cu analyzer list --profile prod
az cu doctor --profile prod
```

Profiles are shared with standalone `cu`. See the
[CU CLI profile usage guide](../../docs/usage-guide.md#cu-cli-profiles) for
profile resolution and environment-variable overrides.
