# DESIGN

## Translation rules

`C[e]` denotes the compiled target term for source expression `e`. All
rules below are implemented in `compiler.py`'s `_CompileVisitor`, one
method per source constructor, dispatched through `D0ExpVisitor`.

```
C[n]                    = NUM(n)                         (n >= 0)
C[true]                  = TRUE
C[false]                 = FALSE
C[x]                     = x
C[lam x. e]              = lam x. C[e]
C[e1 e2]                 = C[e1] C[e2]
C[not e]                  = NOT C[e]
C[e1 op e2]               = OP C[e1] C[e2]        op in {+,-,*,<,<=,>,>=,==,!=}
C[e1 and e2]              = (C[e1] (lam u. C[e2]) (lam v. FALSE)) I
C[e1 or e2]                = (C[e1] (lam u. TRUE) (lam v. C[e2])) I
C[if c then t else f]    = (C[c] (lam u. C[t]) (lam v. C[f])) I
C[let x = e1 in e2]      = (lam x. C[e2]) C[e1]
C[pair e1 e2]              = PAIR C[e1] C[e2]
C[fst e]                  = FST C[e]
C[snd e]                  = SND C[e]
C[fix f(x). e]            = Z (lam f. lam x. C[e])
```

`I`, `NOT`, `TRUE`, `FALSE`, `PAIR`, `FST`, `SND`, `Z`, and `OP` are the
closed library terms of `church_encodings.py`, already pure `Var`/`Lam`/
`App` values; no separate expansion step is needed, since they were never
anything but pure terms. `u` and `v` are freshly chosen, unused thunk
parameters (see "Freshness policy" below). These rules are compositional:
each clause translates only the immediate subexpressions and combines the
results; no rule inspects a subexpression's *value*, so a non-terminating
subexpression still compiles (`compiler.py` never calls `reducer.py` or
`evaluator.py`).

## Predecessor construction

`PRED` uses the standard "shift-and-drop" pair trick, since there is no
direct Church encoding of decrement. Define a step function
`STEPFN(q) = PAIR (SND q) (SUCC (SND q))`, and seed a pair with
`(ZERO, ZERO)`. Applying `STEPFN` to a seed pair `(a, b)` produces
`(b, b+1)`; so after `k` applications starting from `(0, 0)`, the pair
holds `(k - 1, k)` for `k >= 1`, and remains `(0, 0)` for `k = 0` (zero
applications are performed). `PRED(n) = FST (n STEPFN (PAIR ZERO ZERO))`
applies `STEPFN` exactly `n` times (using the Church numeral `n` itself
as the iterator) and takes the first component, giving `n - 1` for
`n >= 1` and `0` for `n = 0` -- exactly the required "predecessor of zero
is zero" behavior, obtained for free from the seed rather than from a
special case.

## Freshness policy

`target_ast.FreshNamer` holds one monotonically increasing counter, never
reset within a compilation. `fresh(avoid, prefix)` tries
`f"{prefix}{counter}"`, increments the counter, and repeats until the
candidate is not in the caller-supplied `avoid` set. This is deterministic
(the same sequence of calls, with the same `avoid` sets, always returns
the same names) and reserves nothing a priori: an ordinary source
identifier like `s`, `z`, `t`, `f`, or `x` is only ever skipped if it is
actually present in the specific `avoid` set checked at that call site.

Two call sites use it. (1) `substitute`'s capture-avoiding rename, when a
`Lam`'s bound parameter would otherwise be captured by a substituted
replacement term; there, `avoid` is the union of the replacement's free
variables, the lambda body's free variables, and the two names already in
play, which is exactly the set that must not include the fresh parameter.
(2) The compiler's delayed-branch helper (`if`/`and`/`or`), which needs `u`
not free in the "then" branch and `v` not free in the "else" branch -- so
`avoid` is `free_vars` of that specific compiled branch term, computed
directly from the already-built target subterm rather than from any
whole-program approximation, which would otherwise be either unsafe (too
small, if a locally-free name is not globally free) or merely wasteful (too
large).

## Evaluation strategy

