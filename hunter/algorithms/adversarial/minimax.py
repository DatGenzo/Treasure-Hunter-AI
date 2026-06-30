"""
minimax.py — Minimax adversarial search algorithm implementation.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional, Tuple
from collections import deque

from algorithms.base_algorithm import AIAlgorithm, AlgorithmStats, StepResult
from algorithms.adversarial.combat_rules import (
    CombatState,
    evaluate_state,
    get_actions,
    get_successor,
)
from maps.tilemap import TileMap


class MinimaxAlgorithm(AIAlgorithm):
    """Minimax turn-based search solver.

    Explores game tree of depth 2 to choose optimal combat moves.
    """

    def __init__(self, depth: int = 2) -> None:
        self._max_depth = depth
        self._stats_obj = AlgorithmStats()
        self._combat_state: Optional[CombatState] = None

        # Visual overlays stats
        self._nodes_evaluated = 0
        self._best_action = ""

        # Pathfinder states
        self._start: Tuple[int, int] = (0, 0)
        self._goal: Tuple[int, int] = (0, 0)
        self._tilemap: Optional[TileMap] = None
        self._path: List[Tuple[int, int]] = []
        self._path_index: int = 0
        self._pf_phase: str = "IDLE"
        self._locked_doors: Set[Tuple[int, int]] = set()

    def initialise(
        self,
        start: Tuple[int, int],
        goal: Tuple[int, int],
        tilemap: TileMap,
        game_state: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize algorithm state with pathfinding support."""
        self._stats_obj = AlgorithmStats()
        self._start = start
        self._goal = goal
        self._tilemap = tilemap
        self._pf_phase = "SEARCHING"
        self._path = []
        self._path_index = 0
        self._locked_doors = set()
        if game_state and "doors" in game_state:
            for col, row, locked in game_state["doors"]:
                if locked:
                    self._locked_doors.add((col, row))

    def set_combat_state(self, state: CombatState) -> None:
        """Set the active combat state to evaluate."""
        self._combat_state = state

    def is_done(self) -> bool:
        """Done when pathfinding is finished."""
        return self._pf_phase in {"DONE", "FAILED"}

    @property
    def stats(self) -> AlgorithmStats:
        return self._stats_obj

    def step(self) -> StepResult:
        """Execute pathfinding or minimax search on the combat state."""
        # If in pathfinding mode, navigate the map
        if self._pf_phase not in {"IDLE"}:
            return self._pf_step()

        if self._combat_state is None:
            return StepResult("wait")

        start_time = time.perf_counter()
        self._nodes_evaluated = 0

        tree_nodes = []
        best_val = -999999.0
        best_act = "ATTACK"

        for action in get_actions():
            successor = get_successor(self._combat_state, action)
            self._nodes_evaluated += 1

            # Evaluate successor at depth 1 (Monster minimizing)
            val = self._minimax_tracked(successor, depth=1, maximizing=False, tree_nodes=tree_nodes, path=[action])
            tree_nodes.append({
                "depth": 1,
                "action": action,
                "value": val,
                "is_max": True
            })
            if val > best_val:
                best_val = val
                best_act = action

        self._best_action = best_act
        self._stats_obj.elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        vis_data = {
            "tree_depth": self._max_depth,
            "nodes_evaluated": self._nodes_evaluated,
            "best_action": self._best_action,
            "pruned_count": 0,
            "tree_nodes": tree_nodes,
        }

        return StepResult(best_act, vis_data)

    def _minimax_tracked(self, state: CombatState, depth: int, maximizing: bool, tree_nodes: list, path: list) -> float:
        """Recursive minimax evaluation tracking nodes."""
        if depth == 0 or state.player_hp <= 0 or state.monster_hp <= 0:
            val = evaluate_state(state)
            return val

        if maximizing:
            max_val = -999999.0
            for action in get_actions():
                successor = get_successor(state, action)
                self._nodes_evaluated += 1
                val = self._minimax_tracked(successor, depth - 1, False, tree_nodes, path + [action])
                max_val = max(max_val, val)
                tree_nodes.append({
                    "depth": 2 - depth + 1,
                    "action": action,
                    "value": val,
                    "is_max": True,
                    "parent_action": path[-1] if path else None
                })
            return max_val
        else:
            min_val = 999999.0
            for action in get_actions():
                successor = get_successor(state, action)
                self._nodes_evaluated += 1
                val = self._minimax_tracked(successor, depth - 1, True, tree_nodes, path + [action])
                min_val = min(min_val, val)
                tree_nodes.append({
                    "depth": 2 - depth + 1,
                    "action": action,
                    "value": val,
                    "is_max": False,
                    "parent_action": path[-1] if path else None
                })
            return min_val

    # --- Pathfinder Methods ---

    def _pathfind_bfs(self) -> None:
        """BFS pathfinder to navigate map."""
        if not self._tilemap:
            self._pf_phase = "FAILED"
            return

        queue = deque([(self._start, [self._start])])
        visited = {self._start}

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
                if (nc, nr) in self._locked_doors and (nc, nr) != self._goal:
                    continue
                visited.add((nc, nr))
                queue.append(((nc, nr), path + [(nc, nr)]))

        self._pf_phase = "FAILED"

    def _pf_step(self) -> StepResult:
        """Execute one pathfinding step."""
        if self._pf_phase == "SEARCHING":
            self._pathfind_bfs()
            return StepResult(action="wait", vis_data={"path": self._path})

        if self._pf_phase == "EXECUTING":
            if self._path_index >= len(self._path) - 1:
                self._pf_phase = "DONE"
                return StepResult(action="done", vis_data={"path": self._path})

            curr = self._path[self._path_index]
            nxt = self._path[self._path_index + 1]
            self._path_index += 1

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

            return StepResult(action=action, vis_data={"path": self._path})

        return StepResult(action="done", vis_data={})

    def _minimax(self, state: CombatState, depth: int, maximizing: bool) -> float:
        """Recursive minimax evaluation."""
        # Base case
        if depth == 0 or state.player_hp <= 0 or state.monster_hp <= 0:
            return evaluate_state(state)

        if maximizing:
            max_val = -999999.0
            for action in get_actions():
                successor = get_successor(state, action)
                self._nodes_evaluated += 1
                val = self._minimax(successor, depth - 1, False)
                max_val = max(max_val, val)
            return max_val
        else:
            min_val = 999999.0
            for action in get_actions():
                successor = get_successor(state, action)
                self._nodes_evaluated += 1
                val = self._minimax(successor, depth - 1, True)
                min_val = min(min_val, val)
            return min_val
