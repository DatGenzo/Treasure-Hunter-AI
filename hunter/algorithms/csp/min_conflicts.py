"""
min_conflicts.py — Min-Conflicts local search CSP solver for Latin Square puzzle.
Also supports pathfinding interface when initialized on the map.
"""

from __future__ import annotations

import logging
import random
from collections import deque
from typing import Any, Dict, Generator, List, Optional, Set, Tuple

from algorithms.base_algorithm import AIAlgorithm, AlgorithmStats, StepResult
from maps.tilemap import TileMap
from maps.puzzle import GemPuzzle

logger = logging.getLogger(__name__)


class MinConflictsSolver(AIAlgorithm):
    """Step-by-step CSP solver using Min-Conflicts local search.

    For Latin Square CSP.
    Also implements the pathfinding interface of AIAlgorithm as a fallback to navigate the map.
    """

    def __init__(self, max_steps: int = 1000) -> None:
        self.max_steps = max_steps

        # Pathfinder states
        self._start: Tuple[int, int] = (0, 0)
        self._goal: Tuple[int, int] = (0, 0)
        self._tilemap: Optional[TileMap] = None
        self._path: List[Tuple[int, int]] = []
        self._path_index: int = 0
        self._pf_phase: str = "SEARCHING"

        # CSP states
        self._puzzle: Optional[GemPuzzle] = None
        self._generator: Optional[Generator[Tuple[bool, Dict[Tuple[int, int], int], Dict[Tuple[int, int], List[int]], Optional[Tuple[int, int]]], None, None]] = None
        self._is_done = False
        self._success = False
        self._is_csp_mode = False

        # CSP stats & visualization
        self.assignments = 0
        self.backtracks = 0  # Not used in local search but kept for compatibility
        self.assigned: Dict[Tuple[int, int], int] = {}
        self.domains: Dict[Tuple[int, int], List[int]] = {}
        self.current_var: Optional[Tuple[int, int]] = None
        self.violations: Set[Tuple[int, int]] = set()

        self._stats_obj = AlgorithmStats()

    # --- Pathfinder Methods ---

    def _pathfind_bfs(self) -> None:
        """Simple BFS pathfinder fallback."""
        if not self._tilemap:
            self._pf_phase = "FAILED"
            return

        queue = deque([(self._start, [self._start])])
        visited = {self._start}

        locked = getattr(self, "_locked_doors", set())
        fog = getattr(self, "_fog_grid", None)

        while queue:
            pos, path = queue.popleft()
            if pos == self._goal:
                self._path = path
                self._path_index = 0
                self._pf_phase = "EXECUTING"
                self._stats_obj.path_length = len(path)
                return

            c, r = pos
            for dc, dr in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                nc, nr = c + dc, r + dr
                if (nc, nr) in visited:
                    continue
                if not self._tilemap.is_walkable(nc, nr):
                    continue
                if (nc, nr) in locked and (nc, nr) != self._goal:
                    continue
                if fog is not None:
                    if 0 <= nr < len(fog) and 0 <= nc < len(fog[0]):
                        if fog[nr][nc]:
                            continue
                visited.add((nc, nr))
                queue.append(((nc, nr), path + [(nc, nr)]))

        self._pf_phase = "FAILED"

    def _pf_step(self) -> StepResult:
        """Execute one pathfinding action step."""
        if self._pf_phase == "SEARCHING":
            self._pathfind_bfs()
            return StepResult(action="wait", vis_data=self._get_pf_vis_data())

        if self._pf_phase == "EXECUTING":
            if self._path_index >= len(self._path) - 1:
                self._pf_phase = "DONE"
                return StepResult(action="done", vis_data=self._get_pf_vis_data())

            curr = self._path[self._path_index]
            nxt = self._path[self._path_index + 1]
            self._path_index += 1

            self._stats_obj.path_cost += self._tilemap.move_cost(nxt[0], nxt[1])

            dc, dr = nxt[0] - curr[0], nxt[1] - curr[1]
            action = "wait"
            if dc == 1:
                action = "move_e"
            elif dc == -1:
                action = "move_w"
            elif dr == 1:
                action = "move_s"
            elif dr == -1:
                action = "move_n"

            return StepResult(action=action, vis_data=self._get_pf_vis_data())

        return StepResult(action="done", vis_data=self._get_pf_vis_data())

    def _get_pf_vis_data(self) -> Dict[str, Any]:
        return {
            "visited": set(self._path[:self._path_index + 1]),
            "frontier": set(),
            "current": self._path[self._path_index] if self._path_index < len(self._path) else None,
            "path": self._path,
        }

    # --- CSP Solver Methods ---

    def initialise(self, start: Any, goal: Any = None, tilemap: Any = None,
                    game_state: Any = None) -> None:
        """Initialize the solver. Handles both CSP Puzzle and Map pathfinding."""
        if isinstance(start, GemPuzzle):
            # CSP Mode
            self._is_csp_mode = True
            self._puzzle = start
            self._puzzle.reset()
            self._is_done = False
            self._success = False
            self.assignments = 0
            self.backtracks = 0

            self.assigned = {}
            self.domains = {var: list(self._puzzle.domains[var]) for var in self._puzzle.variables}
            self.current_var = None
            self.violations = set()

            self._generator = self._solve_stepwise()
        else:
            # Pathfinder Mode
            self._is_csp_mode = False
            self._start = start
            self._goal = goal
            self._tilemap = tilemap
            self._pf_phase = "SEARCHING"
            self._path = []
            self._path_index = 0
            self._stats_obj = AlgorithmStats(nodes_visited=1)

            self._locked_doors: Set[Tuple[int, int]] = set()
            if game_state and "doors" in game_state:
                for col, row, locked in game_state["doors"]:
                    if locked:
                        self._locked_doors.add((col, row))

            self._fog_grid = None
            if game_state and "fog_grid" in game_state:
                self._fog_grid = game_state["fog_grid"]

    def is_done(self) -> bool:
        if self._is_csp_mode:
            return self._is_done
        return self._pf_phase in {"DONE", "FAILED"}

    def is_success(self) -> bool:
        if self._is_csp_mode:
            return self._success
        return self._pf_phase == "DONE"

    @property
    def stats(self) -> AlgorithmStats:
        return self._stats_obj

    def get_vis_data(self) -> Dict[str, Any]:
        if self._is_csp_mode:
            domain_sizes = {k: len(v) for k, v in self.domains.items()}
            violations = []
            assigned_vars = list(self.assigned.keys())
            for i in range(len(assigned_vars)):
                for j in range(i + 1, len(assigned_vars)):
                    v1, v2 = assigned_vars[i], assigned_vars[j]
                    if self.assigned[v1] == self.assigned[v2] and self.assigned[v1] != 0:
                        if v1[0] == v2[0] or v1[1] == v2[1]:
                            violations.append((v1, v2))
            return {
                "assigned": self.assigned.copy(),
                "violations": self.violations.copy(),
                "current_var": self.current_var,
                "domains": {str(k): v for k, v in self.domains.items()},
                "domain_sizes": domain_sizes,
                "constraint_violations": violations,
                "assignments_count": self.assignments,
                "backtracks_count": self.backtracks,  # Min-Conflicts tracks conflicts/steps
            }
        return self._get_pf_vis_data()

    def step(self) -> Any:
        """Advance one search/solving step."""
        if not self._is_csp_mode:
            return self._pf_step()

        # CSP Step
        if self._generator is None or self._is_done or self._puzzle is None:
            return self._puzzle.grid if self._puzzle else [[0]*3 for _ in range(3)]

        try:
            success, assignment, domains, cur_var = next(self._generator)
            self.assigned = assignment.copy()
            self.domains = {v: list(d) for v, d in domains.items()}
            self.current_var = cur_var

            # Sync assignment to puzzle grid
            for r in range(3):
                for c in range(3):
                    if not self._puzzle.fixed[r][c]:
                        self._puzzle.grid[r][c] = self.assigned.get((r, c), 0)

            return self._puzzle.grid
        except StopIteration:
            self._is_done = True
            if self._puzzle:
                self._success = self._puzzle.is_solved()
                # Ensure grid matches final assignment
                for r in range(3):
                    for c in range(3):
                        if not self._puzzle.fixed[r][c]:
                            self._puzzle.grid[r][c] = self.assigned.get((r, c), 0)
            return self._puzzle.grid if self._puzzle else [[0]*3 for _ in range(3)]

    def _count_conflicts(self, var: Tuple[int, int], val: int, assignment: Dict[Tuple[int, int], int]) -> int:
        """Count the number of constraint violations if var = val."""
        if self._puzzle is None:
            return 0

        row, col = var
        conflicts = 0

        # Row check
        for c in range(self._puzzle.size):
            if c != col:
                # Check fixed cells first
                if self._puzzle.fixed[row][c] and self._puzzle.grid[row][c] == val:
                    conflicts += 1
                # Check assigned variables
                elif (row, c) in assignment and assignment[(row, c)] == val:
                    conflicts += 1

        # Column check
        for r in range(self._puzzle.size):
            if r != row:
                # Check fixed cells first
                if self._puzzle.fixed[r][col] and self._puzzle.grid[r][col] == val:
                    conflicts += 1
                # Check assigned variables
                elif (r, col) in assignment and assignment[(r, col)] == val:
                    conflicts += 1

        return conflicts

    def _get_all_conflicted_vars(self, assignment: Dict[Tuple[int, int], int]) -> List[Tuple[int, int]]:
        """Return a list of all variables currently in conflict."""
        if self._puzzle is None:
            return []

        conflicted = []
        for var in self._puzzle.variables:
            val = assignment.get(var, 0)
            if self._count_conflicts(var, val, assignment) > 0:
                conflicted.append(var)
        return conflicted

    def _solve_stepwise(self) -> Generator[Tuple[bool, Dict[Tuple[int, int], int], Dict[Tuple[int, int], List[int]], Optional[Tuple[int, int]]], None, None]:
        """Generator performing Min-Conflicts local search."""
        if self._puzzle is None:
            return

        assignment: Dict[Tuple[int, int], int] = {}
        # 1. Complete initial assignment: assign a random value (or 1) to each variable
        for var in self._puzzle.variables:
            assignment[var] = random.choice([1, 2, 3])
            self.assignments += 1

        domains = {var: list(self._puzzle.domains[var]) for var in self._puzzle.variables}

        # Yield initial complete assignment
        yield False, assignment, domains, None

        for step_num in range(self.max_steps):
            # Check if solved
            conflicted_vars = self._get_all_conflicted_vars(assignment)
            if not conflicted_vars:
                # Solution found!
                yield True, assignment, domains, None
                return

            # Keep track of violations for highlighting
            self.violations = set(conflicted_vars)

            # Pick a conflicted variable
            var = random.choice(conflicted_vars)
            self.current_var = var

            # Find the value that minimizes conflicts
            best_vals = []
            min_c = 999
            for val in [1, 2, 3]:
                c_count = self._count_conflicts(var, val, assignment)
                if c_count < min_c:
                    min_c = c_count
                    best_vals = [val]
                elif c_count == min_c:
                    best_vals.append(val)

            # Assign the best value
            assigned_val = random.choice(best_vals)
            assignment[var] = assigned_val
            self.assignments += 1

            # Update domains for visualization (set it to the assigned value)
            domains[var] = [assigned_val]

            yield False, assignment, domains, var

        self._is_done = True
        self._success = self._puzzle.is_solved()
