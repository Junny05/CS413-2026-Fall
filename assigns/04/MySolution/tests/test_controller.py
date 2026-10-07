import threading

import pytest

import lambda_backend as real_backend
from controller import Controller
from lambda_backend import Operation, Result, Status
from model import ModelError, SourceModel, SourceRejected
from samples import FACTORIAL


class FakeBackend:
    def __init__(self):
        self.calls = []
        self.gate = None
        self.fail_with = None

    def _record(self, name, source, revision):
        self.calls.append((name, source, revision))
        if self.gate is not None:
            self.gate.wait(5)
        if self.fail_with is not None:
            raise self.fail_with
        return Result(Operation(name), revision, Status.OK, f"fake {name}")

    def lint(self, source, revision):
        return self._record("lint", source, revision)

    def interpret(self, source, revision):
        return self._record("interpret", source, revision)

    def typecheck(self, source, revision):
        return self._record("typecheck", source, revision)

    def compile(self, source, revision):
        return self._record("compile", source, revision)

    def execute(self, artifact, revision):
        self.calls.append(("execute", artifact, revision))
        return Result(Operation.EXECUTE, revision, Status.NOT_IMPLEMENTED, "no")


def make(backend=None):
    backend = backend or FakeBackend()
    return Controller(SourceModel(), backend), backend


def button(state, operation):
    return next(b for b in state.buttons if b.operation is operation)


def test_controller_runs_without_browser_using_substitute_backend():
    controller, backend = make()
    controller.load_canned("factorial")
    controller.run(Operation.LINT).result()
    assert backend.calls == [("lint", FACTORIAL, 1)]


def test_dispatch_passes_applied_source_and_revision():
    controller, backend = make()
    controller.load_canned("factorial")
    controller.load_canned("fibonacci")
    controller.run(Operation.INTERPRET).result()
    name, source, revision = backend.calls[-1]
    assert name == "interpret" and revision == 2 and "fib" in source


def test_result_is_recorded_for_current_revision():
    controller, _ = make()
    controller.load_canned("factorial")
    controller.run(Operation.LINT).result()
    snap = controller.snapshot()
    assert snap.results[0].operation is Operation.LINT
    assert snap.results[0].revision == 1


def test_editing_clears_results_and_creates_revision():
    controller, _ = make()
    controller.load_canned("factorial")
    controller.run(Operation.LINT).result()
    controller.edit("D0Eint(9)")
    controller.apply_changes()
    snap = controller.snapshot()
    assert snap.revision == 2
    assert snap.results == ()


def test_placeholder_operations_dispatch_to_backend_not_success():
    controller, backend = make()
    controller.load_canned("factorial")
    controller.run(Operation.TYPECHECK).result()
    controller.run(Operation.COMPILE).result()
    assert [c[0] for c in backend.calls] == ["typecheck", "compile"]


def test_execute_is_disabled_without_artifact():
    controller, _ = make()
    controller.load_canned("factorial")
    state = controller.snapshot()
    execute = button(state, Operation.EXECUTE)
    assert not execute.enabled
    assert "Compile" in execute.reason
    with pytest.raises(ModelError, match="Compile"):
        controller.run(Operation.EXECUTE)


def test_execute_never_falls_back_to_interpretation():
    controller, backend = make()
    controller.load_canned("factorial")
    with pytest.raises(ModelError):
        controller.run(Operation.EXECUTE)
    assert backend.calls == []


def test_buttons_disabled_without_source_and_with_pending_edits():
    controller, _ = make()
    state = controller.snapshot()
    assert not button(state, Operation.LINT).enabled
    controller.load_canned("factorial")
    controller.edit("unapplied")
    state = controller.snapshot()
    assert not button(state, Operation.INTERPRET).enabled
    assert "Apply" in button(state, Operation.INTERPRET).reason


def test_source_replacement_blocked_while_edits_pending():
    controller, _ = make()
    controller.load_canned("factorial")
    controller.edit("unapplied")
    with pytest.raises(ModelError):
        controller.load_canned("fibonacci")


def test_rejected_upload_keeps_previous_source():
    controller, _ = make()
    controller.load_canned("factorial")
    with pytest.raises(SourceRejected):
        controller.load_upload("bad.lam", b"\xff\xfe")
    assert controller.snapshot().applied_text == FACTORIAL


def test_rejected_edit_keeps_text_for_correction():
    controller, _ = make()
    controller.load_canned("factorial")
    controller.edit("   ")
    with pytest.raises(SourceRejected):
        controller.apply_changes()
    snap = controller.snapshot()
    assert snap.applied_text == FACTORIAL
    assert snap.pending_text == "   "


def test_manual_input_then_apply_runs_real_lint():
    controller = Controller(SourceModel(), real_backend)
    controller.open_manual()
    controller.edit('D0Evar("x")')
    controller.apply_changes()
    result = controller.run(Operation.LINT).result()
    assert result.status is Status.LANGUAGE_ERROR
    assert result.free_vars == ("x",)


def test_real_interpret_of_canned_factorial():
    controller = Controller(SourceModel(), real_backend)
    controller.load_canned("factorial")
    result = controller.run(Operation.INTERPRET).result()
    assert result.message == "D0Vint(arg1=120)"


def test_busy_state_blocks_conflicting_actions_and_restores_after_completion():
    backend = FakeBackend()
    backend.gate = threading.Event()
    controller, _ = make(backend)
    controller.load_canned("factorial")
    future = controller.run(Operation.INTERPRET)

    state = controller.snapshot()
    assert state.busy is Operation.INTERPRET
    assert not button(state, Operation.LINT).enabled
    with pytest.raises(ModelError, match="running"):
        controller.run(Operation.LINT)
    with pytest.raises(ModelError, match="running"):
        controller.edit("x")

    backend.gate.set()
    future.result()
    state = controller.snapshot()
    assert state.busy is None
    assert button(state, Operation.LINT).enabled


def test_backend_failure_is_reported_and_source_preserved_for_retry():
    backend = FakeBackend()
    backend.fail_with = RuntimeError("boom")
    controller, _ = make(backend)
    controller.load_canned("factorial")
    result = controller.run(Operation.LINT).result()
    assert result.status is Status.BACKEND_ERROR
    assert "boom" in result.message

    state = controller.snapshot()
    assert state.busy is None
    assert state.applied_text == FACTORIAL
    backend.fail_with = None
    retry = controller.run(Operation.LINT).result()
    assert retry.status is Status.OK


def test_timeout_result_from_backend_allows_retry():
    class TimingOut(FakeBackend):
        def interpret(self, source, revision):
            return Result(Operation.INTERPRET, revision, Status.TIMEOUT, "stopped")

    controller, _ = make(TimingOut())
    controller.load_canned("factorial")
    assert controller.run(Operation.INTERPRET).result().status is Status.TIMEOUT
    assert controller.snapshot().busy is None
    assert controller.run(Operation.INTERPRET).result().status is Status.TIMEOUT
