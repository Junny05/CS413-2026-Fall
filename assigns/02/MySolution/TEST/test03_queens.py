"""Tests for the LAMBDA0 translation of the ATS2 eight-queens solver.

Run with: python3 MySolution/TEST/test03_queens.py
Requires Python 3.12 or later, like lambda0.py.
"""

import itertools
import sys
import unittest
from pathlib import Path

# Allow this file to run directly from any working directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lambda0 import T0Mint, T0Mbtf, T0Mapp, t0erm_cbv_evaluate0
from queens_lambda0 import (
    APP, board_literal, board_to_python, build_queens,
    result_boards, result_count,
)


# A known conflict-free solution to 8-queens (row i's queen is in
# column SOLUTION_8[i]); used to test the translated conflict checks
# against a real solution rather than only synthetic boards.
SOLUTION_8 = [0, 4, 7, 5, 2, 6, 1, 3]

# The number of solutions to the N-queens problem, N = 0..8 (N = 0 and
# N = 1..3 are boundary/small cases; N = 8 is the original problem).
EXPECTED_SOLUTION_COUNTS = {1: 1, 2: 0, 3: 0, 4: 2, 5: 10, 6: 4, 7: 40, 8: 92}


def has_conflict(cols):
    """Reference conflict check over a Python list of columns, used to
    cross-check the translated safety_test1/safety_test2 terms."""
    n = len(cols)
    for i in range(n):
        for j in range(i + 1, n):
            if cols[i] == cols[j] or abs(i - j) == abs(cols[i] - cols[j]):
                return True
    return False


class TestBoardGetSet(unittest.TestCase):
    def setUp(self):
        self.q = build_queens(8)
        self.bd0 = board_literal([0, 1, 2, 3, 4, 5, 6, 7])

    def get(self, i):
        return t0erm_cbv_evaluate0(APP(self.q.board_get, self.bd0, T0Mint(i)))

    def test_in_range_indices(self):
        for i in range(8):
            with self.subTest(i=i):
                self.assertEqual(self.get(i), T0Mint(i))

    def test_out_of_range_indices_return_minus_one(self):
        for i in (-1, 8, 100):
            with self.subTest(i=i):
                self.assertEqual(self.get(i), T0Mint(-1))

    def test_board_set_in_range(self):
        result = t0erm_cbv_evaluate0(
            APP(self.q.board_set, self.bd0, T0Mint(3), T0Mint(9))
        )
        self.assertEqual(board_to_python(result), (0, 1, 2, 9, 4, 5, 6, 7))

    def test_board_set_out_of_range_is_unchanged(self):
        for i in (-1, 8):
            with self.subTest(i=i):
                result = t0erm_cbv_evaluate0(
                    APP(self.q.board_set, self.bd0, T0Mint(i), T0Mint(99))
                )
                self.assertEqual(board_to_python(result), (0, 1, 2, 3, 4, 5, 6, 7))

    def test_board_set_does_not_disturb_other_rows(self):
        result = t0erm_cbv_evaluate0(
            APP(self.q.board_set, self.bd0, T0Mint(0), T0Mint(9))
        )
        self.assertEqual(board_to_python(result), (9, 1, 2, 3, 4, 5, 6, 7))
        result = t0erm_cbv_evaluate0(
            APP(self.q.board_set, self.bd0, T0Mint(7), T0Mint(9))
        )
        self.assertEqual(board_to_python(result), (0, 1, 2, 3, 4, 5, 6, 9))


class TestSafetyChecks(unittest.TestCase):
    def setUp(self):
        self.q = build_queens(8)

    def safety_test1(self, i0, j0, i1, j1):
        term = APP(self.q.safety_test1, T0Mint(i0), T0Mint(j0), T0Mint(i1), T0Mint(j1))
        return t0erm_cbv_evaluate0(term)

    def safety_test2(self, i0, j0, bd_values, i):
        bd = board_literal(bd_values)
        term = APP(self.q.safety_test2, T0Mint(i0), T0Mint(j0), bd, T0Mint(i))
        return t0erm_cbv_evaluate0(term)

    def test_safety_test1_cases(self):
        # Same diagonal, same column, or the same square are all unsafe;
        # same row is never compared by construction, so it is not tested.
        for i0, j0, i1, j1, expected in [
            (0, 0, 1, 1, False),  # diagonal
            (0, 0, 1, 2, True),   # safe
            (0, 0, 0, 0, False),  # same square
            (0, 0, 7, 7, False),  # diagonal
            (0, 7, 7, 0, False),  # diagonal
            (0, 0, 7, 1, True),   # safe
            (2, 5, 4, 5, False),  # same column
        ]:
            with self.subTest(i0=i0, j0=j0, i1=i1, j1=j1):
                self.assertEqual(self.safety_test1(i0, j0, i1, j1), T0Mbtf(expected))

    def test_safety_test2_against_existing_queens(self):
        # Queens already placed at rows 0..2, columns 0, 2, 4.
        bd = [0, 2, 4, 0, 0, 0, 0, 0]
        # Row 3, column 6 conflicts with none of rows 0..2.
        self.assertEqual(self.safety_test2(3, 6, bd, 2), T0Mbtf(True))
        # Row 3, column 0 shares a column with row 0.
        self.assertEqual(self.safety_test2(3, 0, bd, 2), T0Mbtf(False))

    def test_safety_test2_base_case(self):
        # i = -1 means there are no existing queens to conflict with.
        self.assertEqual(self.safety_test2(0, 0, [0] * 8, -1), T0Mbtf(True))

    def test_safety_test2_on_a_real_solution(self):
        # Every row of a genuine solution must be safe against all
        # earlier rows.
        for row in range(8):
            with self.subTest(row=row):
                self.assertEqual(
                    self.safety_test2(row, SOLUTION_8[row], SOLUTION_8, row - 1),
                    T0Mbtf(True),
                )

    def test_safety_test2_detects_an_injected_conflict(self):
        # Same solution, but with row 7 moved onto row 0's column.
        conflicting = list(SOLUTION_8)
        conflicting[7] = conflicting[0]
        self.assertEqual(
            self.safety_test2(7, conflicting[7], conflicting, 6),
            T0Mbtf(False),
        )


