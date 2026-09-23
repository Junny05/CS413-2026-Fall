"""Tests for pairs and projections (T0Mpair, T0Mpfst, T0Mpsnd).

Run with: python3 MySolution/TEST/test02_lambda0.py
Requires Python 3.12 or later, like lambda0.py.
"""

import sys
import unittest
from pathlib import Path

# Allow this file to run directly from any working directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lambda0 import (
    T0Mint, T0Mbtf, T0Mstr, T0Mvar, T0Mlam, T0Mfix, T0Mapp, T0Mif0, T0Mop1, T0Mop2,
    T0Mpair, T0Mpfst, T0Mpsnd,
    t0erm_size, t0erm_fvset, t0erm_subst0, t0erm_cbv_evaluate0,
)


class TestSize(unittest.TestCase):
    def test_pair_size(self):
        self.assertEqual(t0erm_size(T0Mpair(T0Mint(1), T0Mint(2))), 3)

    def test_projection_size(self):
        pair = T0Mpair(T0Mint(1), T0Mint(2))
        self.assertEqual(t0erm_size(T0Mpfst(pair)), 4)
        self.assertEqual(t0erm_size(T0Mpsnd(pair)), 4)

    def test_nested_pair_size(self):
        # ((1, 2), 3): outer pair, inner pair, and three ints -> 5 nodes.
        term = T0Mpair(T0Mpair(T0Mint(1), T0Mint(2)), T0Mint(3))
        self.assertEqual(t0erm_size(term), 5)

    def test_pair_inside_other_constructs(self):
        # if true then (1, 2) else 0 -- the pair still counts its own nodes.
        term = T0Mif0(T0Mbtf(True), T0Mpair(T0Mint(1), T0Mint(2)), T0Mint(0))
        self.assertEqual(t0erm_size(term), 1 + 1 + 3 + 1)

    def test_projection_of_lambda_body(self):
        term = T0Mlam("p", T0Mpfst(T0Mvar("p")))
        self.assertEqual(t0erm_size(term), 1 + (1 + 1))


class TestFreeVariables(unittest.TestCase):
    def test_pair_fvset(self):
        term = T0Mpair(T0Mvar("x"), T0Mvar("y"))
        self.assertEqual(t0erm_fvset(term), frozenset({"x", "y"}))

    def test_projection_fvset(self):
        pair = T0Mpair(T0Mvar("x"), T0Mvar("y"))
        self.assertEqual(t0erm_fvset(T0Mpfst(pair)), frozenset({"x", "y"}))
        self.assertEqual(t0erm_fvset(T0Mpsnd(pair)), frozenset({"x", "y"}))

    def test_pair_binds_no_variables(self):
        # Unlike T0Mlam/T0Mfix, a pair does not remove any variable.
        term = T0Mpair(T0Mvar("x"), T0Mint(0))
        self.assertEqual(t0erm_fvset(term), frozenset({"x"}))

    def test_nested_pair_fvset(self):
        term = T0Mpair(T0Mpair(T0Mvar("a"), T0Mvar("b")), T0Mvar("c"))
        self.assertEqual(t0erm_fvset(term), frozenset({"a", "b", "c"}))

    def test_pair_under_lambda_binder(self):
        # lambda x. (x, y) -- x is bound, y remains free.
        term = T0Mlam("x", T0Mpair(T0Mvar("x"), T0Mvar("y")))
        self.assertEqual(t0erm_fvset(term), frozenset({"y"}))

    def test_repeated_variable_in_pair(self):
        term = T0Mpfst(T0Mpair(T0Mvar("x"), T0Mvar("x")))
        self.assertEqual(t0erm_fvset(term), frozenset({"x"}))


