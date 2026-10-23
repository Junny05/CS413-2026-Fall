"""Documented command-line demonstration (DEM-01, DEM-02).

Run from assigns/06/MySolution/:

    python3 demo.py

For each example this builds the source AST directly in Python, compiles
it, prints the generated pure term, reduces it under EXEC_BUDGET
beta-value steps, decodes the result under OBS_BUDGET further beta-value
steps (both budgets, and the step counts actually used, are reported
separately), and compares the decoded answer with the expected answer
obtained from evaluator.evaluate_source (for terminating examples) or
with a documented expected "budget exhaustion" outcome (for the two
divergent examples).
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "05"))
from lambda1_vp import (
    D0Eapp, D0Ebtf, D0Eif0, D0Eint, D0Elam, D0Elet, D0Eop1, D0Eop2,
    D0Epair, D0Epfst, D0Epsnd, D0Evar, D0Efix,
)

from compiler import compile_expr
from church_encodings import TRUE
from evaluator import evaluate_source
from reducer import eval_target
from target_ast import print_term
from observers import observe_nat, observe_bool, ObserveStatus

EXEC_BUDGET = 200_000   # beta-value steps allowed for program execution
OBS_BUDGET = 2_000      # beta-value steps allowed for decoding the result

LOOP = D0Eapp(D0Efix("loop", "x", D0Eapp(D0Evar("loop"), D0Evar("x"))), D0Eint(0))


def _fact() -> D0Eapp:
    body = D0Efix(
        "fact", "n",
        D0Eif0(
            D0Eop2("==", D0Evar("n"), D0Eint(0)),
            D0Eint(1),
            D0Eop2("*", D0Evar("n"), D0Eapp(D0Evar("fact"), D0Eop2("-", D0Evar("n"), D0Eint(1)))),
        ),
    )
    return D0Eapp(body, D0Eint(4))


def _fib() -> D0Eapp:
    body = D0Efix(
        "fib", "n",
        D0Eif0(
            D0Eop2("<=", D0Evar("n"), D0Eint(1)),
            D0Evar("n"),
            D0Eop2(
                "+",
                D0Eapp(D0Evar("fib"), D0Eop2("-", D0Evar("n"), D0Eint(1))),
                D0Eapp(D0Evar("fib"), D0Eop2("-", D0Evar("n"), D0Eint(2))),
            ),
        ),
    )
    return D0Eapp(body, D0Eint(5))


DEMOS: list[tuple[str, object, str, object]] = [
    ("2 + 3 * 4", D0Eop2("+", D0Eint(2), D0Eop2("*", D0Eint(3), D0Eint(4))), "nat", 14),
    ("2 - 5", D0Eop2("-", D0Eint(2), D0Eint(5)), "nat", 0),
    ("if 2 <= 3 then 7 else 9",
     D0Eif0(D0Eop2("<=", D0Eint(2), D0Eint(3)), D0Eint(7), D0Eint(9)), "nat", 7),
    ("let x = 3 in (lam y. x + y) 4",
     D0Elet("x", D0Eint(3),
            D0Eapp(D0Elam("y", D0Eop2("+", D0Evar("x"), D0Evar("y"))), D0Eint(4))),
     "nat", 7),
    ("fst (pair 2 true)", D0Epfst(D0Epair(D0Eint(2), D0Ebtf(True))), "nat", 2),
    ("snd (pair 2 true)", D0Epsnd(D0Epair(D0Eint(2), D0Ebtf(True))), "bool", True),
    ("(lam f. f 3) (lam x. x + 1)",
     D0Eapp(D0Elam("f", D0Eapp(D0Evar("f"), D0Eint(3))),
            D0Elam("x", D0Eop2("+", D0Evar("x"), D0Eint(1)))),
     "nat", 4),
    ("true and false", D0Eop2("and", D0Ebtf(True), D0Ebtf(False)), "bool", False),
    ("false or true", D0Eop2("or", D0Ebtf(False), D0Ebtf(True)), "bool", True),
    ("if true then 1 else LOOP", D0Eif0(D0Ebtf(True), D0Eint(1), LOOP), "nat", 1),
    ("(lam x. 0) LOOP", D0Eapp(D0Elam("x", D0Eint(0)), LOOP), "nat", None),
    ("factorial(4)", _fact(), "nat", 24),
    ("fibonacci(5)", _fib(), "nat", 5),
    ("LOOP", LOOP, "nat", None),
]


def _run_one(name: str, source, kind: str, expected) -> bool:
    print(f"=== {name} ===")
    term = compile_expr(source)
    rendered = print_term(term)
    shown = rendered if len(rendered) <= 300 else rendered[:300] + " ...(truncated)"
    print(f"compiled: {shown}")

    exec_result = eval_target(term, EXEC_BUDGET)
    print(f"execution: completed={exec_result.completed} steps={exec_result.steps} "
          f"(budget={EXEC_BUDGET})")

    if expected is None:
        ok = not exec_result.completed
        print(f"expected: budget exhaustion -> {'OK' if ok else 'MISMATCH'}")
        print()
        return ok

    if not exec_result.completed:
        print("expected a value but execution exhausted its budget -> MISMATCH")
        print()
        return False

    observe = observe_nat if kind == "nat" else observe_bool
    obs = observe(exec_result.value, OBS_BUDGET)
    print(f"observation: status={obs.status.name} steps={obs.steps} (budget={OBS_BUDGET})")

    decoded = obs.value if obs.status is ObserveStatus.DECODED else None
    print(f"decoded answer: {decoded}; expected answer: {expected}")

    ok = obs.status is ObserveStatus.DECODED and decoded == expected
    print("OK" if ok else "MISMATCH")
    print()
    return ok


def main() -> int:
    results = [_run_one(name, source, kind, expected) for name, source, kind, expected in DEMOS]
    total = len(results)
    passed = sum(results)
    print(f"{passed}/{total} demonstrations matched their expected outcome.")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
