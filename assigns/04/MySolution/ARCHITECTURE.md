# Architecture

## Component diagram

Arrows point from a module to the modules it imports. Module-level imports only, checked against the source.

```
app.py  (HTTP adapter)
 |-- controller.py  (Controller)
 |     |-- model.py          (SourceModel, decode_upload, MANUAL_NAME)
 |     |     '-- lambda_backend.py  (Operation, Result, Status types only)
 |     |-- lambda_backend.py (run operations)
 |     '-- samples.py        (canned FACTORIAL, FIBONACCI)
 |-- model.py          (SourceModel, MAX_SOURCE_BYTES, ModelError)
 |-- view.py           (render_page)
 |     |-- controller.py     (ViewState, BUTTON_ORDER, CANNED)
 |     '-- lambda_backend.py (Operation, for button labels)
 '-- lambda_backend.py (Operation; main() passes this module as the backend)

lambda_backend.py
 '-- lambda1.py  (supplied interpreter: d0exp_fvset, d0exp_evaluate, constructors)
```

Dependency rules, checked against the imports:

- `model.py` imports `lambda_backend` only for the `Operation`, `Result`, and `Status` types. It never calls the backend and imports no web, HTML, or HTTP code.
- `view.py` never imports the model. It reads `ViewState` and the button and canned-example tables from the controller. Its one use of the backend module is the `Operation` enum for labels; it calls no backend function.
- `app.py` is the only module that knows HTTP. It calls the controller and renders through `view.py`.
- `lambda_backend.py` is the only module that imports `lambda1.py`.
- `samples.py` imports nothing.

## Responsibility table

| Role | Implementation | Responsibility |
| --- | --- | --- |
| Model | `model.py`: `SourceModel` | Applied source, unapplied draft, revision counter, results per operation, artifact slot, busy flag. Enforces: no edits or replacement while a draft is pending or an operation runs; no tool action without applied source and with pending edits; empty, whitespace-only, oversized, or non-UTF-8 input rejected (`validate_text`, `decode_upload`); every accepted change creates a revision and clears results and artifact. |
| View | `view.py`: `render_page(ViewState, notice)` | Renders the source menu, editor, action buttons with disabled reasons, status, notices, and results as escaped HTML. Contains no decisions about what is allowed; it displays the flags the controller computed. A small inline script forwards editor input to `/draft`. |
| Controller | `controller.py`: `Controller` | Maps user actions to model changes; decides button states (`snapshot`); runs backend operations on a single background thread under a lock; records results back into the model; builds `ViewState` snapshots. Owns the canned catalog (`CANNED`). |
| HTTP adapter | `app.py`: `make_handler`, `make_server`, `_multipart_file` | Parses routes and form and multipart bodies, enforces the request size cap, turns `ModelError` and `ValueError` into a notice carried on a redirect, and binds to 127.0.0.1 only. |
| Backend adapter | `lambda_backend.py`: `lint`, `interpret`, `typecheck`, `compile`, `execute`, `read_expression` | Parses constructor input with a restricted reader (`ast`, no `exec`); computes free variables with `d0exp_fvset`; evaluates in a child process with `d0exp_evaluate`; returns `Result` objects; placeholder operations return `not_implemented`. |

## Who coordinates the backend

The **controller** calls the backend. The model only checks state rules and records results. This keeps the model free of I/O and concurrency, so it can be tested with no server and no interpreter. The controller passes the backend object into its constructor and holds the dispatch table, so tests can substitute a fake backend without touching the view.

## Sequence: Load source → Lint → Interpret

Undeclared-variable case, with the source `D0Eop2("+", D0Evar("x"), D0Eint(1))`:

1. Browser POSTs `/canned` (or `/upload`, or `/manual` then `/apply`). `app.py` calls `Controller.load_canned` (or `load_upload`, or `open_manual` then `edit` and `apply_changes`).
2. The controller calls `SourceModel.replace_source` (or `apply_changes`). The model validates the text, sets `applied`, increments `revision` to 1, and clears results.
3. `app.py` redirects (303) to `/`. The browser GETs `/`; the controller builds a `ViewState`; `view.py` renders it.
4. Browser POSTs `/run` with `op=lint`. `app.py` calls `Controller.run(Operation.LINT)`.
5. The controller calls `SourceModel.start_operation`, which checks busy, pending edits, and applied source, sets `busy = LINT`, and returns revision 1. The controller submits `_work` to its executor and returns immediately.
6. Background thread: `_work` calls `lambda_backend.lint(source, 1)`.
7. `lint` calls `read_expression`, which returns a `D0Eop2`. `d0exp_fvset` returns `frozenset({"x"})`. `lint` returns `Result(LINT, 1, LANGUAGE_ERROR, "Undeclared variable(s): x", ("x",))`. Nothing is evaluated.
8. `_work` calls `_finish`: the controller takes the lock, `SourceModel.finish_operation` clears `busy` and stores the result under `LINT`.
9. The page shows the stored result (a busy page polls `/status` and reloads once the run finishes). `view.py` shows "Lint · revision 1 · language_error" and the message, escaped.
10. Browser POSTs `/run` with `op=interpret`. Steps 5–9 repeat with `interpret`. `lambda_backend.interpret` parses the same expression, starts a spawned process, and evaluates `d0exp_evaluate(expr, ENVnil())`. The unbound `x` yields the error sentinel, and the enclosing `+` raises `TypeError`. The child reports `("runtime", "TypeError: ...")`, and the result is `RUNTIME_ERROR`. The Interpret result is shown separately from the Lint result, which is what the assignment asks us to demonstrate.

