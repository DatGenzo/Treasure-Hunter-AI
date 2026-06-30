"""
belief_overlay.py — Belief state visualization overlay rendering belief sets, current node, paths, and sensor bubbles.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Set, Tuple

import pygame

from config.settings import TILE_SIZE, VIS_SOLUTION, VIS_CURRENT
from maps.tilemap import TileMap
from utils.vec2 import Vec2
from visualisation.overlay import VisOverlay


class BeliefOverlay(VisOverlay):
    """Renders belief state nodes, planned paths, and active sensor areas for complex environments."""

    def render(
        self,
        surface: pygame.Surface,
        vis_data: Dict[str, Any],
        camera_offset: Vec2,
        tilemap: TileMap,
    ) -> None:
        """Render belief state search overlays."""
        # 1. Gather nodes
        belief_nodes = vis_data.get("visited", set())
        current_node = vis_data.get("current", None)
        path = vis_data.get("path", [])
        sensor_radius = vis_data.get("sensor_radius", 0)

        # 2. Render belief state cells with distinct purple-blue color (100, 80, 200, 120)
        belief_color = (100, 80, 200)
        for col, row in belief_nodes:
            self.draw_tile_highlight(surface, col, row, belief_color, 120, camera_offset)

        # 3. Render "known" real path in green as usual (VIS_SOLUTION, alpha=90)
        if path:
            for col, row in path:
                self.draw_tile_highlight(surface, col, row, VIS_SOLUTION, 90, camera_offset)
            
            # Connect path nodes with arrows
            for i in range(len(path) - 1):
                self.draw_arrow(surface, path[i], path[i + 1], VIS_SOLUTION, camera_offset, tilemap)

        # 4. Render current node with pulsing yellow highlight
        if current_node:
            pulse_alpha = int(120 + 100 * abs(math.sin(pygame.time.get_ticks() * 0.006)))
            self.draw_tile_highlight(surface, current_node[0], current_node[1], VIS_CURRENT, pulse_alpha, camera_offset)
            
            screen_x = current_node[0] * TILE_SIZE - camera_offset.x
            screen_y = current_node[1] * TILE_SIZE - camera_offset.y
            pygame.draw.rect(surface, VIS_CURRENT, (screen_x, screen_y, TILE_SIZE, TILE_SIZE), 2)

            # 5. Render sensor bubble (circle) around current node if sensor_radius > 0
            if sensor_radius > 0:
                cx = screen_x + TILE_SIZE // 2
                cy = screen_y + TILE_SIZE // 2
                radius_px = sensor_radius * TILE_SIZE
                
                # Draw outer bubble border
                pygame.draw.circle(surface, (100, 180, 255), (cx, cy), radius_px, 1)
                
                # Draw light sensor fill
                sensor_surf = pygame.Surface((radius_px * 2, radius_px * 2), pygame.SRCALPHA)
                pygame.draw.circle(sensor_surf, (100, 180, 255, 30), (radius_px, radius_px), radius_px)
                surface.blit(sensor_surf, (cx - radius_px, cy - radius_px))
