# CS413 Midterm 1: Compiling Extended LAMBDA into Pure Lambda-Calculus

## Python version and dependencies

Python 3.12 or later (developed and tested on Python 3.13.11). No third-party
dependencies; only the standard library (`unittest`, `dataclasses`, `enum`,
`abc`, `typing`) and `assigns/05/lambda1_vp.py`, imported unmodified.

## Commands (run from `assigns/06/`)

```bash
# Automated test suite (141 tests)
python3 -m unittest discover -s MySolution

# Documented end-to-end demonstration command (DEM-01)
python3 MySolution/demo.py
```

Both commands must be run with `assigns/06/` as the current working
directory (not from inside `MySolution/`), since `demo.py` and the test
package locate `assigns/05/lambda1_vp.py` relative to their own file
location, and `unittest discover` needs to see `MySolution` as a package
root for the `tests` package's relative imports to resolve. Equivalently,
from inside `MySolution/`, run `python3 -m unittest discover` directly.

## Module overview

| Module | Responsibility |
| --- | --- |
| `target_ast.py` | The pure target AST (`Var`/`Lam`/`App`), printer, free variables, capture-avoiding substitution, and the deterministic `FreshNamer` fresh-name policy. |
| `reducer.py` | The weak, left-to-right call-by-value reducer for target terms, with a configurable beta-value step budget (iterative, not recursive, so large budgets do not risk Python's recursion limit). |
| `church_encodings.py` | The closed Church-encoding library: `TRUE`/`FALSE`, `NUM(n)`, `PAIR`/`FST`/`SND`, `Z`, `I`, and all required arithmetic, comparison, and boolean combinators, expressed purely in `Var`/`Lam`/`App`. (Named `church_encodings.py`, not `encodings.py`, to avoid shadowing the Python standard library's `encodings` package.) |
| `compiler.py` | The compositional compiler, `compile_expr`, implemented as a `D0ExpVisitor[Term]` over `assigns/05/lambda1_vp.py`'s source AST. Rejects negative literals and unsupported operators anywhere in the tree. |
| `evaluator.py` | The single shared evaluator: `evaluate_source` (full, unbounded source-language semantics, used as the expected-answer oracle for terminating examples) and `evaluate_target` (delegates to `reducer.eval_target`, operating only on target syntax). Does not import `compiler.py`. |
| `observers.py` | Bounded observers (`observe_nat`, `observe_bool`, `observe_pair`) that decode target values into Python data using pure observation contexts evaluated by `reducer.eval_target`. |
| `demo.py` | The documented demonstration command: runs all 14 required examples through compilation, execution, and observation, and reports source, compiled term, reduction/observation statuses and step counts, and decoded vs. expected answers. |
| `tests/` | The `unittest` suite (141 tests across target AST/reducer, encodings, compiler, and observers/demo). |

## Budgets

`demo.py` uses `EXEC_BUDGET = 200_000` beta-value steps for program
execution and `OBS_BUDGET = 2_000` beta-value steps for decoding, reported
separately for each example; both are comfortably larger than the step
counts actually consumed by every terminating example (the largest,
`fibonacci(5)`, uses 1,794 execution steps and 45 observation steps). The
two divergent examples (`(lam x. 0) LOOP` and `LOOP`) exhaust `EXEC_BUDGET`
by construction, which is reported as budget exhaustion, not as a proof of
nontermination. Tests use smaller, case-appropriate budgets (typically
1,000-50,000), documented inline at each call site.

## Statuses and diagnostics

- `reducer.EvalResult(completed, value, steps)`: `completed=True` means a
  value was reached (possibly in zero steps); `completed=False` means the
  step budget was exhausted before a value was reached. `steps` is always
  the exact number of beta-value steps actually performed.
- `observers.ObserveResult(status, value, steps)`: `status` is one of
  `ObserveStatus.DECODED`, `EXHAUSTED` (the observation step budget ran
  out), or `MALFORMED` (the final shape did not match the expected kind's
  observation contract). `value` is populated only when `status is
  DECODED`.
- `compiler.CompileError`: raised for a negative integer literal or an
  unsupported operator spelling, anywhere in the source AST (including
  unselected `if` branches, unapplied lambda bodies, and fix bodies),
  identifying the offending literal or operator name in the message.
- `evaluator.SourceEvalError`: raised by `evaluate_source` for an
  ill-formed source program (e.g. applying a non-function, or a
  type-mismatched operator use); only exercised for terminating,
  well-formed examples in this submission.

## Limitations

- No source parser; examples are built directly as `lambda1_vp` AST nodes,
  as permitted by the assignment.
- No signed integers, lists, or division; these are explicitly out of
  scope and rejected by the compiler.
- Static type checking is not implemented; ill-typed source programs may
  raise a Python exception from `evaluate_source` rather than a
  dedicated diagnostic, as permitted by the assignment ("static type
  checking and runtime type-error preservation are not required").
- `reducer.eval_target`'s handling of an open term in function position
  (a free variable applied to something) treats it as stuck rather than
  as an error; execution is intended for closed programs, where this case
  does not arise, consistent with the assignment's "Execution may be
  restricted to closed terms" allowance.

## Slides and recording

Slides (PDF): `slides.pdf`, in this directory. Editable source:
https://docs.google.com/presentation/d/1DvpwWvFtkiYTx_jiCoWCI87l6IVQnfozAvCWTE5TH8M/edit?usp=sharing

Presentation recording: `presentation.mp4`, in this directory (~16:44).
Also available at:
https://docs.google.com/videos/d/1_Zh2LeVLm7pz4GeJcwUsp7AaqTBBg3ooE8jMAkUTIbk/play
