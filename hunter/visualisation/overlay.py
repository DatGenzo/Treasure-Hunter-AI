"""
overlay.py — Abstract base class for algorithm visualisation overlays.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Tuple

import pygame

from config.settings import TILE_SIZE
from maps.tilemap import TileMap
from utils.vec2 import Vec2


class VisOverlay(ABC):
    """Base class for rendering algorithm execution overlays onto the game board."""

    @abstractmethod
    def render(
        self,
        surface: pygame.Surface,
        vis_data: Dict[str, Any],
        camera_offset: Vec2,
        tilemap: TileMap,
    ) -> None:
        """Draw the visualization overlay.

        Args:
            surface:       The 960 × 720 game surface.
            vis_data:      The latest visualisation dictionary from the algorithm.
            camera_offset: The active camera offset.
            tilemap:       The active TileMap.
        """

    def draw_tile_highlight(
        self,
        surface: pygame.Surface,
        col: int,
        row: int,
        color: Tuple[int, int, int],
        alpha: int,
        camera_offset: Vec2,
    ) -> None:
        """Draw a semi-transparent colored block over a grid tile.

        Args:
            surface:       Target surface.
            col:           Grid column.
            row:           Grid row.
            color:         RGB color tuple.
            alpha:         Transparency level (0 to 255).
            camera_offset: Camera offset.
        """
        # Calculate screen coordinates
        screen_x = col * TILE_SIZE - camera_offset.x
        screen_y = row * TILE_SIZE - camera_offset.y

        # Draw highlight block
        highlight = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        highlight.fill((*color, alpha))
        surface.blit(highlight, (screen_x, screen_y))

    def draw_arrow(
        self,
        surface: pygame.Surface,
        from_col_row: Tuple[int, int],
        to_col_row: Tuple[int, int],
        color: Tuple[int, int, int],
        camera_offset: Vec2,
        tilemap: TileMap,
    ) -> None:
        """Draw a connecting line with an arrow head between two grid tiles.

        Args:
            surface:       Target surface.
            from_col_row:  Starting grid position.
            to_col_row:    Ending grid position.
            color:         Arrow color.
            camera_offset: Camera offset.
            tilemap:       The active TileMap.
        """
        from_world = tilemap.grid_to_world(from_col_row[0], from_col_row[1])
        to_world = tilemap.grid_to_world(to_col_row[0], to_col_row[1])

        start_px = (from_world.x - camera_offset.x, from_world.y - camera_offset.y)
        end_px = (to_world.x - camera_offset.x, to_world.y - camera_offset.y)

        # Draw line
        pygame.draw.line(surface, color, start_px, end_px, 3)

        # Draw arrowhead
        import math
        dx = end_px[0] - start_px[0]
        dy = end_px[1] - start_px[1]
        angle = math.atan2(dy, dx)

        arrow_length = 8
        arrow_angle = math.pi / 6  # 30 degrees

        p1 = (
            end_px[0] - arrow_length * math.cos(angle - arrow_angle),
            end_px[1] - arrow_length * math.sin(angle - arrow_angle),
        )
        p2 = (
            end_px[0] - arrow_length * math.cos(angle + arrow_angle),
            end_px[1] - arrow_length * math.sin(angle + arrow_angle),
        )

        pygame.draw.polygon(surface, color, [end_px, p1, p2])
