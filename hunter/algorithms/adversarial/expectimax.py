"""
expectimax.py — Expectimax adversarial search algorithm implementation.
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


class ExpectimaxAlgorithm(AIAlgorithm):
    """Expectimax turn-based search solver.

    Player is max node, Monster is chance node (70% optimal, 30% random actions).
    """

    def __init__(self, depth: int = 2) -> None:
        self._max_depth = depth
        self._stats_obj = AlgorithmStats()
        self._combat_state: Optional[CombatState] = None

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
        """Execute pathfinding or expectimax search on the combat state."""
        # If in pathfinding mode, navigate the map
        if self._pf_phase not in {"IDLE"}:
            return self._pf_step()

        if self._combat_state is None:
            return StepResult("wait")

        start_time = time.perf_counter()

        tree_nodes = []
        best_val = -999999.0
        best_act = "ATTACK"
        expected_values = {}

        for action in get_actions():
            successor = get_successor(self._combat_state, action)
            self._nodes_evaluated += 1

            # Depth 1: Monster chance turn
            val = self._expectimax_tracked(successor, depth=1, maximizing=False, tree_nodes=tree_nodes, path=[action])
            expected_values[action] = val
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
            "expected_values": expected_values,
        }

        return StepResult(best_act, vis_data)

    def _expectimax_tracked(self, state: CombatState, depth: int, maximizing: bool, tree_nodes: list, path: list) -> float:
        """Recursive expectimax evaluation tracking nodes."""
        if depth == 0 or state.player_hp <= 0 or state.monster_hp <= 0:
            return evaluate_state(state)

        if maximizing:
            max_val = -999999.0
            for action in get_actions():
                successor = get_successor(state, action)
                self._nodes_evaluated += 1
                val = self._expectimax_tracked(successor, depth - 1, False, tree_nodes, path + [action])
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
            # Chance node: 70% optimal monster action (minimizing player utility) + 30% random choice
            actions = get_actions()
            if not actions:
                return 0.0

            # Evaluate each successor state to identify the optimal action for the monster
            monster_evals = []
            for action in actions:
                successor = get_successor(state, action)
                val = evaluate_state(successor)
                monster_evals.append((action, val))
            # Sort ascending so the action with the lowest player utility is first
            monster_evals.sort(key=lambda x: x[1])
            optimal_action = monster_evals[0][0]

            total_val = 0.0
            for action in actions:
                successor = get_successor(state, action)
                self._nodes_evaluated += 1
                val = self._expectimax_tracked(successor, depth - 1, True, tree_nodes, path + [action])
                
                # Probability = 70% (if optimal action) + 30% split uniformly
                prob = 0.3 / len(actions)
                if action == optimal_action:
                    prob += 0.7

                total_val += val * prob
                tree_nodes.append({
                    "depth": 2 - depth + 1,
                    "action": action,
                    "value": val,
                    "is_max": False,
                    "parent_action": path[-1] if path else None
                })
            return total_val


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

    def _expectimax(self, state: CombatState, depth: int, maximizing: bool) -> float:
        """Recursive expectimax evaluation."""
        if depth == 0 or state.player_hp <= 0 or state.monster_hp <= 0:
            return evaluate_state(state)

        if maximizing:
            max_val = -999999.0
            for action in get_actions():
                successor = get_successor(state, action)
                self._nodes_evaluated += 1
                val = self._expectimax(successor, depth - 1, False)
                max_val = max(max_val, val)
            return max_val
        else:
            # Chance node for Monster
            # First, evaluate each of the 4 actions
            action_vals = []
            for action in get_actions():
                successor = get_successor(state, action)
                self._nodes_evaluated += 1
                val = self._expectimax(successor, depth - 1, True)
                action_vals.append((action, val))

            # Monster wants to MINIMIZE player utility
            # Sort ascending so the first item has the lowest value (optimal for monster)
            action_vals.sort(key=lambda item: item[1])
            
            # Probability distribution:
            # 70% optimal, 30% split equally among all 4 actions
            # Optimal action (index 0) prob = 0.7 + (0.3 / 4) = 0.775
            # Non-optimal actions (indices 1, 2, 3) prob = 0.3 / 4 = 0.075 each
            expected_val = 0.0
            for i, (_, val) in enumerate(action_vals):
                prob = 0.775 if i == 0 else 0.075
                expected_val += prob * val
                
            return expected_val
