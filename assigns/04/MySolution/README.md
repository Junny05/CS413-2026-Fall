# LAMBDA Web Front-End

A local, single-user web front-end for the LAMBDA interpreter in `lambda1.py`. You load or type a LAMBDA constructor expression, check it for undeclared variables (Lint), evaluate it (Interpret), and read the textual result in the browser. Type-check and Compile are placeholders; Execute is disabled until a compiler exists.

Architecture: see [ARCHITECTURE.md](ARCHITECTURE.md). Test results and the manual browser checklist: see [TESTING.md](TESTING.md).

## Runtime versions

- Python 3.13.11 (used for development and all test runs). `lambda1.py` requires Python 3.12+ for `type` statements; Python 3.12 has not been tested.
- pytest 9.1.1 (the only dependency, pinned in `requirements.txt`)
- Standard library only for the web layer (`http.server`, `email`, `urllib`)

## Setup

Run from `assigns/04/MySolution/`:

```
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
```

`lambda1.py` is the supplied interpreter file, copied here so the submission runs from this folder alone.

## Run the tests

```
./.venv/bin/python -m pytest -q
```

Expected: `109 passed`.

## Start the application

```
./.venv/bin/python app.py
```

Then open **http://127.0.0.1:8000/** in a browser. The server binds only to the loopback interface (127.0.0.1); it is not reachable from other machines. Stop it with Ctrl-C.

## Using the application

1. **Load source:** Choose a UTF-8 text file, click Manual input (blank editor), or pick Factorial (canned) or Fibonacci (canned).
2. **Edit:** type in the editor, then click **Apply changes** to make the text the applied source, or **Discard changes** to revert. Editing a file does not change the file on disk. While edits are unapplied, source replacement and tool actions are blocked.
3. **Actions:** **Lint**, **Interpret**, **Type-check**, **Compile**, **Execute** (in that order). Actions need applied source. Each result shows its action, the source revision it was computed for, and its outcome.

Every accepted source change creates a new revision and clears earlier results.

## Demonstration

Sample inputs are in `examples/`.

**1. Factorial and Fibonacci.** Click *Factorial (canned)*, then *Interpret*: the result is `D0Vint(arg1=120)`. Click *Fibonacci (canned)*, then *Interpret*: `D0Vint(arg1=55)`. Revision goes 1 → 2, and the factorial result is cleared.

**2. Open expression, then closed.** Click *Manual input*, type `D0Evar("x")`, click *Apply changes*, then *Lint*. Result: `Undeclared variable(s): x` (outcome `language_error`). Edit it to `D0Elet("x", D0Eint(1), D0Evar("x"))`, apply, then *Lint*: `No free variables found.`

**3. Runtime failure after successful Lint.** Enter `D0Eop2("/", D0Eint(1), D0Eint(0))` (`examples/error_division_by_zero.lam`). *Lint* passes because the expression is closed and Lint never evaluates it. *Interpret* reports `runtime_error`: `ZeroDivisionError`. Lint checks names; Interpret runs the program. A passing Lint says the program is closed, not that it will succeed.

**4. Placeholders.** *Type-check* reports "Type checking is not yet implemented." *Compile* reports "Compilation is not yet implemented." *Execute* is disabled, with the reason: it runs code produced by Compile, and no compiled code exists yet. Interpretation is never used as a stand-in for Execute.

**5. Input errors.** `examples/error_syntax.lam` (unclosed parenthesis) and `examples/error_not_a_constructor.lam` (`__import__(...)`) are reported as `input_error` before anything is evaluated.

## Supported input format

Input is a single Python constructor expression of type `d0exp`, using only the constructors defined in `lambda1.py`:

`D0Eint`, `D0Ebtf`, `D0Eop1`, `D0Eop2`, `D0Evar`, `D0Elam`, `D0Efix`, `D0Eapp`, `D0Eif0`, `D0Elet`, `D0Epair`, `D0Epfst`, `D0Epsnd`

