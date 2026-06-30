"""
event_bus.py — Lightweight publish/subscribe event system.

Decouples Controller, Model, and View layers.  No layer ever imports
a concrete class from another layer directly; instead it publishes or
subscribes to named events through this bus.

Example::

    bus = EventBus()

    def on_treasure(pos: Vec2) -> None:
        print("Collected at", pos)

    bus.subscribe("treasure_collected", on_treasure)
    bus.publish("treasure_collected", Vec2(3, 5))
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Callable, DefaultDict, List

logger = logging.getLogger(__name__)

# A handler is any callable that accepts arbitrary positional args.
EventHandler = Callable[..., None]


class EventBus:
    """Synchronous publish/subscribe event dispatcher.

    All events are dispatched on the calling thread.  Handlers are called
    in subscription order.  Exceptions in handlers are logged and swallowed
    so that one bad handler cannot block the others.
    """

    def __init__(self) -> None:
        self._handlers: DefaultDict[str, List[EventHandler]] = defaultdict(list)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def subscribe(self, event: str, handler: EventHandler) -> None:
        """Register *handler* to be called when *event* is published.

        Args:
            event:   String event name (e.g. ``"player_moved"``).
            handler: Callable that will receive the event's payload args.
        """
        if handler not in self._handlers[event]:
            self._handlers[event].append(handler)
            logger.debug("Subscribed %s -> %s", event, handler.__qualname__)

    def unsubscribe(self, event: str, handler: EventHandler) -> None:
        """Remove *handler* from *event*'s subscriber list.

        No-op if the handler was not subscribed.
        """
        handlers = self._handlers.get(event, [])
        if handler in handlers:
            handlers.remove(handler)
            logger.debug("Unsubscribed %s -> %s", event, handler.__qualname__)

    def publish(self, event: str, *args: Any, **kwargs: Any) -> None:
        """Call all handlers subscribed to *event* with the given payload.

        Args:
            event:  String event name.
            *args:  Positional payload forwarded to each handler.
            **kwargs: Keyword payload forwarded to each handler.
        """
        for handler in list(self._handlers.get(event, [])):
            try:
                handler(*args, **kwargs)
            except Exception:
                logger.exception(
                    "Error in handler %s for event '%s'",
                    handler.__qualname__,
                    event,
                )

    def clear(self, event: str | None = None) -> None:
        """Remove all handlers for *event*, or every handler if *event* is None."""
        if event is None:
            self._handlers.clear()
            logger.debug("EventBus cleared all subscriptions.")
        else:
            self._handlers.pop(event, None)
            logger.debug("EventBus cleared subscriptions for '%s'.", event)

    def subscriber_count(self, event: str) -> int:
        """Return the number of handlers registered for *event*."""
        return len(self._handlers.get(event, []))


# ---------------------------------------------------------------------------
# Well-known event name constants — use these instead of raw strings
# ---------------------------------------------------------------------------

class Events:
    """Namespace for all event name constants used in the game."""

    # Scene / game flow
    SCENE_CHANGE        = "scene_change"
    GAME_PAUSE          = "game_pause"
    GAME_RESUME         = "game_resume"
    LEVEL_COMPLETE      = "level_complete"
    GAME_OVER           = "game_over"

    # Player actions
    PLAYER_MOVED        = "player_moved"
    PLAYER_ATTACKED     = "player_attacked"
    PLAYER_DIED         = "player_died"
    PLAYER_HP_CHANGED   = "player_hp_changed"

    # Item interactions
    TREASURE_COLLECTED  = "treasure_collected"
    KEY_COLLECTED       = "key_collected"
    POTION_USED         = "potion_used"
    ITEM_COLLECTED      = "item_collected"

    # Door / puzzle
    DOOR_UNLOCKED       = "door_unlocked"
    PUZZLE_STARTED      = "puzzle_started"
    PUZZLE_SOLVED       = "puzzle_solved"

    # Monster / combat
    MONSTER_SPOTTED     = "monster_spotted"
    COMBAT_STARTED      = "combat_started"
    COMBAT_ENDED        = "combat_ended"
    MONSTER_DIED        = "monster_died"

    # AI control
    AI_START            = "ai_start"
    AI_STARTED          = "ai_started"
    AI_PAUSED           = "ai_paused"
    AI_RESUMED          = "ai_resumed"
    AI_STOPPED          = "ai_stopped"
    AI_STEP_COMPLETED   = "ai_step_completed"
    AI_GOAL_REACHED     = "ai_goal_reached"
    AI_SUBGOAL_REACHED = "ai_subgoal_reached"
    AI_SUBGOAL_CHANGED = "ai_subgoal_changed"

    # Statistics
    STATS_UPDATED       = "stats_updated"
    MISSION_UPDATED     = "mission_updated"
    TRAP_TRIGGERED      = "trap_triggered"
