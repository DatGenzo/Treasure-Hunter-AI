"""
level_select_scene.py — Screen displaying available levels, unlock states, and detail cards.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Dict, List, Set, Tuple

import pygame

from config.level_config import LEVELS, LEVEL_MAP
from config.settings import (
    ACCENT,
    ACCENT_HOVER,
    DARK_BG,
    DANGER,
    SUCCESS,
    TEXT_MUTED,
    TEXT_PRIMARY,
    WARNING,
    PANEL_BG,
    PANEL_BORDER,
)
from core.event_bus import EventBus, Events
from core.state_machine import GameState, StateMachine
from scene.base_scene import BaseScene
from audio import play_sound, play_music
from ui.widgets import wrap_text

logger = logging.getLogger(__name__)


class LevelSelectScene(BaseScene):
    """Grid menu to browse levels and launch selected ones if unlocked.

    Session level unlock progress is persisted in the class attribute.
    """

    # Class-level persistence for unlocked level IDs
    unlocked_levels: Set[int] = {1}

    def __init__(self, bus: EventBus, state_machine: StateMachine, surface: pygame.Surface) -> None:
        super().__init__(bus, state_machine, surface)

        self._title_font = pygame.font.SysFont("consolas", 36, bold=True)
        self._number_font = pygame.font.SysFont("consolas", 40, bold=True)
        self._name_font = pygame.font.SysFont("consolas", 18, bold=True)
        self._sub_font = pygame.font.SysFont("consolas", 14)
        self._algo_font = pygame.font.SysFont("consolas", 12)
        self._back_font = pygame.font.SysFont("consolas", 16, bold=True)
        self._bold_font = pygame.font.SysFont("consolas", 16, bold=True)

        # Build card grid: 3 columns x 2 rows
        self._cards: List[Tuple[int, pygame.Rect]] = []
        width = surface.get_width()
        
        card_w, card_h = 270, 180
        col_spacing, row_spacing = 30, 30
        
        start_x = width // 2 - (3 * card_w + 2 * col_spacing) // 2
        start_y = 200

        for i in range(1, 8):  # 7 levels
            row = (i - 1) // 3
            col = (i - 1) % 3
            x = start_x + col * (card_w + col_spacing)
            y = start_y + row * (card_h + row_spacing)
            self._cards.append((i, pygame.Rect(x, y, card_w, card_h)))

        # "Unlock All" Dev button
        self._dev_unlock_btn = pygame.Rect(width - 250, surface.get_height() - 60, 230, 40)
        # Back button
        self._back_btn = pygame.Rect(20, 20, 100, 40)

        # Interactivity state
        self._hover_idx: int = -1  # level_id being hovered (-1 if none)
        self._dev_hover = False
        self._back_hover = False
        self._scroll_y = 0

        # Subscribe to level complete event to unlock next level
        self._bus.subscribe(Events.LEVEL_COMPLETE, self._on_level_complete)

    def on_enter(self) -> None:
        """Called when entering the level select scene."""
        play_music("tunic_menu.mp3")

    def on_exit(self) -> None:
        """Unsubscribe level complete handler when leaving scene."""
        self._bus.unsubscribe(Events.LEVEL_COMPLETE, self._on_level_complete)

    def _on_level_complete(self, level_id: int) -> None:
        """Unlock the next consecutive level when LevelComplete triggers."""
        next_id = level_id + 1
        if next_id in LEVEL_MAP and next_id not in LevelSelectScene.unlocked_levels:
            LevelSelectScene.unlocked_levels.add(next_id)
            logger.info("LevelSelectScene: Unlocked level %d", next_id)

    def handle_event(self, event: pygame.event.Event) -> None:
        """Process card selection, back button, and dev unlock mode clicks."""
        if event.type == pygame.MOUSEWHEEL:
            self._scroll_y += event.y * 30
            # Cards are in 3 columns. Max cards is len(self._cards).
            # The bottom of the lowest row is:
            # start_y + (rows - 1) * (card_h + row_spacing) + card_h
            if self._cards:
                # Get max y position of bottom row
                max_bottom = max(r.bottom for _, r in self._cards)
                # We want to be able to scroll until max_bottom is visible with some margin
                # window height is 720
                min_scroll = min(0, 720 - max_bottom - 40)
            else:
                min_scroll = 0
            
            self._scroll_y = max(min_scroll, min(0, self._scroll_y))
            
        elif event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            self._back_hover = self._back_btn.collidepoint(mx, my)

            # Check dev button hover
            px = mx - 960
            self._dev_hover = self._dev_unlock_btn.collidepoint(px, my)

            self._hover_idx = -1
            for lid, r in self._cards:
                rect = r.move(0, self._scroll_y)
                if rect.collidepoint(mx, my):
                    self._hover_idx = lid
                    break

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                mx, my = event.pos
                
                # Check Back Button
                if self._back_btn.collidepoint(mx, my):
                    self._sm.transition(GameState.MAIN_MENU)
                    return

                # Check Dev Unlock button on Panel
                px = mx - 960
                if self._dev_unlock_btn.collidepoint(px, my):
                    logger.info("Dev Mode: Unlocking all levels!")
                    LevelSelectScene.unlocked_levels = {1, 2, 3, 4, 5, 6, 7}
                    # Save progression persistence
                    try:
                        with open("unlocked_levels.json", "w", encoding="utf-8") as f:
                            json.dump(list(LevelSelectScene.unlocked_levels), f)
                    except Exception as e:
                        logger.debug("Failed to save dev progression: %s", e)
                    play_sound("door_open")
                    return

                # Check Benchmark Level Button on Panel
                if hasattr(self, "_bench_btn_rect") and self._bench_btn_rect.collidepoint(px, my):
                    target_id = self._hover_idx if self._hover_idx != -1 else 1
                    if target_id in LevelSelectScene.unlocked_levels:
                        logger.info("LevelSelectScene: Benchmark requested for level %d", target_id)
                        self._bus.publish("start_benchmark", level_id=target_id)
                    return

                # Check Level Select Cards
                for lid, r in self._cards:
                    rect = r.move(0, self._scroll_y)
                    if rect.collidepoint(mx, my):
                        # Attempt to load if unlocked
                        if lid in LevelSelectScene.unlocked_levels:
                            logger.info("LevelSelectScene: Selected Level %d", lid)
                            self._bus.publish("load_level", level_id=lid)
                        else:
                            logger.warning("LevelSelectScene: Level %d is locked!", lid)
                        break

    def update(self, dt: float) -> None:
        """No frame logic needed."""
        pass

    def render(self, surface: pygame.Surface) -> None:
        """Render level list overlay cards on left game canvas."""
        surface.fill(DARK_BG)

        # 1. Title
        title_surf = self._title_font.render("SELECT LEVEL", True, TEXT_PRIMARY)
        surface.blit(title_surf, title_surf.get_rect(center=(surface.get_width() // 2, 98)))

        # 2. Back Button
        back_color = ACCENT_HOVER if self._back_hover else ACCENT
        back_bg = (30, 45, 75) if self._back_hover else (22, 28, 48)
        pygame.draw.rect(surface, back_bg, self._back_btn, border_radius=6)
        pygame.draw.rect(surface, back_color, self._back_btn, 2, border_radius=6)
        back_text = self._back_font.render("← BACK", True, TEXT_PRIMARY)
        surface.blit(back_text, back_text.get_rect(center=self._back_btn.center))

        # 3. Draw cards
        for lid, r in self._cards:
            rect = r.move(0, self._scroll_y)
            lv = LEVEL_MAP[lid]
            is_unlocked = lid in LevelSelectScene.unlocked_levels
            is_hovered = self._hover_idx == lid

            # Determine card style
            if not is_unlocked:
                border_color = (60, 60, 80)
                bg_color = (15, 15, 22)
                text_color = (100, 100, 120)
            elif is_hovered:
                border_color = ACCENT_HOVER
                bg_color = (30, 45, 75)
                text_color = TEXT_PRIMARY
            else:
                border_color = (70, 70, 110)
                bg_color = (22, 22, 38)
                text_color = TEXT_PRIMARY

            # Card background
            pygame.draw.rect(surface, bg_color, rect, border_radius=10)
            pygame.draw.rect(surface, border_color, rect, 2, border_radius=10)

            # Level number (Large)
            num_color = ACCENT if is_unlocked else (70, 70, 85)
            num_surf = self._number_font.render(f"{lid:02d}", True, num_color)
            surface.blit(num_surf, (rect.x + 20, rect.y + 15))

            # Locked / Unlocked badge
            if not is_unlocked:
                badge_text = self._sub_font.render("LOCKED", True, DANGER)
                pygame.draw.rect(surface, (50, 20, 25), (rect.right - 80, rect.y + 18, 65, 20), border_radius=4)
                surface.blit(badge_text, (rect.right - 75, rect.y + 19))
            else:
                badge_text = self._sub_font.render("UNLOCKED", True, SUCCESS)
                pygame.draw.rect(surface, (20, 45, 30), (rect.right - 95, rect.y + 18, 80, 20), border_radius=4)
                surface.blit(badge_text, (rect.right - 88, rect.y + 19))

            # Level Name
            name_surf = self._name_font.render(lv.name, True, text_color)
            surface.blit(name_surf, (rect.x + 20, rect.y + 70))

            # Level Subtitle
            sub_surf = self._sub_font.render(lv.subtitle.split(" — ")[1], True, TEXT_MUTED)
            surface.blit(sub_surf, (rect.x + 20, rect.y + 95))

            # Divider line
            pygame.draw.line(surface, (50, 50, 70), (rect.x + 20, rect.y + 125), (rect.right - 20, rect.y + 125), 1)

            # Brief clean details line (prevents overflows!)
            n_algos = len(lv.allowed_algorithms)
            badge_str = f"🤖 {n_algos} Algos"
            if lv.has_monsters:
                badge_str += " | 👾 Hostiles"
            if lv.has_puzzle:
                badge_str += " | 🔑 Puzzles"
            if lv.fog_of_war:
                badge_str += " | 🌫️ Fog"

            algo_surf = self._algo_font.render(badge_str, True, (130, 150, 180) if is_unlocked else (90, 90, 110))
            surface.blit(algo_surf, (rect.x + 20, rect.y + 138))

    def render_panel(self, panel: pygame.Surface) -> None:
        """Render a beautiful level detail inspection card on the right panel."""
        panel.fill(PANEL_BG)

        # Draw panel border separating canvas
        pygame.draw.line(panel, PANEL_BORDER, (0, 0), (0, 720), 2)

        # Header Title
        title_surf = self._title_font.render("📖 LEVEL DATA", True, TEXT_PRIMARY)
        panel.blit(title_surf, (20, 20))
        pygame.draw.line(panel, PANEL_BORDER, (10, 60), (310, 60), 2)

        # Select target level to show detail (hovered level, default to Level 1)
        target_id = self._hover_idx if self._hover_idx != -1 else 1
        lv = LEVEL_MAP[target_id]
        is_unlocked = target_id in LevelSelectScene.unlocked_levels

        # Render detail preview
        y = 80
        # Level Title
        num_lbl = self._bold_font.render(f"LEVEL {target_id:02d}", True, ACCENT)
        panel.blit(num_lbl, (20, y))
        y += 22

        # Wrap Level Name to fit the 280px width preview card area
        name_lines = wrap_text(lv.name, self._title_font, 280)
        for line in name_lines:
            name_lbl = self._title_font.render(line, True, TEXT_PRIMARY)
            panel.blit(name_lbl, (20, y))
            y += name_lbl.get_height() + 4
        y += 8

        # Lock / Unlock notice
        status_str = "🔓 READY TO PLAY" if is_unlocked else "🔒 LOCKED (beat prior levels)"
        status_color = SUCCESS if is_unlocked else DANGER
        status_lbl = self._bold_font.render(status_str, True, status_color)
        panel.blit(status_lbl, (20, y))
        y += 35

        # Benchmark button placement in panel
        self._bench_btn_rect = pygame.Rect(20, y, 280, 36)
        if is_unlocked:
            # Check mouse collision on panel relative coordinates
            mx, my = pygame.mouse.get_pos()
            px = mx - 960
            bench_hover = self._bench_btn_rect.collidepoint(px, my)
            btn_bg = ACCENT_HOVER if bench_hover else (30, 45, 75)
            btn_border = ACCENT_HOVER if bench_hover else ACCENT
            pygame.draw.rect(panel, btn_bg, self._bench_btn_rect, border_radius=6)
            pygame.draw.rect(panel, btn_border, self._bench_btn_rect, 2, border_radius=6)
            
            btn_txt = self._bold_font.render("⚡ BENCHMARK LEVEL", True, TEXT_PRIMARY)
            panel.blit(btn_txt, btn_txt.get_rect(center=self._bench_btn_rect.center))
        else:
            pygame.draw.rect(panel, (30, 30, 40), self._bench_btn_rect, border_radius=6)
            pygame.draw.rect(panel, (50, 50, 60), self._bench_btn_rect, 1, border_radius=6)
            btn_txt = self._bold_font.render("🔒 BENCHMARK LOCKED", True, TEXT_MUTED)
            panel.blit(btn_txt, btn_txt.get_rect(center=self._bench_btn_rect.center))
        y += 48

        # Features List
        features_lbl = self._bold_font.render("CHALLENGE FEATURES:", True, TEXT_MUTED)
        panel.blit(features_lbl, (20, y))
        y += 25

        features = [
            ("🌫️ Fog of War", lv.fog_of_war),
            ("🔑 Locked Doors / CSP", lv.has_puzzle),
            ("👾 Patrol Monsters", lv.has_monsters),
        ]
        for name, active in features:
            status_char = "YES" if active else "NO"
            clr = SUCCESS if active else TEXT_MUTED
            feat_surf = self._sub_font.render(f"{name}:", True, TEXT_PRIMARY)
            val_surf = self._bold_font.render(status_char, True, clr)
            panel.blit(feat_surf, (20, y))
            panel.blit(val_surf, (200, y))
            y += 20

        # Allowed Algorithms Tag Pills (Wrapped nicely!)
        y += 15
        algos_lbl = self._bold_font.render("ALLOWED AI SOLVERS:", True, TEXT_MUTED)
        panel.blit(algos_lbl, (20, y))
        y += 25

        tx, ty = 20, y
        tag_h = 24
        for algo in sorted(list(lv.allowed_algorithms)):
            tag_str = algo.upper()
            text_w = self._algo_font.size(tag_str)[0]
            tag_w = text_w + 16
            
            # Wrap to next row if overflowing panel boundary
            if tx + tag_w > 300:
                tx = 20
                ty += 30

            # Draw tag capsule pill
            bg_clr = (40, 50, 75) if is_unlocked else (30, 30, 40)
            brd_clr = ACCENT if is_unlocked else (50, 50, 60)
            txt_clr = TEXT_PRIMARY if is_unlocked else TEXT_MUTED

            pygame.draw.rect(panel, bg_clr, (tx, ty, tag_w, tag_h), border_radius=12)
            pygame.draw.rect(panel, brd_clr, (tx, ty, tag_w, tag_h), 1, border_radius=12)

            t_surf = self._algo_font.render(tag_str, True, txt_clr)
            panel.blit(t_surf, t_surf.get_rect(center=(tx + tag_w // 2, ty + tag_h // 2)))
            tx += tag_w + 8

        # Developer unlock helper button (bottom of panel)
        dev_bg = (50, 20, 25) if self._dev_hover else (30, 15, 20)
        dev_brd = DANGER if self._dev_hover else (80, 40, 45)
        pygame.draw.rect(panel, dev_bg, self._dev_unlock_btn, border_radius=6)
        pygame.draw.rect(panel, dev_brd, self._dev_unlock_btn, 2, border_radius=6)
        
        dev_txt = self._bold_font.render("🔓 DEV: UNLOCK ALL LEVELS", True, WARNING if self._dev_hover else DANGER)
        panel.blit(dev_txt, dev_txt.get_rect(center=self._dev_unlock_btn.center))
