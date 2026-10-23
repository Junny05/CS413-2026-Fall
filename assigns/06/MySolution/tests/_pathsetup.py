import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_MYSOLUTION = os.path.join(_HERE, "..")
_ASSIGN05 = os.path.join(_HERE, "..", "..", "..", "05")
for p in (_MYSOLUTION, _ASSIGN05):
    if p not in sys.path:
        sys.path.insert(0, p)
