# Testing

## Automated tests

Run from `MySolution/` after installing dependencies (see README.md):

```
./.venv/bin/python -m pytest -q
```

Result at the time of writing: 109 passed.

| File | Scope |
| --- | --- |
| `tests/test_lambda_backend.py` | Free-variable analysis, reader, real Lint and Interpret, timeout, placeholders |
| `tests/test_model.py` | Source model rules (no web or backend imports) |
| `tests/test_controller.py` | Controller dispatch, busy state, failure injection, real Lint/Interpret through the controller |
| `tests/test_app.py` | HTTP layer against a real loopback server: routes, uploads, escaping, refusals |

## Traceability

Test names are listed as `file::name`. Abbreviations: `backend` = `tests/test_lambda_backend.py`, `model` = `tests/test_model.py`, `controller` = `tests/test_controller.py`, `app` = `tests/test_app.py`.

| ID | Requirement | Automated checks | Browser check |
| --- | --- | --- | --- |
| F1 | Source menu (Choose File, Manual input, Factorial, Fibonacci); source name and revision shown | app::test_index_page_shows_menu_and_disabled_execute; app::test_load_factorial_then_lint_and_interpret; app::test_valid_upload_creates_revision_with_filename; model::test_load_sets_name_and_applied_text; model::test_manual_input_opens_blank_editor_without_upload | B1, B2, B3 |
| F2 | Type or edit source; Apply and Discard; applied edits don't touch the original file; replacement and tools blocked while edits pending | model::test_typing_then_applying_creates_source; model::test_discard_restores_applied_source; model::test_source_replacement_blocked_while_edits_pending; model::test_tool_actions_blocked_while_edits_pending; app::test_draft_blocks_source_replacement_and_tool_actions; app::test_discard_restores_applied_source | B4, B5 |
| F3 | Reject empty, whitespace, invalid UTF-8, oversized input; keep previous source and rejected edits | model::test_empty_or_blank_source_is_rejected_and_previous_kept; model::test_oversized_source_is_rejected; model::test_oversized_multibyte_text_is_rejected_by_bytes; model::test_invalid_utf8_upload_is_rejected; controller::test_rejected_upload_keeps_previous_source; controller::test_rejected_edit_keeps_text_for_correction; app::test_invalid_utf8_upload_is_rejected_and_previous_source_kept; app::test_empty_upload_is_rejected; app::test_rejected_edit_keeps_text_for_correction; app::test_quote_heavy_edit_at_limit_is_accepted; app::test_quote_heavy_edit_over_limit_gets_size_notice; app::test_request_beyond_form_cap_gets_size_notice | B6 |
| F4 | Buttons in order Lint, Interpret, Type-check, Compile, Execute; require applied source; Execute disabled | controller::test_buttons_disabled_without_source_and_with_pending_edits; app::test_index_page_shows_menu_and_disabled_execute. Button order is not asserted by a test. | B7 (order checked by eye) |
| F5 | Real free-variable Lint with undeclared-name error or "no free variables" | backend::test_lint_closed_program_passes; backend::test_lint_open_program_lists_names_in_sorted_order; backend::test_lint_does_not_evaluate_closed_program_that_would_fail; app::test_open_expression_lint_then_fixed_expression_passes | B2, B8 |
| F6 | Real Interpret; distinguish input errors from runtime failures | backend::test_interpret_arithmetic; backend::test_interpret_factorial; backend::test_interpret_factorial_base_case; backend::test_interpret_fibonacci; backend::test_interpret_fibonacci_base_cases; backend::test_interpret_division_by_zero_is_runtime_error_not_input_error; backend::test_interpret_type_mismatch_is_runtime_error; backend::test_interpret_unbound_variable_is_runtime_error; backend::test_interpret_malformed_input_is_input_error; controller::test_real_interpret_of_canned_factorial | B2, B9 |
| F7 | Type-check and Compile report not implemented; Execute explanation | backend::test_typecheck_is_not_reported_as_success; backend::test_compile_is_not_reported_as_success; backend::test_execute_without_artifact_is_not_implemented; controller::test_execute_is_disabled_without_artifact; controller::test_execute_never_falls_back_to_interpretation; app::test_execute_action_is_refused | B7 |
| F8 | Each accepted source change creates a revision and clears results and artifacts; rejected changes keep state | model::test_replace_source_creates_revision_and_clears_results; model::test_applied_edit_creates_new_revision_and_clears_results; model::test_artifact_is_cleared_by_new_revision; controller::test_editing_clears_results_and_creates_revision | B4 |
| F9 | Result shows action, revision, outcome; line breaks preserved; HTML-like text shown literally | app::test_html_like_source_and_output_are_escaped. Line-break preservation is not automated. | B10 |
| F10 | Busy status; conflicting actions blocked; controls restored; source kept on backend error; retry; bounded execution | controller::test_busy_state_blocks_conflicting_actions_and_restores_after_completion; controller::test_backend_failure_is_reported_and_source_preserved_for_retry; controller::test_timeout_result_from_backend_allows_retry; model::test_busy_blocks_conflicting_actions_and_edits; model::test_abort_releases_busy_state_for_retry; backend::test_interpret_timeout_stops_nonterminating_work; backend::test_interpret_succeeds_after_timeout; app::test_status_endpoint_reports_busy_until_done; app::test_busy_flag_is_exposed_to_page_script | B11, B12 |

