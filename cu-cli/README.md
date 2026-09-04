# CU CLI

`cu` is the preview command-line interface for Azure Content Understanding in
Foundry Tools. Use it to provision the required Microsoft Foundry resource,
optionally deploy selected supported large language models (LLMs) and embeddings
models, configure Content Understanding defaults, analyze local files, manage
analyzers, and configure CU CLI profiles.

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

CU CLI also uses a **profile**, which is local CLI configuration for one
Microsoft Foundry resource. A profile isn't an Azure resource. It tells CU CLI
which resource endpoint, authentication method, and API version to use, and it
can store model deployment mappings for Content Understanding defaults setup.

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
polling flow. This can simplify scripting for small, low-latency inputs.

```bash
cu analyze --inline --api-version 2026-06-01-preview document.pdf --analyzer prebuilt-layout
```

Save the preview version to a profile to avoid passing `--api-version` on
every call: `cu profile set api_version 2026-06-01-preview`. Preview API
versions may change behavior before they reach GA; pin to `2025-11-01` for
production workloads that don't need preview capabilities.

Further reading:

- [What's new in the `2026-06-01-preview` API](https://learn.microsoft.com/azure/ai-services/content-understanding/whats-new#july-2026)
- Run `cu analyze --help` for all analyze options.

## Provision and configure Azure resources

To use Content Understanding, you need an Azure subscription and a Microsoft
Foundry resource in a supported region. This is the resource described in the
[Content Understanding documentation](https://aka.ms/cu-doc) and is separate
from a local CU CLI profile.

Content Understanding uses Foundry model deployments for operations that
require generative AI. A **model deployment** makes a supported Foundry model
available under a deployment name in your Microsoft Foundry resource. These
operations require a supported large language model (LLM) for chat completion
and an embeddings model. **Content Understanding defaults** map supported model
names and prebuilt analyzer model aliases to those deployment names. Setting
these defaults once on the resource means analyze requests don't need to provide
the mappings. CU CLI manages them with the `cu defaults` command.

The `prebuilt-digitalParse`, `prebuilt-read`, and `prebuilt-layout` content
extraction analyzers don't require a language model or embeddings model. Other
prebuilt analyzers and custom analyzers require the model deployments supported
by that analyzer.

`cu infra generate` generates an azd/Bicep template; it does not run a deployment.
Run `azd up` from the generated `./provision` directory to provision the
required Microsoft Foundry resource. It can also deploy selected supported LLMs
and embeddings models, configure Content Understanding defaults, and configure
the automatic `default` CU CLI profile with `prebuilt-layout` as its default
analyzer.

### Azure permissions

`cu infra generate` only writes files and performs control-plane discovery. It
does not deploy resources or call the Content Understanding data plane.

The generated project supports two deployment paths:

- **Create a new Microsoft Foundry resource**: `azd up` creates a new resource
  group, a Microsoft Foundry resource (an Azure AI Services account with kind
  `AIServices`), a Foundry project, and the selected model deployments.
- **Use an existing Microsoft Foundry resource**: `azd up` reuses the selected
  Microsoft Foundry resource and its resource group. It does not create another
  resource group, Foundry resource, or Foundry project, but it does create the
  selected model deployments on that resource.

The generated Bicep deploys at subscription scope in both paths. Use the
following scenarios to determine the required access:

During the new-resource path, `azd up` can optionally assign three roles on the
new Microsoft Foundry resource to the current user or service principal running
azd:

- **Cognitive Services User**
- **Cognitive Services OpenAI User**
- **Azure AI Developer**

This role-assignment step only grants that principal Entra-based access to the
new resource so CU CLI can authenticate without a resource key. It does not
grant these roles to other users. Apart from these assignments, the step does
not change access for any other identity. The existing-resource path does not
create role assignments.

| Scenario | Required access |
| --- | --- |
| Create a new Microsoft Foundry resource **and automatically assign roles** | One of:<ul><li><strong>Owner</strong> on the selected subscription</li><li><strong>Contributor</strong> plus <strong>Role Based Access Control Administrator</strong> on the selected subscription</li><li><strong>Contributor</strong> plus <strong>User Access Administrator</strong> on the selected subscription</li></ul> |
| Create a new Microsoft Foundry resource **without assigning roles** | One of:<ul><li><strong>Contributor</strong> on the selected subscription</li><li><strong>Owner</strong> on the selected subscription</li><li>A custom role with equivalent permissions</li></ul>The identity needs permission to create the resource group, Foundry resource and project, and model deployments. If you have Contributor only, decline the role-assignment prompt; the generated post-provision step uses key authentication. |
| Use an existing Microsoft Foundry resource | One of:<ul><li><strong>Contributor</strong> on the selected subscription</li><li>A narrower custom role with the required subscription deployment and resource actions</li></ul>The identity needs permission to run the subscription-scope deployment and create model deployments on the selected Microsoft Foundry resource. This path does not create role assignments. |
| Use CU CLI with Microsoft Entra ID authentication | <ul><li><strong>Cognitive Services User</strong> on the Microsoft Foundry resource</li></ul>This grants the Content Understanding data-plane access used to configure defaults and create, manage, and run analyzers. Owner and Contributor do not include this access. |
| Use CU CLI with key authentication | <ul><li>A valid resource key</li></ul><strong>Cognitive Services User</strong> is not required for requests authenticated with that key. |

For a new Microsoft Foundry resource, `azd up` can assign **Cognitive Services
User** when automatic role assignment is enabled. For an existing Microsoft
Foundry resource, grant the identity this role first (Azure portal → the
Microsoft Foundry resource → **Access control (IAM)** → **Add role assignment**
→ **Cognitive Services User**). Without it, Entra-authenticated commands such
as `cu defaults set`, `cu analyzer create`, and `cu analyze` fail with an
authorization error.

See [Azure built-in privileged roles](https://learn.microsoft.com/azure/role-based-access-control/built-in-roles/privileged#contributor)
and [Cognitive Services User](https://learn.microsoft.com/azure/role-based-access-control/built-in-roles/ai-machine-learning#cognitive-services-user)
for the current role definitions.

Before running `cu infra generate`, sign in to both command-line tools. Azure CLI and
Azure Developer CLI use separate sign-in sessions:

```bash
az login
azd auth login
```

Choose the setup that matches your current Azure resources.
After completing the applicable setup, continue through the sections below to:

1. Check the resulting configuration with `cu doctor`.
2. Review or customize the CU CLI profile.
3. Run a prebuilt analyzer.
4. Optionally create a custom analyzer after its required model deployments and
   Content Understanding defaults are ready.

### Azure subscription, but no supported-region Microsoft Foundry resource

Create a Microsoft Foundry resource in a
[Content Understanding supported region](https://learn.microsoft.com/azure/ai-services/content-understanding/language-region-support#region-support).
Select the region in the interactive wizard, or pass it with `--location`.
Choose `--models none` when you want to start with content extraction analyzers
that don't require model deployments:

```bash
cu infra generate --location <supported-region> --models none
cd provision
azd up
```

After the resource endpoint and authentication are configured,
`prebuilt-digitalParse`, `prebuilt-read`, and `prebuilt-layout` are available.
Other prebuilt analyzers and custom analyzers are not ready until their required
models are deployed and Content Understanding defaults are set.

### Microsoft Foundry resource, but no required model deployments

Point `cu infra generate` at the existing resource and let the generated
post-provision hook deploy a recommended LLM and embeddings model, configure
Content Understanding defaults, and update the default CU CLI profile:

```bash
cu infra generate \
  --foundry-endpoint https://<resource-name>.services.ai.azure.com/ \
  --models recommended
cd provision
azd up
```

Model availability and quota vary by region. See
[Supported generative models](https://learn.microsoft.com/azure/ai-services/content-understanding/service-limits#supported-generative-models)
for the current requirements. Omit `--models` to choose models interactively.

### Microsoft Foundry resource and model deployments already exist

You do not need `cu infra generate`. Configure the local CU CLI profile first, then
configure Content Understanding defaults. The command is `cu defaults set`
(plural):

> **Note:** `cu defaults set` requires the **Cognitive Services User** role on
> the resource — see
> [Provision and configure Azure resources](#provision-and-configure-azure-resources)
> above.

```bash
# Point the active CU CLI profile to your existing Microsoft Foundry resource.
cu profile set endpoint https://<resource-name>.services.ai.azure.com/

# Login authentication is the default; you don't need to set auth_mode.
# cu profile set auth_mode login

# Sign in through Azure CLI. This doesn't change the CU CLI profile.
az login

# Replace these examples with the model names and deployment names from your resource.
cu defaults set \
  --model gpt-5.2=my-gpt-52-deployment \
  --model text-embedding-3-large=my-embedding-deployment

# Copy the resource's Content Understanding defaults into the active local profile.
cu profile sync-defaults
```

`cu defaults set` configures Content Understanding defaults by mapping model
names to deployment names. `cu profile sync-defaults` copies those mappings into
the active local CU CLI profile. If the mappings are already saved in the active
profile instead, push them to the resource with `cu defaults set --from-profile`.

The post-provision hook reports which workflows are ready and provides focused
repair guidance for missing models, quota failures, or default model deployment
failures. An optional model deployment failure does not prevent CU CLI profile
setup or use of content extraction analyzers that don't require models.

Further reading:

- [Create a Microsoft Foundry resource](https://learn.microsoft.com/azure/ai-services/content-understanding/how-to/create-multi-service-resource)
- [Content Understanding regions and languages](https://learn.microsoft.com/azure/ai-services/content-understanding/language-region-support)
- [Supported generative models and service limits](https://learn.microsoft.com/azure/ai-services/content-understanding/service-limits)
- [Model deployment options for analyzers](https://learn.microsoft.com/azure/ai-services/content-understanding/concepts/models-deployments)
- [Content Understanding setup quickstart](https://learn.microsoft.com/azure/ai-services/content-understanding/quickstart/content-understanding-studio)

## Check setup with `cu doctor`

After provisioning or manually configuring a resource, verify the active CU CLI
profile before analyzing content:

```bash
cu doctor
```

`cu doctor` checks the API version, Microsoft Foundry resource endpoint,
authentication, service connectivity, and Content Understanding defaults. It
exits nonzero when a required check fails, so scripts and coding agents can use
it as a readiness gate. Check a named profile without activating it with
`cu doctor --profile NAME`.

If locally configured model mappings need to be applied as Content
Understanding defaults, review them first with `cu profile show`, then run:

```bash
cu doctor --fix-defaults
```

Further reading:

- [Content Understanding REST API quickstart](https://learn.microsoft.com/azure/ai-services/content-understanding/quickstart/use-rest-api)
- Run `cu doctor --help` for all checks and repair options.

## Configure CU CLI profiles

A CU CLI profile is local CLI configuration for a Microsoft Foundry resource.
It stores the resource endpoint, authentication method, Content Understanding
API version, and model deployment mappings used by CU CLI commands. A profile
doesn't create or change an Azure resource by itself.

CU CLI provides an automatic `default` profile. If you use one resource, set
values on that profile directly; there is no profile-creation step:

```bash
cu profile set endpoint https://<resource-name>.services.ai.azure.com/
# Login authentication is the default; you don't need to set auth_mode.
# cu profile set auth_mode login
az login
cu profile show
```

For key authentication:

```bash
cu profile set api_key <key>
cu profile show
```

The API key is redacted by `cu profile get` and `cu profile show`.

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
```

Further reading:

- [CU CLI profile usage guide](docs/usage-guide.md#cu-cli-profiles)
- [Secure communications for Content Understanding](https://learn.microsoft.com/azure/ai-services/content-understanding/concepts/secure-communications)

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
[Provision and configure Azure resources](#provision-and-configure-azure-resources):

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
[Microsoft Foundry resource and model deployments already exist](#microsoft-foundry-resource-and-model-deployments-already-exist)
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

Use this README for installation, Azure resource setup, and the first successful
analysis. For detailed operational guidance, see the
[CU CLI usage guide](docs/usage-guide.md). It explains:

- CU CLI profile resolution and environment-variable overrides
- safe batch previews, output handling, and machine-readable reports
- analyzer schema, lifecycle, testing, and cross-resource copy workflows
- Content Understanding defaults and troubleshooting

## More information

- [Azure Content Understanding documentation](https://aka.ms/cu-doc)
- [Support](SUPPORT.md)
- [Contributing](CONTRIBUTING.md)

The standalone distribution is `cu-cli`. It depends on the separately built
`cu-cli-core` implementation package in this same product tree. `cu-cli-core`
is an internal implementation boundary for official CU command-line frontends;
install and use `cu-cli` rather than importing the core package directly.
