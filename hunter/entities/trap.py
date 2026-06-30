"""
trap.py — Entity representing a trap on the tilemap that damages the player.
"""

from __future__ import annotations

import logging
from typing import Any, Tuple

# pyrefly: ignore [missing-import]
import pygame

from config.settings import TILE_SIZE
from core.event_bus import EventBus, Events
from entities.base_entity import Entity
from maps.tilemap import TileMap
from utils.vec2 import Vec2

logger = logging.getLogger(__name__)


class Trap(Entity):
    """A trap tile that damages the player when stepped on.

    Args:
        col:       Grid column.
        row:       Grid row.
        tilemap:   The active TileMap.
        bus:       Shared EventBus.
        trap_type: "spike" or "poison".
        damage:    Damage amount (default: 10).
        visible:   Whether the trap is visible (default: True).
    """

    def __init__(
        self,
        col: int,
        row: int,
        tilemap: TileMap,
        bus: EventBus,
        trap_type: str = "spike",
        damage: int = 10,
        visible: bool = True,
    ) -> None:
        super().__init__(col, row, tilemap)
        self._bus = bus
        self.trap_type = trap_type
        self.damage = damage
        self.visible = visible
        self.triggered = False
        self._pulse_timer = 0.0

    def trigger(self, player: Any) -> int:
        """Apply trap damage to player, mark as triggered, and publish event."""
        if self.triggered:
            return 0
        
        self.triggered = True
        player.take_damage(self.damage)
        self._bus.publish("trap_triggered", trap=self, damage=self.damage)
        logger.info("Trap at (%d, %d) triggered! Dealt %d damage.", self._col, self._row, self.damage)
        return self.damage

    def update(self, dt: float) -> None:
        """Update pulse animation timer for rendering."""
        self._pulse_timer += dt

    def render(self, surface: pygame.Surface, camera_offset: Vec2) -> None:
        """Render trap spikes if visible or triggered."""
        if not self.active:
            return

        # If not visible and not triggered, do not draw it
        if not self.visible and not self.triggered:
            return

        px = self._col * TILE_SIZE - camera_offset.x
        py = self._row * TILE_SIZE - camera_offset.y
        rect = pygame.Rect(px, py, TILE_SIZE, TILE_SIZE)

        if self.triggered:
            # Draw triggered trap (flat grey/red state)
            pygame.draw.rect(surface, (80, 80, 90), rect, border_radius=4)
            # Center red trigger point
            pygame.draw.circle(surface, (200, 50, 50), (px + TILE_SIZE // 2, py + TILE_SIZE // 2), 4)
        else:
            # Draw active spikes or poison puddle
            if self.trap_type == "spike":
                # Draw dark spike plate with warning outline
                pygame.draw.rect(surface, (70, 70, 75), rect, border_radius=4)
                pygame.draw.rect(surface, (120, 20, 20), rect, 2, border_radius=4)
                # Draw small triangles for spikes
                pts1 = [(px + 6, py + 26), (px + 12, py + 10), (px + 18, py + 26)]
                pts2 = [(px + 14, py + 26), (px + 20, py + 10), (px + 26, py + 26)]
                pygame.draw.polygon(surface, (180, 180, 180), pts1)
                pygame.draw.polygon(surface, (150, 150, 150), pts2)
            else:  # poison
                # Draw poison green puddle
                import math
                pulse = int(4 * math.sin(self._pulse_timer * 4.0))
                puddle_r = max(4, 10 + pulse)
                pygame.draw.circle(surface, (40, 180, 40), (px + TILE_SIZE // 2, py + TILE_SIZE // 2), puddle_r)
                pygame.draw.circle(surface, (80, 220, 80), (px + TILE_SIZE // 2, py + TILE_SIZE // 2), max(1, puddle_r - 4))
