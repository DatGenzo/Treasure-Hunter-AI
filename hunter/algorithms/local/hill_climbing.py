"""
hill_climbing.py — Hill Climbing local search algorithm optimizing score paths.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from algorithms.base_algorithm import AIAlgorithm, AlgorithmStats, StepResult
from maps.tilemap import TileMap

logger = logging.getLogger(__name__)


class HillClimbingAlgorithm(AIAlgorithm):
    """Hill Climbing local search solver.

    Optimizes the score path by maximizing treasures collected within a lookahead budget.
    """

    def __init__(self, budget: int = 8) -> None:
        self._budget = budget

        self._start: Tuple[int, int] = (0, 0)
        self._goal: Tuple[int, int] = (0, 0)
        self._tilemap: Optional[TileMap] = None

        self._current_node: Tuple[int, int] = (0, 0)
        self._treasures: Set[Tuple[int, int]] = set()
        self._collected: Set[Tuple[int, int]] = set()

        self._phase: str = "SEARCHING"
        self._path: List[Tuple[int, int]] = []
        self._stats_obj = AlgorithmStats()

        # Vis data
        self._neighbors: Set[Tuple[int, int]] = set()
        self._best_neighbor: Optional[Tuple[int, int]] = None
        self._score_map: Dict[Tuple[int, int], float] = {}
        self._is_stuck: bool = False

    @property
    def is_stuck(self) -> bool:
        return self._is_stuck

    def initialise(
        self,
        start: Tuple[int, int],
        goal: Tuple[int, int],
        tilemap: TileMap,
        game_state: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Set up local search and identify treasure locations."""
        self._start = start
        self._goal = goal
        self._tilemap = tilemap

        self._locked_doors = set()
        if game_state and "doors" in game_state:
            for col, row, locked in game_state["doors"]:
                if locked:
                    self._locked_doors.add((col, row))

        self._fog_grid = None
        if game_state and "fog_grid" in game_state:
            self._fog_grid = game_state["fog_grid"]

        self._current_node = start
        self._path = [start]
        self._phase = "SEARCHING"
        self._is_stuck = False


        # Scan map for treasures
        self._treasures = {
            (col, row) for col, row, type_str in tilemap.item_spawns if type_str == "treasure"
        }
        self._collected = set()

        self._neighbors = set()
        self._best_neighbor = None
        self._score_map = {}

        self._stats_obj = AlgorithmStats(nodes_visited=1)

    def is_done(self) -> bool:
        """Return True when local optimum or goal is hit."""
        return self._phase in {"DONE", "FAILED"}

    @property
    def stats(self) -> AlgorithmStats:
        """Return search metrics."""
        return self._stats_obj

    def _objective(self, col: int, row: int, collected_set: frozenset) -> float:
        """Evaluate the objective value of the state: max treasures collected in budget steps."""
        if self._tilemap is None or not self._tilemap.is_walkable(col, row):
            return -999999.0

        if (col, row) in self._locked_doors and (col, row) != self._goal:
            return -999999.0

        if self._fog_grid is not None:
            if 0 <= row < len(self._fog_grid) and 0 <= col < len(self._fog_grid[0]):
                if self._fog_grid[row][col]:
                    return -999999.0

        # Run a lookahead BFS to find maximum treasures collectable within budget steps
        max_treasures = self._get_max_treasures_in_budget(col, row, collected_set, self._budget)
        val = float(max_treasures)

        # Tie-breaker: guide towards nearest uncollected treasure
        active_treasures = self._treasures - collected_set
        if active_treasures:
            min_dist = min(abs(col - tc) + abs(row - tr) for tc, tr in active_treasures)
            val += 1.0 / (min_dist + 1)
        else:
            # Guide to exit if all treasures collected
            dist_to_exit = abs(col - self._goal[0]) + abs(row - self._goal[1])
            val += 1.0 / (dist_to_exit + 1)

        # Cost penalty to avoid mud/water
        val -= self._tilemap.move_cost(col, row) * 0.05
        return val

    def _get_max_treasures_in_budget(
        self, start_col: int, start_row: int, start_collected: frozenset, budget: int
    ) -> int:
        """BFS lookahead to calculate the maximum treasures collectable within budget steps."""
        if self._tilemap is None or budget <= 0:
            return len(start_collected)

        queue = [(start_col, start_row, start_collected, 0)]
        visited = set()
        max_t = len(start_collected)

        while queue:
            c, r, col_set, steps = queue.pop(0)

            # If standing on a new treasure, add it
            new_col_set = col_set
            if (c, r) in self._treasures and (c, r) not in col_set:
                new_col_set = col_set | {(c, r)}
                max_t = max(max_t, len(new_col_set))

            if steps >= budget:
                continue

            state_key = (c, r, new_col_set)
            if state_key in visited:
                continue
            visited.add(state_key)

            for neighbor_vec in self._tilemap.neighbors(c, r, treat_goal_as_walkable=self._goal):
                nc, nr = neighbor_vec.x, neighbor_vec.y
                if (nc, nr) in self._locked_doors and (nc, nr) != self._goal:
                    continue
                # Fog tiles are treated as walkable.
                queue.append((nc, nr, new_col_set, steps + 1))

        return max_t

    def step(self) -> StepResult:
        """Evaluate neighbors and greedily move to the highest objective value neighbor."""
        if self._tilemap is None or self.is_done():
            return StepResult("done")

        # Update collected treasures list
        if self._current_node in self._treasures:
            self._collected.add(self._current_node)

        # Check goal reached
        if self._current_node == self._goal:
            self._phase = "DONE"
            return StepResult("done", self.get_vis_data())

        curr = self._current_node
        self._stats_obj.nodes_expanded += 1

        # Generate neighbors
        neighbors_vec = self._tilemap.neighbors(curr[0], curr[1], treat_goal_as_walkable=self._goal)
        neighbors = [(n.x, n.y) for n in neighbors_vec]
        
        self._neighbors = set(neighbors)
        self._stats_obj.nodes_visited += len(neighbors)

        if not neighbors:
            self._phase = "FAILED"
            return StepResult("done", self.get_vis_data())

        # Evaluate neighbors
        current_state_collected = frozenset(self._collected)
        current_obj = self._objective(curr[0], curr[1], current_state_collected)

        best_val = -999999.0
        best_n = None
        self._score_map.clear()

        for n in neighbors:
            # Check locked doors and fog for neighbors
            if n in self._locked_doors and n != self._goal:
                continue
            # Fog tiles are treated as walkable.
            val = self._objective(n[0], n[1], current_state_collected)
            self._score_map[n] = val
            if val > best_val:
                best_val = val
                best_n = n

        # Check for local optimum (no neighbor is strictly better than current state)
        if best_n is None or best_val <= current_obj:
            logger.info("Hill Climbing: Stuck in local optimum at %s", str(curr))
            self._phase = "DONE"
            self._is_stuck = True
            return StepResult("done", self.get_vis_data())


        # Move to best neighbor
        self._best_neighbor = best_n
        
        # Update memory peak
        self._stats_obj.memory_peak = max(self._stats_obj.memory_peak, 1 + len(neighbors))

        dx = best_n[0] - curr[0]
        dy = best_n[1] - curr[1]

        action = "wait"
        if dx == 0 and dy == -1:
            action = "move_n"
        elif dx == 0 and dy == 1:
            action = "move_s"
        elif dx == -1 and dy == 0:
            action = "move_w"
        elif dx == 1 and dy == 0:
            action = "move_e"

        self._current_node = best_n
        self._path.append(best_n)

        # Update stats
        self._stats_obj.path_length = len(self._path) - 1
        self._stats_obj.path_cost += self._tilemap.move_cost(best_n[0], best_n[1])

        return StepResult(action, self.get_vis_data())

    def get_vis_data(self) -> Dict[str, Any]:
        """Format visualisation data."""
        # Convert neighbors to candidate pool for overlay compatibility
        return {
            "current": self._current_node,
            "candidates": self._neighbors,
            "best": {self._best_neighbor} if self._best_neighbor else set(),
            "rejected": self._neighbors - {self._best_neighbor} if self._best_neighbor else self._neighbors,
            "score_map": self._score_map.copy(),
            "path": self._path,
        }
