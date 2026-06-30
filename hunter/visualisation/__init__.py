"""Visualisation package — algorithm-specific overlays drawn on the game map."""

from __future__ import annotations

from typing import Optional

from visualisation.local_overlay import LocalOverlay
from visualisation.overlay import VisOverlay
from visualisation.path_overlay import PathOverlay
from visualisation.belief_overlay import BeliefOverlay

# Cache instances for reuse
_PATH_OVERLAY = PathOverlay()
_LOCAL_OVERLAY = LocalOverlay()
_BELIEF_OVERLAY = BeliefOverlay()


def get_overlay(algorithm_key: str) -> VisOverlay:
    """Factory to retrieve the appropriate visualisation overlay based on the algorithm key.

    Args:
        algorithm_key: Registration key of the algorithm.

    Returns:
        A VisOverlay instance.
    """
    key = algorithm_key.lower()
    if key in {
        "bfs",
        "dfs",
        "iddfs",
        "ucs",
        "greedy",
        "astar",
        "partial_obs",
        "online_search",
        "and_or",
    }:
        return _PATH_OVERLAY
    elif key == "no_observation":
        return _BELIEF_OVERLAY
    elif key in {"hill_climbing", "local_beam", "simulated_annealing"}:
        return _LOCAL_OVERLAY
    else:
        # Default fallback to path overlay
        return _PATH_OVERLAY
