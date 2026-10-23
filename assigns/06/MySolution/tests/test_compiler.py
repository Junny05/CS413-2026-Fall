"""Task 3 tests: compositional compiler coverage. Testing obligations
4, 5, 6, 7 (scope/shadowing/fix binders/open expressions/FV preservation,
divergence skipping under if/and/or and forced-but-unused divergence,
every source constructor and operator, rejection of bad literals/ops,
structural purity, and that compilation never calls the evaluator)."""

import unittest

from . import _pathsetup  # noqa: F401
from lambda1_vp import (
    D0Eapp, D0Ebtf, D0Eif0, D0Eint, D0Elam, D0Elet, D0Eop1, D0Eop2,
    D0Epair, D0Epfst, D0Epsnd, D0Evar, D0Efix, d0exp_fvset,
)
from compiler import compile_expr, CompileError
from target_ast import App, Lam, Term, Var, free_vars, print_term
from reducer import eval_target
from observers import observe_nat, observe_bool

BUDGET = 50_000


def run_nat(source):
    r = eval_target(compile_expr(source), BUDGET)
    assert r.completed, r
    return observe_nat(r.value, BUDGET).value


def run_bool(source):
    r = eval_target(compile_expr(source), BUDGET)
    assert r.completed, r
    return observe_bool(r.value, BUDGET).value


def is_exhausted(source, budget=5000):
    r = eval_target(compile_expr(source), budget)
    return not r.completed


LOOP = D0Eapp(D0Efix("loop", "x", D0Eapp(D0Evar("loop"), D0Evar("x"))), D0Eint(0))


def _assert_pure(term: Term) -> None:
    if isinstance(term, Var):
        return
    if isinstance(term, Lam):
        _assert_pure(term.body)
        return
    if isinstance(term, App):
        _assert_pure(term.fn)
        _assert_pure(term.arg)
        return
    raise AssertionError(f"not a pure Var/Lam/App node: {term!r}")


class EveryConstructorTests(unittest.TestCase):
    def test_int(self):
        self.assertEqual(run_nat(D0Eint(5)), 5)

    def test_btf_true_false(self):
        self.assertEqual(run_bool(D0Ebtf(True)), True)
        self.assertEqual(run_bool(D0Ebtf(False)), False)

    def test_var_and_lam_and_app(self):
        e = D0Eapp(D0Elam("x", D0Eop2("+", D0Evar("x"), D0Eint(1))), D0Eint(9))
        self.assertEqual(run_nat(e), 10)

    def test_not(self):
        self.assertEqual(run_bool(D0Eop1("not", D0Ebtf(True))), False)

    def test_all_binary_nat_ops(self):
        self.assertEqual(run_nat(D0Eop2("+", D0Eint(2), D0Eint(3))), 5)
        self.assertEqual(run_nat(D0Eop2("-", D0Eint(2), D0Eint(3))), 0)
        self.assertEqual(run_nat(D0Eop2("*", D0Eint(2), D0Eint(3))), 6)
        self.assertEqual(run_bool(D0Eop2("<", D0Eint(2), D0Eint(3))), True)
        self.assertEqual(run_bool(D0Eop2("<=", D0Eint(3), D0Eint(3))), True)
        self.assertEqual(run_bool(D0Eop2(">", D0Eint(3), D0Eint(2))), True)
        self.assertEqual(run_bool(D0Eop2(">=", D0Eint(3), D0Eint(3))), True)
        self.assertEqual(run_bool(D0Eop2("==", D0Eint(3), D0Eint(3))), True)
        self.assertEqual(run_bool(D0Eop2("!=", D0Eint(3), D0Eint(4))), True)

    def test_and_or(self):
        self.assertEqual(run_bool(D0Eop2("and", D0Ebtf(True), D0Ebtf(True))), True)
        self.assertEqual(run_bool(D0Eop2("or", D0Ebtf(False), D0Ebtf(False))), False)

    def test_and_full_truth_table(self):
        for a in (True, False):
            for b in (True, False):
                with self.subTest(a=a, b=b):
                    self.assertEqual(
                        run_bool(D0Eop2("and", D0Ebtf(a), D0Ebtf(b))), a and b
                    )

    def test_or_full_truth_table(self):
        for a in (True, False):
            for b in (True, False):
                with self.subTest(a=a, b=b):
                    self.assertEqual(
                        run_bool(D0Eop2("or", D0Ebtf(a), D0Ebtf(b))), a or b
                    )

    def test_if0(self):
        self.assertEqual(run_nat(D0Eif0(D0Ebtf(True), D0Eint(1), D0Eint(2))), 1)
        self.assertEqual(run_nat(D0Eif0(D0Ebtf(False), D0Eint(1), D0Eint(2))), 2)

    def test_let(self):
        e = D0Elet("x", D0Eint(5), D0Eop2("+", D0Evar("x"), D0Eint(1)))
        self.assertEqual(run_nat(e), 6)

    def test_pair_fst_snd(self):
        p = D0Epair(D0Eint(3), D0Ebtf(False))
        self.assertEqual(run_nat(D0Epfst(p)), 3)
        self.assertEqual(run_bool(D0Epsnd(p)), False)

    def test_fix(self):
        fact = D0Efix(
            "f", "n",
            D0Eif0(D0Eop2("==", D0Evar("n"), D0Eint(0)), D0Eint(1),
                   D0Eop2("*", D0Evar("n"), D0Eapp(D0Evar("f"), D0Eop2("-", D0Evar("n"), D0Eint(1))))),
        )
        self.assertEqual(run_nat(D0Eapp(fact, D0Eint(5))), 120)


