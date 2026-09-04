# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

"""Typed request and planning contracts shared by CU command frontends."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Mapping


class ResultView(str, Enum):
    LLM_INPUT = "llm-input"
    FULL = "full"


class SelectionMode(str, Enum):
    POSITIONAL = "positional"
    NAMED_FILES = "named-files"
    NAMED_SOURCES = "named-sources"


class InputOrigin(str, Enum):
    POSITIONAL_FILE = "positional-file"
    POSITIONAL_SOURCE = "positional-source"
    NAMED_FILE = "named-file"
    NAMED_SOURCE = "named-source"


class ExistingResultPolicy(str, Enum):
    ERROR = "error"
    SKIP = "skip"
    REANALYZE = "reanalyze"


class AuthMode(str, Enum):
    LOGIN = "login"
    KEY = "key"


class OutcomeStatus(str, Enum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class ProfileShowRequest:
    name: str | None = None


@dataclass(frozen=True)
class ProfileListRequest:
    pass


@dataclass(frozen=True)
class ProfileGetRequest:
    key: str
    name: str | None = None


@dataclass(frozen=True)
class ProfileSetRequest:
    key: str
    value: str
    name: str | None = None


@dataclass(frozen=True)
class ProfileUnsetRequest:
    key: str
    name: str | None = None


@dataclass(frozen=True)
class ProfileCreateRequest:
    name: str


@dataclass(frozen=True)
class ProfileDeleteRequest:
    name: str


@dataclass(frozen=True)
class ProfileCopyRequest:
    destination: str
    source: str | None = None


@dataclass(frozen=True)
class ProfileRenameRequest:
    source: str
    destination: str


@dataclass(frozen=True)
class ProfileSetActiveRequest:
    name: str


@dataclass(frozen=True)
class ProfileSyncModelsRequest:
    name: str | None = None


@dataclass(frozen=True)
class AnalyzerShowRequest:
    """Canonical request for retrieving one analyzer."""

    name: str

    def __post_init__(self) -> None:
        normalized = self.name.strip()
        if not normalized:
            raise ValueError("analyzer name cannot be empty.")
        object.__setattr__(self, "name", normalized)


@dataclass(frozen=True)
class AnalyzerListRequest:
    kind: str = "all"
    sort_by: str = "analyzerId"

    def __post_init__(self) -> None:
        if self.kind not in {"all", "prebuilt", "custom"}:
            raise ValueError(f"invalid analyzer kind: {self.kind}")
        if self.sort_by not in {"analyzerId", "createdAt", "lastModifiedAt"}:
            raise ValueError(f"invalid analyzer sort field: {self.sort_by}")


@dataclass(frozen=True)
class AnalyzerCreateRequest:
    name: str
    schema: Path

    def __post_init__(self) -> None:
        normalized = self.name.strip()
        if not normalized:
            raise ValueError("analyzer name cannot be empty.")
        object.__setattr__(self, "name", normalized)
        object.__setattr__(self, "schema", Path(self.schema))


@dataclass(frozen=True)
class AnalyzerDeleteRequest:
    name: str
    yes: bool = False

    def __post_init__(self) -> None:
        normalized = self.name.strip()
        if not normalized:
            raise ValueError("analyzer name cannot be empty.")
        object.__setattr__(self, "name", normalized)


@dataclass(frozen=True)
class AnalyzeRequest:
    positional_inputs: tuple[Path, ...] = ()
    files: tuple[Path, ...] = ()
    sources: tuple[Path, ...] = ()
    pattern: str | None = None
    recursive: bool = False
    analyzer: str | None = None
    inline: bool = False
    usage: bool = False
    llm_input: bool = False
    output_file: Path | None = None
    output_dir: Path | None = None
    on_existing: ExistingResultPolicy | None = None
    dry_run: bool = False
    yes: bool = False
    report_file: Path | None = None
    concurrency: int = 4

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "positional_inputs",
            tuple(Path(path) for path in self.positional_inputs),
        )
        object.__setattr__(self, "files", tuple(Path(path) for path in self.files))
        object.__setattr__(self, "sources", tuple(Path(path) for path in self.sources))
        if self.output_file is not None:
            object.__setattr__(self, "output_file", Path(self.output_file))
        if self.output_dir is not None:
            object.__setattr__(self, "output_dir", Path(self.output_dir))
        if self.report_file is not None:
            object.__setattr__(self, "report_file", Path(self.report_file))
        if isinstance(self.on_existing, str):
            object.__setattr__(
                self,
                "on_existing",
                ExistingResultPolicy(self.on_existing),
            )
        if not 1 <= self.concurrency <= 32:
            raise ValueError("concurrency must be between 1 and 32.")


@dataclass(frozen=True)
class AnalyzerTestRequest:
    name: str
    positional_inputs: tuple[Path, ...] = ()
    files: tuple[Path, ...] = ()
    sources: tuple[Path, ...] = ()
    pattern: str | None = None
    recursive: bool = False
    dry_run: bool = False
    output_file: Path | None = None
    force: bool = False
    yes: bool = False
    concurrency: int = 4

    def __post_init__(self) -> None:
        normalized = self.name.strip()
        if not normalized:
            raise ValueError("analyzer name cannot be empty.")
        object.__setattr__(self, "name", normalized)
        object.__setattr__(
            self,
            "positional_inputs",
            tuple(Path(path) for path in self.positional_inputs),
        )
        object.__setattr__(self, "files", tuple(Path(path) for path in self.files))
        object.__setattr__(self, "sources", tuple(Path(path) for path in self.sources))
        if self.output_file is not None:
            object.__setattr__(self, "output_file", Path(self.output_file))
        if not 1 <= self.concurrency <= 16:
            raise ValueError("concurrency must be between 1 and 16.")


@dataclass(frozen=True)
class AnalyzerCopyRequest:
    source: str
    destination: str
    source_resource: str | None = None
    source_subscription: str | None = None
    source_resource_group: str | None = None
    source_profile: str | None = None
    destination_resource: str | None = None
    destination_subscription: str | None = None
    destination_resource_group: str | None = None
    destination_profile: str | None = None

    def __post_init__(self) -> None:
        source = self.source.strip()
        destination = self.destination.strip()
        if not source or not destination:
            raise ValueError("source and destination analyzer names are required.")
        object.__setattr__(self, "source", source)
        object.__setattr__(self, "destination", destination)
        if self.source_resource and self.source_profile:
            raise ValueError(
                "--source-resource and --source-profile are mutually exclusive."
            )
        if self.destination_resource and self.destination_profile:
            raise ValueError(
                "--destination-resource and --destination-profile are mutually exclusive."
            )


@dataclass(frozen=True)
class AnalyzerValidateRequest:
    schema: Path
    strict: bool = False
    spec: bool = False
    api_version: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema", Path(self.schema))


@dataclass(frozen=True)
class AnalyzerSchemaCreateRequest:
    from_template: bool = False
    from_sample: Path | None = None
    name: str = "my_analyzer_v1"
    base: str | None = None
    modality: str = "document"
    output_file: Path | None = None
    template_type: str = "extraction"
    force: bool = False

    def __post_init__(self) -> None:
        name = self.name.strip()
        if not name:
            raise ValueError("analyzer name cannot be empty.")
        object.__setattr__(self, "name", name)
        if self.from_sample is not None:
            object.__setattr__(self, "from_sample", Path(self.from_sample))
        if self.output_file is not None:
            object.__setattr__(self, "output_file", Path(self.output_file))
        if self.from_template and self.from_sample is not None:
            raise ValueError("--from-template and --from-sample cannot be combined.")
        if self.modality not in {"document", "image", "audio", "video"}:
            raise ValueError(f"invalid modality: {self.modality}")
        if self.template_type not in {"extraction", "classification"}:
            raise ValueError(f"invalid schema type: {self.template_type}")
        if self.from_sample is not None and (
            self.template_type != "extraction"
            or self.modality != "document"
            or self.base is not None
        ):
            raise ValueError(
                "--from-sample cannot be combined with --type classification, "
                "--modality, or --base."
            )


@dataclass(frozen=True)
class DefaultsShowRequest:
    pass


@dataclass(frozen=True)
class DefaultsSetRequest:
    models: tuple[str, ...] = ()
    from_profile: bool = False
    replace: bool = False


@dataclass(frozen=True)
class EnvironmentVariableListRequest:
    pass


@dataclass(frozen=True)
class PlannedInput:
    path: Path
    source_root: Path
    relative_path: Path
    origin: InputOrigin
    size_bytes: int


@dataclass(frozen=True)
class SkippedInput:
    path: Path
    reason: str


@dataclass(frozen=True)
class InputPlan:
    inputs: tuple[PlannedInput, ...]
    mode: SelectionMode
    recursive: bool
    pattern: str | None
    total_bytes: int
    extension_counts: Mapping[str, int] = field(default_factory=dict)
    skipped: tuple[SkippedInput, ...] = ()


@dataclass(frozen=True)
class PlannedOutput:
    source: PlannedInput
    path: Path | None
    exists: bool = False
    skipped: bool = False


@dataclass(frozen=True)
class ExecutionPlan:
    input_plan: InputPlan
    outputs: tuple[PlannedOutput, ...]
    on_existing: ExistingResultPolicy
    dry_run: bool


@dataclass(frozen=True)
class ErrorDetail:
    code: str | None = None
    message: str | None = None
    target: str | None = None


@dataclass(frozen=True)
class FileOutcome:
    source: Path
    status: OutcomeStatus
    analyzer: str
    output_path: Path | None = None
    usage: Mapping[str, Any] | None = None
    error: ErrorDetail | None = None
    payload: Any = None


@dataclass(frozen=True)
class BatchReport:
    outcomes: tuple[FileOutcome, ...]

    @property
    def succeeded(self) -> int:
        return sum(item.status is OutcomeStatus.SUCCEEDED for item in self.outcomes)

    @property
    def failed(self) -> int:
        return sum(item.status is OutcomeStatus.FAILED for item in self.outcomes)

    @property
    def skipped(self) -> int:
        return sum(item.status is OutcomeStatus.SKIPPED for item in self.outcomes)
