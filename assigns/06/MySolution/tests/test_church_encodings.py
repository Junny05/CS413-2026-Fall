"""Task 2 tests: Church encodings tested independently of the compiler.
Covers testing obligation 3 (every required operator/comparison,
zero/predecessor-of-zero, both outcomes of each comparison, boolean truth
tables) and structural purity of library combinators."""

import unittest

from . import _pathsetup  # noqa: F401
from target_ast import App, free_vars
from reducer import eval_target
from observers import observe_nat, observe_bool
import church_encodings as enc

BUDGET = 10_000


def nat(n):
    r = eval_target(enc.NUM(n), BUDGET)
    assert r.completed
    return observe_nat(r.value, BUDGET).value


def run_nat(term):
    r = eval_target(term, BUDGET)
    assert r.completed, "execution budget exhausted in test"
    obs = observe_nat(r.value, BUDGET)
    assert obs.value is not None, obs
    return obs.value


def run_bool(term):
    r = eval_target(term, BUDGET)
    assert r.completed, "execution budget exhausted in test"
    obs = observe_bool(r.value, BUDGET)
    assert obs.value is not None, obs
    return obs.value


def binop(combinator, a, b):
    return App(App(combinator, enc.NUM(a)), enc.NUM(b))


class ClosedCombinatorTests(unittest.TestCase):
    COMBINATORS = {
        "TRUE": enc.TRUE, "FALSE": enc.FALSE, "I": enc.I_COMBINATOR,
        "NOT": enc.NOT, "SUCC": enc.SUCC, "PRED": enc.PRED, "PAIR": enc.PAIR,
        "FST": enc.FST, "SND": enc.SND, "ADD": enc.ADD, "SUB": enc.SUB,
        "MUL": enc.MUL, "ISZERO": enc.ISZERO, "LEQ": enc.LEQ, "LT": enc.LT,
        "GT": enc.GT, "GEQ": enc.GEQ, "EQ": enc.EQ, "NEQ": enc.NEQ,
        "Z": enc.Z_COMBINATOR, "NUM(3)": enc.NUM(3), "ZERO": enc.ZERO,
        "_EAGER_AND": enc._EAGER_AND, "_EAGER_OR": enc._EAGER_OR,
        "NUM(0)": enc.NUM(0), "NUM(10)": enc.NUM(10),
    }

    def test_every_combinator_is_closed(self):
        for name, term in self.COMBINATORS.items():
            with self.subTest(name=name):
                self.assertEqual(free_vars(term), frozenset())


class NaturalTests(unittest.TestCase):
    def test_zero(self):
        self.assertEqual(nat(0), 0)

    def test_small_numeral(self):
        self.assertEqual(nat(5), 5)

    def test_successor(self):
        self.assertEqual(run_nat(App(enc.SUCC, enc.NUM(4))), 5)

    def test_predecessor_of_zero_is_zero(self):
        self.assertEqual(run_nat(App(enc.PRED, enc.NUM(0))), 0)

    def test_predecessor_of_positive(self):
        self.assertEqual(run_nat(App(enc.PRED, enc.NUM(7))), 6)

    def test_addition(self):
        self.assertEqual(run_nat(binop(enc.ADD, 3, 4)), 7)

    def test_truncated_subtraction_positive(self):
        self.assertEqual(run_nat(binop(enc.SUB, 9, 4)), 5)

    def test_truncated_subtraction_floors_at_zero(self):
        self.assertEqual(run_nat(binop(enc.SUB, 2, 5)), 0)

    def test_subtraction_equal_operands(self):
        self.assertEqual(run_nat(binop(enc.SUB, 6, 6)), 0)

    def test_multiplication(self):
        self.assertEqual(run_nat(binop(enc.MUL, 3, 4)), 12)

    def test_multiplication_by_zero(self):
        self.assertEqual(run_nat(binop(enc.MUL, 0, 9)), 0)