class ScopeTests(unittest.TestCase):
    def test_nested_shadowing_lambda(self):
        e = D0Elam("x", D0Elam("x", D0Evar("x")))
        e = D0Eapp(D0Eapp(e, D0Eint(1)), D0Eint(2))
        self.assertEqual(run_nat(e), 2)

    def test_nested_let_shadowing(self):
        e = D0Elet("x", D0Eint(1), D0Elet("x", D0Eint(2), D0Evar("x")))
        self.assertEqual(run_nat(e), 2)

    def test_let_initializer_not_in_scope_of_its_own_name(self):
        # let x = x in x, with x free in the initializer only.
        e = D0Elet("x", D0Evar("x"), D0Evar("x"))
        term = compile_expr(e)
        self.assertEqual(free_vars(term), frozenset({"x"}))

    def test_fix_binders_distinct(self):
        e = D0Efix("f", "x", D0Eif0(D0Eop2("==", D0Evar("x"), D0Eint(0)), D0Eint(0),
                                     D0Eapp(D0Evar("f"), D0Eop2("-", D0Evar("x"), D0Eint(1)))))
        self.assertEqual(run_nat(D0Eapp(e, D0Eint(3))), 0)

    def test_fix_coincident_binders(self):
        # (fix f(f). f) 3 -- the parameter shadows the function name, so
        # the body "f" refers to the parameter, returning 3 unchanged.
        e = D0Eapp(D0Efix("f", "f", D0Evar("f")), D0Eint(3))
        self.assertEqual(run_nat(e), 3)

    def test_open_expression_preserves_free_variables(self):
        for e in [
            D0Evar("s"), D0Evar("z"), D0Evar("t"), D0Evar("f"), D0Evar("x"),
            D0Eop2("+", D0Evar("s"), D0Evar("z")),
            D0Elam("q", D0Eop2("+", D0Evar("q"), D0Evar("s"))),
            D0Eif0(D0Evar("t"), D0Evar("f"), D0Eint(0)),
            D0Efix("f", "x", D0Eop2("+", D0Evar("f"), D0Evar("x"))),
        ]:
            with self.subTest(e=e):
                term = compile_expr(e)
                self.assertEqual(free_vars(term), d0exp_fvset(e))

    def test_names_s_z_t_f_x_available_to_source(self):
        e = D0Elam("s", D0Elam("z", D0Elam("t", D0Elam("f", D0Elam(
            "x", D0Eop2("+", D0Evar("s"), D0Evar("z")))))))
        e = D0Eapp(D0Eapp(D0Eapp(D0Eapp(D0Eapp(e, D0Eint(1)), D0Eint(2)), D0Ebtf(True)),
                          D0Ebtf(False)), D0Eint(0))
        self.assertEqual(run_nat(e), 3)

    def test_if_thunk_does_not_capture_free_var_named_like_thunk_param(self):
        # A branch that is free in a variable the compiler might otherwise
        # pick as its thunk parameter must still be returned unchanged.
        e = D0Eif0(D0Ebtf(True), D0Evar("w"), D0Eint(0))
        term = compile_expr(e)
        self.assertEqual(free_vars(term), frozenset({"w"}))


