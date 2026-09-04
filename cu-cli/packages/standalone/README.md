# CU CLI

`cu` is the preview command-line interface for Azure Content Understanding in
Foundry Tools. Use it to provision the required Microsoft Foundry resource,
optionally deploy selected supported large language models (LLMs) and embeddings
models, configure Content Understanding defaults, analyze local files, manage
analyzers, and manage local configuration.

> [!IMPORTANT]
> CU CLI is in preview. Commands and package contracts may change before general
> availability.

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

CU CLI lets you configure a Microsoft Foundry resource, select an analyzer,
submit local files, and save analyzer results without calling the REST API
directly.

Further reading:

- [What is Content Understanding?](https://learn.microsoft.com/azure/ai-services/content-understanding/overview)
- [Content Understanding terminology](https://learn.microsoft.com/azure/ai-services/content-understanding/glossary)

## Install

Requirements:

- Python 3.10 or later
- [Azure CLI](https://aka.ms/azcli) for login and resource discovery
- [Azure Developer CLI](https://aka.ms/azd) only when using `cu infra generate`

```bash
python -m pip install cu-cli
cu --version
cu --help
```

macOS includes an unrelated system command named `cu`. Use the equivalent
`cu-cli` executable on macOS:

```bash
cu-cli --help
```

## Connect to Microsoft Foundry and check setup

You need a Microsoft Foundry resource endpoint. LLM-based prebuilt analyzers and
custom analyzers also need supported LLM and embeddings deployments plus Content
Understanding defaults. If any of these are missing, follow the complete
[Microsoft Foundry provisioning guide](https://github.com/Azure/content-understanding-toolkit/blob/main/cu-cli/docs/provisioning.md).

A CU CLI profile is local configuration for one Microsoft Foundry resource. It
stores the endpoint, authentication method, API version, and optional model
deployment mappings; it is not an Azure resource. For a ready resource,
configure the automatically available `default` profile. With Microsoft Entra
ID authentication:

```bash
cu profile set endpoint https://<resource-name>.services.ai.azure.com/
cu profile set auth_mode login
az login
cu doctor
```

Alternatively, use a resource key:

```bash
cu profile set endpoint https://<resource-name>.services.ai.azure.com/
cu profile set api_key <key>
cu doctor
```

The API key is redacted by `cu profile get` and `cu profile show`. `cu doctor`
checks the API version, endpoint, authentication, service connectivity, and
Content Understanding defaults. It exits nonzero when a required check fails,
so it can serve as a readiness gate.

## Supported Content Understanding API versions

Content Understanding API version. Known versions: 2025-11-01 (GA) and
2026-06-01-preview (preview); any YYYY-MM-DD-preview version is also accepted.

CU CLI defaults to `2025-11-01`. Override the version with `cu profile set
api_version <version>`, the `--api-version` flag, or the `CU_API_VERSION`
environment variable; run `cu profile show` to see the active profile's
configured version.

The preview API adds capabilities beyond the GA version. CU CLI returns
result-based capabilities, such as document metadata and signatures, through
the normal analysis result without dedicated CLI options. Inline analysis is
the only preview capability that requires a new CU CLI option:
`cu analyze --inline` runs supported analysis synchronously and returns the
result directly instead of using the default long-running-operation (LRO)
polling flow.

```bash
cu analyze --inline --api-version 2026-06-01-preview document.pdf --analyzer prebuilt-layout
```

Save the preview version to a profile to avoid passing `--api-version` on every
call: `cu profile set api_version 2026-06-01-preview`. Pin to `2025-11-01` for
production workloads that don't need preview capabilities.

Further reading:

- [What's new in the `2026-06-01-preview` API](https://learn.microsoft.com/azure/ai-services/content-understanding/whats-new#july-2026)
- Run `cu analyze --help` for all analyze options.

## Use prebuilt analyzers

List the prebuilt analyzers available to the configured resource:

```bash
cu analyzer list
```

Start with the `prebuilt-layout` content extraction analyzer. It extracts text,
paragraphs, tables, figures, and document structure without requiring a language
model or embeddings model. `-a` is the short form of `--analyzer`:

```bash
# Generate Markdown from the analyzer result with the CU SDK's to_llm_input().
cu analyze ./document.pdf -a prebuilt-layout
```

Markdown generated by the Content Understanding SDK's `to_llm_input()` helper is
the default output format. The helper formats field extraction results as
Markdown with YAML frontmatter so they can be used as generative AI model input.
Use `--llm-input` to select this default view explicitly, or use `--json` to
return the complete analyzer result as JSON. See the
[Content Understanding SDK `to_llm_input()` helper](https://learn.microsoft.com/azure/ai-services/content-understanding/whats-new#april-2026).

Domain-specific prebuilt analyzers, such as `prebuilt-invoice`, extract a
defined set of structured fields. They require the model setup described in
[Deploy models and configure defaults](https://github.com/Azure/content-understanding-toolkit/blob/main/cu-cli/docs/provisioning.md#deploy-models-and-configure-defaults):

```bash
cu analyze ./invoice.pdf --analyzer prebuilt-invoice --json
```

The command returns an analyzer result. Use `--json` when you want the
structured result as JSON.

Analyze several files into one output directory. `--pattern` requires
`--source`, because a positional path can be either a file or a directory and
`--pattern` only makes sense once a directory is named explicitly:

```bash
cu analyze --source ./documents --pattern "*.pdf" --output-dir ./results
```

Each result is written under `./results` and keeps the input path relative to
`./documents`. For example, `./documents/invoice-01.pdf` produces
`./results/invoice-01.pdf.result.md`. Markdown results use the
`.result.md` suffix; adding `--json` produces `.result.json` files instead.

Further reading:

- [Prebuilt analyzers](https://learn.microsoft.com/azure/ai-services/content-understanding/concepts/prebuilt-analyzers)
- [Supported input files and service limits](https://learn.microsoft.com/azure/ai-services/content-understanding/service-limits#input-file-limits)
- Run `cu analyze --help` for input, output, overwrite, concurrency, and reporting options.

## Create a custom analyzer

A custom analyzer lets you define the structured fields needed by your
application. Its analyzer schema identifies a base analyzer for the content type
and includes a field schema that describes the field names, value types, and
generation methods.

Custom analyzers require supported model deployments and configured Content
Understanding defaults. Confirm the model-to-deployment mappings before creating
the analyzer:

```bash
# Show the Content Understanding defaults configured on the resource.
cu defaults show
```

If the required mappings are missing, follow
[Configure defaults manually](https://github.com/Azure/content-understanding-toolkit/blob/main/cu-cli/docs/provisioning.md#configure-defaults-manually)
to configure them. Then generate a starter analyzer schema from a representative
file:

```bash
# Generate a schema from a representative document.
cu analyzer schema create \
  --from-sample ./invoice.pdf \
  --output-file ./invoice-schema.json

# Review and update the generated schema for your extraction requirements,
# then create the analyzer.
cu analyzer create --name invoice_v1 --schema ./invoice-schema.json

# Run the analyzer against the sample and summarize whether fields were returned
# and any confidence values supplied by the service. This is not an accuracy
# benchmark and does not compare the result with labeled ground truth.
cu analyzer test invoice_v1 ./invoice.pdf

cu analyze ./invoice.pdf --analyzer invoice_v1 --json
```

Schema generation preserves existing files by default. Pass `--force` only when
you intentionally want to replace the selected `--output-file`.

Further reading:

- [Create a custom analyzer](https://learn.microsoft.com/azure/ai-services/content-understanding/tutorial/create-custom-analyzer)
- [Supported generative models](https://learn.microsoft.com/azure/ai-services/content-understanding/service-limits#supported-generative-models)
- Run `cu analyzer --help` for analyzer management and testing commands.

## Command overview

| Command | Purpose |
| --- | --- |
| `cu analyze` | Analyze local files and return analyzer results. |
| `cu analyzer` | List, show, create, copy, delete, and test analyzers; create and validate local analyzer schemas. |
| `cu defaults` | Read or configure Content Understanding defaults that map models to deployments. |
| `cu profile` | Manage local CU CLI endpoint, authentication, API, and model settings. |
| `cu infra generate` | Generate an azd/Bicep project used to provision a Microsoft Foundry resource and configure Content Understanding. Run `azd up` to provision it. |
| `cu doctor` | Verify the active CU CLI profile, authentication, and model readiness. |
| `cu env-var` | Inspect supported environment-variable overrides. |

Every command provides examples:

```bash
cu profile --help
cu analyzer copy --help
cu infra generate --help
```

## CU CLI usage guide

Use this README for installation, resource connection, and the first successful
analysis. For Azure provisioning, see the
[Microsoft Foundry provisioning guide](https://github.com/Azure/content-understanding-toolkit/blob/main/cu-cli/docs/provisioning.md). For detailed
operational guidance, see the
[CU CLI usage guide](https://github.com/Azure/content-understanding-toolkit/blob/main/cu-cli/docs/usage-guide.md). It explains:

- CU CLI profile resolution and environment-variable overrides
- safe batch previews, output handling, and machine-readable reports
- analyzer schema, lifecycle, testing, and cross-resource copy workflows
- Content Understanding defaults and troubleshooting

## More information

- [Azure Content Understanding documentation](https://aka.ms/cu-doc)
- [Support](https://github.com/Azure/content-understanding-toolkit/blob/main/cu-cli/SUPPORT.md)
- [Contributing](https://github.com/Azure/content-understanding-toolkit/blob/main/cu-cli/CONTRIBUTING.md)

The standalone distribution is `cu-cli`. It depends on the separately built
`cu-cli-core` implementation package in this same product tree. `cu-cli-core`
is an internal implementation boundary for official CU command-line frontends;
install and use `cu-cli` rather than importing the core package directly.

## Telemetry

CU CLI adds `cu-cli/<version>` to the standard Azure SDK `User-Agent` header on
requests to the Azure Content Understanding service. Microsoft uses this
identifier to understand CU CLI adoption. CU CLI does not add customer content
or separate usage and analytics events to this telemetry.

To remove the `cu-cli/<version>` identifier, set `CU_TELEMETRY=off` (also
accepts `0`, `false`, or `no`) before running CU CLI. The Azure SDK continues to
send its standard `User-Agent` as part of service requests. See the repository
[data collection notice](https://github.com/Azure/content-understanding-toolkit#data-collection)
for more information.

## Use multiple profiles

If you work with multiple resources, create named profiles and either activate
one or select it per command:

```bash
cu profile create dev
cu profile set endpoint https://<dev-resource>.services.ai.azure.com/ --name dev
cu profile create prod
cu profile set endpoint https://<prod-resource>.services.ai.azure.com/ --name prod

cu profile set-active dev
cu analyzer list
cu analyzer list --profile prod
cu doctor --profile prod
```

See the [CU CLI profile usage guide](https://github.com/Azure/content-understanding-toolkit/blob/main/cu-cli/docs/usage-guide.md#cu-cli-profiles) for
profile resolution and environment-variable overrides.
