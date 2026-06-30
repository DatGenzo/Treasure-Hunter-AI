"""
menu_scene.py — The main menu scene with starfield animations and interactive buttons.
"""

from __future__ import annotations

import math
import random
from typing import List, Tuple

import pygame

from config.settings import (
    ACCENT,
    ACCENT_HOVER,
    DARK_BG,
    TEXT_MUTED,
    TEXT_PRIMARY,
)
from core.event_bus import EventBus
from core.state_machine import GameState, StateMachine
from scene.base_scene import BaseScene
from audio import play_music


class MenuScene(BaseScene):
    """Main menu of the game featuring a dynamic starfield background and menu options.

    Args:
        bus:           Shared EventBus.
        state_machine: Shared StateMachine.
        surface:       The drawing surface.
    """

    def __init__(self, bus: EventBus, state_machine: StateMachine, surface: pygame.Surface) -> None:
        super().__init__(bus, state_machine, surface)

        # Title and buttons fonts
        self._title_font = pygame.font.SysFont("consolas", 48, bold=True)
        self._subtitle_font = pygame.font.SysFont("consolas", 22)
        self._button_font = pygame.font.SysFont("consolas", 20, bold=True)
        self._footer_font = pygame.font.SysFont("consolas", 14)

        # Starfield particle definitions: (x, y, speed, size)
        self._stars: List[List[float]] = []
        width = surface.get_width()
        height = surface.get_height()
        for _ in range(75):
            self._stars.append([
                random.uniform(0, width),
                random.uniform(0, height),
                random.uniform(10, 45),  # Speed (pixels per sec)
                random.uniform(1, 3.5),  # Size (radius)
            ])

        # Define button rects (centered horizontally)
        btn_w, btn_h = 240, 50
        cx = width // 2 - btn_w // 2
        self._play_btn = pygame.Rect(cx, 320, btn_w, btn_h)
        self._quit_btn = pygame.Rect(cx, 390, btn_w, btn_h)

        # Hover states
        self._play_hover = False
        self._quit_hover = False

    def on_enter(self) -> None:
        """Called when entering the menu scene."""
        play_music("tunic_menu.mp3")

    def handle_event(self, event: pygame.event.Event) -> None:
        """Handle button clicks and mouse movements."""
        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            self._play_hover = self._play_btn.collidepoint(mx, my)
            self._quit_hover = self._quit_btn.collidepoint(mx, my)

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                mx, my = event.pos
                if self._play_btn.collidepoint(mx, my):
                    logger = pygame.logging.getLogger(__name__) if hasattr(pygame, "logging") else None
                    self._sm.transition(GameState.LEVEL_SELECT)
                elif self._quit_btn.collidepoint(mx, my):
                    pygame.event.post(pygame.event.Event(pygame.QUIT))

    def update(self, dt: float) -> None:
        """Update background stars movement."""
        width = self._surface.get_width()
        for star in self._stars:
            # Move stars leftward
            star[0] -= star[2] * dt
            if star[0] < 0:
                star[0] = width
                star[1] = random.uniform(0, self._surface.get_height())

    def render(self, surface: pygame.Surface) -> None:
        """Draw starfield, glowing title, and styled buttons."""
        # 1. Background
        surface.fill(DARK_BG)

        # 2. Draw Stars
        for star in self._stars:
            # Twinkle brightness
            alpha = int(100 + 155 * abs(math.sin(pygame.time.get_ticks() * 0.002 * (star[2] / 40.0))))
            color = (alpha, alpha, min(255, alpha + 30))
            pygame.draw.circle(surface, color, (int(star[0]), int(star[1])), int(star[3]))

        # 3. Glowing Title Effect (draw 3 times with offsets & decreasing alpha/brightness)
        title_str = "TREASURE HUNTER AI"
        tx = surface.get_width() // 2
        ty = 130

        # Layer 1: Soft large glow
        glow1 = self._title_font.render(title_str, True, (30, 60, 120))
        surface.blit(glow1, glow1.get_rect(center=(tx - 2, ty - 2)))
        surface.blit(glow1, glow1.get_rect(center=(tx + 2, ty + 2)))

        # Layer 2: Colored inner glow
        glow2 = self._title_font.render(title_str, True, ACCENT)
        surface.blit(glow2, glow2.get_rect(center=(tx - 1, ty - 1)))
        surface.blit(glow2, glow2.get_rect(center=(tx + 1, ty + 1)))

        # Layer 3: Solid text
        title_surf = self._title_font.render(title_str, True, TEXT_PRIMARY)
        surface.blit(title_surf, title_surf.get_rect(center=(tx, ty)))

        # Subtitle
        sub_str = "Visualize AI Search Algorithms"
        sub_surf = self._subtitle_font.render(sub_str, True, TEXT_MUTED)
        surface.blit(sub_surf, sub_surf.get_rect(center=(tx, ty + 50)))

        # 4. Draw Play Button
        play_color = ACCENT_HOVER if self._play_hover else ACCENT
        play_bg = (30, 45, 75) if self._play_hover else (22, 28, 48)
        pygame.draw.rect(surface, play_bg, self._play_btn, border_radius=8)
        pygame.draw.rect(surface, play_color, self._play_btn, 2, border_radius=8)
        
        play_text = self._button_font.render("PLAY GAME", True, TEXT_PRIMARY)
        surface.blit(play_text, play_text.get_rect(center=self._play_btn.center))

        # 5. Draw Quit Button
        quit_color = (255, 100, 100) if self._quit_hover else (220, 60, 60)
        quit_bg = (70, 30, 35) if self._quit_hover else (45, 20, 25)
        pygame.draw.rect(surface, quit_bg, self._quit_btn, border_radius=8)
        pygame.draw.rect(surface, quit_color, self._quit_btn, 2, border_radius=8)

        quit_text = self._button_font.render("QUIT GAME", True, TEXT_PRIMARY)
        surface.blit(quit_text, quit_text.get_rect(center=self._quit_btn.center))

        # 6. Version and copyright
        footer = self._footer_font.render("v1.0.0 | Google DeepMind Pair Programming", True, TEXT_MUTED)
        surface.blit(footer, (surface.get_width() - footer.get_width() - 20, surface.get_height() - 30))
