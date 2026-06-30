"""
local_beam.py — Local Beam Search algorithm implementation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

from algorithms.base_algorithm import AIAlgorithm, AlgorithmStats, StepResult
from maps.tilemap import TileMap


class LocalBeamAlgorithm(AIAlgorithm):
    """Local Beam Search pathfinder.

    Maintains k candidate paths in parallel, expanding successors and pruning down to the best k.
    """

    def __init__(self, beam_width: int = 4) -> None:
        self._beam_width = beam_width

        self._start: Tuple[int, int] = (0, 0)
        self._goal: Tuple[int, int] = (0, 0)
        self._tilemap: Optional[TileMap] = None

        self._beams: List[List[Tuple[int, int]]] = []  # List of paths
        self._phase: str = "SEARCHING"

        self._path: List[Tuple[int, int]] = []
        self._path_index: int = 0
        self._current_node: Optional[Tuple[int, int]] = None

        self._candidates: Set[Tuple[int, int]] = set()
        self._successors_count: int = 0
        self._stats_obj = AlgorithmStats()

    def _heuristic(self, col: int, row: int) -> float:
        """Manhattan distance heuristic. Return negative distance so higher value is better."""
        return -float(abs(col - self._goal[0]) + abs(row - self._goal[1]))

    def initialise(
        self,
        start: Tuple[int, int],
        goal: Tuple[int, int],
        tilemap: TileMap,
        game_state: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Set up Local Beam variables."""
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

        self._beams = [[start]]
        self._phase = "SEARCHING"

        self._path = []
        self._path_index = 0
        self._current_node = None

        self._candidates = set()
        self._stats_obj = AlgorithmStats(nodes_visited=1)
        self._stats_obj.beam_count = self._beam_width

    def is_done(self) -> bool:
        """Return True when AI execution completes or fails."""
        return self._phase in {"DONE", "FAILED"}

    @property
    def stats(self) -> AlgorithmStats:
        """Return live metrics."""
        return self._stats_obj

    def get_vis_data(self) -> Dict[str, Any]:
        """Format visualisation dictionary."""
        beams_ends = [p[-1] for p in self._beams]
        return {
            "beams": beams_ends,
            "candidates": self._candidates,
            "current": self._current_node,
            "path": self._path,
        }

    def _reconstruct_path(self, final_path: List[Tuple[int, int]]) -> None:
        """Set path and compute statistics."""
        self._path = final_path
        self._stats_obj.path_length = len(final_path) - 1
        
        cost = 0.0
        if self._tilemap:
            for col, row in final_path[1:]:
                cost += self._tilemap.move_cost(col, row)
        self._stats_obj.path_cost = cost

    def step(self) -> StepResult:
        """Execute one beam expansion step or drive the character."""
        if self._tilemap is None:
            return StepResult("wait")

        if self._phase == "SEARCHING":
            if not self._beams:
                self._phase = "FAILED"
                return StepResult("done", self.get_vis_data())

            # Check if any beam has reached the goal
            for p in self._beams:
                if p[-1] == self._goal:
                    self._reconstruct_path(p)
                    self._phase = "EXECUTING"
                    return StepResult("wait", self.get_vis_data())

            successors: List[List[Tuple[int, int]]] = []
            self._candidates.clear()

            # Expand each beam state
            for p in self._beams:
                curr = p[-1]
                self._stats_obj.nodes_expanded += 1

                for neighbor_vec in self._tilemap.neighbors(curr[0], curr[1], treat_goal_as_walkable=self._goal):
                    n = (neighbor_vec.x, neighbor_vec.y)
                    if n in self._locked_doors and n != self._goal:
                        continue
                    # We no longer block pathfinding on unrevealed/fog tiles so AI can explore towards goals.
                    # Simple cycle prevention along this specific beam path
                    if n not in p:
                        new_path = p + [n]
                        successors.append(new_path)
                        self._candidates.add(n)

            if not successors:
                self._phase = "FAILED"
                return StepResult("done", self.get_vis_data())

            self._stats_obj.nodes_visited += len(self._candidates)
            
            # Update memory peak
            self._stats_obj.memory_peak = max(self._stats_obj.memory_peak, len(self._beams) + len(self._candidates))

            # Sort successors by heuristic value (higher is better)
            successors.sort(key=lambda path: self._heuristic(path[-1][0], path[-1][1]), reverse=True)

            # Keep top k successors
            self._beams = successors[:self._beam_width]
            
            # Set current visualization focus node to the best beam endpoint
            if self._beams:
                self._current_node = self._beams[0][-1]

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
