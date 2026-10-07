import pytest

import lambda1 as L
import lambda_backend as B
from lambda_backend import Operation, Status
from samples import FACTORIAL, FIBONACCI, FIBONACCI_SLOW


def var(name):
    return L.D0Evar(name)


def fv(expr):
    return L.d0exp_fvset(expr)


# Free-variable analysis

def test_fvset_returns_frozenset():
    assert isinstance(fv(L.D0Eint(1)), frozenset)


@pytest.mark.parametrize("expr", [L.D0Eint(1), L.D0Ebtf(True)])
def test_fvset_literals_are_closed(expr):
    assert fv(expr) == frozenset()


def test_fvset_variable():
    assert fv(var("x")) == {"x"}


def test_fvset_unary_and_binary_ops():
    assert fv(L.D0Eop1("+1", var("a"))) == {"a"}
    assert fv(L.D0Eop2("+", var("a"), var("b"))) == {"a", "b"}


def test_fvset_duplicate_occurrences_collapse():
    assert fv(L.D0Eop2("+", var("x"), var("x"))) == {"x"}


def test_fvset_lambda_binds_parameter():
    assert fv(L.D0Elam("x", L.D0Eop2("+", var("x"), var("y")))) == {"y"}


def test_fvset_application_and_conditional_traverse_all_parts():
    expr = L.D0Eif0(var("a"), L.D0Eapp(var("b"), var("c")), var("d"))
    assert fv(expr) == {"a", "b", "c", "d"}


def test_fvset_both_conditional_branches_are_checked():
    expr = L.D0Eif0(L.D0Ebtf(True), var("then_branch"), var("else_branch"))
    assert fv(expr) == {"then_branch", "else_branch"}


def test_fvset_pairs_and_projections():
    expr = L.D0Epair(var("p"), L.D0Epfst(var("q")))
    assert fv(expr) == {"p", "q"}
    assert fv(L.D0Epsnd(var("r"))) == {"r"}


def test_fvset_let_initializer_does_not_see_its_own_name():
    expr = L.D0Elet("x", var("x"), var("x"))
    assert fv(expr) == {"x"}
    assert fv(L.D0Elet("x", L.D0Eint(1), var("x"))) == frozenset()


def test_fvset_let_binds_name_in_body():
    expr = L.D0Elet("x", L.D0Eint(1), L.D0Eop2("+", var("x"), var("y")))
    assert fv(expr) == {"y"}


def test_fvset_recursive_function_binds_name_and_parameter():
    expr = L.D0Efix("f", "n", L.D0Eapp(var("f"), var("n")))
    assert fv(expr) == frozenset()


def test_fvset_recursive_function_leaves_other_names_free():
    expr = L.D0Efix("f", "n", L.D0Eapp(var("g"), var("m")))
    assert fv(expr) == {"g", "m"}


def test_fvset_nested_bindings_shadow_correctly():
    inner = L.D0Elam("x", L.D0Eop2("+", var("x"), var("y")))
    expr = L.D0Elam("y", L.D0Eapp(inner, var("y")))
    assert fv(expr) == frozenset()


# Reader

def test_reader_accepts_comments_and_multiline_nested_input():
    expr = B.read_expression("""
        # a comment
        D0Eop2("+",
               D0Eint(20),   # inline comment
               D0Eint(22))
    """)
    assert expr == L.D0Eop2("+", L.D0Eint(20), L.D0Eint(22))


def test_reader_accepts_negative_integers():
    assert B.read_expression("D0Eint(-3)") == L.D0Eint(-3)


@pytest.mark.parametrize("text, fragment", [
    ("D0Eint(", "Syntax error"),
    ("__import__('os')", "Unknown constructor"),
    ("D0Eint(1, 2)", "expects 1 argument"),
    ("D0Eint(x=1)", "positional arguments only"),
    ("D0Eint('1')", "integer literal"),
    ("D0Eint(True)", "integer literal"),
    ("D0Ebtf(1)", "True or False"),
    ("D0Evar(1)", "string literal"),
    ("D0Eapp(D0Eint(1), D0Eint(2)).x", "Expected a LAMBDA constructor"),
    ("1 + 2", "Expected a LAMBDA constructor"),
    ("D0Eint(1) if True else 0", "Expected a LAMBDA constructor"),
    ("D0Eint(1)\x00", "null bytes"),
    ("D0Eint(D0Eint(1))", "integer literal"),
])
def test_reader_rejects_malformed_input(text, fragment):
    with pytest.raises(B.ReaderError, match=fragment):
        B.read_expression(text)


def test_reader_does_not_execute_arbitrary_code():
    with pytest.raises(B.ReaderError):
        B.read_expression("__import__('os').system('echo unsafe')")