class DivergenceSkippingTests(unittest.TestCase):
    def test_unselected_if_branch_skipped(self):
        self.assertEqual(run_nat(D0Eif0(D0Ebtf(True), D0Eint(1), LOOP)), 1)
        self.assertEqual(run_nat(D0Eif0(D0Ebtf(False), LOOP, D0Eint(2))), 2)

    def test_short_circuit_and_or_skip_divergence(self):
        self.assertEqual(run_bool(D0Eop2("and", D0Ebtf(False), LOOP)), False)
        self.assertEqual(run_bool(D0Eop2("or", D0Ebtf(True), LOOP)), True)

    def test_let_initializer_divergence_forced_even_if_unused(self):
        self.assertTrue(is_exhausted(D0Elet("x", LOOP, D0Eint(2))))

    def test_pair_component_divergence_forced_even_if_unused(self):
        self.assertTrue(is_exhausted(D0Epfst(D0Epair(D0Eint(2), LOOP))))
        self.assertTrue(is_exhausted(D0Epsnd(D0Epair(LOOP, D0Ebtf(True)))))

    def test_function_argument_divergence_forced(self):
        self.assertTrue(is_exhausted(D0Eapp(D0Elam("x", D0Eint(0)), LOOP)))


class ACC08Tests(unittest.TestCase):
    """Exact ACC-08 verification cases from REQUIREMENTS.md Section 7.2."""

    def test_let_x_equals_loop_in_2_exhausts(self):
        self.assertTrue(is_exhausted(D0Elet("x", LOOP, D0Eint(2))))

    def test_fst_pair_2_loop_exhausts(self):
        self.assertTrue(is_exhausted(D0Epfst(D0Epair(D0Eint(2), LOOP))))

    def test_snd_pair_loop_true_exhausts(self):
        self.assertTrue(is_exhausted(D0Epsnd(D0Epair(LOOP, D0Ebtf(True)))))

    def test_false_and_loop_yields_false(self):
        self.assertEqual(run_bool(D0Eop2("and", D0Ebtf(False), LOOP)), False)

    def test_true_or_loop_yields_true(self):
        self.assertEqual(run_bool(D0Eop2("or", D0Ebtf(True), LOOP)), True)


class RejectionTests(unittest.TestCase):
    def test_negative_literal_rejected(self):
        with self.assertRaises(CompileError):
            compile_expr(D0Eint(-1))

    def test_division_rejected(self):
        with self.assertRaises(CompileError):
            compile_expr(D0Eop2("/", D0Eint(4), D0Eint(2)))

    def test_unsupported_unary_operator_rejected(self):
        with self.assertRaises(CompileError):
            compile_expr(D0Eop1("+1", D0Eint(4)))

    def test_rejected_in_unselected_if_branch(self):
        e = D0Eif0(D0Ebtf(True), D0Eint(1), D0Eint(-1))
        with self.assertRaises(CompileError):
            compile_expr(e)

    def test_rejected_in_unapplied_lambda_body(self):
        e = D0Elam("x", D0Eop2("/", D0Evar("x"), D0Eint(2)))
        with self.assertRaises(CompileError):
            compile_expr(e)

    def test_rejected_inside_fix_body_even_if_never_called(self):
        e = D0Efix("f", "x", D0Eint(-5))
        with self.assertRaises(CompileError):
            compile_expr(e)

    def test_rejected_inside_let_initializer(self):
        e = D0Elet("x", D0Eop2("/", D0Eint(4), D0Eint(2)), D0Eint(1))
        with self.assertRaises(CompileError):
            compile_expr(e)

    def test_rejected_inside_unused_pair_component(self):
        e = D0Epfst(D0Epair(D0Eint(1), D0Eint(-7)))
        with self.assertRaises(CompileError):
            compile_expr(e)

    def test_rejected_unsupported_binary_operator_spelling(self):
        with self.assertRaises(CompileError):
            compile_expr(D0Eop2("%", D0Eint(5), D0Eint(2)))

    def test_rejection_error_identifies_offender(self):
        try:
            compile_expr(D0Eint(-42))
            self.fail("expected CompileError")
        except CompileError as exc:
            self.assertIn("-42", str(exc))
        try:
            compile_expr(D0Eop2("/", D0Eint(1), D0Eint(1)))
            self.fail("expected CompileError")
        except CompileError as exc:
            self.assertIn("/", str(exc))


