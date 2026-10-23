"""The shared evaluator: one module handling both source ASTs and target
terms, as required by Assign06 ("Use one evaluator for both source ASTs
and target terms").

evaluate_source(expr) implements the source-language semantics directly
(left-to-right call-by-value, boolean if0, short-circuit and/or,
truncated subtraction, pairs, let, fix) and is not step-bounded, per the
assignment ("Source-side evaluation is required only for terminating
examples and need not be step-bounded").

evaluate_target(term, budget) evaluates a pure target term for exactly
the variable/lambda/application cases, under a configurable beta-value
step budget; it is implemented by reducer.eval_target and performs no
source-language operations.

This module does not import compiler.py, so the target-reduction path
cannot invoke compilation.
"""

from __future__ import annotations

import os
import sys

_ASSIGN05_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "05")
if _ASSIGN05_DIR not in sys.path:
    sys.path.insert(0, _ASSIGN05_DIR)

from lambda1_vp import (
    D0Eapp, D0Ebtf, D0Eif0, D0Eint, D0Elam, D0Elet, D0Eop1, D0Eop2,
    D0Epair, D0Epfst, D0Epsnd, D0Evar, D0Efix, D0ExpVisitor, d0exp,
    D0Vint, D0Vbtf, D0Vpair, D0Vlam, D0Vfix, d0val, d0env, d0env_search,
    ENVnil, ENVcns,
)
from reducer import EvalResult, eval_target as _reduce_target
from target_ast import Term

SUPPORTED_BINARY_OPS = frozenset(
    {"+", "-", "*", "<", "<=", ">", ">=", "==", "!=", "and", "or"}
)
SUPPORTED_UNARY_OPS = frozenset({"not"})


class SourceEvalError(Exception):
    """Raised for an ill-formed source program at evaluation time."""