def test_constructor_specs_match_lambda1_fields():
    for name, kinds in B.CONSTRUCTOR_SPECS.items():
        cls = getattr(L, name)
        assert len(cls.__dataclass_fields__) == len(kinds), name


# Lint

def test_lint_closed_program_passes():
    result = B.lint(FACTORIAL, revision=1)
    assert result.status is Status.OK
    assert result.operation is Operation.LINT
    assert result.revision == 1
    assert result.free_vars == ()


def test_lint_open_program_lists_names_in_sorted_order():
    result = B.lint('D0Eop2("+", D0Evar("zeta"), D0Evar("alpha"))', revision=2)
    assert result.status is Status.LANGUAGE_ERROR
    assert result.free_vars == ("alpha", "zeta")
    assert "alpha, zeta" in result.message


def test_lint_reports_free_variable_after_binding_is_out_of_scope():
    result = B.lint('D0Eop2("+", D0Elet("x", D0Eint(1), D0Evar("x")), D0Evar("x"))', revision=1)
    assert result.free_vars == ("x",)


def test_lint_does_not_evaluate_closed_program_that_would_fail():
    result = B.lint('D0Eop2("/", D0Eint(1), D0Eint(0))', revision=1)
    assert result.status is Status.OK


def test_lint_reports_input_error_for_malformed_source():
    result = B.lint("D0Eint(", revision=1)
    assert result.status is Status.INPUT_ERROR


# Interpret

def test_interpret_arithmetic():
    result = B.interpret('D0Eop2("+", D0Eint(20), D0Eint(22))', revision=3)
    assert result.status is Status.OK
    assert result.operation is Operation.INTERPRET
    assert result.revision == 3
    assert result.message == "D0Vint(arg1=42)"


def test_interpret_factorial():
    assert B.interpret(FACTORIAL, revision=1).message == "D0Vint(arg1=120)"


def test_interpret_factorial_base_case():
    expr = FACTORIAL.replace("D0Eint(5))", "D0Eint(0))")
    assert B.interpret(expr, revision=1).message == "D0Vint(arg1=1)"


def test_interpret_fibonacci():
    assert B.interpret(FIBONACCI, revision=1).message == "D0Vint(arg1=55)"


def test_interpret_fibonacci_base_cases():
    assert B.interpret(FIBONACCI.replace("D0Eint(10))", "D0Eint(0))"), 1).message == "D0Vint(arg1=0)"
    assert B.interpret(FIBONACCI.replace("D0Eint(10))", "D0Eint(1))"), 1).message == "D0Vint(arg1=1)"


def test_interpret_division_by_zero_is_runtime_error_not_input_error():
    result = B.interpret('D0Eop2("/", D0Eint(1), D0Eint(0))', revision=1)
    assert result.status is Status.RUNTIME_ERROR
    assert "ZeroDivisionError" in result.message


def test_interpret_type_mismatch_is_runtime_error():
    result = B.interpret("D0Epfst(D0Eint(1))", revision=1)
    assert result.status is Status.RUNTIME_ERROR


def test_interpret_unbound_variable_is_runtime_error():
    result = B.interpret('D0Evar("x")', revision=1)
    assert result.status is Status.RUNTIME_ERROR


def test_interpret_malformed_input_is_input_error():
    result = B.interpret("D0Eint(", revision=1)
    assert result.status is Status.INPUT_ERROR


def test_interpret_timeout_stops_nonterminating_work():
    result = B.interpret(FIBONACCI_SLOW, revision=1, timeout=0.3)
    assert result.status is Status.TIMEOUT
    assert result.operation is Operation.INTERPRET


def test_interpret_succeeds_after_timeout():
    assert B.interpret(FIBONACCI_SLOW, revision=1, timeout=0.3).status is Status.TIMEOUT
    assert B.interpret(FACTORIAL, revision=2).status is Status.OK


def test_error_sentinel_inside_pair_is_error():
    assert B._contains_error(L.D0Vpair(L.D0Vint(1), L.D0V000()))
    assert B._contains_error(L.D0V000())
    assert not B._contains_error(L.D0Vpair(L.D0Vint(1), L.D0Vint(2)))


# Placeholders and dispatch

def test_typecheck_is_not_reported_as_success():
    result = B.typecheck(FACTORIAL, revision=4)
    assert result.status is Status.NOT_IMPLEMENTED
    assert result.operation is Operation.TYPECHECK
    assert "not yet implemented" in result.message


def test_compile_is_not_reported_as_success():
    result = B.compile(FACTORIAL, revision=4)
    assert result.status is Status.NOT_IMPLEMENTED
    assert result.operation is Operation.COMPILE
    assert "not yet implemented" in result.message


def test_execute_without_artifact_is_not_implemented():
    result = B.execute(None, revision=4)
    assert result.status is Status.NOT_IMPLEMENTED
    assert result.operation is Operation.EXECUTE
    assert "Compile" in result.message
