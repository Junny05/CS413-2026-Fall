"""Translate the ATS2 eight-queens solver into a LAMBDA0 lambda-term.

The original program is ``sourcecode.dats`` (copied into this directory
unchanged), taken from the Assignment 1 solution. Its algorithm and all of
its helper functions -- ``board_get``, ``board_set``, ``safety_test1``,
``safety_test2``, and ``search`` -- are re-expressed below as closed
``t0erm`` values built from ``T0Mlam``, ``T0Mapp``, ``T0Mfix``, and the pair
constructs ``T0Mpair``/``T0Mpfst``/``T0Mpsnd``. The resulting term is
evaluated by the extended ``t0erm_cbv_evaluate0`` -- the search itself runs
inside the interpreter, not in the surrounding Python.

No new interpreter primitives were needed: ``T0Mop2`` already supports the
integer comparisons (``<``, ``>``, ``<=``, ``>=``, ``==``, ``!=``) that the
translation requires.

Run with: python3 MySolution/queens_lambda0.py
"""

import itertools
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lambda0 import (
    T0Mint, T0Mbtf, T0Mvar, T0Mlam, T0Mfix, T0Mapp, T0Mif0, T0Mop1, T0Mop2,
    T0Mpair, T0Mpfst, T0Mpsnd,
    t0erm_size, t0erm_cbv_evaluate0,
)

########################################################################
# Small AST-building helpers (not part of the interpreter; these just
# assemble t0erm values in Python, the way the CHURCH_* combinators in
# TEST/test01_lambda0.py are assembled).
########################################################################

_fresh_counter = itertools.count()


def fresh(prefix: str) -> str:
    """A variable name that cannot collide with any other name this
    module generates, so nested LET/ABS calls never capture each other."""
    return f"__{prefix}{next(_fresh_counter)}"


def LET(value, body_fn):
    """let x = value in body_fn(x) end.

    Encoded as ((lambda x. body_fn(x)) value); call-by-value evaluates
    [value] exactly once, before body_fn's term runs, matching ATS2's
    strict `val` bindings.
    """
    x = fresh("let")
    return T0Mapp(T0Mlam(x, body_fn(T0Mvar(x))), value)


def AND(a, b):
    """Short-circuit `andalso`: only evaluate b when a is true."""
    return T0Mif0(a, b, T0Mbtf(False))


def ABS(e):
    """Absolute value, matching ATS2's `abs`. Binds e via LET so an
    expression with side effects (e.g. division) is evaluated once."""
    return LET(e, lambda x: T0Mif0(T0Mop2("<", x, T0Mint(0)), T0Mop1("-", x), x))


def APP(fn, *args):
    """Chain of applications: fn(a1)(a2)...(an), for curried functions."""
    term = fn
    for a in args:
        term = T0Mapp(term, a)
    return term


########################################################################
# Board representation.
#
# ATS2 represents the board as an [int8] tuple (8 ints, one column index
# per row). LAMBDA0 has no native tuple, so a board of size N is
# represented as a right-nested chain of N pairs:
#
#   (b0, (b1, (b2, ... (b_{N-1}, NIL) ...)))
#
# built with T0Mpair, i.e. a cons-list. NIL is a sentinel (T0Mint(-1))
# that also stands in for "no such row" -- the same -1 that ATS2's
# board_get returns for an out-of-range index.
########################################################################

NIL = T0Mint(-1)


def cons(head, tail):
    return T0Mpair(head, tail)


def board_literal(values):
    """Build a board term from a Python list of ints (front = row 0)."""
    term = NIL
    for v in reversed(values):
        term = cons(T0Mint(v), term)
    return term


def board_to_python(term):
    """Read back an evaluated board term as a Python tuple, for tests."""
    values = []
    while isinstance(term, T0Mpair):
        head = term.arg1
        if not isinstance(head, T0Mint):
            raise TypeError(f"board_to_python: expected an int row, got {head}")
        values.append(head.arg1)
        term = term.arg2
    return tuple(values)


########################################################################
# The translation, parameterized by board size N so smaller boards can
# be exercised in tests as well as the full 8x8 case.
########################################################################

def build_board_get(n):
    """board_get(bd, i): the column stored at row i, or -1 if i is out
    of [0, n). Mirrors the if-i=0-then-bd.0-else-if... chain in ATS2 by
    walking the pair chain instead, which generalizes to any n."""
    lst = T0Mvar("lst")
    i = T0Mvar("i")
    rec = T0Mvar("board_get")
    body = T0Mif0(
        T0Mop2("<", i, T0Mint(0)),
        T0Mint(-1),
        T0Mif0(
            T0Mop2(">=", i, T0Mint(n)),
            T0Mint(-1),
            T0Mif0(
                T0Mop2("==", i, T0Mint(0)),
                T0Mpfst(lst),
                APP(rec, T0Mpsnd(lst), T0Mop2("-", i, T0Mint(1))),
            ),
        ),
    )
    return T0Mfix("board_get", "lst", T0Mlam("i", body))


