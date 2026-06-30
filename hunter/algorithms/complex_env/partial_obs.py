"""
partial_obs.py — Partially Observable search algorithm with Fog of War replanning.
"""

from __future__ import annotations

import heapq
import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from algorithms.base_algorithm import AIAlgorithm, AlgorithmStats, StepResult
from maps.tilemap import TileMap
from utils.priority_queue import PriorityQueue

logger = logging.getLogger(__name__)


class PartialObsAlgorithm(AIAlgorithm):
    """Partially Observable A* replanning solver.

    Discovers wall obstacles dynamically within a sensor radius (fog of war) and replans paths.
    """

    def __init__(self, sensor_radius: int = 5) -> None:
        self._sensor_radius = sensor_radius

        self._start: Tuple[int, int] = (0, 0)
        self._goal: Tuple[int, int] = (0, 0)
        self._tilemap: Optional[TileMap] = None

        self._current_node: Tuple[int, int] = (0, 0)
        self._known_walls: Set[Tuple[int, int]] = set()
        self._revealed_tiles: Set[Tuple[int, int]] = set()

        self._phase: str = "SEARCHING"
        self._path: List[Tuple[int, int]] = []
        self._path_index: int = 0
        self._stats_obj = AlgorithmStats()

        # For visualization
        self._vis_visited: Set[Tuple[int, int]] = set()
        self._vis_frontier: Set[Tuple[int, int]] = set()

    def _manhattan(self, p1: Tuple[int, int], p2: Tuple[int, int]) -> int:
        return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])

    def initialise(
        self,
        start: Tuple[int, int],
        goal: Tuple[int, int],
        tilemap: TileMap,
        game_state: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Set up search variables."""
        self._start = start
        self._goal = goal
        self._tilemap = tilemap

        self._locked_doors = set()
        if game_state and "doors" in game_state:
            for col, row, locked in game_state["doors"]:
                if locked:
                    self._locked_doors.add((col, row))

        self._current_node = start
        self._known_walls = set()
        self._revealed_tiles = set()
        
        self._phase = "SEARCHING"
        self._path = []
        self._path_index = 0
        
        self._vis_visited = set()
        self._vis_frontier = set()

        self._fog_grid = None
        if game_state and "fog_grid" in game_state and game_state["fog_grid"] is not None:
            self._fog_grid = game_state["fog_grid"]
            # Populate revealed_tiles from fog_grid
            for r in range(len(self._fog_grid)):
                for c in range(len(self._fog_grid[r])):
                    if not self._fog_grid[r][c]: # False = revealed
                        self._revealed_tiles.add((c, r))
                        tile = self._tilemap.get_tile(c, r)
                        is_wall = not tile.walkable or ((c, r) in self._locked_doors and (c, r) != self._goal)
                        if is_wall:
                            self._known_walls.add((c, r))

        # Initialize borders as known walls
        for r in range(tilemap.height):
            self._known_walls.add((0, r))
            self._known_walls.add((tilemap.width - 1, r))
        for c in range(tilemap.width):
            self._known_walls.add((c, 0))
            self._known_walls.add((c, tilemap.height - 1))

        self._stats_obj = AlgorithmStats(nodes_visited=1)

    def is_done(self) -> bool:
        """Return True when AI completes execution."""
        return self._phase in {"DONE", "FAILED"}

    @property
    def stats(self) -> AlgorithmStats:
        """Return live metrics."""
        return self._stats_obj

    def get_vis_data(self) -> Dict[str, Any]:
        """Format visualisation data, highlighting sensor radius."""
        fog = set()
        if self._tilemap:
            for r in range(self._tilemap.height):
                for c in range(self._tilemap.width):
                    if (c, r) not in self._revealed_tiles:
                        fog.add((c, r))
        return {
            "visited": self._vis_visited,
            "frontier": self._vis_frontier,
            "current": self._current_node,
            "path": self._path,
            "revealed": self._revealed_tiles,
            "sensor_radius": self._sensor_radius,
            "fog": fog,
        }

    def _reveal_sensor_area(self) -> bool:
        """Reveal surroundings and return True if any new walls are found."""
        if self._tilemap is None:
            return False

        new_wall_discovered = False
        cx, cy = self._current_node
        r = self._sensor_radius

        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                col = cx + dx
                row = cy + dy
                if 0 <= col < self._tilemap.width and 0 <= row < self._tilemap.height:
                    # Circular radius check
                    if dx * dx + dy * dy <= r * r:
                        self._revealed_tiles.add((col, row))
                        tile = self._tilemap.get_tile(col, row)
                        is_wall = not tile.walkable or ((col, row) in self._locked_doors and (col, row) != self._goal)
                        if is_wall:
                            if (col, row) not in self._known_walls:
                                self._known_walls.add((col, row))
                                new_wall_discovered = True

        return new_wall_discovered

    def _run_astar_on_known_map(self) -> List[Tuple[int, int]]:
        """Run standard A* pathfinder on the current known map."""
        if self._tilemap is None:
            return []

        start = self._current_node
        goal = self._goal

        pq = PriorityQueue()
        pq.push(0.0, start)
        
        g_score = {start: 0.0}
        parent = {start: None}
        closed_set = set()

        self._vis_visited.clear()
        self._vis_frontier.clear()

        while not pq.is_empty():
            curr = pq.pop()
            if curr in closed_set:
                continue
            closed_set.add(curr)
            self._vis_visited.add(curr)

            if curr == goal:
                # Reconstruct path
                path = []
                p = goal
                while p is not None:
                    path.append(p)
                    p = parent[p]
                path.reverse()
                return path

            # Neighbors
            for neighbor_vec in self._tilemap.neighbors(curr[0], curr[1], treat_goal_as_walkable=self._goal):
                n = (neighbor_vec.x, neighbor_vec.y)
                # Check if it is a known wall or locked door
                if n in self._known_walls or (n in self._locked_doors and n != self._goal):
                    continue

                g_tentative = g_score[curr] + self._tilemap.move_cost(n[0], n[1])
                if n not in g_score or g_tentative < g_score[n]:
                    g_score[n] = g_tentative
                    f_val = g_tentative + self._manhattan(n, goal)
                    parent[n] = curr
                    pq.push(f_val, n)
                    self._vis_frontier.add(n)
                    self._stats_obj.nodes_visited += 1

            # Update memory peak
            open_set_size = len({node for _, _, node in pq._heap})
            self._stats_obj.memory_peak = max(self._stats_obj.memory_peak, len(closed_set) + open_set_size)

            self._stats_obj.nodes_expanded += 1

        return []

    def step(self) -> StepResult:
        """Observe sensor radius, replan if blocked, and execute moves."""
        if self._tilemap is None or self.is_done():
            return StepResult("done")

        # Check goal reached
        if self._current_node == self._goal:
            self._phase = "DONE"
            return StepResult("done", self.get_vis_data())

        # 1. Reveal surroundings
        new_walls_found = self._reveal_sensor_area()

        # 2. Check path validity
        replan_needed = False
        if not self._path:
            replan_needed = True
        else:
            # Check if remaining path goes through any newly discovered known walls
            remaining_path = self._path[self._path_index:]
            for node in remaining_path:
                if node in self._known_walls:
                    replan_needed = True
                    break

        # 3. Replan if needed
        if replan_needed or new_walls_found:
            new_path = self._run_astar_on_known_map()
            if not new_path:
                self._phase = "FAILED"
                logger.warning("PartialObs: Exit blocked by known walls!")
                return StepResult("done", self.get_vis_data())
            
            self._path = new_path
            self._path_index = 0

        # 4. Advance player along path
        if self._path_index >= len(self._path) - 1:
            self._phase = "DONE"
            return StepResult("done", self.get_vis_data())

        curr_pos = self._path[self._path_index]
        next_pos = self._path[self._path_index + 1]
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

        # Update stats
        self._current_node = next_pos
        self._stats_obj.path_length = len(self._path) - 1
        self._stats_obj.path_cost += self._tilemap.move_cost(next_pos[0], next_pos[1])

        return StepResult(action, self.get_vis_data())
