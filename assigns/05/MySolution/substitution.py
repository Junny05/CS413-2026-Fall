"""Capture-avoiding substitution visitor for the LAMBDA AST (Assignment 5, Task 2).

Fresh-name policy
------------------
Fresh names are generated deterministically as ``f"{base}_{n}"`` for the
smallest positive integer ``n`` such that the resulting name is not in a
shared "avoid" set. That set is seeded, before any renaming happens, with
every variable and binder name that occurs anywhere in the original
expression, every name occurring in the replacement expression, and the
substitution target itself. Every name generated during a single top-level
call to ``d0exp_substitute`` is also added to the same set immediately, so
later renamings (including nested ones) never collide with earlier ones.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lambda1_vp import (  # noqa: E402
    D0ExpVisitor,
    D0Eint,
    D0Ebtf,
    D0Eop1,
    D0Eop2,
    D0Evar,
    D0Elam,
    D0Efix,
    D0Eapp,
    D0Eif0,
    D0Elet,
    D0Epair,
    D0Epfst,
    D0Epsnd,
    d0exp,
    dvar,
    d0exp_fvset,
)


class NameCollectorVisitor(D0ExpVisitor[frozenset[dvar]]):
    """Collect every variable/binder name occurring anywhere in an expression."""

    def visit_int(self, dexp: D0Eint) -> frozenset[dvar]:
        return frozenset()

    def visit_btf(self, dexp: D0Ebtf) -> frozenset[dvar]:
        return frozenset()

    def visit_var(self, dexp: D0Evar) -> frozenset[dvar]:
        return frozenset({dexp.arg1})

    def visit_lam(self, dexp: D0Elam) -> frozenset[dvar]:
        return dexp.arg2.accept(self) | {dexp.arg1}

    def visit_fix(self, dexp: D0Efix) -> frozenset[dvar]:
        return dexp.arg3.accept(self) | {dexp.arg1, dexp.arg2}

    def visit_let(self, dexp: D0Elet) -> frozenset[dvar]:
        return dexp.arg2.accept(self) | dexp.arg3.accept(self) | {dexp.arg1}

    def visit_if0(self, dexp: D0Eif0) -> frozenset[dvar]:
        return (dexp.arg1.accept(self) | dexp.arg2.accept(self)
                | dexp.arg3.accept(self))

    def visit_op1(self, dexp: D0Eop1) -> frozenset[dvar]:
        return dexp.arg1.accept(self)

    def visit_op2(self, dexp: D0Eop2) -> frozenset[dvar]:
        return dexp.arg1.accept(self) | dexp.arg2.accept(self)

    def visit_app(self, dexp: D0Eapp) -> frozenset[dvar]:
        return dexp.arg1.accept(self) | dexp.arg2.accept(self)

    def visit_pair(self, dexp: D0Epair) -> frozenset[dvar]:
        return dexp.arg1.accept(self) | dexp.arg2.accept(self)

    def visit_pfst(self, dexp: D0Epfst) -> frozenset[dvar]:
        return dexp.arg1.accept(self)

    def visit_psnd(self, dexp: D0Epsnd) -> frozenset[dvar]:
        return dexp.arg1.accept(self)


def d0exp_names(dexp: d0exp) -> frozenset[dvar]:
    """Return every variable and binder name occurring anywhere in dexp."""
    return dexp.accept(NameCollectorVisitor())


def fresh_name(base: dvar, avoid: set[dvar]) -> dvar:
    """Return ``base_n`` for the smallest n>=1 not in avoid, and reserve it."""
    counter = 1
    candidate = f"{base}_{counter}"
    while candidate in avoid:
        counter += 1
        candidate = f"{base}_{counter}"
    avoid.add(candidate)
    return candidate


class SubstitutionVisitor(D0ExpVisitor[d0exp]):
    """Compute e[target := replacement], renaming binders to avoid capture.

    ``avoid`` is a mutable set, shared across the whole top-level call
    (including any nested renaming sub-visitors), used to pick fresh names
    that cannot collide with anything already present or already generated.
    """

    def __init__(self, target: dvar, replacement: d0exp, avoid: set[dvar]) -> None:
        self.target = target
        self.replacement = replacement
        self.avoid = avoid

    def _rename(self, old: dvar, new: dvar, body: d0exp) -> d0exp:
        """Replace bound occurrences of old with new (a fresh, hence safe, name)."""
        renamer = SubstitutionVisitor(old, D0Evar(new), self.avoid)
        return body.accept(renamer)

    def visit_int(self, dexp: D0Eint) -> d0exp:
        return D0Eint(dexp.arg1)

    def visit_btf(self, dexp: D0Ebtf) -> d0exp:
        return D0Ebtf(dexp.arg1)

    def visit_var(self, dexp: D0Evar) -> d0exp:
        return self.replacement if dexp.arg1 == self.target else D0Evar(dexp.arg1)

    def visit_op1(self, dexp: D0Eop1) -> d0exp:
        return D0Eop1(dexp.name, dexp.arg1.accept(self))

    def visit_op2(self, dexp: D0Eop2) -> d0exp:
        return D0Eop2(dexp.name, dexp.arg1.accept(self), dexp.arg2.accept(self))

    def visit_app(self, dexp: D0Eapp) -> d0exp:
        return D0Eapp(dexp.arg1.accept(self), dexp.arg2.accept(self))

    def visit_if0(self, dexp: D0Eif0) -> d0exp:
        return D0Eif0(dexp.arg1.accept(self), dexp.arg2.accept(self),
                      dexp.arg3.accept(self))

    def visit_pair(self, dexp: D0Epair) -> d0exp:
        return D0Epair(dexp.arg1.accept(self), dexp.arg2.accept(self))

    def visit_pfst(self, dexp: D0Epfst) -> d0exp:
        return D0Epfst(dexp.arg1.accept(self))

    def visit_psnd(self, dexp: D0Epsnd) -> d0exp:
        return D0Epsnd(dexp.arg1.accept(self))

    def visit_lam(self, dexp: D0Elam) -> d0exp:
        param, body = dexp.arg1, dexp.arg2
        if param == self.target:
            return D0Elam(param, body)
        if self.target not in d0exp_fvset(body):
            return D0Elam(param, body)
        if param not in d0exp_fvset(self.replacement):
            return D0Elam(param, body.accept(self))
        fresh = fresh_name(param, self.avoid)
        renamed_body = self._rename(param, fresh, body)
        return D0Elam(fresh, renamed_body.accept(self))

    def visit_let(self, dexp: D0Elet) -> d0exp:
        name, init, body = dexp.arg1, dexp.arg2, dexp.arg3
        new_init = init.accept(self)
        if name == self.target:
            return D0Elet(name, new_init, body)
        if self.target not in d0exp_fvset(body):
            return D0Elet(name, new_init, body)
        if name not in d0exp_fvset(self.replacement):
            return D0Elet(name, new_init, body.accept(self))
        fresh = fresh_name(name, self.avoid)
        renamed_body = self._rename(name, fresh, body)
        return D0Elet(fresh, new_init, renamed_body.accept(self))

    def visit_fix(self, dexp: D0Efix) -> d0exp:
        fname, param, body = dexp.arg1, dexp.arg2, dexp.arg3
        if self.target in (fname, param):
            return D0Efix(fname, param, body)
        if self.target not in d0exp_fvset(body):
            return D0Efix(fname, param, body)
        replacement_fv = d0exp_fvset(self.replacement)
        new_fname, new_param = fname, param
        new_body = body
        if fname == param:
            # A single shared binder (the parameter shadows the function
            # name); rename it once so both roles stay in sync.
            if fname in replacement_fv:
                fresh = fresh_name(fname, self.avoid)
                new_body = self._rename(fname, fresh, new_body)
                new_fname = new_param = fresh
        else:
            if fname in replacement_fv:
                new_fname = fresh_name(fname, self.avoid)
                new_body = self._rename(fname, new_fname, new_body)
            if param in replacement_fv:
                new_param = fresh_name(param, self.avoid)
                new_body = self._rename(param, new_param, new_body)
        return D0Efix(new_fname, new_param, new_body.accept(self))


def d0exp_substitute(dexp: d0exp, variable: dvar, replacement: d0exp) -> d0exp:
    """Return dexp[variable := replacement] without mutating either input."""
    avoid: set[dvar] = set(d0exp_names(dexp)) | set(d0exp_names(replacement))
    avoid.add(variable)
    visitor = SubstitutionVisitor(variable, replacement, avoid)
    return dexp.accept(visitor)
