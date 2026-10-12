"""unittest suite for Assignment 5.

Run from the assigns/05 directory with:
    python3 -m unittest MySolution.test_unittest -v
"""

from __future__ import annotations

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lambda1_vp import (
    D0Eint, D0Ebtf, D0Eop1, D0Eop2, D0Evar, D0Elam, D0Efix, D0Eapp,
    D0Eif0, D0Elet, D0Epair, D0Epfst, D0Epsnd, d0exp_fvset,
)
from MySolution.pretty_print import d0exp_pretty
from MySolution.substitution import d0exp_substitute


class TestPrettyPrint(unittest.TestCase):
    def test_int_positive(self):
        self.assertEqual(d0exp_pretty(D0Eint(4)), "4")

    def test_int_negative(self):
        self.assertEqual(d0exp_pretty(D0Eint(-17)), "-17")

    def test_int_large(self):
        self.assertEqual(d0exp_pretty(D0Eint(123456789012345)), "123456789012345")

    def test_btf_true(self):
        self.assertEqual(d0exp_pretty(D0Ebtf(True)), "true")

    def test_btf_false(self):
        self.assertEqual(d0exp_pretty(D0Ebtf(False)), "false")

    def test_var(self):
        self.assertEqual(d0exp_pretty(D0Evar("x")), "x")

    def test_op1(self):
        self.assertEqual(d0exp_pretty(D0Eop1("+1", D0Evar("x"))), "(+1 x)")

    def test_op2(self):
        self.assertEqual(
            d0exp_pretty(D0Eop2("+", D0Evar("x"), D0Eint(1))), "(x + 1)")

    def test_op2_division_by_zero_not_raised(self):
        self.assertEqual(
            d0exp_pretty(D0Eop2("/", D0Eint(1), D0Eint(0))), "(1 / 0)")

    def test_lam(self):
        self.assertEqual(
            d0exp_pretty(D0Elam("x", D0Evar("x"))), "(lam x. x)")

    def test_fix(self):
        self.assertEqual(
            d0exp_pretty(D0Efix("f", "x", D0Eapp(D0Evar("f"), D0Evar("x")))),
            "(fix f(x). (f x))")

    def test_app(self):
        self.assertEqual(
            d0exp_pretty(D0Eapp(D0Evar("f"), D0Evar("x"))), "(f x)")

    def test_if0(self):
        self.assertEqual(
            d0exp_pretty(D0Eif0(D0Ebtf(True), D0Eint(1), D0Eint(2))),
            "(if true then 1 else 2)")

    def test_let(self):
        self.assertEqual(
            d0exp_pretty(D0Elet("x", D0Eint(1), D0Evar("x"))),
            "(let x = 1 in x)")

    def test_pair(self):
        self.assertEqual(
            d0exp_pretty(D0Epair(D0Eint(1), D0Eint(2))), "(pair 1 2)")

    def test_pfst(self):
        self.assertEqual(
            d0exp_pretty(D0Epfst(D0Epair(D0Eint(1), D0Eint(2)))),
            "(fst (pair 1 2))")

    def test_psnd(self):
        self.assertEqual(
            d0exp_pretty(D0Epsnd(D0Epair(D0Eint(1), D0Eint(2)))),
            "(snd (pair 1 2))")

    def test_nested_example_from_spec(self):
        expr = D0Eapp(
            D0Elam("x", D0Eop2("+", D0Evar("x"), D0Eint(1))), D0Eint(4))
        self.assertEqual(d0exp_pretty(expr), "((lam x. (x + 1)) 4)")

    def test_deeply_nested(self):
        expr = D0Eif0(
            D0Eop2("==", D0Evar("x"), D0Eint(0)),
            D0Elet("y", D0Eint(1), D0Eop2("+", D0Evar("y"), D0Evar("x"))),
            D0Epfst(D0Epair(D0Evar("x"), D0Evar("y"))))
        self.assertEqual(
            d0exp_pretty(expr),
            "(if (x == 0) then (let y = 1 in (y + x)) else (fst (pair x y)))")


