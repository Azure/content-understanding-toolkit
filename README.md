# Azure Content Understanding Toolkit

The **Azure Content Understanding Toolkit** is a set of tools that ease integration with [Azure Content Understanding][cu_overview], together with experimental tools that capture best practices for building on Content Understanding.

## Tools in this repository

| Tool | Location | Description |
| --- | --- | --- |
| **CU CLI** | [`cu-cli/`](cu-cli/README.md) | Analyze files, create and test custom analyzers, manage resource profiles and model defaults, and generate Azure infrastructure. Install with `pip install cu-cli`. |
| **Prebuilt schema definitions** | [`prebuilt-schema/`](prebuilt-schema/README.md) | Browse domain-specific prebuilt analyzer schemas by API version, or use the [single-file analyzer index](prebuilt-schema/SUPPORTED_ANALYZERS.md). |

More tools will be added over time.

## What is Content Understanding?

New to CU? Start here. **Azure Content Understanding** is a multimodal AI service in Microsoft Foundry that turns unstructured files — documents, images, audio, and video — into structured, machine-readable output. See [What is Content Understanding?][cu_overview].

**Key concepts:**
- **Analyzer** — the unit that processes a file. Use a **prebuilt analyzer** (e.g. `prebuilt-layout` for markdown/OCR, `prebuilt-invoice` for invoice fields) or author a **custom analyzer** with your own field schema. See [Prebuilt analyzers][cu_prebuilt_analyzers] and [Create a custom analyzer][cu_custom_analyzer].
- **Field schema** — the JSON that defines what a custom analyzer extracts (field name, type, and a description that guides the model).
- **Classifier** — an analyzer that categorizes (and optionally routes/splits) content by category. See [Classifier overview][cu_classifier].
- **Modalities** — document, image, audio, and video. See the [Document][cu_document], [Image][cu_image], [Audio][cu_audio], and [Video][cu_video] overviews.
- **Model deployments & defaults** — custom and LLM-backed analyzers use chat + embedding model deployments on your Foundry resource. See [Models and deployments][cu_models].
- **Foundry resource & endpoint** — CU runs on a Microsoft Foundry resource; its endpoint has the form `https://<resource>.services.ai.azure.com/`.

**Why teams use CU:**
- Advanced layout for complex, multi-column, nested-table documents, plus industry-leading OCR.
- Grounded field extraction with source spans and confidence — not just raw text.
- One consistent API across documents, images, audio, and video.
- LLM-friendly markdown output that drops straight into RAG and agent pipelines.

**Real-world uses:**
- **Retrieval-augmented generation (RAG)** — preprocess documents into clean markdown/fields for indexing. See [Build a RAG solution][cu_rag].
- **Document process automation (RPA)** — extract structured fields to drive downstream automation. See [Build an RPA solution][cu_rpa].
- **No-code exploration** — try analyzers first in [Content Understanding Studio][cu_studio].

Full docs: [aka.ms/cu-doc](https://aka.ms/cu-doc).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for repository-wide contribution and
Contributor License Agreement (CLA) guidance. Each tool may also provide
development instructions in its own directory.

## Security

See [SECURITY.md](SECURITY.md) for how to report security issues.

## Support

See [SUPPORT.md](SUPPORT.md) for toolkit support channels and the distinction
between GitHub issues and Azure service support.

## Code of conduct

This project follows the
[Microsoft Open Source Code of Conduct](CODE_OF_CONDUCT.md).

## Data collection

The CU CLI adds `cu-cli/<version>` to the standard Azure SDK `User-Agent`
header on requests to the Azure Content Understanding service. Microsoft uses
this identifier to understand CU CLI adoption. CU CLI does not add customer
content or separate usage and analytics events to this telemetry.

To remove the `cu-cli/<version>` identifier, set `CU_TELEMETRY=off` (also
accepts `0`, `false`, or `no`) before running CU CLI. The Azure SDK continues to
send its standard `User-Agent` as part of service requests.

**Data Collection.** The software may collect information about you and your
use of the software and send it to Microsoft. Microsoft may use this
information to provide services and improve our products and services. You may
turn off the telemetry as described in the repository. There are also some
features in the software that may enable you and Microsoft to collect data from
users of your applications. If you use these features, you must comply with
applicable law, including providing appropriate notices to users of your
applications together with a copy of [Microsoft's privacy
statement](https://go.microsoft.com/fwlink/?LinkID=824704). You can learn more
about data collection and use in the help documentation and our privacy
statement. Your use of the software operates as your consent to these
practices.

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft trademarks or logos is subject to and must follow [Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/legal/intellectualproperty/trademarks/usage/general). Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship. Any use of third-party trademarks or logos are subject to those third-parties' policies.

## License

Licensed under the [MIT License](LICENSE.txt).

[cu_overview]: https://learn.microsoft.com/azure/ai-services/content-understanding/overview
[cu_prebuilt_analyzers]: https://learn.microsoft.com/azure/ai-services/content-understanding/concepts/prebuilt-analyzers
[cu_custom_analyzer]: https://learn.microsoft.com/azure/ai-services/content-understanding/tutorial/create-custom-analyzer
[cu_classifier]: https://learn.microsoft.com/azure/ai-services/content-understanding/concepts/classifier
[cu_document]: https://learn.microsoft.com/azure/ai-services/content-understanding/document/overview
[cu_image]: https://learn.microsoft.com/azure/ai-services/content-understanding/image/overview
[cu_audio]: https://learn.microsoft.com/azure/ai-services/content-understanding/audio/overview
[cu_video]: https://learn.microsoft.com/azure/ai-services/content-understanding/video/overview
[cu_models]: https://learn.microsoft.com/azure/ai-services/content-understanding/concepts/models-deployments
[cu_rag]: https://learn.microsoft.com/azure/ai-services/content-understanding/tutorial/build-rag-solution
[cu_rpa]: https://learn.microsoft.com/azure/ai-services/content-understanding/tutorial/robotic-process-automation
[cu_studio]: https://learn.microsoft.com/azure/ai-services/content-understanding/quickstart/content-understanding-studio
