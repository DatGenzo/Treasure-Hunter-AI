"""
iddfs.py — Iterative-Deepening Depth-First Search algorithm implementation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

from algorithms.base_algorithm import AIAlgorithm, AlgorithmStats, StepResult
from maps.tilemap import TileMap


class IDDFSAlgorithm(AIAlgorithm):
    """Iterative-Deepening Depth-First Search (IDDFS) pathfinder.

    Combines DFS space efficiency with BFS optimality by running DLS with increasing limits.
    """

    def __init__(self, depth_step: int = 1) -> None:
        self._depth_step = depth_step

        self._start: Tuple[int, int] = (0, 0)
        self._goal: Tuple[int, int] = (0, 0)
        self._tilemap: Optional[TileMap] = None

        self._current_limit: int = 0
        self._stack: List[Tuple[Tuple[int, int], int]] = []  # Stack stores ((col, row), depth)
        self._visited: Set[Tuple[int, int]] = set()
        self._parent: Dict[Tuple[int, int], Optional[Tuple[int, int]]] = {}
        self._pruned_occurred: bool = False

        self._phase: str = "SEARCHING"
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
        """Set up IDDFS initial variables."""
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

        self._current_limit = 0
        self._stack = [(start, 0)]
        self._visited = {start}
        self._parent = {start: None}
        self._pruned_occurred = False

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
        frontier = {node for node, depth in self._stack}
        return {
            "visited": self._visited,
            "frontier": frontier,
            "current": self._current_node,
            "path": self._path,
            "depth_limit": self._current_limit,
        }

    def _reconstruct_path(self) -> None:
        """Trace back parents to construct path from start to goal."""
        curr = self._goal
        path = []
        while curr is not None:
            path.append(curr)
            curr = self._parent[curr]
        path.reverse()
        self._path = path

        self._stats_obj.path_length = len(path) - 1
        cost = 0.0
        if self._tilemap:
            for col, row in path[1:]:
                cost += self._tilemap.move_cost(col, row)
        self._stats_obj.path_cost = cost

    def step(self) -> StepResult:
        """Process one DLS search step or one movement command."""
        if self._tilemap is None:
            return StepResult("wait")

        if self._phase == "SEARCHING":
            if not self._stack:
                # If we finished DLS and pruned nodes exist, increase limit and restart DLS
                if self._pruned_occurred:
                    self._current_limit += self._depth_step
                    self._stack = [(self._start, 0)]
                    self._visited = {self._start}
                    self._parent = {self._start: None}
                    self._pruned_occurred = False
                    return StepResult("wait", self.get_vis_data())
                else:
                    # Space completely explored at all limits, no solution
                    self._phase = "FAILED"
                    return StepResult("done", self.get_vis_data())

            curr, depth = self._stack.pop()
            self._current_node = curr
            self._stats_obj.nodes_expanded += 1

            if curr == self._goal:
                self._reconstruct_path()
                self._phase = "EXECUTING"
                return StepResult("wait", self.get_vis_data())

            # Only expand neighbors if depth limit has not been hit
            self._stats_obj.current_depth = self._current_limit
            if depth < self._current_limit:
                neighbors = self._tilemap.neighbors(curr[0], curr[1], treat_goal_as_walkable=self._goal)
                for neighbor_vec in reversed(neighbors):
                    n = (neighbor_vec.x, neighbor_vec.y)
                    if n in self._locked_doors and n != self._goal:
                        continue
                    # We no longer block pathfinding on unrevealed/fog tiles so AI can explore towards goals.
                    if n not in self._visited:
                        self._visited.add(n)
                        self._stats_obj.nodes_visited += 1
                        self._parent[n] = curr
                        self._stack.append((n, depth + 1))
            else:
                # We hit the depth limit. Check if unvisited neighbors exist to flag DLS pruning
                neighbors = self._tilemap.neighbors(curr[0], curr[1], treat_goal_as_walkable=self._goal)
                has_unvisited = False
                for neighbor_vec in neighbors:
                    n = (neighbor_vec.x, neighbor_vec.y)
                    if n in self._locked_doors and n != self._goal:
                        continue
                    # Fog tiles are treated as walkable.
                    if n not in self._visited:
                        has_unvisited = True
                        break
                if has_unvisited:
                    self._pruned_occurred = True

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