class TestSubstitution(unittest.TestCase):
    def test_substitute_into_pair_components(self):
        term = T0Mpair(T0Mvar("x"), T0Mvar("y"))
        result = t0erm_subst0(term, "x", T0Mint(1))
        self.assertEqual(result, T0Mpair(T0Mint(1), T0Mvar("y")))

    def test_substitute_into_second_component_only(self):
        term = T0Mpair(T0Mvar("x"), T0Mvar("y"))
        result = t0erm_subst0(term, "y", T0Mint(2))
        self.assertEqual(result, T0Mpair(T0Mvar("x"), T0Mint(2)))

    def test_substitute_into_projection_operand(self):
        term = T0Mpfst(T0Mvar("x"))
        self.assertEqual(t0erm_subst0(term, "x", T0Mpair(T0Mint(1), T0Mint(2))),
                          T0Mpfst(T0Mpair(T0Mint(1), T0Mint(2))))
        term = T0Mpsnd(T0Mvar("x"))
        self.assertEqual(t0erm_subst0(term, "x", T0Mpair(T0Mint(1), T0Mint(2))),
                          T0Mpsnd(T0Mpair(T0Mint(1), T0Mint(2))))

    def test_substitute_into_nested_pairs(self):
        term = T0Mpair(T0Mpair(T0Mvar("x"), T0Mvar("x")), T0Mvar("x"))
        result = t0erm_subst0(term, "x", T0Mint(7))
        self.assertEqual(result, T0Mpair(T0Mpair(T0Mint(7), T0Mint(7)), T0Mint(7)))

    def test_substitution_under_lambda_binder(self):
        # lambda x. (x, y)[y := 1] = lambda x. (x, 1); x is bound, unaffected.
        term = T0Mlam("x", T0Mpair(T0Mvar("x"), T0Mvar("y")))
        result = t0erm_subst0(term, "y", T0Mint(1))
        self.assertEqual(result, T0Mlam("x", T0Mpair(T0Mvar("x"), T0Mint(1))))

    def test_substitution_stops_at_shadowing_lambda_binder(self):
        # lambda x. (x, y)[x := 1] leaves the bound x untouched.
        term = T0Mlam("x", T0Mpair(T0Mvar("x"), T0Mvar("y")))
        result = t0erm_subst0(term, "x", T0Mint(1))
        self.assertEqual(result, term)

    def test_substitution_under_fix_binder(self):
        # fix f(x) = (x, y)[y := 1]; f and x are bound, y is substituted.
        term = T0Mfix("f", "x", T0Mpair(T0Mvar("x"), T0Mvar("y")))
        result = t0erm_subst0(term, "y", T0Mint(1))
        self.assertEqual(result, T0Mfix("f", "x", T0Mpair(T0Mvar("x"), T0Mint(1))))

    def test_substitution_stops_at_shadowing_fix_binder(self):
        term = T0Mfix("f", "x", T0Mpsnd(T0Mvar("f")))
        result = t0erm_subst0(term, "f", T0Mpair(T0Mint(1), T0Mint(2)))
        self.assertEqual(result, term)


