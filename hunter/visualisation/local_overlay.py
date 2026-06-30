"""
local_overlay.py — Local search visualization overlay rendering candidates, best, and rejected states.
"""

from __future__ import annotations

import math
from typing import Any, Dict

import pygame

from config.settings import (
    VIS_BEST,
    VIS_CANDIDATE,
    VIS_CURRENT,
    VIS_REJECTED,
)
from maps.tilemap import TileMap
from utils.vec2 import Vec2
from visualisation.overlay import VisOverlay


class LocalOverlay(VisOverlay):
    """Renders candidate pools, accepted bests, and rejected search nodes for local optimizers."""

    def render(
        self,
        surface: pygame.Surface,
        vis_data: Dict[str, Any],
        camera_offset: Vec2,
        tilemap: TileMap,
    ) -> None:
        """Render local search overlays."""
        candidates = vis_data.get("candidates", set())
        best_nodes = vis_data.get("best", set())
        if isinstance(best_nodes, tuple):  # support single node or set
            best_nodes = {best_nodes}
        rejected_nodes = vis_data.get("rejected", set())
        beams = vis_data.get("beams", set())
        current_node = vis_data.get("current", None)

        # 1. Render all candidates (alpha=80)
        for col, row in candidates:
            self.draw_tile_highlight(surface, col, row, VIS_CANDIDATE, 80, camera_offset)

        # 2. Render beams if present (alpha=100 with orange color)
        for col, row in beams:
            self.draw_tile_highlight(surface, col, row, VIS_CANDIDATE, 110, camera_offset)
            # Draw double border for beam indicators
            screen_x = col * 32 - camera_offset.x
            screen_y = row * 32 - camera_offset.y
            pygame.draw.rect(surface, VIS_CANDIDATE, (screen_x + 2, screen_y + 2, 28, 28), 2)

        # 3. Render rejected candidates (alpha=60 and red X marker)
        for col, row in rejected_nodes:
            self.draw_tile_highlight(surface, col, row, VIS_REJECTED, 60, camera_offset)
            # Draw red cross (X)
            screen_x = col * 32 - camera_offset.x
            screen_y = row * 32 - camera_offset.y
            pygame.draw.line(surface, VIS_REJECTED, (screen_x + 8, screen_y + 8), (screen_x + 24, screen_y + 24), 2)
            pygame.draw.line(surface, VIS_REJECTED, (screen_x + 24, screen_y + 8), (screen_x + 8, screen_y + 24), 2)

        # 4. Render best candidates (alpha=200 and green star marker)
        for col, row in best_nodes:
            self.draw_tile_highlight(surface, col, row, VIS_BEST, 180, camera_offset)
            # Draw a small check mark or star in green
            screen_x = col * 32 - camera_offset.x
            screen_y = row * 32 - camera_offset.y
            pygame.draw.polygon(
                surface,
                (255, 255, 255),
                [
                    (screen_x + 10, screen_y + 16),
                    (screen_x + 14, screen_y + 22),
                    (screen_x + 24, screen_y + 10),
                    (screen_x + 14, screen_y + 19),
                ],
            )

        # 5. Render current active local search node (alpha=200 pulsing)
        if current_node:
            pulse_alpha = int(120 + 100 * abs(math.sin(pygame.time.get_ticks() * 0.006)))
            self.draw_tile_highlight(surface, current_node[0], current_node[1], VIS_CURRENT, pulse_alpha, camera_offset)
            
            screen_x = current_node[0] * 32 - camera_offset.x
            screen_y = current_node[1] * 32 - camera_offset.y
            pygame.draw.rect(surface, VIS_CURRENT, (screen_x, screen_y, 32, 32), 2)

        # 6. Render mini temperature gauge if SA temperature is active
        temp = vis_data.get("temperature", None)
        if temp is not None:
            # Draw vertical temperature gauge at bottom-right corner of game surface (960x720)
            # Let's position it at x=930, y=630
            gx, gy = 930, 630
            gw, gh = 10, 60
            
            # Background bar
            pygame.draw.rect(surface, (30, 30, 45), (gx, gy, gw, gh), border_radius=3)
            pygame.draw.rect(surface, (60, 65, 80), (gx, gy, gw, gh), 1, border_radius=3)
            
            # Fill bar based on temperature (assuming initial temp around 100)
            fill_ratio = min(1.0, max(0.0, temp / 100.0))
            fill_h = int(gh * fill_ratio)
            # Color transition from hot red (255, 60, 60) to cool blue (60, 120, 255)
            r = int(255 * fill_ratio + 60 * (1 - fill_ratio))
            g = int(60 * fill_ratio + 120 * (1 - fill_ratio))
            b = int(60 * fill_ratio + 255 * (1 - fill_ratio))
            
            if fill_h > 0:
                pygame.draw.rect(surface, (r, g, b), (gx, gy + (gh - fill_h), gw, fill_h), border_radius=3)
            
            # Draw Label "T: temp"
            font = pygame.font.SysFont("consolas", 11)
            text_surf = font.render(f"T:{temp:.1f}°", True, (240, 240, 250))
            # Place label slightly to the left of the gauge
            text_rect = text_surf.get_rect(right=gx - 8, centery=gy + gh // 2)
            surface.blit(text_surf, text_rect)
