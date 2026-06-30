"""
benchmark_scene.py — Interactive scene to display headlessly evaluated search algorithms results.
"""

from __future__ import annotations

import pygame
from typing import Dict, List, Any

from config.settings import (
    DARK_BG,
    PANEL_BG,
    PANEL_BORDER,
    TEXT_PRIMARY,
    TEXT_MUTED,
    SUCCESS,
    WARNING,
    DANGER,
    ACCENT,
    ACCENT_HOVER,
)
from core.event_bus import EventBus
from core.state_machine import GameState, StateMachine
from scene.base_scene import BaseScene
from ui.widgets import Button, StatRow
from systems.benchmark_runner import BenchmarkRunner, BenchmarkResult
from config.level_config import LEVEL_MAP


class BenchmarkScene(BaseScene):
    """Sortable table scene showing performance metrics for each allowed level algorithm."""

    def __init__(
        self,
        bus: EventBus,
        state_machine: StateMachine,
        game_surface: pygame.Surface,
        panel_surface: pygame.Surface,
        level_id: int,
    ) -> None:
        super().__init__(bus, state_machine, game_surface)
        self._panel_surface = panel_surface
        self._level_id = level_id

        # Run benchmark headlessly
        lv = LEVEL_MAP[level_id]
        allowed_algos = list(lv.allowed_algorithms)
        self._results_dict = BenchmarkRunner.run_benchmark(level_id, allowed_algos)
        self._results_list = list(self._results_dict.values())

        # Sort state
        self._sort_key = "time_ms"  # "name", "success", "time_ms", "nodes", "cost", "length"
        self._sort_reverse = False
        self._sort_results()

        # Fonts
        self._title_font = pygame.font.SysFont("consolas", 24, bold=True)
        self._bold_font = pygame.font.SysFont("consolas", 16, bold=True)
        self._font = pygame.font.SysFont("consolas", 14)
        self._header_font = pygame.font.SysFont("consolas", 12, bold=True)

        # Back button
        self._back_btn = Button(
            20, 100, 280, 42, "BACK TO LEVEL SELECT", self._bold_font, (40, 45, 60), (60, 65, 80), PANEL_BORDER
        )

        # Sort Buttons on panel
        self._sort_time_btn = Button(20, 200, 280, 36, "Sort by Time", self._font, PANEL_BG, ACCENT_HOVER, PANEL_BORDER)
        self._sort_nodes_btn = Button(20, 250, 280, 36, "Sort by Nodes Expanded", self._font, PANEL_BG, ACCENT_HOVER, PANEL_BORDER)
        self._sort_cost_btn = Button(20, 300, 280, 36, "Sort by Path Cost", self._font, PANEL_BG, ACCENT_HOVER, PANEL_BORDER)

        # Header columns bounding boxes for sorting by click on main table
        self._headers = [
            ("Algorithm", "name", pygame.Rect(50, 140, 180, 30)),
            ("Success", "success", pygame.Rect(240, 140, 80, 30)),
            ("Time (ms)", "time_ms", pygame.Rect(330, 140, 100, 30)),
            ("Nodes Exp.", "nodes", pygame.Rect(440, 140, 100, 30)),
            ("Cost", "cost", pygame.Rect(550, 140, 80, 30)),
            ("Length", "length", pygame.Rect(640, 140, 80, 30)),
        ]

    def _sort_results(self) -> None:
        if self._sort_key == "name":
            self._results_list.sort(key=lambda r: r.display_name, reverse=self._sort_reverse)
        elif self._sort_key == "success":
            self._results_list.sort(key=lambda r: r.success, reverse=self._sort_reverse)
        elif self._sort_key == "time_ms":
            self._results_list.sort(key=lambda r: r.time_ms if r.success else 9999999, reverse=self._sort_reverse)
        elif self._sort_key == "nodes":
            self._results_list.sort(key=lambda r: r.nodes_expanded if r.success else 9999999, reverse=self._sort_reverse)
        elif self._sort_key == "cost":
            self._results_list.sort(key=lambda r: r.path_cost if r.success else 9999999, reverse=self._sort_reverse)
        elif self._sort_key == "length":
            self._results_list.sort(key=lambda r: r.path_length if r.success else 9999999, reverse=self._sort_reverse)

    def handle_event(self, event: pygame.event.Event) -> None:
        self._back_btn.handle_event(event, offset_x=960)
        self._sort_time_btn.handle_event(event, offset_x=960)
        self._sort_nodes_btn.handle_event(event, offset_x=960)
        self._sort_cost_btn.handle_event(event, offset_x=960)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            
            # 1. Back button
            if self._back_btn.rect.collidepoint(mx - 960, my):
                self._sm.transition(GameState.LEVEL_SELECT)
                return

            # 2. Panel Sort Buttons
            if self._sort_time_btn.rect.collidepoint(mx - 960, my):
                self._sort_key = "time_ms"
                self._sort_reverse = False
                self._sort_results()
                return
            if self._sort_nodes_btn.rect.collidepoint(mx - 960, my):
                self._sort_key = "nodes"
                self._sort_reverse = False
                self._sort_results()
                return
            if self._sort_cost_btn.rect.collidepoint(mx - 960, my):
                self._sort_key = "cost"
                self._sort_reverse = False
                self._sort_results()
                return

            # 3. Main table header clicks
            for label, key, rect in self._headers:
                if rect.collidepoint(mx, my):
                    if self._sort_key == key:
                        self._sort_reverse = not self._sort_reverse
                    else:
                        self._sort_key = key
                        self._sort_reverse = False
                    self._sort_results()
                    break

    def update(self, dt: float) -> None:
        pass

    def render(self, surface: pygame.Surface) -> None:
        surface.fill(DARK_BG)

        # Header Title
        title_surf = self._title_font.render(f"LEVEL {self._level_id} ALGORITHM BENCHMARK REPORT", True, WARNING)
        surface.blit(title_surf, title_surf.get_rect(center=(surface.get_width() // 2, 50)))

        # Help tip
        tip_surf = self._font.render("Click table headers on this screen to sort result rows dynamically.", True, TEXT_MUTED)
        surface.blit(tip_surf, tip_surf.get_rect(center=(surface.get_width() // 2, 90)))

        # Draw Table Headers
        pygame.draw.rect(surface, (20, 22, 35), (40, 130, 880, 40), border_radius=6)
        pygame.draw.rect(surface, PANEL_BORDER, (40, 130, 880, 40), 1, border_radius=6)

        for label, key, rect in self._headers:
            # Highlight sorted column
            color = ACCENT if key == self._sort_key else TEXT_PRIMARY
            suffix = " ▲" if (key == self._sort_key and not self._sort_reverse) else (" ▼" if (key == self._sort_key and self._sort_reverse) else "")
            lbl_surf = self._header_font.render(label + suffix, True, color)
            surface.blit(lbl_surf, lbl_surf.get_rect(midleft=(rect.x, rect.centery)))

        # Draw Rows
        ry = 180
        # Find fastest (min time) and slowest (max time) to apply row coloring
        successful_runs = [r for r in self._results_list if r.success]
        fastest_key = min(successful_runs, key=lambda r: r.time_ms).algorithm_key if successful_runs else ""
        slowest_key = max(successful_runs, key=lambda r: r.time_ms).algorithm_key if len(successful_runs) > 1 else ""

        for res in self._results_list:
            # Determine row bg color/border
            if not res.success:
                border_color = (60, 40, 40)
                bg_color = (25, 15, 15)
                text_color = TEXT_MUTED
            elif res.algorithm_key == fastest_key:
                border_color = (40, 100, 50)
                bg_color = (15, 30, 20)
                text_color = SUCCESS
            elif res.algorithm_key == slowest_key:
                border_color = (100, 40, 40)
                bg_color = (30, 15, 15)
                text_color = DANGER
            else:
                border_color = PANEL_BORDER
                bg_color = (20, 20, 30)
                text_color = TEXT_PRIMARY

            rect = pygame.Rect(40, ry, 880, 36)
            pygame.draw.rect(surface, bg_color, rect, border_radius=6)
            pygame.draw.rect(surface, border_color, rect, 1, border_radius=6)

            # Draw cell text
            # Col 1: Name
            name_surf = self._font.render(res.display_name, True, text_color)
            surface.blit(name_surf, (50, ry + 10))

            # Col 2: Success
            status_str = "SUCCESS" if res.success else "FAILED"
            status_color = SUCCESS if res.success else DANGER
            status_surf = self._bold_font.render(status_str, True, status_color)
            surface.blit(status_surf, (240, ry + 10))

            # Col 3: Time
            time_str = f"{res.time_ms:.2f} ms" if res.success else "N/A"
            time_surf = self._font.render(time_str, True, text_color)
            surface.blit(time_surf, (330, ry + 10))

            # Col 4: Nodes
            nodes_str = str(res.nodes_expanded) if res.success else "N/A"
            nodes_surf = self._font.render(nodes_str, True, text_color)
            surface.blit(nodes_surf, (440, ry + 10))

            # Col 5: Cost
            cost_str = f"{res.path_cost:.1f}" if res.success else "N/A"
            cost_surf = self._font.render(cost_str, True, text_color)
            surface.blit(cost_surf, (550, ry + 10))

            # Col 6: Length
            len_str = f"{res.path_length}" if res.success else "N/A"
            len_surf = self._font.render(len_str, True, text_color)
            surface.blit(len_surf, (640, ry + 10))

            ry += 42

    def render_panel(self, panel: pygame.Surface) -> None:
        panel.fill(PANEL_BG)
        pygame.draw.line(panel, PANEL_BORDER, (0, 0), (0, 720), 2)

        # Title
        title_surf = self._title_font.render("⚡ BENCH CONTROLS", True, TEXT_PRIMARY)
        panel.blit(title_surf, (20, 20))
        pygame.draw.line(panel, PANEL_BORDER, (10, 60), (310, 60), 2)

        # Buttons
        self._back_btn.render(panel)
        self._sort_time_btn.render(panel)
        self._sort_nodes_btn.render(panel)
        self._sort_cost_btn.render(panel)

        # Summary detail
        y = self._sort_cost_btn.rect.bottom + 44
        pygame.draw.line(panel, PANEL_BORDER, (10, y), (310, y), 1)
        sum_hdr = self._bold_font.render("BENCHMARK SUMMARY", True, TEXT_PRIMARY)
        panel.blit(sum_hdr, (20, y + 15))

        successful = [r for r in self._results_list if r.success]
        total_runs = len(self._results_list)
        
        y += 40
        y = StatRow("Total Algos:", f"{total_runs}", self._font).render(panel, 20, y)
        y = StatRow("Succeeded:", f"{len(successful)} / {total_runs}", self._font).render(panel, 20, y)
        
        if successful:
            fastest = min(successful, key=lambda r: r.time_ms)
            y = StatRow("Fastest Algo:", fastest.display_name, self._font).render(panel, 20, y)