class TestSubstitution(unittest.TestCase):
    # --- every constructor -------------------------------------------------
    def test_int_unaffected(self):
        self.assertEqual(
            d0exp_substitute(D0Eint(5), "x", D0Eint(9)), D0Eint(5))

    def test_btf_unaffected(self):
        self.assertEqual(
            d0exp_substitute(D0Ebtf(True), "x", D0Eint(9)), D0Ebtf(True))

    def test_var_matching(self):
        self.assertEqual(
            d0exp_substitute(D0Evar("x"), "x", D0Eint(9)), D0Eint(9))

    def test_var_nonmatching(self):
        self.assertEqual(
            d0exp_substitute(D0Evar("y"), "x", D0Eint(9)), D0Evar("y"))

    def test_op1(self):
        self.assertEqual(
            d0exp_substitute(D0Eop1("+1", D0Evar("x")), "x", D0Eint(9)),
            D0Eop1("+1", D0Eint(9)))

    def test_op2(self):
        self.assertEqual(
            d0exp_substitute(
                D0Eop2("+", D0Evar("x"), D0Evar("y")), "x", D0Eint(9)),
            D0Eop2("+", D0Eint(9), D0Evar("y")))

    def test_app(self):
        self.assertEqual(
            d0exp_substitute(
                D0Eapp(D0Evar("x"), D0Evar("y")), "x", D0Eint(9)),
            D0Eapp(D0Eint(9), D0Evar("y")))

    def test_if0(self):
        self.assertEqual(
            d0exp_substitute(
                D0Eif0(D0Evar("x"), D0Evar("x"), D0Evar("y")), "x", D0Eint(9)),
            D0Eif0(D0Eint(9), D0Eint(9), D0Evar("y")))

    def test_pair_pfst_psnd(self):
        self.assertEqual(
            d0exp_substitute(
                D0Epfst(D0Epair(D0Evar("x"), D0Evar("y"))), "x", D0Eint(9)),
            D0Epfst(D0Epair(D0Eint(9), D0Evar("y"))))
        self.assertEqual(
            d0exp_substitute(
                D0Epsnd(D0Epair(D0Evar("x"), D0Evar("y"))), "y", D0Eint(9)),
            D0Epsnd(D0Epair(D0Evar("x"), D0Eint(9))))

    def test_replacement_contains_target(self):
        result = d0exp_substitute(D0Evar("x"), "x", D0Eop2("+", D0Evar("x"), D0Eint(1)))
        self.assertEqual(result, D0Eop2("+", D0Evar("x"), D0Eint(1)))

    # --- shadowing -----------------------------------------------------
    def test_lambda_shadow_blocks_substitution(self):
        expr = D0Elam("x", D0Eop2("+", D0Evar("x"), D0Evar("y")))
        self.assertEqual(d0exp_substitute(expr, "x", D0Eint(3)), expr)

    def test_fix_shadow_blocks_on_function_name(self):
        expr = D0Efix("f", "n", D0Evar("f"))
        self.assertEqual(d0exp_substitute(expr, "f", D0Eint(3)), expr)

    def test_fix_shadow_blocks_on_parameter(self):
        expr = D0Efix("f", "n", D0Evar("n"))
        self.assertEqual(d0exp_substitute(expr, "n", D0Eint(3)), expr)

    def test_fix_shared_name_shadow(self):
        # parameter shadows function name when they coincide
        expr = D0Efix("f", "f", D0Evar("f"))
        self.assertEqual(d0exp_substitute(expr, "f", D0Eint(3)), expr)

    def test_let_shadow_blocks_in_body(self):
        expr = D0Elet("x", D0Evar("z"), D0Eop2("+", D0Evar("x"), D0Evar("y")))
        result = d0exp_substitute(expr, "x", D0Eint(3))
        self.assertEqual(result.arg3, D0Eop2("+", D0Evar("x"), D0Evar("y")))

    # --- let initializer vs. body --------------------------------------
    def test_let_substitutes_initializer_even_if_name_matches(self):
        expr = D0Elet("x", D0Evar("x"), D0Eop2("+", D0Evar("x"), D0Evar("y")))
        result = d0exp_substitute(expr, "x", D0Eint(3))
        self.assertEqual(result.arg1, "x")
        self.assertEqual(result.arg2, D0Eint(3))
        self.assertEqual(result.arg3, D0Eop2("+", D0Evar("x"), D0Evar("y")))

    # --- capture avoidance ----------------------------------------------
    def test_lambda_capture_avoidance(self):
        expr = D0Elam("y", D0Eop2("+", D0Evar("x"), D0Evar("y")))
        result = d0exp_substitute(expr, "x", D0Evar("y"))
        self.assertIsInstance(result, D0Elam)
        self.assertNotEqual(result.arg1, "y")
        self.assertEqual(d0exp_pretty(result), f"(lam {result.arg1}. (y + {result.arg1}))")

    def test_let_capture_avoidance(self):
        expr = D0Elet("y", D0Evar("x"), D0Eop2("+", D0Evar("x"), D0Evar("y")))
        result = d0exp_substitute(expr, "x", D0Evar("y"))
        self.assertEqual(result.arg2, D0Evar("y"))
        self.assertNotEqual(result.arg1, "y")
        self.assertEqual(
            d0exp_pretty(result.arg3), f"(y + {result.arg1})")

    def test_fix_capture_avoidance_function_name(self):
        expr = D0Efix("f", "n", D0Eop2("+", D0Evar("x"), D0Eapp(D0Evar("f"), D0Evar("n"))))
        result = d0exp_substitute(expr, "x", D0Evar("f"))
        self.assertNotEqual(result.arg1, "f")
        self.assertEqual(result.arg2, "n")
        self.assertEqual(
            d0exp_pretty(result.arg3),
            f"(f + ({result.arg1} n))")

    def test_fix_capture_avoidance_both_binders(self):
        # replacement conflicts with both the function name and the parameter
        expr = D0Efix("f", "n", D0Eop2("+", D0Evar("x"), D0Eapp(D0Evar("f"), D0Evar("n"))))
        result = d0exp_substitute(expr, "x", D0Eop2("+", D0Evar("f"), D0Evar("n")))
        self.assertNotEqual(result.arg1, "f")
        self.assertNotEqual(result.arg2, "n")
        self.assertNotEqual(result.arg1, result.arg2)
        # no bound occurrence of the new names should have been left free/stale
        self.assertEqual(d0exp_fvset(result), frozenset({"f", "n"}))

    # --- nested shadowing / fresh-name collisions -------------------------
    def test_nested_shadowing_during_rename(self):
        # (lam y. (lam y. (x + y))) [x := y]
        # Both the outer and the inner y-binder independently capture the
        # free y in the replacement and must each be alpha-renamed, using
        # distinct fresh names (nested shadowing must not merge them).
        inner = D0Elam("y", D0Eop2("+", D0Evar("x"), D0Evar("y")))
        expr = D0Elam("y", inner)
        result = d0exp_substitute(expr, "x", D0Evar("y"))
        self.assertNotEqual(result.arg1, "y")
        inner_result = result.arg2
        self.assertNotEqual(inner_result.arg1, "y")
        self.assertNotEqual(inner_result.arg1, result.arg1)
        self.assertEqual(
            d0exp_pretty(inner_result.arg2), f"(y + {inner_result.arg1})")

    def test_fresh_name_collision_with_existing_bound_name(self):
        # Force the first candidate fresh name (y_1) to already be in use.
        expr = D0Elam("y", D0Eop2("+", D0Evar("x"),
                                  D0Eop2("+", D0Evar("y"), D0Evar("y_1"))))
        result = d0exp_substitute(expr, "x", D0Evar("y"))
        self.assertNotIn(result.arg1, ("y", "y_1"))

    # --- preservation / determinism ---------------------------------------
    def test_inputs_not_mutated(self):
        expr = D0Elam("y", D0Eop2("+", D0Evar("x"), D0Evar("y")))
        replacement = D0Evar("y")
        expr_copy_pretty = d0exp_pretty(expr)
        replacement_copy_pretty = d0exp_pretty(replacement)
        d0exp_substitute(expr, "x", replacement)
        self.assertEqual(d0exp_pretty(expr), expr_copy_pretty)
        self.assertEqual(d0exp_pretty(replacement), replacement_copy_pretty)

    def test_deterministic(self):
        expr = D0Elam("y", D0Eop2("+", D0Evar("x"), D0Evar("y")))
        r1 = d0exp_substitute(expr, "x", D0Evar("y"))
        r2 = d0exp_substitute(expr, "x", D0Evar("y"))
        self.assertEqual(d0exp_pretty(r1), d0exp_pretty(r2))

    # --- free-variable property --------------------------------------------
    def test_free_variable_property_when_free(self):
        expr = D0Elam("y", D0Eop2("+", D0Evar("x"), D0Evar("y")))
        replacement = D0Eop2("+", D0Evar("z"), D0Evar("w"))
        result = d0exp_substitute(expr, "x", replacement)
        expected = (d0exp_fvset(expr) - {"x"}) | d0exp_fvset(replacement)
        self.assertEqual(d0exp_fvset(result), expected)

    def test_free_variable_property_when_not_free(self):
        expr = D0Elam("x", D0Evar("x"))
        result = d0exp_substitute(expr, "x", D0Eint(42))
        self.assertEqual(d0exp_fvset(result), d0exp_fvset(expr))
        self.assertEqual(d0exp_pretty(result), d0exp_pretty(expr))


if __name__ == "__main__":
    unittest.main()
