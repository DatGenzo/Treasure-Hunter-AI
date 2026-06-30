"""
item.py — Represents collectable items (treasures, keys, potions) in the world.
"""

from __future__ import annotations

from enum import Enum, auto
import math
from typing import Dict, Tuple

import pygame

from config.settings import HEALTH_POTION_HEAL, KEY_SCORE, TILE_SIZE, TREASURE_SCORE
from entities.base_entity import Entity
from maps.tilemap import TileMap
from utils.vec2 import Vec2


class ItemType(Enum):
    """Enumeration of all item types."""

    TREASURE = auto()
    TREASURE_SMALL = auto()
    TREASURE_MEDIUM = auto()
    TREASURE_LARGE = auto()
    KEY = auto()
    HEALTH_POTION = auto()


ITEM_COLOR: Dict[ItemType, Tuple[int, int, int]] = {
    ItemType.TREASURE: (255, 200, 40),
    ItemType.TREASURE_SMALL: (255, 220, 80),
    ItemType.TREASURE_MEDIUM: (255, 200, 40),
    ItemType.TREASURE_LARGE: (255, 160, 0),
    ItemType.KEY: (180, 180, 50),
    ItemType.HEALTH_POTION: (200, 50, 50),
}

ITEM_SCORE: Dict[ItemType, int] = {
    ItemType.TREASURE: TREASURE_SCORE,
    ItemType.TREASURE_SMALL: 10,
    ItemType.TREASURE_MEDIUM: 25,
    ItemType.TREASURE_LARGE: 50,
    ItemType.KEY: KEY_SCORE,
    ItemType.HEALTH_POTION: 0,
}

# Gold value awarded to inventory.gold when collected
VALUE_MAP: Dict[ItemType, int] = {
    ItemType.TREASURE: 25,
    ItemType.TREASURE_SMALL: 10,
    ItemType.TREASURE_MEDIUM: 25,
    ItemType.TREASURE_LARGE: 50,
    ItemType.KEY: 0,
    ItemType.HEALTH_POTION: 0,
}

ITEM_VALUE: Dict[ItemType, int] = {
    ItemType.TREASURE: TREASURE_SCORE,
    ItemType.TREASURE_SMALL: 10,
    ItemType.TREASURE_MEDIUM: 25,
    ItemType.TREASURE_LARGE: 50,
    ItemType.KEY: KEY_SCORE,
    ItemType.HEALTH_POTION: HEALTH_POTION_HEAL,
}


class Item(Entity):
    """A collectable item lying on a tile.

    Args:
        col:       Grid column.
        row:       Grid row.
        item_type: The Type of item (e.g. TREASURE).
        tilemap:   The active TileMap.
    """

    def __init__(self, col: int, row: int, item_type: ItemType, tilemap: TileMap) -> None:
        super().__init__(col, row, tilemap)
        self.item_type = item_type
        self.value = ITEM_VALUE.get(item_type, 0)
        self.collected: bool = False

        self._time_elapsed: float = 0.0
        self._pulse_scale: float = 1.0

    @property
    def color(self) -> Tuple[int, int, int]:
        """Return the representative RGB color of the item."""
        return ITEM_COLOR.get(self.item_type, (255, 255, 255))

    def update(self, dt: float) -> None:
        """Update animation timer and calculate pulse scaling."""
        if not self.active or self.collected:
            return

        self._time_elapsed += dt
        # Pulse scale oscillates between 0.85 and 1.15
        self._pulse_scale = 1.0 + 0.15 * math.sin(self._time_elapsed * 5.0)

    def render(self, surface: pygame.Surface, camera_offset: Vec2) -> None:
        """Draw the item circle and two transparency glowing rings."""
        if not self.active or self.collected:
            return

        wpos = self.world_pos
        screen_x = wpos.x - camera_offset.x
        screen_y = wpos.y - camera_offset.y

        color = ITEM_COLOR.get(self.item_type, (255, 255, 255))
        base_radius = int(8 * self._pulse_scale)

        # 1. Draw outer glow (alpha ring 1)
        outer_radius = int(base_radius * 2.2)
        glow_surf1 = pygame.Surface((outer_radius * 2, outer_radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf1, (*color, 40), (outer_radius, outer_radius), outer_radius)
        surface.blit(glow_surf1, (screen_x - outer_radius, screen_y - outer_radius))

        # 2. Draw mid glow (alpha ring 2)
        mid_radius = int(base_radius * 1.6)
        glow_surf2 = pygame.Surface((mid_radius * 2, mid_radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf2, (*color, 80), (mid_radius, mid_radius), mid_radius)
        surface.blit(glow_surf2, (screen_x - mid_radius, screen_y - mid_radius))

        # 3. Draw core solid circle
        pygame.draw.circle(surface, color, (screen_x, screen_y), base_radius)
        pygame.draw.circle(surface, (255, 255, 255), (screen_x, screen_y), max(1, base_radius // 3))
