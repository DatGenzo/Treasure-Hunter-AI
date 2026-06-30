"""
no_observation.py — Sensorless (No-Observation) Search via Belief State BFS.

In a no-observation environment, the agent cannot sense its position.
It maintains a BELIEF STATE — a set of possible positions — and applies
actions that move ALL members of the belief set simultaneously.

The goal is to find a sequence of actions guaranteed to reach the goal
regardless of which cell in the belief state the agent is actually in.

Belief State BFS:
  - Initial belief: all walkable cells (agent could be anywhere)
  - Each action moves every state in the belief set
  - Goal: belief state ⊆ {goal_cell}
"""

from __future__ import annotations

import logging
from collections import deque
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

from algorithms.base_algorithm import AIAlgorithm, AlgorithmStats, StepResult
from maps.tilemap import TileMap

logger = logging.getLogger(__name__)


class NoObservationAlgorithm(AIAlgorithm):
    """Sensorless planning via Belief-State BFS.

    Since the agent has no sensors, it maintains a belief state (set of
    possible positions). The planner finds an action sequence guaranteed
    to reach the goal from ANY starting position.

    For practical gameplay:
      - Initial belief = all walkable tiles
      - Uses BFS over belief states (each state is a frozenset of grid cells)
      - Follows the found action sequence deterministically
    """

    DIRECTIONS = [(0, -1), (0, 1), (-1, 0), (1, 0)]
    ACTION_NAMES = {(0, -1): "move_n", (0, 1): "move_s", (-1, 0): "move_w", (1, 0): "move_e"}

    def __init__(self) -> None:
        self._start: Tuple[int, int] = (0, 0)
        self._goal: Tuple[int, int] = (0, 0)
        self._tilemap: Optional[TileMap] = None

        self._action_sequence: List[Tuple[int, int]] = []
        self._exec_index: int = 0

        self._phase: str = "PLANNING"
        self._visited_beliefs: Set[FrozenSet[Tuple[int, int]]] = set()
        self._plan_path: List[Tuple[int, int]] = []  # simplified path for visualization
        self._current_node: Optional[Tuple[int, int]] = None
        self._belief_display: Set[Tuple[int, int]] = set()

        # Fallback: use A* path directly if belief planning times out
        self._fallback_path: List[Tuple[int, int]] = []
        self._path_index: int = 0

        self._stats_obj = AlgorithmStats()

    def initialise(
        self,
        start: Tuple[int, int],
        goal: Tuple[int, int],
        tilemap: TileMap,
        game_state: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize sensorless planner with full belief state."""
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

        self._phase = "PLANNING"
        self._action_sequence = []
        self._exec_index = 0
        self._plan_path = [start]
        self._path_index = 0
        self._current_node = start
        self._stats_obj = AlgorithmStats(nodes_visited=1)

        # Build initial belief: all walkable tiles
        all_walkable: FrozenSet[Tuple[int, int]] = frozenset(
            (c, r)
            for r in range(tilemap.height)
            for c in range(tilemap.width)
            if self._is_walkable(c, r)
        )
        self._belief_display = set(all_walkable)
        self._visited_beliefs = set()

        # Run belief-state BFS (limited depth for performance) or fallback if state space is too large
        if len(all_walkable) > 100:
            logger.warning("Belief state too large for sensorless planning, falling back to BFS to prevent crash.")
            self._fallback_to_bfs()
        else:
            self._run_belief_bfs(all_walkable)


    def _is_walkable(self, col: int, row: int) -> bool:
        if not self._tilemap.is_walkable(col, row, treat_goal_as_walkable=self._goal):
            return False
        if (col, row) in self._locked_doors and (col, row) != self._goal:
            return False
        # Fog of war: we assume fogged cells are walkable (Optimistic Free-space assumption)
        # to allow planning a path towards the goal through unexplored areas.
        return True

    def _apply_action(self, belief: FrozenSet[Tuple[int, int]], direction: Tuple[int, int]) -> FrozenSet[Tuple[int, int]]:
        """Apply action to all states in belief set."""
        dx, dy = direction
        new_belief: Set[Tuple[int, int]] = set()
        for (c, r) in belief:
            nc, nr = c + dx, r + dy
            if self._is_walkable(nc, nr):
                new_belief.add((nc, nr))
            else:
                new_belief.add((c, r))  # Blocked: stay in place
        return frozenset(new_belief)

    def _run_belief_bfs(self, initial_belief: FrozenSet[Tuple[int, int]], max_depth: int = 40) -> None:
        """BFS over belief states to find guaranteed action sequence."""
        # Queue: (belief_state, action_sequence_so_far, simplified_real_pos_path)
        queue: deque = deque([(initial_belief, [], [self._start])])
        self._visited_beliefs.add(initial_belief)
        goal_frozenset = frozenset({self._goal})

        while queue:
            belief, actions, pos_path = queue.popleft()
            self._stats_obj.nodes_expanded += 1

            if len(actions) > max_depth:
                break

            for direction in self.DIRECTIONS:
                new_belief = self._apply_action(belief, direction)

                # Check if goal achieved (all states lead to goal)
                if self._goal in new_belief and len(new_belief) == 1:
                    self._action_sequence = actions + [direction]
                    self._plan_path = pos_path + [self._goal]
                    self._stats_obj.path_length = len(self._action_sequence)
                    return

                if new_belief not in self._visited_beliefs:
                    self._visited_beliefs.add(new_belief)
                    # Track simplified position: follow real start position
                    c, r = pos_path[-1]
                    dx, dy = direction
                    nc, nr = c + dx, r + dy
                    if self._is_walkable(nc, nr):
                        new_pos = (nc, nr)
                    else:
                        new_pos = (c, r)
                    queue.append((new_belief, actions + [direction], pos_path + [new_pos]))
                    self._stats_obj.nodes_visited += 1

            self._stats_obj.memory_peak = max(self._stats_obj.memory_peak, len(self._visited_beliefs) + len(self._belief_display))

        # Fallback: use direct path from start to goal (simple BFS)
        self._fallback_to_bfs()

    def _fallback_to_bfs(self) -> None:
        """Simple BFS fallback when belief planning exceeds depth limit."""
        from collections import deque as dq
        queue: deque = dq([(self._start, [self._start])])
        visited = {self._start}
        while queue:
            pos, path = queue.popleft()
            if pos == self._goal:
                self._plan_path = path
                # Convert path to action sequence
                self._action_sequence = []
                for i in range(1, len(path)):
                    dx = path[i][0] - path[i-1][0]
                    dy = path[i][1] - path[i-1][1]
                    self._action_sequence.append((dx, dy))
                self._stats_obj.path_length = len(self._action_sequence)
                return
            for direction in self.DIRECTIONS:
                dx, dy = direction
                nc, nr = pos[0] + dx, pos[1] + dy
                if (nc, nr) not in visited and self._is_walkable(nc, nr):
                    visited.add((nc, nr))
                    queue.append(((nc, nr), path + [(nc, nr)]))

    def step(self) -> StepResult:
        """Execute planned action sequence step by step."""
        if self._phase == "PLANNING":
            # Planning is done in initialise; start executing immediately
            if self._action_sequence:
                self._phase = "EXECUTING"
            else:
                self._phase = "FAILED"
            return StepResult(action="wait", vis_data=self._get_vis_data())

        elif self._phase == "EXECUTING":
            if self._exec_index >= len(self._action_sequence):
                self._phase = "DONE"
                return StepResult(action="done", vis_data=self._get_vis_data())

            direction = self._action_sequence[self._exec_index]
            self._exec_index += 1

            if self._exec_index < len(self._plan_path):
                self._current_node = self._plan_path[self._exec_index]
                if self._current_node:
                    self._stats_obj.path_cost += self._tilemap.move_cost(
                        self._current_node[0], self._current_node[1]
                    )

            action = self.ACTION_NAMES.get(direction, "wait")
            return StepResult(action=action, vis_data=self._get_vis_data())

        return StepResult(action="done", vis_data=self._get_vis_data())

    def is_done(self) -> bool:
        return self._phase in {"DONE", "FAILED"}

    @property
    def stats(self) -> AlgorithmStats:
        return self._stats_obj

    def _get_vis_data(self) -> Dict[str, Any]:
        # Show belief state as 'visited' for visualization
        return {
            "visited": self._belief_display,
            "frontier": set(),
            "current": self._current_node,
            "path": self._plan_path,
        }
