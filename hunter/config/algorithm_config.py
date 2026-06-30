"""
algorithm_config.py — Per-algorithm hyper-parameters and metadata.

Centralises every algorithm's default configuration so the AI Panel can
read and display settings without importing algorithm implementations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Final, List


@dataclass(frozen=True)
class AlgorithmMeta:
    """Immutable descriptor for one AI algorithm."""

    key: str                   # internal identifier, e.g. "bfs"
    display_name: str          # shown in dropdown, e.g. "Breadth-First Search"
    category: str              # group label in dropdown
    description: str           # one-line tooltip description
    params: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Algorithm registry (ordered for dropdown display)
# ---------------------------------------------------------------------------

ALGORITHMS: Final[List[AlgorithmMeta]] = [
    # ── Uninformed Search ────────────────────────────────────────────────
    AlgorithmMeta(
        key="bfs",
        display_name="Breadth-First Search",
        category="Uninformed Search",
        description="Finds shortest path by exploring level by level.",
    ),
    AlgorithmMeta(
        key="dfs",
        display_name="Depth-First Search",
        category="Uninformed Search",
        description="Explores deeply before backtracking.",
        params={"max_depth": 200},
    ),
    AlgorithmMeta(
        key="iddfs",
        display_name="Iterative-Deepening DFS",
        category="Uninformed Search",
        description="DFS with increasing depth limits; combines BFS optimality with DFS memory.",
        params={"depth_step": 1},
    ),
    # ── Informed Search ──────────────────────────────────────────────────
    AlgorithmMeta(
        key="ucs",
        display_name="Uniform-Cost Search",
        category="Informed Search",
        description="Expands lowest-cost node first; optimal with varying tile weights.",
    ),
    AlgorithmMeta(
        key="greedy",
        display_name="Greedy Best-First Search",
        category="Informed Search",
        description="Chooses node closest to goal by heuristic; fast but not always optimal.",
    ),
    AlgorithmMeta(
        key="astar",
        display_name="A* Search",
        category="Informed Search",
        description="Optimal and complete; balances path cost and heuristic estimate.",
    ),
    # ── Local Search ─────────────────────────────────────────────────────
    AlgorithmMeta(
        key="hill_climbing",
        display_name="Hill Climbing",
        category="Local Search",
        description="Greedily improves current state; may get stuck in local optima.",
    ),
    AlgorithmMeta(
        key="local_beam",
        display_name="Local Beam Search",
        category="Local Search",
        description="Maintains k candidate states in parallel; diversifies search.",
        params={"beam_width": 4},
    ),
    AlgorithmMeta(
        key="simulated_annealing",
        display_name="Simulated Annealing",
        category="Local Search",
        description="Probabilistically accepts worse states to escape local optima.",
        params={"initial_temp": 100.0, "cooling_rate": 0.95, "min_temp": 0.01},
    ),
    # ── Complex Environment ───────────────────────────────────────────────
    AlgorithmMeta(
        key="and_or",
        display_name="AND-OR Search",
        category="Complex Environment",
        description="Plans for non-deterministic actions with contingency branches.",
    ),
    AlgorithmMeta(
        key="no_observation",
        display_name="No-Observation (Sensorless)",
        category="Complex Environment",
        description="Navigates using belief states with zero sensor information.",
    ),
    AlgorithmMeta(
        key="partial_obs",
        display_name="Partially Observable Search",
        category="Complex Environment",
        description="Navigates under Fog of War using partial sensor observations.",
    ),
    AlgorithmMeta(
        key="online_search",
        display_name="Online Search (LRTA*)",
        category="Complex Environment",
        description="Discovers unknown map interactively while moving (Learning RTA*).",
    ),
    # ── CSP ──────────────────────────────────────────────────────────────
    AlgorithmMeta(
        key="constraint_propagation",
        display_name="Constraint Propagation (AC-3)",
        category="Constraint Satisfaction",
        description="Enforces arc consistency to reduce puzzle variable domains.",
    ),
    AlgorithmMeta(
        key="backtracking",
        display_name="Backtracking Search",
        category="Constraint Satisfaction",
        description="Systematically assigns values with forward checking and MAC.",
    ),
    AlgorithmMeta(
        key="min_conflicts",
        display_name="Min-Conflicts",
        category="Constraint Satisfaction",
        description="Repairs invalid CSP assignments by minimising violated constraints.",
        params={"max_steps": 1000},
    ),
    # ── Adversarial Search ────────────────────────────────────────────────
    AlgorithmMeta(
        key="minimax",
        display_name="Minimax",
        category="Adversarial Search",
        description="Optimal strategy against an intelligent monster adversary.",
        params={"max_depth": 4},
    ),
    AlgorithmMeta(
        key="alpha_beta",
        display_name="Alpha-Beta Pruning",
        category="Adversarial Search",
        description="Minimax with branch pruning; same quality, much faster.",
        params={"max_depth": 6},
    ),
    AlgorithmMeta(
        key="expectimax",
        display_name="Expectimax",
        category="Adversarial Search",
        description="Handles random monster behaviour with expected-value reasoning.",
        params={"max_depth": 4},
    ),
]

# Quick lookup: key → AlgorithmMeta
ALGORITHM_MAP: Final[Dict[str, AlgorithmMeta]] = {a.key: a for a in ALGORITHMS}

# Group by category for dropdown rendering
ALGORITHM_CATEGORIES: Final[List[str]] = list(
    dict.fromkeys(a.category for a in ALGORITHMS)
)