Architectural boundaries: model tests import no web or backend code; controller tests substitute a fake backend (`FakeBackend`) with no view code involved.

## Browser checklist (manual)

No browser automation was run for this document. Start the server (`./.venv/bin/python app.py` from `MySolution/`), open http://127.0.0.1:8000/, perform each step, and record what you observe. Mark each row Pass or Fail and note anything unexpected.

| ID | Steps | Expected outcome | Observed | Pass/Fail |
| --- | --- | --- | --- | --- |
| B1 | Load page. | Source menu shows Choose a UTF-8 text file, Manual input, Factorial (canned), Fibonacci (canned). Source "none", revision 0. Execute is disabled and its reason is shown. | Performed manually by the student, who reports it passed; per-step notes not recorded. | Pass (student report) |
| B2 | Click Factorial (canned). Click Interpret. | Source "Factorial (canned)", revision 1. Result shows `D0Vint(arg1=120)` with the revision and outcome. | Performed manually by the student, who reports it passed; per-step notes not recorded. | Pass (student report) |
| B3 | Click Fibonacci (canned). Click Interpret. | Revision 2. Result shows `D0Vint(arg1=55)`. The earlier factorial result is gone. | Performed manually by the student, who reports it passed; per-step notes not recorded. | Pass (student report) |
| B4 | Click Manual input. Type `D0Evar("x")`. Click Apply changes. | Revision increments. Previous results are cleared. Editor shows the applied text. | Performed manually by the student, who reports it passed; per-step notes not recorded. | Pass (student report) |
| B5 | Type an edit without applying. Try Lint and the source menu buttons. Then click Discard changes. | Menu and tool buttons are disabled while edits are unapplied. Discard restores the applied text. | Performed manually by the student, who reports it passed; per-step notes not recorded. | Pass (student report) |
| B6 | Apply a whitespace-only edit. Then try to load a non-UTF-8 file with Choose a file. | Each is rejected with a message. Previous applied source and revision remain. Rejected text stays in the editor for correction. | Performed manually by the student, who reports it passed; per-step notes not recorded. | Pass (student report) |
| B7 | Load factorial. Check the button row and Execute. Click Type-check, then Compile. | Buttons appear in order Lint, Interpret, Type-check, Compile, Execute. Execute is disabled with an explanation. Type-check and Compile each report "not yet implemented". | Performed manually by the student, who reports it passed; per-step notes not recorded. | Pass (student report) |
| B8 | Manual input `D0Evar("x")`, apply, click Lint. Then edit to `D0Elet("x", D0Eint(1), D0Evar("x"))`, apply, click Lint. | First: error naming `x`. Second: "No free variables found." | Performed manually by the student, who reports it passed; per-step notes not recorded. | Pass (student report) |
| B9 | Enter `D0Eint(` and click Interpret. Then enter `D0Eop2("/", D0Eint(1), D0Eint(0))` and click Interpret. | First: input (syntax) error. Second: runtime error mentioning ZeroDivisionError. Messages are distinguishable. | Performed manually by the student, who reports it passed; per-step notes not recorded. | Pass (student report) |
| B10 | Enter `D0Evar("<b>x</b>")`, apply, Lint. Enter a multi-line expression and check the output. | `<b>` text appears literally, not as bold. Multi-line source and output keep their line breaks. | Performed manually by the student, who reports it passed; per-step notes not recorded. | Pass (student report) |
| B11 | Load Fibonacci with `D0Eint(32)` in the editor (apply), click Interpret. Watch the status and buttons while it runs. | Status shows Busy while running; buttons are disabled. After about 5 seconds the run stops with a timeout message and controls come back. | Performed manually by the student, who reports it passed; per-step notes not recorded. | Pass (student report) |
| B12 | After B11, click Interpret on a short program (factorial). | Controls work again; the run completes normally (retry works). | Performed manually by the student, who reports it passed; per-step notes not recorded. | Pass (student report) |

## Known gaps

- Button order (F4) and literal line-break rendering (F9) are checked by eye in B7 and B10, not by tests.
- No browser automation has been run. The browser rows were performed manually by the student, who reports they passed; per-step observations were not written down.