One evaluator module (`evaluator.py`) serves both languages. `evaluate_source`
implements the source semantics directly: left-to-right call-by-value,
`if0` testing a boolean (not numeric zero, despite the name), truncated
subtraction via `max(m - n, 0)`, and short-circuiting `and`/`or` that
evaluates the right operand only when needed. It is unbounded, used only
as the oracle for terminating examples. `evaluate_target` operates
exclusively on `Var`/`Lam`/`App` and is implemented by `reducer.eval_target`:
a weak (no reduction under a `Lam`), left-to-right call-by-value small-step
reducer, implemented iteratively with an explicit control stack rather than
recursively, so that step budgets in the thousands do not approach Python's
recursion limit. It accepts a nonnegative step budget, performs no more
beta-value steps than that, and reports completion (with the resulting
value and the exact step count, zero for an already-irreducible term) or
exhaustion (another step was needed, but the budget was spent).

Delayed branches are why `if`/`and`/`or` need the `(lam u. ...) (lam v.
...) I` shape rather than plain arguments: the target's call-by-value
semantics evaluates *both* arguments of an application before substituting
either into the selector's body, so passing `C[t]` and `C[f]` directly
would force both branches unconditionally, including a divergent
unselected branch. Wrapping each branch in a thunk (`lam u. C[t]`) delays
its evaluation to argument-position *construction* time (building a
`Lam` value, which is cheap and never diverges) rather than its *body*
evaluation time; only the branch selected by `C[c]`'s own Church-boolean
application is then forced, by applying it to the harmless dummy `I`.
`Z` is required instead of the textbook `Y` combinator for the same
underlying reason: ordinary `Y = lam g. (lam x. g (x x)) (lam x. g (x x))`
immediately self-applies `x x` as soon as `Y g`'s body is entered, which
diverges under call-by-value before `g` is ever given a chance to return a
value; `Z` instead wraps the self-application in `lam v. x x v`, a value,
so it is only forced when (and if) the eventual recursive call actually
supplies an argument.

## Correctness claim and its limits

Claim: for a closed, well-typed program in the source language above that
produces a natural number, a boolean, or a finite pair of such results,
observing the compiled term's result (via `observe_nat`/`observe_bool`/
`observe_pair`, applied recursively for nested pairs) under a sufficiently
large execution and observation budget yields the same data as evaluating
the source program directly with `evaluate_source`.

The argument proceeds by structural induction on the translation rules.
Each rule preserves both the *result* and the *free-variable set*
(`FV(C[e]) = FV(e)`, verified for every binding form in `tests/test_compiler.py`'s
`ScopeTests`): application and `let` reduce to ordinary substitution,
which both calculi share; `if`/`and`/`or` preserve meaning because the
selected Church boolean always applies its first argument to select the
"then"/true thunk and its second to select the "else"/false thunk, and
forcing only the selected thunk with `I` reproduces exactly the source's
"evaluate only the selected branch" rule; `fix` preserves meaning because
`Z g` behaves, up to the number of unfoldings actually demanded, like a
fixed point of `g`, matching the source's lazy (call-by-need-free,
call-by-value-safe) recursive unfolding.

Testing, however, cannot establish this claim in general: a finite test
suite checks finitely many inputs and budgets, while the claim is
universally quantified over source programs and requires reduction
resources whose sufficiency is only an empirical observation for the
tested cases, not a proven bound. A full proof would need a logical
relation between source values and target terms (showing, e.g., that
every closed source natural's compiled form reduces to some `NUM(n)` for
the matching `n`, by induction on reduction length) together with an
adequacy argument connecting target-value termination to source-value
termination; that is substantially more work than the structural argument
above and is explicitly not required here.

## Tradeoffs

The reducer is a plain tree-walking interpreter with capture-avoiding
substitution performed by full term reconstruction on every beta step,
which is simple to verify but not scaled for large programs (each
factorial(4) run performs several hundred substitution passes over
progressively larger terms). An environment/closure-based reducer, or
explicit sharing of substituted subterms, would reduce this asymptotic
cost but would also move the implementation further from the literal
"beta-value step on `Var`/`Lam`/`App`" model the assignment asks the
tests to exercise directly, so the simpler model was kept.
