"""Task 1 tests: printer, free variables, substitution, and the weak
call-by-value target reducer. Covers testing obligations 1 and 2."""

import unittest

from . import _pathsetup  # noqa: F401
from target_ast import App, FreshNamer, Lam, Var, alpha_equivalent, free_vars, print_term, substitute
from reducer import eval_target


class PrinterTests(unittest.TestCase):
    def test_variable(self):
        self.assertEqual(print_term(Var("x")), "x")

    def test_abstraction(self):
        self.assertEqual(print_term(Lam("x", Var("x"))), "(lam x. x)")

    def test_application(self):
        self.assertEqual(print_term(App(Var("f"), Var("x"))), "(f x)")

    def test_nested(self):
        t = App(Lam("x", App(Var("x"), Var("y"))), Var("z"))
        self.assertEqual(print_term(t), "((lam x. (x y)) z)")

    def test_nested_target_term_multiple_levels(self):
        # ((lam x. (lam y. (x (f y)))) a) b, printed fully parenthesized.
        t = App(
            App(Lam("x", Lam("y", App(Var("x"), App(Var("f"), Var("y"))))), Var("a")),
            Var("b"),
        )
        self.assertEqual(
            print_term(t),
            "(((lam x. (lam y. (x (f y)))) a) b)",
        )

    def test_lambda_body_itself_an_application(self):
        t = Lam("x", App(Var("x"), Var("x")))
        self.assertEqual(print_term(t), "(lam x. (x x))")


class FreshNamerTests(unittest.TestCase):
    def test_skips_names_in_avoid_set(self):
        namer = FreshNamer()
        name = namer.fresh(frozenset({"_g0", "_g1"}), prefix="_g")
        self.assertEqual(name, "_g2")

    def test_repeated_calls_never_collide_even_with_disjoint_avoid_sets(self):
        namer = FreshNamer()
        names = [namer.fresh(frozenset(), prefix="_g") for _ in range(20)]
        self.assertEqual(len(names), len(set(names)))

    def test_deterministic_given_same_call_sequence(self):
        namer1 = FreshNamer()
        namer2 = FreshNamer()
        avoid_sets = [frozenset({"_g0"}), frozenset(), frozenset({"_g1", "_g2"})]
        seq1 = [namer1.fresh(a, prefix="_g") for a in avoid_sets]
        seq2 = [namer2.fresh(a, prefix="_g") for a in avoid_sets]
        self.assertEqual(seq1, seq2)

    def test_ordinary_identifiers_not_reserved_unless_in_avoid_set(self):
        namer = FreshNamer()
        # A completely empty avoid set never forces skipping "_g0" itself.
        self.assertEqual(namer.fresh(frozenset(), prefix="_g"), "_g0")


class FreeVarTests(unittest.TestCase):
    def test_var_is_free(self):
        self.assertEqual(free_vars(Var("x")), frozenset({"x"}))

    def test_lam_binds(self):
        self.assertEqual(free_vars(Lam("x", Var("x"))), frozenset())

    def test_lam_leaves_other_free(self):
        self.assertEqual(free_vars(Lam("x", Var("y"))), frozenset({"y"}))

    def test_app_unions(self):
        t = App(Var("x"), Var("y"))
        self.assertEqual(free_vars(t), frozenset({"x", "y"}))


class SubstitutionTests(unittest.TestCase):
    def test_capture_hazard_renames(self):
        # substituting x := y in (lam y. x) must avoid capturing y;
        # result must be alpha-equivalent to (lam fresh. y), with y free.
        term = Lam("y", Var("x"))
        result = substitute(term, "x", Var("y"))
        self.assertIsInstance(result, Lam)
        self.assertNotEqual(result.param, "y")
        self.assertTrue(alpha_equivalent(result, Lam("fresh", Var("y"))))
        self.assertIn("y", free_vars(result))

    def test_no_op_when_shadowed(self):
        term = Lam("x", Var("x"))
        result = substitute(term, "x", Var("z"))
        self.assertTrue(alpha_equivalent(result, Lam("x", Var("x"))))

    def test_simple_replacement(self):
        term = Var("x")
        result = substitute(term, "x", App(Var("f"), Var("y")))
        self.assertTrue(alpha_equivalent(result, App(Var("f"), Var("y"))))

    def test_does_not_mutate_input(self):
        term = Lam("y", Var("x"))
        snapshot = print_term(term)
        substitute(term, "x", Var("y"))
        self.assertEqual(print_term(term), snapshot)

    def test_app_both_sides(self):
        term = App(Var("x"), Var("x"))
        result = substitute(term, "x", Var("y"))
        self.assertTrue(alpha_equivalent(result, App(Var("y"), Var("y"))))

    def test_no_capture_when_param_absent_from_replacement(self):
        term = Lam("y", App(Var("x"), Var("y")))
        result = substitute(term, "x", Var("z"))
        self.assertTrue(alpha_equivalent(result, Lam("y", App(Var("z"), Var("y")))))


