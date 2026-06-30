"""
puzzle_trigger.py — Entity representing a puzzle trigger zone on the tilemap.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import pygame

from config.settings import TILE_SIZE
from core.event_bus import EventBus
from entities.base_entity import Entity
from maps.tilemap import TileMap
from utils.vec2 import Vec2

logger = logging.getLogger(__name__)


class PuzzleTrigger(Entity):
    """A tile trigger that starts a Gem Puzzle minigame when stepped on.

    Args:
        col:       Grid column.
        row:       Grid row.
        puzzle_id: Unique identifier for this puzzle.
        tilemap:   The active TileMap.
        bus:       Shared EventBus.
    """

    def __init__(self, col: int, row: int, puzzle_id: str, tilemap: TileMap, bus: EventBus, color: Optional[Tuple[int, int, int]] = None) -> None:
        super().__init__(col, row, tilemap)
        self.puzzle_id = puzzle_id
        self._bus = bus
        self.solved = False
        self.color = color if color is not None else (140, 80, 250)
        self._bus.subscribe("puzzle_solved", self._on_puzzle_solved)

    def _on_puzzle_solved(self, puzzle_id: Optional[str] = None, **kwargs: Any) -> None:
        p_id = puzzle_id or kwargs.get("puzzle_id")
        if p_id == self.puzzle_id:
            self.solved = True
            self.active = False
            logger.info("PuzzleTrigger %s disabled — puzzle solved.", self.puzzle_id)

    def check_trigger(self, player_grid_pos: tuple[int, int]) -> bool:
        """Evaluate trigger activation based on player grid coordinates."""
        if self.active and not self.solved and self.grid_pos == player_grid_pos:
            logger.info("PuzzleTrigger: Player entered trigger zone for %s", self.puzzle_id)
            self._bus.publish("puzzle_triggered", puzzle_id=self.puzzle_id)
            return True
        return False

    def update(self, dt: float) -> None:
        """Idle update."""
        pass

    def render(self, surface: pygame.Surface, camera_offset: Vec2) -> None:
        """Draw an arcane rune representing the puzzle trigger zone."""
        if not self.active or self.solved:
            return

        px = self._col * TILE_SIZE - camera_offset.x
        py = self._row * TILE_SIZE - camera_offset.y

        # Arcane runic rectangle
        rect = pygame.Rect(px + 4, py + 4, TILE_SIZE - 8, TILE_SIZE - 8)
        pygame.draw.rect(surface, self.color, rect, 2, border_radius=6)
        
        # Center core indicator
        pygame.draw.circle(surface, self.color, (px + TILE_SIZE // 2, py + TILE_SIZE // 2), 4)
