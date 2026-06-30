"""
benchmark_runner.py — Runs allowed level algorithms headlessly and records performance metrics.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, List, Tuple, Any

from config.level_config import LEVEL_MAP
from config.algorithm_config import ALGORITHM_MAP
from maps.loader import load_level
from algorithms import create_algorithm
from utils.vec2 import Vec2


@dataclass
class BenchmarkResult:
    algorithm_key: str
    display_name: str
    success: bool
    time_ms: float
    nodes_expanded: int
    path_cost: float
    path_length: int


class BenchmarkRunner:
    """Simulates search algorithms headlessly without updating the Pygame screen."""

    @staticmethod
    def run_benchmark(level_id: int, allowed_algorithms: List[str]) -> Dict[str, BenchmarkResult]:
        """Runs each algorithm in allowed_algorithms on level_id and returns results."""
        results: Dict[str, BenchmarkResult] = {}
        
        # Load level once
        try:
            tilemap = load_level(level_id)
        except Exception:
            return {}

        spawn_pos = (tilemap.spawn_pos.x, tilemap.spawn_pos.y)
        exit_pos = (tilemap.exit_pos.x, tilemap.exit_pos.y)

        # Build game state snapshot (locked doors)
        locked_doors = []
        for door_info in getattr(tilemap, "doors_data", []):
            if door_info.get("key_required"):
                locked_doors.append((door_info["col"], door_info["row"], True))

        game_state = {
            "player_pos": spawn_pos,
            "exit_pos": exit_pos,
            "doors": locked_doors,
        }

        for algo_key in allowed_algorithms:
            meta = ALGORITHM_MAP.get(algo_key)
            display_name = meta.display_name if meta else algo_key.upper()

            # Skip CSP and Adversarial algorithms from standard pathfinding benchmark if they aren't pathfinders
            # Note: backtracking and minimax DO implement pathfinder fallback, but we should handle failure gracefully.
            try:
                algo = create_algorithm(algo_key)
                
                # Perform simulation
                start_time = time.perf_counter()
                
                # Initialise
                algo.initialise(spawn_pos, exit_pos, tilemap, game_state)
                
                steps = 0
                max_steps = 10000
                success = False
                
                while not algo.is_done() and steps < max_steps:
                    res = algo.step()
                    steps += 1
                    if res.action == "done" and algo.is_done():
                        # check if solver reports success or reached exit
                        success = getattr(algo, "is_success", lambda: True)()
                        break

                # If it stopped due to limit or reports not success
                if steps >= max_steps:
                    success = False
                elif not algo.is_done():
                    success = False
                else:
                    success = True

                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                stats = algo.stats

                results[algo_key] = BenchmarkResult(
                    algorithm_key=algo_key,
                    display_name=display_name,
                    success=success,
                    time_ms=elapsed_ms,
                    nodes_expanded=stats.nodes_expanded,
                    path_cost=stats.path_cost,
                    path_length=stats.path_length,
                )

            except Exception:
                # Graceful error handling
                results[algo_key] = BenchmarkResult(
                    algorithm_key=algo_key,
                    display_name=display_name,
                    success=False,
                    time_ms=0.0,
                    nodes_expanded=0,
                    path_cost=0.0,
                    path_length=0,
                )

        return results
