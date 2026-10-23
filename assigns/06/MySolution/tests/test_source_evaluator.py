"""Direct tests of the source-side half of the shared evaluator
(evaluator.evaluate_source), which was previously only exercised
indirectly through compiled-and-decoded answers. Covers the semantics
table in Assign06/REQUIREMENTS Section 3.2: left-to-right call-by-value,
a boolean (not numeric-zero) if0 test, truncated subtraction, and
short-circuit and/or, plus error behavior on ill-formed programs and
agreement with the compiled-and-decoded pipeline on every mandatory demo
case."""

import unittest

from . import _pathsetup  # noqa: F401
from lambda1_vp import (
    D0Eapp, D0Ebtf, D0Eif0, D0Eint, D0Elam, D0Elet, D0Eop1, D0Eop2,
    D0Epair, D0Epfst, D0Epsnd, D0Evar, D0Efix, D0Vint, D0Vbtf, D0Vpair,
)
from evaluator import evaluate_source, SourceEvalError
import demo


class LiteralAndVariableTests(unittest.TestCase):
    def test_int_literal(self):
        self.assertEqual(evaluate_source(D0Eint(7)), D0Vint(7))

    def test_bool_literals(self):
        self.assertEqual(evaluate_source(D0Ebtf(True)), D0Vbtf(True))
        self.assertEqual(evaluate_source(D0Ebtf(False)), D0Vbtf(False))

    def test_negative_literal_rejected(self):
        with self.assertRaises(SourceEvalError):
            evaluate_source(D0Eint(-3))


class ArithmeticSemanticsTests(unittest.TestCase):
    def test_addition_and_multiplication(self):
        e = D0Eop2("+", D0Eint(2), D0Eop2("*", D0Eint(3), D0Eint(4)))
        self.assertEqual(evaluate_source(e), D0Vint(14))

    def test_truncated_subtraction_floors_at_zero(self):
        self.assertEqual(evaluate_source(D0Eop2("-", D0Eint(2), D0Eint(5))), D0Vint(0))

    def test_truncated_subtraction_positive(self):
        self.assertEqual(evaluate_source(D0Eop2("-", D0Eint(9), D0Eint(4))), D0Vint(5))

    def test_all_comparisons_both_outcomes(self):
        cases = [
            ("<", 2, 3, True), ("<", 3, 2, False),
            ("<=", 3, 3, True), ("<=", 4, 3, False),
            (">", 3, 2, True), (">", 2, 3, False),
            (">=", 3, 3, True), (">=", 2, 3, False),
            ("==", 3, 3, True), ("==", 3, 4, False),
            ("!=", 3, 4, True), ("!=", 3, 3, False),
        ]
        for op, a, b, expected in cases:
            with self.subTest(op=op, a=a, b=b):
                self.assertEqual(
                    evaluate_source(D0Eop2(op, D0Eint(a), D0Eint(b))), D0Vbtf(expected)
                )


class BooleanSemanticsTests(unittest.TestCase):
    def test_not_both_directions(self):
        self.assertEqual(evaluate_source(D0Eop1("not", D0Ebtf(True))), D0Vbtf(False))
        self.assertEqual(evaluate_source(D0Eop1("not", D0Ebtf(False))), D0Vbtf(True))

    def test_and_truth_table(self):
        for a in (True, False):
            for b in (True, False):
                with self.subTest(a=a, b=b):
                    e = D0Eop2("and", D0Ebtf(a), D0Ebtf(b))
                    self.assertEqual(evaluate_source(e), D0Vbtf(a and b))

    def test_or_truth_table(self):
        for a in (True, False):
            for b in (True, False):
                with self.subTest(a=a, b=b):
                    e = D0Eop2("or", D0Ebtf(a), D0Ebtf(b))
                    self.assertEqual(evaluate_source(e), D0Vbtf(a or b))

    def test_and_short_circuits_on_false_left(self):
        # The right operand, if evaluated, would raise; it must not be.
        poison = D0Eop2("+", D0Ebtf(True), D0Eint(1))  # ill-typed, would raise
        e = D0Eop2("and", D0Ebtf(False), poison)
        self.assertEqual(evaluate_source(e), D0Vbtf(False))

    def test_or_short_circuits_on_true_left(self):
        poison = D0Eop2("+", D0Ebtf(True), D0Eint(1))
        e = D0Eop2("or", D0Ebtf(True), poison)
        self.assertEqual(evaluate_source(e), D0Vbtf(True))