class TestEvaluation(unittest.TestCase):
    def test_example_from_assignment(self):
        term = T0Mpsnd(T0Mpair(T0Mint(1), T0Mop2("+", T0Mint(2), T0Mint(3))))
        self.assertEqual(t0erm_cbv_evaluate0(term), T0Mint(5))

    def test_pair_construction_requires_evaluation(self):
        term = T0Mpair(T0Mop2("+", T0Mint(1), T0Mint(1)), T0Mop2("*", T0Mint(3), T0Mint(3)))
        self.assertEqual(t0erm_cbv_evaluate0(term), T0Mpair(T0Mint(2), T0Mint(9)))

    def test_both_projections(self):
        pair = T0Mpair(T0Mop2("+", T0Mint(1), T0Mint(1)), T0Mstr("hi"))
        self.assertEqual(t0erm_cbv_evaluate0(T0Mpfst(pair)), T0Mint(2))
        self.assertEqual(t0erm_cbv_evaluate0(T0Mpsnd(pair)), T0Mstr("hi"))

    def test_nested_pairs(self):
        term = T0Mpair(T0Mpair(T0Mint(1), T0Mint(2)), T0Mint(3))
        self.assertEqual(
            t0erm_cbv_evaluate0(term),
            T0Mpair(T0Mpair(T0Mint(1), T0Mint(2)), T0Mint(3)),
        )
        self.assertEqual(
            t0erm_cbv_evaluate0(T0Mpfst(T0Mpfst(term))),
            T0Mint(1),
        )

    def test_pair_of_different_kinds_of_values(self):
        term = T0Mpair(T0Mint(1), T0Mlam("x", T0Mvar("x")))
        result = t0erm_cbv_evaluate0(term)
        self.assertEqual(result.arg1, T0Mint(1))
        self.assertEqual(result.arg2, T0Mlam("x", T0Mvar("x")))

    def test_function_returning_pair(self):
        # (lambda x. (x, x + 1)) 4 -> (4, 5)
        term = T0Mapp(
            T0Mlam("x", T0Mpair(T0Mvar("x"), T0Mop2("+", T0Mvar("x"), T0Mint(1)))),
            T0Mint(4),
        )
        self.assertEqual(t0erm_cbv_evaluate0(term), T0Mpair(T0Mint(4), T0Mint(5)))

    def test_function_accepting_pair_via_projections(self):
        # (lambda p. pfst(p) + psnd(p)) (3, 4) -> 7
        term = T0Mapp(
            T0Mlam("p", T0Mop2("+", T0Mpfst(T0Mvar("p")), T0Mpsnd(T0Mvar("p")))),
            T0Mpair(T0Mint(3), T0Mint(4)),
        )
        self.assertEqual(t0erm_cbv_evaluate0(term), T0Mint(7))

    def test_recursive_function_over_pairs(self):
        # fix sum_to(p) = if fst(p) <= 0 then snd(p)
        #                 else sum_to((fst(p) - 1, snd(p) + fst(p)))
        p = T0Mvar("p")
        body = T0Mif0(
            T0Mop2("<=", T0Mpfst(p), T0Mint(0)),
            T0Mpsnd(p),
            T0Mapp(
                T0Mvar("sum_to"),
                T0Mpair(
                    T0Mop2("-", T0Mpfst(p), T0Mint(1)),
                    T0Mop2("+", T0Mpsnd(p), T0Mpfst(p)),
                ),
            ),
        )
        sum_to = T0Mfix("sum_to", "p", body)
        term = T0Mapp(sum_to, T0Mpair(T0Mint(5), T0Mint(0)))
        self.assertEqual(t0erm_cbv_evaluate0(term), T0Mint(15))

    def test_projection_of_non_pair_raises_type_error(self):
        for value in [T0Mint(5), T0Mbtf(True), T0Mstr("x"), T0Mlam("x", T0Mvar("x"))]:
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    t0erm_cbv_evaluate0(T0Mpfst(value))
                with self.assertRaises(TypeError):
                    t0erm_cbv_evaluate0(T0Mpsnd(value))

    def test_left_to_right_evaluation_order(self):
        # The first component's error occurs before the second is evaluated.
        term = T0Mpair(
            T0Mop2("/", T0Mint(1), T0Mint(0)),
            T0Mop1("-", T0Mstr("bad")),
        )
        with self.assertRaises(ZeroDivisionError):
            t0erm_cbv_evaluate0(term)

    def test_both_components_evaluated_even_if_unused_by_projection(self):
        # From the assignment: pfst must not skip evaluating the second
        # component just because a projection does not select it.
        term = T0Mpfst(T0Mpair(T0Mint(1), T0Mop2("/", T0Mint(1), T0Mint(0))))
        with self.assertRaises(ZeroDivisionError):
            t0erm_cbv_evaluate0(term)

        # Symmetrically, psnd must not skip the unused first component.
        term = T0Mpsnd(T0Mpair(T0Mop2("/", T0Mint(1), T0Mint(0)), T0Mint(2)))
        with self.assertRaises(ZeroDivisionError):
            t0erm_cbv_evaluate0(term)

    def test_substitution_during_application_with_pairs(self):
        # (fix f(p) = if fst(p) == 0 then snd(p) else f((fst(p)-1, snd(p)*fst(p))))
        # applied to (4, 1) computes 4! = 24.
        p = T0Mvar("p")
        body = T0Mif0(
            T0Mop2("==", T0Mpfst(p), T0Mint(0)),
            T0Mpsnd(p),
            T0Mapp(
                T0Mvar("fact"),
                T0Mpair(
                    T0Mop2("-", T0Mpfst(p), T0Mint(1)),
                    T0Mop2("*", T0Mpsnd(p), T0Mpfst(p)),
                ),
            ),
        )
        fact = T0Mfix("fact", "p", body)
        term = T0Mapp(fact, T0Mpair(T0Mint(4), T0Mint(1)))
        self.assertEqual(t0erm_cbv_evaluate0(term), T0Mint(24))


if __name__ == "__main__":
    unittest.main(verbosity=2)
