# Assignment 5 — Pretty Printing and Capture-Avoiding Substitution

## Python version

Python 3.12 or later (tested with CPython 3.13.11).

## Setup

From the `assigns/05` directory (one level above `MySolution/`):

```sh
python3 -m pip install --user pytest
```

No other dependencies are required.

## Running the tests

Both commands are run from the `assigns/05` directory.

**unittest suite:**

```sh
python3 -m unittest MySolution.test_unittest -v
```

**pytest suite:**

```sh
python3 -m pytest MySolution/test_pytest.py -v
```

## Files

- `pretty_print.py` — `PrettyPrintVisitor` and `d0exp_pretty`.
- `substitution.py` — `NameCollectorVisitor`, `SubstitutionVisitor`, and
  `d0exp_substitute`.
- `test_unittest.py` — `unittest.TestCase`-based suite.
- `test_pytest.py` — pytest-style suite using plain `assert`.

## Examples

```python
from pretty_print import d0exp_pretty
from substitution import d0exp_substitute
from lambda1_vp import D0Eapp, D0Elam, D0Eop2, D0Evar, D0Eint

expr = D0Eapp(D0Elam("x", D0Eop2("+", D0Evar("x"), D0Eint(1))), D0Eint(4))
d0exp_pretty(expr)
# "((lam x. (x + 1)) 4)"

captured = D0Elam("y", D0Eop2("+", D0Evar("x"), D0Evar("y")))
result = d0exp_substitute(captured, "x", D0Evar("y"))
d0exp_pretty(result)
# "(lam y_1. (y + y_1))"   -- the free y in the replacement is not captured
```

## Fresh-name policy

Fresh names are generated deterministically as `f"{base}_{n}"`, for the
smallest positive integer `n` such that the candidate is not already in a
shared `avoid` set. Before any renaming happens for a top-level call to
`d0exp_substitute`, `avoid` is seeded with:

- every variable and binder name occurring anywhere in the original
  expression (collected by `NameCollectorVisitor`, which — unlike
  `FreeVariableVisitor` — also records *bound* names);
- every name occurring anywhere in the replacement expression;
- the substitution target itself.

Every fresh name actually generated during that call is added to `avoid`
immediately, so later renamings — including renamings nested inside the
first one's body, and renamings triggered by sibling binders — can never
collide with each other or with anything already present. The same `avoid`
set object is threaded through every recursive `SubstitutionVisitor`
instance created during one call (including the ones used purely to carry
out a rename), which is what makes this guarantee hold recursively.

Renaming is only performed when it is actually needed: a binder is left
untouched whenever the substitution target does not occur free in its body,
or whenever the binder's name does not occur free in the replacement.

## Known limitations

- Fresh names are generated per top-level `d0exp_substitute` call; two
  separate calls may reuse the same fresh name, which is fine because
  results are only required to be correct and alpha-equivalent, not
  globally unique across calls.
- No parser or web interface is provided, per the assignment's scope.

## Reflection/ Design explanation (visitor design)

Both operations are written only through the supplied `D0ExpVisitor` interface, dispatching through each expression's `accept` method. Neither one evaluates its input.

**Result types.** `D0ExpVisitor` is generic in its result type `R`, so each operation just picks a different `R`. `PrettyPrintVisitor` is a `D0ExpVisitor[str]`: each `visit_*` method returns a string built from the pretty-printed children, following the exact format table in the assignment. `SubstitutionVisitor` is a `D0ExpVisitor[d0exp]`: each `visit_*` method returns an expression, either a brand-new node or a reused one. `NameCollectorVisitor` is a small helper that returns a `frozenset[str]` of names. It works like the supplied `FreeVariableVisitor`, except that it also records bound names, and I use it to seed the fresh-name policy. I made one visitor class per operation instead of one visitor with a mode flag, so each operation's logic and result type stay self-contained.

**Carrying context.** Pretty-printing is a simple bottom-up fold, but substitution is not. What happens at a node depends on information from above (the target variable and the replacement expression) as well as information from below (whether the target occurs free in a subtree, and which names occur anywhere). I store the downward part as constructor arguments on `SubstitutionVisitor`: the `target`, the `replacement`, and a shared `avoid` set of names that fresh variables must not reuse. This is the same pattern `EvaluateVisitor` uses for its environment. When I enter a binder's scope that needs renaming, I create a new visitor instance with updated values. For forms that don't bind anything, I just reuse `self`. This also keeps the `visit_*` signatures simple, since I don't have to thread extra parameters through every method.

**Respecting scope.** Renaming a binder is done by substitution: to rename `old` to a fresh `new`, I run `SubstitutionVisitor(old, D0Evar(new), avoid)` over the binder's body. Since `new` is fresh, nothing can be captured. Since this reuses the same binder logic as normal substitution, an inner binder that shadows `old` (for example, an inner `lam old. ...`) is skipped automatically, which is what lexical scoping requires. I don't need a separate rename visitor that could drift out of sync with the real one.

**New operation vs. new constructor.** Adding a new operation is purely additive. `PrettyPrintVisitor` and `SubstitutionVisitor` are new subclasses of `D0ExpVisitor`, and nothing in `lambda1_vp.py` had to change, including the expression classes, `FreeVariableVisitor`, and `EvaluateVisitor`. Adding a new expression constructor is harder, because every existing visitor must get a new abstract `visit_*` method, and the abstract base class forces each one to stay complete. The Visitor pattern makes new operations easy and new constructors costly, and this assignment asks us to extend along the easy axis.