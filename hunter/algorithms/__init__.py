"""
Algorithms package — all 19 AI algorithm implementations.

Sub-packages:
  uninformed/   — BFS, DFS, IDDFS
  informed/     — UCS, Greedy, A*
  local/        — Hill Climbing, Local Beam, Simulated Annealing
  complex_env/  — AND-OR, No-Observation, Partial-Obs, Online Search
  csp/          — Constraint Propagation (AC-3), Backtracking, Min-Conflicts
  adversarial/  — Minimax, Alpha-Beta, Expectimax
"""

from __future__ import annotations

from typing import Any

from algorithms.base_algorithm import AIAlgorithm
from algorithms.uninformed import BFSAlgorithm, DFSAlgorithm, IDDFSAlgorithm
from algorithms.informed import UCSAlgorithm, GreedyAlgorithm, AStarAlgorithm
from algorithms.local import HillClimbingAlgorithm, LocalBeamAlgorithm, SimulatedAnnealingAlgorithm
from algorithms.complex_env import OnlineSearchAlgorithm, PartialObsAlgorithm
from algorithms.complex_env.and_or import AndOrAlgorithm
from algorithms.complex_env.no_observation import NoObservationAlgorithm
from algorithms.csp.backtracking import BacktrackingCSPSolver
from algorithms.csp.constraint_propagation import ConstraintPropagationSolver
from algorithms.csp.min_conflicts import MinConflictsSolver
from algorithms.adversarial.minimax import MinimaxAlgorithm
from algorithms.adversarial.alpha_beta import AlphaBetaAlgorithm
from algorithms.adversarial.expectimax import ExpectimaxAlgorithm


def create_algorithm(key: str, **kwargs: Any) -> AIAlgorithm:
    """Factory function to instantiate an AI algorithm by its registration key.

    Args:
        key:      Internal key identifier (e.g. "bfs").
        **kwargs: Optional hyper-parameters passed to constructors.

    Returns:
        An initialized subclass of AIAlgorithm.

    Raises:
        ValueError: If key is not registered.
    """
    k = key.lower()
    if k == "bfs":
        return BFSAlgorithm()
    elif k == "dfs":
        return DFSAlgorithm(max_depth=kwargs.get("max_depth", 200))
    elif k == "iddfs":
        return IDDFSAlgorithm(depth_step=kwargs.get("depth_step", 1))
    elif k == "ucs":
        return UCSAlgorithm()
    elif k == "greedy":
        return GreedyAlgorithm()
    elif k == "astar":
        return AStarAlgorithm()
    elif k == "hill_climbing":
        return HillClimbingAlgorithm()
    elif k == "local_beam":
        return LocalBeamAlgorithm(beam_width=kwargs.get("beam_width", 4))
    elif k == "simulated_annealing":
        return SimulatedAnnealingAlgorithm(
            initial_temp=kwargs.get("initial_temp", 100.0),
            cooling_rate=kwargs.get("cooling_rate", 0.95),
            min_temp=kwargs.get("min_temp", 0.01)
        )
    elif k == "online_search":
        return OnlineSearchAlgorithm()
    elif k == "partial_obs":
        return PartialObsAlgorithm(sensor_radius=kwargs.get("sensor_radius", 5))
    elif k == "and_or":
        return AndOrAlgorithm()
    elif k == "no_observation":
        return NoObservationAlgorithm()
    elif k == "constraint_propagation":
        return ConstraintPropagationSolver()
    elif k == "backtracking":
        return BacktrackingCSPSolver()
    elif k == "min_conflicts":
        return MinConflictsSolver(max_steps=kwargs.get("max_steps", 1000))
    elif k == "minimax":
        return MinimaxAlgorithm(depth=kwargs.get("depth", 2))
    elif k == "alpha_beta":
        return AlphaBetaAlgorithm(depth=kwargs.get("depth", 2))
    elif k == "expectimax":
        return ExpectimaxAlgorithm(depth=kwargs.get("depth", 2))
    else:
        raise ValueError(f"Unknown or unimplemented algorithm key: {key}")
