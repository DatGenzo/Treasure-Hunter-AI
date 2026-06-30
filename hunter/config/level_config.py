"""
level_config.py — Level definitions and unlock progression logic.

Each LevelConfig describes the level's file, allowed algorithms, and the
set of objectives that must be completed to unlock the next level.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final, FrozenSet, List, Optional


@dataclass(frozen=True)
class LevelConfig:
    """Immutable descriptor for one game level."""

    level_id: int
    name: str
    subtitle: str
    csv_file: str                                   # relative to LEVELS_DIR
    allowed_algorithms: FrozenSet[str]              # algorithm keys available in this level
    unlock_requires: Optional[int] = None           # level_id that must be beaten first
    fog_of_war: bool = False
    has_puzzle: bool = False
    has_monsters: bool = False
    time_limit: Optional[int] = None               # seconds; None = unlimited


# ---------------------------------------------------------------------------
# Level definitions
# ---------------------------------------------------------------------------

LEVELS: Final[List[LevelConfig]] = [
    LevelConfig(
        level_id=1,
        name="The Dark Corridor",
        subtitle="Level 1 — Basic Pathfinding",
        csv_file="level_01.json",
        allowed_algorithms=frozenset({
            "bfs", "dfs", "iddfs",
        }),
        unlock_requires=None,
        fog_of_war=False,
        has_puzzle=False,
        has_monsters=False,
    ),
    LevelConfig(
        level_id=2,
        name="Weighted Ruins",
        subtitle="Level 2 — Terrain Costs",
        csv_file="level_02.json",
        allowed_algorithms=frozenset({
            "ucs", "greedy", "astar",
        }),
        unlock_requires=1,
        fog_of_war=False,
        has_puzzle=False,
        has_monsters=False,
    ),
    LevelConfig(
        level_id=3,
        name="The Shifting Heights",
        subtitle="Level 3 — Local Search",
        csv_file="level_03.json",
        allowed_algorithms=frozenset({
            "hill_climbing", "local_beam", "simulated_annealing",
        }),
        unlock_requires=2,
        fog_of_war=False,
        has_puzzle=False,
        has_monsters=False,
    ),
    LevelConfig(
        level_id=4,
        name="Temple of Shadows",
        subtitle="Level 4 — Partially Observable",
        csv_file="level_04.json",
        allowed_algorithms=frozenset({
            "online_search", "partial_obs", "no_observation", "and_or",
        }),
        unlock_requires=3,
        fog_of_war=True,
        has_puzzle=False,
        has_monsters=False,
    ),
    LevelConfig(
        level_id=5,
        name="The Puzzle Sanctum",
        subtitle="Level 5 — Constraint Satisfaction",
        csv_file="level_05.json",
        allowed_algorithms=frozenset({
            "constraint_propagation", "backtracking", "min_conflicts",
        }),
        unlock_requires=4,
        has_puzzle=True,
        has_monsters=False,
    ),
    LevelConfig(
        level_id=6,
        name="Monster Lair",
        subtitle="Level 6 — Adversarial Search",
        csv_file="level_06.json",
        allowed_algorithms=frozenset({
            "minimax", "alpha_beta", "expectimax",
        }),
        unlock_requires=5,
        has_puzzle=False,
        has_monsters=True,
    ),
    LevelConfig(
        level_id=7,
        name="Grand Temple",
        subtitle="Level 7 — The Ultimate Trial",
        csv_file="level_07.json",
        allowed_algorithms=frozenset({
            "bfs", "dfs", "iddfs", "ucs", "greedy", "astar",
            "hill_climbing", "local_beam", "simulated_annealing",
            "and_or", "no_observation", "partial_obs", "online_search",
            "constraint_propagation", "backtracking", "min_conflicts",
            "minimax", "alpha_beta", "expectimax",
        }),
        unlock_requires=6,
        fog_of_war=True,
        has_puzzle=True,
        has_monsters=True,
    ),
]

# Quick lookup: level_id → LevelConfig
LEVEL_MAP: Final[dict[int, LevelConfig]] = {lv.level_id: lv for lv in LEVELS}

# Level IDs that are unlocked by default (no prior level required)
DEFAULT_UNLOCKED: Final[FrozenSet[int]] = frozenset(
    lv.level_id for lv in LEVELS if lv.unlock_requires is None
)
