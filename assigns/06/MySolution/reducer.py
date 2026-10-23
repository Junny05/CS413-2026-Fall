"""Weak, left-to-right call-by-value reducer for target terms.

Implements RED-01..RED-05: a beta-value step contracts
    (lam x. body) v  -->  body[x := v]
only when v is a value (a Lam). Evaluation never reduces beneath a lambda
and never performs eta reduction. The evaluator accepts a configurable,
nonnegative maximum number of beta-value steps and reports either
completion with the resulting value, or budget exhaustion, together with
the exact number of beta-value steps performed. Alpha-renames performed
internally by substitution do not count as steps.

Implemented iteratively (an explicit control stack, not Python recursion)
so that step budgets in the thousands do not risk hitting Python's
recursion limit.
"""

from __future__ import annotations

from dataclasses import dataclass

from target_ast import App, Lam, Term, Var, substitute


@dataclass(frozen=True)
class EvalResult:
    completed: bool
    value: Term | None
    steps: int


def is_value(t: Term) -> bool:
    return isinstance(t, Lam)


def eval_target(term: Term, budget: int) -> EvalResult:
    """Evaluate term under at most `budget` beta-value steps.

    term is never mutated. A free variable in function position (only
    possible for an open term) is treated as stuck and left in place,
    rather than as an error; execution is documented as intended for
    closed terms, where this case cannot arise.
    """
    if budget < 0:
        raise ValueError("step budget must be nonnegative")

    steps = 0
    stack: list[tuple[str, Term]] = []
    t: Term = term
    mode_eval = True  # True: drive t down to irreducible form; False: propagate t up.

    while True:
        if mode_eval:
            if isinstance(t, App):
                stack.append(("ARG", t.arg))
                t = t.fn
                continue
            # t is Var or Lam: irreducible on its own. Start propagating up.
            mode_eval = False
            continue

        if not stack:
            return EvalResult(completed=True, value=t, steps=steps)

        tag, frame_term = stack.pop()
        if tag == "ARG":
            # t is the evaluated function position; now evaluate the argument.
            stack.append(("APPLY", t))
            t = frame_term
            mode_eval = True
            continue

        # tag == "APPLY": frame_term is the evaluated function, t is the
        # evaluated argument.
        fn_value = frame_term
        arg_value = t
        if isinstance(fn_value, Lam):
            if steps >= budget:
                return EvalResult(completed=False, value=None, steps=steps)
            steps += 1
            t = substitute(fn_value.body, fn_value.param, arg_value)
            mode_eval = True
            continue
        # fn_value is a free Var (stuck, open term): leave the application
        # in place as an irreducible result and keep unwinding the stack.
        t = App(fn_value, arg_value)
        mode_eval = False
