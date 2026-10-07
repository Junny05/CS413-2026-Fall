import ast
import multiprocessing
import queue
import textwrap
from dataclasses import dataclass
from enum import Enum

import lambda1 as L

INTERPRET_TIMEOUT_S = 5.0


class Operation(str, Enum):
    LINT = "lint"
    INTERPRET = "interpret"
    TYPECHECK = "typecheck"
    COMPILE = "compile"
    EXECUTE = "execute"


class Status(str, Enum):
    OK = "ok"
    INPUT_ERROR = "input_error"
    LANGUAGE_ERROR = "language_error"
    RUNTIME_ERROR = "runtime_error"
    TIMEOUT = "timeout"
    BACKEND_ERROR = "backend_error"
    NOT_IMPLEMENTED = "not_implemented"


@dataclass(frozen=True)
class Result:
    operation: Operation
    revision: int | None
    status: Status
    message: str
    free_vars: tuple[str, ...] = ()


class ReaderError(ValueError):
    pass


# constructor name -> kinds of its arguments: "exp", "int", "bool", "str"
CONSTRUCTOR_SPECS = {
    "D0Eint": ("int",),
    "D0Ebtf": ("bool",),
    "D0Eop1": ("str", "exp"),
    "D0Eop2": ("str", "exp", "exp"),
    "D0Evar": ("str",),
    "D0Elam": ("str", "exp"),
    "D0Efix": ("str", "str", "exp"),
    "D0Eapp": ("exp", "exp"),
    "D0Eif0": ("exp", "exp", "exp"),
    "D0Elet": ("str", "exp", "exp"),
    "D0Epair": ("exp", "exp"),
    "D0Epfst": ("exp",),
    "D0Epsnd": ("exp",),
}


def read_expression(text: str) -> L.D0E000:
    try:
        tree = ast.parse(textwrap.dedent(text).strip(), mode="eval")
    except SyntaxError as e:
        raise ReaderError(f"Syntax error at line {e.lineno}: {e.msg}") from None
    except (ValueError, RecursionError) as e:
        raise ReaderError(f"Input could not be read: {e}") from None
    try:
        return _build(tree.body)
    except RecursionError:
        raise ReaderError("Expression is nested too deeply") from None


def _build(node: ast.AST) -> L.D0E000:
    if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
        raise ReaderError("Expected a LAMBDA constructor call such as D0Eint(1)")
    name = node.func.id
    if name not in CONSTRUCTOR_SPECS:
        raise ReaderError(f"Unknown constructor {name}")
    if node.keywords:
        raise ReaderError(f"{name} takes positional arguments only")
    kinds = CONSTRUCTOR_SPECS[name]
    if len(node.args) != len(kinds):
        raise ReaderError(f"{name} expects {len(kinds)} argument(s), got {len(node.args)}")
    args = [_convert(arg, kind, name) for arg, kind in zip(node.args, kinds)]
    return getattr(L, name)(*args)


def _convert(node: ast.AST, kind: str, owner: str):
    if kind == "exp":
        return _build(node)
    if kind == "int":
        negative = isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub)
        const = node.operand if negative else node
        if isinstance(const, ast.Constant) and type(const.value) is int:
            return -const.value if negative else const.value
        raise ReaderError(f"{owner} expects an integer literal")
    if kind == "bool":
        if isinstance(node, ast.Constant) and type(node.value) is bool:
            return node.value
        raise ReaderError(f"{owner} expects True or False")
    if isinstance(node, ast.Constant) and type(node.value) is str:
        return node.value
    raise ReaderError(f"{owner} expects a string literal")


def lint(source: str, revision: int) -> Result:
    try:
        expr = read_expression(source)
    except ReaderError as e:
        return Result(Operation.LINT, revision, Status.INPUT_ERROR, str(e))
    free = sorted(L.d0exp_fvset(expr))
    if free:
        names = ", ".join(free)
        return Result(Operation.LINT, revision, Status.LANGUAGE_ERROR,
                      f"Undeclared variable(s): {names}", tuple(free))
    return Result(Operation.LINT, revision, Status.OK, "No free variables found.")


def _contains_error(value) -> bool:
    if type(value) is L.D0V000:
        return True
    if isinstance(value, L.D0Vpair):
        return _contains_error(value.arg1) or _contains_error(value.arg2)
    return False


def _evaluate_worker(expr, out):
    try:
        value = L.d0exp_evaluate(expr, L.ENVnil())
        if _contains_error(value):
            out.put(("runtime", "Evaluation reached an error value"))
        else:
            out.put(("ok", repr(value)))
    except RecursionError:
        out.put(("runtime", "Recursion limit exceeded"))
    except Exception as e:
        out.put(("runtime", f"{type(e).__name__}: {e}"))


def interpret(source: str, revision: int, timeout: float = INTERPRET_TIMEOUT_S) -> Result:
    try:
        expr = read_expression(source)
    except ReaderError as e:
        return Result(Operation.INTERPRET, revision, Status.INPUT_ERROR, str(e))
    ctx = multiprocessing.get_context("spawn")
    out = ctx.Queue()
    proc = ctx.Process(target=_evaluate_worker, args=(expr, out), daemon=True)
    proc.start()
    try:
        kind, text = out.get(timeout=timeout)
    except queue.Empty:
        if proc.is_alive():
            proc.terminate()
            proc.join()
            return Result(Operation.INTERPRET, revision, Status.TIMEOUT,
                          f"Interpretation exceeded {timeout:g} seconds and was stopped.")
        return Result(Operation.INTERPRET, revision, Status.BACKEND_ERROR,
                      f"Interpreter worker exited with code {proc.exitcode}.")
    finally:
        proc.join(timeout=1)
    if kind == "ok":
        return Result(Operation.INTERPRET, revision, Status.OK, text)
    return Result(Operation.INTERPRET, revision, Status.RUNTIME_ERROR, text)


def typecheck(source: str, revision: int) -> Result:
    return Result(Operation.TYPECHECK, revision, Status.NOT_IMPLEMENTED,
                  "Type checking is not yet implemented.")


def compile(source: str, revision: int) -> Result:
    return Result(Operation.COMPILE, revision, Status.NOT_IMPLEMENTED,
                  "Compilation is not yet implemented.")


def execute(artifact, revision: int) -> Result:
    return Result(Operation.EXECUTE, revision, Status.NOT_IMPLEMENTED,
                  "Execute runs generated code produced by Compile. No compiled "
                  "artifact exists yet, so Execute is unavailable.")
