"""
bfs.py — Breadth-First Search algorithm implementation.
"""

from __future__ import annotations

from collections import deque
from typing import Any, Dict, List, Optional, Set, Tuple

from algorithms.base_algorithm import AIAlgorithm, AlgorithmStats, StepResult
from maps.tilemap import TileMap


class BFSAlgorithm(AIAlgorithm):
    """Breadth-First Search (BFS) pathfinder.

    Expands level-by-level using a FIFO queue. Guarantees shortest path in uniform grids.
    """

    def __init__(self) -> None:
        self._start: Tuple[int, int] = (0, 0)
        self._goal: Tuple[int, int] = (0, 0)
        self._tilemap: Optional[TileMap] = None

        self._queue: deque[Tuple[int, int]] = deque()
        self._visited: Set[Tuple[int, int]] = set()
        self._parent: Dict[Tuple[int, int], Optional[Tuple[int, int]]] = {}

        self._phase: str = "SEARCHING"  # "SEARCHING", "EXECUTING", "DONE", "FAILED"
        self._path: List[Tuple[int, int]] = []
        self._path_index: int = 0
        self._current_node: Optional[Tuple[int, int]] = None

        self._stats_obj = AlgorithmStats()

    def initialise(
        self,
        start: Tuple[int, int],
        goal: Tuple[int, int],
        tilemap: TileMap,
        game_state: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Set up BFS initial variables."""
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

        self._queue = deque([start])
        self._visited = {start}
        self._parent = {start: None}

        self._phase = "SEARCHING"
        self._path = []
        self._path_index = 0
        self._current_node = None

        self._stats_obj = AlgorithmStats(nodes_visited=1)

    def is_done(self) -> bool:
        """Return True when AI execution completes or fails."""
        return self._phase in {"DONE", "FAILED"}

    @property
    def stats(self) -> AlgorithmStats:
        """Return live metrics."""
        return self._stats_obj

    def get_vis_data(self) -> Dict[str, Any]:
        """Format visualisation dictionary."""
        return {
            "visited": self._visited,
            "frontier": set(self._queue),
            "current": self._current_node,
            "path": self._path,
        }

    def _reconstruct_path(self) -> None:
        """Trace back parents to construct shortest path from start to goal."""
        curr = self._goal
        path = []
        while curr is not None:
            path.append(curr)
            curr = self._parent[curr]
        path.reverse()
        self._path = path

        # Calculate metrics
        self._stats_obj.path_length = len(path) - 1
        cost = 0.0
        if self._tilemap:
            for col, row in path[1:]:  # Skip start cell cost
                cost += self._tilemap.move_cost(col, row)
        self._stats_obj.path_cost = cost

    def step(self) -> StepResult:
        """Process one search iteration or one movement command."""
        if self._tilemap is None:
            return StepResult("wait")

        if self._phase == "SEARCHING":
            if not self._queue:
                self._phase = "FAILED"
                return StepResult("done", self.get_vis_data())

            curr = self._queue.popleft()
            self._current_node = curr
            self._stats_obj.nodes_expanded += 1

            if curr == self._goal:
                self._reconstruct_path()
                self._phase = "EXECUTING"
                return StepResult("wait", self.get_vis_data())

            # Expand neighbors
            for neighbor_vec in self._tilemap.neighbors(curr[0], curr[1], treat_goal_as_walkable=self._goal):
                n = (neighbor_vec.x, neighbor_vec.y)
                if n in self._locked_doors and n != self._goal:
                    continue
                # We no longer block pathfinding on unrevealed/fog tiles so AI can explore towards goals.
                if n not in self._visited:
                    self._visited.add(n)
                    self._stats_obj.nodes_visited += 1
                    self._parent[n] = curr
                    self._queue.append(n)

            return StepResult("wait", self.get_vis_data())

        elif self._phase == "EXECUTING":
            if self._path_index >= len(self._path) - 1:
                self._phase = "DONE"
                return StepResult("done", self.get_vis_data())

            curr_pos = self._path[self._path_index]
            next_pos = self._path[self._path_index + 1]

            # Replan if the next step is blocked (e.g. wall/door in revealed map)
            if not self._tilemap.is_walkable(next_pos[0], next_pos[1], treat_goal_as_walkable=self._goal) or (next_pos in self._locked_doors and next_pos != self._goal):
                doors_list = [(col, row, True) for col, row in self._locked_doors]
                self.initialise(curr_pos, self._goal, self._tilemap, {"doors": doors_list})
                return StepResult("wait", self.get_vis_data())

            self._path_index += 1

            # Convert coordinate difference to action strings
            dx = next_pos[0] - curr_pos[0]
            dy = next_pos[1] - curr_pos[1]

            action = "wait"
            if dx == 0 and dy == -1:
                action = "move_n"
            elif dx == 0 and dy == 1:
                action = "move_s"
            elif dx == -1 and dy == 0:
                action = "move_w"
            elif dx == 1 and dy == 0:
                action = "move_e"

            return StepResult(action, self.get_vis_data())

        return StepResult("done", self.get_vis_data())
