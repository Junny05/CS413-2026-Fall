"""Target AST for pure, untyped lambda-calculus terms.

Term ::= Var(name) | Lam(param, body) | App(fn, arg)

This module provides the three term constructors, a printer, free-variable
analysis, and capture-avoiding substitution with a deterministic fresh-name
policy. It has no dependency on the source AST or the compiler.
"""

from __future__ import annotations

from dataclasses import dataclass

IDENT_RE_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_"


@dataclass(frozen=True)
class Term:
    """Abstract base of the three target forms."""


@dataclass(frozen=True)
class Var(Term):
    name: str


@dataclass(frozen=True)
class Lam(Term):
    param: str
    body: Term


@dataclass(frozen=True)
class App(Term):
    fn: Term
    arg: Term


def print_term(t: Term) -> str:
    """Render t using 'x', '(lam x. body)', '(fn arg)'."""
    if isinstance(t, Var):
        return t.name
    if isinstance(t, Lam):
        return f"(lam {t.param}. {print_term(t.body)})"
    if isinstance(t, App):
        return f"({print_term(t.fn)} {print_term(t.arg)})"
    raise TypeError(f"not a Term: {t!r}")


def free_vars(t: Term) -> frozenset[str]:
    """Return the set of free variable names occurring in t."""
    if isinstance(t, Var):
        return frozenset({t.name})
    if isinstance(t, Lam):
        return free_vars(t.body) - {t.param}
    if isinstance(t, App):
        return free_vars(t.fn) | free_vars(t.arg)
    raise TypeError(f"not a Term: {t!r}")


def is_closed(t: Term) -> bool:
    return len(free_vars(t)) == 0


class FreshNamer:
    """Deterministic, monotonic fresh-name generator.

    Each call to fresh() advances a single global counter and returns the
    first candidate "<prefix><n>" not contained in the caller-supplied
    avoid set. The counter never resets within a FreshNamer instance, so
    two calls never return the same name, and the result for a given
    sequence of (prefix, avoid) arguments is always the same. No ordinary
    source identifier is reserved: any name is only skipped if it actually
    appears in the supplied avoid set.
    """

    def __init__(self) -> None:
        self._counter = 0

    def fresh(self, avoid: frozenset[str], prefix: str = "_g") -> str:
        while True:
            candidate = f"{prefix}{self._counter}"
            self._counter += 1
            if candidate not in avoid:
                return candidate


def substitute(t: Term, name: str, replacement: Term) -> Term:
    """Return t[name := replacement], capture-avoiding. Does not mutate t."""
    if isinstance(t, Var):
        return replacement if t.name == name else t
    if isinstance(t, App):
        return App(substitute(t.fn, name, replacement), substitute(t.arg, name, replacement))
    if isinstance(t, Lam):
        if t.param == name:
            return t
        if t.param not in free_vars(replacement):
            return Lam(t.param, substitute(t.body, name, replacement))
        namer = _RENAME_NAMER
        avoid = free_vars(replacement) | free_vars(t.body) | {name, t.param}
        fresh_param = namer.fresh(avoid, prefix="_s")
        renamed_body = substitute(t.body, t.param, Var(fresh_param))
        return Lam(fresh_param, substitute(renamed_body, name, replacement))
    raise TypeError(f"not a Term: {t!r}")


# Dedicated namer used only for capture-avoidance renames performed inside
# substitute(). Kept separate from compiler-introduced binder names.
_RENAME_NAMER = FreshNamer()


def alpha_equivalent(t1: Term, t2: Term, env1: dict[str, int] | None = None,
                      env2: dict[str, int] | None = None, depth: int = 0) -> bool:
    """Structural equality up to consistent renaming of bound variables."""
    env1 = {} if env1 is None else env1
    env2 = {} if env2 is None else env2
    if isinstance(t1, Var) and isinstance(t2, Var):
        b1 = env1.get(t1.name)
        b2 = env2.get(t2.name)
        if b1 is None and b2 is None:
            return t1.name == t2.name
        return b1 == b2
    if isinstance(t1, Lam) and isinstance(t2, Lam):
        e1 = dict(env1)
        e2 = dict(env2)
        e1[t1.param] = depth
        e2[t2.param] = depth
        return alpha_equivalent(t1.body, t2.body, e1, e2, depth + 1)
    if isinstance(t1, App) and isinstance(t2, App):
        return (alpha_equivalent(t1.fn, t2.fn, env1, env2, depth)
                and alpha_equivalent(t1.arg, t2.arg, env1, env2, depth))
    return False
