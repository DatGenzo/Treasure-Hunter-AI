"""
stats_tracker.py — Handles saving, loading, and comparing run statistics between human and AI players.

Storage schema (v2):
  {
    "<level_id>": {
      "<algorithm_key>": [RunStats_dict, ...]   # up to MAX_RUNS_PER_KEY most recent runs
    }
  }
Backward compatibility: legacy "human" / "ai" keys that contain a single dict (not a list)
are transparently migrated to the new list schema on first load.
"""

from __future__ import annotations

import json
import os
import logging
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

from config.settings import SAVES_DIR

logger = logging.getLogger(__name__)

MAX_RUNS_PER_KEY: int = 5


@dataclass
class RunStats:
    """Statistics captured during a single game run.

    Extended fields track movement granularity, memory usage, collection rates,
    mission completion percentage, remaining health, and a computed star rating.
    """

    is_ai: bool
    algorithm_key: str
    time_elapsed: float
    path_cost: float
    nodes_expanded: int
    treasures_collected: int
    deaths: int
    combat_wins: int
    steps_taken: int = 0
    memory_peak: int = 0
    treasures_total: int = 0
    completion_pct: float = 100.0
    hp_remaining: int = 100
    star_rating: int = 1


class StatsTracker:
    """Loads, saves, and computes comparison statistics for game levels."""

    def __init__(self, stats_file_path: Optional[str] = None) -> None:
        if stats_file_path is None:
            self.file_path = os.path.join(SAVES_DIR, "stats.json")
        else:
            self.file_path = stats_file_path

        # Create SAVES_DIR if it doesn't exist
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

        self._data: Dict[str, Dict[str, Any]] = self._load_data()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_data(self) -> Dict[str, Dict[str, Any]]:
        """Load JSON data from file, migrating legacy schema if needed."""
        if not os.path.exists(self.file_path):
            return {}

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return self._migrate(data)
        except Exception:
            logger.exception("Failed to load statistics file. Starting fresh.")

        return {}

    def _migrate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate legacy single-dict entries to list schema in-place."""
        for lvl_key, lvl_data in data.items():
            if not isinstance(lvl_data, dict):
                continue
            for mode_key, value in list(lvl_data.items()):
                if isinstance(value, dict):
                    # Legacy: single dict → wrap in list
                    lvl_data[mode_key] = [value]
                    logger.debug("Migrated legacy stats entry: level=%s key=%s", lvl_key, mode_key)
        return data

    def _save_data(self) -> None:
        """Write current stats data to disk."""
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=4)
        except Exception:
            logger.exception("Failed to save statistics data to %s", self.file_path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save_run(self, level_id: int, stats: RunStats) -> None:
        """Save a new run for the specified level.

        Keeps up to MAX_RUNS_PER_KEY most recent runs per algorithm key.
        Also maintains the legacy ``human`` / ``ai`` aggregate keys for
        backward compatibility with get_comparison().
        """
        lvl_key = str(level_id)
        # Derive a stable per-algorithm key for the new schema
        algo_key = stats.algorithm_key if stats.algorithm_key else ("ai" if stats.is_ai else "human")
        mode_key = "ai" if stats.is_ai else "human"  # legacy key

        if lvl_key not in self._data:
            self._data[lvl_key] = {}

        stats_dict = asdict(stats)

        # --- New per-algorithm list schema ---
        run_list: List[Dict[str, Any]] = self._data[lvl_key].get(algo_key, [])
        if not isinstance(run_list, list):
            run_list = [run_list]  # migrate stale entry
        run_list.append(stats_dict)
        # Keep only the MAX_RUNS_PER_KEY most recent
        self._data[lvl_key][algo_key] = run_list[-MAX_RUNS_PER_KEY:]

        # --- Legacy human/ai best-run key (backward compat) ---
        existing = self._data[lvl_key].get(mode_key)
        # existing may now be a list (after migration); get the best from it
        if isinstance(existing, list):
            existing_best = min(existing, key=lambda d: d.get("path_cost", 999999.0), default=None)
        else:
            existing_best = existing

        if existing_best:
            prev_cost = existing_best.get("path_cost", 999999.0)
            prev_time = existing_best.get("time_elapsed", 999999.0)
            if stats.path_cost < prev_cost or (stats.path_cost == prev_cost and stats.time_elapsed < prev_time):
                self._data[lvl_key][mode_key] = stats_dict
                logger.info("Saved new BEST run for Level %d (%s)", level_id, mode_key.upper())
            else:
                logger.info("New run for Level %d (%s) was not better than existing best.", level_id, mode_key.upper())
        elif mode_key != algo_key:
            # Only write legacy key if it is distinct from the algo_key
            self._data[lvl_key][mode_key] = stats_dict
            logger.info("Saved initial run for Level %d (%s)", level_id, mode_key.upper())

        self._save_data()

    def get_comparison(self, level_id: int) -> Dict[str, Any]:
        """Return best human / AI stats for the level (backward-compatible).

        Format:
        {
            "human": { ...stats dict or None... },
            "ai": { ...stats dict or None... }
        }
        """
        lvl_key = str(level_id)
        lvl_data = self._data.get(lvl_key, {})

        def _resolve(entry: Any) -> Optional[Dict[str, Any]]:
            if entry is None:
                return None
            if isinstance(entry, list):
                # Return the best (lowest cost) from the list
                return min(entry, key=lambda d: d.get("path_cost", 999999.0), default=None)
            return entry  # legacy single dict

        return {
            "human": _resolve(lvl_data.get("human")),
            "ai": _resolve(lvl_data.get("ai")),
        }

    def get_all_algorithm_results(self, level_id: int) -> Dict[str, RunStats]:
        """Return the best run (by lowest path_cost) per algorithm key for a level.

        Returns:
            Dict mapping algorithm_key -> RunStats dataclass instance.
            Only keys with actual run history are included.
        """
        lvl_key = str(level_id)
        lvl_data = self._data.get(lvl_key, {})
        results: Dict[str, RunStats] = {}

        # Legacy mode keys to skip (they are mirrors of algo keys, avoid duplication)
        legacy_keys = {"human", "ai"}

        for key, value in lvl_data.items():
            run_list: List[Dict[str, Any]]
            if isinstance(value, list):
                run_list = value
            elif isinstance(value, dict):
                run_list = [value]
            else:
                continue

            if not run_list:
                continue

            # Pick the best run (lowest path_cost)
            best_dict = min(run_list, key=lambda d: d.get("path_cost", 999999.0))

            # Skip legacy aggregate keys if the real algo key is also present
            algo_key = best_dict.get("algorithm_key", key)
            if key in legacy_keys and algo_key in lvl_data and algo_key not in legacy_keys:
                continue

            try:
                results[key] = RunStats(
                    is_ai=best_dict.get("is_ai", False),
                    algorithm_key=best_dict.get("algorithm_key", key),
                    time_elapsed=best_dict.get("time_elapsed", 0.0),
                    path_cost=best_dict.get("path_cost", 0.0),
                    nodes_expanded=best_dict.get("nodes_expanded", 0),
                    treasures_collected=best_dict.get("treasures_collected", 0),
                    deaths=best_dict.get("deaths", 0),
                    combat_wins=best_dict.get("combat_wins", 0),
                    steps_taken=best_dict.get("steps_taken", 0),
                    memory_peak=best_dict.get("memory_peak", 0),
                    treasures_total=best_dict.get("treasures_total", 0),
                    completion_pct=best_dict.get("completion_pct", 100.0),
                    hp_remaining=best_dict.get("hp_remaining", 100),
                    star_rating=best_dict.get("star_rating", 1),
                )
            except Exception:
                logger.exception("Failed to reconstruct RunStats for key=%s", key)

        return results

    def get_run_history(self, level_id: int, algo_key: str) -> List[Dict[str, Any]]:
        """Return up to MAX_RUNS_PER_KEY recent runs for a specific algorithm."""
        lvl_key = str(level_id)
        lvl_data = self._data.get(lvl_key, {})
        value = lvl_data.get(algo_key, [])
        if isinstance(value, dict):
            return [value]
        return list(value)