- Nested constructors, `#` comments, and multi-line expressions are accepted.
- Arguments must be literals or constructor calls: integers (optionally negative), `True`/`False`, and strings.
- The reader parses the text with Python's `ast` module and builds constructor objects itself. Nothing is executed, so names, attributes, imports, and other calls are rejected.

## Execution bounds

- Source size limit: **64 KiB** (UTF-8 bytes). Larger uploads or edits are rejected with a notice. Typed edits are sent form-encoded, which can expand each byte to three, so the HTTP request body is capped at 208 KiB (3 × 64 KiB + 16 KiB).
- Interpret runs in a separate process with a **5-second** timeout. On timeout the process is terminated and the result is `timeout`.
- Recursion that exceeds Python's recursion limit is reported as a runtime error.
- Lint does not evaluate anything, so it has no time bound beyond parsing.
- One operation runs at a time; while it runs, the page shows "Busy" and actions and edits are disabled. While a run is in progress, the page polls `/status` twice a second and reloads when the run finishes.

## Known limitations

- **Unbound variables in Interpret:** `lambda1.py` returns an error sentinel `D0V000()` for an unbound name, and the enclosing operator then reports `TypeError: D0Vint(...) expected: D0V000()`. The outcome is correctly `runtime_error`, but the message is less clear than it could be. Lint is the intended way to find undeclared names.
- **Interpreter error messages** come from `lambda1.py` and are shown as Python exception text.
- **Button order and literal line-break rendering** are verified manually (TESTING.md B7 and B10), not by automated tests.
- **Browser testing** has not been automated; the manual checklist in TESTING.md is the browser verification.
- **Single user, single server, in-memory state.** Source and results are lost when the server stops. No accounts, persistence, or public deployment.
- **Timeout uses a process per run.** On the development machine a small Interpret took about 40 ms on average, including process start.
- **No type checker or compiler yet.** Execute cannot run anything.

## Reflection

MVC made the most difference to testing. The model enforces the rules that matter (no changes while edits are pending, no changes while an operation is running, empty and oversized input rejected, stale results cleared on each revision), and I could test those rules without starting a server or a browser. The controller is tested with a fake backend that injects failures and blocks mid-run, which exercised the busy-state and retry paths directly. The view only renders a snapshot, so the escaping rules and button states sit in one place.

Separation was hardest for state that several parts touch. The busy flag has to live in the model so that edits and source replacement can be refused, but it is set by the controller around a background thread, so the controller takes a lock around every model access. The rejected-edit rule also needed care: the model keeps the rejected text as the pending draft, so the editor can show it again, and the view has no say in that.

A future change the architecture makes easier is a real compiler. `Compile` would produce an artifact, `Execute` would take it, and the model already has an artifact slot that is cleared on every revision, so stale generated code cannot be run. The browser code would not change: it renders the same snapshot and the same buttons, and only the backend object would gain a working `compile` and `execute`.

## Sample inputs

| File | Purpose | Expected |
| --- | --- | --- |
| `examples/factorial.lam` | Factorial of 5 | Interpret: `D0Vint(arg1=120)` |
| `examples/fibonacci.lam` | Fibonacci of 10 | Interpret: `D0Vint(arg1=55)` |
| `examples/error_open_variable.lam` | Undeclared `x` | Lint: `language_error`, lists `x` |
| `examples/error_division_by_zero.lam` | Runtime failure | Lint passes; Interpret: `runtime_error` |
| `examples/error_syntax.lam` | Malformed input | `input_error` |
| `examples/error_not_a_constructor.lam` | Rejected call | `input_error` |

## Files

- `app.py`: HTTP adapter (routes, uploads, redirects)
- `view.py`: renders a snapshot as HTML
- `controller.py`: user actions, background execution, view snapshot
- `model.py`: applied source, draft, revisions, results, busy state, rules
- `lambda_backend.py`: language-tool adapter (lint, interpret, typecheck, compile, execute) and the constructor reader
- `lambda1.py`: supplied interpreter
- `samples.py`: canned factorial and Fibonacci programs
- `tests/`: automated tests
