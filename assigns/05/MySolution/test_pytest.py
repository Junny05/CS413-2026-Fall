"""pytest suite for Assignment 5.

Run from the assigns/05 directory with:
    python3 -m pytest MySolution/test_pytest.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lambda1_vp import (
    D0Eint, D0Ebtf, D0Eop1, D0Eop2, D0Evar, D0Elam, D0Efix, D0Eapp,
    D0Eif0, D0Elet, D0Epair, D0Epfst, D0Epsnd, d0exp_fvset,
)
from pretty_print import d0exp_pretty
from substitution import d0exp_substitute


# --- pretty printing: every constructor, nesting, ints, booleans -----------

def test_pp_int_positive():
    assert d0exp_pretty(D0Eint(4)) == "4"


def test_pp_int_negative():
    assert d0exp_pretty(D0Eint(-99)) == "-99"


def test_pp_int_large():
    assert d0exp_pretty(D0Eint(10**12)) == "1000000000000"


def test_pp_btf():
    assert d0exp_pretty(D0Ebtf(True)) == "true"
    assert d0exp_pretty(D0Ebtf(False)) == "false"


def test_pp_var():
    assert d0exp_pretty(D0Evar("abc_1")) == "abc_1"


def test_pp_op1():
    assert d0exp_pretty(D0Eop1("-1", D0Evar("x"))) == "(-1 x)"


def test_pp_op2():
    assert d0exp_pretty(D0Eop2("*", D0Eint(2), D0Eint(3))) == "(2 * 3)"


def test_pp_op2_division_by_zero_does_not_raise():
    assert d0exp_pretty(D0Eop2("/", D0Eint(1), D0Eint(0))) == "(1 / 0)"


def test_pp_lam():
    assert d0exp_pretty(D0Elam("x", D0Evar("x"))) == "(lam x. x)"


def test_pp_fix():
    expr = D0Efix("f", "x", D0Eapp(D0Evar("f"), D0Evar("x")))
    assert d0exp_pretty(expr) == "(fix f(x). (f x))"


def test_pp_app():
    assert d0exp_pretty(D0Eapp(D0Evar("f"), D0Eint(1))) == "(f 1)"


def test_pp_if0():
    expr = D0Eif0(D0Ebtf(False), D0Eint(1), D0Eint(2))
    assert d0exp_pretty(expr) == "(if false then 1 else 2)"


def test_pp_let():
    expr = D0Elet("x", D0Eint(1), D0Evar("x"))
    assert d0exp_pretty(expr) == "(let x = 1 in x)"


def test_pp_pair_fst_snd():
    pair = D0Epair(D0Eint(1), D0Eint(2))
    assert d0exp_pretty(pair) == "(pair 1 2)"
    assert d0exp_pretty(D0Epfst(pair)) == "(fst (pair 1 2))"
    assert d0exp_pretty(D0Epsnd(pair)) == "(snd (pair 1 2))"


def test_pp_spec_example():
    expr = D0Eapp(D0Elam("x", D0Eop2("+", D0Evar("x"), D0Eint(1))), D0Eint(4))
    assert d0exp_pretty(expr) == "((lam x. (x + 1)) 4)"


def test_pp_nested():
    expr = D0Elet("x", D0Eif0(D0Ebtf(True), D0Eint(1), D0Eint(2)),
                  D0Efix("f", "n", D0Eapp(D0Evar("f"), D0Evar("n"))))
    assert d0exp_pretty(expr) == (
        "(let x = (if true then 1 else 2) in (fix f(n). (f n)))")


# --- substitution: every constructor ---------------------------------------

def test_sub_int_and_btf_unaffected():
    assert d0exp_substitute(D0Eint(7), "x", D0Eint(0)) == D0Eint(7)
    assert d0exp_substitute(D0Ebtf(False), "x", D0Eint(0)) == D0Ebtf(False)


def test_sub_var_matching_and_nonmatching():
    assert d0exp_substitute(D0Evar("x"), "x", D0Eint(5)) == D0Eint(5)
    assert d0exp_substitute(D0Evar("y"), "x", D0Eint(5)) == D0Evar("y")


def test_sub_op1_op2():
    assert d0exp_substitute(D0Eop1("+1", D0Evar("x")), "x", D0Eint(5)) == \
        D0Eop1("+1", D0Eint(5))
    assert d0exp_substitute(
        D0Eop2("-", D0Evar("x"), D0Evar("x")), "x", D0Eint(5)) == \
        D0Eop2("-", D0Eint(5), D0Eint(5))


def test_sub_app_if0():
    assert d0exp_substitute(
        D0Eapp(D0Evar("x"), D0Evar("y")), "x", D0Eint(5)) == \
        D0Eapp(D0Eint(5), D0Evar("y"))
    assert d0exp_substitute(
        D0Eif0(D0Evar("x"), D0Eint(1), D0Eint(2)), "x", D0Ebtf(True)) == \
        D0Eif0(D0Ebtf(True), D0Eint(1), D0Eint(2))


def test_sub_pair_pfst_psnd():
    pair = D0Epair(D0Evar("x"), D0Evar("y"))
    assert d0exp_substitute(pair, "x", D0Eint(1)) == D0Epair(D0Eint(1), D0Evar("y"))
    assert d0exp_substitute(D0Epfst(pair), "y", D0Eint(2)) == \
        D0Epfst(D0Epair(D0Evar("x"), D0Eint(2)))
    assert d0exp_substitute(D0Epsnd(pair), "y", D0Eint(2)) == \
        D0Epsnd(D0Epair(D0Evar("x"), D0Eint(2)))


def test_sub_replacement_contains_target():
    result = d0exp_substitute(D0Evar("x"), "x", D0Eop2("+", D0Evar("x"), D0Eint(1)))
    assert result == D0Eop2("+", D0Evar("x"), D0Eint(1))


# --- shadowing ---------------------------------------------------------------

def test_shadow_lambda():
    expr = D0Elam("x", D0Eop2("+", D0Evar("x"), D0Evar("y")))
    assert d0exp_substitute(expr, "x", D0Eint(3)) == expr


def test_shadow_let():
    # the initializer references a free "x" from outside the let, which
    # must still be substituted even though the let shadows x in the body
    expr = D0Elet("x", D0Evar("x"), D0Evar("x"))
    result = d0exp_substitute(expr, "x", D0Eint(3))
    assert result.arg2 == D0Eint(3)   # initializer still substituted
    assert result.arg3 == D0Evar("x")  # body shadowed


def test_shadow_fix_function_name():
    expr = D0Efix("f", "n", D0Evar("f"))
    assert d0exp_substitute(expr, "f", D0Eint(3)) == expr


def test_shadow_fix_parameter():
    expr = D0Efix("f", "n", D0Evar("n"))
    assert d0exp_substitute(expr, "n", D0Eint(3)) == expr


def test_shadow_fix_shared_name():
    expr = D0Efix("f", "f", D0Evar("f"))
    assert d0exp_substitute(expr, "f", D0Eint(3)) == expr


# --- let initializer vs body -------------------------------------------------

def test_let_initializer_vs_body_distinction():
    expr = D0Elet("x", D0Evar("x"), D0Eop2("+", D0Evar("x"), D0Evar("y")))
    result = d0exp_substitute(expr, "x", D0Eint(3))
    assert result.arg1 == "x"
    assert result.arg2 == D0Eint(3)
    assert result.arg3 == D0Eop2("+", D0Evar("x"), D0Evar("y"))


# --- capture avoidance --------------------------------------------------------

def test_capture_avoidance_lambda():
    expr = D0Elam("y", D0Eop2("+", D0Evar("x"), D0Evar("y")))
    result = d0exp_substitute(expr, "x", D0Evar("y"))
    assert result.arg1 != "y"
    assert d0exp_pretty(result) == f"(lam {result.arg1}. (y + {result.arg1}))"


def test_capture_avoidance_let():
    expr = D0Elet("y", D0Evar("x"), D0Eop2("+", D0Evar("x"), D0Evar("y")))
    result = d0exp_substitute(expr, "x", D0Evar("y"))
    assert result.arg1 != "y"
    assert result.arg2 == D0Evar("y")
    assert d0exp_pretty(result.arg3) == f"(y + {result.arg1})"


def test_capture_avoidance_fix_both_binders():
    expr = D0Efix("f", "n", D0Eop2("+", D0Evar("x"), D0Eapp(D0Evar("f"), D0Evar("n"))))
    result = d0exp_substitute(
        expr, "x", D0Eop2("+", D0Evar("f"), D0Evar("n")))
    assert result.arg1 != "f"
    assert result.arg2 != "n"
    assert result.arg1 != result.arg2
    assert d0exp_fvset(result) == frozenset({"f", "n"})


# --- nested shadowing / fresh-name collisions --------------------------------

def test_nested_shadowing_is_respected():
    # Both the outer and inner y-binders independently capture the free y
    # in the replacement, so each needs its own distinct fresh name.
    inner = D0Elam("y", D0Eop2("+", D0Evar("x"), D0Evar("y")))
    expr = D0Elam("y", inner)
    result = d0exp_substitute(expr, "x", D0Evar("y"))
    assert result.arg1 != "y"
    assert result.arg2.arg1 != "y"
    assert result.arg2.arg1 != result.arg1
    assert d0exp_pretty(result.arg2.arg2) == f"(y + {result.arg2.arg1})"


def test_fresh_name_collision_with_existing_name():
    expr = D0Elam("y", D0Eop2("+", D0Evar("x"),
                              D0Eop2("+", D0Evar("y"), D0Evar("y_1"))))
    result = d0exp_substitute(expr, "x", D0Evar("y"))
    assert result.arg1 not in ("y", "y_1")


def test_fresh_name_collision_with_generated_name_in_same_call():
    # Two sibling binders both named y both conflict with the replacement;
    # the second fresh name picked must avoid the first one generated.
    expr = D0Epair(
        D0Elam("y", D0Eop2("+", D0Evar("x"), D0Evar("y"))),
        D0Elam("y", D0Eop2("+", D0Evar("x"), D0Evar("y"))))
    result = d0exp_substitute(expr, "x", D0Evar("y"))
    assert result.arg1.arg1 != result.arg2.arg1
    assert result.arg1.arg1 != "y"
    assert result.arg2.arg1 != "y"


# --- preservation / determinism / no evaluation ------------------------------

def test_inputs_preserved():
    expr = D0Elam("y", D0Eop2("+", D0Evar("x"), D0Evar("y")))
    replacement = D0Evar("y")
    before_expr, before_repl = d0exp_pretty(expr), d0exp_pretty(replacement)
    d0exp_substitute(expr, "x", replacement)
    assert d0exp_pretty(expr) == before_expr
    assert d0exp_pretty(replacement) == before_repl


def test_substitution_is_deterministic():
    expr = D0Elam("y", D0Eop2("+", D0Evar("x"), D0Evar("y")))
    r1 = d0exp_substitute(expr, "x", D0Evar("y"))
    r2 = d0exp_substitute(expr, "x", D0Evar("y"))
    assert d0exp_pretty(r1) == d0exp_pretty(r2)


def test_pretty_print_does_not_evaluate():
    # Division by zero must print, not raise, proving no evaluation occurs.
    assert d0exp_pretty(D0Eop2("/", D0Eint(1), D0Eint(0))) == "(1 / 0)"


def test_substitution_does_not_evaluate():
    expr = D0Eop2("/", D0Evar("x"), D0Eint(0))
    result = d0exp_substitute(expr, "x", D0Eint(1))
    assert result == D0Eop2("/", D0Eint(1), D0Eint(0))


# --- free-variable property ---------------------------------------------------

def test_free_variable_property_holds_when_free():
    expr = D0Elam("y", D0Eop2("+", D0Evar("x"), D0Evar("y")))
    replacement = D0Eop2("+", D0Evar("z"), D0Evar("w"))
    result = d0exp_substitute(expr, "x", replacement)
    expected = (d0exp_fvset(expr) - {"x"}) | d0exp_fvset(replacement)
    assert d0exp_fvset(result) == expected


def test_free_variable_property_holds_when_not_free():
    expr = D0Elet("x", D0Evar("z"), D0Evar("x"))
    result = d0exp_substitute(expr, "x", D0Eint(42))
    assert d0exp_fvset(result) == d0exp_fvset(expr)