def build_board_set(n):
    """board_set(bd, i, j): a new board with row i set to column j, or
    the board unchanged if i is out of [0, n)."""
    lst = T0Mvar("lst")
    i = T0Mvar("i")
    j = T0Mvar("j")
    rec = T0Mvar("board_set")
    body = T0Mif0(
        T0Mop2("<", i, T0Mint(0)),
        lst,
        T0Mif0(
            T0Mop2(">=", i, T0Mint(n)),
            lst,
            T0Mif0(
                T0Mop2("==", i, T0Mint(0)),
                T0Mpair(j, T0Mpsnd(lst)),
                T0Mpair(T0Mpfst(lst), APP(rec, T0Mpsnd(lst), T0Mop2("-", i, T0Mint(1)), j)),
            ),
        ),
    )
    return T0Mfix("board_set", "lst", T0Mlam("i", T0Mlam("j", body)))


def build_safety_test1():
    """safety_test1(i0, j0, i1, j1): the two queens at (i0,j0)/(i1,j1)
    do not share a column or a diagonal. Not recursive, so a plain
    (non-fix) curried lambda, like ATS2's non-recursive `fun`."""
    i0, j0, i1, j1 = T0Mvar("i0"), T0Mvar("j0"), T0Mvar("i1"), T0Mvar("j1")
    body = AND(
        T0Mop2("!=", j0, j1),
        T0Mop2("!=", ABS(T0Mop2("-", i0, i1)), ABS(T0Mop2("-", j0, j1))),
    )
    return T0Mlam("i0", T0Mlam("j0", T0Mlam("i1", T0Mlam("j1", body))))


def build_safety_test2(safety_test1, board_get):
    """safety_test2(i0, j0, bd, i): the queen at (i0,j0) is safe against
    every existing queen in rows 0..i. i0, j0, and bd do not change
    across the recursive walk, so they are threaded through unchanged
    exactly as in ATS2's `safety_test2 (i0, j0, bd, i-1)`."""
    i0, j0, bd, i = T0Mvar("i0"), T0Mvar("j0"), T0Mvar("bd"), T0Mvar("i")
    rec = T0Mvar("safety_test2")
    body = T0Mif0(
        T0Mop2(">=", i, T0Mint(0)),
        T0Mif0(
            APP(safety_test1, i0, j0, i, APP(board_get, bd, i)),
            APP(rec, i0, j0, bd, T0Mop2("-", i, T0Mint(1))),
            T0Mbtf(False),
        ),
        T0Mbtf(True),
    )
    return T0Mfix("safety_test2", "i0", T0Mlam("j0", T0Mlam("bd", T0Mlam("i", body))))


def build_search(n, safety_test2, board_get, board_set):
    """search(bd, i, j, nsol): try column j at row i onward, counting and
    collecting completed solutions. A literal translation of ATS2's
    `search`, including its control-flow quirk: once row i is the last
    row (i+1 = n), the next candidate at that row is tried against the
    *original* bd (not bd1).

    The one change is output. ATS2 prints each solution bd1 and finally
    returns nsol; LAMBDA0 has no I/O, so this search returns the pair
    (nsol, sols), where sols is a NIL-terminated pair chain of the
    solution boards in the order ATS2 prints them. On a solution,

        let r = search(bd, i, j+1, nsol+1) in (pfst r, cons(bd1, psnd r))

    replaces `print_board(bd1); search(bd, i, j+1, nsol+1)`. Building
    the list on the way out, rather than threading an accumulator
    through every call, matters under this substitution-based
    interpreter: an accumulator would be substituted into, and
    re-evaluated by, every one of the ~17,700 search steps (about 4x
    slower in practice), whereas this touches the list only once per
    solution.
    """
    bd, i, j, nsol = T0Mvar("bd"), T0Mvar("i"), T0Mvar("j"), T0Mvar("nsol")
    rec = T0Mvar("search")

    def recurse(bd_, i_, j_, nsol_):
        return APP(rec, bd_, i_, j_, nsol_)

    body = T0Mif0(
        T0Mop2("<", j, T0Mint(n)),
        LET(
            APP(safety_test2, i, j, bd, T0Mop2("-", i, T0Mint(1))),
            lambda test: T0Mif0(
                test,
                LET(
                    APP(board_set, bd, i, j),
                    lambda bd1: T0Mif0(
                        T0Mop2("==", T0Mop2("+", i, T0Mint(1)), T0Mint(n)),
                        # ATS2: print bd1 as "Solution #nsol+1", then continue.
                        LET(
                            recurse(bd, i, T0Mop2("+", j, T0Mint(1)), T0Mop2("+", nsol, T0Mint(1))),
                            lambda r: T0Mpair(T0Mpfst(r), cons(bd1, T0Mpsnd(r))),
                        ),
                        recurse(bd1, T0Mop2("+", i, T0Mint(1)), T0Mint(0), nsol),
                    ),
                ),
                recurse(bd, i, T0Mop2("+", j, T0Mint(1)), nsol),
            ),
        ),
        T0Mif0(
            T0Mop2(">", i, T0Mint(0)),
            recurse(
                bd,
                T0Mop2("-", i, T0Mint(1)),
                T0Mop2("+", APP(board_get, bd, T0Mop2("-", i, T0Mint(1))), T0Mint(1)),
                nsol,
            ),
            T0Mpair(nsol, NIL),
        ),
    )
    return T0Mfix("search", "bd", T0Mlam("i", T0Mlam("j", T0Mlam("nsol", body))))


