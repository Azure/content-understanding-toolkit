# Azure Content Understanding starter (azd template)

Provision a Microsoft Foundry resource and project, configure a local CU CLI
profile, and optionally deploy selected supported large language models (LLMs)
and embeddings models
supported by the selected Content Understanding API version. The model
deployments enable prebuilt analyzers such as `prebuilt-invoice` and custom
analyzers. The template also configures Content Understanding defaults that map
model names to deployment names. It is purpose-built as a launchpad for
**Azure Content Understanding in Foundry Tools** workflows and the
[`cu` CLI](https://github.com/Azure/content-understanding-toolkit/tree/main/cu-cli).
```sh
azd init --template kmuthukrishn/content-understanding-starter
azd env new dev
azd env set AZURE_LOCATION eastus2
azd up
```

That's it. No app code, no Container Apps, no AI Search — just the bits you
need to start authoring analyzers.

## Permissions required for `azd up`

This template deploys at subscription scope. For the complete new-resource
path, the identity running `azd up` needs **Contributor** or **Owner** on the
selected subscription, or a custom role with equivalent permissions. This
allows the deployment to create the resource group, Foundry resource and
project, and selected model deployments.

Contributor cannot create Azure role assignments. If the deployment should
also assign the generated data-plane roles, the identity additionally needs
**Role Based Access Control Administrator**, **User Access Administrator**, or
**Owner** on the subscription. If you have Contributor only, set
`AZURE_ASSIGN_ROLES` to `false`; the post-provision hook uses resource-key
authentication instead.

With Entra authentication, CU CLI also requires **Cognitive Services User** on
the Microsoft Foundry resource to configure defaults and create, manage, and run
analyzers. This is data-plane access and is not included in Owner or
Contributor.

## What gets provisioned

| Resource | Purpose |
| --- | --- |
| Resource group `rg-<env>` | Container for everything |
| `Microsoft.CognitiveServices/accounts` (kind `AIServices`) | Microsoft Foundry resource that exposes Content Understanding and other Foundry Tools through one endpoint |
| `Microsoft.CognitiveServices/accounts/projects` | Foundry project (defaults to `proj-<env>`) |
| `Microsoft.CognitiveServices/accounts/deployments` | Models selected from the live Content Understanding and Microsoft Foundry resource catalogs, or none |
| Role assignments on the calling user | `Cognitive Services User`, `Cognitive Services OpenAI User`, `Azure AI Developer` — enough for Entra-auth data-plane access from `cu` |

The resource endpoint is `https://<resource-name>.services.ai.azure.com/` — the same
host that serves `/contentunderstanding/...`, `/openai/...`, and the Foundry
project API.

If `FOUNDRY_EXISTING_ENDPOINT` is set, this template skips resource and project
creation and performs the same live discovery against that existing resource.

## Microsoft Foundry resource naming

The Microsoft Foundry resource name must be globally unique because it becomes part of a
public DNS hostname:

`https://<resource-name>.services.ai.azure.com/`

By default, this template uses `aif-<unique-suffix>`. To make the name more
meaningful, set an optional prefix and azd will construct:

`<prefix>-<unique-suffix>`

Example:

```sh
azd env set FOUNDRY_RESOURCE_PREFIX yslincu
azd up
```

This produces resource names like `yslincu-xbrzt4yrmiexg`.

## Live model setup

The first infrastructure deployment intentionally creates the Foundry resource
with an empty `infra/models.json`. The post-provision hook then:

1. Calls `GET prebuilt-document` with `CU_API_VERSION`.
2. Reads `supportedModels.completion` and `supportedModels.embedding`.
3. Calls `az cognitiveservices account list-models` for the provisioned resource.
4. Shows only model versions present in both live catalogs.
5. Deploys the selection and writes it to `infra/models.json`, making subsequent
   Bicep runs repeatable.

Choose `0` to deploy no models. In that mode, `prebuilt-digitalParse`,
`prebuilt-read`, and `prebuilt-layout` are available without language or
embeddings model deployments.
Set `CU_MODEL_SELECTION=recommended` for noninteractive selection or
`CU_MODEL_SELECTION=none` for deterministic setup without model deployments.

The generated hook runs `cu _infra-models`, so keep the `cu` CLI installed and
on `PATH` when running `azd up` (`cu-cli` on macOS). A saved `prompt` selection
requires an interactive terminal; set `CU_MODEL_SELECTION=recommended`, `none`,
or explicit `model@version` selectors for unattended runs. Model setup failures
are reported without blocking CU CLI profile configuration. Resolve the model
deployment issue and rerun `azd up`; `prebuilt-digitalParse`, `prebuilt-read`,
and `prebuilt-layout` remain available without language or embeddings models.

## Auto-configuring the CU CLI profile

After live model setup, the post-provision hook automatically runs:

```sh
cu profile set endpoint <FOUNDRY_ENDPOINT>
cu profile set default_analyzer prebuilt-layout
cu doctor

# safe first sanity check (no language or embeddings model required):
cu analyze <file> --analyzer prebuilt-layout

# When model deployments and Content Understanding defaults are ready:
cu analyzer schema create --from-sample <file> --output-file schema.json
cu analyzer create --name my-analyzer --schema schema.json
cu analyze <file> --analyzer my-analyzer
```

so the freshly provisioned resource is saved in the default CU CLI profile
immediately after `azd up`, with `prebuilt-layout` configured as the default
analyzer. The hook prints the redacted `cu profile show --name default` result.
If the default profile already has saved values, the hook preserves it and
explains how to rerun `cu infra generate --force` before `azd up` to replace values.

The post-provision hook only prints the custom-analyzer workflow after it
verifies succeeded chat completion and embeddings model deployments and
configures Content Understanding defaults. Otherwise it prints the specific
repair action and retains the `prebuilt-layout` sanity check.

On macOS, use `cu-cli` in place of `cu` (macOS ships a built-in `cu` command).

Profile setup is automatic and requires no environment variable. To opt out,
set `CU_DISABLE_AUTO_PROFILE_SETUP=true` before `azd up`. Generated templates
also honor the legacy `CU_AUTOCONFIG=false` setting. This does not disable live
model setup; use `azd env set CU_MODEL_SELECTION none` to skip model deployments.

## Cleanup

```sh
azd down --purge
```

The `--purge` flag is important — Microsoft Foundry resource names are
soft-deleted for 48h after `azd down`, and a follow-up `azd up` in the same
environment would otherwise fail.

## Outputs

After `azd up`, `azd env get-values` exposes:

| Variable | Notes |
| --- | --- |
| `FOUNDRY_ENDPOINT` | `https://<resource-name>.services.ai.azure.com/` |
| `FOUNDRY_EXISTING_ENDPOINT` | Optional existing endpoint to reuse instead of provisioning a new resource |
| `FOUNDRY_EXISTING_RESOURCE_GROUP` | Resource group for `FOUNDRY_EXISTING_ENDPOINT` |
| `FOUNDRY_PROJECT_ENDPOINT` | Project-scoped URL (`/api/projects/<project>`) |
| `FOUNDRY_RESOURCE_NAME` | Account name (also the custom subdomain) |
| `FOUNDRY_PROJECT_NAME` | Project name |
| `CU_ENDPOINT` | Alias of `FOUNDRY_ENDPOINT` for clarity |
| `MODEL_DEPLOYMENTS` | JSON array describing each deployment |
| `CU_API_VERSION` | API version used for live `prebuilt-document` model discovery |
| `CU_MODEL_SELECTION` | `prompt`, `recommended`, `none`, or explicit model selectors |
| `CU_MODEL_SETUP_COMPLETE` | Prevents repeated prompting after successful setup |

## Layout

```text
.
├── azure.yaml           # azd project manifest + postprovision hook wiring
├── infra/
│   ├── main.bicep              # subscription-scope entrypoint
│   ├── main.parameters.json    # azd → Bicep parameter glue
│   └── modules/
│       └── foundry.bicep       # account + project + persisted model deployments + RBAC
└── hooks/
    ├── postprovision.ps1       # Windows live model setup + cu autoconfig
    └── postprovision.sh        # POSIX live model setup + cu autoconfig
```

## Status

Experimental / personal starter. Not yet on awesome-azd.
