# Azure Content Understanding Toolkit

The **Azure Content Understanding Toolkit** is a set of tools that ease integration with [Azure Content Understanding][cu_overview], together with experimental tools that capture best practices for building on Content Understanding.

## Tools in this repository

| Tool | Location | Description |
| --- | --- | --- |
| **CU CLI** | [`cu-cli/`](cu-cli/README.md) | Analyze files, create and test custom analyzers, manage resource profiles and model defaults, and generate Azure infrastructure. Install with `pip install cu-cli`. |

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

This project welcomes contributions and suggestions. Per-tool contribution guides live in each tool directory (for example [`cu-cli/CONTRIBUTING.md`](cu-cli/CONTRIBUTING.md)).

Most contributions require you to agree to a Microsoft Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us the rights to use your contribution. For details, visit https://cla.opensource.microsoft.com.

## Security

See [SECURITY.md](SECURITY.md) for how to report security issues.

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft trademarks or logos is subject to and must follow [Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/legal/intellectualproperty/trademarks/usage/general). Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship. Any use of third-party trademarks or logos are subject to those third-parties' policies.

## License

Licensed under the [MIT License](LICENSE).

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
