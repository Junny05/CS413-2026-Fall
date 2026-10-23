"""Church-encoding library: closed target-AST combinators.

Every combinator defined here is a closed Term (no free variables) built
purely from Var/Lam/App. Names such as TRUE, PAIR, Z, ADD are Python
builder names / documentation abbreviations, not target-language
primitives; by construction they already are pure Var/Lam/App terms, so
no separate "expansion" step is needed when they are spliced into
compiler output.

Bound-variable names used inside these combinators (s, z, t, f, m, n, p,
a, b, g, x, v, w, c, ...) are purely local to each closed combinator and
never escape it, by ordinary lexical scoping -- so reusing common letters
here does not reserve them for compiler use and does not collide with any
source program's identifiers.
"""

from __future__ import annotations

from target_ast import App, Lam, Term, Var, free_vars


def _check_closed(name: str, t: Term) -> Term:
    fv = free_vars(t)
    if fv:
        raise AssertionError(f"library combinator {name} is not closed: {fv}")
    return t


# ---------------------------------------------------------------------------
# Booleans
# ---------------------------------------------------------------------------

TRUE = _check_closed("TRUE", Lam("t", Lam("f", Var("t"))))
FALSE = _check_closed("FALSE", Lam("t", Lam("f", Var("f"))))

# Closed dummy value used to force a selected thunk: I = lam w. w
I_COMBINATOR = _check_closed("I", Lam("w", Var("w")))

NOT = _check_closed("NOT", Lam("b", App(App(Var("b"), FALSE), TRUE)))


# ---------------------------------------------------------------------------
# Naturals
# ---------------------------------------------------------------------------

def NUM(n: int) -> Term:
    """lam s. lam z. s applied n times to z."""
    if n < 0:
        raise ValueError("NUM requires a nonnegative integer")
    body: Term = Var("z")
    for _ in range(n):
        body = App(Var("s"), body)
    return Lam("s", Lam("z", body))


ZERO = NUM(0)

# SUCC = lam n. lam s. lam z. s (n s z)
SUCC = _check_closed(
    "SUCC",
    Lam("n", Lam("s", Lam("z", App(Var("s"), App(App(Var("n"), Var("s")), Var("z")))))),
)

# PAIR = lam a. lam b. lam p. p a b
PAIR = _check_closed(
    "PAIR",
    Lam("a", Lam("b", Lam("p", App(App(Var("p"), Var("a")), Var("b"))))),
)
FST = _check_closed("FST", Lam("p", App(Var("p"), Lam("a", Lam("b", Var("a"))))))
SND = _check_closed("SND", Lam("p", App(Var("p"), Lam("a", Lam("b", Var("b"))))))


# PRED via the standard "shift and drop" pair trick:
#   PRED(n) = FST( n (lam q. PAIR (SND q) (SUCC (SND q))) (PAIR ZERO ZERO) )
# Starting from (0, 0) and, on each of n steps, replacing (prev, cur) with
# (cur, cur+1), after n steps the pair holds (n-1, n); its first component
# is n-1 for n >= 1, and remains 0 when n = 0 because the seed pair is
# (0, 0) and zero steps are taken. See DESIGN.md for the full explanation.
_PRED_STEP = Lam(
    "q",
    App(App(PAIR, App(SND, Var("q"))), App(SUCC, App(SND, Var("q")))),
)
PRED = _check_closed(
    "PRED",
    Lam(
        "n",
        App(
            FST,
            App(App(Var("n"), _PRED_STEP), App(App(PAIR, ZERO), ZERO)),
        ),
    ),
)

# ADD = lam m. lam n. lam s. lam z. m s (n s z)
ADD = _check_closed(
    "ADD",
    Lam(
        "m",
        Lam(
            "n",
            Lam(
                "s",
                Lam(
                    "z",
                    App(App(Var("m"), Var("s")), App(App(Var("n"), Var("s")), Var("z"))),
                ),
            ),
        ),
    ),
)

# MUL = lam m. lam n. lam s. lam z. m (n s) z
MUL = _check_closed(
    "MUL",
    Lam(
        "m",
        Lam(
            "n",
            Lam(
                "s",
                Lam("z", App(App(Var("m"), App(Var("n"), Var("s"))), Var("z"))),
            ),
        ),
    ),
)

# SUB(m, n) = n applications of PRED to m (truncated subtraction).
SUB = _check_closed(
    "SUB",
    Lam("m", Lam("n", App(App(Var("n"), PRED), Var("m")))),
)

# ISZERO = lam n. n (lam _. FALSE) TRUE
ISZERO = _check_closed(
    "ISZERO",
    Lam("n", App(App(Var("n"), Lam("_", FALSE)), TRUE)),
)

# LEQ(m, n) = ISZERO (SUB m n)
LEQ = _check_closed(
    "LEQ",
    Lam("m", Lam("n", App(ISZERO, App(App(SUB, Var("m")), Var("n"))))),
)

# LT(m, n) = NOT (LEQ n m)   i.e. m < n  iff  not (n <= m)
LT = _check_closed(
    "LT",
    Lam("m", Lam("n", App(NOT, App(App(LEQ, Var("n")), Var("m"))))),
)

# GT(m, n) = LT(n, m); GEQ(m, n) = LEQ(n, m)
GT = _check_closed("GT", Lam("m", Lam("n", App(App(LT, Var("n")), Var("m")))))
GEQ = _check_closed("GEQ", Lam("m", Lam("n", App(App(LEQ, Var("n")), Var("m")))))

# EQ(m, n) = LEQ(m, n) AND LEQ(n, m); eager AND is fine here since both
# operands are already-reduced Church boolean values.
_EAGER_AND = Lam("a", Lam("b", App(App(Var("a"), Var("b")), FALSE)))
_EAGER_OR = Lam("a", Lam("b", App(App(Var("a"), TRUE), Var("b"))))

EQ = _check_closed(
    "EQ",
    Lam(
        "m",
        Lam(
            "n",
            App(
                App(_EAGER_AND, App(App(LEQ, Var("m")), Var("n"))),
                App(App(LEQ, Var("n")), Var("m")),
            ),
        ),
    ),
)
NEQ = _check_closed("NEQ", Lam("m", Lam("n", App(NOT, App(App(EQ, Var("m")), Var("n"))))))


# ---------------------------------------------------------------------------
# Recursion: the call-by-value fixed-point combinator.
# Z = lam g. (lam x. g (lam v. x x v)) (lam x. g (lam v. x x v))
# ---------------------------------------------------------------------------

def _z_half() -> Term:
    return Lam("x", App(Var("g"), Lam("v", App(App(Var("x"), Var("x")), Var("v")))))


Z_COMBINATOR = _check_closed("Z", Lam("g", App(_z_half(), _z_half())))


BINARY_NAT_COMBINATORS: dict[str, Term] = {
    "+": ADD,
    "-": SUB,
    "*": MUL,
    "<": LT,
    "<=": LEQ,
    ">": GT,
    ">=": GEQ,
    "==": EQ,
    "!=": NEQ,
}
