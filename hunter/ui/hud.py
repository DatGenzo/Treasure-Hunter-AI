"""
hud.py — In-game Heads Up Display showing player stats and level context.
"""

from __future__ import annotations

import math
from typing import Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from entities.player import Player
    from systems.mission_system import MissionSystem

import pygame

from config.settings import (
    HP_GREEN,
    HP_RED,
    SCORE_GOLD,
    TEXT_PRIMARY,
    TEXT_MUTED,
    SUCCESS,
    WARNING,
)
from utils.sprite_utils import get_key_surface
from ui.widgets import wrap_text


class HUD:
    """Renders the player's health, score, keys, and active algorithm status on the game surface."""

    def __init__(self) -> None:
        self._font = pygame.font.SysFont("consolas", 16)
        self._large_font = pygame.font.SysFont("consolas", 20, bold=True)

    def _draw_star(self, surface: pygame.Surface, color: Tuple[int, int, int], center: Tuple[float, float], size: float) -> None:
        """Helper to draw a 5-pointed star polygon."""
        points = []
        for i in range(10):
            r = size if i % 2 == 0 else size / 2.0
            angle = i * math.pi / 5.0 - math.pi / 2.0
            points.append((center[0] + r * math.cos(angle), center[1] + r * math.sin(angle)))
        pygame.draw.polygon(surface, color, points)

    def _draw_key(self, surface: pygame.Surface, color: Tuple[int, int, int], center: Tuple[float, float]) -> None:
        """Helper to draw the custom pixel art key."""
        cx, cy = center
        key_surf = get_key_surface(scale=1)
        kx = int(cx - key_surf.get_width() / 2)
        ky = int(cy - key_surf.get_height() / 2)
        surface.blit(key_surf, (kx, ky))

    def render(
        self,
        surface: pygame.Surface,
        player: "Player",  # Forward ref to Player
        level_id: int,
        algorithm_name: str = "",
        mission_system: Optional["MissionSystem"] = None,
    ) -> None:
        """Render HUD overlays onto the main gameplay surface.

        Args:
            surface:        The 960 × 720 game surface.
            player:         The Player instance.
            level_id:       Current level id.
            algorithm_name: Name of the running AI algorithm (if any).
            mission_system: The MissionSystem instance (optional).
        """
        # Draw translucent HUD background panels for readability
        hud_bar_height = 50
        panel_top = pygame.Surface((surface.get_width(), hud_bar_height), pygame.SRCALPHA)
        panel_top.fill((10, 10, 15, 180))  # Semi-transparent dark background
        surface.blit(panel_top, (0, 0))

        # 1. Top-Left: Health Bar with gradient and numeric label
        hp_x, hp_y = 20, 15
        hp_width, hp_height = 160, 18
        # Background outline
        pygame.draw.rect(surface, (50, 50, 70), (hp_x, hp_y, hp_width, hp_height), border_radius=4)
        # Gradient foreground
        ratio = max(0.0, min(1.0, player.hp / player.max_hp))
        curr_width = int(hp_width * ratio)
        if curr_width > 0:
            # Color interpolation HP_RED -> HP_GREEN
            r = int(HP_RED[0] + (HP_GREEN[0] - HP_RED[0]) * ratio)
            g = int(HP_RED[1] + (HP_GREEN[1] - HP_RED[1]) * ratio)
            b = int(HP_RED[2] + (HP_GREEN[2] - HP_RED[2]) * ratio)
            pygame.draw.rect(surface, (r, g, b), (hp_x, hp_y, curr_width, hp_height), border_radius=4)
        
        hp_text = self._font.render(f"HP: {player.hp}/{player.max_hp}", True, TEXT_PRIMARY)
        surface.blit(hp_text, (hp_x + 12, hp_y + 1))

        # 2. Top-Left below HUD bar: Score with animated star
        score_x, score_y = 200, 24
        self._draw_star(surface, SCORE_GOLD, (score_x, score_y), 8.0)
        score_text = self._large_font.render(f"{player.score}", True, SCORE_GOLD)
        surface.blit(score_text, (score_x + 14, score_y - 11))

        # 2b. Gold counter (only shown when player has opened at least one chest)
        if hasattr(player, "inventory") and player.inventory.gold > 0:
            gold_x = score_x + 14 + score_text.get_width() + 18
            gold_text = self._font.render(f"\U0001f4b0 {player.inventory.gold}G", True, (255, 215, 60))
            surface.blit(gold_text, (gold_x, score_y - 9))

        # 3. Top-Right: Level indicator
        level_text = self._large_font.render(f"LEVEL {level_id}", True, (90, 160, 255))
        surface.blit(level_text, (surface.get_width() - 120, 15))

        # 4. Top-Right: Key indicator next to Level
        if player.has_key:
            key_x = surface.get_width() - 160
            self._draw_key(surface, WARNING, (key_x, 25))

        # 5. Bottom-Left / Center: Mission Progress Bar & Current Mission text
        if mission_system and mission_system.steps:
            bar_w = 300
            bar_h = 10
            bar_x = 20
            bar_y = surface.get_height() - 25

            # Calculate mission progress
            required_steps = [s for s in mission_system.steps if not s.is_optional]
            if required_steps:
                completed_count = sum(1 for s in required_steps if s.completed)
                progress_ratio = completed_count / len(required_steps)
            else:
                progress_ratio = 1.0

            # Draw progress bar background
            pygame.draw.rect(surface, (40, 40, 50), (bar_x, bar_y, bar_w, bar_h), border_radius=3)
            # Draw progress fill
            fill_w = int(bar_w * progress_ratio)
            if fill_w > 0:
                pygame.draw.rect(surface, SUCCESS, (bar_x, bar_y, fill_w, bar_h), border_radius=3)

            # Get current active step
            current_step = mission_system.get_current_step()
            if current_step:
                mission_info = f"{current_step.icon} Current Mission: {current_step.description}"
            else:
                mission_info = "🎉 All Missions Completed!"

            # Wrap mission info text to prevent it from overlapping other elements or AI badge
            mission_lines = wrap_text(mission_info, self._font, 400)
            curr_my = bar_y - 20 - (len(mission_lines) - 1) * 18
            for line in mission_lines:
                mission_text = self._font.render(line, True, TEXT_PRIMARY)
                surface.blit(mission_text, (bar_x, curr_my))
                curr_my += 18

        # 6. Bottom-Right: Active AI algorithm badge
        if algorithm_name:
            badge_text = self._font.render(f"🤖 AI: {algorithm_name}", True, (255, 255, 255))
            text_w, text_h = badge_text.get_size()
            
            badge_w = text_w + 24
            badge_h = text_h + 10
            badge_x = surface.get_width() - badge_w - 20
            badge_y = surface.get_height() - badge_h - 20

            # Badge container surface with transparency
            badge_surf = pygame.Surface((badge_w, badge_h), pygame.SRCALPHA)
            # Glowing border and background
            pygame.draw.rect(badge_surf, (90, 160, 255, 40), (0, 0, badge_w, badge_h), border_radius=6)
            pygame.draw.rect(badge_surf, (90, 160, 255, 180), (0, 0, badge_w, badge_h), 2, border_radius=6)
            badge_surf.blit(badge_text, (12, 5))
            
            surface.blit(badge_surf, (badge_x, badge_y))