class StructuralPurityTests(unittest.TestCase):
    def test_output_contains_only_var_lam_app(self):
        fact = D0Efix(
            "f", "n",
            D0Eif0(D0Eop2("==", D0Evar("n"), D0Eint(0)), D0Eint(1),
                   D0Eop2("*", D0Evar("n"), D0Eapp(D0Evar("f"), D0Eop2("-", D0Evar("n"), D0Eint(1))))),
        )
        term = compile_expr(D0Eapp(fact, D0Eint(4)))
        _assert_pure(term)

    def test_input_ast_not_mutated(self):
        e = D0Eop2("+", D0Eint(2), D0Eint(3))
        before = (e.name, e.arg1.arg1, e.arg2.arg1)
        compile_expr(e)
        after = (e.name, e.arg1.arg1, e.arg2.arg1)
        self.assertEqual(before, after)

    def test_input_ast_not_mutated_for_if_let_pair_fix(self):
        import copy

        exprs = [
            D0Eif0(D0Ebtf(True), D0Eint(1), D0Eint(2)),
            D0Elet("x", D0Eint(3), D0Eop2("+", D0Evar("x"), D0Eint(1))),
            D0Epair(D0Eint(1), D0Ebtf(False)),
            D0Efix("f", "n", D0Eif0(D0Eop2("==", D0Evar("n"), D0Eint(0)), D0Eint(1),
                                     D0Eop2("*", D0Evar("n"), D0Eapp(D0Evar("f"),
                                                                      D0Eop2("-", D0Evar("n"), D0Eint(1)))))),
        ]
        for e in exprs:
            with self.subTest(e=type(e).__name__):
                snapshot = copy.deepcopy(e)
                compile_expr(e)
                self.assertEqual(e, snapshot)

    def test_repeated_compilation_is_deterministic(self):
        e = D0Eif0(D0Eop2("and", D0Ebtf(True), D0Ebtf(False)), D0Eint(1), D0Eint(2))
        t1 = compile_expr(e)
        t2 = compile_expr(e)
        self.assertEqual(print_term(t1), print_term(t2))

    def test_compilation_does_not_invoke_the_evaluator(self):
        import reducer
        import evaluator

        def _boom(*args, **kwargs):
            raise AssertionError("compilation invoked the evaluator")

        saved_reducer = reducer.eval_target
        saved_eval_source = evaluator.evaluate_source
        saved_eval_target = evaluator.evaluate_target
        reducer.eval_target = _boom
        evaluator.evaluate_source = _boom
        evaluator.evaluate_target = _boom
        try:
            fact = D0Efix(
                "f", "n",
                D0Eif0(D0Eop2("==", D0Evar("n"), D0Eint(0)), D0Eint(1),
                       D0Eop2("*", D0Evar("n"), D0Eapp(D0Evar("f"), D0Eop2("-", D0Evar("n"), D0Eint(1))))),
            )
            compile_expr(D0Eapp(fact, D0Eint(4)))
            compile_expr(LOOP)
        finally:
            reducer.eval_target = saved_reducer
            evaluator.evaluate_source = saved_eval_source
            evaluator.evaluate_target = saved_eval_target


if __name__ == "__main__":
    unittest.main()
