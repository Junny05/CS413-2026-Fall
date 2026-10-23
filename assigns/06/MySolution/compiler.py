"""Compositional compiler from extended LAMBDA source ASTs to pure terms.

Translation rules (C[e] denotes the compiled target term):

    C[x]                  = x
    C[n]                  = NUM(n)                      (n >= 0 only)
    C[true]               = TRUE
    C[false]              = FALSE
    C[lam x. e]            = lam x. C[e]
    C[e1 e2]               = C[e1] C[e2]
    C[not e]                = NOT C[e]
    C[e1 op e2]             = OP C[e1] C[e2]             (op in +,-,*,<,<=,>,>=,==,!=)
    C[e1 and e2]            = (C[e1] (lam u. C[e2]) (lam v. FALSE)) I
    C[e1 or e2]             = (C[e1] (lam u. TRUE) (lam v. C[e2])) I
    C[if c then t else f]  = (C[c] (lam u. C[t]) (lam v. C[f])) I
    C[let x = e1 in e2]    = (lam x. C[e2]) C[e1]
    C[pair e1 e2]           = PAIR C[e1] C[e2]
    C[fst e]                = FST C[e]
    C[snd e]                = SND C[e]
    C[fix f(x). e]          = Z (lam f. lam x. C[e])

Here I, NOT, PAIR, FST, SND, Z, and each binary-operator combinator are the
closed library terms from encodings.py, already expressed purely in
Var/Lam/App. u and v are thunk parameters, unused in their bodies, chosen
fresh against the free variables of the branch they guard so that they can
never capture a same-named free variable of that branch.

Compilation never calls the shared evaluator (reducer.eval_target /
evaluator.evaluate_source); it only builds target ASTs structurally and
compositionally, so even a divergent source program compiles.
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
    d0exp_fvset,
)
from target_ast import App, Lam, Term, Var, FreshNamer, free_vars
from church_encodings import (
    BINARY_NAT_COMBINATORS, FALSE, FST, I_COMBINATOR, NOT, NUM, PAIR, SND,
    TRUE, Z_COMBINATOR,
)

SUPPORTED_OP2 = frozenset(BINARY_NAT_COMBINATORS) | frozenset({"and", "or"})
SUPPORTED_OP1 = frozenset({"not"})


class CompileError(Exception):
    """Raised for an unsupported literal or operator found anywhere in the
    source AST, including inside unselected branches or unapplied bodies."""


class _CompileVisitor(D0ExpVisitor[Term]):
    def __init__(self, namer: FreshNamer) -> None:
        self.namer = namer

    def visit_int(self, dexp: D0Eint) -> Term:
        if dexp.arg1 < 0:
            raise CompileError(f"negative literal not supported: {dexp.arg1}")
        return NUM(dexp.arg1)

    def visit_btf(self, dexp: D0Ebtf) -> Term:
        return TRUE if dexp.arg1 else FALSE

    def visit_var(self, dexp: D0Evar) -> Term:
        return Var(dexp.arg1)

    def visit_lam(self, dexp: D0Elam) -> Term:
        return Lam(dexp.arg1, dexp.arg2.accept(self))

    def visit_app(self, dexp: D0Eapp) -> Term:
        return App(dexp.arg1.accept(self), dexp.arg2.accept(self))

    def visit_op1(self, dexp: D0Eop1) -> Term:
        if dexp.name not in SUPPORTED_OP1:
            raise CompileError(f"unsupported unary operator: {dexp.name!r}")
        return App(NOT, dexp.arg1.accept(self))

    def visit_op2(self, dexp: D0Eop2) -> Term:
        if dexp.name not in SUPPORTED_OP2:
            raise CompileError(f"unsupported binary operator: {dexp.name!r}")
        c1 = dexp.arg1.accept(self)
        c2 = dexp.arg2.accept(self)
        if dexp.name == "and":
            return self._delayed_choice(c1, c2, FALSE)
        if dexp.name == "or":
            return self._delayed_choice(c1, TRUE, c2)
        combinator = BINARY_NAT_COMBINATORS[dexp.name]
        return App(App(combinator, c1), c2)

    def visit_if0(self, dexp: D0Eif0) -> Term:
        c = dexp.arg1.accept(self)
        t = dexp.arg2.accept(self)
        f = dexp.arg3.accept(self)
        return self._delayed_choice(c, t, f)

    def visit_let(self, dexp: D0Elet) -> Term:
        init = dexp.arg2.accept(self)
        body = dexp.arg3.accept(self)
        return App(Lam(dexp.arg1, body), init)

    def visit_pair(self, dexp: D0Epair) -> Term:
        return App(App(PAIR, dexp.arg1.accept(self)), dexp.arg2.accept(self))

    def visit_pfst(self, dexp: D0Epfst) -> Term:
        return App(FST, dexp.arg1.accept(self))

    def visit_psnd(self, dexp: D0Epsnd) -> Term:
        return App(SND, dexp.arg1.accept(self))

    def visit_fix(self, dexp: D0Efix) -> Term:
        body = dexp.arg3.accept(self)
        return App(Z_COMBINATOR, Lam(dexp.arg1, Lam(dexp.arg2, body)))

    def _delayed_choice(self, cond: Term, true_branch: Term, false_branch: Term) -> Term:
        """(cond (lam u. true_branch) (lam v. false_branch)) I

        u, v are fresh against the free variables of the branch each one
        guards, so wrapping that branch in "lam u. ..." (or "lam v. ...")
        can never capture a free variable of that branch that happens to
        share the thunk parameter's name.
        """
        u = self.namer.fresh(free_vars(true_branch), prefix="_u")
        v = self.namer.fresh(free_vars(false_branch), prefix="_v")
        return App(
            App(App(cond, Lam(u, true_branch)), Lam(v, false_branch)),
            I_COMBINATOR,
        )


def compile_expr(source_expression: d0exp) -> Term:
    """Compile a source AST into a pure target term.

    Compositional: every translation rule combines the translations of its
    subexpressions. Raises CompileError for a negative literal or an
    unsupported operator anywhere in the tree, including unselected
    branches and unapplied function bodies, since the traversal visits
    every subexpression regardless of which branch would execute. Does not
    invoke the shared evaluator and does not mutate source_expression.
    """
    namer = FreshNamer()
    visitor = _CompileVisitor(namer)
    return source_expression.accept(visitor)