class ComparisonTests(unittest.TestCase):
    def test_iszero_true(self):
        self.assertEqual(run_bool(App(enc.ISZERO, enc.NUM(0))), True)

    def test_iszero_false(self):
        self.assertEqual(run_bool(App(enc.ISZERO, enc.NUM(1))), False)

    def test_lt_true_and_false(self):
        self.assertEqual(run_bool(binop(enc.LT, 2, 5)), True)
        self.assertEqual(run_bool(binop(enc.LT, 5, 2)), False)
        self.assertEqual(run_bool(binop(enc.LT, 3, 3)), False)

    def test_leq_true_and_false(self):
        self.assertEqual(run_bool(binop(enc.LEQ, 3, 3)), True)
        self.assertEqual(run_bool(binop(enc.LEQ, 4, 3)), False)

    def test_gt_true_and_false(self):
        self.assertEqual(run_bool(binop(enc.GT, 5, 2)), True)
        self.assertEqual(run_bool(binop(enc.GT, 2, 5)), False)

    def test_geq_true_and_false(self):
        self.assertEqual(run_bool(binop(enc.GEQ, 3, 3)), True)
        self.assertEqual(run_bool(binop(enc.GEQ, 2, 3)), False)

    def test_eq_true_and_false(self):
        self.assertEqual(run_bool(binop(enc.EQ, 4, 4)), True)
        self.assertEqual(run_bool(binop(enc.EQ, 4, 5)), False)

    def test_neq_true_and_false(self):
        self.assertEqual(run_bool(binop(enc.NEQ, 4, 5)), True)
        self.assertEqual(run_bool(binop(enc.NEQ, 4, 4)), False)


class BooleanTruthTableTests(unittest.TestCase):
    def test_not(self):
        self.assertEqual(run_bool(App(enc.NOT, enc.TRUE)), False)
        self.assertEqual(run_bool(App(enc.NOT, enc.FALSE)), True)

    def test_eager_and_truth_table(self):
        and_ = enc._EAGER_AND
        self.assertEqual(run_bool(App(App(and_, enc.TRUE), enc.TRUE)), True)
        self.assertEqual(run_bool(App(App(and_, enc.TRUE), enc.FALSE)), False)
        self.assertEqual(run_bool(App(App(and_, enc.FALSE), enc.TRUE)), False)
        self.assertEqual(run_bool(App(App(and_, enc.FALSE), enc.FALSE)), False)

    def test_eager_or_truth_table(self):
        or_ = enc._EAGER_OR
        self.assertEqual(run_bool(App(App(or_, enc.TRUE), enc.TRUE)), True)
        self.assertEqual(run_bool(App(App(or_, enc.TRUE), enc.FALSE)), True)
        self.assertEqual(run_bool(App(App(or_, enc.FALSE), enc.TRUE)), True)
        self.assertEqual(run_bool(App(App(or_, enc.FALSE), enc.FALSE)), False)


class PairTests(unittest.TestCase):
    def test_projections(self):
        p = App(App(enc.PAIR, enc.NUM(2)), enc.TRUE)
        self.assertEqual(run_nat(App(enc.FST, p)), 2)
        self.assertEqual(run_bool(App(enc.SND, p)), True)

    def test_nested_pair_projections(self):
        inner = App(App(enc.PAIR, enc.NUM(2)), enc.TRUE)
        outer = App(App(enc.PAIR, inner), enc.NUM(3))
        first = App(enc.FST, outer)
        self.assertEqual(run_nat(App(enc.FST, first)), 2)
        self.assertEqual(run_bool(App(enc.SND, first)), True)
        self.assertEqual(run_nat(App(enc.SND, outer)), 3)


class SuccAndNumeralRelationTests(unittest.TestCase):
    def test_succ_of_succ_matches_direct_numeral(self):
        twice_succ = App(enc.SUCC, App(enc.SUCC, enc.NUM(0)))
        self.assertEqual(run_nat(twice_succ), nat(2))

    def test_pred_undoes_succ(self):
        for n in range(5):
            with self.subTest(n=n):
                self.assertEqual(run_nat(App(enc.PRED, App(enc.SUCC, enc.NUM(n)))), n)


if __name__ == "__main__":
    unittest.main()
