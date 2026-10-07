import pytest

from lambda_backend import Operation, Result, Status
from model import (
    MAX_SOURCE_BYTES,
    BusyError,
    NoSourceError,
    PendingEditsError,
    SourceModel,
    SourceRejected,
    decode_upload,
)
from samples import FACTORIAL


def loaded(text=FACTORIAL):
    model = SourceModel()
    model.replace_source("factorial.lam", text)
    return model


def test_model_runs_without_web_or_backend_calls():
    model = SourceModel()
    assert model.revision == 0
    assert model.applied is None


def test_replace_source_creates_revision_and_clears_results():
    model = loaded()
    model.start_operation(Operation.LINT)
    model.finish_operation(Result(Operation.LINT, 1, Status.OK, "ok"))
    assert Operation.LINT in model.results

    model.replace_source("other.lam", 'D0Eint(1)')
    assert model.revision == 2
    assert model.results == {}


def test_load_sets_name_and_applied_text():
    model = loaded()
    assert model.name == "factorial.lam"
    assert model.applied == FACTORIAL


@pytest.mark.parametrize("text", ["", "   \n\t  "])
def test_empty_or_blank_source_is_rejected_and_previous_kept(text):
    model = loaded()
    with pytest.raises(SourceRejected, match="empty"):
        model.replace_source("bad.lam", text)
    assert model.applied == FACTORIAL
    assert model.revision == 1


def test_oversized_source_is_rejected():
    model = loaded()
    with pytest.raises(SourceRejected, match="limit"):
        model.replace_source("big.lam", "x" * (MAX_SOURCE_BYTES + 1))
    assert model.applied == FACTORIAL


def test_oversized_multibyte_text_is_rejected_by_bytes():
    text = "é" * (MAX_SOURCE_BYTES // 2 + 1)
    with pytest.raises(SourceRejected, match="limit"):
        decode_upload(text.encode("utf-8"))


def test_invalid_utf8_upload_is_rejected():
    with pytest.raises(SourceRejected, match="UTF-8"):
        decode_upload(b"\xff\xfe\x00bad")


def test_valid_utf8_upload_decodes():
    assert decode_upload("D0Eint(1)".encode("utf-8")) == "D0Eint(1)"


def test_manual_input_opens_blank_editor_without_upload():
    model = SourceModel()
    model.open_blank()
    assert model.has_pending
    assert model.pending == ""
    assert model.applied is None
    assert model.name == "Manual input"


def test_typing_then_applying_creates_source():
    model = SourceModel()
    model.open_blank()
    model.edit('D0Eint(7)')
    model.apply_changes()
    assert model.applied == "D0Eint(7)"
    assert model.revision == 1
    assert not model.has_pending


def test_applied_edit_creates_new_revision_and_clears_results():
    model = loaded()
    model.start_operation(Operation.INTERPRET)
    model.finish_operation(Result(Operation.INTERPRET, 1, Status.OK, "x"))
    model.edit('D0Eint(3)')
    assert model.applied == FACTORIAL
    model.apply_changes()
    assert model.revision == 2
    assert model.results == {}


def test_discard_restores_applied_source():
    model = loaded()
    model.edit("changed")
    model.discard_changes()
    assert model.applied == FACTORIAL
    assert not model.has_pending


def test_rejected_edit_keeps_applied_source_and_pending_text():
    model = loaded()
    model.edit("   ")
    with pytest.raises(SourceRejected):
        model.apply_changes()
    assert model.applied == FACTORIAL
    assert model.revision == 1
    assert model.pending == "   "


def test_source_replacement_blocked_while_edits_pending():
    model = loaded()
    model.edit("unapplied")
    with pytest.raises(PendingEditsError):
        model.replace_source("new.lam", "D0Eint(1)")
    with pytest.raises(PendingEditsError):
        model.open_blank()


def test_tool_actions_blocked_while_edits_pending():
    model = loaded()
    model.edit("unapplied")
    with pytest.raises(PendingEditsError):
        model.require_runnable(Operation.LINT)


def test_tool_action_requires_applied_source():
    model = SourceModel()
    with pytest.raises(NoSourceError):
        model.require_runnable(Operation.LINT)


def test_edit_without_source_or_blank_editor_is_refused():
    with pytest.raises(NoSourceError):
        SourceModel().edit("D0Eint(1)")


def test_busy_blocks_conflicting_actions_and_edits():
    model = loaded()
    model.start_operation(Operation.INTERPRET)
    with pytest.raises(BusyError):
        model.start_operation(Operation.LINT)
    with pytest.raises(BusyError):
        model.replace_source("new.lam", "D0Eint(1)")
    with pytest.raises(BusyError):
        model.edit("x")


def test_finish_releases_busy_state():
    model = loaded()
    model.start_operation(Operation.LINT)
    model.finish_operation(Result(Operation.LINT, 1, Status.OK, "ok"))
    assert model.busy is None
    model.start_operation(Operation.INTERPRET)


def test_abort_releases_busy_state_for_retry():
    model = loaded()
    model.start_operation(Operation.INTERPRET)
    model.abort_operation()
    assert model.busy is None
    model.start_operation(Operation.INTERPRET)


def test_source_cannot_change_while_operation_runs():
    model = loaded()
    model.start_operation(Operation.LINT)
    with pytest.raises(BusyError):
        model.apply_changes()
    with pytest.raises(BusyError):
        model.discard_changes()
    model.finish_operation(Result(Operation.LINT, 1, Status.OK, "ok"))
    assert model.applied == FACTORIAL


def test_artifact_is_cleared_by_new_revision():
    model = loaded()
    model.artifact = object()
    model.replace_source("other.lam", "D0Eint(2)")
    assert model.artifact is None