def reference_solutions(n):
    """All n-queens solutions by brute force over column permutations
    (which already rules out shared rows and columns). permutations()
    yields tuples in lexicographic order, which is also the order in
    which ATS2's search (row by row, column 0 upward) finds and prints
    them."""
    return [cols for cols in itertools.permutations(range(n))
            if not has_conflict(list(cols))]


def assert_valid_board(test, board, n):
    """n queens, one per row, all columns in range, and no two sharing a
    column or a diagonal (rows are distinct by the representation)."""
    test.assertEqual(len(board), n)
    test.assertTrue(all(0 <= c < n for c in board), board)
    test.assertEqual(len(set(board)), n, f"shared column in {board}")
    test.assertEqual(len({i + c for i, c in enumerate(board)}), n, f"shared diagonal in {board}")
    test.assertEqual(len({i - c for i, c in enumerate(board)}), n, f"shared anti-diagonal in {board}")


class TestSearch(unittest.TestCase):
    # N = 1..4 run comfortably; larger boards need the deep-recursion
    # runner (see queens_lambda0.run_with_deep_recursion: the
    # interpreter is not tail-call optimized even though ATS2's
    # `search` is a tail call), which QueensLambda0.run always uses.

    def test_result_shape(self):
        # search returns the LAMBDA0 value (nsol, sols).
        result = build_queens(4).run()
        self.assertIsInstance(result.arg1, T0Mint)
        self.assertEqual(result_count(result), 2)
        self.assertEqual(result_boards(result), [(1, 3, 0, 2), (2, 0, 3, 1)])

    def test_small_boards_match_reference(self):
        for n in (1, 2, 3, 4, 5, 6, 7):
            with self.subTest(n=n):
                result = build_queens(n).run()
                self.assertEqual(result_count(result), EXPECTED_SOLUTION_COUNTS[n])
                boards = result_boards(result)
                self.assertEqual(boards, reference_solutions(n))
                for board in boards:
                    assert_valid_board(self, board, n)


class TestEightQueens(unittest.TestCase):
    """The original problem. The 8x8 search is slow under the
    substitution-based interpreter, so it is evaluated once and shared."""

    @classmethod
    def setUpClass(cls):
        cls.result = build_queens(8).run()
        cls.boards = result_boards(cls.result)

    def test_count_matches_original_ats2_program(self):
        # sourcecode.dats prints "Solution #1" .. "Solution #92" and
        # returns nsol = 92.
        self.assertEqual(result_count(self.result), 92)
        self.assertEqual(len(self.boards), 92)

    def test_every_board_is_a_valid_solution(self):
        for board in self.boards:
            with self.subTest(board=board):
                assert_valid_board(self, board, 8)

    def test_boards_are_distinct(self):
        self.assertEqual(len(set(self.boards)), 92)

    def test_boards_match_original_order(self):
        # ATS2 prints the solutions in lexicographic order, starting with
        # the board below (checked against the Assignment 1 translation's
        # printed output as well).
        self.assertEqual(self.boards[0], (0, 4, 7, 5, 2, 6, 1, 3))
        self.assertEqual(self.boards[-1], (7, 3, 0, 2, 5, 1, 6, 4))
        self.assertEqual(self.boards, reference_solutions(8))


class TestSolutionValidity(unittest.TestCase):
    """Cross-checks the translated safety_test1/safety_test2 terms, the
    conflict logic search relies on, against a pure-Python reference."""

    def test_reference_solution_is_conflict_free(self):
        self.assertFalse(has_conflict(SOLUTION_8))

    def test_translated_checks_agree_with_reference_on_random_boards(self):
        import random
        rng = random.Random(0)
        q = build_queens(8)
        for _ in range(20):
            cols = [rng.randrange(8) for _ in range(8)]
            expected_has_conflict = has_conflict(cols)
            # A board is fully safe iff every row is safe against all
            # earlier rows.
            all_safe = all(
                t0erm_cbv_evaluate0(
                    APP(q.safety_test2, T0Mint(i), T0Mint(cols[i]), board_literal(cols), T0Mint(i - 1))
                ) == T0Mbtf(True)
                for i in range(8)
            )
            with self.subTest(cols=cols):
                self.assertEqual(all_safe, not expected_has_conflict)


if __name__ == "__main__":
    unittest.main(verbosity=2)
