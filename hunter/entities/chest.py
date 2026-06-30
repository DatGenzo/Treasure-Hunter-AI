"""
chest.py — A treasure chest entity that can be opened by the player to earn gold.
Follows the same pattern as key_item.py (inherits Item).
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pygame

from entities.item import Item, ItemType
from maps.tilemap import TileMap
from core.event_bus import EventBus
from utils.vec2 import Vec2

if TYPE_CHECKING:
    from entities.player import Player


class Chest(Item):
    """A collectible treasure chest.  Opens when the player stands on the same tile
    and the 'F' key is pressed (or via :meth:`try_open`).

    Args:
        col:            Grid column.
        row:            Grid row.
        tilemap:        The active TileMap.
        bus:            EventBus for publishing the ``chest_opened`` event.
        treasure_value: Gold awarded when the chest is opened (default 50).
    """

    # Visual palette
    _COLOR_CLOSED = (180, 110, 30)   # Warm brown
    _COLOR_OPEN   = (100,  70, 20)   # Darker brown (empty)
    _COLOR_GOLD   = (255, 200,  40)  # Gold rim / lid glow

    def __init__(
        self,
        col: int,
        row: int,
        tilemap: TileMap,
        bus: EventBus,
        treasure_value: int = 50,
    ) -> None:
        # Use TREASURE_LARGE as base item type — carries the chest into the scoring
        # pipeline without breaking existing treasure counting.
        super().__init__(col, row, ItemType.TREASURE_LARGE, tilemap)
        self._bus = bus
        self.treasure_value = treasure_value
        self.state: str = "CLOSED"  # "CLOSED" | "OPEN"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def try_open(self, player: "Player") -> bool:
        """Attempt to open the chest.

        The chest opens when the player is on the **same tile** or an
        **adjacent** (4-directional) tile.

        Returns:
            True if the chest was just opened, False otherwise.
        """
        if self.state == "OPEN" or not self.active:
            return False

        px, py = player.grid_pos
        cx, cy = self.grid_pos
        dist = abs(px - cx) + abs(py - cy)
        if dist > 1:
            return False

        self.state = "OPEN"
        player.inventory.add_gold(self.treasure_value)
        player.score += self.treasure_value  # also add to score for HUD display
        self._bus.publish("chest_opened", col=cx, row=cy, value=self.treasure_value)
        return True

    # ------------------------------------------------------------------
    # Entity interface
    # ------------------------------------------------------------------

    def update(self, dt: float) -> None:
        """Animate only when closed."""
        if not self.active or self.state == "OPEN":
            return
        self._time_elapsed += dt
        self._pulse_scale = 1.0 + 0.08 * math.sin(self._time_elapsed * 4.0)

    def render(self, surface: pygame.Surface, camera_offset: Vec2) -> None:
        """Draw a small pixel-art chest — brown box with a gold lid outline."""
        if not self.active:
            return

        wpos = self.world_pos
        sx = int(wpos.x - camera_offset.x)
        sy = int(wpos.y - camera_offset.y)

        box_color  = self._COLOR_CLOSED if self.state == "CLOSED" else self._COLOR_OPEN
        lid_color  = self._COLOR_GOLD   if self.state == "CLOSED" else (60, 40, 10)

        # Scale slightly with pulse when closed
        scale = self._pulse_scale if self.state == "CLOSED" else 1.0
        hw = int(11 * scale)   # half-width
        hh = int(8  * scale)   # half-height of lower body
        lh = int(4  * scale)   # height of lid

        # --- Glow ring when closed ---
        if self.state == "CLOSED":
            outer = int(hw * 2.0)
            glow = pygame.Surface((outer * 2, outer * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*self._COLOR_GOLD, 35), (outer, outer), outer)
            surface.blit(glow, (sx - outer, sy - outer))

        # --- Body (lower rectangle) ---
        body_rect = pygame.Rect(sx - hw, sy - hh + lh, hw * 2, hh * 2)
        pygame.draw.rect(surface, box_color, body_rect, border_radius=2)
        pygame.draw.rect(surface, lid_color, body_rect, 1, border_radius=2)

        # --- Lid (upper rectangle) ---
        lid_rect = pygame.Rect(sx - hw, sy - hh - lh + lh, hw * 2, lh * 2)
        pygame.draw.rect(surface, box_color, lid_rect, border_radius=2)
        pygame.draw.rect(surface, lid_color, lid_rect, 1, border_radius=2)

        # --- Latch dot ---
        if self.state == "CLOSED":
            pygame.draw.circle(surface, self._COLOR_GOLD, (sx, sy), max(2, int(3 * scale)))
        else:
            # Open: draw a lighter interior hint
            inner = pygame.Rect(sx - hw + 3, sy - hh + lh + 3, (hw - 3) * 2, hh * 2 - 6)
            pygame.draw.rect(surface, (40, 25, 10), inner, border_radius=1)

        # --- "OPEN" label ---
        if self.state == "OPEN":
            try:
                font = pygame.font.SysFont("consolas", 10)
                label = font.render("OPEN", True, (200, 200, 100))
                surface.blit(label, (sx - label.get_width() // 2, sy - hh - lh - 12))
            except Exception:
                pass