def run_with_deep_recursion(term, recursion_limit=200_000, stack_size=512 * 1024 * 1024):
    """Evaluate a t0erm on a thread with a raised recursion limit and a
    larger C stack.

    ATS2's `search` is written as a tail call (`search (bd1, i+1, 0,
    nsol)`, etc.), which ATS2 compiles into a loop. `t0erm_cbv_evaluate0`
    has no such tail-call optimization: evaluating one `search` step
    means a real, non-tail Python call to `t0erm_cbv_evaluate0` (through
    substitution and the surrounding T0Mif0/T0Mapp cases) for every
    step. The 8-queens search takes about 17,700 such steps, each several
    interpreter frames deep, which overflows Python's default recursion
    limit (RecursionError) well before N reaches 8. Rather than restructure
    the interpreter, this raises the limit and runs on a thread with a
    correspondingly larger stack -- the interpreter and the translated
    term are unchanged.
    """
    result = {}

    def target():
        old_limit = sys.getrecursionlimit()
        sys.setrecursionlimit(recursion_limit)
        try:
            result["value"] = t0erm_cbv_evaluate0(term)
        except BaseException as exc:  # re-raise on the calling thread
            result["error"] = exc
        finally:
            sys.setrecursionlimit(old_limit)

    threading.stack_size(stack_size)
    thread = threading.Thread(target=target)
    thread.start()
    thread.join()
    if "error" in result:
        raise result["error"]
    return result["value"]


class QueensLambda0:
    """All the translated pieces for a board of size n, plus the fully
    applied `search` term ready to hand to t0erm_cbv_evaluate0."""

    def __init__(self, n):
        self.n = n
        self.board_get = build_board_get(n)
        self.board_set = build_board_set(n)
        self.safety_test1 = build_safety_test1()
        self.safety_test2 = build_safety_test2(self.safety_test1, self.board_get)
        self.search = build_search(n, self.safety_test2, self.board_get, self.board_set)
        self.board0 = board_literal([0] * n)
        self.term = APP(self.search, self.board0, T0Mint(0), T0Mint(0), T0Mint(0))

    def run(self):
        """Evaluate the term; returns the LAMBDA0 value T0Mpair(nsol, sols)."""
        return run_with_deep_recursion(self.term)


def result_count(result):
    """The solution count from an evaluated search result (nsol, sols)."""
    if not (isinstance(result, T0Mpair) and isinstance(result.arg1, T0Mint)):
        raise TypeError(f"result_count: expected (nsol, sols), got {result}")
    return result.arg1.arg1


def result_boards(result):
    """The solution boards from an evaluated search result, as Python
    tuples, in the order ATS2 prints them."""
    boards = []
    sols = result.arg2
    while isinstance(sols, T0Mpair):
        boards.append(board_to_python(sols.arg1))
        sols = sols.arg2
    return boards


def format_board(board):
    """Render a board the way ATS2's print_board does."""
    n = len(board)
    return "".join(". " * c + "Q " + ". " * (n - c - 1) + "\n" for c in board)


def build_queens(n=8):
    return QueensLambda0(n)


if __name__ == "__main__":
    queens = build_queens(8)
    print(f"t0erm_size(search term) = {t0erm_size(queens.term)}")
    result = queens.run()
    for k, board in enumerate(result_boards(result), 1):
        print(f"Solution #{k}:\n")
        print(format_board(board))
    print(f"Number of solutions to {queens.n}-queens: {result_count(result)}")
