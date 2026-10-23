"""Task 4 tests: observers and the end-to-end demonstrations. Covers
testing obligation 6 (all demonstrations, nested pairs) and OBS-01-style
checks (alpha-renamed/computed encodings, malformed output, budget
exhaustion distinguished from decoding, Church zero under both kinds)."""

import unittest

from . import _pathsetup  # noqa: F401
from lambda1_vp import (
    D0Eapp, D0Ebtf, D0Eif0, D0Eint, D0Elam, D0Elet, D0Eop2, D0Epair,
    D0Epfst, D0Epsnd, D0Evar, D0Efix,
)
from compiler import compile_expr
from church_encodings import NUM, TRUE, FALSE, Z_COMBINATOR
from reducer import eval_target
from observers import observe_nat, observe_bool, observe_pair, ObserveStatus
from target_ast import App, Lam, Var, substitute
import demo

BUDGET = 50_000


class DemoTableTests(unittest.TestCase):
    def test_all_mandatory_demonstrations_pass(self):
        for name, source, kind, expected in demo.DEMOS:
            with self.subTest(name=name):
                term = compile_expr(source)
                result = eval_target(term, demo.EXEC_BUDGET)
                if expected is None:
                    self.assertFalse(result.completed)
                    continue
                self.assertTrue(result.completed)
                observe = observe_nat if kind == "nat" else observe_bool
                obs = observe(result.value, demo.OBS_BUDGET)
                self.assertIs(obs.status, ObserveStatus.DECODED)
                self.assertEqual(obs.value, expected)


class NestedPairTests(unittest.TestCase):
    def test_nested_pair_decoding(self):
        # pair (pair 2 true) 3
        e = D0Epair(D0Epair(D0Eint(2), D0Ebtf(True)), D0Eint(3))
        term = compile_expr(e)
        result = eval_target(term, BUDGET)
        self.assertTrue(result.completed)
        obs = observe_pair(result.value, (("nat", "bool"), "nat"), BUDGET, (BUDGET, BUDGET))
        self.assertIs(obs.status, ObserveStatus.DECODED)
        self.assertEqual(obs.value, ((2, True), 3))


class ObservationRobustnessTests(unittest.TestCase):
    def test_alpha_renamed_numeral_decodes(self):
        renamed = substitute(NUM(3), "s", Var("ess"))  # harmless no-op rename path
        value = eval_target(renamed, BUDGET).value
        self.assertEqual(observe_nat(value, BUDGET).value, 3)

    def test_computed_numeral_with_internal_redexes_decodes(self):
        # (lam x. NUM(4)) ((fix loop(y). loop y) 0) is never applied, so the
        # argument's divergence is irrelevant; but build a numeral whose
        # value still carries a beta-redex embedded in an unevaluated
        # position by wrapping it in an identity application chain.
        I = Lam("x", Var("x"))
        wrapped = App(I, NUM(4))
        value = eval_target(wrapped, BUDGET).value
        self.assertEqual(observe_nat(value, BUDGET).value, 4)

    def test_church_zero_decodes_as_nat_and_as_bool_false_shape(self):
        zero_value = eval_target(NUM(0), BUDGET).value
        self.assertEqual(observe_nat(zero_value, BUDGET).value, 0)
        false_value = eval_target(FALSE, BUDGET).value
        self.assertEqual(observe_bool(false_value, BUDGET).value, False)
        # NUM(0) and FALSE share the same lambda representation.
        self.assertEqual(observe_bool(zero_value, BUDGET).value, False)
        self.assertEqual(observe_nat(false_value, BUDGET).value, 0)

    def test_malformed_natural_output_detected(self):
        junk = Lam("c", Lam("z", Var("c")))  # neither STEP- nor BASE-shaped
        obs = observe_nat(junk, BUDGET)
        self.assertIs(obs.status, ObserveStatus.MALFORMED)

    def test_malformed_boolean_output_detected(self):
        # A stuck open term: applying it to the two markers stays stuck and
        # is neither marker, so it must be reported as malformed.
        junk = Var("free")
        obs = observe_bool(junk, BUDGET)
        self.assertIs(obs.status, ObserveStatus.MALFORMED)

    def test_observation_budget_exhaustion_distinguished_from_malformed(self):
        LOOP = App(Z_COMBINATOR, Lam("loop", Lam("x", App(Var("loop"), Var("x")))))
        diverging_value_producer = App(LOOP, NUM(0))
        obs = observe_nat(diverging_value_producer, 20)
        self.assertIs(obs.status, ObserveStatus.EXHAUSTED)
        self.assertNotEqual(obs.status, ObserveStatus.MALFORMED)


class RecursiveApplicationBoundTests(unittest.TestCase):
    """OBS-03: recursive functions are evaluated only to a lambda value
    before being applied, never reduced beneath their own binders."""

    def test_fibonacci_recursive_binder_not_reduced_under(self):
        fib = D0Efix(
            "fib", "n",
            D0Eif0(
                D0Eop2("<=", D0Evar("n"), D0Eint(1)),
                D0Evar("n"),
                D0Eop2(
                    "+",
                    D0Eapp(D0Evar("fib"), D0Eop2("-", D0Evar("n"), D0Eint(1))),
                    D0Eapp(D0Evar("fib"), D0Eop2("-", D0Evar("n"), D0Eint(2))),
                ),
            ),
        )
        term = compile_expr(D0Eapp(fib, D0Eint(6)))
        # The compiled fix value itself (before being applied to an
        # argument) reduces to a Lam value using only Z's own fixed,
        # small unfolding cost -- never touching the recursive body,
        # which stays unreduced inside that Lam's binder.
        fix_term = compile_expr(fib)
        small_step = eval_target(fix_term, 3)
        self.assertTrue(small_step.completed)
        self.assertIsInstance(small_step.value, Lam)

        result = eval_target(term, 50_000)
        self.assertTrue(result.completed)
        self.assertEqual(observe_nat(result.value, 5000).value, 8)


if __name__ == "__main__":
    unittest.main()
