"""
door.py — Door entity that can be unlocked using keys to clear paths.
"""

from __future__ import annotations

import logging
from typing import Any, Optional, Tuple

import pygame

from config.settings import TILE_SIZE, WARNING, SUCCESS
from core.event_bus import EventBus, Events
from entities.base_entity import Entity
from maps.tilemap import TileMap
from utils.vec2 import Vec2

logger = logging.getLogger(__name__)


class Door(Entity):
    """A locked doorway blocking access to exit or treasure rooms.

    Args:
        col:     Grid column.
        row:     Grid row.
        tilemap: The active TileMap.
        bus:     Shared EventBus.
    """

    def __init__(self, col: int, row: int, tilemap: TileMap, bus: EventBus, door_id: str = "door", key_required: Optional[str] = None, puzzle_id: Optional[str] = None, color: Optional[Tuple[int, int, int]] = None) -> None:
        super().__init__(col, row, tilemap)
        self._bus = bus
        self.door_id = door_id
        self.key_required = key_required
        self.puzzle_id = puzzle_id
        self.locked = True
        self.color = color if color is not None else WARNING
        self._bus.subscribe("puzzle_solved", self._on_puzzle_solved)

    @property
    def grid_pos(self) -> Tuple[int, int]:
        return self._col, self._row

    def _on_puzzle_solved(self, puzzle_id: Optional[str] = None, **kwargs: Any) -> None:
        p_id = puzzle_id or kwargs.get("puzzle_id")
        if self.puzzle_id and p_id == self.puzzle_id:
            logger.info("Door %s unlocked via Puzzle %s solved!", self.door_id, p_id)
            self.locked = False
            from maps.tile import Tile, TileType
            self._tilemap._grid[self._row][self._col] = Tile(TileType.FLOOR)
            self._bus.publish(Events.DOOR_UNLOCKED, door_id=self.door_id)

    def unlock(self, player: Any) -> bool:
        """Unlock the door if the player meets the key/puzzle requirements."""
        if not self.locked:
            return True

        if self.puzzle_id:
            logger.warning("Door %s is locked by an unsolved puzzle %s!", self.door_id, self.puzzle_id)
            return False

        # If specific key is required
        if self.key_required:
            if player.inventory.has_key(self.key_required):
                self.locked = False
                from maps.tile import Tile, TileType
                self._tilemap._grid[self._row][self._col] = Tile(TileType.FLOOR)
                logger.info("Door %s at (%d, %d) unlocked successfully!", self.door_id, self._col, self._row)
                self._bus.publish(Events.DOOR_UNLOCKED, door_id=self.door_id)
                return True
            else:
                logger.warning("Door %s requires key: %s", self.door_id, self.key_required)
                return False

        # Fallback to generic key check
        if player.has_key:
            self.locked = False
            from maps.tile import Tile, TileType
            self._tilemap._grid[self._row][self._col] = Tile(TileType.FLOOR)
            
            logger.info("Door at (%d, %d) unlocked successfully!", self._col, self._row)
            self._bus.publish(Events.DOOR_UNLOCKED, door_id=self.door_id)
            return True
        else:
            logger.warning("Door is locked! You need a Key to open it.")
            return False

    def update(self, dt: float) -> None:
        """Idle update."""
        pass

    def render(self, surface: pygame.Surface, camera_offset: Vec2) -> None:
        """Draw locked or unlocked door state."""
        px = self._col * TILE_SIZE - camera_offset.x
        py = self._row * TILE_SIZE - camera_offset.y

        rect = pygame.Rect(px, py, TILE_SIZE, TILE_SIZE)

        if self.locked:
            # Draw locked brown door with a gold handle/warning icon
            pygame.draw.rect(surface, (120, 70, 30), rect, border_radius=4)
            pygame.draw.rect(surface, self.color, rect, 3, border_radius=4)
            # Gold lock center icon
            pygame.draw.circle(surface, self.color, (px + TILE_SIZE // 2, py + TILE_SIZE // 2), 6)
            pygame.draw.rect(surface, self.color, (px + TILE_SIZE // 2 - 3, py + TILE_SIZE // 2, 6, 8))
        else:
            # Draw open green gateway
            pygame.draw.rect(surface, (30, 80, 50), rect, border_radius=4)
            pygame.draw.rect(surface, SUCCESS, rect, 2, border_radius=4)
