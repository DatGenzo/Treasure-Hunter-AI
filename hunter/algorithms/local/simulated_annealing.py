"""
simulated_annealing.py — Simulated Annealing local search algorithm implementation.
"""

from __future__ import annotations

import logging
import math
import random
from typing import Any, Dict, List, Optional, Set, Tuple

from algorithms.base_algorithm import AIAlgorithm, AlgorithmStats, StepResult
from maps.tilemap import TileMap

logger = logging.getLogger(__name__)


class SimulatedAnnealingAlgorithm(AIAlgorithm):
    """Simulated Annealing local search solver.

    Probabilistically accepts worse moves based on current temperature to escape local optima.
    """

    def __init__(
        self,
        initial_temp: float = 100.0,
        cooling_rate: float = 0.95,
        min_temp: float = 0.01,
    ) -> None:
        self._initial_temp = initial_temp
        self._cooling_rate = cooling_rate
        self._min_temp = min_temp

        self._start: Tuple[int, int] = (0, 0)
        self._goal: Tuple[int, int] = (0, 0)
        self._tilemap: Optional[TileMap] = None

        self._current_node: Tuple[int, int] = (0, 0)
        self._temp: float = initial_temp
        self._treasures: Set[Tuple[int, int]] = set()
        self._collected_treasures: Set[Tuple[int, int]] = set()

        self._phase: str = "SEARCHING"
        self._path: List[Tuple[int, int]] = []
        self._stats_obj = AlgorithmStats()

        # Visualization variables
        self._candidates: Set[Tuple[int, int]] = set()
        self._candidate_node: Optional[Tuple[int, int]] = None
        self._accepted: bool = False

        self._accepted_node: Optional[Tuple[int, int]] = None
        self._rejected_node: Optional[Tuple[int, int]] = None

    def _value(self, col: int, row: int) -> float:
        """Calculate the potential gradient value for the cell (col, row)."""
        if self._tilemap is None or not self._tilemap.is_walkable(col, row):
            return -999999.0

        if (col, row) in self._locked_doors and (col, row) != self._goal:
            return -999999.0

        # Fog tiles are treated as walkable.

        # Remaining active treasures
        active_treasures = self._treasures - self._collected_treasures
        if not active_treasures:
            dist = abs(col - self._goal[0]) + abs(row - self._goal[1])
            return 100.0 / (dist + 1)

        val = 0.0
        for t_col, t_row in active_treasures:
            dist = abs(col - t_col) + abs(row - t_row)
            if dist == 0:
                val += 200.0
            else:
                val += 15.0 / dist

        # Subtract movement cost penalty
        val -= self._tilemap.move_cost(col, row) * 0.5
        return val

    def initialise(
        self,
        start: Tuple[int, int],
        goal: Tuple[int, int],
        tilemap: TileMap,
        game_state: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Set up Simulated Annealing search parameters."""
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
        self._temp = self._initial_temp
        self._path = [start]
        self._phase = "SEARCHING"

        # Scan map for treasures
        self._treasures = {
            (col, row) for col, row, type_str in tilemap.item_spawns if type_str == "treasure"
        }
        self._collected_treasures = set()

        self._candidates = set()
        self._candidate_node = None
        self._accepted = False
        self._accepted_node = None
        self._rejected_node = None

        self._stats_obj = AlgorithmStats(nodes_visited=1)
        self._stats_obj.temperature = self._temp

    def is_done(self) -> bool:
        """Return True when temperature drops too low or goal reached."""
        return self._phase in {"DONE", "FAILED"}

    @property
    def stats(self) -> AlgorithmStats:
        """Return live metrics."""
        return self._stats_obj

    def get_vis_data(self) -> Dict[str, Any]:
        """Format visualisation dictionary."""
        best_set = {self._accepted_node} if (self._accepted_node and self._accepted) else set()
        rejected_set = {self._rejected_node} if (self._rejected_node and not self._accepted) else set()
        return {
            # For LocalOverlay rendering
            "candidates": self._candidates,
            "best": best_set,
            "rejected": rejected_set,
            "current": self._current_node,
            "path": self._path,
            # For prompt specifications
            "candidate": self._candidate_node,
            "temperature": self._temp,
            "accepted": self._accepted,
        }

    def step(self) -> StepResult:
        """Pick a random neighbor, accept probabilistically, and cool temperature."""
        if self._tilemap is None or self.is_done():
            return StepResult("done")

        # Update collected treasures list
        if self._current_node in self._treasures:
            self._collected_treasures.add(self._current_node)

        # Check goal reached
        if self._current_node == self._goal:
            self._phase = "DONE"
            return StepResult("done", self.get_vis_data())

        # Check temperature limit
        if self._temp < self._min_temp:
            logger.info("Simulated Annealing: Minimum temperature hit. Stopping.")
            self._phase = "DONE"
            return StepResult("done", self.get_vis_data())

        # Generate neighbors
        neighbors_vec = self._tilemap.neighbors(self._current_node[0], self._current_node[1], treat_goal_as_walkable=self._goal)
        neighbors = [(n.x, n.y) for n in neighbors_vec]
        
        self._candidates = set(neighbors)
        self._stats_obj.nodes_expanded += 1

        if not neighbors:
            self._phase = "FAILED"
            return StepResult("done", self.get_vis_data())

        # Select a random neighbor candidate
        candidate = random.choice(neighbors)
        self._candidate_node = candidate
        self._stats_obj.nodes_visited += 1

        val_curr = self._value(self._current_node[0], self._current_node[1])
        val_cand = self._value(candidate[0], candidate[1])
        dE = val_cand - val_curr

        accepted = False
        if dE > 0:
            accepted = True
        else:
            # Acceptance probability P = e^(dE / T)
            p = math.exp(dE / self._temp)
            if random.random() < p:
                accepted = True

        self._accepted = accepted

        # Cool temperature
        self._temp *= self._cooling_rate
        self._stats_obj.temperature = self._temp
        self._stats_obj.memory_peak = max(self._stats_obj.memory_peak, 1 + len(neighbors))

        if accepted:
            self._accepted_node = candidate
            self._rejected_node = None

            # Calculate direction action
            dx = candidate[0] - self._current_node[0]
            dy = candidate[1] - self._current_node[1]

            action = "wait"
            if dx == 0 and dy == -1:
                action = "move_n"
            elif dx == 0 and dy == 1:
                action = "move_s"
            elif dx == -1 and dy == 0:
                action = "move_w"
            elif dx == 1 and dy == 0:
                action = "move_e"

            # Perform move
            self._current_node = candidate
            self._path.append(candidate)
            self._stats_obj.path_length = len(self._path) - 1
            self._stats_obj.path_cost += self._tilemap.move_cost(candidate[0], candidate[1])

            return StepResult(action, self.get_vis_data())
        else:
            self._accepted_node = None
            self._rejected_node = candidate
            # Stand still for this step
            return StepResult("wait", self.get_vis_data())