class ConditionalSemanticsTests(unittest.TestCase):
    def test_if0_tests_boolean_not_numeric_zero(self):
        # D0Eif0 tests a boolean condition, not whether a number is zero.
        e = D0Eif0(D0Ebtf(True), D0Eint(1), D0Eint(2))
        self.assertEqual(evaluate_source(e), D0Vint(1))

    def test_if0_evaluates_only_selected_branch(self):
        poison = D0Eop2("+", D0Ebtf(True), D0Eint(1))
        self.assertEqual(evaluate_source(D0Eif0(D0Ebtf(True), D0Eint(1), poison)), D0Vint(1))
        self.assertEqual(evaluate_source(D0Eif0(D0Ebtf(False), poison, D0Eint(2))), D0Vint(2))

    def test_if0_requires_boolean_condition(self):
        with self.assertRaises(SourceEvalError):
            evaluate_source(D0Eif0(D0Eint(0), D0Eint(1), D0Eint(2)))


class BindingSemanticsTests(unittest.TestCase):
    def test_let_binds_body_not_initializer(self):
        # let x = 3 in (lam y. x + y) 4
        e = D0Elet(
            "x", D0Eint(3),
            D0Eapp(D0Elam("y", D0Eop2("+", D0Evar("x"), D0Evar("y"))), D0Eint(4)),
        )
        self.assertEqual(evaluate_source(e), D0Vint(7))

    def test_let_initializer_evaluated_before_body(self):
        poison = D0Eop2("+", D0Ebtf(True), D0Eint(1))
        with self.assertRaises(SourceEvalError):
            evaluate_source(D0Elet("x", poison, D0Eint(2)))

    def test_unbound_variable_raises(self):
        with self.assertRaises(SourceEvalError):
            evaluate_source(D0Evar("nope"))


class PairSemanticsTests(unittest.TestCase):
    def test_pair_and_projections(self):
        e = D0Epair(D0Eint(2), D0Ebtf(True))
        self.assertEqual(evaluate_source(e), D0Vpair(D0Vint(2), D0Vbtf(True)))
        self.assertEqual(evaluate_source(D0Epfst(e)), D0Vint(2))
        self.assertEqual(evaluate_source(D0Epsnd(e)), D0Vbtf(True))

    def test_pair_components_evaluated_left_to_right_even_if_unused(self):
        poison = D0Eop2("+", D0Ebtf(True), D0Eint(1))
        with self.assertRaises(SourceEvalError):
            evaluate_source(D0Epfst(D0Epair(D0Eint(2), poison)))
        with self.assertRaises(SourceEvalError):
            evaluate_source(D0Epsnd(D0Epair(poison, D0Ebtf(True))))


class RecursionSemanticsTests(unittest.TestCase):
    def test_factorial(self):
        fact = D0Efix(
            "f", "n",
            D0Eif0(D0Eop2("==", D0Evar("n"), D0Eint(0)), D0Eint(1),
                   D0Eop2("*", D0Evar("n"), D0Eapp(D0Evar("f"), D0Eop2("-", D0Evar("n"), D0Eint(1))))),
        )
        self.assertEqual(evaluate_source(D0Eapp(fact, D0Eint(4))), D0Vint(24))

    def test_coincident_fix_binders(self):
        e = D0Eapp(D0Efix("f", "f", D0Evar("f")), D0Eint(3))
        self.assertEqual(evaluate_source(e), D0Vint(3))

    def test_applying_non_function_raises(self):
        with self.assertRaises(SourceEvalError):
            evaluate_source(D0Eapp(D0Eint(1), D0Eint(2)))


class OracleAgreementTests(unittest.TestCase):
    """evaluate_source, used as the expected-answer oracle, must agree
    with the compiled-and-decoded pipeline on every terminating demo
    case -- i.e. the hardcoded `expected` table in demo.py is not just an
    assertion in isolation, but actually matches the source semantics."""

    def test_source_oracle_matches_demo_table(self):
        for name, source, kind, expected in demo.DEMOS:
            if expected is None:
                continue
            with self.subTest(name=name):
                value = evaluate_source(source)
                if kind == "nat":
                    self.assertIsInstance(value, D0Vint)
                    self.assertEqual(value.arg1, expected)
                else:
                    self.assertIsInstance(value, D0Vbtf)
                    self.assertEqual(value.arg1, expected)


if __name__ == "__main__":
    unittest.main()
