"""
online_search.py — Learning Real-Time A* (LRTA*) online search algorithm implementation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

from algorithms.base_algorithm import AIAlgorithm, AlgorithmStats, StepResult
from maps.tilemap import TileMap


class OnlineSearchAlgorithm(AIAlgorithm):
    """Learning Real-Time A* (LRTA*) online search solver.

    Updates heuristic values of visited states interactively to guarantee complete exploration.
    """

    def __init__(self) -> None:
        self._start: Tuple[int, int] = (0, 0)
        self._goal: Tuple[int, int] = (0, 0)
        self._tilemap: Optional[TileMap] = None

        self._current_node: Tuple[int, int] = (0, 0)
        self._h_table: Dict[Tuple[int, int], float] = {}
        self._visited: Set[Tuple[int, int]] = set()

        self._phase: str = "SEARCHING"
        self._path: List[Tuple[int, int]] = []
        self._stats_obj = AlgorithmStats()

    def _heuristic(self, col: int, row: int) -> float:
        """Manhattan distance estimate."""
        return float(abs(col - self._goal[0]) + abs(row - self._goal[1]))

    def initialise(
        self,
        start: Tuple[int, int],
        goal: Tuple[int, int],
        tilemap: TileMap,
        game_state: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Set up LRTA* parameters."""
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
        self._h_table = {start: self._heuristic(start[0], start[1])}
        self._visited = {start}
        self._path = [start]
        self._phase = "SEARCHING"

        self._stats_obj = AlgorithmStats(nodes_visited=1)

    def is_done(self) -> bool:
        """Return True when goal is reached."""
        return self._phase in {"DONE", "FAILED"}

    @property
    def stats(self) -> AlgorithmStats:
        """Return live metrics."""
        return self._stats_obj

    def get_vis_data(self) -> Dict[str, Any]:
        """Format visualisation dictionary."""
        return {
            "visited": self._visited,
            "frontier": set(self._h_table.keys()) - {self._current_node},
            "current": self._current_node,
            "path": self._path,
            "h_values": self._h_table.copy(),
            "observed": set(self._h_table.keys()),
        }

    def step(self) -> StepResult:
        """Update current cell heuristic and move to neighbor minimizing cost + h."""
        if self._tilemap is None or self.is_done():
            return StepResult("done")

        if self._current_node == self._goal:
            self._phase = "DONE"
            return StepResult("done", self.get_vis_data())

        curr = self._current_node
        self._visited.add(curr)
        self._stats_obj.nodes_expanded += 1

        # 1. Get walkable neighbors
        neighbors_vec = self._tilemap.neighbors(curr[0], curr[1], treat_goal_as_walkable=self._goal)
        neighbors = []
        for n_vec in neighbors_vec:
            n = (n_vec.x, n_vec.y)
            if n in self._locked_doors and n != self._goal:
                continue
            # Fog tiles are treated as walkable.
            neighbors.append(n)

        if not neighbors:
            self._phase = "FAILED"
            return StepResult("done", self.get_vis_data())

        # Initialize heuristics for neighbors
        for n in neighbors:
            if n not in self._h_table:
                self._h_table[n] = self._heuristic(n[0], n[1])
                self._stats_obj.nodes_visited += 1

        # Update memory peak
        self._stats_obj.memory_peak = max(self._stats_obj.memory_peak, len(self._visited) + len(self._h_table))

        # 2. Update rule: h(s) = max(h(s), min_a( cost(s, s') + h(s') ))
        min_cost_h = 999999.0
        best_neighbor = None

        for n in neighbors:
            cost = self._tilemap.move_cost(n[0], n[1])
            cost_h = cost + self._h_table[n]
            if cost_h < min_cost_h:
                min_cost_h = cost_h
                best_neighbor = n

        # Update table value
        self._h_table[curr] = max(self._h_table[curr], min_cost_h)

        if best_neighbor is None:
            self._phase = "FAILED"
            return StepResult("done", self.get_vis_data())

        # 3. Move to the best neighbor
        dx = best_neighbor[0] - curr[0]
        dy = best_neighbor[1] - curr[1]

        action = "wait"
        if dx == 0 and dy == -1:
            action = "move_n"
        elif dx == 0 and dy == 1:
            action = "move_s"
        elif dx == -1 and dy == 0:
            action = "move_w"
        elif dx == 1 and dy == 0:
            action = "move_e"

        # Update position
        self._current_node = best_neighbor
        self._path.append(best_neighbor)
        
        # Update metrics
        self._stats_obj.path_length = len(self._path) - 1
        self._stats_obj.path_cost += self._tilemap.move_cost(best_neighbor[0], best_neighbor[1])

        return StepResult(action, self.get_vis_data())
