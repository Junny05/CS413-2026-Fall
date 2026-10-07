# Canned LAMBDA constructor expressions loaded by the Load source menu.

FACTORIAL = """\
# factorial 5
D0Eapp(
  D0Efix("fact", "n",
    D0Eif0(D0Eop2("==", D0Evar("n"), D0Eint(0)),
           D0Eint(1),
           D0Eop2("*", D0Evar("n"),
                  D0Eapp(D0Evar("fact"), D0Eop2("-", D0Evar("n"), D0Eint(1)))))),
  D0Eint(5))
"""

FIBONACCI = """\
# fibonacci 10
D0Eapp(
  D0Efix("fib", "n",
    D0Eif0(D0Eop2("<", D0Evar("n"), D0Eint(2)),
           D0Evar("n"),
           D0Eop2("+",
                  D0Eapp(D0Evar("fib"), D0Eop2("-", D0Evar("n"), D0Eint(1))),
                  D0Eapp(D0Evar("fib"), D0Eop2("-", D0Evar("n"), D0Eint(2)))))),
  D0Eint(10))
"""

FIBONACCI_SLOW = FIBONACCI.replace("D0Eint(10))", "D0Eint(32))")
