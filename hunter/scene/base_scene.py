"""
base_scene.py — Abstract base class for all game scenes.

Every concrete scene (MenuScene, GameScene, etc.) inherits from ``BaseScene``
and implements the four lifecycle methods.  The SceneManager only ever calls
these four methods, ensuring a clean interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

import pygame

from core.event_bus import EventBus
from core.state_machine import StateMachine


class BaseScene(ABC):
    """Abstract scene with a standard lifecycle contract.

    Args:
        bus:           Shared EventBus.
        state_machine: Shared StateMachine.
        surface:       Primary drawing surface for this scene.
    """

    def __init__(
        self,
        bus: EventBus,
        state_machine: StateMachine,
        surface: pygame.Surface,
    ) -> None:
        self._bus = bus
        self._sm = state_machine
        self._surface = surface

    # ------------------------------------------------------------------
    # Lifecycle hooks
    # ------------------------------------------------------------------

    def on_enter(self) -> None:
        """Called once when this scene becomes active.

        Override to perform scene-specific setup (load assets, subscribe
        to events, reset state).
        """

    def on_exit(self) -> None:
        """Called once just before this scene is deactivated.

        Override to unsubscribe events and release resources.
        """

    @abstractmethod
    def handle_event(self, event: pygame.event.Event) -> None:
        """Process one pygame event.

        Args:
            event: A pygame event from the event queue.
        """

    @abstractmethod
    def update(self, dt: float) -> None:
        """Advance the scene's logic by *dt* seconds.

        Args:
            dt: Delta-time in seconds since the last frame.
        """

    @abstractmethod
    def render(self, surface: pygame.Surface) -> None:
        """Draw the scene onto *surface* (the game canvas).

        Args:
            surface: The 960 × 720 game drawing surface.
        """

    def render_panel(self, panel: pygame.Surface) -> None:
        """Draw the AI control panel onto *panel*.

        Override in scenes that have an AI panel (GameScene).
        Default implementation draws nothing.

        Args:
            panel: The 320 × 720 panel drawing surface.
        """
