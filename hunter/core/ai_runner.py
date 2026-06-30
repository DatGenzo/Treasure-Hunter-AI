"""
ai_runner.py — Per-frame AI step budget controller.

The AIRunner sits between the Game loop and the active AIAlgorithm.
Each frame it:
  1. Determines how many ``algorithm.step()`` calls the budget allows
     (based on the player's speed-slider setting).
  2. Calls ``step()`` that many times and collects visualisation data.
  3. Converts algorithm actions into entity movement commands via the EventBus.
  4. Detects goal-reached / exhausted conditions and stops automatically.
"""

from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING, Optional

from config.settings import AI_STEPS_PER_SECOND_DEFAULT
from core.event_bus import EventBus, Events
from core.state_machine import GameState, StateMachine

if TYPE_CHECKING:
    from algorithms.base_algorithm import AIAlgorithm

logger = logging.getLogger(__name__)


class AIRunner:
    """Manages the per-frame execution budget for the active AI algorithm.

    Args:
        bus:           Shared EventBus for publishing AI events.
        state_machine: Shared StateMachine to check/change AI states.
    """

    def __init__(self, bus: EventBus, state_machine: StateMachine, scene_manager: Optional[Any] = None) -> None:
        self._bus = bus
        self._sm = state_machine
        self._scene_manager = scene_manager

        self._algorithm: Optional["AIAlgorithm"] = None
        self._steps_per_second: float = float(AI_STEPS_PER_SECOND_DEFAULT)
        self._step_accumulator: float = 0.0   # fractional steps carried over

        # Subscribe to EventBus commands
        self._bus.subscribe("set_ai_algorithm", self._on_set_algorithm)
        self._bus.subscribe("set_ai_speed", self.set_speed)
        self._bus.subscribe("ai_pause", self.pause)
        self._bus.subscribe("ai_resume", self.resume)
        self._bus.subscribe("ai_stop", self.stop)

    def _on_set_algorithm(self, algorithm: "AIAlgorithm", speed: float) -> None:
        self.set_algorithm(algorithm)
        self.set_speed(speed)

    # ------------------------------------------------------------------
    # Control API (called by AIPanel / UI)
    # ------------------------------------------------------------------

    def set_algorithm(self, algorithm: "AIAlgorithm") -> None:
        """Attach a freshly initialised algorithm to the runner.

        Args:
            algorithm: An ``AIAlgorithm`` instance that has already had
                       ``initialise(game_state)`` called on it.
        """
        self._algorithm = algorithm
        self._step_accumulator = 0.0
        logger.info("AIRunner: algorithm set to %s", type(algorithm).__name__)

    def set_speed(self, speed: float = 10.0, **kwargs: Any) -> None:
        """Adjust the playback speed.

        Args:
            speed: Number of algorithm steps to execute per second.
        """
        new_speed = max(0.1, speed)
        if getattr(self, "_steps_per_second", None) != new_speed:
            self._steps_per_second = new_speed
            logger.debug("AIRunner speed: %.1f steps/s", self._steps_per_second)

    def pause(self) -> None:
        """Suspend AI execution (transition to AI_PAUSED)."""
        if self._sm.state == GameState.AI_RUNNING:
            self._sm.transition(GameState.AI_PAUSED)
            self._bus.publish(Events.AI_PAUSED)
            logger.info("AIRunner paused.")

    def resume(self) -> None:
        """Resume AI execution from AI_PAUSED."""
        if self._sm.state == GameState.AI_PAUSED:
            self._sm.transition(GameState.AI_RUNNING)
            self._bus.publish(Events.AI_RESUMED)
            logger.info("AIRunner resumed.")

    def stop(self) -> None:
        """Stop AI and hand control back to the player."""
        self._algorithm = None
        self._step_accumulator = 0.0
        if self._sm.is_ai_active():
            self._sm.transition(GameState.PLAYING)
        self._bus.publish(Events.AI_STOPPED)
        logger.info("AIRunner stopped.")

    # ------------------------------------------------------------------
    # Per-frame update (called by Game._loop)
    # ------------------------------------------------------------------

    def update(self, dt: float) -> None:
        """Execute the budgeted number of algorithm steps for this frame.

        Args:
            dt: Delta-time in seconds since the last frame.
        """
        if self._algorithm is None or self._sm.state != GameState.AI_RUNNING:
            return

        # If player is moving (sliding between cells), wait for the movement to complete
        if self._scene_manager is not None and self._scene_manager._active is not None:
            active_scene = self._scene_manager._active
            if type(active_scene).__name__ == "GameScene":
                if active_scene._player.is_moving:
                    return

        # Accumulate fractional steps
        self._step_accumulator += self._steps_per_second * dt

        # Execute as many whole steps as the budget allows
        while self._step_accumulator >= 1.0 and not self._algorithm.is_done():
            self._step_accumulator -= 1.0
            try:
                step_result = self._algorithm.step()
            except Exception:
                logger.exception("AIRunner: algorithm step raised an exception.")
                self.stop()
                return

            # Publish step event (scene picks up vis_data + action)
            self._bus.publish(Events.AI_STEP_COMPLETED, step=step_result)

            # Update live statistics
            self._bus.publish(Events.STATS_UPDATED, stats=self._algorithm.stats)

        # Check if player reached the sub-goal
        player_reached_subgoal = False
        if self._scene_manager is not None and self._scene_manager._active is not None:
            active_scene = self._scene_manager._active
            if type(active_scene).__name__ == "GameScene":
                player = getattr(active_scene, "_player", None)
                subgoal = getattr(active_scene, "_current_subgoal", None)
                if player and subgoal and player.grid_pos == subgoal:
                    player_reached_subgoal = True

        # Check termination or subgoal reached
        if self._algorithm.is_done() or player_reached_subgoal:
            if self._algorithm is not None and type(self._algorithm).__name__ == "HillClimbingAlgorithm":
                if getattr(self._algorithm, "is_stuck", False):
                    self._bus.publish("ai_algo_stuck", algo=self._algorithm)
            logger.info("AIRunner: algorithm reached its goal / exhausted search / player at subgoal.")
            self._bus.publish("ai_subgoal_reached_check")
            if self._algorithm is None or self._algorithm.is_done():
                self._bus.publish(Events.AI_GOAL_REACHED, stats=self._algorithm.stats if self._algorithm else None)
                self.stop()


