"""
base_algorithm.py — Abstract base class and dataclasses for all AI search algorithms.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Set, List, Tuple

from maps.tilemap import TileMap


@dataclass
class StepResult:
    """The outcome of a single algorithm search or execution step.

    Attributes:
        action:   Directional action to take ("move_n", "move_s", "move_e", "move_w", "wait", "done").
        vis_data: Visualisation data dict containing visited nodes, frontier, current node, etc.
    """

    action: str
    vis_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AlgorithmStats:
    """Live execution metrics collected during search execution."""

    nodes_expanded: int = 0
    nodes_visited: int = 0
    path_length: int = 0
    path_cost: float = 0.0
    elapsed_ms: float = 0.0
    memory_peak: int = 0
    current_depth: int = 0
    temperature: float = 0.0
    beam_count: int = 0
    open_list_size: int = 0
    closed_list_size: int = 0
    current_iteration: int = 0
    belief_state_size: int = 0
    assignments_count: int = 0
    backtracks_count: int = 0
    pruned_count: int = 0
    g_cost: float = 0.0
    h_cost: float = 0.0


class AIAlgorithm(ABC):
    """Abstract interface defining the execution contract for any search algorithm."""

    @abstractmethod
    def initialise(
        self,
        start: Tuple[int, int],
        goal: Tuple[int, int],
        tilemap: TileMap,
        game_state: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize or reset search parameters before running.

        Args:
            start:      Start grid coordinate (col, row).
            goal:       Target grid coordinate (col, row).
            tilemap:    The active TileMap.
            game_state: Optional snapshot of the game state.
        """

    @abstractmethod
    def step(self) -> StepResult:
        """Execute a single search step (expanding one node or moving along path).

        Returns:
            A StepResult containing the next action and visual states.
        """

    @abstractmethod
    def is_done(self) -> bool:
        """Return True if the search is complete (goal found or space exhausted)."""

    @property
    @abstractmethod
    def stats(self) -> AlgorithmStats:
        """Return the collected statistics for the current run."""
