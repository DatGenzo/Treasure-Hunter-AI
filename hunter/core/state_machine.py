"""
state_machine.py — Game-wide finite state machine.

Manages transitions between high-level game states (menu, playing,
AI running, puzzle solving, combat, etc.) and notifies listeners via
the EventBus whenever a transition occurs.
"""

from __future__ import annotations

import logging
from enum import Enum, auto
from typing import Callable, Dict, FrozenSet, Optional, Set

from core.event_bus import EventBus, Events

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# State enumeration
# ---------------------------------------------------------------------------

class GameState(Enum):
    """All possible high-level game states."""

    MAIN_MENU       = auto()
    LEVEL_SELECT    = auto()
    PLAYING         = auto()
    PAUSED          = auto()
    AI_RUNNING      = auto()
    AI_PAUSED       = auto()
    PUZZLE_SOLVING  = auto()
    COMBAT          = auto()
    LEVEL_COMPLETE  = auto()
    STATS           = auto()
    GAME_OVER       = auto()


# ---------------------------------------------------------------------------
# Allowed transitions table
# ---------------------------------------------------------------------------

_ALLOWED_TRANSITIONS: Dict[GameState, FrozenSet[GameState]] = {
    GameState.MAIN_MENU: frozenset({
        GameState.LEVEL_SELECT,
    }),
    GameState.LEVEL_SELECT: frozenset({
        GameState.MAIN_MENU,
        GameState.PLAYING,
    }),
    GameState.PLAYING: frozenset({
        GameState.PAUSED,
        GameState.AI_RUNNING,
        GameState.PUZZLE_SOLVING,
        GameState.COMBAT,
        GameState.LEVEL_COMPLETE,
        GameState.GAME_OVER,
    }),
    GameState.PAUSED: frozenset({
        GameState.PLAYING,
        GameState.MAIN_MENU,
        GameState.LEVEL_SELECT,
    }),
    GameState.AI_RUNNING: frozenset({
        GameState.AI_PAUSED,
        GameState.PLAYING,
        GameState.PUZZLE_SOLVING,
        GameState.COMBAT,
        GameState.LEVEL_COMPLETE,
        GameState.GAME_OVER,
    }),
    GameState.AI_PAUSED: frozenset({
        GameState.AI_RUNNING,
        GameState.PLAYING,
        GameState.COMBAT,
        GameState.PUZZLE_SOLVING,
    }),
    GameState.PUZZLE_SOLVING: frozenset({
        GameState.PLAYING,
        GameState.AI_RUNNING,
        GameState.AI_PAUSED,
        GameState.GAME_OVER,
    }),
    GameState.COMBAT: frozenset({
        GameState.PLAYING,
        GameState.AI_RUNNING,
        GameState.AI_PAUSED,
        GameState.GAME_OVER,
    }),
    GameState.LEVEL_COMPLETE: frozenset({
        GameState.STATS,
        GameState.LEVEL_SELECT,
        GameState.PLAYING,
    }),
    GameState.STATS: frozenset({
        GameState.LEVEL_SELECT,
        GameState.PLAYING,     # "Next Level" shortcut
    }),
    GameState.GAME_OVER: frozenset({
        GameState.MAIN_MENU,
        GameState.LEVEL_SELECT,
    }),
}


# ---------------------------------------------------------------------------
# StateMachine
# ---------------------------------------------------------------------------

class StateMachine:
    """Controls game-wide state and validates transitions.

    Args:
        bus:           The shared EventBus for publishing state-change events.
        initial_state: Starting state (default: ``GameState.MAIN_MENU``).
    """

    def __init__(
        self,
        bus: EventBus,
        initial_state: GameState = GameState.MAIN_MENU,
    ) -> None:
        self._bus = bus
        self._state: GameState = initial_state
        self._history: list[GameState] = [initial_state]
        logger.info("StateMachine initialised in state: %s", initial_state.name)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def state(self) -> GameState:
        """The current game state."""
        return self._state

    # ------------------------------------------------------------------
    # Transition
    # ------------------------------------------------------------------

    def transition(self, new_state: GameState) -> bool:
        """Attempt to transition to *new_state*.

        Args:
            new_state: The target state.

        Returns:
            ``True`` if the transition was performed; ``False`` if it is not
            allowed from the current state.
        """
        allowed = _ALLOWED_TRANSITIONS.get(self._state, frozenset())
        if new_state not in allowed:
            logger.warning(
                "Invalid transition: %s -> %s",
                self._state.name,
                new_state.name,
            )
            return False

        old_state = self._state
        self._state = new_state
        self._history.append(new_state)

        logger.info("State: %s -> %s", old_state.name, new_state.name)
        self._bus.publish(Events.SCENE_CHANGE, old_state=old_state, new_state=new_state)
        return True

    def force_transition(self, new_state: GameState) -> None:
        """Unconditionally set the state (use only for error recovery / testing).

        Args:
            new_state: Target state to jump to.
        """
        old_state = self._state
        self._state = new_state
        self._history.append(new_state)
        logger.warning(
            "FORCED state transition: %s -> %s", old_state.name, new_state.name
        )
        self._bus.publish(Events.SCENE_CHANGE, old_state=old_state, new_state=new_state)

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def is_playing(self) -> bool:
        """Return ``True`` if the game is in an interactive play state."""
        return self._state in {GameState.PLAYING, GameState.AI_RUNNING}

    def is_ai_active(self) -> bool:
        """Return ``True`` if the AI runner is in control."""
        return self._state in {GameState.AI_RUNNING, GameState.AI_PAUSED}

    def can_accept_player_input(self) -> bool:
        """Return ``True`` if human keyboard/mouse input should be processed."""
        return self._state == GameState.PLAYING

    def previous_state(self) -> Optional[GameState]:
        """Return the state immediately before the current one, if any."""
        return self._history[-2] if len(self._history) >= 2 else None
