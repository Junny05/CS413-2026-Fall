#!/usr/bin/env python3
import sys

N = 8

# A board is represented as an 8-tuple of ints, one column index per row
# (mirrors the [int8] tuple type in the original .dats source).

def print_dots(i: int) -> None:
    if i > 0:
        print(". ", end="")
        print_dots(i - 1)
    # end of [if]
# end of [print_dots]

def print_row(i: int) -> None:
    print_dots(i)
    print("Q ", end="")
    print_dots(N - i - 1)
    print()
# end of [print_row]

def print_board(bd) -> None:
    for i in range(8):
        print_row(bd[i])
    print()
# end of [print_board]

def board_get(bd, i: int) -> int:
    if 0 <= i <= 7:
        return bd[i]
    else:
        return -1
    # end of [if]
# end of [board_get]

def board_set(bd, i: int, j: int):
    if 0 <= i <= 7:
        return bd[:i] + (j,) + bd[i + 1:]
    else:
        return bd
    # end of [if]
# end of [board_set]

def safety_test1(i0: int, j0: int, i1: int, j1: int) -> bool:
    return j0 != j1 and abs(i0 - i1) != abs(j0 - j1)
# end of [safety_test1]

def safety_test2(i0: int, j0: int, bd, i: int) -> bool:
    if i >= 0:
        if safety_test1(i0, j0, i, board_get(bd, i)):
            return safety_test2(i0, j0, bd, i - 1)
        else:
            return False
        # end of [if]
    else:
        return True
    # end of [if]
# end of [safety_test2]

def search(bd, i: int, j: int, nsol: int) -> int:
    # Every recursive call in the original [search] is in tail position,
    # so it is written here as a loop instead of Python recursion (Python
    # has no tail-call optimization, and the .dats version relies on it).
    while True:
        if j < N:
            test = safety_test2(i, j, bd, i - 1)
            if test:
                bd1 = board_set(bd, i, j)
                if i + 1 == N:
                    print("Solution #", nsol + 1, ":\n", sep="")
                    print_board(bd1)
                    j, nsol = j + 1, nsol + 1
                    continue
                else:
                    # positioning next piece
                    bd, i, j = bd1, i + 1, 0
                    continue
                # end of [if]
            else:
                j = j + 1
                continue
            # end of [if]
        else:
            if i > 0:
                j = board_get(bd, i - 1) + 1
                i = i - 1
                continue
            else:
                return nsol
            # end of [if]
        # end of [if]
    # end of [while]
# end of [search]

def main() -> None:
    sys.setrecursionlimit(10000)
    bd0 = (0, 0, 0, 0, 0, 0, 0, 0)
    search(bd0, 0, 0, 0)

    # board_get
    print(board_get(bd0,7))
    print(board_get(bd0,3))
    print(board_get(bd0,1))
    print(board_get(bd0,-1))

    # board_set
    print(board_set(bd0, -1, 8))
    print(board_set(bd0, 2, 3))
    print(board_set(bd0, 0, 1))
    print(board_set(bd0, 4, 7))

    # safety_test1
    print(safety_test1(0,0,1,1))
    print(safety_test1(0,0,1,2))
    print(safety_test1(0,0,0,0))
    print(safety_test1(0,0,7,7))
    print(safety_test1(0,7,7,0))
    print(safety_test1(0,0,7,1))

    # safety_test2
    print(safety_test2(3,6,bd0,2))
    print(safety_test2(3,0,bd0,2))
    
# end of [main]

if __name__ == "__main__":
    main()
