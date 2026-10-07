from dataclasses import dataclass, field

from lambda_backend import Operation, Result

MAX_SOURCE_BYTES = 64 * 1024
MANUAL_NAME = "Manual input"


class ModelError(Exception):
    pass


class SourceRejected(ModelError):
    pass


class PendingEditsError(ModelError):
    pass


class NoSourceError(ModelError):
    pass


class BusyError(ModelError):
    pass


def validate_text(text: str) -> str:
    if not text.strip():
        raise SourceRejected("Source is empty or contains only whitespace.")
    if len(text.encode("utf-8")) > MAX_SOURCE_BYTES:
        raise SourceRejected(f"Source exceeds the {MAX_SOURCE_BYTES // 1024} KiB limit.")
    return text


def decode_upload(data: bytes) -> str:
    if len(data) > MAX_SOURCE_BYTES:
        raise SourceRejected(f"File exceeds the {MAX_SOURCE_BYTES // 1024} KiB limit.")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise SourceRejected("File is not valid UTF-8 text.") from None
    return validate_text(text)


@dataclass
class SourceModel:
    name: str | None = None
    revision: int = 0
    applied: str | None = None
    pending: str | None = None
    results: dict[Operation, Result] = field(default_factory=dict)
    artifact: object | None = None
    busy: Operation | None = None

    @property
    def has_pending(self) -> bool:
        return self.pending is not None

    def replace_source(self, name: str, text: str) -> None:
        self._require_idle()
        self._require_no_pending()
        validated = validate_text(text)
        self._set_applied(name, validated)

    def open_blank(self) -> None:
        self._require_idle()
        self._require_no_pending()
        self.name = MANUAL_NAME
        self.applied = None
        self.pending = ""
        self._clear_results()

    def edit(self, text: str) -> None:
        self._require_idle()
        if self.applied is None and self.pending is None:
            raise NoSourceError("Open or load a source before editing.")
        self.pending = text

    def apply_changes(self) -> None:
        self._require_idle()
        if self.pending is None:
            return
        validated = validate_text(self.pending)
        self._set_applied(self.name or MANUAL_NAME, validated)

    def discard_changes(self) -> None:
        self._require_idle()
        self.pending = None
        if self.applied is None:
            self.name = None

    def require_runnable(self, operation: Operation) -> str:
        if self.busy is not None:
            raise BusyError(f"{self.busy.value} is still running.")
        if self.has_pending:
            raise PendingEditsError("Apply or discard unapplied edits first.")
        if self.applied is None:
            raise NoSourceError("Load or enter a source before running this action.")
        return self.applied

    def start_operation(self, operation: Operation) -> int:
        self.require_runnable(operation)
        self.busy = operation
        return self.revision

    def finish_operation(self, result: Result) -> None:
        if self.busy is None:
            raise ModelError("No operation is running.")
        self.busy = None
        self.results[result.operation] = result

    def abort_operation(self) -> None:
        self.busy = None

    def _set_applied(self, name: str, text: str) -> None:
        self.name = name
        self.applied = text
        self.pending = None
        self.revision += 1
        self._clear_results()

    def _clear_results(self) -> None:
        self.results = {}
        self.artifact = None

    def _require_idle(self) -> None:
        if self.busy is not None:
            raise BusyError(f"{self.busy.value} is still running.")

    def _require_no_pending(self) -> None:
        if self.has_pending:
            raise PendingEditsError("Apply or discard unapplied edits first.")
