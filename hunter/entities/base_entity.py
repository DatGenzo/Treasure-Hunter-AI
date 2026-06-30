"""
base_entity.py — Abstract base class for all game entities.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Tuple
import pygame

from config.settings import TILE_SIZE
from maps.tilemap import TileMap
from utils.vec2 import Vec2


class Entity(ABC):
    """Abstract base class representing any dynamic or static game object.

    Args:
        col:     Starting grid column.
        row:     Starting grid row.
        tilemap: The active TileMap.
    """

    def __init__(self, col: int, row: int, tilemap: TileMap) -> None:
        self._col = col
        self._row = row
        self._tilemap = tilemap
        self.active: bool = True

    @property
    def grid_pos(self) -> Tuple[int, int]:
        """Get the current grid coordinate (col, row)."""
        return self._col, self._row

    @grid_pos.setter
    def grid_pos(self, pos: Tuple[int, int]) -> None:
        """Set the current grid coordinate (col, row)."""
        self._col, self._row = pos

    @property
    def world_pos(self) -> Vec2:
        """Get the current pixel world coordinate of the entity's center."""
        return self._tilemap.grid_to_world(self._col, self._row)

    @property
    def rect(self) -> pygame.Rect:
        """Get a pygame.Rect representing the entity's boundary in world coordinates."""
        # Calculate top-left based on TILE_SIZE centered on world_pos
        wpos = self.world_pos
        left = wpos.x - TILE_SIZE // 2
        top = wpos.y - TILE_SIZE // 2
        return pygame.Rect(left, top, TILE_SIZE, TILE_SIZE)

    @abstractmethod
    def render(self, surface: pygame.Surface, camera_offset: Vec2) -> None:
        """Draw the entity onto the surface using camera offset.

        Args:
            surface:       The drawing surface.
            camera_offset: The translation offset to apply.
        """

    @abstractmethod
    def update(self, dt: float) -> None:
        """Advance the entity's internal state.

        Args:
            dt: Delta-time in seconds.
        """