A closed expression such as `D0Elet("x", D0Eint(1), D0Evar("x"))` passes Lint (`OK`, "No free variables found.") and interprets to `D0Vint(arg1=1)`.

## Backend contract

Every operation takes the source (or artifact) and the revision it applies to, and returns a `Result`:

```
Result(operation: Operation, revision: int | None, status: Status, message: str, free_vars: tuple[str, ...])
```

| Operation | Input | Status values it may return |
| --- | --- | --- |
| `lint(source, revision)` | source text | `ok` (no free variables), `input_error`, `language_error` (free variables; names in `free_vars`, sorted) |
| `interpret(source, revision, timeout)` | source text | `ok` (value text such as `D0Vint(arg1=42)`), `input_error`, `runtime_error` (includes error sentinel), `timeout` |
| `typecheck(source, revision)` | source text | `not_implemented` |
| `compile(source, revision)` | source text | `not_implemented` |
| `execute(artifact, revision)` | generated artifact | `not_implemented` (until Compile exists) |

- `backend_error` is set by the controller, not the adapter, when a backend call raises an unexpected exception. The page shows it and keeps the applied source for retry.
- `timeout` is set by the adapter when the child process exceeds the interpret timeout (5 s); the child is terminated.
- Every `Result` carries the revision it was computed for. The model stores a result only under its operation, and clears all results when the revision changes, so a result is always shown against the source it came from.

## Design decisions and tradeoffs

**1. Interpretation runs in a child process.** `d0exp_evaluate` is ordinary Python recursion and can loop forever. A thread cannot be killed in Python, so a nonterminating program would keep the page busy indefinitely. A child process can be terminated at the deadline. The cost is a process start on each Interpret (about 40 ms here) and the need for the expression to be picklable (the constructor dataclasses are). We accept that cost for a bound the assignment requires.

**2. The model holds state rules; the controller holds coordination.** The model refuses an action if it would break a rule (pending edits, busy, no source), but it never calls the backend or starts a thread. The controller does the calling, locking, and background work, then tells the model the result. The benefit is that the model is testable with no concurrency and no interpreter. The cost is that the controller must remember to lock around every model access. A single `RLock` in the controller does that, and the busy flag in the model is what makes concurrent requests safe to reject rather than queue.

## Artifact contract (intended, not implemented)

An artifact is produced only by `compile(source, revision)` and must carry:

| Field | Meaning |
| --- | --- |
| `revision` | The source revision it was compiled from. Required. |
| `location` | Where the generated code lives (for example, a temporary file path or a Python callable). Owned by the compiler adapter. |
| `producer` | The operation that produced it, always `compile`. |

Rules the model enforces (intended):

- An artifact is stored only if its `revision` equals the model's current revision.
- Every accepted source change clears the artifact slot, and so does any failed recompilation. Execute therefore never sees an artifact for old source.
- `execute(artifact, revision)` runs the artifact as-is. It never recompiles and never falls back to interpretation.

Until a compiler exists, the slot is always empty and Execute is disabled.

## Replacing placeholders with real type-checking and compilation

- **Type-checking:** `typecheck(source, revision)` gets a real implementation returning `Result(TYPECHECK, revision, OK | language_error, ...)`. The view and controller need no change: the button already dispatches to `backend.typecheck`. A type checker would run in the same child-process pattern as Interpret if it can loop.
- **Compilation:** `compile(source, revision)` would produce an artifact (for example, a path to generated code or a Python callable, tagged with its revision). It returns `Result(COMPILE, revision, OK, ...)` and the artifact is stored in the model's `artifact` slot. Storing it requires a model method that checks the revision matches the current revision, because a compile result for an old revision must not be attached to new source.
- **How generated code reaches Execute:** `Controller._run_execute` already reads `model.artifact` and refuses when it is `None`. When an artifact exists, Execute calls `backend.execute(artifact, revision)`, which runs the generated code without recompiling. Because every accepted source change clears the artifact slot (`_clear_results`), a source change or a failed recompile leaves no artifact, so Execute is disabled rather than running stale code.

## Extension (not required): a real compiler

Connecting a compiler would add: a `compile` implementation that writes its output to a temporary file keyed by revision; a model method `attach_artifact(artifact, revision)` that rejects a revision mismatch; and `execute` that loads and runs the artifact in a child process with the same timeout. The view and the rest of the controller do not change, which is the point of the contract.
