"""
clock.py — Frame-rate management and delta-time helpers.

Wraps ``pygame.time.Clock`` so that the rest of the codebase never
imports pygame directly just for timing.
"""

from __future__ import annotations

import logging

import pygame

from config.settings import FPS

logger = logging.getLogger(__name__)


class GameClock:
    """Manages the game loop tick rate and exposes a delta-time in seconds.

    Args:
        target_fps: Desired frames per second (default from settings).

    Example::

        clock = GameClock()
        while running:
            dt = clock.tick()          # seconds since last frame
            physics.update(dt)
    """

    def __init__(self, target_fps: int = FPS) -> None:
        self._clock: pygame.time.Clock = pygame.time.Clock()
        self._target_fps: int = target_fps
        self._dt: float = 0.0          # seconds since last tick
        self._total_time: float = 0.0  # cumulative seconds
        self._frame_count: int = 0

    # ------------------------------------------------------------------
    # Main tick
    # ------------------------------------------------------------------

    def tick(self) -> float:
        """Advance the clock by one frame.

        Blocks the calling thread if necessary to maintain ``target_fps``.

        Returns:
            Delta-time in **seconds** since the previous frame.
        """
        raw_ms: int = self._clock.tick(self._target_fps)
        self._dt = raw_ms / 1_000.0
        self._total_time += self._dt
        self._frame_count += 1
        return self._dt

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def dt(self) -> float:
        """Delta-time in seconds for the most recent frame."""
        return self._dt

    @property
    def fps(self) -> float:
        """Actual frames per second reported by pygame."""
        return self._clock.get_fps()

    @property
    def total_time(self) -> float:
        """Total elapsed game time in seconds (pauses not excluded)."""
        return self._total_time

    @property
    def frame_count(self) -> int:
        """Total number of frames since the clock was created."""
        return self._frame_count

    @property
    def target_fps(self) -> int:
        """The configured target frame rate."""
        return self._target_fps

    @target_fps.setter
    def target_fps(self, value: int) -> None:
        if value <= 0:
            raise ValueError(f"target_fps must be positive, got {value}")
        self._target_fps = value

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset cumulative counters (useful between levels)."""
        self._total_time = 0.0
        self._frame_count = 0
        self._dt = 0.0
        # Tick once to clear the internal pygame delta accumulator
        self._clock.tick(0)
        logger.debug("GameClock reset.")