class AlphaEquivalenceTests(unittest.TestCase):
    def test_renamed_lambda_is_equivalent(self):
        self.assertTrue(alpha_equivalent(Lam("x", Var("x")), Lam("y", Var("y"))))

    def test_different_structure_is_not_equivalent(self):
        self.assertFalse(alpha_equivalent(Lam("x", Var("x")), Lam("x", Var("z"))))

    def test_free_variable_identity_matters(self):
        self.assertFalse(alpha_equivalent(Var("a"), Var("b")))

    def test_nested_binders_renamed_consistently(self):
        t1 = Lam("x", Lam("y", App(Var("x"), Var("y"))))
        t2 = Lam("p", Lam("q", App(Var("p"), Var("q"))))
        t3 = Lam("p", Lam("q", App(Var("q"), Var("p"))))
        self.assertTrue(alpha_equivalent(t1, t2))
        self.assertFalse(alpha_equivalent(t1, t3))


class DeeperSubstitutionTests(unittest.TestCase):
    def test_nested_lambda_capture_hazard(self):
        # Substituting x := y in (lam z. lam y. x) must rename the inner y
        # binder so the substituted free y is not captured.
        term = Lam("z", Lam("y", Var("x")))
        result = substitute(term, "x", Var("y"))
        self.assertTrue(alpha_equivalent(result, Lam("z", Lam("fresh", Var("y")))))

    def test_substitution_into_both_branches_of_app(self):
        term = App(Lam("y", Var("x")), Var("x"))
        result = substitute(term, "x", App(Var("f"), Var("y")))
        expected = App(Lam("fresh", App(Var("f"), Var("y"))), App(Var("f"), Var("y")))
        self.assertTrue(alpha_equivalent(result, expected))

    def test_shadowed_inner_binder_not_disturbed_when_name_absent(self):
        term = Lam("x", App(Var("x"), Var("y")))
        result = substitute(term, "y", Var("z"))
        self.assertTrue(alpha_equivalent(result, Lam("x", App(Var("x"), Var("z")))))


class ReducerTests(unittest.TestCase):
    def test_zero_step_value(self):
        value = Lam("x", Var("x"))
        result = eval_target(value, 1000)
        self.assertTrue(result.completed)
        self.assertEqual(result.steps, 0)
        self.assertTrue(alpha_equivalent(result.value, value))

    def test_value_with_budget_zero(self):
        value = Lam("x", Var("x"))
        result = eval_target(value, 0)
        self.assertTrue(result.completed)
        self.assertEqual(result.steps, 0)

    def test_left_to_right_order_and_no_reduction_under_lambda(self):
        # (lam x. ((lam y. y) x)) must stay a value unchanged in zero steps:
        # its body is never reduced because it is under a binder.
        I = Lam("x", Var("x"))
        body_has_redex = Lam("x", App(Lam("y", Var("y")), Var("x")))
        result = eval_target(body_has_redex, 1000)
        self.assertTrue(result.completed)
        self.assertEqual(result.steps, 0)
        self.assertTrue(alpha_equivalent(result.value, body_has_redex))

    def test_application_order_left_then_right_then_contract(self):
        # (I I) (I I) where I = lam x. x: evaluates fn, then arg, then applies.
        I = Lam("x", Var("x"))
        term = App(App(I, I), App(I, I))
        result = eval_target(term, 10)
        self.assertTrue(result.completed)
        self.assertTrue(alpha_equivalent(result.value, I))

    def test_budget_boundary_I_zero_budget(self):
        I = Lam("x", Var("x"))
        result = eval_target(I, 0)
        self.assertTrue(result.completed)
        self.assertEqual(result.steps, 0)

    def test_budget_boundary_II_zero_budget_exhausts(self):
        I = Lam("x", Var("x"))
        result = eval_target(App(I, I), 0)
        self.assertFalse(result.completed)
        self.assertEqual(result.steps, 0)

    def test_budget_boundary_II_one_budget_completes(self):
        I = Lam("x", Var("x"))
        result = eval_target(App(I, I), 1)
        self.assertTrue(result.completed)
        self.assertEqual(result.steps, 1)
        self.assertTrue(alpha_equivalent(result.value, I))

    def test_deterministic_and_input_unchanged(self):
        I = Lam("x", Var("x"))
        term = App(App(I, I), I)
        snapshot = print_term(term)
        r1 = eval_target(term, 5)
        r2 = eval_target(term, 5)
        self.assertEqual(r1.completed, r2.completed)
        self.assertEqual(r1.steps, r2.steps)
        self.assertEqual(print_term(term), snapshot)

    def test_diverging_term_exhausts_budget(self):
        omega_body = Lam("x", App(Var("x"), Var("x")))
        omega = App(omega_body, omega_body)
        result = eval_target(omega, 50)
        self.assertFalse(result.completed)
        self.assertEqual(result.steps, 50)


if __name__ == "__main__":
    unittest.main()
