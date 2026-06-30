"""
path_overlay.py — Pathfinding visualization overlay rendering visited sets, open set, and solution paths.
"""

from __future__ import annotations

import math
from typing import Any, Dict

import pygame

from config.settings import (
    TILE_SIZE,
    VIS_CLOSED,
    VIS_CURRENT,
    VIS_FRONTIER,
    VIS_OPEN,
    VIS_SOLUTION,
    VIS_VISITED,
)
from maps.tilemap import TileMap
from utils.vec2 import Vec2
from visualisation.overlay import VisOverlay


class PathOverlay(VisOverlay):
    """Renders frontier, explored sets, active nodes, and reconstructed paths for search solvers."""

    def render(
        self,
        surface: pygame.Surface,
        vis_data: Dict[str, Any],
        camera_offset: Vec2,
        tilemap: TileMap,
    ) -> None:
        """Render search graphs overlays."""
        # 1. Gather A* sets or general search sets
        visited_nodes = vis_data.get("closed_set", vis_data.get("visited", set()))
        frontier_nodes = vis_data.get("open_set", vis_data.get("frontier", set()))
        current_node = vis_data.get("current", None)
        path = vis_data.get("path", [])

        # Select color palettes
        is_astar = "open_set" in vis_data
        visited_color = VIS_CLOSED if is_astar else VIS_VISITED
        frontier_color = VIS_OPEN if is_astar else VIS_FRONTIER

        # 2. Render explored / visited set (alpha=60)
        for col, row in visited_nodes:
            self.draw_tile_highlight(surface, col, row, visited_color, 60, camera_offset)

        # 3. Render frontier / open list set (alpha=100)
        for col, row in frontier_nodes:
            self.draw_tile_highlight(surface, col, row, frontier_color, 100, camera_offset)
            
            # Display f-value label if present
            f_values = vis_data.get("f_values", {})
            if f_values and (col, row) in f_values:
                val = f_values[(col, row)]
                # Draw small text on node (tile >= 32px)
                if TILE_SIZE >= 32:
                    font = pygame.font.SysFont("consolas", 10)
                    text_surf = font.render(f"{val:.1f}", True, (255, 255, 180))
                    screen_x = col * TILE_SIZE - camera_offset.x
                    screen_y = row * TILE_SIZE - camera_offset.y
                    # Center the text on the tile
                    text_rect = text_surf.get_rect(center=(screen_x + TILE_SIZE // 2, screen_y + TILE_SIZE // 2))
                    surface.blit(text_surf, text_rect)

        # 4. Render solution path (alpha=150 and arrow overlays)
        if path:
            for col, row in path:
                self.draw_tile_highlight(surface, col, row, VIS_SOLUTION, 90, camera_offset)
            
            # Connect path nodes with lines and arrows
            for i in range(len(path) - 1):
                self.draw_arrow(surface, path[i], path[i + 1], VIS_SOLUTION, camera_offset, tilemap)

        # 5. Render current search node with pulse highlight
        if current_node:
            pulse_alpha = int(120 + 100 * abs(math.sin(pygame.time.get_ticks() * 0.006)))
            self.draw_tile_highlight(surface, current_node[0], current_node[1], VIS_CURRENT, pulse_alpha, camera_offset)
            
            # Draw extra yellow border around current tile
            screen_x = current_node[0] * TILE_SIZE - camera_offset.x
            screen_y = current_node[1] * TILE_SIZE - camera_offset.y
            pygame.draw.rect(surface, VIS_CURRENT, (screen_x, screen_y, TILE_SIZE, TILE_SIZE), 2)
