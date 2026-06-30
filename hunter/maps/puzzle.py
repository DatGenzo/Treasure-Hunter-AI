"""
puzzle.py — Gem arrangement puzzle configuration and validation rules (Latin Square CSP).
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple


class GemPuzzle:
    """A 3x3 Latin Square Gem Arrangement Puzzle.

    Colors:
        0: Empty (Gray)
        1: Red Gem
        2: Green Gem
        3: Blue Gem

    Rules:
        No row or column can contain more than one gem of the same color.
    """

    def __init__(self, initial_grid: Optional[List[List[int]]] = None) -> None:
        if initial_grid is None:
            # Default solvable puzzle with 2 gems pre-placed
            self.grid = [
                [1, 0, 0],
                [0, 0, 2],
                [0, 0, 0],
            ]
            self.fixed = [
                [True, False, False],
                [False, False, True],
                [False, False, False],
            ]
        else:
            self.grid = [row[:] for row in initial_grid]
            self.fixed = [[cell != 0 for cell in row] for row in initial_grid]

        self.size = 3

        # CSP variables and domains definition
        self.variables: List[Tuple[int, int]] = []
        self.domains: Dict[Tuple[int, int], List[int]] = {}
        self.reset()

    def reset(self) -> None:
        """Restore the puzzle to its initial state and initialize CSP variables/domains."""
        self.variables.clear()
        self.domains.clear()

        for r in range(self.size):
            for c in range(self.size):
                if not self.fixed[r][c]:
                    self.grid[r][c] = 0
                    var = (r, c)
                    self.variables.append(var)
                    self.domains[var] = [1, 2, 3]  # Red, Green, Blue
                else:
                    # Clear values for cells that aren't fixed if grid was modified
                    pass

    def set_val(self, row: int, col: int, val: int) -> bool:
        """Place a gem color at (row, col) if the cell is not fixed."""
        if 0 <= row < self.size and 0 <= col < self.size:
            if not self.fixed[row][col]:
                self.grid[row][col] = val
                return True
        return False

    def get_val(self, row: int, col: int) -> int:
        """Return color value at (row, col)."""
        return self.grid[row][col]

    def is_consistent(self, var: Tuple[int, int], value: int, assignment: Dict[Tuple[int, int], int]) -> bool:
        """Check if assigning value to var is consistent with current assignment and fixed cells."""
        row, col = var

        # 1. Check against other assigned variables in same row/col
        for other_var, other_val in assignment.items():
            if other_var != var:
                orow, ocol = other_var
                if (orow == row or ocol == col) and other_val == value:
                    return False

        # 2. Check against fixed cells in same row/col
        for r in range(self.size):
            if r != row and self.fixed[r][col] and self.grid[r][col] == value:
                return False
        for c in range(self.size):
            if c != col and self.fixed[row][c] and self.grid[row][c] == value:
                return False

        return True

    def is_complete(self, assignment: Dict[Tuple[int, int], int]) -> bool:
        """Check if all variables have been assigned."""
        return len(assignment) == len(self.variables)

    def is_valid(self, row: int, col: int, val: int) -> bool:
        """Verify if placing val at (row, col) respects Latin Square rules (for manual play)."""
        if val == 0:
            return True

        # Check row constraint
        for c in range(self.size):
            if c != col and self.grid[row][c] == val:
                return False

        # Check column constraint
        for r in range(self.size):
            if r != row and self.grid[r][col] == val:
                return False

        return True

    def is_solved(self) -> bool:
        """Check if all cells are filled and satisfy Latin Square conditions."""
        for r in range(self.size):
            for c in range(self.size):
                val = self.grid[r][c]
                if val == 0:
                    return False
                if not self.is_valid(r, c, val):
                    return False
        return True
