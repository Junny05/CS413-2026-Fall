# AI Transcript

## AI tool used

Claude Code (Anthropic's CLI), running Claude Sonnet 5, in a terminal session in the course repository. The assistant read files, ran commands, wrote and edited code and documents, and ran the tests. The student directed each step and approved it before the assistant acted.

## How the work was directed

The student asked the assistant to check in before every step. Each step was proposed in one or two sentences, and the assistant waited for approval before changing anything. The main steps and approvals were:

1. Read the assignment and the stakeholder brief (read-only).
2. Inspect the solution folders and the key functions in `lambda1.py` (read-only).
3. Check Python version and the `lambda1.py` import (read-only).
4. Create a project-local virtual environment with pytest and a `.gitignore`.
5. Write the language-tool adapter (`lambda_backend.py`); the student asked for the design to be shown first.
6. Write the adapter tests and copy `lambda1.py` into `MySolution/`.
7. Write the source model (`model.py`) and its tests.
8. Write the controller (`controller.py`) and tests. The student chose the standard library over Flask for the web layer.
9. Write the web layer (`view.py`, `app.py`) and HTTP tests. Run the server for the student to try in Chrome.
10. Browser smoke test: the student declined the Chrome extension, so the assistant wrote a manual checklist instead of running a browser test.

## Important prompts and what the assistant suggested

- **Assignment prompt:** the student pasted the full assignment and asked for a step-by-step approach with approval at each step. The assistant proposed the steps above.
- **Design of the adapter:** the assistant proposed a restricted reader based on Python's `ast` module (no `exec`), a result type carrying operation, revision, and status, and interpretation in a child process so a nonterminating program can be stopped. The student approved this after seeing the design.
- **Web framework:** the assistant offered Flask and the standard library. The student chose the standard library to avoid extra dependencies.
- **Browser testing:** the assistant asked whether to drive Chrome. The student declined the extension, so no browser test was run. Browser checks are a manual checklist (TESTING.md B1–B12) that has not been performed by the assistant.

## How the output was reviewed and tested

- Every module was run against the automated tests before the next step. Final state: 109 tests passing (`./.venv/bin/python -m pytest -q`).
- **Audit after the first commits:** a review against the full assignment found that typed edits up to the 64 KiB limit were rejected by the form-body cap (form encoding expanded them about threefold), and the busy page reloaded itself every second. Both were fixed and tested.
- The lint and interpret behavior was checked directly against the examples in `examples/`, including the open-variable and runtime-failure examples.
- The web server was started and fetched with `curl`, and then the student opened it in Chrome to confirm it works.
- Some assistant output was wrong and was corrected after testing or review. These are the ones worth recording:
  - **Multi-line input bug:** the reader rejected indented multi-line input because it did not dedent before `ast.parse`. A test caught it; the fix was `textwrap.dedent`.
  - **Null-byte message:** a test expectation was wrong about how Python reports null bytes. The test was corrected, not the code.
  - **Draft blocking gap:** `replace_source` did not refuse while unapplied edits were pending, although the assignment requires it. A test caught it; the check was added to the model.
  - **Impossible test removed:** a stale-result test described a state the busy rule already prevents. The test and its guard were removed, and a test for the busy rule was added instead.
  - **Wrong test string:** an HTTP test expected the revision markup in the wrong order. The assertion was corrected to match the rendered HTML.
  - **Unverified claim:** the assistant first wrote a timing estimate in the README for process start-up. It was replaced with a measured value (about 40 ms).
  - **Fabricated history:** the assistant's first draft of the README reflection described a design change that never happened. It was removed, and the reflection was rewritten to describe only what the code does.
- The reflection in README.md was drafted by the assistant and must be rewritten in the student's own words before submission.
- Known limitation found during review, not fixed: interpreting an open expression produces `TypeError: D0Vint(...) expected: D0V000()` because `lambda1.py` returns an error sentinel for unbound names. The outcome is still reported as a runtime error.

## What was not AI-generated

- `lambda1.py` is the supplied file from the course, copied unchanged.
- The assignment text and the stakeholder brief are the course's.
