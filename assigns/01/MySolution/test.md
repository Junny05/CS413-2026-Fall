**`board_get(bd, i)`**
- In-range indices (0, 3, 7) return the correct column value.
- Out-of-range indices (-1, 8) return -1.

**`board_set(bd, i, j)`**
- Setting an in-range index returns a new tuple with that index updated.
- Out-of-range indices (-1, 8) return the board unchanged.

**`safety_test1(i0, j0, i1, j1)`**
- False   # (0,0) vs (1,1) — unsafe
- True    # (0,0) vs (1,2) — safe
- False   # (0,0) vs (0,0) — unsafe
- False   # (0,0) vs (7,7) — unsafe
- False   # (0,7) vs (7,0) — unsafe
- True    # (0,0) vs (7,1) — safe

**`safety_test2(i0, j0, bd, i)`**
- (3, 6) checked against queens at rows 0-2 (cols 0,2,4) - True
- (3, 0) checked against same queens - False 


