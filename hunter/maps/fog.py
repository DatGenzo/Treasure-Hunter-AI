"""
fog.py — Fog of War system simulating visibility and sương mù.
"""

from __future__ import annotations

import math
from typing import List

import pygame

from config.settings import TILE_SIZE


class FogOfWar:
    """Manages partially visible tiles and draws dark overlay on hidden cells."""

    def __init__(self, cols: int, rows: int) -> None:
        self._cols = cols
        self._rows = rows
        # True = hidden under sương mù, False = revealed/visible
        self._fog_grid = [[True for _ in range(cols)] for _ in range(rows)]

    def reveal(self, player_col: int, player_row: int, radius: int = 4) -> None:
        """Clear sương mù in a circular radius around the player position."""
        for r in range(max(0, player_row - radius), min(self._rows, player_row + radius + 1)):
            for c in range(max(0, player_col - radius), min(self._cols, player_col + radius + 1)):
                # Distance calculation for circular radius
                dx = c - player_col
                dy = r - player_row
                if dx * dx + dy * dy <= radius * radius:
                    self._fog_grid[r][c] = False

    def is_visible(self, col: int, row: int) -> bool:
        """Return True if the grid tile is revealed."""
        if 0 <= col < self._cols and 0 <= row < self._rows:
            return not self._fog_grid[row][col]
        return False

    def render(self, surface: pygame.Surface, camera_offset: pygame.Vector2) -> None:
        """Render semi-transparent dark blocks over unrevealed tiles."""
        fog_surf = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        fog_surf.fill((8, 8, 15, 240))  # Dark blue-black translucent fog

        for r in range(self._rows):
            for c in range(self._cols):
                if self._fog_grid[r][c]:
                    # Screen coordinates
                    sx = c * TILE_SIZE - camera_offset.x
                    sy = r * TILE_SIZE - camera_offset.y
                    # Skip rendering if out of screen bounds
                    if -TILE_SIZE <= sx <= surface.get_width() and -TILE_SIZE <= sy <= surface.get_height():
                        surface.blit(fog_surf, (sx, sy))