class _SourceEvalVisitor(D0ExpVisitor[d0val]):
    """Left-to-right call-by-value evaluator for the extended source
    language, implementing the semantics in Assign06 Section
    "Evaluation strategy" (boolean if0, short-circuit and/or, truncated
    subtraction). Not a step-bounded evaluator; used only for terminating
    source-side examples and as the oracle for expected answers."""

    def __init__(self, denv: d0env = ENVnil()) -> None:
        self.denv = denv

    def visit_int(self, dexp: D0Eint) -> d0val:
        if dexp.arg1 < 0:
            raise SourceEvalError(f"negative literal not supported: {dexp.arg1}")
        return D0Vint(dexp.arg1)

    def visit_btf(self, dexp: D0Ebtf) -> d0val:
        return D0Vbtf(dexp.arg1)

    def visit_var(self, dexp: D0Evar) -> d0val:
        value = d0env_search(self.denv, dexp.arg1)
        if not isinstance(value, (D0Vint, D0Vbtf, D0Vpair, D0Vlam, D0Vfix)):
            raise SourceEvalError(f"unbound variable: {dexp.arg1}")
        return value

    def visit_lam(self, dexp: D0Elam) -> d0val:
        return D0Vlam(self.denv, dexp)

    def visit_fix(self, dexp: D0Efix) -> d0val:
        return D0Vfix(self.denv, dexp)

    def visit_app(self, dexp: D0Eapp) -> d0val:
        dfun = dexp.arg1.accept(self)
        darg = dexp.arg2.accept(self)
        if isinstance(dfun, D0Vlam):
            dlam = dfun.arg2
            denv = ENVcns(dlam.arg1, darg, dfun.arg1)
            return dlam.arg2.accept(_SourceEvalVisitor(denv))
        if isinstance(dfun, D0Vfix):
            dfix = dfun.arg2
            denv = ENVcns(dfix.arg1, dfun, dfun.arg1)
            denv = ENVcns(dfix.arg2, darg, denv)
            return dfix.arg3.accept(_SourceEvalVisitor(denv))
        raise SourceEvalError(f"applying a non-function value: {dfun}")

    def visit_if0(self, dexp: D0Eif0) -> d0val:
        cond = dexp.arg1.accept(self)
        if not isinstance(cond, D0Vbtf):
            raise SourceEvalError(f"boolean expected in conditional: {cond}")
        return (dexp.arg2 if cond.arg1 else dexp.arg3).accept(self)

    def visit_let(self, dexp: D0Elet) -> d0val:
        value = dexp.arg2.accept(self)
        denv = ENVcns(dexp.arg1, value, self.denv)
        return dexp.arg3.accept(_SourceEvalVisitor(denv))

    def visit_pair(self, dexp: D0Epair) -> d0val:
        first = dexp.arg1.accept(self)
        second = dexp.arg2.accept(self)
        return D0Vpair(first, second)

    def visit_pfst(self, dexp: D0Epfst) -> d0val:
        pair = dexp.arg1.accept(self)
        if not isinstance(pair, D0Vpair):
            raise SourceEvalError(f"pair expected: {pair}")
        return pair.arg1

    def visit_psnd(self, dexp: D0Epsnd) -> d0val:
        pair = dexp.arg1.accept(self)
        if not isinstance(pair, D0Vpair):
            raise SourceEvalError(f"pair expected: {pair}")
        return pair.arg2

    def visit_op1(self, dexp: D0Eop1) -> d0val:
        if dexp.name not in SUPPORTED_UNARY_OPS:
            raise SourceEvalError(f"unsupported unary operator: {dexp.name!r}")
        value = dexp.arg1.accept(self)
        if not isinstance(value, D0Vbtf):
            raise SourceEvalError(f"boolean expected for 'not': {value}")
        return D0Vbtf(not value.arg1)

    def visit_op2(self, dexp: D0Eop2) -> d0val:
        name = dexp.name
        if name not in SUPPORTED_BINARY_OPS:
            raise SourceEvalError(f"unsupported binary operator: {name!r}")
        if name == "and":
            left = dexp.arg1.accept(self)
            if not isinstance(left, D0Vbtf):
                raise SourceEvalError(f"boolean expected: {left}")
            if not left.arg1:
                return D0Vbtf(False)
            right = dexp.arg2.accept(self)
            if not isinstance(right, D0Vbtf):
                raise SourceEvalError(f"boolean expected: {right}")
            return D0Vbtf(right.arg1)
        if name == "or":
            left = dexp.arg1.accept(self)
            if not isinstance(left, D0Vbtf):
                raise SourceEvalError(f"boolean expected: {left}")
            if left.arg1:
                return D0Vbtf(True)
            right = dexp.arg2.accept(self)
            if not isinstance(right, D0Vbtf):
                raise SourceEvalError(f"boolean expected: {right}")
            return D0Vbtf(right.arg1)

        left = dexp.arg1.accept(self)
        right = dexp.arg2.accept(self)
        if not isinstance(left, D0Vint) or not isinstance(right, D0Vint):
            raise SourceEvalError(f"naturals expected for {name!r}: {left}, {right}")
        match name:
            case "+":
                return D0Vint(left.arg1 + right.arg1)
            case "-":
                return D0Vint(max(left.arg1 - right.arg1, 0))
            case "*":
                return D0Vint(left.arg1 * right.arg1)
            case "<":
                return D0Vbtf(left.arg1 < right.arg1)
            case "<=":
                return D0Vbtf(left.arg1 <= right.arg1)
            case ">":
                return D0Vbtf(left.arg1 > right.arg1)
            case ">=":
                return D0Vbtf(left.arg1 >= right.arg1)
            case "==":
                return D0Vbtf(left.arg1 == right.arg1)
            case "!=":
                return D0Vbtf(left.arg1 != right.arg1)
        raise SourceEvalError(f"unreachable operator: {name!r}")


def evaluate_source(expr: d0exp, denv: d0env = ENVnil()) -> d0val:
    """Evaluate a source AST under the extended-LAMBDA semantics. Not step
    bounded; intended for terminating examples used as the expected-result
    oracle."""
    return expr.accept(_SourceEvalVisitor(denv))


def evaluate_target(term: Term, budget: int) -> EvalResult:
    """Evaluate a pure target term for at most `budget` beta-value steps.
    Operates exclusively on target syntax (Var/Lam/App); performs no
    source-language operations. See reducer.eval_target."""
    return _reduce_target(term, budget)
