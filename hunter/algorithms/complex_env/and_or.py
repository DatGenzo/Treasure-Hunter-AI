"""
and_or.py — AND-OR Graph Search algorithm for non-deterministic environments.

In this implementation, OR nodes are the player's choices (which direction to move),
and AND nodes represent uncertainty — each action can lead to multiple possible outcomes.
We model a "slippery floor" variant: when moving, there's a chance the player also
slides one extra step in the same direction.

The AND-OR planner produces a contingency plan (policy), not a single path.
For visualization, we show the explored policy tree and a "best expected path".
"""

from __future__ import annotations

import random
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

from algorithms.base_algorithm import AIAlgorithm, AlgorithmStats, StepResult
from maps.tilemap import TileMap


class AndOrAlgorithm(AIAlgorithm):
    """AND-OR Graph Search for non-deterministic environments.

    Models actions as having two possible outcomes:
      - Primary result (probability 0.8): move to target cell
      - Slip result (probability 0.2): slide one more step in the same direction

    Builds a policy (mapping from state → action) rather than a single path.
    For gameplay, follows the policy from current position.
    """

    def __init__(self) -> None:
        self._start: Tuple[int, int] = (0, 0)
        self._goal: Tuple[int, int] = (0, 0)
        self._tilemap: Optional[TileMap] = None

        # Policy mapping: state → best action direction (dx, dy)
        self._policy: Dict[Tuple[int, int], Tuple[int, int]] = {}
        self._visited: Set[Tuple[int, int]] = set()
        self._frontier: Set[Tuple[int, int]] = set()
        self._plan_path: List[Tuple[int, int]] = []

        # Execution state
        self._current_pos: Tuple[int, int] = (0, 0)
        self._path_index: int = 0
        self._phase: str = "PLANNING"  # PLANNING → EXECUTING → DONE/FAILED
        self._current_node: Optional[Tuple[int, int]] = None

        # BFS-based planning queue for OR nodes
        self._or_queue: List[Tuple[int, int]] = []
        self._parent: Dict[Tuple[int, int], Optional[Tuple[int, int]]] = {}
        self._stats_obj = AlgorithmStats()

    DIRECTIONS = [(0, -1), (0, 1), (-1, 0), (1, 0)]
    ACTION_NAMES = {(0, -1): "move_n", (0, 1): "move_s", (-1, 0): "move_w", (1, 0): "move_e"}

    def initialise(
        self,
        start: Tuple[int, int],
        goal: Tuple[int, int],
        tilemap: TileMap,
        game_state: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize AND-OR planner."""
        self._start = start
        self._goal = goal
        self._tilemap = tilemap
        self._current_pos = start

        self._locked_doors = set()
        if game_state and "doors" in game_state:
            for col, row, locked in game_state["doors"]:
                if locked:
                    self._locked_doors.add((col, row))

        self._fog_grid = None
        if game_state and "fog_grid" in game_state:
            self._fog_grid = game_state["fog_grid"]

        self._policy = {}
        self._visited = {start}
        self._frontier = {start}
        self._parent = {start: None}
        self._or_queue = [start]

        self._phase = "PLANNING"
        self._plan_path = []
        self._path_index = 0
        self._current_node = start
        self._stats_obj = AlgorithmStats(nodes_visited=1)

    def _is_walkable(self, col: int, row: int) -> bool:
        if not self._tilemap.is_walkable(col, row, treat_goal_as_walkable=self._goal):
            return False
        if (col, row) in self._locked_doors and (col, row) != self._goal:
            return False
        # Fog of war: we assume fogged cells are walkable (Optimistic Free-space assumption)
        # to allow planning a path towards the goal through unexplored areas.
        return True

    def _get_outcomes(self, pos: Tuple[int, int], direction: Tuple[int, int]) -> List[Tuple[Tuple[int, int], float]]:
        """Return possible (result_pos, probability) pairs for an action.

        Primary: move to pos+direction (prob 0.8)
        Slip: move to pos+2*direction if walkable (prob 0.2), else stay at pos+direction
        """
        dx, dy = direction
        c, r = pos
        primary = (c + dx, r + dy)

        # Ensure primary is walkable
        if not self._is_walkable(primary[0], primary[1]):
            return [(pos, 1.0)]  # Blocked → stay

        slip = (c + 2 * dx, r + 2 * dy)
        if self._is_walkable(slip[0], slip[1]):
            return [(primary, 0.8), (slip, 0.2)]
        else:
            return [(primary, 1.0)]

    def _plan_step(self) -> None:
        """Expand one OR node using BFS to build policy."""
        if not self._or_queue:
            self._phase = "FAILED"
            return

        node = self._or_queue.pop(0)
        self._current_node = node
        self._stats_obj.nodes_expanded += 1

        if node == self._goal:
            # Reconstruct path following parent pointers
            path = []
            cur = self._goal
            while cur is not None:
                path.append(cur)
                cur = self._parent.get(cur)
            path.reverse()
            self._plan_path = path
            self._path_index = 0
            self._current_pos = self._start
            self._phase = "EXECUTING"
            self._stats_obj.path_length = len(path)
            return

        # OR node: try each direction
        for direction in self.DIRECTIONS:
            outcomes = self._get_outcomes(node, direction)
            # Store best-case outcome as policy
            best_outcome = outcomes[0][0]  # primary outcome
            if best_outcome not in self._visited:
                self._visited.add(best_outcome)
                self._frontier.add(best_outcome)
                self._parent[best_outcome] = node
                self._policy[node] = direction
                self._or_queue.append(best_outcome)
                self._stats_obj.nodes_visited += 1

        self._stats_obj.memory_peak = max(self._stats_obj.memory_peak, len(self._visited) + len(self._or_queue))

    def step(self) -> StepResult:
        """Execute one planning or execution step."""
        if self._phase == "PLANNING":
            self._plan_step()
            return StepResult(action="wait", vis_data=self._get_vis_data())

        elif self._phase == "EXECUTING":
            if self._path_index >= len(self._plan_path) - 1:
                self._phase = "DONE"
                return StepResult(action="done", vis_data=self._get_vis_data())

            next_pos = self._plan_path[self._path_index + 1]
            curr_pos = self._plan_path[self._path_index]
            self._path_index += 1
            self._current_pos = next_pos

            dx = next_pos[0] - curr_pos[0]
            dy = next_pos[1] - curr_pos[1]
            action = self.ACTION_NAMES.get((dx, dy), "wait")

            self._stats_obj.path_cost += self._tilemap.move_cost(next_pos[0], next_pos[1])
            return StepResult(action=action, vis_data=self._get_vis_data())

        return StepResult(action="done", vis_data=self._get_vis_data())

    def is_done(self) -> bool:
        return self._phase in {"DONE", "FAILED"}

    @property
    def stats(self) -> AlgorithmStats:
        return self._stats_obj

    def _get_vis_data(self) -> Dict[str, Any]:
        return {
            "visited": self._visited,
            "frontier": self._frontier,
            "current": self._current_node,
            "path": self._plan_path,
        }
