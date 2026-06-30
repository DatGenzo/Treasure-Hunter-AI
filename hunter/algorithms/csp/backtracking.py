"""
backtracking.py — Backtracking CSP solver with Forward Checking.
"""

from __future__ import annotations

from typing import Any, Dict, Generator, List, Optional, Set, Tuple
from collections import deque

from algorithms.base_algorithm import AIAlgorithm, AlgorithmStats, StepResult
from maps.tilemap import TileMap
from maps.puzzle import GemPuzzle


class BacktrackingCSPSolver(AIAlgorithm):
    """Step-by-step backtracking search solver with Forward Checking for Latin Square CSP.
    Also implements the pathfinding interface of AIAlgorithm as a fallback to navigate the map.
    """

    def __init__(self) -> None:
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

        # CSP stats
        self.assignments = 0
        self.backtracks = 0

        # Current state for visualization
        self.assigned: Dict[Tuple[int, int], int] = {}
        self.domains: Dict[Tuple[int, int], List[int]] = {}
        self.current_var: Optional[Tuple[int, int]] = None
        self.violations: Set[Tuple[int, int]] = set()

        self._stats_obj = AlgorithmStats()

    def initialise(
        self,
        start: Any,
        goal: Any = None,
        tilemap: Any = None,
        game_state: Any = None,
    ) -> None:
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
            # Initial domains
            self.domains = {var: list(start.domains[var]) for var in start.variables}
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
        """Return True when solver finishes (succeeded or failed)."""
        if self._is_csp_mode:
            return self._is_done
        return self._pf_phase in {"DONE", "FAILED"}

    def is_success(self) -> bool:
        """Return True if a valid solution was found."""
        if self._is_csp_mode:
            return self._success
        return self._pf_phase == "DONE"

    @property
    def stats(self) -> AlgorithmStats:
        """Return stats."""
        return self._stats_obj

    def step(self) -> Any:
        """Advance search by one step (either CSP or Pathfinder)."""
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

    def _select_unassigned_var(self, assignment: Dict[Tuple[int, int], int], domains: Dict[Tuple[int, int], List[int]]) -> Optional[Tuple[int, int]]:
        """Select next variable using MRV (Minimum Remaining Values) heuristic."""
        if self._puzzle is None:
            return None

        best_var = None
        min_domain_size = 999

        for var in self._puzzle.variables:
            if var not in assignment:
                size = len(domains[var])
                if size < min_domain_size:
                    min_domain_size = size
                    best_var = var
        return best_var

    def get_vis_data(self) -> Dict[str, Any]:
        """Format visualisation dictionary."""
        if self._is_csp_mode:
            # Build domain sizes dict {(row,col): int}
            domain_sizes = {k: len(v) for k, v in self.domains.items()}
            
            # Find constraint violations (cells in same row/col with same value)
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
                "backtracks_count": self.backtracks,
            }
        return self._get_pf_vis_data()

    def _solve_stepwise(self) -> Generator[Tuple[bool, Dict[Tuple[int, int], int], Dict[Tuple[int, int], List[int]], Optional[Tuple[int, int]]], None, None]:
        """Recursive backtracking search with Forward Checking as a generator."""
        if self._puzzle is None:
            return

        assignment: Dict[Tuple[int, int], int] = {}
        initial_domains = {var: list(self._puzzle.domains[var]) for var in self._puzzle.variables}

        def backtrack_fc(
            assign: Dict[Tuple[int, int], int],
            doms: Dict[Tuple[int, int], List[int]]
        ) -> Generator[Tuple[bool, Dict[Tuple[int, int], int], Dict[Tuple[int, int], List[int]], Optional[Tuple[int, int]]], None, None]:
            
            if self._puzzle.is_complete(assign):
                yield True, assign, doms, None
                return

            var = self._select_unassigned_var(assign, doms)
            if var is None:
                return

            row, col = var
            for val in list(doms[var]):
                if self._puzzle.is_consistent(var, val, assign):
                    # Assign value
                    assign[var] = val
                    self.assignments += 1
                    self.violations.clear()

                    # Forward checking: prune domains of neighboring variables
                    new_doms = {v: list(d) for v, d in doms.items()}
                    new_doms[var] = [val]

                    # Prune row and column neighbors
                    prune_failed = False
                    for other_var in self._puzzle.variables:
                        if other_var not in assign:
                            orow, ocol = other_var
                            if orow == row or ocol == col:
                                if val in new_doms[other_var]:
                                    new_doms[other_var].remove(val)
                                    if not new_doms[other_var]:
                                        prune_failed = True

                    if not prune_failed:
                        # Yield the successful assignment state
                        yield False, assign, new_doms, var
                        yield from backtrack_fc(assign, new_doms)
                        if self._puzzle.is_solved():
                            return
                    else:
                        # Pruning failed (domain wiped out), show as violation/backtrack trigger
                        self.violations.add(var)
                        yield False, assign, new_doms, var

                    # Backtrack (undo)
                    del assign[var]
                    self.backtracks += 1
                    yield False, assign, doms, var

        yield from backtrack_fc(assignment, initial_domains)
        self._is_done = True
        if self._puzzle:
            self._success = self._puzzle.is_solved()

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
