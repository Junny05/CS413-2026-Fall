import threading
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass

from lambda_backend import Operation, Result, Status
from model import MANUAL_NAME, ModelError, SourceModel, decode_upload
from samples import FACTORIAL, FIBONACCI

CANNED = {
    "factorial": ("Factorial (canned)", FACTORIAL),
    "fibonacci": ("Fibonacci (canned)", FIBONACCI),
}

BUTTON_ORDER = (Operation.LINT, Operation.INTERPRET, Operation.TYPECHECK, Operation.COMPILE, Operation.EXECUTE)
EXECUTE_DISABLED_REASON = (
    "Execute runs code produced by Compile. Compilation is not yet implemented, "
    "so no generated code exists to run."
)


@dataclass(frozen=True)
class ButtonState:
    operation: Operation
    enabled: bool
    reason: str = ""


@dataclass(frozen=True)
class ViewState:
    source_name: str | None
    revision: int
    applied_text: str | None
    pending_text: str | None
    has_pending: bool
    busy: Operation | None
    buttons: tuple[ButtonState, ...]
    results: tuple[Result, ...]
    message: str = ""


class Controller:
    def __init__(self, model: SourceModel, backend, executor: ThreadPoolExecutor | None = None):
        self.model = model
        self.backend = backend
        self._lock = threading.RLock()
        self._executor = executor or ThreadPoolExecutor(max_workers=1)
        self._message = ""
        self._dispatch = {
            Operation.LINT: backend.lint,
            Operation.INTERPRET: backend.interpret,
            Operation.TYPECHECK: backend.typecheck,
            Operation.COMPILE: backend.compile,
        }

    def load_upload(self, filename: str, data: bytes) -> None:
        text = decode_upload(data)
        with self._lock:
            self.model.replace_source(filename, text)
            self._message = f"Loaded {filename}."

    def load_canned(self, key: str) -> None:
        name, text = CANNED[key]
        with self._lock:
            self.model.replace_source(name, text)
            self._message = f"Loaded {name}."

    def open_manual(self) -> None:
        with self._lock:
            self.model.open_blank()
            self._message = f"{MANUAL_NAME} opened with a blank editor."

    def edit(self, text: str) -> None:
        with self._lock:
            self.model.edit(text)

    def apply_changes(self) -> None:
        with self._lock:
            self.model.apply_changes()
            self._message = "Changes applied."

    def discard_changes(self) -> None:
        with self._lock:
            self.model.discard_changes()
            self._message = "Changes discarded."

    def run(self, operation: Operation) -> Future:
        with self._lock:
            if operation is Operation.EXECUTE:
                return self._run_execute()
            source = self.model.require_runnable(operation)
            revision = self.model.start_operation(operation)
            self._message = f"{operation.value.capitalize()} is running."
        return self._executor.submit(self._work, operation, source, revision)

    def _run_execute(self) -> Future:
        artifact = self.model.artifact
        if artifact is None:
            raise ModelError(EXECUTE_DISABLED_REASON)
        self.model.require_runnable(Operation.EXECUTE)
        revision = self.model.start_operation(Operation.EXECUTE)
        return self._executor.submit(self._work_execute, artifact, revision)

    def _work(self, operation: Operation, source: str, revision: int) -> Result:
        try:
            result = self._dispatch[operation](source, revision)
        except Exception as e:
            result = Result(operation, revision, Status.BACKEND_ERROR,
                            f"Backend failure: {type(e).__name__}: {e}")
        return self._finish(result)

    def _work_execute(self, artifact, revision: int) -> Result:
        try:
            result = self.backend.execute(artifact, revision)
        except Exception as e:
            result = Result(Operation.EXECUTE, revision, Status.BACKEND_ERROR,
                            f"Backend failure: {type(e).__name__}: {e}")
        return self._finish(result)

    def _finish(self, result: Result) -> Result:
        with self._lock:
            self.model.finish_operation(result)
            self._message = f"{result.operation.value.capitalize()}: {result.status.value}."
        return result

    def snapshot(self) -> ViewState:
        with self._lock:
            m = self.model
            buttons = tuple(self._button_state(op) for op in BUTTON_ORDER)
            return ViewState(
                source_name=m.name,
                revision=m.revision,
                applied_text=m.applied,
                pending_text=m.pending,
                has_pending=m.has_pending,
                busy=m.busy,
                buttons=buttons,
                results=tuple(m.results[op] for op in BUTTON_ORDER if op in m.results),
                message=self._message,
            )

    def _button_state(self, operation: Operation) -> ButtonState:
        m = self.model
        if operation is Operation.EXECUTE:
            return ButtonState(operation, False, EXECUTE_DISABLED_REASON)
        try:
            m.require_runnable(operation)
        except ModelError as e:
            return ButtonState(operation, False, str(e))
        return ButtonState(operation, True)
