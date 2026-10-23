"""Bounded observers that decode target values into Python data.

Implements OBS-01..OBS-03: all observation is done through pure target
observation contexts, evaluated by the shared call-by-value engine
(evaluator.evaluate_target), under a caller-supplied, separate
observation step budget. Python only inspects the *final*, already fully
(top-level) reduced shape; it never evaluates under lambdas itself and
never substitutes host arithmetic for target reduction. Decoding accepts
the caller's expected kind, since NUM(0) and FALSE share a lambda
representation, and tolerates alpha-renaming and redexes left inside
unevaluated lambda bodies (because the value is always freshly re-applied
to the observation context's own fixed combinators and then reduced to a
value before any Python-side pattern match).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from target_ast import App, Lam, Term, Var, alpha_equivalent
from reducer import eval_target


class ObserveStatus(Enum):
    DECODED = auto()
    EXHAUSTED = auto()
    MALFORMED = auto()


@dataclass(frozen=True)
class ObserveResult:
    status: ObserveStatus
    value: object | None  # int, bool, or a nested tuple for pairs
    steps: int


# STEP = lam tail. lam c. lam z. c tail
NAT_STEP = Lam("tail", Lam("c", Lam("z", App(Var("c"), Var("tail")))))
# BASE = lam c. lam z. z
NAT_BASE = Lam("c", Lam("z", Var("z")))

# Two distinct, closed marker values for boolean observation.
BOOL_MARK_TRUE = Lam("_m1", Var("_m1"))
BOOL_MARK_FALSE = Lam("_m2", Lam("_n2", Var("_m2")))


def observe_nat(value_term: Term, budget: int) -> ObserveResult:
    """Decode value_term, expected to be a Church numeral, as a Python int.

    Applies value_term to NAT_STEP and NAT_BASE and reduces under `budget`
    beta-value steps, then walks the resulting value structurally: a node
    shaped like "lam c. lam z. c <tail>" (up to alpha) contributes one unit
    and continues into <tail>; a node shaped like "lam c. lam z. z" (up to
    alpha, i.e. z referenced directly) is the base case.
    """
    probe = App(App(value_term, NAT_STEP), NAT_BASE)
    result = eval_target(probe, budget)
    if not result.completed:
        return ObserveResult(ObserveStatus.EXHAUSTED, None, result.steps)

    cur = result.value
    count = 0
    while True:
        if not isinstance(cur, Lam):
            return ObserveResult(ObserveStatus.MALFORMED, None, result.steps)
        p1 = cur.param
        inner = cur.body
        if not isinstance(inner, Lam):
            return ObserveResult(ObserveStatus.MALFORMED, None, result.steps)
        p2 = inner.param
        body = inner.body
        if isinstance(body, Var) and body.name == p2:
            return ObserveResult(ObserveStatus.DECODED, count, result.steps)
        if isinstance(body, App) and isinstance(body.fn, Var) and body.fn.name == p1:
            cur = body.arg
            count += 1
            continue
        return ObserveResult(ObserveStatus.MALFORMED, None, result.steps)


def observe_bool(value_term: Term, budget: int) -> ObserveResult:
    """Decode value_term, expected to be a Church boolean, as a Python bool."""
    probe = App(App(value_term, BOOL_MARK_TRUE), BOOL_MARK_FALSE)
    result = eval_target(probe, budget)
    if not result.completed:
        return ObserveResult(ObserveStatus.EXHAUSTED, None, result.steps)

    value = result.value
    if alpha_equivalent(value, BOOL_MARK_TRUE):
        return ObserveResult(ObserveStatus.DECODED, True, result.steps)
    if alpha_equivalent(value, BOOL_MARK_FALSE):
        return ObserveResult(ObserveStatus.DECODED, False, result.steps)
    return ObserveResult(ObserveStatus.MALFORMED, None, result.steps)


# FST = lam p. p (lam a. lam b. a); SND = lam p. p (lam a. lam b. b)
_PAIR_FST = Lam("p", App(Var("p"), Lam("a", Lam("b", Var("a")))))
_PAIR_SND = Lam("p", App(Var("p"), Lam("a", Lam("b", Var("b")))))


def observe_pair(value_term: Term, expected_kinds: tuple[object, object],
                  exec_budget: int, obs_budgets: tuple[int, int]) -> ObserveResult:
    """Decode value_term, expected to be a Church pair, as a Python tuple.

    First evaluates value_term to a value under exec_budget. Then applies
    each Church projection and evaluates the projection under exec_budget,
    and finally observes each component with its expected kind
    ("nat", "bool", or a nested (kind1, kind2) tuple for a nested pair)
    under its own entry of obs_budgets. Execution and observation budgets
    and the resulting steps are kept and reported separately.
    """
    head = eval_target(value_term, exec_budget)
    if not head.completed:
        return ObserveResult(ObserveStatus.EXHAUSTED, None, head.steps)

    first_proj = eval_target(App(_PAIR_FST, head.value), exec_budget)
    second_proj = eval_target(App(_PAIR_SND, head.value), exec_budget)
    if not first_proj.completed or not second_proj.completed:
        steps = head.steps + first_proj.steps + second_proj.steps
        return ObserveResult(ObserveStatus.EXHAUSTED, None, steps)

    kind1, kind2 = expected_kinds
    budget1, budget2 = obs_budgets
    comp1 = _observe_by_kind(first_proj.value, kind1, exec_budget, budget1)
    comp2 = _observe_by_kind(second_proj.value, kind2, exec_budget, budget2)
    total_steps = head.steps + first_proj.steps + second_proj.steps + comp1.steps + comp2.steps
    if comp1.status is not ObserveStatus.DECODED:
        return ObserveResult(comp1.status, None, total_steps)
    if comp2.status is not ObserveStatus.DECODED:
        return ObserveResult(comp2.status, None, total_steps)
    return ObserveResult(ObserveStatus.DECODED, (comp1.value, comp2.value), total_steps)


def _observe_by_kind(term: Term, kind: object, exec_budget: int, obs_budget: int) -> ObserveResult:
    if kind == "nat":
        return observe_nat(term, obs_budget)
    if kind == "bool":
        return observe_bool(term, obs_budget)
    if isinstance(kind, tuple):
        return observe_pair(term, kind, exec_budget, (obs_budget, obs_budget))
    raise ValueError(f"unknown expected kind: {kind!r}")
